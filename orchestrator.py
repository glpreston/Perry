"""
Lightweight orchestrator for multi-agent calls with optional delegation.

This implementation supports:
- per-agent calls via `/api/generate`
- delegation detection ("ask <Agent> ...") with a toggle
- persistence hooks via `memory_db.save_qa`
"""

import json
import logging
import re
import requests
import uuid
import time
from typing import Dict, List, Optional, Tuple

from agents import Agent
from prompt_builder import PromptBuilder
from router import Router


class MultiAgentOrchestrator:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.moderator: Optional[Agent] = None
        self.use_moderator: bool = False
        # Whether to ask the primary agent to rephrase/quote delegated replies
        self.use_primary_rephrase: bool = True
        self.servers: Dict[str, str] = {}
        self.agent_styles: Dict[str, dict] = {}
        self.memory_db = None
        self.use_memory: bool = True
        self.use_group_memory: bool = True
        self.use_delegation: bool = True
        # agent_status: name -> one of 'ok', 'down', 'unknown'
        self.agent_status: Dict[str, str] = {}
        # Circuit breaker / failure tracking
        self.fail_counts: Dict[str, int] = {}
        self.cooldowns: Dict[str, float] = {}
        self.cooldown_seconds: float = 30.0
        self.failure_threshold: int = 2
        # Logger
        self.logger = logging.getLogger(__name__)
        if not logging.getLogger().handlers:
            logging.basicConfig(level=logging.INFO)

    def chat(self, user_query: str, messages=None) -> Dict[str, str]:
        """Send user_query to one or more agents and return a mapping agent->reply."""
        original_query = user_query or ""
        replies: Dict[str, str] = {}

        # decide whether the query targets a specific agent
        target_agent, _ = Router.route(original_query, list(self.agents.keys()))
        conv_id = str(uuid.uuid4())

        # primary agent(s)
        if target_agent:
            agent_items = [(target_agent, self.agents[target_agent])]
        else:
            agent_items = [(n, a) for n, a in self.agents.items() if n != "Moderator"]

        # detect delegated chained calls if target_agent and delegation enabled
        chained_calls: List[Tuple[str, str]] = []
        if target_agent and self.use_delegation:
            lowered_q = original_query.lower()
            prefixes = [
                "ask",
                "please ask",
                "can you ask",
                "could you ask",
                "please have",
                "tell",
                "relay to",
                "pass to",
            ]
            for aname in self.agents.keys():
                if aname.lower() == target_agent.lower():
                    continue
                for pref in prefixes:
                    pattern = rf"{pref}\s+{re.escape(aname.lower())}\b(?:\s+(?:to|about|if|whether|for))?[\s,:-]+(.+)"
                    m = re.search(pattern, lowered_q, re.IGNORECASE)
                    if m:
                        q = m.group(1).strip()
                        if q:
                            chained_calls.append((aname, q))
                            break
                if chained_calls:
                    break
            # proximity fallback
            if not chained_calls and "ask" in lowered_q:
                for aname in self.agents.keys():
                    if aname.lower() == target_agent.lower():
                        continue
                    idx = lowered_q.find("ask")
                    if idx >= 0:
                        tail = lowered_q[idx : idx + 120]
                        if aname.lower() in tail:
                            parts = tail.split(aname.lower(), 1)
                            if len(parts) > 1:
                                q = parts[1].strip(" \t\n,:-\"'")
                                if q:
                                    chained_calls.append((aname, q))
                                    break

        # call primary agents
        for name, agent in agent_items:
            # check cooldown
            now = time.time()
            cd = self.cooldowns.get(name)
            if cd and cd > now:
                self.logger.info(f"Skipping {name} due to cooldown until {cd}")
                replies[name] = "(Agent temporarily unavailable)"
                continue
            payload = {
                "model": getattr(agent, "model", None),
                "prompt": PromptBuilder.build_prompt(
                    original_query,
                    name,
                    agent,
                    self.memory_db,
                    self.use_memory,
                    self.use_group_memory,
                    target_agent,
                ),
                # include agent name in system prompt so the model answers as the agent
                "system": f"You are {name}. "
                + (getattr(agent, "persona", "") or getattr(agent, "personality", "")),
                "stream": False,
            }
            # try with one retry on failure
            attempt = 0
            resp = None
            while attempt < 2:
                try:
                    resp = requests.post(
                        f"{agent.host}/api/generate", json=payload, timeout=30
                    )
                    if resp is not None and resp.status_code == 200:
                        data = resp.json()
                        text = (
                            data.get("response") or data.get("output") or ""
                        ).strip()
                        replies[name] = text or "(No response)"
                        break
                    else:
                        replies[name] = "(Agent unavailable)"
                        # mark status down and increment failure count
                        self.agent_status[name] = "down"
                        self.fail_counts[name] = self.fail_counts.get(name, 0) + 1
                        if self.fail_counts[name] >= self.failure_threshold:
                            self.cooldowns[name] = time.time() + self.cooldown_seconds
                except Exception as e:
                    replies[name] = f"(Request error for {name}: {e})"
                    self.agent_status[name] = "down"
                    self.fail_counts[name] = self.fail_counts.get(name, 0) + 1
                    if self.fail_counts[name] >= self.failure_threshold:
                        self.cooldowns[name] = time.time() + self.cooldown_seconds

                attempt += 1
                if attempt < 2:
                    try:
                        self.logger.info(
                            f"[Orch] retrying {name} (attempt {attempt+1})"
                        )
                        time.sleep(1)
                    except Exception:
                        pass
            # if the final outcome looked successful, mark agent ok
            try:
                if replies.get(name) and not replies.get(name).startswith("("):
                    self.agent_status[name] = "ok"
                    # reset failure counts on success
                    self.fail_counts[name] = 0
                    if name in self.cooldowns:
                        del self.cooldowns[name]
            except Exception:
                pass

            # persist per-agent QA
            try:
                if self.memory_db and replies.get(name) is not None:
                    ans = replies.get(name)
                    low = (ans or "").lower()
                    is_err = ans.startswith("(") and (
                        "timed out" in low or "request error" in low
                    )
                    if is_err:
                        self.memory_db.save_qa(
                            name, original_query, "", conv_id=conv_id
                        )
                    else:
                        self.memory_db.save_qa(
                            name, original_query, ans, conv_id=conv_id
                        )
            except Exception:
                pass

        # Debug: report primary replies collected so far
        try:
            self.logger.info(f"[Orch] conv_id={conv_id} primary_replies={replies}")
        except Exception:
            pass

        # broadcast question-only group memory row (when no target agent)
        if not target_agent and self.use_group_memory and self.memory_db:
            try:
                self.memory_db.save_qa("__group__", original_query, "", conv_id=conv_id)
            except Exception:
                pass

        # handle chained delegated calls
        if target_agent and chained_calls:
            for cname, cquestion in chained_calls:
                cagent = self.agents.get(cname)
                if not cagent:
                    replies[cname] = f"(Agent {cname} not found)"
                    continue
                primary = replies.get(target_agent, "")[:800]
                chained_prompt = (
                    f"[Requested by {target_agent}]\nPrimary reply: {primary}\n---\n"
                    + cquestion
                )
                payload = {
                    "model": cagent.model,
                    "prompt": PromptBuilder.build_prompt(
                        chained_prompt,
                        cname,
                        cagent,
                        self.memory_db,
                        self.use_memory,
                        self.use_group_memory,
                        target_agent=cname,
                    ),
                    "system": getattr(cagent, "persona", "")
                    or getattr(cagent, "personality", ""),
                    "stream": False,
                }
                # chained call: also retry once on failure
                attempt = 0
                while attempt < 2:
                    try:
                        cresp = requests.post(
                            f"{cagent.host}/api/generate", json=payload, timeout=60
                        )
                        if cresp is not None and cresp.status_code == 200:
                            cdata = cresp.json()
                            creply = (
                                cdata.get("response") or cdata.get("output") or ""
                            ).strip()
                            replies[cname] = creply or "(No response)"
                            self.agent_status[cname] = "ok"
                            break
                        else:
                            replies[cname] = "(Agent unavailable)"
                            self.agent_status[cname] = "down"
                    except Exception as e:
                        replies[cname] = f"(Request error for {cname}: {e})"
                        self.agent_status[cname] = "down"

                    attempt += 1
                    if attempt < 2:
                        try:
                            self.logger.info(
                                f"[Orch] retrying chained call {cname} (attempt {attempt+1})"
                            )
                            time.sleep(1)
                        except Exception:
                            pass

                # persist chained QA
                try:
                    if self.memory_db and replies.get(cname) is not None:
                        self.memory_db.save_qa(
                            cname, cquestion, replies.get(cname), conv_id=conv_id
                        )
                except Exception:
                    pass

            # If we have chained replies, append them to the primary agent's reply
            try:
                if target_agent in replies and chained_calls:
                    parts = []
                    for cname, _ in chained_calls:
                        ctext = replies.get(cname, "(no reply)")
                        parts.append(f"[{cname} replied]: {ctext}")
                    if parts:
                        # Append quoted replies to primary agent's reply so it can quote others
                        replies[target_agent] = (
                            replies.get(target_agent, "") + "\n\n" + "\n\n".join(parts)
                        )
            except Exception:
                pass

            # Ask the primary agent to rephrase/quote other agents' replies for a natural quote
            # This step can be toggled via `use_primary_rephrase` to avoid extra agent calls.
            if self.use_primary_rephrase:
                try:
                    primary_agent = self.agents.get(target_agent)
                    if primary_agent:
                        primary_before = replies.get(target_agent, "")
                    rephrase_parts = [
                        f"Original question: {original_query}",
                        f"Your original reply: {primary_before}",
                        "Other agents replied:",
                    ]
                    for cname, _ in chained_calls:
                        retext = replies.get(cname, "(no reply)")
                        rephrase_parts.append(f"- {cname}: {retext}")
                    # Strongly instruct the primary agent to produce a predictable quoting format
                    # The response must be in the primary agent's voice and follow this exact structure:
                    # <AgentName>: "<final reply content>"
                    # Quoted replies:
                    # - <OtherAgentName>: "<their reply>"
                    # The primary reply should be 1-3 sentences and may include a short justification.
                    rephrase_prompt = (
                        "\n".join(rephrase_parts)
                        + "\n\nPlease produce a revised reply in the voice of "
                        + target_agent
                        + ". Follow this exact format (do not add extra sections):\n"
                        + f'{target_agent}: "<your reply here>"\n\nQuoted replies:\n'
                    )
                    for cname, _ in chained_calls:
                        crep = replies.get(cname, "(no reply)")
                        rephrase_prompt += f'- {cname}: "{crep}"\n'
                    rephrase_prompt += "\nKeep the final reply concise (1-3 sentences). If you rely on another agent's answer, briefly cite them in parentheses."

                    rpayload = {
                        "model": getattr(primary_agent, "model", None),
                        "prompt": PromptBuilder.build_prompt(
                            rephrase_prompt,
                            target_agent,
                            primary_agent,
                            self.memory_db,
                            self.use_memory,
                            self.use_group_memory,
                            target_agent=target_agent,
                        ),
                        "system": f"You are {target_agent}. "
                        + (
                            getattr(primary_agent, "persona", "")
                            or getattr(primary_agent, "personality", "")
                        ),
                        "stream": False,
                    }
                    try:
                        rresp = requests.post(
                            f"{primary_agent.host}/api/generate",
                            json=rpayload,
                            timeout=30,
                        )
                        if rresp is not None and rresp.status_code == 200:
                            rdata = rresp.json()
                            rtext = (
                                rdata.get("response") or rdata.get("output") or ""
                            ).strip()
                            if rtext:
                                replies[target_agent] = rtext
                                # persist rephrased primary reply
                                try:
                                    if self.memory_db:
                                        self.memory_db.save_qa(
                                            target_agent,
                                            original_query,
                                            rtext,
                                            conv_id=conv_id,
                                        )
                                except Exception:
                                    pass
                        else:
                            # keep existing primary reply
                            pass
                    except Exception:
                        pass
                except Exception:
                    pass

        # Debug: final reply set for this chat invocation
        try:
            self.logger.debug(f"[Orch] conv_id={conv_id} final_replies={replies}")
        except Exception:
            pass

        # If this was a broadcast and a moderator is enabled, ask the moderator to summarize
        if not target_agent and self.use_moderator and self.moderator:
            try:
                # Build a concise summary prompt containing the question and agent replies
                summary_parts = [f"Question: {original_query}", "Replies:"]
                for n, txt in replies.items():
                    summary_parts.append(f"- {n}: {txt}")
                summary_prompt = "\n".join(summary_parts)

                # Instruct the Moderator to rank and recommend the best answer
                moderator_instruction = (
                    "You are Moderator. Read the question and the replies and: "
                    "(1) identify which agent gave the best answer, (2) provide a concise authoritative recommendation that cites the chosen reply, "
                    "and (3) include a short justification (1-2 sentences)."
                )

                mpayload = {
                    "model": getattr(self.moderator, "model", None),
                    "prompt": PromptBuilder.build_prompt(
                        summary_prompt
                        + "\n\nPlease rank these replies and give a single recommended answer.",
                        self.moderator.name,
                        self.moderator,
                        self.memory_db,
                        self.use_memory,
                        self.use_group_memory,
                        target_agent=None,
                    ),
                    "system": moderator_instruction
                    + " "
                    + (
                        getattr(self.moderator, "persona", "")
                        or getattr(self.moderator, "personality", "")
                    ),
                    "stream": False,
                }
                mresp = None
                try:
                    mresp = requests.post(
                        f"{self.moderator.host}/api/generate", json=mpayload, timeout=30
                    )
                    if mresp is not None and mresp.status_code == 200:
                        mdata = mresp.json()
                        mtext = (
                            mdata.get("response") or mdata.get("output") or ""
                        ).strip()
                        replies["Moderator"] = mtext or "(No moderator response)"
                        # persist moderator QA
                        try:
                            if self.memory_db:
                                self.memory_db.save_qa(
                                    "Moderator",
                                    summary_prompt,
                                    replies.get("Moderator"),
                                    conv_id=conv_id,
                                )
                        except Exception:
                            pass
                        # mark moderator ok
                        self.agent_status["Moderator"] = "ok"
                    else:
                        replies["Moderator"] = "(Moderator unavailable)"
                        self.agent_status["Moderator"] = "down"
                except Exception as e:
                    replies["Moderator"] = f"(Moderator error: {e})"
                    self.agent_status["Moderator"] = "down"
            except Exception:
                pass

        return replies

    def add_agent(self, name: str, host: str, model: str, persona: str):
        self.agents[name] = Agent(name, host, model, persona)

    def set_delegation_usage(self, use_delegation: bool):
        self.use_delegation = bool(use_delegation)

    def set_memory_usage(self, use_memory: bool):
        self.use_memory = bool(use_memory)

    def load_config(self, path: str = "agents_config.json") -> None:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        self.servers = cfg.get("servers", {})
        self.agent_styles = cfg.get("agent_styles", {})

        self.agents = {}
        for agent_cfg in cfg.get("agents", []):
            server_url = self.servers.get(
                agent_cfg.get("server"), agent_cfg.get("server")
            )
            persona = agent_cfg.get("personality") or agent_cfg.get("persona", "")
            self.add_agent(
                agent_cfg["name"], server_url, agent_cfg.get("model"), persona
            )

        # moderator
        self.use_moderator = cfg.get("use_moderator", False)
        moderator_cfg = cfg.get("moderator")
        if moderator_cfg:
            server_url = self.servers.get(
                moderator_cfg.get("server"), moderator_cfg.get("server")
            )
            mod_persona = moderator_cfg.get("personality") or moderator_cfg.get(
                "persona", "You are the moderator."
            )
            self.moderator = Agent(
                "Moderator", server_url, moderator_cfg.get("model"), mod_persona
            )
            if self.use_moderator:
                self.agents["Moderator"] = self.moderator

    def save_config(self, path: str = "agents_config.json") -> None:
        cfg = {
            "servers": self.servers,
            "agent_styles": self.agent_styles,
            "agents": [],
            "use_moderator": self.use_moderator,
            "moderator": {"server": None, "model": None, "persona": None},
        }

        for name, agent in self.agents.items():
            if name == "Moderator":
                continue
            server_name = None
            for k, v in self.servers.items():
                if v == agent.host:
                    server_name = k
                    break
            cfg["agents"].append(
                {
                    "name": agent.name,
                    "server": server_name or agent.host,
                    "model": agent.model,
                    "persona": agent.persona,
                }
            )

        if self.moderator:
            server_name = None
            for k, v in self.servers.items():
                if v == self.moderator.host:
                    server_name = k
                    break
            cfg["moderator"] = {
                "server": server_name or self.moderator.host,
                "model": self.moderator.model,
                "persona": self.moderator.persona,
            }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

    def check_agents(self, timeout: float = 2.0) -> Dict[str, str]:
        """Ping each configured agent to determine health.

        Tries `/api/health` then `/health` on the agent host. Updates
        `self.agent_status` and returns the mapping name->status.
        """
        results: Dict[str, str] = {}
        for name, agent in self.agents.items():
            status = "unknown"
            try:
                # prefer explicit health endpoint
                urls = [f"{agent.host}/api/health", f"{agent.host}/health", agent.host]
                ok = False
                for u in urls:
                    try:
                        r = requests.get(u, timeout=timeout)
                        if r is not None and r.status_code == 200:
                            ok = True
                            break
                    except Exception:
                        continue
                status = "ok" if ok else "down"
            except Exception:
                status = "down"
            self.agent_status[name] = status
            results[name] = status
        return results

    def set_moderator(self):
        """Ensure the Moderator agent is present or removed according to `self.use_moderator`.

        If a moderator Agent instance doesn't exist and `use_moderator` is True,
        create a lightweight default moderator using the first configured server
        (if available) and a generic persona. If `use_moderator` is False,
        remove the Moderator from `self.agents` but keep `self.moderator` for
        future re-enablement.
        """
        try:
            if self.use_moderator:
                if not self.moderator:
                    # pick a server host if available, else empty string
                    host = None
                    if isinstance(self.servers, dict) and len(self.servers) > 0:
                        # pick first server value
                        host = next(iter(self.servers.values()))
                    host = host or ""
                    self.moderator = Agent(
                        "Moderator", host, None, "You are the moderator."
                    )
                # ensure present in agents mapping
                self.agents["Moderator"] = self.moderator
            else:
                # disable moderator in active agents but keep the object for later
                if "Moderator" in self.agents:
                    try:
                        del self.agents["Moderator"]
                    except Exception:
                        pass
        except Exception:
            # swallow any errors here to avoid UI crashes
            return

    def set_primary_rephrase_usage(self, use_rephrase: bool):
        try:
            self.use_primary_rephrase = bool(use_rephrase)
        except Exception:
            pass

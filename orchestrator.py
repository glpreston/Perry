import json
import os

from agents import Agent
from prompt_builder import PromptBuilder
from router import Router


class MultiAgentOrchestrator:
    def __init__(self):
        self.agents = {}
        self.moderator = None
        self.use_moderator = False
        self.safe_mode = False
        self.servers = {}
        self.agent_styles = {}
        self.memory_db = None  # assume you have a memory_db object
        self.use_memory = True  # NEW: toggle for memory injection (enabled by default)
        self.use_group_memory = True  # optional: include global group memory (enabled by default)

        # Try to initialize MemoryDB if configuration/env is present.
        try:
            if os.getenv("DB_HOST"):
                from memory import MemoryDB
                try:
                    self.memory_db = MemoryDB()
                except Exception:
                    # If DB init fails, leave memory_db as None but don't crash the app
                    self.memory_db = None
        except Exception:
            # If memory module isn't available or other import errors, skip DB initialization
            self.memory_db = None

    def oldchat(self, user_query: str, messages):
        import requests
        replies = {}

        # Build the list of agents to query
        agent_items = list(self.agents.items())
        if self.use_moderator and self.moderator:
            agent_items.append(("Moderator", self.moderator))

        for name, agent in agent_items:
            host = agent.host  # resolved server URL from load_config
            model = getattr(agent, "model", None)

            # Compose payload; adapt to your server API
            payload = {
                "model": model,
                "prompt": user_query,
                "system": agent.persona,
                "stream": False
            }

            try:
                resp = requests.post(f"{host}/api/generate", json=payload, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    # Adapt field names if your server differs
                    reply_text = data.get("response") or data.get("output") or ""
                    replies[name] = reply_text.strip() if reply_text else "(No response)"
                else:
                    replies[name] = f"(Error {resp.status_code} from {name} at {host})"
            except Exception as e:
                replies[name] = f"(Request error for {name}: {e})"

        return replies

    def olderchat(self, user_query: str, messages):
        import requests
        replies = {}

        # Normalize query for matching
        lowered = user_query.lower()

        # Check if the query explicitly mentions an agent
        target_agent = None
        for name in self.agents.keys():
            if lowered.startswith(name.lower()) or name.lower() in lowered:
                target_agent = name
                break

        # Build list of agents to query
        if target_agent:
            agent_items = [(target_agent, self.agents[target_agent])]
        else:
            agent_items = list(self.agents.items())
            if self.use_moderator and self.moderator:
                agent_items.append(("Moderator", self.moderator))

        for name, agent in agent_items:
            host = agent.host
            model = agent.model
            payload = {
                "model": model,
                "prompt": user_query,
                "system": agent.persona,
                "stream": False
            }
            try:
                resp = requests.post(f"{host}/api/generate", json=payload, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    reply_text = data.get("response") or data.get("output") or ""
                    replies[name] = reply_text.strip() if reply_text else "(No response)"
                else:
                    replies[name] = f"(Error {resp.status_code} from {name} at {host})"
            except Exception as e:
                replies[name] = f"(Request error for {name}: {e})"

        return replies

    def olederrchat(self, user_query: str, messages):
        import requests

        replies = {}
        lowered = user_query.lower().strip()

        # Sort agent names by length so "Netty P" is checked before "Netty"
        agent_names_sorted = sorted(self.agents.keys(), key=lambda n: len(n), reverse=True)

        target_agent = None
        for name in agent_names_sorted:
            if lowered.startswith(name.lower()):
                target_agent = name
                break

        # Build list of agents to query
        if target_agent:
            agent_items = [(target_agent, self.agents[target_agent])]
        else:
            agent_items = list(self.agents.items())
            if self.use_moderator and self.moderator:
                agent_items.append(("Moderator", self.moderator))

        # Query each agent
        for name, agent in agent_items:
            host = agent.host
            model = agent.model
            payload = {
                "model": model,
                "prompt": user_query,
                "system": agent.persona,
                "stream": False
            }
            try:
                resp = requests.post(f"{host}/api/generate", json=payload, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    reply_text = data.get("response") or data.get("output") or ""
                    replies[name] = reply_text.strip() if reply_text else "(No response)"
                else:
                    replies[name] = f"(Error {resp.status_code} from {name} at {host})"
            except requests.exceptions.Timeout:
                replies[name] = "(Timed out — server too slow)"
            except Exception as e:
                replies[name] = f"(Request error for {name}: {e})"

        return replies

    def chat(self, user_query: str, messages):
        import re
        import requests

        replies = {}

        # Normalize input
        original_query = user_query
        lowered = original_query.lower().strip()

        # Routing: determine whether this is addressed to one agent or a broadcast
        agent_names_sorted = list(self.agents.keys())
        target_agent, matched_pattern = Router.route(original_query, agent_names_sorted)

        # Debug routing decision
        print(f"[Orchestrator] Routing decision: "
              f"{'target=' + target_agent if target_agent else 'broadcast'} | "
              f"matched_pattern={matched_pattern} | query='{original_query}'")

        # Build the list of agents to query
        if target_agent:
            agent_items = [(target_agent, self.agents[target_agent])]
        else:
            agent_items = list(self.agents.items())
            if self.use_moderator and self.moderator:
                agent_items.append(("Moderator", self.moderator))

        # (Do not save the user's message here; we'll persist QA pairs after replies.)

        # Query each selected agent (Ollama /api/generate)
        for name, agent in agent_items:
            host = agent.host
            model = agent.model

            # Build prompt (memory injection and sanitization) via PromptBuilder
            prompt = PromptBuilder.build_prompt(
                original_query,
                name,
                agent,
                self.memory_db,
                self.use_memory,
                self.use_group_memory,
                target_agent,
            )

            # Persona key in your config was "personality" in agents_config.json,
            # but you load it as agent_cfg.get("persona", "") in load_config.
            # Ensure agent.persona is set accordingly in load_config.
            system_prompt = getattr(agent, "persona", "") or getattr(agent, "personality", "")

            payload = {
                "model": model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False
            }

            try:
                resp = requests.post(f"{host}/api/generate", json=payload, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    reply_text = (data.get("response") or data.get("output") or "").strip()
                    replies[name] = reply_text if reply_text else "(No response)"
                else:
                    replies[name] = f"(Error {resp.status_code} from {name} at {host})"
            except requests.exceptions.Timeout:
                replies[name] = "(Timed out — server too slow)"
            except Exception as e:
                replies[name] = f"(Request error for {name}: {e})"

            # Persist QA pair into memory if DB is available
            try:
                if self.memory_db and replies.get(name) is not None:
                    reply_text = replies.get(name)
                    # Detect timeout/error replies and do not save them as the 'answer' field
                    low = (reply_text or "").lower()
                    is_err = (reply_text.startswith("(") and ("timed out" in low or "request error" in low or low.startswith("(error")))
                    try:
                        if is_err:
                            # Save question-only (answer empty) so we don't inject error text
                            self.memory_db.save_qa(name, original_query, "")
                        else:
                            self.memory_db.save_qa(name, original_query, reply_text)
                    except Exception:
                        # Fallback: save legacy memory_text (avoid storing error text as answer)
                        if not is_err:
                            self.memory_db.save_memory(name, reply_text)
                        else:
                            self.memory_db.save_memory(name, original_query)
            except Exception:
                pass

        # If this was a broadcast (no specific target) and we have a Moderator reply,
        # save the Moderator's synthesized answer into group memory as a QA pair.
        try:
            if target_agent is None and self.memory_db:
                GROUP_KEY = "__group__"
                # Save the broadcast user's message into group memory as a question (answer may be empty)
                try:
                    self.memory_db.save_qa(GROUP_KEY, original_query, "")
                except Exception:
                    try:
                        self.memory_db.save_group_memory(original_query)
                    except Exception:
                        self.memory_db.save_memory(GROUP_KEY, original_query)

                # Note: do NOT save the Moderator's synthesized answer into group memory
                # to avoid echoing the moderator's own synthesis back into agents.
        except Exception:
            pass

        return replies

    def add_agent(self, name, host, model, persona):
        self.agents[name] = Agent(name, host, model, persona)

    def set_moderator(self):
        if self.use_moderator and self.moderator:
            self.agents["Moderator"] = self.moderator

    def set_memory_usage(self, use_memory: bool):
        """Enable or disable memory injection into prompts."""
        self.use_memory = use_memory

    def load_config(self, path="agents_config.json"):
        # Force UTF-8 when reading
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        # Load servers and styles
        self.servers = cfg.get("servers", {})
        self.agent_styles = cfg.get("agent_styles", {})

        # Load agents
        self.agents = {}
        for agent_cfg in cfg.get("agents", []):
            server_url = self.servers.get(agent_cfg["server"], agent_cfg["server"])
            # Support both 'personality' and legacy 'persona' keys in config
            persona = agent_cfg.get("personality") or agent_cfg.get("persona", "")
            self.add_agent(
                agent_cfg["name"],
                server_url,
                agent_cfg["model"],
                persona
            )

        # Load moderator
        self.use_moderator = cfg.get("use_moderator", False)
        moderator_cfg = cfg.get("moderator")
        if moderator_cfg:
            server_url = self.servers.get(moderator_cfg["server"], moderator_cfg["server"])
            mod_persona = moderator_cfg.get("personality") or moderator_cfg.get("persona", "You are the moderator.")
            self.moderator = Agent(
                "Moderator",
                server_url,
                moderator_cfg["model"],
                mod_persona
            )
            if self.use_moderator:
                self.agents["Moderator"] = self.moderator

    def save_config(self, path="agents_config.json"):
        cfg = {
            "servers": self.servers,
            "agent_styles": self.agent_styles,
            "agents": [],
            "use_moderator": self.use_moderator,
            "moderator": {
                "server": None,
                "model": None,
                "persona": None
            }
        }

        # Save agents
        for name, agent in self.agents.items():
            if name == "Moderator":
                continue
            server_name = None
            for k, v in self.servers.items():
                if v == agent.host:
                    server_name = k
                    break
            cfg["agents"].append({
                "name": agent.name,
                "server": server_name or agent.host,
                "model": agent.model,
                "persona": agent.persona
            })

        # Save moderator
        if self.moderator:
            server_name = None
            for k, v in self.servers.items():
                if v == self.moderator.host:
                    server_name = k
                    break
            cfg["moderator"] = {
                "server": server_name or self.moderator.host,
                "model": self.moderator.model,
                "persona": self.moderator.persona
            }

        # Force UTF-8 when writing, keep emojis
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

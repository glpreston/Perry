import re
from typing import List, Optional


class PromptBuilder:
    """Builds prompts for agents, including memory injection.

    This isolates memory formatting and any sanitization needed before
    sending the prompt to a model server.
    """

    @staticmethod
    def strip_leading_agent_name(q: str) -> str:
        if not q:
            return q
        # remove leading artifact like "AgentName: " or "AgentName - "
        return re.sub(r'^[A-Za-z0-9_\- ]{1,100}\s*[:\- ,]\s*', '', q)

    @staticmethod
    def is_error_text(s: str) -> bool:
        if not s:
            return False
        low = s.lower()
        return (low.startswith("(error") or "timed out" in low or "request error" in low or "timeout" in low)

    @staticmethod
    def format_memories(memories: List[dict], limit: int = 3) -> List[str]:
        out = []
        for item in memories[:limit]:
            q = PromptBuilder.strip_leading_agent_name(item.get('q', ''))
            a = item.get('a', '')
            out.append(f"Q: {q} A: {a}")
        return out

    @staticmethod
    def build_prompt(original_query: str,
                     agent_name: str,
                     agent_obj,
                     memory_db,
                     use_memory: bool,
                     use_group_memory: bool,
                     target_agent: Optional[str]) -> str:
        """Return the prompt string for the given agent.

        - `agent_obj` is the Agent instance (for persona, model, etc.)
        - `memory_db` is optional and should expose `load_recent_qa(name, limit)`
        """
        prompt = original_query

        if not use_memory or not memory_db:
            return prompt

        try:
            # Per-agent memories
            agent_qa = memory_db.load_recent_qa(agent_name, limit=10)
            filtered_agent_qa = [item for item in agent_qa if item.get('a') and not PromptBuilder.is_error_text(item.get('a'))]
            if filtered_agent_qa:
                formatted = PromptBuilder.format_memories(filtered_agent_qa, limit=3)
                prompt = "[Agent recent context: " + " | ".join(formatted) + "]\n\n" + prompt

            # Group memories: include for broadcasts or when explicitly enabled
            include_group = (target_agent is None) or use_group_memory
            if include_group:
                group_qa = memory_db.load_recent_qa(None, limit=10)
                filtered_group_qa = [item for item in group_qa if item.get('a') and not PromptBuilder.is_error_text(item.get('a'))]
                if filtered_group_qa:
                    gformatted = PromptBuilder.format_memories(filtered_group_qa, limit=3)
                    prompt = "[Group recent context: " + " | ".join(gformatted) + "]\n\n" + prompt
        except Exception:
            # Any memory errors should not stop prompt building
            pass

        return prompt

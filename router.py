import re
from typing import List, Optional, Tuple


class Router:
    """Simple router to decide if a query targets a specific agent or is a broadcast."""

    @staticmethod
    def route(original_query: str, agent_names: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """Return (target_agent, matched_pattern).

        `target_agent` is the name of the matched agent (or None for broadcast).
        `matched_pattern` is the regex used (or None).
        """
        lowered = (original_query or "").lower().strip()
        # sort by length to prefer longer names (avoid substrings)
        sorted_names = sorted(agent_names, key=lambda n: len(n), reverse=True)
        delim = r"(?:\s|:|,|-|$)"
        for name in sorted_names:
            pattern = rf"^{re.escape(name.lower())}{delim}"
            if re.match(pattern, lowered):
                return name, pattern
        return None, None

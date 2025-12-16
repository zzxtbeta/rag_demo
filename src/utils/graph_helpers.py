"""Graph-related helpers.

Keep `agent/graph.py` focused on graph wiring.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List

from langchain_core.messages import SystemMessage


def now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def prepend_system_prompt(messages: Iterable, system_prompt_template: str) -> List:
    """Prepend a SystemMessage built from template.

    The template is expected to accept `{time}`.
    """
    system_message = SystemMessage(content=system_prompt_template.format(time=now_iso()))
    return [system_message, *list(messages)]


__all__ = ["now_iso", "prepend_system_prompt"]

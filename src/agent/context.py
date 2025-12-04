"""Define the runtime context information for the agent."""

import os
from dataclasses import dataclass, field, fields

from typing_extensions import Annotated

from agent import prompts


@dataclass(kw_only=True)
class Context:
    """Runtime context for the Agentic RAG system."""

    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="qwen-plus-latest",
        metadata={
            "description": "The name of the language model to use. "
            "Default is DashScope Qwen Plus."
        },
    )

    def __post_init__(self):
        """Fetch env vars for attributes that were not passed as args."""
        for f in fields(self):
            if not f.init:
                continue

            if getattr(self, f.name) == f.default:
                setattr(self, f.name, os.environ.get(f.name.upper(), f.default))

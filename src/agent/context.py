"""定义代理的运行时上下文信息。"""

import os
from dataclasses import dataclass, field, fields

from typing_extensions import Annotated

from agent import prompts


@dataclass(kw_only=True)
class Context:
    """代理式 RAG 系统的运行时上下文。"""

    chat_model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="qwen-plus-latest",
        metadata={
            "description": "The name of the chat model to use. "
            "Default is DashScope Qwen Plus."
        },
    )

    def __post_init__(self):
        """获取未作为参数传递的属性的环境变量。"""
        for f in fields(self):
            if not f.init:
                continue

            if getattr(self, f.name) == f.default:
                setattr(self, f.name, os.environ.get(f.name.upper(), f.default))

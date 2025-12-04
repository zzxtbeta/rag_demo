"""LLM 加载工具。"""

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from config.settings import get_settings


def load_chat_model(
    fully_specified_name: str | None = None,
    temperature: float = 0.7,
    max_retries: int = 2,
) -> BaseChatModel:
    """Load a chat model configured via Settings."""
    settings = get_settings()
    model_name = fully_specified_name or settings.model_name

    return ChatOpenAI(
        model=model_name,
        api_key=settings.dascope_api_key,
        base_url=settings.dascope_base_url,
        temperature=temperature,
        max_retries=max_retries,
    )

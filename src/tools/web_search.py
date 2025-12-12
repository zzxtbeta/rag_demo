"""Web search tool using Tavily API for real-time information retrieval."""

from typing import Optional

from langchain.tools import tool
from langchain_community.tools import TavilySearchResults

from config.settings import get_settings


def _get_tavily_search_tool() -> Optional[TavilySearchResults]:
    """Initialize and return Tavily search tool if API key is configured.
    
    Returns:
        TavilySearchResults tool instance or None if API key is not set.
    """
    settings = get_settings()
    if not settings.tavily_api_key:
        return None
    
    return TavilySearchResults(
        max_results=5,
        include_raw_content=True,
        api_key=settings.tavily_api_key,
    )


@tool(response_format="content_and_artifact")
def web_search(query: str) -> tuple[str, list]:
    """Search the web for real-time information using Tavily.
    
    Use this tool when you need current information not available in the knowledge base,
    such as recent news, current events, real-time data, or information beyond your
    training data cutoff.
    
    Args:
        query: The search query string.
    
    Returns:
        tuple: (formatted_content, raw_results)
            - formatted_content: Human-readable search results
            - raw_results: Raw search result objects for reference
    """
    tavily_tool = _get_tavily_search_tool()
    if not tavily_tool:
        return (
            "Web search is not configured. Please set TAVILY_API_KEY in environment variables.",
            []
        )
    
    try:
        results = tavily_tool.invoke({"query": query})
        
        if isinstance(results, str):
            return results, []
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            if isinstance(result, dict):
                title = result.get("title", "No title")
                url = result.get("url", "No URL")
                content = result.get("content", "No content")
                formatted_results.append(
                    f"[{i}] {title}\nURL: {url}\nContent: {content}"
                )
            else:
                formatted_results.append(str(result))
        
        formatted_content = "\n\n".join(formatted_results)
        return formatted_content, results
    except Exception as e:
        error_msg = f"Web search failed: {str(e)}"
        return error_msg, []


__all__ = ["web_search", "_get_tavily_search_tool"]

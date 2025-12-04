"""Chat-related API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_graph
from api.schemas import ChatRequest, ChatResponse
from api.utils import extract_content


router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, graph=Depends(get_graph)):
    config = {"configurable": {"thread_id": req.thread_id}}
    if req.user_id:
        config["configurable"]["user_id"] = req.user_id

    payload = {"messages": [{"role": "user", "content": req.message}]}
    result = await graph.ainvoke(payload, config)

    messages = result.get("messages", [])
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Model returned empty response",
        )

    answer = extract_content(messages[-1])
    return ChatResponse(thread_id=req.thread_id, user_id=req.user_id, answer=answer)


__all__ = ["router"]


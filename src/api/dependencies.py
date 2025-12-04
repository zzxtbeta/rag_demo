"""Common FastAPI dependencies."""

from __future__ import annotations

from fastapi import HTTPException, Request, status


def get_graph(request: Request):
    """Fetch the compiled graph instance from app state."""
    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Graph is not ready yet",
        )
    return graph


__all__ = ["get_graph"]


from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/search")
async def search_references(request: SearchRequest):
    """Search reference corpus (debug-friendly endpoint)."""
    from app.main import app

    retrieval_svc = getattr(app.state, "retrieval_service", None)
    if not retrieval_svc:
        return {"results": [], "message": "Retrieval service not initialized"}
    results = retrieval_svc.search(request.query, request.top_k)
    return {"results": results, "query": request.query, "top_k": request.top_k}

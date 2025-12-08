from fastapi import APIRouter, Query
from typing import List, Dict, Any

from core.canonical_retriever import get_canonical_suggestions

router = APIRouter()


@router.get("/faq/search")
async def search_faq(
    query: str = Query(..., min_length=3),
    top_k: int = Query(3, ge=1, le=10),
    min_score: float = Query(0.72, ge=0.0, le=1.0),
) -> Dict[str, Any]:
    """
    Recherche FAQ dans les canoniques/paires Shadow.
    Retourne Top-K résultats au-dessus du seuil.
    """
    suggestions = await get_canonical_suggestions(
        question=query,
        top_k=top_k,
        min_similarity=min_score,
    )

    results: List[Dict[str, Any]] = []
    for s in suggestions:
        results.append({
            "question": s.get("question_example"),
            "response": s.get("answer"),
            "score": float(s.get("score", 0.0)),
            "source": s.get("source"),
        })

    best_score = max((r["score"] for r in results), default=0.0)
    has_match = bool(results) and best_score >= float(min_score)

    return {
        "query": query,
        "results": results,
        "has_match": has_match,
        "best_score": best_score,
    }

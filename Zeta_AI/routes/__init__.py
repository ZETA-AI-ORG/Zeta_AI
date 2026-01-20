from fastapi import APIRouter
from .meili import router as meili_router

# Endpoint de vérification pour N8N
@meili_router.get("/verify-indexation/{company_id}")
async def verify_indexation_endpoint(company_id: str):
    """
    Endpoint de vérification pour N8N - affiche l'état des index après ingestion
    """
    from ingestion.ingestion_api import verify_indexation_results
    
    results = verify_indexation_results(company_id)
    
    return {
        "company_id": company_id,
        "verification_results": results,
        "summary": {
            "total_documents": results["total_documents"],
            "indexes_with_data": len([s for s in results["indexes_status"].values() if s["document_count"] > 0]),
            "empty_indexes": len([s for s in results["indexes_status"].values() if s["document_count"] == 0]),
            "errors": len(results["errors"])
        }
    }
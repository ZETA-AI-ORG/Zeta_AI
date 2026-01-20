# Import du nouveau client natif
from .native_pgvector_client import native_client

# Fonctions de compatibilité avec l'ancien code
async def purge_company_chunks(company_id: str, collection_name: str = None, 
                             embedding_function=None, data_type: str = None) -> int:
    """Fonction de compatibilité - utilise le nouveau client natif"""
    return await native_client.purge_company_chunks(company_id, data_type)

async def insert_company_chunks(company_id: str, chunks: list, 
                               collection_name: str = None, embedding_function=None) -> list:
    """Fonction de compatibilité - utilise le nouveau client natif"""
    return await native_client.insert_company_chunks(company_id, chunks, "document")

async def upsert_company_chunks_by_chunk_id(company_id: str, chunks: list,
                                            collection_name: str = None, embedding_function=None) -> list:
    """Upsert idempotent basé sur metadata.chunk_id - utilise le client natif"""
    return await native_client.upsert_company_chunks_by_chunk_id(company_id, chunks, "document")

async def search_company_documents(company_id: str, query_embedding: list, 
                                 limit: int = 5, score_threshold: float = 0.5, mode: str = "dense", **kwargs) -> list:
    """Recherche avancée dans les documents d'une entreprise (multi-embedding)."""
    return await native_client.search_documents(company_id, query_embedding, "document", limit, score_threshold, mode=mode, **kwargs)

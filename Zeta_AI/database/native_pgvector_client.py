import os
import logging
import json
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.extensions import AsIs
from typing import List, Dict, Any, Optional
from .pgvector_config import PG_CONNECTION_STRING

logger = logging.getLogger(__name__)

class NativePGVectorClient:
    """
    Client PGVector natif utilisant directement la table 'documents' sans LangChain.
    Architecture propre avec contrôle total sur les requêtes SQL.
    """
    
    def __init__(self):
        self.connection_string = PG_CONNECTION_STRING
    
    def _get_connection(self):
        """Retourne une connexion PostgreSQL"""
        return psycopg2.connect(self.connection_string)
    
    async def purge_company_chunks(self, company_id: str, data_type: str = None) -> int:
        """
        Supprime tous les documents/chunks pour un company_id donné.
        Si data_type est spécifié, ne supprime que les documents de ce type.
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                if data_type:
                    # Suppression spécifique par company_id ET data_type
                    cur.execute("""
                        DELETE FROM documents 
                        WHERE (metadata->>'company_id' = %s OR content LIKE %s) 
                        AND (metadata->>'data_type' = %s)
                    """, (company_id, f'%{company_id}%', data_type))
                    logger.info(f"[NATIVE_PG][PURGE] Suppression pour company_id={company_id}, data_type={data_type}")
                else:
                    # Suppression par company_id seulement
                    cur.execute("""
                        DELETE FROM documents 
                        WHERE metadata->>'company_id' = %s OR content LIKE %s
                    """, (company_id, f'%{company_id}%'))
                    logger.info(f"[NATIVE_PG][PURGE] Suppression pour company_id={company_id} (tous types)")
                
                deleted = cur.rowcount
                conn.commit()
            conn.close()
            
            logger.info(f"[NATIVE_PG][PURGE] {deleted} chunks supprimés")
            return deleted
        except Exception as e:
            logger.error(f"[NATIVE_PG][PURGE][ERREUR] {type(e).__name__}: {e}")
            return 0
    
    async def insert_company_chunks(self, company_id: str, chunks: List[Dict], data_type: str = "document") -> List[str]:
        """
        Insère une liste de chunks dans la table documents.
        Chaque chunk doit avoir: content, embedding, metadata (optionnel)
        """
        try:
            conn = self._get_connection()
            inserted_ids = []
            
            with conn.cursor() as cur:
                for chunk in chunks:
                    # Préparer les métadonnées
                    metadata = chunk.get('metadata', {})
                    metadata['company_id'] = company_id
                    metadata['data_type'] = data_type
                    
                    # Insertion
                    # Convertir numpy array en liste pour PostgreSQL
                    embedding = chunk['embedding']
                    if hasattr(embedding, 'tolist'):
                        embedding = embedding.tolist()
                    
                    cur.execute("""
                        INSERT INTO documents (content, embedding, metadata, company_id)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """, (
                        chunk['content'],
                        embedding,
                        json.dumps(metadata),
                        company_id
                    ))
                    
                    inserted_id = cur.fetchone()[0]
                    inserted_ids.append(str(inserted_id))
                
                conn.commit()
            conn.close()
            
            logger.info(f"[NATIVE_PG][INSERT] {len(inserted_ids)} chunks insérés pour company_id={company_id}")
            return inserted_ids
        except Exception as e:
            logger.error(f"[NATIVE_PG][INSERT][ERREUR] {type(e).__name__}: {e}")
            return []
    
    async def upsert_company_chunks_by_chunk_id(self, company_id: str, chunks: List[Dict], data_type: str = "document") -> List[str]:
        """
        Upsert idempotent des chunks basés sur metadata.chunk_id pour un company_id et un data_type donnés.
        Supporte embeddings multiples (dense, sparse, multi-vector).
        """
        try:
            conn = self._get_connection()
            inserted_ids = []
            with conn.cursor() as cur:
                for chunk in chunks:
                    metadata = chunk.get('metadata', {})
                    metadata['company_id'] = company_id
                    metadata['data_type'] = data_type
                    chunk_id = metadata.get('chunk_id')
                    embedding_dense = chunk.get('embedding_dense')
                    embedding_sparse = chunk.get('embedding_sparse')
                    embedding_multi_vector = chunk.get('embedding_multi_vector')
                    # Logs détaillés sur les embeddings
                    try:
                        dense_len = len(embedding_dense) if embedding_dense is not None else 0
                    except Exception:
                        dense_len = -1
                    try:
                        sparse_len = len(embedding_sparse) if embedding_sparse is not None else 0
                    except Exception:
                        sparse_len = -1
                    try:
                        multi_count = len(embedding_multi_vector) if embedding_multi_vector is not None else 0
                        multi_dim = len(embedding_multi_vector[0]) if (embedding_multi_vector and len(embedding_multi_vector) > 0) else 0
                    except Exception:
                        multi_count, multi_dim = -1, -1
                    logger.debug(
                        f"[NATIVE_PG][UPSERT][PREP] chunk_id={chunk_id} | key={metadata.get('key')} | idx={metadata.get('chunk_index')} | "
                        f"dense_len={dense_len} | sparse_len={sparse_len} | multi_count={multi_count} x {multi_dim} | "
                        f"content_len={len(chunk.get('content', ''))}"
                    )
                    if hasattr(embedding_dense, 'tolist'):
                        embedding_dense = embedding_dense.tolist()
                    # Log des types Python réellement envoyés
                    logger.debug(
                        f"[NATIVE_PG][UPSERT][TYPES] chunk_id={chunk_id} | types: "
                        f"dense={type(embedding_dense)} | sparse(jsonb)={type(embedding_sparse)} | multi(vector[])={type(embedding_multi_vector)}"
                    )
                    # Construction du littéral SQL pour vector[] si présent
                    mv_pg = None
                    if embedding_multi_vector and isinstance(embedding_multi_vector, list) and len(embedding_multi_vector) > 0:
                        try:
                            def _vec_literal(vec):
                                return '[' + ','.join(f"{float(x):.6f}" for x in vec) + ']'
                            vector_literals = [f"'{_vec_literal(v)}'::vector" for v in embedding_multi_vector]
                            array_sql = 'ARRAY[' + ','.join(vector_literals) + ']'
                            mv_pg = AsIs(array_sql)
                            logger.debug(f"[NATIVE_PG][UPSERT][MULTI] vector[] construit: {len(vector_literals)} sous-vecteurs")
                        except Exception as e:
                            logger.exception(f"[NATIVE_PG][UPSERT][MULTI][BUILD_ERR] {e}")
                            mv_pg = None
                    if not chunk_id:
                        cur.execute("""
                            INSERT INTO documents (content, embedding_dense, embedding_sparse, embedding_multi_vector, metadata, company_id, chunk_id, chunk_index, data_type)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, (
                            chunk['content'],
                            embedding_dense,
                            Json(embedding_sparse) if embedding_sparse is not None else None,
                            mv_pg,
                            json.dumps(metadata),
                            company_id,
                            metadata.get('chunk_id'),
                            metadata.get('chunk_index'),
                            data_type
                        ))
                        inserted_id = cur.fetchone()[0]
                        inserted_ids.append(str(inserted_id))
                        continue
                    cur.execute(
                        """
                        DELETE FROM documents
                        WHERE company_id = %s
                        AND data_type = %s
                        AND chunk_id = %s
                        """,
                        (company_id, data_type, str(chunk_id))
                    )
                    cur.execute(
                        """
                        INSERT INTO documents (content, embedding_dense, embedding_sparse, embedding_multi_vector, metadata, company_id, chunk_id, chunk_index, data_type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            chunk['content'],
                            embedding_dense,
                            Json(embedding_sparse) if embedding_sparse is not None else None,
                            mv_pg,
                            json.dumps(metadata),
                            company_id,
                            metadata.get('chunk_id'),
                            metadata.get('chunk_index'),
                            data_type
                        )
                    )
                    inserted_id = cur.fetchone()[0]
                    inserted_ids.append(str(inserted_id))
                conn.commit()
            conn.close()
            logger.info(f"[NATIVE_PG][UPSERT] {len(inserted_ids)} chunks upsert multi-embedding pour company_id={company_id}")
            return inserted_ids
        except Exception as e:
            logger.error(f"[NATIVE_PG][UPSERT][ERREUR] {type(e).__name__}: {e}")
            return []
    
    async def search_documents(self, company_id: str, query_embedding: List[float], 
                             data_type: str = "document", limit: int = 5, 
                             score_threshold: float = 0.5, mode: str = "dense", 
                             query_sparse: Optional[Dict] = None, query_multi_vector: Optional[List[List[float]]] = None,
                             hybrid_weight: float = 0.5) -> List[Dict]:
        """
        Recherche avancée dans les documents d'une entreprise.
        mode: "dense" | "sparse" | "multi_vector" | "hybrid"
        - dense: recherche sur embedding_dense
        - sparse: recherche sur embedding_sparse (BM25/SPLADE)
        - multi_vector: recherche sur embedding_multi_vector (ColBERT-like)
        - hybrid: combinaison pondérée dense+sparse
        """
        try:
            conn = self._get_connection()
            results = []
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if mode == "dense":
                    cur.execute("""
                        SELECT 
                            id, content, metadata, embedding_dense,
                            (embedding_dense <=> %s::vector) as distance,
                            (1 - (embedding_dense <=> %s::vector)) as similarity_score
                        FROM documents 
                        WHERE company_id = %s 
                        AND data_type = %s
                        AND (embedding_dense <=> %s::vector) < %s
                        ORDER BY embedding_dense <=> %s::vector
                        LIMIT %s
                    """, (
                        query_embedding, query_embedding, company_id, data_type, 
                        query_embedding, 1 - score_threshold, query_embedding, limit
                    ))
                    results = cur.fetchall()
                elif mode == "sparse":
                    # Recherche sparse: tri par score BM25/SPLADE stocké dans embedding_sparse
                    # On suppose embedding_sparse est un dict {token: weight}
                    # TODO: Remplacer par une vraie logique de matching sparse (ex: via une extension SQL ou Python)
                    raise NotImplementedError("Recherche sparse non implémentée (à brancher sur extension ou code Python)")
                elif mode == "multi_vector":
                    # Recherche multi-vector: matching ColBERT-like (requête = liste de sous-vecteurs)
                    # TODO: Implémenter la logique de matching multi-vector
                    raise NotImplementedError("Recherche multi-vector non implémentée")
                elif mode == "hybrid":
                    # Recherche hybride: combiner dense et sparse (pondération)
                    # 1. Recherche dense
                    cur.execute("""
                        SELECT 
                            id, content, metadata, embedding_dense,
                            (embedding_dense <=> %s::vector) as distance,
                            (1 - (embedding_dense <=> %s::vector)) as similarity_score
                        FROM documents 
                        WHERE company_id = %s 
                        AND data_type = %s
                        AND (embedding_dense <=> %s::vector) < %s
                        ORDER BY embedding_dense <=> %s::vector
                        LIMIT %s
                    """, (
                        query_embedding, query_embedding, company_id, data_type, 
                        query_embedding, 1 - score_threshold, query_embedding, limit
                    ))
                    dense_results = cur.fetchall()
                    # 2. Recherche sparse (stub)
                    sparse_results = []
                    # TODO: Ajouter code sparse réel
                    # 3. Fusion pondérée (dense * w + sparse * (1-w))
                    # Pour l'instant, on retourne juste les résultats denses
                    results = dense_results
                else:
                    raise ValueError(f"Mode de recherche inconnu: {mode}")
            conn.close()
            # Formatage résultat
            formatted_results = []
            for row in results:
                formatted_results.append({
                    'id': str(row['id']),
                    'content': row['content'],
                    'metadata': row['metadata'],
                    'distance': float(row.get('distance', 0)),
                    'similarity_score': float(row.get('similarity_score', 0))
                })
            logger.info(f"[NATIVE_PG][SEARCH][{mode}] {len(formatted_results)} documents trouvés pour company_id={company_id}")
            return formatted_results
        except Exception as e:
            logger.error(f"[NATIVE_PG][SEARCH][{mode}][ERREUR] {type(e).__name__}: {e}")
            return []
    
    async def count_documents(self, company_id: str, data_type: str = None) -> int:
        """
        Compte le nombre de documents pour une entreprise.
        """
        try:
            conn = self._get_connection()
            
            with conn.cursor() as cur:
                if data_type:
                    cur.execute("""
                        SELECT COUNT(*) FROM documents 
                        WHERE metadata->>'company_id' = %s 
                        AND metadata->>'data_type' = %s
                    """, (company_id, data_type))
                else:
                    cur.execute("""
                        SELECT COUNT(*) FROM documents 
                        WHERE metadata->>'company_id' = %s
                    """, (company_id,))
                
                count = cur.fetchone()[0]
            conn.close()
            
            return count
        except Exception as e:
            logger.error(f"[NATIVE_PG][COUNT][ERREUR] {type(e).__name__}: {e}")
            return 0

# Instance globale
native_client = NativePGVectorClient()

# Fonctions de compatibilité avec l'ancien code
async def purge_company_chunks(company_id: str, collection_name: str = None, 
                             embedding_function=None, data_type: str = None) -> int:
    """Fonction de compatibilité avec l'ancien code"""
    return await native_client.purge_company_chunks(company_id, data_type)

async def insert_company_chunks(company_id: str, chunks: List[Dict], 
                               collection_name: str = None, embedding_function=None) -> List[str]:
    """Fonction de compatibilité avec l'ancien code"""
    return await native_client.insert_company_chunks(company_id, chunks, "document")

async def search_company_documents(company_id: str, query_embedding: List[float], 
                                 limit: int = 5, score_threshold: float = 0.5) -> List[Dict]:
    """Recherche dans les documents d'une entreprise"""
    return await native_client.search_documents(company_id, query_embedding, "document", limit, score_threshold)

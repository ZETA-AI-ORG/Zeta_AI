import psycopg2
from psycopg2 import sql
import os

from .pgvector_config import PG_CONNECTION_STRING

# --- Utilitaire pour créer dynamiquement une table PGVector si elle n'existe pas ---
def ensure_pgvector_table_exists(collection_name: str, embedding_dim: int = 768, multi_vector_dim: int = 768):
    """
    Crée dynamiquement une table PGVector pour la collection si elle n'existe pas (scalable, multi-embeddings).
    """
    conn = psycopg2.connect(PG_CONNECTION_STRING.replace('postgresql+psycopg2://', 'postgresql://'))
    try:
        with conn.cursor() as cur:
            # Nouvelle structure multi-embeddings
            create_table_query = sql.SQL("""
                CREATE TABLE IF NOT EXISTS {table} (
                    id SERIAL PRIMARY KEY,
                    content TEXT,
                    embedding_dense VECTOR(%s),
                    embedding_sparse JSONB,
                    embedding_multi_vector JSONB,
                    metadata JSONB,
                    company_id TEXT,
                    chunk_id TEXT,
                    chunk_index INT,
                    data_type TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(company_id, chunk_id)
                )
            """).format(table=sql.Identifier(collection_name))
            cur.execute(create_table_query, (embedding_dim,))

            # Index HNSW sur embedding_dense
            cur.execute(sql.SQL("""
                CREATE INDEX IF NOT EXISTS {index_name}_hnsw
                ON {table} USING hnsw (embedding_dense vector_cosine_ops);
            """).format(
                index_name=sql.Identifier(f"idx_{collection_name}_dense"),
                table=sql.Identifier(collection_name)
            ))
            # Index GIN sur metadata
            cur.execute(sql.SQL("""
                CREATE INDEX IF NOT EXISTS {index_name}_gin
                ON {table} USING GIN (metadata);
            """).format(
                index_name=sql.Identifier(f"idx_{collection_name}_metadata"),
                table=sql.Identifier(collection_name)
            ))
            # Index sur company_id et data_type
            cur.execute(sql.SQL("""
                CREATE INDEX IF NOT EXISTS {index_name}_company
                ON {table} (company_id);
            """).format(
                index_name=sql.Identifier(f"idx_{collection_name}_company"),
                table=sql.Identifier(collection_name)
            ))
            cur.execute(sql.SQL("""
                CREATE INDEX IF NOT EXISTS {index_name}_datatype
                ON {table} (data_type);
            """).format(
                index_name=sql.Identifier(f"idx_{collection_name}_datatype"),
                table=sql.Identifier(collection_name)
            ))
        conn.commit()
    finally:
        conn.close()

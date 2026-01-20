#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migration vers embeddings 384 dimensions
Modèle: all-MiniLM-L6-v2 (384 dim) vs all-mpnet-base-v2 (768 dim)
Gain: 2x vitesse + 50% mémoire
"""

import os
import sys
import time
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
import psycopg2
from psycopg2.extras import execute_batch
from tqdm import tqdm

# Configuration
SUPABASE_URL = "postgresql://postgres.ilbihprkxcgsigvueeme:Bac2018mado%40@aws-0-eu-west-3.pooler.supabase.com:5432/postgres"
BATCH_SIZE = 100  # Traiter 100 documents à la fois
MODEL_NAME = "all-MiniLM-L6-v2"  # 384 dimensions

def main():
    print("=" * 80)
    print("🚀 MIGRATION EMBEDDINGS 384 DIMENSIONS")
    print("=" * 80)
    
    # 1. Charger modèle
    print(f"\n📥 Chargement modèle {MODEL_NAME}...")
    start = time.time()
    model = SentenceTransformer(MODEL_NAME)
    print(f"✅ Modèle chargé en {time.time() - start:.2f}s")
    print(f"   Dimensions: {model.get_sentence_embedding_dimension()}")
    
    # 2. Connexion Supabase
    print("\n🔌 Connexion à Supabase...")
    conn = psycopg2.connect(SUPABASE_URL)
    cursor = conn.cursor()
    print("✅ Connecté")
    
    # 3. Compter documents à migrer
    cursor.execute("""
        SELECT COUNT(*) 
        FROM documents 
        WHERE content IS NOT NULL 
          AND (embedding_384_half IS NULL OR embedding_384 IS NULL)
    """)
    total_docs = cursor.fetchone()[0]
    print(f"\n📊 Documents à migrer: {total_docs:,}")
    
    if total_docs == 0:
        print("✅ Tous les documents sont déjà migrés!")
        return
    
    # 4. Migrer par batch
    print(f"\n🔄 Migration par batch de {BATCH_SIZE}...")
    migrated = 0
    errors = 0
    
    with tqdm(total=total_docs, desc="Migration") as pbar:
        while migrated < total_docs:
            # Récupérer batch
            cursor.execute("""
                SELECT id, content
                FROM documents
                WHERE content IS NOT NULL
                  AND (embedding_384_half IS NULL OR embedding_384 IS NULL)
                LIMIT %s
            """, (BATCH_SIZE,))
            
            batch = cursor.fetchall()
            if not batch:
                break
            
            # Générer embeddings
            doc_ids = [row[0] for row in batch]
            contents = [row[1] for row in batch]
            
            try:
                embeddings = model.encode(contents, show_progress_bar=False)
                
                # Convertir en float16 pour économie mémoire
                embeddings_half = embeddings.astype(np.float16)
                
                # Mettre à jour DB
                update_data = [
                    (
                        embeddings[i].tolist(),  # float32
                        embeddings_half[i].tolist(),  # float16
                        doc_ids[i]
                    )
                    for i in range(len(doc_ids))
                ]
                
                execute_batch(
                    cursor,
                    """
                    UPDATE documents
                    SET 
                        embedding_384 = %s::vector(384),
                        embedding_384_half = %s::halfvec(384)
                    WHERE id = %s
                    """,
                    update_data,
                    page_size=BATCH_SIZE
                )
                
                conn.commit()
                migrated += len(batch)
                pbar.update(len(batch))
                
            except Exception as e:
                print(f"\n❌ Erreur batch: {e}")
                errors += len(batch)
                conn.rollback()
                continue
    
    # 5. Statistiques finales
    print("\n" + "=" * 80)
    print("📊 RÉSULTATS MIGRATION")
    print("=" * 80)
    print(f"✅ Migrés: {migrated:,}")
    print(f"❌ Erreurs: {errors:,}")
    print(f"📈 Taux succès: {100 * migrated / (migrated + errors):.1f}%")
    
    # 6. Vérifier distribution
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(embedding_384) as with_384_float32,
            COUNT(embedding_384_half) as with_384_float16,
            ROUND(100.0 * COUNT(embedding_384_half) / COUNT(*), 2) as pct_migrated
        FROM documents
    """)
    stats = cursor.fetchone()
    print(f"\n📊 État base de données:")
    print(f"   Total documents: {stats[0]:,}")
    print(f"   Avec 384 float32: {stats[1]:,}")
    print(f"   Avec 384 float16: {stats[2]:,}")
    print(f"   % migré: {stats[3]}%")
    
    # 7. Comparer tailles
    cursor.execute("""
        SELECT 
            pg_size_pretty(pg_column_size(embedding)) as size_768_float32,
            pg_size_pretty(pg_column_size(embedding_half)) as size_768_float16,
            pg_size_pretty(pg_column_size(embedding_384)) as size_384_float32,
            pg_size_pretty(pg_column_size(embedding_384_half)) as size_384_float16
        FROM documents
        WHERE embedding IS NOT NULL
          AND embedding_384_half IS NOT NULL
        LIMIT 1
    """)
    sizes = cursor.fetchone()
    if sizes:
        print(f"\n💾 Tailles par document:")
        print(f"   768 float32: {sizes[0]}")
        print(f"   768 float16: {sizes[1]}")
        print(f"   384 float32: {sizes[2]}")
        print(f"   384 float16: {sizes[3]} ⭐ (4x plus petit!)")
    
    cursor.close()
    conn.close()
    
    print("\n✅ Migration terminée!")
    print("\n💡 Prochaines étapes:")
    print("   1. Créer index HNSW: database/supabase_384_dimensions_migration.sql")
    print("   2. Tester performance avec match_documents_384()")
    print("   3. Comparer qualité résultats 768 vs 384")
    print("   4. Si OK, supprimer anciennes colonnes 768 dim")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Migration interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

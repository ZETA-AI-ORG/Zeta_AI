"""
🔄 MIGRATION: Ajouter métadonnées automatiques aux documents existants
========================================================================

Ce script:
1. Récupère tous les documents de Supabase
2. Extrait automatiquement les métadonnées (catégories, attributs)
3. Met à jour les documents avec les métadonnées

✅ Scalable: Traite tous les documents de toutes les entreprises
✅ Idempotent: Peut être relancé sans problème
✅ Progressif: Affiche la progression
"""

import asyncio
from supabase import create_client, Client
from core.smart_metadata_extractor import auto_detect_metadata
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ SUPABASE_URL et SUPABASE_SERVICE_KEY requis dans .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


async def migrate_documents(batch_size: int = 100, dry_run: bool = False):
    """
    Migre tous les documents pour ajouter les métadonnées
    
    Args:
        batch_size: Nombre de documents à traiter par batch
        dry_run: Si True, affiche les métadonnées sans les sauvegarder
    """
    print("=" * 80)
    print("🔄 MIGRATION: Ajout métadonnées automatiques")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (test)' if dry_run else 'PRODUCTION'}")
    print(f"Batch size: {batch_size}")
    print()
    
    # Compter le total de documents
    try:
        count_response = supabase.table('documents').select('id', count='exact').execute()
        total_docs = count_response.count
        print(f"📊 Total documents: {total_docs}")
    except Exception as e:
        print(f"⚠️ Impossible de compter les documents: {e}")
        total_docs = "?"
    
    print()
    
    # Traiter par batch
    offset = 0
    processed = 0
    updated = 0
    errors = 0
    
    while True:
        print(f"\n{'='*80}")
        print(f"📦 BATCH {offset // batch_size + 1} (offset: {offset})")
        print(f"{'='*80}")
        
        # Récupérer un batch de documents
        try:
            response = supabase.table('documents')\
                .select('id, company_id, content, metadata')\
                .range(offset, offset + batch_size - 1)\
                .execute()
            
            docs = response.data
            
            if not docs:
                print("✅ Tous les documents traités!")
                break
            
            print(f"📄 {len(docs)} documents récupérés")
            
        except Exception as e:
            print(f"❌ Erreur récupération batch: {e}")
            break
        
        # Traiter chaque document
        for i, doc in enumerate(docs, 1):
            doc_id = doc['id']
            company_id = doc['company_id']
            content = doc.get('content', '')
            existing_metadata = doc.get('metadata', {})
            
            try:
                # Extraire les métadonnées
                new_metadata = auto_detect_metadata(content, company_id)
                
                # Fusionner avec métadonnées existantes (garder les anciennes si présentes)
                merged_metadata = {**existing_metadata, **new_metadata}
                
                # Afficher les métadonnées extraites
                print(f"\n  [{i}/{len(docs)}] Doc {doc_id[:8]}...")
                print(f"    Type: {new_metadata.get('doc_type', 'N/A')}")
                print(f"    Catégories: {', '.join(new_metadata.get('categories', [])) or 'Aucune'}")
                print(f"    Sous-catégories: {', '.join(new_metadata.get('subcategories', [])) or 'Aucune'}")
                print(f"    Attributs: {list(new_metadata.get('attributes', {}).keys()) or 'Aucun'}")
                
                # Sauvegarder (sauf en dry run)
                if not dry_run:
                    supabase.table('documents')\
                        .update({'metadata': merged_metadata})\
                        .eq('id', doc_id)\
                        .execute()
                    print(f"    ✅ Mis à jour")
                    updated += 1
                else:
                    print(f"    🔍 DRY RUN - Pas de sauvegarde")
                
                processed += 1
                
            except Exception as e:
                print(f"    ❌ Erreur: {e}")
                errors += 1
        
        # Passer au batch suivant
        offset += batch_size
        
        # Afficher progression
        if total_docs != "?":
            progress = (processed / total_docs) * 100
            print(f"\n📊 Progression: {processed}/{total_docs} ({progress:.1f}%)")
    
    # Résumé final
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ MIGRATION")
    print("=" * 80)
    print(f"✅ Documents traités: {processed}")
    if not dry_run:
        print(f"✅ Documents mis à jour: {updated}")
    print(f"❌ Erreurs: {errors}")
    print("=" * 80)


async def test_single_document(doc_id: str):
    """
    Teste l'extraction de métadonnées sur un seul document
    
    Args:
        doc_id: ID du document à tester
    """
    print("=" * 80)
    print(f"🧪 TEST: Document {doc_id}")
    print("=" * 80)
    
    try:
        # Récupérer le document
        response = supabase.table('documents')\
            .select('*')\
            .eq('id', doc_id)\
            .execute()
        
        if not response.data:
            print(f"❌ Document {doc_id} introuvable")
            return
        
        doc = response.data[0]
        
        print(f"\n📄 Document:")
        print(f"  ID: {doc['id']}")
        print(f"  Company: {doc['company_id']}")
        print(f"  Contenu (100 premiers chars): {doc['content'][:100]}...")
        
        # Extraire métadonnées
        metadata = auto_detect_metadata(doc['content'], doc['company_id'])
        
        print(f"\n🎯 Métadonnées extraites:")
        print(f"  Type: {metadata.get('doc_type')}")
        print(f"  Catégories: {metadata.get('categories')}")
        print(f"  Sous-catégories: {metadata.get('subcategories')}")
        print(f"  Attributs: {metadata.get('attributes')}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")


async def main():
    """Menu principal"""
    import sys
    
    if len(sys.argv) < 2:
        print("""
Usage:
  python migrate_add_metadata.py test <doc_id>     # Tester sur 1 document
  python migrate_add_metadata.py dry-run           # Tester sans sauvegarder
  python migrate_add_metadata.py migrate           # Migrer tous les documents
  python migrate_add_metadata.py migrate --batch 50 # Migrer avec batch size 50
        """)
        return
    
    command = sys.argv[1]
    
    if command == "test":
        if len(sys.argv) < 3:
            print("❌ Usage: python migrate_add_metadata.py test <doc_id>")
            return
        doc_id = sys.argv[2]
        await test_single_document(doc_id)
    
    elif command == "dry-run":
        batch_size = 100
        if "--batch" in sys.argv:
            idx = sys.argv.index("--batch")
            batch_size = int(sys.argv[idx + 1])
        await migrate_documents(batch_size=batch_size, dry_run=True)
    
    elif command == "migrate":
        batch_size = 100
        if "--batch" in sys.argv:
            idx = sys.argv.index("--batch")
            batch_size = int(sys.argv[idx + 1])
        
        # Confirmation
        print("⚠️  ATTENTION: Vous allez modifier TOUS les documents en base!")
        confirm = input("Taper 'OUI' pour confirmer: ")
        if confirm != "OUI":
            print("❌ Migration annulée")
            return
        
        await migrate_documents(batch_size=batch_size, dry_run=False)
    
    else:
        print(f"❌ Commande inconnue: {command}")


if __name__ == "__main__":
    asyncio.run(main())

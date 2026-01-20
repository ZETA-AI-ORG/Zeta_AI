#!/usr/bin/env python3
"""
Script pour forcer la purge de l'index company_docs_XkCn8fjNWEWwqiiKMgJX7OcQrUJ3
"""

import os
import sys
import meilisearch
import time

# Configuration
MEILI_URL = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
MEILI_KEY = os.environ.get("MEILISEARCH_KEY", "")
COMPANY_ID = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"
INDEX_NAME = f"company_docs_{COMPANY_ID}"

def force_purge_now():
    """Force la purge immédiate de l'index problématique"""
    
    if not MEILI_KEY:
        print("❌ ERREUR: Variable MEILISEARCH_KEY non définie")
        return False
    
    try:
        client = meilisearch.Client(MEILI_URL, MEILI_KEY)
        
        print(f"🔥 PURGE FORCÉE DE: {INDEX_NAME}")
        print("=" * 50)
        
        # Méthode 1: Suppression complète de l'index
        print("🗑️ Suppression complète de l'index...")
        try:
            delete_result = client.delete_index(INDEX_NAME)
            print(f"✅ Index supprimé: {delete_result}")
            time.sleep(3)
        except Exception as e:
            print(f"⚠️ Suppression échouée (peut être normal): {e}")
        
        # Méthode 2: Recréation avec configuration optimisée
        print("🆕 Recréation avec configuration optimisée...")
        try:
            # Recréer l'index
            create_result = client.create_index(INDEX_NAME, {"primaryKey": "id"})
            print(f"✅ Index recréé: {create_result}")
            time.sleep(2)
            
            # Appliquer la configuration optimisée
            optimized_settings = {
                "searchableAttributes": [
                    "searchable_text", "content_fr", "product_name", "color", 
                    "tags", "zone", "method", "details", "category", "name"
                ],
                "filterableAttributes": [
                    "company_id", "type", "category", "subcategory", "color",
                    "price", "currency", "stock", "city", "zone", "zone_group",
                    "method", "policy_kind", "tags", "brand", "section"
                ],
                "sortableAttributes": ["price", "stock", "updated_at"],
                "rankingRules": ["words", "typo", "proximity", "attribute", "exactness"],
                "synonyms": {
                    "cocody": ["cocody-angré", "cocody-danga", "cocody-riviera"],
                    "yopougon": ["yop", "yopougon-niangon", "yopougon-selmer"],
                    "abidjan": ["cocody", "yopougon", "plateau", "marcory", "treichville"],
                    "casque": ["casques", "helmet", "helmets"],
                    "moto": ["motorcycle", "motorbike", "scooter"],
                    "noir": ["black", "noire"],
                    "bleu": ["blue", "bleue"],
                    "rouge": ["red"],
                    "gris": ["gray", "grey", "grise"]
                },
                "stopWords": [
                    "le", "la", "les", "de", "du", "des", "un", "une", "et", "à", "au", "aux",
                    "en", "pour", "sur", "par", "avec", "sans", "ce", "cette", "ces"
                ],
                "typoTolerance": {
                    "enabled": True,
                    "minWordSizeForTypos": {"oneTypo": 5, "twoTypos": 9},
                    "disableOnWords": ["paris", "violet", "inexistant"],
                    "disableOnAttributes": ["zone", "color"]
                }
            }
            
            client.index(INDEX_NAME).update_settings(optimized_settings)
            print("✅ Configuration optimisée appliquée")
            
        except Exception as e:
            print(f"❌ Erreur recréation: {e}")
            return False
        
        # Vérification finale
        print("📊 Vérification finale...")
        try:
            stats = client.index(INDEX_NAME).get_stats()
            doc_count = stats.numberOfDocuments if hasattr(stats, 'numberOfDocuments') else stats.get('numberOfDocuments', 0)
            print(f"📄 Documents dans l'index: {doc_count}")
            
            if doc_count == 0:
                print("✅ PURGE RÉUSSIE - Index vide et prêt")
                return True
            else:
                print(f"❌ {doc_count} documents encore présents")
                return False
                
        except Exception as e:
            print(f"❌ Erreur vérification: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        return False

if __name__ == "__main__":
    success = force_purge_now()
    
    if success:
        print("\n🎉 INDEX PURGÉ ET RECONFIGURÉ AVEC SUCCÈS")
        print("L'index est maintenant vide et prêt pour une nouvelle ingestion")
    else:
        print("\n💥 ÉCHEC DE LA PURGE")
        print("Investigation manuelle requise")
    
    sys.exit(0 if success else 1)

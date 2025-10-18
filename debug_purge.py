#!/usr/bin/env python3
"""
Script de diagnostic pour identifier pourquoi la purge ne fonctionne pas
pour l'index company_docs_XkCn8fjNWEWwqiiKMgJX7OcQrUJ3
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

def debug_purge_issue():
    """Diagnostique le problème de purge"""
    
    if not MEILI_KEY:
        print("❌ ERREUR: Variable MEILISEARCH_KEY non définie")
        return False
    
    try:
        client = meilisearch.Client(MEILI_URL, MEILI_KEY)
        
        print(f"🔍 DIAGNOSTIC DE PURGE POUR: {INDEX_NAME}")
        print("=" * 70)
        
        # 1. Vérifier l'état initial de l'index
        try:
            stats = client.index(INDEX_NAME).get_stats()
            doc_count = getattr(stats, 'numberOfDocuments', 0)
            print(f"📊 Documents avant purge: {doc_count}")
            
            if doc_count == 0:
                print("✅ Index déjà vide - pas besoin de purge")
                return True
                
        except Exception as e:
            print(f"❌ Erreur lecture stats: {e}")
            return False
        
        # 2. Tenter la purge avec delete_all_documents
        print(f"\n🗑️ TENTATIVE DE PURGE...")
        try:
            purge_task = client.index(INDEX_NAME).delete_all_documents()
            print(f"📋 Task de purge créée: {purge_task}")
            
            # Attendre que la tâche soit terminée
            task_uid = purge_task.get('taskUid') if isinstance(purge_task, dict) else None
            if task_uid:
                print(f"⏳ Attente de la tâche {task_uid}...")
                
                # Attendre jusqu'à 30 secondes
                for i in range(30):
                    try:
                        task_status = client.get_task(task_uid)
                        status = task_status.get('status', 'unknown')
                        print(f"   Statut: {status}")
                        
                        if status == 'succeeded':
                            print("✅ Purge réussie!")
                            break
                        elif status == 'failed':
                            print(f"❌ Purge échouée: {task_status.get('error', 'Erreur inconnue')}")
                            return False
                        elif status in ['enqueued', 'processing']:
                            time.sleep(1)
                        else:
                            print(f"⚠️ Statut inattendu: {status}")
                            time.sleep(1)
                    except Exception as task_e:
                        print(f"❌ Erreur vérification tâche: {task_e}")
                        break
                        
        except Exception as purge_e:
            print(f"❌ Erreur lors de la purge: {purge_e}")
            return False
        
        # 3. Vérifier l'état après purge
        print(f"\n📊 VÉRIFICATION POST-PURGE...")
        try:
            time.sleep(2)  # Attendre un peu plus
            stats_after = client.index(INDEX_NAME).get_stats()
            doc_count_after = getattr(stats_after, 'numberOfDocuments', 0)
            print(f"📊 Documents après purge: {doc_count_after}")
            
            if doc_count_after == 0:
                print("✅ PURGE RÉUSSIE - Index vide")
                return True
            else:
                print(f"❌ PURGE ÉCHOUÉE - {doc_count_after} documents restants")
                
                # Lister quelques documents restants pour diagnostic
                try:
                    remaining_docs = client.index(INDEX_NAME).search("", {"limit": 5})
                    print(f"📄 Exemples de documents restants:")
                    for doc in remaining_docs.get('hits', []):
                        print(f"   - ID: {doc.get('id', 'N/A')} | Type: {doc.get('type', 'N/A')}")
                except Exception as list_e:
                    print(f"❌ Erreur listage documents: {list_e}")
                
                return False
                
        except Exception as stats_e:
            print(f"❌ Erreur vérification post-purge: {stats_e}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        return False

def force_purge_alternative():
    """Méthode alternative de purge en supprimant et recréant l'index"""
    
    try:
        client = meilisearch.Client(MEILI_URL, MEILI_KEY)
        
        print(f"\n🔄 PURGE ALTERNATIVE - SUPPRESSION/RECRÉATION INDEX")
        print("=" * 70)
        
        # 1. Supprimer complètement l'index
        try:
            delete_task = client.delete_index(INDEX_NAME)
            print(f"🗑️ Index supprimé: {delete_task}")
            time.sleep(3)  # Attendre la suppression
        except Exception as delete_e:
            print(f"⚠️ Erreur suppression (peut être normal): {delete_e}")
        
        # 2. Recréer l'index
        try:
            create_task = client.create_index(INDEX_NAME, {"primaryKey": "id"})
            print(f"🆕 Index recréé: {create_task}")
            time.sleep(2)  # Attendre la création
        except Exception as create_e:
            print(f"❌ Erreur création: {create_e}")
            return False
        
        # 3. Vérifier que l'index est vide
        try:
            stats = client.index(INDEX_NAME).get_stats()
            doc_count = getattr(stats, 'numberOfDocuments', 0)
            print(f"📊 Documents dans le nouvel index: {doc_count}")
            
            if doc_count == 0:
                print("✅ PURGE ALTERNATIVE RÉUSSIE")
                return True
            else:
                print(f"❌ PURGE ALTERNATIVE ÉCHOUÉE - {doc_count} documents")
                return False
                
        except Exception as verify_e:
            print(f"❌ Erreur vérification: {verify_e}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur purge alternative: {e}")
        return False

if __name__ == "__main__":
    print("🚀 DIAGNOSTIC DE PURGE MEILISEARCH")
    print("=" * 70)
    
    # Test 1: Purge normale
    success = debug_purge_issue()
    
    if not success:
        print(f"\n⚠️ Purge normale échouée - Tentative méthode alternative...")
        success = force_purge_alternative()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ PURGE RÉUSSIE")
    else:
        print("❌ PURGE ÉCHOUÉE - Investigation manuelle requise")
    
    sys.exit(0 if success else 1)

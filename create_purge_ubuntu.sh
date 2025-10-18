#!/bin/bash
# 🧹 CRÉATION ET EXÉCUTION DU SCRIPT DE PURGE MEILISEARCH SUR UBUNTU

echo "🚀 CRÉATION DU SCRIPT DE PURGE MEILISEARCH"
echo "=========================================="

# Créer le script Python directement sur Ubuntu
cat > ~/CHATBOT2.0/purge_meili_complete.py << 'EOF'
#!/usr/bin/env python3
"""
🧹 PURGE COMPLÈTE MEILISEARCH
Supprime tous les index et documents pour repartir sur une base vierge
"""

import asyncio
import meilisearch
from datetime import datetime
import json

# Configuration MeiliSearch
MEILI_URL = "http://localhost:7700"
MEILI_KEY = "N80w8LbzObzK18rZk7zwiHNpJLA_YFSvYGt2XzGLP_4"

def log_purge(message, data=None):
    """Log formaté pour la purge"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[PURGE_MEILI][{timestamp}] {message}")
    if data:
        print(f"  📊 {json.dumps(data, indent=2, ensure_ascii=False)}")

class MeiliPurgeManager:
    """
    Gestionnaire de purge complète MeiliSearch
    """
    
    def __init__(self):
        self.client = meilisearch.Client(MEILI_URL, MEILI_KEY)
        
    async def get_all_indexes(self):
        """
        Récupère tous les index existants
        """
        try:
            indexes = self.client.get_indexes()
            index_list = []
            
            for index_info in indexes['results']:
                index_list.append({
                    'uid': index_info['uid'],
                    'primaryKey': index_info.get('primaryKey'),
                    'createdAt': index_info.get('createdAt'),
                    'updatedAt': index_info.get('updatedAt')
                })
            
            log_purge("📋 INDEX TROUVÉS", {
                "total_indexes": len(index_list),
                "index_names": [idx['uid'] for idx in index_list]
            })
            
            return index_list
            
        except Exception as e:
            log_purge(f"❌ ERREUR RÉCUPÉRATION INDEX: {e}")
            return []

    async def get_index_stats(self, index_uid):
        """
        Récupère les statistiques d'un index
        """
        try:
            index = self.client.index(index_uid)
            stats = index.get_stats()
            
            return {
                'uid': index_uid,
                'numberOfDocuments': stats.get('numberOfDocuments', 0),
                'isIndexing': stats.get('isIndexing', False),
                'fieldDistribution': stats.get('fieldDistribution', {})
            }
            
        except Exception as e:
            log_purge(f"⚠️ ERREUR STATS INDEX {index_uid}: {e}")
            return {'uid': index_uid, 'error': str(e)}

    async def delete_all_documents_from_index(self, index_uid):
        """
        Supprime tous les documents d'un index
        """
        try:
            index = self.client.index(index_uid)
            
            # Récupérer le nombre de documents avant suppression
            stats = await self.get_index_stats(index_uid)
            doc_count = stats.get('numberOfDocuments', 0)
            
            if doc_count > 0:
                log_purge(f"🗑️ SUPPRESSION DOCUMENTS INDEX: {index_uid}", {
                    "documents_count": doc_count
                })
                
                # Supprimer tous les documents
                task = index.delete_all_documents()
                
                # Attendre la fin de la tâche
                self.client.wait_for_task(task['taskUid'])
                
                log_purge(f"✅ DOCUMENTS SUPPRIMÉS: {index_uid}")
                return True
            else:
                log_purge(f"ℹ️ INDEX DÉJÀ VIDE: {index_uid}")
                return True
                
        except Exception as e:
            log_purge(f"❌ ERREUR SUPPRESSION DOCUMENTS {index_uid}: {e}")
            return False

    async def delete_index(self, index_uid):
        """
        Supprime complètement un index
        """
        try:
            log_purge(f"🗑️ SUPPRESSION INDEX: {index_uid}")
            
            task = self.client.delete_index(index_uid)
            
            # Attendre la fin de la tâche
            self.client.wait_for_task(task['taskUid'])
            
            log_purge(f"✅ INDEX SUPPRIMÉ: {index_uid}")
            return True
            
        except Exception as e:
            log_purge(f"❌ ERREUR SUPPRESSION INDEX {index_uid}: {e}")
            return False

    async def purge_all_data(self, delete_indexes=True):
        """
        Purge complète de toutes les données
        """
        log_purge("🚀 DÉMARRAGE PURGE COMPLÈTE MEILISEARCH")
        
        # Étape 1: Récupérer tous les index
        indexes = await self.get_all_indexes()
        
        if not indexes:
            log_purge("ℹ️ AUCUN INDEX TROUVÉ - MEILISEARCH DÉJÀ VIERGE")
            return True
        
        # Étape 2: Afficher les statistiques avant purge
        print(f"\n📊 STATISTIQUES AVANT PURGE:")
        total_documents = 0
        
        for index_info in indexes:
            stats = await self.get_index_stats(index_info['uid'])
            doc_count = stats.get('numberOfDocuments', 0)
            total_documents += doc_count
            
            print(f"  📁 {index_info['uid']}: {doc_count} documents")
        
        log_purge("📈 RÉSUMÉ AVANT PURGE", {
            "total_indexes": len(indexes),
            "total_documents": total_documents
        })
        
        # Étape 3: Supprimer selon la stratégie choisie
        success_count = 0
        
        if delete_indexes:
            # Suppression complète des index
            log_purge("🗑️ SUPPRESSION COMPLÈTE DES INDEX")
            
            for index_info in indexes:
                success = await self.delete_index(index_info['uid'])
                if success:
                    success_count += 1
        else:
            # Suppression des documents seulement
            log_purge("🗑️ SUPPRESSION DES DOCUMENTS UNIQUEMENT")
            
            for index_info in indexes:
                success = await self.delete_all_documents_from_index(index_info['uid'])
                if success:
                    success_count += 1
        
        # Étape 4: Vérification finale
        final_indexes = await self.get_all_indexes()
        
        log_purge("🎉 PURGE TERMINÉE", {
            "indexes_traités": len(indexes),
            "succès": success_count,
            "échecs": len(indexes) - success_count,
            "indexes_restants": len(final_indexes) if delete_indexes else len(indexes)
        })
        
        return success_count == len(indexes)

    async def verify_clean_state(self):
        """
        Vérifie que MeiliSearch est dans un état vierge
        """
        log_purge("🔍 VÉRIFICATION ÉTAT VIERGE")
        
        indexes = await self.get_all_indexes()
        
        if not indexes:
            log_purge("✅ MEILISEARCH COMPLÈTEMENT VIERGE")
            return True
        
        total_docs = 0
        for index_info in indexes:
            stats = await self.get_index_stats(index_info['uid'])
            doc_count = stats.get('numberOfDocuments', 0)
            total_docs += doc_count
        
        if total_docs == 0:
            log_purge("✅ MEILISEARCH VIERGE (INDEX VIDES)", {
                "indexes_vides": len(indexes)
            })
            return True
        else:
            log_purge("⚠️ MEILISEARCH NON VIERGE", {
                "indexes_avec_données": len(indexes),
                "total_documents": total_docs
            })
            return False

async def main():
    """
    Fonction principale de purge
    """
    print("🧹 PURGE COMPLÈTE MEILISEARCH")
    print("=" * 60)
    
    manager = MeiliPurgeManager()
    
    try:
        # Test de connexion
        log_purge("🔌 TEST CONNEXION MEILISEARCH")
        health = manager.client.health()
        log_purge("✅ CONNEXION OK", health)
        
        # Purge complète (suppression des index)
        success = await manager.purge_all_data(delete_indexes=True)
        
        if success:
            # Vérification finale
            await manager.verify_clean_state()
            
            print(f"\n🎉 PURGE COMPLÈTE RÉUSSIE!")
            print(f"✅ MeiliSearch est maintenant vierge")
            print(f"🚀 Prêt pour nouvelle ingestion via N8N")
        else:
            print(f"\n⚠️ PURGE PARTIELLE - Vérifier les erreurs ci-dessus")
            
    except Exception as e:
        print(f"\n💥 ERREUR CRITIQUE DURANT LA PURGE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/hyde_word_scorer.py" ~/ZETA_APP/CHATBOT2.0/core/hyde_word_scorer.py
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/ingestion_hyde_analyzer.py" ~/ZETA_APP/CHATBOT2.0/core/ingestion_hyde_analyzer.py
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/show_hyde_scores.py" ~/ZETA_APP/CHATBOT2.0/show_hyde_scores.py
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/rapport_performance_hyde.py" ~/ZETA_APP/CHATBOT2.0/rapport_performance_hyde.py

echo "🎉 PURGE TERMINÉE!"

#!/usr/bin/env python3
"""
🔍 VÉRIFICATION CONFIGURATION MEILISEARCH
Vérifie les attributs searchable, filterable, sortable pour tous les index
"""

import asyncio
import aiohttp
import json
import os
from typing import Dict, List, Any

class MeiliConfigVerifier:
    """Vérificateur de configuration MeiliSearch"""
    
    def __init__(self):
        self.url = os.getenv("MEILI_URL", "http://localhost:7700")
        self.api_key = os.getenv("MEILI_API_KEY", "")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        } if self.api_key else {"Content-Type": "application/json"}
        
    async def check_connection(self) -> bool:
        """Vérifie si MeiliSearch est accessible"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/health", headers=self.headers) as response:
                    if response.status == 200:
                        print(f"✅ MeiliSearch accessible sur {self.url}")
                        return True
                    else:
                        print(f"❌ MeiliSearch inaccessible: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Erreur connexion MeiliSearch: {e}")
            return False
    
    async def get_all_indexes(self) -> List[Dict]:
        """Récupère la liste de tous les index"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/indexes", headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        indexes = data.get('results', [])
                        print(f"📋 {len(indexes)} index trouvés")
                        return indexes
                    else:
                        print(f"❌ Erreur récupération index: {response.status}")
                        return []
        except Exception as e:
            print(f"❌ Erreur récupération index: {e}")
            return []
    
    async def get_index_settings(self, index_uid: str) -> Dict[str, Any]:
        """Récupère les paramètres d'un index"""
        settings = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                # Récupérer les attributs searchable
                async with session.get(f"{self.url}/indexes/{index_uid}/settings/searchable-attributes", headers=self.headers) as response:
                    if response.status == 200:
                        settings['searchable_attributes'] = await response.json()
                
                # Récupérer les attributs filterable
                async with session.get(f"{self.url}/indexes/{index_uid}/settings/filterable-attributes", headers=self.headers) as response:
                    if response.status == 200:
                        settings['filterable_attributes'] = await response.json()
                
                # Récupérer les attributs sortable
                async with session.get(f"{self.url}/indexes/{index_uid}/settings/sortable-attributes", headers=self.headers) as response:
                    if response.status == 200:
                        settings['sortable_attributes'] = await response.json()
                
                # Récupérer les attributs displayed
                async with session.get(f"{self.url}/indexes/{index_uid}/settings/displayed-attributes", headers=self.headers) as response:
                    if response.status == 200:
                        settings['displayed_attributes'] = await response.json()
                
                # Récupérer les stop words
                async with session.get(f"{self.url}/indexes/{index_uid}/settings/stop-words", headers=self.headers) as response:
                    if response.status == 200:
                        settings['stop_words'] = await response.json()
                
                # Récupérer les synonymes
                async with session.get(f"{self.url}/indexes/{index_uid}/settings/synonyms", headers=self.headers) as response:
                    if response.status == 200:
                        settings['synonyms'] = await response.json()
                
                # Récupérer les stats de l'index
                async with session.get(f"{self.url}/indexes/{index_uid}/stats", headers=self.headers) as response:
                    if response.status == 200:
                        settings['stats'] = await response.json()
                        
        except Exception as e:
            print(f"❌ Erreur récupération paramètres {index_uid}: {e}")
            
        return settings
    
    async def verify_company_indexes(self, company_id: str = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"):
        """Vérifie les index d'une entreprise spécifique"""
        print(f"\n🏢 VÉRIFICATION POUR COMPANY: {company_id}")
        print("=" * 80)
        
        expected_indexes = [
            f"products_{company_id}",
            f"delivery_{company_id}",
            f"localisation_{company_id}",
            f"support_paiement_{company_id}",
            f"company_docs_{company_id}"
        ]
        
        all_indexes = await self.get_all_indexes()
        existing_indexes = [idx['uid'] for idx in all_indexes]
        
        for expected_index in expected_indexes:
            if expected_index in existing_indexes:
                print(f"\n📂 INDEX: {expected_index}")
                print("-" * 60)
                
                settings = await self.get_index_settings(expected_index)
                
                if 'stats' in settings:
                    stats = settings['stats']
                    print(f"📊 Documents: {stats.get('numberOfDocuments', 0)}")
                    print(f"📏 Taille: {stats.get('databaseSize', 0)} bytes")
                    print(f"🔄 Indexing: {stats.get('isIndexing', False)}")
                
                if 'searchable_attributes' in settings:
                    searchable = settings['searchable_attributes']
                    print(f"🔍 Searchable: {searchable if searchable else '(tous par défaut)'}")
                
                if 'filterable_attributes' in settings:
                    filterable = settings['filterable_attributes']
                    print(f"🔽 Filterable: {filterable if filterable else '(aucun)'}")
                
                if 'sortable_attributes' in settings:
                    sortable = settings['sortable_attributes']
                    print(f"📈 Sortable: {sortable if sortable else '(aucun)'}")
                
                if 'displayed_attributes' in settings:
                    displayed = settings['displayed_attributes']
                    if displayed != ["*"]:
                        print(f"👁️ Displayed: {displayed}")
                
                if 'stop_words' in settings:
                    stop_words = settings['stop_words']
                    if stop_words:
                        print(f"🚫 Stop words: {len(stop_words)} mots")
                
                if 'synonyms' in settings:
                    synonyms = settings['synonyms']
                    if synonyms:
                        print(f"🔄 Synonymes: {len(synonyms)} groupes")
                        
            else:
                print(f"❌ INDEX MANQUANT: {expected_index}")
    
    async def test_search_capability(self, company_id: str = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"):
        """Test la capacité de recherche sur les index"""
        print(f"\n🧪 TEST DE RECHERCHE")
        print("=" * 50)
        
        test_queries = [
            ("couches", "products"),
            ("livraison", "delivery"), 
            ("cocody", "localisation"),
            ("paiement", "support_paiement")
        ]
        
        for query, index_type in test_queries:
            index_name = f"{index_type}_{company_id}"
            try:
                async with aiohttp.ClientSession() as session:
                    search_data = {"q": query, "limit": 1}
                    async with session.post(f"{self.url}/indexes/{index_name}/search", 
                                          headers=self.headers, 
                                          json=search_data) as response:
                        if response.status == 200:
                            result = await response.json()
                            hits = result.get('hits', [])
                            print(f"✅ {index_name}: '{query}' → {len(hits)} résultats")
                        else:
                            print(f"❌ {index_name}: '{query}' → Erreur {response.status}")
            except Exception as e:
                print(f"❌ {index_name}: '{query}' → Exception: {str(e)[:50]}")

async def main():
    """Fonction principale de vérification"""
    print("🔍 VÉRIFICATION CONFIGURATION MEILISEARCH")
    print("=" * 80)
    
    verifier = MeiliConfigVerifier()
    
    # 1. Vérifier la connexion
    if not await verifier.check_connection():
        print("❌ Impossible de se connecter à MeiliSearch")
        return
    
    # 2. Vérifier les index de l'entreprise
    await verifier.verify_company_indexes()
    
    # 3. Tester les capacités de recherche
    await verifier.test_search_capability()
    
    print("\n🏁 Vérification terminée !")

if __name__ == "__main__":
    asyncio.run(main())

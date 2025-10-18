#!/usr/bin/env python3
"""
🔧 CONFIGURATION COMPLÈTE ATTRIBUTS MEILISEARCH
Configure tous les attributs comme recherchables, filtrables et triables
"""

import requests
import os
from typing import List, Dict

class MeiliSearchConfigurator:
    def __init__(self, company_id: str = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"):
        self.company_id = company_id
        self.meili_url = os.getenv("MEILISEARCH_URL", "http://localhost:7700")
        self.meili_key = os.getenv("MEILISEARCH_MASTER_KEY", "")
        # Vérifier si la clé existe et n'est pas vide
        if not self.meili_key:
            print("❌ ERREUR: MEILISEARCH_MASTER_KEY non définie dans les variables d'environnement")
            raise ValueError("Clé MeiliSearch manquante")
            
        self.headers = {
            "Authorization": f"Bearer {self.meili_key}",
            "Content-Type": "application/json"
        }
        
        print(f"🔑 Utilisation clé MeiliSearch: {self.meili_key[:8]}...")
        print(f"🌐 URL MeiliSearch: {self.meili_url}")

    def configure_products_index(self) -> bool:
        """Configure l'index products avec tous les attributs nécessaires"""
        index_name = f"products_{self.company_id}"
        print(f"🔧 Configuration index: {index_name}")
        
        # ATTRIBUTS RECHERCHABLES - Tous les champs texte importants
        searchable_attributes = [
            "product_name",
            "searchable_text", 
            "content",
            "content_fr",
            "category",
            "subcategory",
            "color",
            "slug",
            "product_id",
            "attributes",
            "tags"
        ]
        
        # ATTRIBUTS FILTRABLES - Pour filtres et recherches structurées
        filterable_attributes = [
            "company_id",
            "type", 
            "category",
            "subcategory",
            "color",
            "price",
            "min_price",
            "max_price",
            "currency",
            "stock",
            "total_stock",
            "product_id",
            "tags",
            "facets",
            "facet_tags",
            "available_attributes"
        ]
        
        # ATTRIBUTS TRIABLES - Pour ordonner les résultats
        sortable_attributes = [
            "price",
            "min_price", 
            "max_price",
            "stock",
            "total_stock",
            "product_name",
            "category"
        ]
        
        # ATTRIBUTS AFFICHÉS - Optimiser la réponse
        displayed_attributes = [
            "id",
            "product_id",
            "product_name",
            "category",
            "subcategory", 
            "color",
            "price",
            "currency",
            "stock",
            "content_fr",
            "searchable_text",
            "content"
        ]
        
        try:
            # 1. Configurer attributs recherchables
            response = requests.put(
                f"{self.meili_url}/indexes/{index_name}/settings/searchable-attributes",
                headers=self.headers,
                json=searchable_attributes
            )
            if response.status_code in [200, 202]:
                print("✅ Attributs recherchables configurés")
            else:
                print(f"❌ Erreur attributs recherchables: {response.status_code}")
                print(f"📝 Réponse: {response.text}")
                print(f"🔍 Headers envoyés: {self.headers}")
                return False
            
            # 2. Configurer attributs filtrables  
            response = requests.put(
                f"{self.meili_url}/indexes/{index_name}/settings/filterable-attributes",
                headers=self.headers,
                json=filterable_attributes
            )
            if response.status_code in [200, 202]:
                print("✅ Attributs filtrables configurés")
            else:
                print(f"❌ Erreur attributs filtrables: {response.status_code}")
                return False
            
            # 3. Configurer attributs triables
            response = requests.put(
                f"{self.meili_url}/indexes/{index_name}/settings/sortable-attributes", 
                headers=self.headers,
                json=sortable_attributes
            )
            if response.status_code in [200, 202]:
                print("✅ Attributs triables configurés")
            else:
                print(f"❌ Erreur attributs triables: {response.status_code}")
                return False
            
            # 4. Configurer attributs affichés
            response = requests.put(
                f"{self.meili_url}/indexes/{index_name}/settings/displayed-attributes",
                headers=self.headers, 
                json=displayed_attributes
            )
            if response.status_code in [200, 202]:
                print("✅ Attributs affichés configurés")
            else:
                print(f"❌ Erreur attributs affichés: {response.status_code}")
                return False
            
            # 5. Configurer synonymes pour améliorer recherche
            synonyms = {
                "casque": ["helmet", "protection", "équipement"],
                "rouge": ["red", "rougeâtre"],
                "bleu": ["blue", "bleue"],
                "noir": ["black", "noire"],
                "gris": ["gray", "grey", "grise"],
                "moto": ["motocyclette", "scooter", "véhicule"],
                "prix": ["coût", "tarif", "montant"],
                "livraison": ["delivery", "transport", "expédition"]
            }
            
            response = requests.put(
                f"{self.meili_url}/indexes/{index_name}/settings/synonyms",
                headers=self.headers,
                json=synonyms
            )
            if response.status_code in [200, 202]:
                print("✅ Synonymes configurés")
            
            print("🎉 Configuration complète terminée!")
            return True
            
        except Exception as e:
            print(f"❌ Erreur configuration: {e}")
            return False

    def test_search(self) -> bool:
        """Test la recherche après configuration"""
        index_name = f"products_{self.company_id}"
        print(f"\n🧪 Test recherche sur: {index_name}")
        
        test_queries = [
            "casque rouge",
            "moto rouge", 
            "6500",
            "CASQUES MOTO",
            "rouge"
        ]
        
        for query in test_queries:
            try:
                response = requests.post(
                    f"{self.meili_url}/indexes/{index_name}/search",
                    headers=self.headers,
                    json={"query": query, "limit": 3}
                )
                
                if response.status_code == 200:
                    results = response.json()
                    hits = len(results.get("hits", []))
                    print(f"🔍 '{query}': {hits} résultats")
                    
                    if hits > 0:
                        # Afficher le premier résultat
                        first_hit = results["hits"][0]
                        print(f"   → {first_hit.get('product_name', 'N/A')} - {first_hit.get('color', 'N/A')}")
                else:
                    print(f"❌ Erreur recherche '{query}': {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Erreur test '{query}': {e}")
        
        return True

    def run_complete_configuration(self):
        """Exécute la configuration complète"""
        print("🚀 CONFIGURATION COMPLÈTE MEILISEARCH")
        print("=" * 50)
        
        success = self.configure_products_index()
        if success:
            print("\n⏳ Attente indexation...")
            import time
            time.sleep(3)
            
            self.test_search()
            print("\n✅ Configuration terminée avec succès!")
        else:
            print("\n❌ Échec de la configuration")

if __name__ == "__main__":
    configurator = MeiliSearchConfigurator()
    configurator.run_complete_configuration()

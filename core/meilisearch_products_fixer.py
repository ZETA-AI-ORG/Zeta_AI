#!/usr/bin/env python3
"""
🔧 CORRECTEUR INDEX MEILISEARCH PRODUCTS
Diagnostique et corrige les problèmes de l'index products qui ne retourne pas de résultats
"""

import asyncio
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime
import os

class MeiliSearchProductsFixer:
    """
    🔧 Correcteur spécialisé pour l'index MeiliSearch products
    """
    
    def __init__(self, company_id: str = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"):
        self.company_id = company_id
        self.meili_url = os.getenv("MEILISEARCH_URL", "http://localhost:7700")
        self.meili_key = os.getenv("MEILISEARCH_MASTER_KEY", "")
        self.index_name = f"products_{company_id}"
        
        self.headers = {
            "Authorization": f"Bearer {self.meili_key}",
            "Content-Type": "application/json"
        }

    def diagnose_products_index(self) -> Dict:
        """
        🔍 Diagnostique complet de l'index products
        """
        print(f"🔍 DIAGNOSTIC INDEX PRODUCTS: {self.index_name}")
        print("=" * 60)
        
        diagnosis = {
            "index_exists": False,
            "document_count": 0,
            "searchable_attributes": [],
            "filterable_attributes": [],
            "sample_documents": [],
            "search_test_results": {},
            "issues_found": [],
            "recommendations": []
        }
        
        try:
            # 1. Vérifier existence de l'index
            response = requests.get(f"{self.meili_url}/indexes/{self.index_name}", headers=self.headers)
            if response.status_code == 200:
                diagnosis["index_exists"] = True
                index_info = response.json()
                print(f"✅ Index existe: {index_info.get('uid')}")
            else:
                diagnosis["issues_found"].append("Index n'existe pas")
                print(f"❌ Index n'existe pas (Status: {response.status_code})")
                return diagnosis
            
            # 2. Compter les documents
            response = requests.get(f"{self.meili_url}/indexes/{self.index_name}/documents", headers=self.headers)
            if response.status_code == 200:
                documents = response.json()
                diagnosis["document_count"] = len(documents.get("results", []))
                diagnosis["sample_documents"] = documents.get("results", [])[:3]
                print(f"📊 Nombre de documents: {diagnosis['document_count']}")
                
                if diagnosis["document_count"] == 0:
                    diagnosis["issues_found"].append("Aucun document dans l'index")
                    diagnosis["recommendations"].append("Réindexer les produits")
            
            # 3. Vérifier configuration de recherche
            response = requests.get(f"{self.meili_url}/indexes/{self.index_name}/settings", headers=self.headers)
            if response.status_code == 200:
                settings = response.json()
                diagnosis["searchable_attributes"] = settings.get("searchableAttributes", [])
                diagnosis["filterable_attributes"] = settings.get("filterableAttributes", [])
                
                print(f"🔍 Attributs recherchables: {diagnosis['searchable_attributes']}")
                print(f"🏷️ Attributs filtrables: {diagnosis['filterable_attributes']}")
                
                if not diagnosis["searchable_attributes"]:
                    diagnosis["issues_found"].append("Aucun attribut recherchable configuré")
                    diagnosis["recommendations"].append("Configurer les attributs recherchables")
            
            # 4. Tests de recherche
            test_queries = ["casque", "rouge", "moto", "6500"]
            for query in test_queries:
                search_response = requests.post(
                    f"{self.meili_url}/indexes/{self.index_name}/search",
                    headers=self.headers,
                    json={"query": query, "limit": 5}
                )
                
                if search_response.status_code == 200:
                    results = search_response.json()
                    diagnosis["search_test_results"][query] = {
                        "hits": len(results.get("hits", [])),
                        "processing_time": results.get("processingTimeMs", 0)
                    }
                    print(f"🔍 Test '{query}': {len(results.get('hits', []))} résultats")
                    
                    if len(results.get("hits", [])) == 0:
                        diagnosis["issues_found"].append(f"Recherche '{query}' ne retourne aucun résultat")
            
            # 5. Analyser les problèmes
            if diagnosis["document_count"] > 0 and all(
                result["hits"] == 0 for result in diagnosis["search_test_results"].values()
            ):
                diagnosis["issues_found"].append("Documents présents mais recherche ne fonctionne pas")
                diagnosis["recommendations"].extend([
                    "Vérifier le format des documents",
                    "Reconfigurer les attributs recherchables",
                    "Réindexer avec le bon format"
                ])
            
        except Exception as e:
            diagnosis["issues_found"].append(f"Erreur diagnostic: {str(e)}")
            print(f"❌ Erreur diagnostic: {e}")
        
        return diagnosis

    def fix_products_index(self) -> bool:
        """
        🔧 Corrige automatiquement l'index products
        """
        print(f"🔧 CORRECTION INDEX PRODUCTS: {self.index_name}")
        print("=" * 60)
        
        try:
            # 1. Configurer les attributs recherchables optimaux
            searchable_config = {
                "searchableAttributes": [
                    "product_name",
                    "searchable_text",
                    "content",
                    "category",
                    "subcategory",
                    "attributes",
                    "color",
                    "description"
                ]
            }
            
            response = requests.patch(
                f"{self.meili_url}/indexes/{self.index_name}/settings/searchable-attributes",
                headers=self.headers,
                json=searchable_config["searchableAttributes"]
            )
            
            if response.status_code in [200, 202]:
                print("✅ Attributs recherchables configurés")
            else:
                print(f"❌ Erreur configuration attributs: {response.status_code}")
                return False
            
            # 2. Configurer les attributs filtrables
            filterable_config = [
                "company_id",
                "type",
                "category",
                "subcategory",
                "color",
                "price_min",
                "price_max"
            ]
            
            response = requests.patch(
                f"{self.meili_url}/indexes/{self.index_name}/settings/filterable-attributes",
                headers=self.headers,
                json=filterable_config
            )
            
            if response.status_code in [200, 202]:
                print("✅ Attributs filtrables configurés")
            else:
                print(f"❌ Erreur configuration filtres: {response.status_code}")
            
            # 3. Configurer les synonymes pour améliorer la recherche
            synonyms_config = {
                "casque": ["helmet", "protection", "équipement"],
                "rouge": ["red", "rougeâtre"],
                "moto": ["motocyclette", "scooter", "véhicule"],
                "livraison": ["delivery", "transport", "expédition"],
                "paiement": ["payment", "règlement", "facturation"]
            }
            
            response = requests.patch(
                f"{self.meili_url}/indexes/{self.index_name}/settings/synonyms",
                headers=self.headers,
                json=synonyms_config
            )
            
            if response.status_code in [200, 202]:
                print("✅ Synonymes configurés")
            
            # 4. Attendre que les tâches se terminent
            print("⏳ Attente de la fin des tâches de configuration...")
            asyncio.sleep(2)
            
            print("🎉 Correction terminée avec succès!")
            return True
            
        except Exception as e:
            print(f"❌ Erreur correction: {e}")
            return False

    def create_test_product(self) -> bool:
        """
        🧪 Crée un produit de test pour vérifier le fonctionnement
        """
        print("🧪 CRÉATION PRODUIT DE TEST")
        print("-" * 30)
        
        test_product = {
            "id": "test_casque_rouge_001",
            "document_id": "test_casque_rouge_001",
            "company_id": self.company_id,
            "type": "product",
            "product_id": "TEST-CASQUE-001",
            "product_name": "CASQUE MOTO ROUGE TEST",
            "slug": "casque-moto-rouge-test",
            "category": "Auto & Moto",
            "subcategory": "Casques & Équipement Moto",
            "attributes": "Couleur: rouge, Taille: universelle",
            "color": "rouge",
            "price_min": 6500,
            "price_max": 6500,
            "currency": "FCFA",
            "stock": 10,
            "description": "Casque de moto rouge haute qualité pour protection optimale",
            "searchable_text": "casque moto rouge protection équipement sécurité 6500 FCFA stock disponible Auto Moto",
            "content": "=== PRODUIT TEST ===\nID: test_casque_rouge_001\nNom: CASQUE MOTO ROUGE TEST\nPrix: 6500 FCFA\nStock: 10 unités\nCouleur: rouge\nCatégorie: Auto & Moto\nDescription: Casque de moto rouge haute qualité"
        }
        
        try:
            response = requests.post(
                f"{self.meili_url}/indexes/{self.index_name}/documents",
                headers=self.headers,
                json=[test_product]
            )
            
            if response.status_code in [200, 202]:
                print("✅ Produit de test créé")
                
                # Attendre l'indexation
                print("⏳ Attente indexation...")
                asyncio.sleep(3)
                
                # Tester la recherche
                search_response = requests.post(
                    f"{self.meili_url}/indexes/{self.index_name}/search",
                    headers=self.headers,
                    json={"query": "casque rouge", "limit": 5}
                )
                
                if search_response.status_code == 200:
                    results = search_response.json()
                    hits = len(results.get("hits", []))
                    print(f"🔍 Test recherche 'casque rouge': {hits} résultats")
                    
                    if hits > 0:
                        print("🎉 SUCCÈS: L'index fonctionne maintenant!")
                        return True
                    else:
                        print("❌ ÉCHEC: Aucun résultat malgré le produit de test")
                        return False
                
            else:
                print(f"❌ Erreur création produit test: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Erreur création produit test: {e}")
            return False

    def run_complete_fix(self) -> Dict:
        """
        🚀 Exécute une correction complète de l'index products
        """
        print("🚀 CORRECTION COMPLÈTE INDEX PRODUCTS")
        print("=" * 70)
        
        results = {
            "diagnosis": {},
            "fix_applied": False,
            "test_product_created": False,
            "final_status": "unknown",
            "recommendations": []
        }
        
        # 1. Diagnostic initial
        print("\n📋 ÉTAPE 1: DIAGNOSTIC")
        results["diagnosis"] = self.diagnose_products_index()
        
        # 2. Appliquer corrections si nécessaire
        if results["diagnosis"]["issues_found"]:
            print("\n🔧 ÉTAPE 2: CORRECTION")
            results["fix_applied"] = self.fix_products_index()
        
        # 3. Créer produit de test
        print("\n🧪 ÉTAPE 3: TEST")
        results["test_product_created"] = self.create_test_product()
        
        # 4. Diagnostic final
        print("\n📊 ÉTAPE 4: VÉRIFICATION FINALE")
        final_diagnosis = self.diagnose_products_index()
        
        # Déterminer le statut final
        if (final_diagnosis["document_count"] > 0 and 
            any(result["hits"] > 0 for result in final_diagnosis["search_test_results"].values())):
            results["final_status"] = "success"
            print("🎉 SUCCÈS: Index products fonctionne correctement!")
        else:
            results["final_status"] = "failed"
            print("❌ ÉCHEC: Index products ne fonctionne toujours pas")
            results["recommendations"] = [
                "Vérifier la configuration MeiliSearch",
                "Réindexer manuellement tous les produits",
                "Vérifier les logs MeiliSearch pour erreurs",
                "Contacter le support technique"
            ]
        
        return results

async def fix_meilisearch_products(company_id: str = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"):
    """
    🔧 Fonction utilitaire pour corriger l'index products
    """
    fixer = MeiliSearchProductsFixer(company_id)
    return fixer.run_complete_fix()

if __name__ == "__main__":
    import asyncio
    
    print("🔧 CORRECTEUR INDEX MEILISEARCH PRODUCTS")
    print("=" * 50)
    
    # Exécuter la correction complète
    fixer = MeiliSearchProductsFixer()
    results = fixer.run_complete_fix()
    
    print(f"\n📊 RÉSUMÉ FINAL:")
    print(f"Status: {results['final_status']}")
    print(f"Corrections appliquées: {results['fix_applied']}")
    print(f"Produit test créé: {results['test_product_created']}")
    
    if results["recommendations"]:
        print(f"\n💡 RECOMMANDATIONS:")
        for rec in results["recommendations"]:
            print(f"  • {rec}")

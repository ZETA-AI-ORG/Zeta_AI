#!/usr/bin/env python3
"""
Script de test ultra-robuste pour Meilisearch - Recherche des défaillances
Basé sur le dataset 'rue du grossiste' - Auto & Moto
Company ID: XkCn8fjNWEWwqiiKMgJX7OcQrUJ3
"""

import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any
import aiohttp
import logging

# Configuration
MEILISEARCH_URL = "http://localhost:7700"
MEILISEARCH_KEY = "N80w8LbzObzK18rZk7zwiHNpJLA_YFSvYGt2XzGLP_4"
COMPANY_ID = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"
INDEX_NAME = f"company_docs_{COMPANY_ID}"

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MeilisearchTester:
    def __init__(self):
        self.base_url = MEILISEARCH_URL
        self.api_key = MEILISEARCH_KEY
        self.index_name = INDEX_NAME
        self.results = []
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def search_query(self, query: str, filters: str = None, limit: int = 20) -> Dict[str, Any]:
        """Effectue une recherche Meilisearch"""
        try:
            search_params = {
                "q": query,
                "limit": limit,
                "attributesToRetrieve": ["*"],
                "attributesToHighlight": ["*"]
            }
            
            if filters:
                search_params["filter"] = filters
                
            url = f"{self.base_url}/indexes/{self.index_name}/search"
            
            start_time = time.time()
            async with self.session.post(url, json=search_params) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "data": data,
                        "response_time": response_time,
                        "status_code": response.status
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": error_text,
                        "response_time": response_time,
                        "status_code": response.status
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": 0,
                "status_code": 0
            }

    async def run_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute un cas de test"""
        logger.info(f"Test: {test_case['name']}")
        
        result = await self.search_query(
            query=test_case['query'],
            filters=test_case.get('filters'),
            limit=test_case.get('limit', 20)
        )
        
        # Analyse des résultats
        analysis = self.analyze_results(test_case, result)
        
        test_result = {
            "test_name": test_case['name'],
            "category": test_case['category'],
            "query": test_case['query'],
            "filters": test_case.get('filters'),
            "expected_behavior": test_case['expected'],
            "actual_result": result,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }
        
        self.results.append(test_result)
        return test_result

    def analyze_results(self, test_case: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyse les résultats par rapport aux attentes"""
        analysis = {
            "passed": False,
            "issues": [],
            "hit_count": 0,
            "response_time_ok": True,
            "relevance_score": 0
        }
        
        if not result["success"]:
            analysis["issues"].append(f"Échec de la requête: {result.get('error', 'Erreur inconnue')}")
            return analysis
            
        hits = result["data"].get("hits", [])
        analysis["hit_count"] = len(hits)
        
        # Vérification du temps de réponse
        if result["response_time"] > 2.0:
            analysis["response_time_ok"] = False
            analysis["issues"].append(f"Temps de réponse lent: {result['response_time']:.2f}s")
            
        # Vérification des attentes
        expected = test_case["expected"]
        
        if expected["should_find_results"] and analysis["hit_count"] == 0:
            analysis["issues"].append("Aucun résultat trouvé alors qu'on en attendait")
        elif not expected["should_find_results"] and analysis["hit_count"] > 0:
            analysis["issues"].append("Résultats trouvés alors qu'on n'en attendait pas")
            
        if "min_results" in expected and analysis["hit_count"] < expected["min_results"]:
            analysis["issues"].append(f"Trop peu de résultats: {analysis['hit_count']} < {expected['min_results']}")
            
        if "max_results" in expected and analysis["hit_count"] > expected["max_results"]:
            analysis["issues"].append(f"Trop de résultats: {analysis['hit_count']} > {expected['max_results']}")
            
        # Vérification du contenu attendu
        if "must_contain" in expected and hits:
            for must_contain in expected["must_contain"]:
                found = any(must_contain.lower() in str(hit).lower() for hit in hits)
                if not found:
                    analysis["issues"].append(f"Contenu manquant: '{must_contain}'")
                    
        if "must_not_contain" in expected and hits:
            for must_not_contain in expected["must_not_contain"]:
                found = any(must_not_contain.lower() in str(hit).lower() for hit in hits)
                if found:
                    analysis["issues"].append(f"Contenu indésirable trouvé: '{must_not_contain}'")
        
        analysis["passed"] = len(analysis["issues"]) == 0
        return analysis

    def get_test_cases(self) -> List[Dict[str, Any]]:
        """Définit tous les cas de test"""
        return [
            # === TESTS PRODUITS - RECHERCHE BASIQUE ===
            {
                "name": "Recherche produit exact",
                "category": "produits_basique",
                "query": "CASQUES MOTO",
                "expected": {"should_find_results": True, "min_results": 4, "must_contain": ["CASQUES MOTO"]}
            },
            {
                "name": "Recherche couleur spécifique",
                "category": "produits_couleur",
                "query": "casque bleu",
                "expected": {"should_find_results": True, "min_results": 1, "must_contain": ["BLEU"]}
            },
            {
                "name": "Recherche prix exact",
                "category": "produits_prix",
                "query": "6500 FCFA",
                "expected": {"should_find_results": True, "min_results": 4}
            },
            
            # === TESTS SENSIBILITÉ CASSE ===
            {
                "name": "Casse mixte",
                "category": "casse",
                "query": "CaSqUe MoTo",
                "expected": {"should_find_results": True, "min_results": 1}
            },
            {
                "name": "Tout minuscule",
                "category": "casse",
                "query": "casques moto noir",
                "expected": {"should_find_results": True, "must_contain": ["NOIR"]}
            },
            
            # === TESTS FAUTES DE FRAPPE ===
            {
                "name": "Faute légère",
                "category": "typos",
                "query": "casque moto",
                "expected": {"should_find_results": True, "min_results": 1}
            },
            {
                "name": "Faute grave",
                "category": "typos",
                "query": "kasque moto",
                "expected": {"should_find_results": False}
            },
            
            # === TESTS COULEURS COMPLEXES ===
            {
                "name": "Couleur avec incohérence casse",
                "category": "couleurs",
                "query": "rouge",
                "expected": {"should_find_results": True, "must_contain": ["rouge"]}
            },
            {
                "name": "Couleur majuscule",
                "category": "couleurs", 
                "query": "GRIS",
                "expected": {"should_find_results": True, "must_contain": ["GRIS"]}
            },
            
            # === TESTS LIVRAISON ===
            {
                "name": "Zone livraison exacte",
                "category": "livraison",
                "query": "Yopougon",
                "expected": {"should_find_results": True, "must_contain": ["Yopougon"]}
            },
            {
                "name": "Prix livraison",
                "category": "livraison",
                "query": "1000 FCFA livraison",
                "expected": {"should_find_results": True, "must_contain": ["1000"]}
            },
            {
                "name": "Zone groupe Cocody",
                "category": "livraison",
                "query": "Cocody",
                "expected": {"should_find_results": True, "must_contain": ["Cocody"]}
            },
            {
                "name": "Hors Abidjan",
                "category": "livraison",
                "query": "Hors Abidjan",
                "expected": {"should_find_results": True, "must_contain": ["Hors Abidjan"]}
            },
            
            # === TESTS PAIEMENT ===
            {
                "name": "Méthode paiement Wave",
                "category": "paiement",
                "query": "Wave",
                "expected": {"should_find_results": True, "must_contain": ["Wave"]}
            },
            {
                "name": "Numéro Wave",
                "category": "paiement",
                "query": "+2250787360757",
                "expected": {"should_find_results": True, "must_contain": ["+2250787360757"]}
            },
            {
                "name": "COD paiement",
                "category": "paiement",
                "query": "paiement livraison",
                "expected": {"should_find_results": True, "must_contain": ["COD"]}
            },
            
            # === TESTS SUPPORT ===
            {
                "name": "Contact support",
                "category": "support",
                "query": "support client",
                "expected": {"should_find_results": True, "must_contain": ["Support"]}
            },
            {
                "name": "WhatsApp support",
                "category": "support",
                "query": "WhatsApp",
                "expected": {"should_find_results": True, "must_contain": ["whatsapp"]}
            },
            
            # === TESTS ENTREPRISE ===
            {
                "name": "Nom entreprise",
                "category": "entreprise",
                "query": "rue du grossiste",
                "expected": {"should_find_results": True, "must_contain": ["rue du grossiste"]}
            },
            {
                "name": "Assistant IA Jessica",
                "category": "entreprise",
                "query": "jessica",
                "expected": {"should_find_results": True, "must_contain": ["jessica"]}
            },
            {
                "name": "Secteur Auto Moto",
                "category": "entreprise",
                "query": "Auto Moto",
                "expected": {"should_find_results": True, "must_contain": ["Auto & Moto"]}
            },
            
            # === TESTS DÉFAILLANCE INTENTIONNELS ===
            {
                "name": "Produit inexistant",
                "category": "defaillance",
                "query": "vélo électrique",
                "expected": {"should_find_results": False}
            },
            {
                "name": "Zone inexistante",
                "category": "defaillance", 
                "query": "livraison Paris",
                "expected": {"should_find_results": False}
            },
            {
                "name": "Prix inexistant",
                "category": "defaillance",
                "query": "100 euros",
                "expected": {"should_find_results": False}
            },
            {
                "name": "Couleur inexistante",
                "category": "defaillance",
                "query": "casque violet",
                "expected": {"should_find_results": False}
            },
            
            # === TESTS RECHERCHE PARTIELLE ===
            {
                "name": "Mot partiel",
                "category": "partiel",
                "query": "casq",
                "expected": {"should_find_results": False}
            },
            {
                "name": "Recherche vide",
                "category": "partiel",
                "query": "",
                "expected": {"should_find_results": True, "min_results": 5}
            },
            
            # === TESTS COMBINAISONS COMPLEXES ===
            {
                "name": "Produit + couleur + prix",
                "category": "combinaison",
                "query": "casque rouge 6500",
                "expected": {"should_find_results": True, "must_contain": ["rouge", "6500"]}
            },
            {
                "name": "Livraison + zone + prix",
                "category": "combinaison",
                "query": "livraison Yopougon 1000",
                "expected": {"should_find_results": True, "must_contain": ["Yopougon", "1000"]}
            },
            
            # === TESTS LIMITES SYSTÈME ===
            {
                "name": "Requête très longue",
                "category": "limites",
                "query": "casque moto rouge bleu noir gris livraison Abidjan Yopougon paiement Wave support client jessica rue grossiste",
                "expected": {"should_find_results": True, "min_results": 1}
            },
            {
                "name": "Caractères spéciaux",
                "category": "limites",
                "query": "casque@moto#rouge!",
                "expected": {"should_find_results": False}
            },
            {
                "name": "Accents et caractères",
                "category": "limites",
                "query": "Côte d'Ivoire",
                "expected": {"should_find_results": True, "must_contain": ["Cote d'ivoire"]}
            }
        ]

    async def run_all_tests(self):
        """Exécute tous les tests"""
        test_cases = self.get_test_cases()
        logger.info(f"Démarrage de {len(test_cases)} tests")
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"[{i}/{len(test_cases)}] {test_case['name']}")
            await self.run_test_case(test_case)
            await asyncio.sleep(0.1)  # Pause entre les tests
            
        self.generate_report()

    def generate_report(self):
        """Génère un rapport détaillé"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["analysis"]["passed"])
        failed_tests = total_tests - passed_tests
        
        # Statistiques par catégorie
        categories = {}
        for result in self.results:
            cat = result["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "passed": 0, "failed": 0}
            categories[cat]["total"] += 1
            if result["analysis"]["passed"]:
                categories[cat]["passed"] += 1
            else:
                categories[cat]["failed"] += 1
        
        # Génération du rapport
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "timestamp": datetime.now().isoformat()
            },
            "categories": categories,
            "failed_tests": [r for r in self.results if not r["analysis"]["passed"]],
            "detailed_results": self.results
        }
        
        # Sauvegarde
        filename = f"meili_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        # Affichage console
        print("\n" + "="*80)
        print("RAPPORT DE TEST MEILISEARCH - DÉFAILLANCES DÉTECTÉES")
        print("="*80)
        print(f"Tests totaux: {total_tests}")
        print(f"Réussis: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"Échoués: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        
        print(f"\nSTATISTIQUES PAR CATÉGORIE:")
        for cat, stats in categories.items():
            print(f"  {cat}: {stats['passed']}/{stats['total']} ({stats['passed']/stats['total']*100:.1f}%)")
            
        if failed_tests > 0:
            print(f"\nDÉFAILLANCES CRITIQUES DÉTECTÉES:")
            for result in report["failed_tests"]:
                print(f"\n❌ {result['test_name']}")
                print(f"   Requête: '{result['query']}'")
                for issue in result["analysis"]["issues"]:
                    print(f"   • {issue}")
                    
        print(f"\nRapport détaillé sauvegardé: {filename}")
        print("="*80)

async def main():
    """Point d'entrée principal"""
    print("🔍 DÉMARRAGE DU TEST ULTRA-ROBUSTE MEILISEARCH")
    print(f"Index: {INDEX_NAME}")
    print(f"URL: {MEILISEARCH_URL}")
    
    async with MeilisearchTester() as tester:
        await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())

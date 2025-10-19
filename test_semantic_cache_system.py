#!/usr/bin/env python3
"""
🧪 TESTS COMPLETS DU SYSTÈME DE CACHE SÉMANTIQUE RÉVOLUTIONNAIRE
================================================================
Tests de validation pour le cache dynamique intention-FAQ

TESTS COUVERTS:
- Performance du cache sémantique
- Two-Stage Retrieval Engine
- Matching sémantique avec embeddings
- Intégration avec le système RAG existant
- Gestion des intentions et entités
"""

import asyncio
import time
import json
from typing import Dict, Any, List
from datetime import datetime

from core.semantic_intent_cache import (
    get_semantic_intent_cache, 
    IntentSignature,
    create_intent_signature_from_detection
)
from core.enhanced_rag_with_semantic_cache import create_enhanced_rag_with_cache
from core.rag_cache_integration import get_rag_cache_integration, with_semantic_cache
from core.universal_rag_engine import UniversalRAGEngine
from utils import log3

class SemanticCacheTestSuite:
    """🧪 Suite de tests pour le cache sémantique"""
    
    def __init__(self):
        self.semantic_cache = get_semantic_intent_cache()
        self.test_results = []
        self.performance_metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_cache_response_time": 0.0,
            "avg_rag_response_time": 0.0,
            "semantic_matches": 0,
            "exact_matches": 0
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """🚀 Exécute tous les tests du cache sémantique"""
        print("🧪 DÉMARRAGE TESTS CACHE SÉMANTIQUE RÉVOLUTIONNAIRE")
        print("=" * 70)
        
        # Vider le cache avant les tests
        await self.semantic_cache.clear_cache()
        
        test_methods = [
            self.test_basic_cache_operations,
            self.test_semantic_similarity_matching,
            self.test_intent_based_caching,
            self.test_two_stage_retrieval,
            self.test_performance_comparison,
            self.test_multi_granular_cache,
            self.test_conversation_context_awareness,
            self.test_cache_integration
        ]
        
        for test_method in test_methods:
            try:
                print(f"\n🔬 {test_method.__name__.replace('_', ' ').title()}")
                print("-" * 50)
                
                start_time = time.time()
                result = await test_method()
                execution_time = time.time() - start_time
                
                self.test_results.append({
                    "test_name": test_method.__name__,
                    "status": "PASSED" if result.get("success", False) else "FAILED",
                    "execution_time": execution_time,
                    "details": result
                })
                
                status_emoji = "✅" if result.get("success", False) else "❌"
                print(f"{status_emoji} {test_method.__name__}: {result.get('message', 'Completed')} ({execution_time:.2f}s)")
                
            except Exception as e:
                print(f"❌ {test_method.__name__}: ERREUR - {e}")
                self.test_results.append({
                    "test_name": test_method.__name__,
                    "status": "ERROR",
                    "execution_time": 0,
                    "error": str(e)
                })
        
        return self._generate_test_report()
    
    async def test_basic_cache_operations(self) -> Dict[str, Any]:
        """Test des opérations de base du cache avec données RUE_DU_GROS"""
        intent_sig = IntentSignature(
            primary_intent="LIVRAISON",
            secondary_intents=["PRIX"],
            entities={"zone": "Cocody", "company_id": "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"},
            context_hash="LIVRAISON|PRIX",
            confidence_score=1.0
        )
        
        # Test stockage avec vraies données Rue_du_gros
        store_success = await self.semantic_cache.store_response(
            query="Combien coûte la livraison à Cocody ?",
            response="La livraison à Cocody coûte 1500 FCFA (zone centrale Abidjan).",
            intent_signature=intent_sig,
            conversation_history="Client demande info livraison Rue_du_gros"
        )
        
        if not store_success:
            return {"success": False, "message": "Échec stockage"}
        
        # Test récupération
        cache_result = await self.semantic_cache.get_cached_response(
            query="Combien coûte la livraison à Cocody ?",
            intent_signature=intent_sig,
            conversation_history="Test basique"
        )
        
        if cache_result:
            response, confidence = cache_result
            return {
                "success": True,
                "message": f"Cache opérationnel (confiance: {confidence:.3f})",
                "response": response
            }
        
        return {"success": False, "message": "Échec récupération"}
    
    async def test_semantic_similarity_matching(self) -> Dict[str, Any]:
        """Test du matching sémantique avec formulations différentes - RUE_DU_GROS"""
        intent_sig = IntentSignature(
            primary_intent="LIVRAISON",
            secondary_intents=["PRIX"],
            entities={"zone": "Yopougon", "company_id": "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"},
            context_hash="LIVRAISON|PRIX",
            confidence_score=1.0
        )
        
        # Stocker avec une formulation (données réelles Rue_du_gros)
        await self.semantic_cache.store_response(
            query="Quel est le prix pour livrer à Yopougon ?",
            response="La livraison à Yopougon coûte 1500 FCFA (zone centrale Abidjan).",
            intent_signature=intent_sig
        )
        
        # Tester avec des formulations différentes
        test_queries = [
            "Combien ça coûte d'envoyer à Yopougon ?",
            "Tarif livraison Yopougon ?",
            "Prix pour expédier vers Yopougon",
            "Coût transport Yopougon"
        ]
        
        matches = 0
        confidences = []
        
        for query in test_queries:
            result = await self.semantic_cache.get_cached_response(
                query=query,
                intent_signature=intent_sig
            )
            
            if result:
                response, confidence = result
                matches += 1
                confidences.append(confidence)
                self.performance_metrics["semantic_matches"] += 1
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "success": matches >= 2,  # Au moins 2 matches sur 4
            "message": f"{matches}/4 formulations matchées (conf. moy: {avg_confidence:.3f})",
            "matches": matches,
            "avg_confidence": avg_confidence
        }
    
    async def test_intent_based_caching(self) -> Dict[str, Any]:
        """Test du cache basé sur les intentions - RUE_DU_GROS"""
        company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
        
        # Créer différentes intentions avec données réelles
        intents = [
            IntentSignature("PRODUIT", ["PRIX"], {"produit": "couches", "company_id": company_id}, "PRODUIT|PRIX", 1.0),
            IntentSignature("LIVRAISON", ["PRIX"], {"zone": "Plateau", "company_id": company_id}, "LIVRAISON|PRIX", 1.0),
            IntentSignature("SUPPORT", ["COMMANDE"], {"type": "whatsapp", "company_id": company_id}, "SUPPORT|COMMANDE", 1.0)
        ]
        
        queries_responses = [
            ("Combien coûtent les couches culottes 3 paquets ?", "Les couches culottes 3 paquets coûtent 13.500 FCFA (4.500 F/paquet)."),
            ("Livraison au Plateau ?", "Livraison Plateau: 1500 FCFA (zone centrale Abidjan)."),
            ("Numéro WhatsApp pour commander ?", "WhatsApp: +2250160924560 | Téléphone: +2250787360757")
        ]
        
        # Stocker les réponses
        for i, (query, response) in enumerate(queries_responses):
            await self.semantic_cache.store_response(
                query=query,
                response=response,
                intent_signature=intents[i]
            )
        
        # Tester la récupération par intention
        correct_retrievals = 0
        
        for i, (test_query, expected_response) in enumerate(queries_responses):
            result = await self.semantic_cache.get_cached_response(
                query=test_query,
                intent_signature=intents[i]
            )
            
            if result:
                response, confidence = result
                if expected_response in response:
                    correct_retrievals += 1
        
        return {
            "success": correct_retrievals == 3,
            "message": f"{correct_retrievals}/3 intentions correctement récupérées",
            "correct_retrievals": correct_retrievals
        }
    
    async def test_two_stage_retrieval(self) -> Dict[str, Any]:
        """Test du moteur Two-Stage Retrieval"""
        # Remplir le cache avec plusieurs entrées
        test_data = [
            ("Prix casque rouge", "PRIX_PRODUIT", {"produit": "casque", "couleur": "rouge"}, "Casque rouge: 7000 FCFA"),
            ("Prix casque bleu", "PRIX_PRODUIT", {"produit": "casque", "couleur": "bleu"}, "Casque bleu: 6500 FCFA"),
            ("Livraison Cocody", "LIVRAISON_INFO", {"zone": "Cocody"}, "Livraison Cocody: 1500 FCFA"),
            ("Livraison Yopougon", "LIVRAISON_INFO", {"zone": "Yopougon"}, "Livraison Yopougon: 1000 FCFA"),
        ]
        
        for query, intent, entities, response in test_data:
            intent_sig = IntentSignature(intent, [], entities, f"test_{intent}", 0.9)
            await self.semantic_cache.store_response(query, response, intent_sig)
        
        # Test Stage 1: Recherche rapide
        retrieval_engine = self.semantic_cache.retrieval_engine
        query_embedding = retrieval_engine.create_query_embedding("Combien coûte le casque rouge ?")
        
        candidates = retrieval_engine.stage1_rapid_search(query_embedding, self.semantic_cache.memory_cache)
        
        # Test Stage 2: Matching contextuel
        if candidates:
            intent_sig = IntentSignature("PRIX_PRODUIT", [], {"produit": "casque", "couleur": "rouge"}, "test", 0.9)
            context_embedding = retrieval_engine.create_context_embedding("")
            
            best_match = retrieval_engine.stage2_contextual_matching(
                query_embedding, context_embedding, intent_sig, candidates, self.semantic_cache.memory_cache
            )
            
            return {
                "success": best_match is not None,
                "message": f"Two-Stage: {len(candidates)} candidats → {'Match trouvé' if best_match else 'Aucun match'}",
                "candidates_count": len(candidates),
                "best_match_found": best_match is not None
            }
        
        return {"success": False, "message": "Aucun candidat trouvé en Stage 1"}
    
    async def test_performance_comparison(self) -> Dict[str, Any]:
        """Test de comparaison de performance cache vs RAG"""
        # Simuler une réponse RAG lente
        async def mock_rag_response(query: str) -> str:
            await asyncio.sleep(2)  # Simuler 2s de traitement RAG
            return f"Réponse RAG simulée pour: {query}"
        
        test_query = "Combien coûte la livraison express ?"
        intent_sig = IntentSignature("LIVRAISON_EXPRESS", [], {"type": "express"}, "perf_test", 0.9)
        
        # Test 1: RAG classique (cache miss)
        start_time = time.time()
        rag_response = await mock_rag_response(test_query)
        rag_time = time.time() - start_time
        
        # Stocker dans le cache
        await self.semantic_cache.store_response(test_query, rag_response, intent_sig)
        
        # Test 2: Cache hit
        start_time = time.time()
        cache_result = await self.semantic_cache.get_cached_response(test_query, intent_sig)
        cache_time = time.time() - start_time
        
        if cache_result:
            speedup = rag_time / cache_time if cache_time > 0 else float('inf')
            self.performance_metrics["avg_rag_response_time"] = rag_time
            self.performance_metrics["avg_cache_response_time"] = cache_time
            
            return {
                "success": speedup > 5,  # Au moins 5x plus rapide
                "message": f"Speedup: {speedup:.1f}x ({rag_time:.2f}s → {cache_time:.3f}s)",
                "rag_time": rag_time,
                "cache_time": cache_time,
                "speedup": speedup
            }
        
        return {"success": False, "message": "Cache hit échoué"}
    
    async def test_multi_granular_cache(self) -> Dict[str, Any]:
        """Test du cache multi-granulaire - RUE_DU_GROS"""
        company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
        
        # Niveau 1: Intention seule
        intent_general = IntentSignature("PRIX", [], {"company_id": company_id}, "PRIX", 1.0)
        await self.semantic_cache.store_response(
            "Quels sont vos prix ?", "Nos prix varient selon les produits: couches à pression, couches culottes, couches adultes.", intent_general
        )
        
        # Niveau 2: Intention + entité
        intent_specific = IntentSignature("PRIX", [], {"produit": "couches", "company_id": company_id}, "PRIX", 1.0)
        await self.semantic_cache.store_response(
            "Prix des couches ?", "Couches culottes: 5.500-168.000 FCFA selon quantité.", intent_specific
        )
        
        # Niveau 3: Intention + entité + contexte
        intent_detailed = IntentSignature("PRIX", [], {"produit": "couches", "quantite": "3", "company_id": company_id}, "PRIX", 1.0)
        await self.semantic_cache.store_response(
            "Prix 3 paquets couches culottes ?", "3 paquets couches culottes: 13.500 FCFA (4.500 F/paquet).", intent_detailed
        )
        
        # Tester la granularité
        test_cases = [
            ("Prix ?", intent_general, "général"),
            ("Prix couches ?", intent_specific, "spécifique"),
            ("Prix 3 paquets couches culottes ?", intent_detailed, "détaillé")
        ]
        
        matches = 0
        for query, intent, level in test_cases:
            result = await self.semantic_cache.get_cached_response(query, intent)
            if result:
                matches += 1
        
        return {
            "success": matches == 3,
            "message": f"Cache multi-granulaire: {matches}/3 niveaux fonctionnels",
            "matches": matches
        }
    
    async def test_conversation_context_awareness(self) -> Dict[str, Any]:
        """Test de la prise en compte du contexte conversationnel"""
        intent_sig = IntentSignature("PRIX_CONTEXTUEL", [], {"produit": "smartphone"}, "context_test", 0.9)
        
        # Contexte 1: Client intéressé
        context1 = "L'utilisateur compare des smartphones pour un achat."
        await self.semantic_cache.store_response(
            "Prix smartphone ?", "Smartphone: 150000 FCFA. Excellent rapport qualité-prix !", 
            intent_sig, context1
        )
        
        # Contexte 2: Client hésitant
        context2 = "L'utilisateur hésite et cherche des alternatives moins chères."
        await self.semantic_cache.store_response(
            "Prix smartphone ?", "Smartphone: 150000 FCFA. Nous avons aussi des modèles à 80000 FCFA.", 
            intent_sig, context2
        )
        
        # Tester avec contextes similaires
        result1 = await self.semantic_cache.get_cached_response(
            "Combien coûte le smartphone ?", intent_sig, 
            "L'utilisateur veut acheter un smartphone de qualité."
        )
        
        result2 = await self.semantic_cache.get_cached_response(
            "Prix du smartphone ?", intent_sig,
            "L'utilisateur cherche quelque chose de pas cher."
        )
        
        context_matches = 0
        if result1 and "qualité-prix" in result1[0]:
            context_matches += 1
        if result2 and "80000" in result2[0]:
            context_matches += 1
        
        return {
            "success": context_matches >= 1,
            "message": f"Contexte conversationnel: {context_matches}/2 matches contextuels",
            "context_matches": context_matches
        }
    
    async def test_cache_integration(self) -> Dict[str, Any]:
        """Test de l'intégration avec le système existant"""
        integration = get_rag_cache_integration()
        
        # Créer une fonction mock avec le décorateur
        @with_semantic_cache
        async def mock_rag_function(query: str, company_id: str) -> str:
            await asyncio.sleep(1)  # Simuler traitement
            return f"Réponse RAG intégrée: {query}"
        
        # Test 1: Première requête (cache miss)
        start1 = time.time()
        result1 = await mock_rag_function("Test intégration cache", "test_company")
        time1 = time.time() - start1
        
        # Test 2: Requête similaire (cache hit attendu)
        start2 = time.time()
        result2 = await mock_rag_function("Test intégration du cache", "test_company")
        time2 = time.time() - start2
        
        # Vérifier l'amélioration de performance
        speedup = time1 / time2 if time2 > 0 else 1
        
        return {
            "success": speedup > 2,  # Au moins 2x plus rapide
            "message": f"Intégration: {speedup:.1f}x speedup ({time1:.2f}s → {time2:.2f}s)",
            "first_call_time": time1,
            "second_call_time": time2,
            "speedup": speedup
        }
    
    def _generate_test_report(self) -> Dict[str, Any]:
        """Génère le rapport final des tests"""
        passed_tests = sum(1 for result in self.test_results if result["status"] == "PASSED")
        total_tests = len(self.test_results)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        cache_stats = self.semantic_cache.get_stats()
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate_percent": round(success_rate, 2)
            },
            "performance_metrics": self.performance_metrics,
            "cache_statistics": cache_stats,
            "detailed_results": self.test_results,
            "timestamp": datetime.now().isoformat(),
            "overall_status": "SUCCESS" if success_rate >= 80 else "PARTIAL" if success_rate >= 60 else "FAILED"
        }
        
        return report

async def main():
    """🚀 Fonction principale de test"""
    print("🧪 LANCEMENT SUITE DE TESTS CACHE SÉMANTIQUE RÉVOLUTIONNAIRE")
    print("=" * 80)
    
    test_suite = SemanticCacheTestSuite()
    
    try:
        # Exécuter tous les tests
        report = await test_suite.run_all_tests()
        
        # Afficher le rapport final
        print("\n" + "=" * 80)
        print("📊 RAPPORT FINAL DES TESTS")
        print("=" * 80)
        
        summary = report["test_summary"]
        print(f"✅ Tests réussis: {summary['passed_tests']}/{summary['total_tests']}")
        print(f"📈 Taux de réussite: {summary['success_rate_percent']}%")
        print(f"🎯 Statut global: {report['overall_status']}")
        
        # Statistiques de performance
        perf = report["performance_metrics"]
        if perf["avg_cache_response_time"] > 0 and perf["avg_rag_response_time"] > 0:
            speedup = perf["avg_rag_response_time"] / perf["avg_cache_response_time"]
            print(f"⚡ Speedup moyen: {speedup:.1f}x")
        
        # Statistiques du cache
        cache_stats = report["cache_statistics"]
        print(f"🎯 Taux de hit cache: {cache_stats.get('hit_rate_percent', 0)}%")
        print(f"💾 Taille du cache: {cache_stats.get('cache_size', 0)} entrées")
        
        # Sauvegarder le rapport
        report_filename = f"semantic_cache_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Rapport sauvegardé: {report_filename}")
        
        # Verdict final
        if report["overall_status"] == "SUCCESS":
            print("\n🎉 SYSTÈME DE CACHE SÉMANTIQUE RÉVOLUTIONNAIRE VALIDÉ !")
            print("✅ Prêt pour la production")
        elif report["overall_status"] == "PARTIAL":
            print("\n⚠️ Système partiellement fonctionnel - Optimisations recommandées")
        else:
            print("\n❌ Problèmes détectés - Corrections nécessaires")
        
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE LORS DES TESTS: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

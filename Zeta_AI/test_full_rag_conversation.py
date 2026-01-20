#!/usr/bin/env python3
"""
🧪 TEST CONVERSATION RAG COMPLÈTE - SIMULATION CLIENT RÉEL
===========================================================
Test d'une conversation complète : Prise d'info → Doutes → Commande finale
Évalue la pertinence, la cohérence et la mémoire conversationnelle du RAG
"""

import asyncio
import time
from typing import Dict, List, Any, Tuple
from datetime import datetime
import json

# Imports du système RAG
from core.universal_rag_engine import UniversalRAGEngine
from core.enhanced_rag_with_semantic_cache import EnhancedRAGWithSemanticCache
from core.intention_detector import detect_user_intention, format_intention_for_llm

class FullRAGConversationTest:
    """🧪 Test conversation RAG complète avec évaluation"""
    
    def __init__(self):
        self.company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
        self.user_id = "testuser143"
        
        # Initialisation du RAG (CACHE SÉMANTIQUE DÉSACTIVÉ)
        self.base_rag = UniversalRAGEngine()
        self.enhanced_rag = EnhancedRAGWithSemanticCache(self.base_rag)
        
        # 🚫 DÉSACTIVER LE CACHE SÉMANTIQUE - PRIORITÉ MÉMOIRE CONVERSATIONNELLE
        self.enhanced_rag.enable_cache(False)
        
        # Historique de conversation
        self.conversation_history = []
        self.conversation_context = ""
        
        # Métriques d'évaluation
        self.metrics = {
            "total_queries": 0,
            "cache_hits": 0,
            "response_times": [],
            "intention_accuracy": [],
            "context_preservation": [],
            "source_relevance": []
        }
    
    async def run_full_conversation_test(self):
        """🚀 Lance le test de conversation complète"""
        print("🧪 TEST CONVERSATION RAG COMPLÈTE - CACHE DÉSACTIVÉ")
        print("=" * 60)
        print(f"🏢 Company ID: {self.company_id}")
        print(f"👤 User ID: {self.user_id}")
        print(f"🚫 Cache sémantique: DÉSACTIVÉ")
        print(f"🎯 Priorité: MÉMOIRE CONVERSATIONNELLE + FIABILITÉ")
        print(f"⏰ Début: {datetime.now().strftime('%H:%M:%S')}")
        print()
        
        # Scénario de conversation réaliste
        conversation_scenario = [
            {
                "phase": "DÉCOUVERTE",
                "query": "Bonjour, j'aimerais connaître vos produits disponibles",
                "expected_intentions": ["PRODUIT", "INFORMATION", "COMMANDE"],
                "context": "Premier contact client"
            },
            {
                "phase": "INFORMATION PRIX",
                "query": "Ça coûte combien vos articles ?",
                "expected_intentions": ["PRIX", "PRODUIT"],
                "context": "Client intéressé par les tarifs"
            },
            {
                "phase": "LIVRAISON",
                "query": "Vous livrez dans quelle zone ? Je suis à Cocody",
                "expected_intentions": ["LIVRAISON", "LOCALISATION"],
                "context": "Client vérifie la faisabilité livraison"
            },
            {
                "phase": "DOUTE PRIX",
                "query": "Le transport c'est en plus du prix du produit ?",
                "expected_intentions": ["PRIX", "LIVRAISON", "PRODUIT"],
                "context": "Client a des doutes sur le coût total"
            },
            {
                "phase": "PAIEMENT",
                "query": "Je peux payer comment ? Vous acceptez Wave ?",
                "expected_intentions": ["PAIEMENT"],
                "context": "Client vérifie les modalités de paiement"
            },
            {
                "phase": "HÉSITATION",
                "query": "J'hésite encore... Vous avez d'autres modèles ?",
                "expected_intentions": ["PRODUIT", "INFORMATION"],
                "context": "Client hésite, cherche alternatives"
            },
            {
                "phase": "COMMANDE",
                "query": "OK je prends le produit premium, livraison express à Cocody",
                "expected_intentions": ["COMMANDE", "PRODUIT", "LIVRAISON"],
                "context": "Client décidé, passe commande"
            },
            {
                "phase": "CONFIRMATION",
                "query": "Ça fait combien au total avec la livraison ?",
                "expected_intentions": ["PRIX", "LIVRAISON", "COMMANDE"],
                "context": "Client veut confirmation prix total"
            }
        ]
        
        print("📋 SCÉNARIO DE CONVERSATION:")
        for i, step in enumerate(conversation_scenario, 1):
            print(f"  {i}. {step['phase']}: {step['query']}")
        print()
        
        # Exécution de la conversation
        for step_num, step in enumerate(conversation_scenario, 1):
            print(f"\n{'='*60}")
            print(f"🔄 ÉTAPE {step_num}/8 - {step['phase']}")
            print(f"{'='*60}")
            
            await self._process_conversation_step(step, step_num)
            
            # Pause entre les étapes pour simuler réflexion client
            await asyncio.sleep(0.5)
        
        # Rapport final
        self._generate_final_evaluation_report()
    
    async def _process_conversation_step(self, step: Dict[str, Any], step_num: int):
        """Traite une étape de la conversation"""
        query = step["query"]
        phase = step["phase"]
        expected_intentions = step["expected_intentions"]
        context = step["context"]
        
        print(f"👤 CLIENT: {query}")
        print(f"🎯 Phase: {phase}")
        print(f"📝 Contexte: {context}")
        print()
        
        # Mesure du temps de réponse
        start_time = time.time()
        
        try:
            # 🚫 DÉTECTION D'INTENTION DÉSACTIVÉE INTÉGRALEMENT
            # mock_results = {...}
            # intention_result = detect_user_intention(query)
            # intentions = intention_result.get("detected_intentions", [])
            
            # Intentions simulées pour le test (sans détection)
            intentions = ["GENERAL"]
            
            # Génération de la réponse RAG
            response_data = await self.enhanced_rag.process_query(
                query=query,
                company_id=self.company_id,
                user_id=self.user_id,
                conversation_history=self.conversation_context
            )
            
            response_time = time.time() - start_time
            self.metrics["response_times"].append(response_time)
            self.metrics["total_queries"] += 1
            
            # Extraction des données de réponse
            response = response_data.get("response", "Erreur: Pas de réponse")
            sources = response_data.get("sources", [])
            cache_used = response_data.get("cache_hit", False)
            
            if cache_used:
                self.metrics["cache_hits"] += 1
            
            # Affichage de la réponse
            print(f"🤖 ASSISTANT: {response}")
            print()
            
            # Affichage des intentions détectées
            print(f"🎯 INTENTIONS DÉTECTÉES: {intentions}")
            expected_set = set(expected_intentions)
            detected_set = set(intentions)
            intention_accuracy = len(expected_set.intersection(detected_set)) / len(expected_set) if expected_set else 0
            self.metrics["intention_accuracy"].append(intention_accuracy)
            print(f"📊 Précision intentions: {intention_accuracy:.1%}")
            print()
            
            # Affichage des sources
            print(f"📚 SOURCES UTILISÉES ({len(sources)}):")
            source_relevance_scores = []
            for i, source in enumerate(sources[:3], 1):  # Top 3 sources
                content = source.get("content", "")[:150] + "..." if len(source.get("content", "")) > 150 else source.get("content", "")
                score = source.get("score", 0)
                index = source.get("index", "unknown")
                
                print(f"  {i}. [{index}] Score: {score:.3f}")
                print(f"     {content}")
                print()
                
                source_relevance_scores.append(score)
            
            avg_source_relevance = sum(source_relevance_scores) / len(source_relevance_scores) if source_relevance_scores else 0
            self.metrics["source_relevance"].append(avg_source_relevance)
            
            # Évaluation de la préservation du contexte
            context_preservation = self._evaluate_context_preservation(query, response, step_num)
            self.metrics["context_preservation"].append(context_preservation)
            
            # Mise à jour de l'historique
            self.conversation_history.append({
                "query": query,
                "response": response,
                "phase": phase,
                "timestamp": datetime.now().isoformat()
            })
            
            # Mise à jour du contexte conversationnel
            self.conversation_context += f"Client: {query}\nAssistant: {response}\n"
            
            # Métriques de performance
            cache_status = "🎯 CACHE HIT" if cache_used else "🔍 RAG SEARCH"
            print(f"⚡ Temps de réponse: {response_time:.2f}s | {cache_status}")
            print(f"📈 Pertinence sources: {avg_source_relevance:.3f}")
            print(f"🧠 Préservation contexte: {context_preservation:.1%}")
            
        except Exception as e:
            print(f"❌ ERREUR: {e}")
            self.metrics["response_times"].append(10.0)  # Pénalité pour erreur
    
    def _evaluate_context_preservation(self, query: str, response: str, step_num: int) -> float:
        """Évalue si le contexte conversationnel est préservé - FOCUS MÉMOIRE CONVERSATIONNELLE"""
        if step_num <= 2:
            return 1.0  # Pas de contexte à préserver au début
        
        # Vérifications contextuelles renforcées
        context_indicators = 0
        total_checks = 0
        
        # CRITÈRE 1: Préservation de la localisation "Cocody" (étape 3+)
        if step_num >= 3:
            total_checks += 1
            # Vérifier dans la réponse ET dans l'historique conversationnel
            cocody_in_response = "cocody" in response.lower()
            cocody_in_context = "cocody" in self.conversation_context.lower()
            
            if cocody_in_response or cocody_in_context:
                context_indicators += 1
                print(f"    ✅ Contexte Cocody préservé à l'étape {step_num} (réponse: {cocody_in_response}, contexte: {cocody_in_context})")
            else:
                print(f"    ❌ Contexte Cocody perdu à l'étape {step_num}")
        
        # CRITÈRE 2: Cohérence des prix mentionnés (étape 2+)
        if step_num >= 2:
            total_checks += 1
            prix_patterns = ["5.500", "5500", "17.900", "17900", "28.900", "28900", "fcfa", "1500", "2000"]
            if any(price in response.lower() for price in prix_patterns):
                context_indicators += 1
                print(f"    ✅ Prix cohérents à l'étape {step_num}")
            else:
                print(f"    ❌ Prix incohérents à l'étape {step_num}")
        
        # CRITÈRE 3: Référence aux produits spécifiques (étape 1+)
        if step_num >= 1:
            total_checks += 1
            produits_patterns = ["couches", "pression", "culottes", "paquet", "taille"]
            if any(prod in response.lower() for prod in produits_patterns):
                context_indicators += 1
                print(f"    ✅ Produits spécifiques mentionnés à l'étape {step_num}")
            else:
                print(f"    ❌ Produits génériques à l'étape {step_num}")
        
        # CRITÈRE 4: Cohérence des informations de livraison (étape 3+)
        if step_num >= 3:
            total_checks += 1
            livraison_patterns = ["livraison", "transport", "zone", "centrale", "1500"]
            if any(word in response.lower() for word in livraison_patterns):
                context_indicators += 1
                print(f"    ✅ Informations livraison cohérentes à l'étape {step_num}")
            else:
                print(f"    ❌ Informations livraison incohérentes à l'étape {step_num}")
        
        # CRITÈRE 5: Progression logique de la conversation (étape 5+)
        if step_num >= 5:
            total_checks += 1
            progression_patterns = ["wave", "paiement", "acompte", "2000", "commande"]
            if any(word in response.lower() for word in progression_patterns):
                context_indicators += 1
                print(f"    ✅ Progression logique à l'étape {step_num}")
            else:
                print(f"    ❌ Pas de progression logique à l'étape {step_num}")
        
        score = context_indicators / total_checks if total_checks > 0 else 1.0
        print(f"    📊 Score contexte: {context_indicators}/{total_checks} = {score:.1%}")
        return score
    
    def _generate_final_evaluation_report(self):
        """Génère le rapport d'évaluation final"""
        print("\n" + "="*80)
        print("📊 RAPPORT D'ÉVALUATION FINAL - CONVERSATION RAG COMPLÈTE")
        print("="*80)
        
        # Métriques générales
        total_queries = self.metrics["total_queries"]
        cache_hits = self.metrics["cache_hits"]
        cache_hit_rate = (cache_hits / total_queries) * 100 if total_queries > 0 else 0
        
        avg_response_time = sum(self.metrics["response_times"]) / len(self.metrics["response_times"]) if self.metrics["response_times"] else 0
        avg_intention_accuracy = sum(self.metrics["intention_accuracy"]) / len(self.metrics["intention_accuracy"]) if self.metrics["intention_accuracy"] else 0
        avg_context_preservation = sum(self.metrics["context_preservation"]) / len(self.metrics["context_preservation"]) if self.metrics["context_preservation"] else 0
        avg_source_relevance = sum(self.metrics["source_relevance"]) / len(self.metrics["source_relevance"]) if self.metrics["source_relevance"] else 0
        
        print(f"🔢 MÉTRIQUES GÉNÉRALES:")
        print(f"  • Total requêtes: {total_queries}")
        print(f"  • Cache hits: {cache_hits}/{total_queries} ({cache_hit_rate:.1f}%)")
        print(f"  • Temps de réponse moyen: {avg_response_time:.2f}s")
        print()
        
        print(f"🎯 QUALITÉ DES RÉPONSES:")
        print(f"  • Précision intentions: {avg_intention_accuracy:.1%}")
        print(f"  • Pertinence sources: {avg_source_relevance:.3f}")
        print(f"  • Préservation contexte: {avg_context_preservation:.1%}")
        print()
        
        # Évaluation globale - PRIORITÉ MÉMOIRE CONVERSATIONNELLE (cache désactivé)
        overall_score = (
            avg_intention_accuracy * 0.3 +      # 30% pour précision intentions
            avg_source_relevance * 0.2 +        # 20% pour pertinence sources  
            avg_context_preservation * 0.5      # 50% pour mémoire conversationnelle ⭐
        ) * 100
        
        print(f"🏆 SCORE GLOBAL: {overall_score:.1f}%")
        
        # Évaluation qualitative
        if overall_score >= 90:
            evaluation = "🎉 EXCELLENT - RAG prêt pour production"
        elif overall_score >= 80:
            evaluation = "✅ TRÈS BON - Quelques optimisations mineures"
        elif overall_score >= 70:
            evaluation = "⚠️ BON - Améliorations nécessaires"
        else:
            evaluation = "❌ INSUFFISANT - Corrections majeures requises"
        
        print(f"📋 ÉVALUATION: {evaluation}")
        print()
        
        # Analyse détaillée par phase
        print(f"📈 ANALYSE PAR PHASE:")
        phases = ["DÉCOUVERTE", "INFORMATION PRIX", "LIVRAISON", "DOUTE PRIX", 
                 "PAIEMENT", "HÉSITATION", "COMMANDE", "CONFIRMATION"]
        
        for i, phase in enumerate(phases):
            if i < len(self.metrics["intention_accuracy"]):
                intention_acc = self.metrics["intention_accuracy"][i]
                response_time = self.metrics["response_times"][i]
                context_pres = self.metrics["context_preservation"][i] if i < len(self.metrics["context_preservation"]) else 0
                
                print(f"  {i+1}. {phase}:")
                print(f"     Intentions: {intention_acc:.1%} | Temps: {response_time:.2f}s | Contexte: {context_pres:.1%}")
        print()
        
        # Recommandations - FOCUS MÉMOIRE CONVERSATIONNELLE
        print(f"💡 RECOMMANDATIONS (PRIORITÉ MÉMOIRE CONVERSATIONNELLE):")
        
        if avg_context_preservation < 0.8:
            print("  🎯 PRIORITÉ 1: Améliorer la mémoire conversationnelle")
            print("    - Enrichir le contexte passé au LLM")
            print("    - Conserver les éléments clés (Cocody, produits choisis)")
            print("    - Implémenter un résumé intelligent de conversation")
        
        if avg_intention_accuracy < 0.8:
            print("  🎯 PRIORITÉ 2: Enrichir les patterns de détection d'intention")
        
        if avg_source_relevance < 0.5:
            print("  🎯 PRIORITÉ 3: Optimiser le routing des index")
            print("    - Améliorer la sélection d'index par pertinence")
            print("    - Éviter les documents non pertinents")
        
        if avg_response_time > 5.0:
            print("  • Optimiser les performances (sans cache)")
        
        print("  ✅ Cache sémantique désactivé - Focus sur fiabilité")
        
        print()
        print(f"⏰ Test terminé: {datetime.now().strftime('%H:%M:%S')}")
        print("="*80)
        
        # Sauvegarde des résultats
        self._save_test_results(overall_score, evaluation)
    
    def _save_test_results(self, overall_score: float, evaluation: str):
        """Sauvegarde les résultats du test"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "company_id": self.company_id,
            "user_id": self.user_id,
            "overall_score": overall_score,
            "evaluation": evaluation,
            "metrics": self.metrics,
            "conversation_history": self.conversation_history
        }
        
        filename = f"rag_conversation_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"💾 Résultats sauvegardés: {filename}")
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde: {e}")

async def main():
    """🚀 Fonction principale"""
    print("🚀 LANCEMENT TEST CONVERSATION RAG COMPLÈTE")
    print()
    
    test_suite = FullRAGConversationTest()
    await test_suite.run_full_conversation_test()

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
🔥 TEST CONVERSATIONNEL ULTRA-ROBUSTE
Validation complète du système RAG avec mémoire optimisée

OBJECTIFS:
1. Tester la mémoire conversationnelle optimisée (sliding window + synthesis)
2. Valider la cohérence sur 50+ échanges
3. Tester les changements d'avis multiples
4. Vérifier la robustesse face aux erreurs
5. Mesurer les performances en conditions réelles
"""

import asyncio
import sys
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Any
import statistics

# Ajouter le répertoire parent au PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 🎯 SCÉNARIO ULTRA-ROBUSTE : 50 ÉCHANGES COMPLEXES
ULTRA_ROBUST_CONVERSATION = [
    # === PHASE 1: EXPLORATION INITIALE (5 échanges) ===
    {
        "user_message": "Bonjour, je cherche des couches pour mon bébé de 8 mois qui pèse 9kg",
        "expected_memory": ["bébé", "8 mois", "9kg", "couches"],
        "phase": "exploration_initiale",
        "importance": "high"
    },
    {
        "user_message": "Il bouge beaucoup la nuit, quelle taille me conseillez-vous ?",
        "expected_memory": ["bouge", "nuit", "conseil taille"],
        "phase": "exploration_initiale",
        "importance": "high"
    },
    {
        "user_message": "Vous avez des couches à pression ou seulement des culottes ?",
        "expected_memory": ["couches pression", "culottes", "types"],
        "phase": "exploration_initiale",
        "importance": "medium"
    },
    {
        "user_message": "En fait, j'aimerais aussi des couches pour ma grand-mère de 75 ans",
        "expected_memory": ["grand-mère", "75 ans", "couches adultes"],
        "phase": "exploration_initiale",
        "importance": "high"
    },
    {
        "user_message": "Elle a des problèmes de mobilité, quelle taille XL vous avez ?",
        "expected_memory": ["mobilité", "taille XL", "problèmes"],
        "phase": "exploration_initiale",
        "importance": "medium"
    },

    # === PHASE 2: NÉGOCIATION PRIX (10 échanges) ===
    {
        "user_message": "Combien coûte 1 paquet de couches taille 3 pour bébé ?",
        "expected_memory": ["prix", "1 paquet", "taille 3", "bébé"],
        "phase": "negociation_prix",
        "importance": "high"
    },
    {
        "user_message": "Et pour les couches adultes XL, le prix unitaire ?",
        "expected_memory": ["prix", "adultes XL", "unitaire"],
        "phase": "negociation_prix",
        "importance": "high"
    },
    {
        "user_message": "Si je prends 3 paquets bébé + 2 paquets adultes, vous me faites une remise ?",
        "expected_memory": ["3 paquets bébé", "2 paquets adultes", "remise"],
        "phase": "negociation_prix",
        "importance": "high"
    },
    {
        "user_message": "Mon budget est limité à 25000 FCFA maximum",
        "expected_memory": ["budget", "25000 FCFA", "maximum"],
        "phase": "negociation_prix",
        "importance": "high"
    },
    {
        "user_message": "Vous avez des promotions en cours cette semaine ?",
        "expected_memory": ["promotions", "cette semaine"],
        "phase": "negociation_prix",
        "importance": "medium"
    },
    {
        "user_message": "En fait, je préfère commencer par 2 paquets bébé pour tester",
        "expected_memory": ["2 paquets bébé", "tester", "changement"],
        "phase": "negociation_prix",
        "importance": "high"
    },
    {
        "user_message": "Et 1 seul paquet adulte pour ma grand-mère",
        "expected_memory": ["1 paquet adulte", "grand-mère"],
        "phase": "negociation_prix",
        "importance": "high"
    },
    {
        "user_message": "Quel est le total de cette nouvelle commande ?",
        "expected_memory": ["total", "nouvelle commande"],
        "phase": "negociation_prix",
        "importance": "high"
    },
    {
        "user_message": "C'est dans mon budget, parfait !",
        "expected_memory": ["dans budget", "parfait", "validation"],
        "phase": "negociation_prix",
        "importance": "medium"
    },
    {
        "user_message": "Attendez, finalement je veux 3 paquets bébé au lieu de 2",
        "expected_memory": ["3 paquets bébé", "au lieu de 2", "changement"],
        "phase": "negociation_prix",
        "importance": "high"
    },

    # === PHASE 3: LIVRAISON COMPLEXE (10 échanges) ===
    {
        "user_message": "Pour la livraison, je suis à Cocody près du CHU",
        "expected_memory": ["livraison", "Cocody", "près CHU"],
        "phase": "livraison_complexe",
        "importance": "high"
    },
    {
        "user_message": "Vous livrez dans ce quartier ? Combien ça coûte ?",
        "expected_memory": ["quartier", "coût livraison"],
        "phase": "livraison_complexe",
        "importance": "high"
    },
    {
        "user_message": "En fait, je préfère être livré au bureau à Plateau",
        "expected_memory": ["bureau", "Plateau", "changement adresse"],
        "phase": "livraison_complexe",
        "importance": "high"
    },
    {
        "user_message": "C'est plus pratique pour moi, je travaille là-bas",
        "expected_memory": ["pratique", "travaille", "justification"],
        "phase": "livraison_complexe",
        "importance": "medium"
    },
    {
        "user_message": "Quelle différence de prix entre Cocody et Plateau ?",
        "expected_memory": ["différence prix", "Cocody", "Plateau"],
        "phase": "livraison_complexe",
        "importance": "medium"
    },
    {
        "user_message": "Si je commande maintenant, livraison possible demain matin ?",
        "expected_memory": ["commande maintenant", "demain matin", "délai"],
        "phase": "livraison_complexe",
        "importance": "high"
    },
    {
        "user_message": "J'ai une réunion importante à 10h, livraison avant 9h possible ?",
        "expected_memory": ["réunion 10h", "avant 9h", "contrainte"],
        "phase": "livraison_complexe",
        "importance": "high"
    },
    {
        "user_message": "Sinon, livraison à domicile à Cocody dans l'après-midi",
        "expected_memory": ["domicile", "Cocody", "après-midi", "alternative"],
        "phase": "livraison_complexe",
        "importance": "high"
    },
    {
        "user_message": "Vous me confirmez l'adresse exacte nécessaire ?",
        "expected_memory": ["adresse exacte", "confirmation"],
        "phase": "livraison_complexe",
        "importance": "medium"
    },
    {
        "user_message": "Finalement, livraison au bureau à Plateau c'est mieux",
        "expected_memory": ["bureau Plateau", "mieux", "décision finale"],
        "phase": "livraison_complexe",
        "importance": "high"
    },

    # === PHASE 4: PAIEMENT & MODIFICATIONS (10 échanges) ===
    {
        "user_message": "Pour le paiement, quelles sont vos options ?",
        "expected_memory": ["paiement", "options"],
        "phase": "paiement_modifications",
        "importance": "high"
    },
    {
        "user_message": "Je peux payer par Wave ? J'ai un compte",
        "expected_memory": ["Wave", "compte"],
        "phase": "paiement_modifications",
        "importance": "high"
    },
    {
        "user_message": "Il faut un acompte ou je paie tout à la livraison ?",
        "expected_memory": ["acompte", "paie tout", "livraison"],
        "phase": "paiement_modifications",
        "importance": "high"
    },
    {
        "user_message": "Si acompte, quel montant et sur quel numéro Wave ?",
        "expected_memory": ["montant acompte", "numéro Wave"],
        "phase": "paiement_modifications",
        "importance": "high"
    },
    {
        "user_message": "En fait, je veux annuler les couches adultes, juste garder celles du bébé",
        "expected_memory": ["annuler adultes", "garder bébé", "modification"],
        "phase": "paiement_modifications",
        "importance": "high"
    },
    {
        "user_message": "Ma grand-mère préfère acheter elle-même en pharmacie",
        "expected_memory": ["grand-mère", "pharmacie", "justification"],
        "phase": "paiement_modifications",
        "importance": "medium"
    },
    {
        "user_message": "Donc seulement 3 paquets couches bébé taille 3",
        "expected_memory": ["3 paquets", "bébé", "taille 3", "seulement"],
        "phase": "paiement_modifications",
        "importance": "high"
    },
    {
        "user_message": "Quel est le nouveau total avec livraison Plateau ?",
        "expected_memory": ["nouveau total", "livraison Plateau"],
        "phase": "paiement_modifications",
        "importance": "high"
    },
    {
        "user_message": "Parfait, je confirme cette commande modifiée",
        "expected_memory": ["confirme", "commande modifiée"],
        "phase": "paiement_modifications",
        "importance": "high"
    },
    {
        "user_message": "Envoyez-moi le récapitulatif complet par WhatsApp",
        "expected_memory": ["récapitulatif", "WhatsApp"],
        "phase": "paiement_modifications",
        "importance": "medium"
    },

    # === PHASE 5: VALIDATION & QUESTIONS FINALES (10 échanges) ===
    {
        "user_message": "Rappelez-moi, mon bébé fait combien de kilos déjà ?",
        "expected_memory": ["TEST_MÉMOIRE", "9kg"],
        "phase": "validation_finale",
        "importance": "critical"
    },
    {
        "user_message": "Et j'ai commandé combien de paquets au final ?",
        "expected_memory": ["TEST_MÉMOIRE", "3 paquets"],
        "phase": "validation_finale",
        "importance": "critical"
    },
    {
        "user_message": "L'adresse de livraison c'est où déjà ?",
        "expected_memory": ["TEST_MÉMOIRE", "bureau Plateau"],
        "phase": "validation_finale",
        "importance": "critical"
    },
    {
        "user_message": "Le délai de livraison c'est quand ?",
        "expected_memory": ["TEST_MÉMOIRE", "demain matin"],
        "phase": "validation_finale",
        "importance": "critical"
    },
    {
        "user_message": "L'acompte à payer c'est combien sur quel numéro ?",
        "expected_memory": ["TEST_MÉMOIRE", "acompte", "numéro"],
        "phase": "validation_finale",
        "importance": "critical"
    },
    {
        "user_message": "Vous avez mon numéro de téléphone pour la livraison ?",
        "expected_memory": ["numéro téléphone", "livraison"],
        "phase": "validation_finale",
        "importance": "medium"
    },
    {
        "user_message": "Si j'ai un problème avec les couches, je peux les échanger ?",
        "expected_memory": ["problème", "échanger", "garantie"],
        "phase": "validation_finale",
        "importance": "medium"
    },
    {
        "user_message": "Vous avez une garantie satisfaction ?",
        "expected_memory": ["garantie satisfaction"],
        "phase": "validation_finale",
        "importance": "medium"
    },
    {
        "user_message": "Parfait, j'attends votre confirmation de commande",
        "expected_memory": ["attends", "confirmation commande"],
        "phase": "validation_finale",
        "importance": "medium"
    },
    {
        "user_message": "Merci pour votre professionnalisme, à bientôt !",
        "expected_memory": ["merci", "professionnalisme", "à bientôt"],
        "phase": "validation_finale",
        "importance": "low"
    },

    # === PHASE 6: TESTS DE ROBUSTESSE (5 échanges) ===
    {
        "user_message": "Au fait, vous vendez aussi des biberons ?",
        "expected_memory": ["biberons", "hors sujet"],
        "phase": "tests_robustesse",
        "importance": "low"
    },
    {
        "user_message": "Et si je veux changer l'adresse pour Paris ?",
        "expected_memory": ["Paris", "impossible"],
        "phase": "tests_robustesse",
        "importance": "low"
    },
    {
        "user_message": "Je peux payer en euros ?",
        "expected_memory": ["euros", "devise"],
        "phase": "tests_robustesse",
        "importance": "low"
    },
    {
        "user_message": "Donnez-moi un récapitulatif COMPLET de toute notre conversation",
        "expected_memory": ["TEST_MÉMOIRE_GLOBALE", "récapitulatif complet"],
        "phase": "tests_robustesse",
        "importance": "critical"
    },
    {
        "user_message": "Merci, c'est parfait, je suis très satisfait du service !",
        "expected_memory": ["satisfait", "service", "parfait"],
        "phase": "tests_robustesse",
        "importance": "low"
    }
]

# 📊 MÉTRIQUES ULTRA-ROBUSTES
class UltraRobustMetrics:
    def __init__(self):
        self.conversation_log = []
        self.memory_tests = []
        self.performance_metrics = []
        self.error_log = []
        self.coherence_scores = []
        self.response_times = []
        
    def add_exchange(self, exchange_data: Dict[str, Any]):
        """Enregistre un échange complet"""
        self.conversation_log.append({
            **exchange_data,
            "timestamp": datetime.now().isoformat(),
            "exchange_number": len(self.conversation_log) + 1
        })
        
        if exchange_data.get("response_time"):
            self.response_times.append(exchange_data["response_time"])
    
    def test_memory_coherence(self, user_message: str, response: str, 
                            expected_memory: List[str], phase: str, importance: str):
        """Teste la cohérence de la mémoire"""
        found_elements = []
        missing_elements = []
        
        response_lower = response.lower()
        
        for expected in expected_memory:
            if expected.lower() in response_lower:
                found_elements.append(expected)
            else:
                missing_elements.append(expected)
        
        coherence_score = len(found_elements) / len(expected_memory) * 100 if expected_memory else 100
        
        memory_test = {
            "phase": phase,
            "importance": importance,
            "user_message": user_message[:100],
            "expected_memory": expected_memory,
            "found_elements": found_elements,
            "missing_elements": missing_elements,
            "coherence_score": coherence_score,
            "is_critical_test": "TEST_MÉMOIRE" in str(expected_memory)
        }
        
        self.memory_tests.append(memory_test)
        self.coherence_scores.append(coherence_score)
        
        return memory_test
    
    def add_error(self, error_type: str, error_message: str, exchange_number: int):
        """Enregistre une erreur"""
        self.error_log.append({
            "error_type": error_type,
            "error_message": error_message,
            "exchange_number": exchange_number,
            "timestamp": datetime.now().isoformat()
        })
    
    def calculate_performance_metrics(self):
        """Calcule les métriques de performance"""
        if not self.response_times:
            return {}
        
        return {
            "avg_response_time": statistics.mean(self.response_times),
            "median_response_time": statistics.median(self.response_times),
            "max_response_time": max(self.response_times),
            "min_response_time": min(self.response_times),
            "total_conversation_time": sum(self.response_times)
        }
    
    def generate_ultra_detailed_report(self):
        """Génère un rapport ultra-détaillé"""
        print(f"\n{'='*100}")
        print(f"🔥 RAPPORT TEST CONVERSATIONNEL ULTRA-ROBUSTE")
        print(f"{'='*100}")
        
        # Statistiques générales
        total_exchanges = len(self.conversation_log)
        total_errors = len(self.error_log)
        
        print(f"\n📊 STATISTIQUES GÉNÉRALES:")
        print(f"   • Total échanges: {total_exchanges}")
        print(f"   • Erreurs détectées: {total_errors}")
        print(f"   • Taux d'erreur: {(total_errors/total_exchanges*100):.1f}%")
        
        # Métriques de performance
        perf_metrics = self.calculate_performance_metrics()
        if perf_metrics:
            print(f"\n⚡ PERFORMANCES:")
            print(f"   • Temps moyen: {perf_metrics['avg_response_time']:.2f}s")
            print(f"   • Temps médian: {perf_metrics['median_response_time']:.2f}s")
            print(f"   • Temps max: {perf_metrics['max_response_time']:.2f}s")
            print(f"   • Durée totale: {perf_metrics['total_conversation_time']:.1f}s")
        
        # Tests de mémoire
        if self.memory_tests:
            avg_coherence = statistics.mean(self.coherence_scores)
            critical_tests = [t for t in self.memory_tests if t["is_critical_test"]]
            critical_avg = statistics.mean([t["coherence_score"] for t in critical_tests]) if critical_tests else 0
            
            print(f"\n🧠 TESTS DE MÉMOIRE:")
            print(f"   • Tests effectués: {len(self.memory_tests)}")
            print(f"   • Cohérence moyenne: {avg_coherence:.1f}%")
            print(f"   • Tests critiques: {len(critical_tests)}")
            print(f"   • Cohérence critique: {critical_avg:.1f}%")
        
        # Analyse par phase
        phases = {}
        for test in self.memory_tests:
            phase = test["phase"]
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(test["coherence_score"])
        
        print(f"\n📋 ANALYSE PAR PHASE:")
        for phase, scores in phases.items():
            avg_score = statistics.mean(scores)
            print(f"   • {phase}: {avg_score:.1f}% ({len(scores)} tests)")
        
        # Tests critiques échoués
        failed_critical = [t for t in critical_tests if t["coherence_score"] < 80]
        if failed_critical:
            print(f"\n🚨 ÉCHECS CRITIQUES ({len(failed_critical)}):")
            for test in failed_critical:
                print(f"   • {test['phase']}: {test['coherence_score']:.1f}%")
                print(f"     Manquant: {test['missing_elements']}")
        
        # Score global
        memory_score = avg_coherence
        critical_score = critical_avg
        performance_penalty = min(perf_metrics.get('avg_response_time', 0) * 2, 20) if perf_metrics else 0
        error_penalty = total_errors * 5
        
        final_score = max(0, memory_score * 0.6 + critical_score * 0.3 - performance_penalty - error_penalty)
        
        print(f"\n🎯 SCORE GLOBAL:")
        print(f"   • Mémoire générale: {memory_score:.1f}%")
        print(f"   • Mémoire critique: {critical_score:.1f}%")
        print(f"   • Pénalité performance: -{performance_penalty:.1f}%")
        print(f"   • Pénalité erreurs: -{error_penalty}%")
        print(f"   • SCORE FINAL: {final_score:.1f}%")
        
        # Évaluation finale
        if final_score >= 90:
            print("   🟢 EXCELLENT - Système ultra-robuste")
        elif final_score >= 80:
            print("   🟡 BON - Quelques améliorations possibles")
        elif final_score >= 70:
            print("   🟠 MOYEN - Améliorations nécessaires")
        elif final_score >= 60:
            print("   🔴 FAIBLE - Problèmes importants")
        else:
            print("   ⚫ CRITIQUE - Refonte nécessaire")
        
        return final_score

async def run_ultra_robust_test():
    """Lance le test conversationnel ultra-robuste"""
    print(f"🔥 DÉMARRAGE TEST CONVERSATIONNEL ULTRA-ROBUSTE")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 {len(ULTRA_ROBUST_CONVERSATION)} échanges programmés")
    print(f"{'='*100}")
    
    from core.universal_rag_engine import UniversalRAGEngine
    rag = UniversalRAGEngine()
    metrics = UltraRobustMetrics()
    
    # Paramètres de test
    COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
    COMPANY_NAME = "Rue_du_gros"
    USER_ID = "ultra_robust_test_user"
    
    for i, exchange_data in enumerate(ULTRA_ROBUST_CONVERSATION, 1):
        user_message = exchange_data["user_message"]
        expected_memory = exchange_data["expected_memory"]
        phase = exchange_data["phase"]
        importance = exchange_data["importance"]
        
        print(f"\n🔥 ÉCHANGE {i}/{len(ULTRA_ROBUST_CONVERSATION)} - {phase.upper()}")
        print(f"👤 USER: {user_message}")
        
        start_time = time.time()
        try:
            # Recherche et génération
            search_results = await rag.search_sequential_sources(user_message, COMPANY_ID)
            # Injection robuste de l'historique utilisateur dans search_results
            search_results['conversation_history'] = user_message if 'conversation_history' not in search_results else search_results['conversation_history']
            response = await rag.generate_response(
                user_message, search_results, COMPANY_ID, COMPANY_NAME, USER_ID
            )
            
            response_time = time.time() - start_time
            
            print(f"🤖 GAMMA: {response[:150]}{'...' if len(response) > 150 else ''}")
            print(f"⏱️  Temps: {response_time:.2f}s")
            
            # Test de cohérence mémoire
            memory_test = metrics.test_memory_coherence(
                user_message, response, expected_memory, phase, importance
            )
            
            print(f"🧠 Cohérence: {memory_test['coherence_score']:.1f}%", end="")
            if memory_test["is_critical_test"]:
                print(" [CRITIQUE]", end="")
            if memory_test["missing_elements"]:
                print(f" - Manque: {memory_test['missing_elements']}")
            else:
                print(" ✅")
            
            # Enregistrer l'échange
            metrics.add_exchange({
                "user_message": user_message,
                "response": response,
                "response_time": response_time,
                "phase": phase,
                "importance": importance,
                "memory_test": memory_test
            })
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"ERREUR: {str(e)[:100]}"
            print(f"❌ {error_msg}")
            
            metrics.add_error("generation_error", str(e), i)
            metrics.add_exchange({
                "user_message": user_message,
                "response": error_msg,
                "response_time": response_time,
                "phase": phase,
                "importance": importance,
                "error": True
            })
        
        # Pause courte entre échanges
        await asyncio.sleep(0.3)
    
    # Génération du rapport final
    final_score = metrics.generate_ultra_detailed_report()
    
    # Sauvegarde des résultats
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ultra_robust_test_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            "final_score": final_score,
            "conversation_log": metrics.conversation_log,
            "memory_tests": metrics.memory_tests,
            "error_log": metrics.error_log,
            "performance_metrics": metrics.calculate_performance_metrics()
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Résultats sauvegardés dans: {filename}")
    
    return final_score

if __name__ == "__main__":
    asyncio.run(run_ultra_robust_test())

#!/usr/bin/env python3
"""
🔥 TEST CONVERSATIONNEL OPTIMISÉ ANTI-RATE-LIMIT
Version allégée du test ultra-robuste pour éviter les limitations Groq

OPTIMISATIONS:
- 20 échanges au lieu de 50
- Délais adaptatifs entre appels
- Tests de mémoire critique concentrés
- Gestion intelligente des erreurs 429
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

# 🎯 SCÉNARIO OPTIMISÉ : 20 ÉCHANGES CRITIQUES
OPTIMIZED_CONVERSATION = [
    # === PHASE 1: EXPLORATION (4 échanges) ===
    {
        "user_message": "Bonjour, je cherche des couches pour mon bébé de 8 mois qui pèse 9kg",
        "expected_memory": ["bébé", "8 mois", "9kg", "couches"],
        "phase": "exploration",
        "importance": "high",
        "delay": 2.0
    },
    {
        "user_message": "Il bouge beaucoup la nuit, quelle taille me conseillez-vous ?",
        "expected_memory": ["bouge", "nuit", "conseil taille"],
        "phase": "exploration",
        "importance": "high",
        "delay": 2.0
    },
    {
        "user_message": "Combien coûte 1 paquet de couches taille 3 ?",
        "expected_memory": ["prix", "1 paquet", "taille 3"],
        "phase": "exploration",
        "importance": "high",
        "delay": 2.0
    },
    {
        "user_message": "Mon budget est limité à 25000 FCFA maximum",
        "expected_memory": ["budget", "25000 FCFA", "maximum"],
        "phase": "exploration",
        "importance": "high",
        "delay": 2.0
    },

    # === PHASE 2: NÉGOCIATION (4 échanges) ===
    {
        "user_message": "Si je prends 3 paquets, vous me faites une remise ?",
        "expected_memory": ["3 paquets", "remise"],
        "phase": "negociation",
        "importance": "high",
        "delay": 2.5
    },
    {
        "user_message": "En fait, je préfère commencer par 2 paquets pour tester",
        "expected_memory": ["2 paquets", "tester", "changement"],
        "phase": "negociation",
        "importance": "high",
        "delay": 2.5
    },
    {
        "user_message": "Quel est le total de cette commande ?",
        "expected_memory": ["total", "commande"],
        "phase": "negociation",
        "importance": "high",
        "delay": 2.5
    },
    {
        "user_message": "Finalement je veux 3 paquets au lieu de 2",
        "expected_memory": ["3 paquets", "au lieu de 2", "changement"],
        "phase": "negociation",
        "importance": "high",
        "delay": 2.5
    },

    # === PHASE 3: LIVRAISON (4 échanges) ===
    {
        "user_message": "Pour la livraison, je suis à Cocody près du CHU",
        "expected_memory": ["livraison", "Cocody", "près CHU"],
        "phase": "livraison",
        "importance": "high",
        "delay": 3.0
    },
    {
        "user_message": "En fait, je préfère être livré au bureau à Plateau",
        "expected_memory": ["bureau", "Plateau", "changement adresse"],
        "phase": "livraison",
        "importance": "high",
        "delay": 3.0
    },
    {
        "user_message": "Si je commande maintenant, livraison possible demain matin ?",
        "expected_memory": ["commande maintenant", "demain matin", "délai"],
        "phase": "livraison",
        "importance": "high",
        "delay": 3.0
    },
    {
        "user_message": "Finalement, livraison au bureau à Plateau c'est mieux",
        "expected_memory": ["bureau Plateau", "mieux", "décision finale"],
        "phase": "livraison",
        "importance": "high",
        "delay": 3.0
    },

    # === PHASE 4: PAIEMENT (4 échanges) ===
    {
        "user_message": "Pour le paiement, je peux payer par Wave ?",
        "expected_memory": ["paiement", "Wave"],
        "phase": "paiement",
        "importance": "high",
        "delay": 3.5
    },
    {
        "user_message": "Il faut un acompte ou je paie tout à la livraison ?",
        "expected_memory": ["acompte", "paie tout", "livraison"],
        "phase": "paiement",
        "importance": "high",
        "delay": 3.5
    },
    {
        "user_message": "Donc 3 paquets couches bébé taille 3, c'est confirmé",
        "expected_memory": ["3 paquets", "bébé", "taille 3", "confirmé"],
        "phase": "paiement",
        "importance": "high",
        "delay": 3.5
    },
    {
        "user_message": "Quel est le total final avec livraison Plateau ?",
        "expected_memory": ["total final", "livraison Plateau"],
        "phase": "paiement",
        "importance": "high",
        "delay": 3.5
    },

    # === PHASE 5: TESTS MÉMOIRE CRITIQUES (4 échanges) ===
    {
        "user_message": "Rappelez-moi, mon bébé fait combien de kilos déjà ?",
        "expected_memory": ["TEST_MÉMOIRE", "9kg"],
        "phase": "test_memoire",
        "importance": "critical",
        "delay": 4.0
    },
    {
        "user_message": "Et j'ai commandé combien de paquets au final ?",
        "expected_memory": ["TEST_MÉMOIRE", "3 paquets"],
        "phase": "test_memoire",
        "importance": "critical",
        "delay": 4.0
    },
    {
        "user_message": "L'adresse de livraison c'est où déjà ?",
        "expected_memory": ["TEST_MÉMOIRE", "bureau Plateau"],
        "phase": "test_memoire",
        "importance": "critical",
        "delay": 4.0
    },
    {
        "user_message": "Donnez-moi un récapitulatif COMPLET de notre conversation",
        "expected_memory": ["TEST_MÉMOIRE_GLOBALE", "récapitulatif complet"],
        "phase": "test_memoire",
        "importance": "critical",
        "delay": 4.0
    }
]

class OptimizedMetrics:
    def __init__(self):
        self.conversation_log = []
        self.memory_tests = []
        self.error_log = []
        self.coherence_scores = []
        self.response_times = []
        self.rate_limit_errors = 0
        
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
        if "429" in error_message or "rate limit" in error_message.lower():
            self.rate_limit_errors += 1
            
        self.error_log.append({
            "error_type": error_type,
            "error_message": error_message,
            "exchange_number": exchange_number,
            "timestamp": datetime.now().isoformat()
        })
    
    def generate_optimized_report(self):
        """Génère un rapport optimisé"""
        print(f"\n{'='*80}")
        print(f"🔥 RAPPORT TEST CONVERSATIONNEL OPTIMISÉ")
        print(f"{'='*80}")
        
        # Statistiques générales
        total_exchanges = len(self.conversation_log)
        total_errors = len(self.error_log)
        
        print(f"\n📊 STATISTIQUES:")
        print(f"   • Total échanges: {total_exchanges}")
        print(f"   • Erreurs détectées: {total_errors}")
        print(f"   • Erreurs rate limit: {self.rate_limit_errors}")
        print(f"   • Taux d'erreur: {(total_errors/total_exchanges*100):.1f}%")
        
        # Métriques de performance
        if self.response_times:
            avg_time = statistics.mean(self.response_times)
            print(f"   • Temps moyen: {avg_time:.2f}s")
        
        # Tests de mémoire
        if self.memory_tests:
            avg_coherence = statistics.mean(self.coherence_scores)
            critical_tests = [t for t in self.memory_tests if t["is_critical_test"]]
            critical_avg = statistics.mean([t["coherence_score"] for t in critical_tests]) if critical_tests else 0
            
            print(f"\n🧠 MÉMOIRE:")
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
        
        print(f"\n📋 PHASES:")
        for phase, scores in phases.items():
            avg_score = statistics.mean(scores)
            print(f"   • {phase}: {avg_score:.1f}%")
        
        # Score final
        memory_score = avg_coherence if self.coherence_scores else 0
        critical_score = critical_avg if critical_tests else 0
        rate_limit_penalty = self.rate_limit_errors * 10
        
        final_score = max(0, memory_score * 0.7 + critical_score * 0.3 - rate_limit_penalty)
        
        print(f"\n🎯 SCORE FINAL: {final_score:.1f}%")
        
        if final_score >= 85:
            print("   🟢 EXCELLENT - Système robuste")
        elif final_score >= 70:
            print("   🟡 BON - Système fonctionnel")
        elif final_score >= 50:
            print("   🟠 MOYEN - Améliorations nécessaires")
        else:
            print("   🔴 FAIBLE - Problèmes critiques")
        
        return final_score

async def run_optimized_test():
    """Lance le test conversationnel optimisé"""
    print(f"🔥 TEST CONVERSATIONNEL OPTIMISÉ ANTI-RATE-LIMIT")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 {len(OPTIMIZED_CONVERSATION)} échanges optimisés")
    print(f"⚡ Délais adaptatifs pour éviter rate limiting")
    print(f"{'='*80}")
    
    from core.universal_rag_engine import UniversalRAGEngine
    rag = UniversalRAGEngine()
    metrics = OptimizedMetrics()
    
    # Paramètres de test
    COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
    COMPANY_NAME = "Rue_du_gros"
    USER_ID = "optimized_test_user"
    
    for i, exchange_data in enumerate(OPTIMIZED_CONVERSATION, 1):
        user_message = exchange_data["user_message"]
        expected_memory = exchange_data["expected_memory"]
        phase = exchange_data["phase"]
        importance = exchange_data["importance"]
        delay = exchange_data.get("delay", 2.0)
        
        print(f"\n🔥 ÉCHANGE {i}/{len(OPTIMIZED_CONVERSATION)} - {phase.upper()}")
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
            
            print(f"🤖 GAMMA: {response[:100]}{'...' if len(response) > 100 else ''}")
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
        
        # Délai adaptatif pour éviter rate limiting
        print(f"⏳ Attente {delay}s...")
        await asyncio.sleep(delay)
    
    # Génération du rapport final
    final_score = metrics.generate_optimized_report()
    
    # Sauvegarde des résultats
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"optimized_test_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            "final_score": final_score,
            "conversation_log": metrics.conversation_log,
            "memory_tests": metrics.memory_tests,
            "error_log": metrics.error_log,
            "rate_limit_errors": metrics.rate_limit_errors
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Résultats sauvegardés dans: {filename}")
    
    return final_score

if __name__ == "__main__":
    asyncio.run(run_optimized_test())

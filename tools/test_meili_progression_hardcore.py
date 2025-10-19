#!/usr/bin/env python3
"""
🔥 TEST CONVERSATIONNEL MEILISEARCH - NIVEAU HARDCORE
Test ultra-complet avec changements d'avis et ambiguïtés multiples

OBJECTIFS:
1. Valider rescoring + filtrage + extraction + ambiguïté sur scénario complexe
2. Tester progression avec changements d'avis multiples
3. Valider mémoire conversationnelle et bloc-note
4. 25 échanges hardcore pour MeiliSearch (full-text)
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

# 🎯 SCÉNARIO HARDCORE : 25 ÉCHANGES COMPLEXES
MEILI_CONVERSATION_HARDCORE = [
    # === PHASE 1: EXPLORATION AMBIGUË (5 échanges) ===
    {
        "user_message": "couches",
        "expected_keywords": ["culottes", "pression", "type"],
        "phase": "exploration_ambigue",
        "importance": "critical",
        "delay": 2.0,
        "expect_ambiguity": True
    },
    {
        "user_message": "culottes",
        "expected_keywords": ["culottes", "lot", "taille"],
        "phase": "exploration_ambigue",
        "importance": "high",
        "delay": 2.0,
        "expect_ambiguity": False
    },
    {
        "user_message": "lot 150",
        "expected_keywords": ["13500", "150", "taille"],
        "phase": "exploration_ambigue",
        "importance": "high",
        "delay": 2.0,
        "expect_ambiguity": False
    },
    {
        "user_message": "taille",
        "expected_keywords": ["taille", "3", "4", "5", "6"],
        "phase": "exploration_ambigue",
        "importance": "high",
        "delay": 2.0,
        "expect_ambiguity": True
    },
    {
        "user_message": "taille 5",
        "expected_keywords": ["taille 5", "12", "18 kg"],
        "phase": "exploration_ambigue",
        "importance": "high",
        "delay": 2.0,
        "expect_ambiguity": False
    },

    # === PHASE 2: NÉGOCIATION PRIX (5 échanges) ===
    {
        "user_message": "prix",
        "expected_keywords": ["13500", "lot 150", "fcfa"],
        "phase": "negociation_prix",
        "importance": "high",
        "delay": 2.5,
        "expect_ambiguity": False
    },
    {
        "user_message": "remise",
        "expected_keywords": ["remise", "prix", "fixe"],
        "phase": "negociation_prix",
        "importance": "medium",
        "delay": 2.5,
        "expect_ambiguity": False
    },
    {
        "user_message": "lot 300",
        "expected_keywords": ["22900", "300", "taille"],
        "phase": "negociation_prix",
        "importance": "high",
        "delay": 2.5,
        "expect_ambiguity": False
    },
    {
        "user_message": "finalement lot 150",
        "expected_keywords": ["13500", "150", "changement"],
        "phase": "negociation_prix",
        "importance": "critical",
        "delay": 2.5,
        "expect_ambiguity": False
    },
    {
        "user_message": "total",
        "expected_keywords": ["13500", "total", "livraison"],
        "phase": "negociation_prix",
        "importance": "high",
        "delay": 2.5,
        "expect_ambiguity": False
    },

    # === PHASE 3: LIVRAISON COMPLEXE (6 échanges) ===
    {
        "user_message": "livraison",
        "expected_keywords": ["livraison", "zone", "commune"],
        "phase": "livraison_complexe",
        "importance": "high",
        "delay": 3.0,
        "expect_ambiguity": True
    },
    {
        "user_message": "Yopougon",
        "expected_keywords": ["Yopougon", "1500", "fcfa"],
        "phase": "livraison_complexe",
        "importance": "high",
        "delay": 3.0,
        "expect_ambiguity": False
    },
    {
        "user_message": "Plateau",
        "expected_keywords": ["Plateau", "1500", "fcfa"],
        "phase": "livraison_complexe",
        "importance": "high",
        "delay": 3.0,
        "expect_ambiguity": False
    },
    {
        "user_message": "différence prix",
        "expected_keywords": ["même", "1500", "Abidjan"],
        "phase": "livraison_complexe",
        "importance": "medium",
        "delay": 3.0,
        "expect_ambiguity": False
    },
    {
        "user_message": "Cocody finalement",
        "expected_keywords": ["Cocody", "1500", "changement"],
        "phase": "livraison_complexe",
        "importance": "critical",
        "delay": 3.0,
        "expect_ambiguity": False
    },
    {
        "user_message": "délai livraison",
        "expected_keywords": ["3h", "acompte", "rapide"],
        "phase": "livraison_complexe",
        "importance": "high",
        "delay": 3.0,
        "expect_ambiguity": False
    },

    # === PHASE 4: PAIEMENT & MODIFICATIONS (5 échanges) ===
    {
        "user_message": "paiement",
        "expected_keywords": ["Wave", "acompte", "2000"],
        "phase": "paiement_modifications",
        "importance": "high",
        "delay": 3.5,
        "expect_ambiguity": False
    },
    {
        "user_message": "numéro Wave",
        "expected_keywords": ["0787360757", "Wave", "acompte"],
        "phase": "paiement_modifications",
        "importance": "high",
        "delay": 3.5,
        "expect_ambiguity": False
    },
    {
        "user_message": "acompte obligatoire",
        "expected_keywords": ["2000", "obligatoire", "fcfa"],
        "phase": "paiement_modifications",
        "importance": "high",
        "delay": 3.5,
        "expect_ambiguity": False
    },
    {
        "user_message": "total final",
        "expected_keywords": ["15000", "13500", "1500"],
        "phase": "paiement_modifications",
        "importance": "critical",
        "delay": 3.5,
        "expect_ambiguity": False
    },
    {
        "user_message": "contact WhatsApp",
        "expected_keywords": ["0160924560", "WhatsApp", "contact"],
        "phase": "paiement_modifications",
        "importance": "high",
        "delay": 3.5,
        "expect_ambiguity": False
    },

    # === PHASE 5: VALIDATION & MÉMOIRE (4 échanges) ===
    {
        "user_message": "rappel commande",
        "expected_keywords": ["lot 150", "taille 5", "Cocody"],
        "phase": "validation_memoire",
        "importance": "critical",
        "delay": 4.0,
        "expect_ambiguity": False
    },
    {
        "user_message": "prix total rappel",
        "expected_keywords": ["15000", "13500", "1500"],
        "phase": "validation_memoire",
        "importance": "critical",
        "delay": 4.0,
        "expect_ambiguity": False
    },
    {
        "user_message": "récapitulatif complet",
        "expected_keywords": ["lot 150", "taille 5", "Cocody", "15000", "Wave"],
        "phase": "validation_memoire",
        "importance": "critical",
        "delay": 4.0,
        "expect_ambiguity": False
    },
    {
        "user_message": "je confirme commande",
        "expected_keywords": ["acompte", "2000", "Wave", "0787360757"],
        "phase": "validation_memoire",
        "importance": "critical",
        "delay": 4.0,
        "expect_ambiguity": False
    }
]

class HardcoreMetrics:
    def __init__(self):
        self.conversation_log = []
        self.keyword_tests = []
        self.ambiguity_tests = []
        self.error_log = []
        self.response_times = []
        self.progression_scores = []
        self.memory_scores = []
        
    def add_exchange(self, exchange_data: Dict[str, Any]):
        """Enregistre un échange complet"""
        self.conversation_log.append({
            **exchange_data,
            "timestamp": datetime.now().isoformat(),
            "exchange_number": len(self.conversation_log) + 1
        })
        
        if exchange_data.get("response_time"):
            self.response_times.append(exchange_data["response_time"])
    
    def test_keywords_and_ambiguity(self, user_message: str, response: str, 
                                   expected_keywords: List[str], phase: str, 
                                   importance: str, expect_ambiguity: bool):
        """Teste mots-clés + ambiguïté"""
        found_keywords = []
        missing_keywords = []
        
        response_lower = response.lower()
        
        for keyword in expected_keywords:
            if keyword.lower() in response_lower:
                found_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)
        
        keyword_score = len(found_keywords) / len(expected_keywords) * 100 if expected_keywords else 100
        
        # Vérifier progression
        has_progression = "?" in response
        
        # Vérifier ambiguïté
        has_ambiguity = any(word in response_lower for word in ["préciser", "type", "quelle", "quel"])
        ambiguity_correct = (has_ambiguity == expect_ambiguity)
        
        keyword_test = {
            "phase": phase,
            "importance": importance,
            "user_message": user_message,
            "expected_keywords": expected_keywords,
            "found_keywords": found_keywords,
            "missing_keywords": missing_keywords,
            "keyword_score": keyword_score,
            "has_progression": has_progression,
            "expect_ambiguity": expect_ambiguity,
            "has_ambiguity": has_ambiguity,
            "ambiguity_correct": ambiguity_correct
        }
        
        self.keyword_tests.append(keyword_test)
        self.progression_scores.append(1 if has_progression else 0)
        
        if expect_ambiguity:
            self.ambiguity_tests.append(keyword_test)
        
        # Test mémoire pour phase validation
        if phase == "validation_memoire":
            self.memory_scores.append(keyword_score)
        
        return keyword_test
    
    def add_error(self, error_type: str, error_message: str, exchange_number: int):
        """Enregistre une erreur"""
        self.error_log.append({
            "error_type": error_type,
            "error_message": error_message,
            "exchange_number": exchange_number,
            "timestamp": datetime.now().isoformat()
        })
    
    def generate_hardcore_report(self):
        """Génère un rapport ultra-détaillé"""
        print(f"\n{'='*100}")
        print(f"🔥 RAPPORT TEST MEILISEARCH - NIVEAU HARDCORE")
        print(f"{'='*100}")
        
        # Statistiques générales
        total_exchanges = len(self.conversation_log)
        total_errors = len(self.error_log)
        
        print(f"\n📊 STATISTIQUES:")
        print(f"   • Total échanges: {total_exchanges}")
        print(f"   • Erreurs: {total_errors}")
        print(f"   • Taux d'erreur: {(total_errors/total_exchanges*100) if total_exchanges > 0 else 0:.1f}%")
        
        # Métriques de performance
        if self.response_times:
            avg_time = statistics.mean(self.response_times)
            print(f"   • Temps moyen: {avg_time:.2f}s")
            print(f"   • Temps total: {sum(self.response_times):.1f}s")
        
        # Tests mots-clés
        if self.keyword_tests:
            avg_keyword_score = statistics.mean([t["keyword_score"] for t in self.keyword_tests])
            progression_rate = sum(self.progression_scores) / len(self.progression_scores) * 100
            
            print(f"\n🔍 MOTS-CLÉS:")
            print(f"   • Tests effectués: {len(self.keyword_tests)}")
            print(f"   • Score moyen: {avg_keyword_score:.1f}%")
            print(f"   • Taux progression: {progression_rate:.1f}%")
        
        # Tests ambiguïté
        if self.ambiguity_tests:
            ambiguity_success = sum(1 for t in self.ambiguity_tests if t["ambiguity_correct"])
            ambiguity_rate = ambiguity_success / len(self.ambiguity_tests) * 100
            
            print(f"\n⚠️ AMBIGUÏTÉ:")
            print(f"   • Tests ambiguïté: {len(self.ambiguity_tests)}")
            print(f"   • Détection correcte: {ambiguity_success}/{len(self.ambiguity_tests)}")
            print(f"   • Taux réussite: {ambiguity_rate:.1f}%")
        
        # Tests mémoire
        if self.memory_scores:
            avg_memory_score = statistics.mean(self.memory_scores)
            print(f"\n🧠 MÉMOIRE:")
            print(f"   • Tests mémoire: {len(self.memory_scores)}")
            print(f"   • Score moyen: {avg_memory_score:.1f}%")
        
        # Analyse par phase
        phases = {}
        for test in self.keyword_tests:
            phase = test["phase"]
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(test["keyword_score"])
        
        print(f"\n📋 PHASES:")
        for phase, scores in phases.items():
            avg_score = statistics.mean(scores)
            print(f"   • {phase}: {avg_score:.1f}% ({len(scores)} tests)")
        
        # Tests critiques échoués
        critical_tests = [t for t in self.keyword_tests if t["importance"] == "critical"]
        failed_critical = [t for t in critical_tests if t["keyword_score"] < 70]
        
        if failed_critical:
            print(f"\n🚨 ÉCHECS CRITIQUES ({len(failed_critical)}):")
            for test in failed_critical:
                print(f"   • {test['user_message']}: {test['keyword_score']:.1f}%")
                print(f"     Manquant: {test['missing_keywords']}")
        
        # Score final
        keyword_score = avg_keyword_score if self.keyword_tests else 0
        progression_score = progression_rate if self.progression_scores else 0
        ambiguity_score = ambiguity_rate if self.ambiguity_tests else 0
        memory_score = avg_memory_score if self.memory_scores else 0
        error_penalty = total_errors * 5
        
        final_score = max(0, 
            keyword_score * 0.4 + 
            progression_score * 0.2 + 
            ambiguity_score * 0.2 + 
            memory_score * 0.2 - 
            error_penalty
        )
        
        print(f"\n🎯 SCORE GLOBAL:")
        print(f"   • Mots-clés: {keyword_score:.1f}%")
        print(f"   • Progression: {progression_score:.1f}%")
        print(f"   • Ambiguïté: {ambiguity_score:.1f}%")
        print(f"   • Mémoire: {memory_score:.1f}%")
        print(f"   • Pénalité erreurs: -{error_penalty}%")
        print(f"   • SCORE FINAL: {final_score:.1f}%")
        
        if final_score >= 90:
            print("   🟢 EXCELLENT - Système ultra-robuste")
        elif final_score >= 80:
            print("   🟡 BON - Quelques améliorations")
        elif final_score >= 70:
            print("   🟠 MOYEN - Améliorations nécessaires")
        elif final_score >= 60:
            print("   🔴 FAIBLE - Problèmes importants")
        else:
            print("   ⚫ CRITIQUE - Refonte nécessaire")
        
        return final_score

async def run_meili_test_hardcore():
    """Lance le test MeiliSearch niveau hardcore"""
    print(f"🔥 TEST MEILISEARCH - NIVEAU HARDCORE")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 {len(MEILI_CONVERSATION_HARDCORE)} échanges complexes")
    print(f"{'='*100}\n")
    
    # ========== DÉSACTIVER LOGS VERBEUX ==========
    import logging
    logging.getLogger("database.vector_store_clean_v2").setLevel(logging.ERROR)
    logging.getLogger("core.context_extractor").setLevel(logging.ERROR)
    logging.getLogger("core.delivery_zone_extractor").setLevel(logging.ERROR)
    logging.getLogger("core.universal_rag_engine").setLevel(logging.ERROR)
    logging.getLogger("app").setLevel(logging.ERROR)
    logging.getLogger("core.conversation_notepad").setLevel(logging.ERROR)
    logging.getLogger("core.rag_tools_integration").setLevel(logging.ERROR)
    logging.getLogger("core.order_state_tracker").setLevel(logging.ERROR)
    logging.getLogger("core.rag_performance_tracker").setLevel(logging.ERROR)
    
    from core.universal_rag_engine import UniversalRAGEngine
    rag = UniversalRAGEngine()
    metrics = HardcoreMetrics()
    
    # Paramètres de test
    COMPANY_ID = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"
    COMPANY_NAME = "Rue_du_gros"
    USER_ID = "test_meili_hardcore_001"
    
    for i, exchange_data in enumerate(MEILI_CONVERSATION_HARDCORE, 1):
        user_message = exchange_data["user_message"]
        expected_keywords = exchange_data["expected_keywords"]
        phase = exchange_data["phase"]
        importance = exchange_data["importance"]
        expect_ambiguity = exchange_data.get("expect_ambiguity", False)
        delay = exchange_data.get("delay", 2.0)
        
        print(f"\n{'='*100}")
        print(f"🔥 ÉCHANGE {i}/{len(MEILI_CONVERSATION_HARDCORE)} - {phase.upper()}")
        print(f"{'='*100}")
        print(f"👤 USER: {user_message}")
        
        start_time = time.time()
        try:
            # Recherche et génération
            search_results = await rag.search_sequential_sources(user_message, COMPANY_ID)
            search_results['conversation_history'] = user_message if 'conversation_history' not in search_results else search_results['conversation_history']
            
            # Extraire contexte pour affichage
            context = search_results.get('context', '')
            docs_count = context.count('DOCUMENT #') if context else 0
            
            print(f"\n📊 DOCUMENTS TROUVÉS: {docs_count}")
            if context:
                # Afficher seulement les 500 premiers chars du contexte
                context_preview = context[:500] + "..." if len(context) > 500 else context
                print(f"\n📄 CONTEXTE (preview):\n{context_preview}")
            
            response = await rag.generate_response(
                user_message, search_results, COMPANY_ID, COMPANY_NAME, USER_ID
            )
            
            response_time = time.time() - start_time
            
            # Extraire thinking et response
            thinking = ""
            response_clean = response
            if "<thinking>" in response:
                import re
                thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL | re.IGNORECASE)
                response_match = re.search(r'<response>(.*?)</response>', response, re.DOTALL | re.IGNORECASE)
                if thinking_match:
                    thinking = thinking_match.group(1).strip()
                if response_match:
                    response_clean = response_match.group(1).strip()
            
            print(f"\n🧠 THINKING ({len(thinking)} chars):")
            if thinking:
                # Afficher seulement les phases importantes
                for line in thinking.split('\n'):
                    if any(keyword in line for keyword in ['Phase', 'Bloc-note', 'ACTION', 'PROGRESSION', 'Question progression']):
                        print(f"   {line.strip()}")
            
            print(f"\n🤖 RESPONSE:")
            print(f"   {response_clean}")
            
            print(f"\n⏱️  TEMPS: {response_time:.2f}s")
            
            # Test mots-clés + ambiguïté
            keyword_test = metrics.test_keywords_and_ambiguity(
                user_message, response_clean, expected_keywords, phase, importance, expect_ambiguity
            )
            
            print(f"\n📈 MÉTRIQUES:")
            print(f"   • Mots-clés: {keyword_test['keyword_score']:.1f}%", end="")
            if keyword_test["has_progression"]:
                print(" ✅ Progression", end="")
            else:
                print(" ❌ Pas de progression", end="")
            if expect_ambiguity:
                if keyword_test["ambiguity_correct"]:
                    print(" ✅ Ambiguïté détectée", end="")
                else:
                    print(" ❌ Ambiguïté manquée", end="")
            print()
            if keyword_test["missing_keywords"]:
                print(f"   • Manquant: {', '.join(keyword_test['missing_keywords'][:3])}")
            
            # Enregistrer l'échange
            metrics.add_exchange({
                "user_message": user_message,
                "response": response_clean,
                "thinking": thinking,
                "context_preview": context_preview if context else "",
                "docs_count": docs_count,
                "response_time": response_time,
                "phase": phase,
                "importance": importance,
                "keyword_test": keyword_test
            })
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"ERREUR: {str(e)[:200]}"
            print(f"\n❌ {error_msg}")
            
            metrics.add_error("generation_error", str(e), i)
            metrics.add_exchange({
                "user_message": user_message,
                "response": error_msg,
                "response_time": response_time,
                "phase": phase,
                "importance": importance,
                "error": True
            })
        
        # Délai adaptatif
        if i < len(MEILI_CONVERSATION_HARDCORE):
            print(f"\n⏳ Attente {delay}s...")
            await asyncio.sleep(delay)
    
    # Génération du rapport final
    final_score = metrics.generate_hardcore_report()
    
    # Sauvegarde des résultats
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"meili_test_hardcore_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            "final_score": final_score,
            "conversation_log": metrics.conversation_log,
            "keyword_tests": metrics.keyword_tests,
            "ambiguity_tests": metrics.ambiguity_tests,
            "error_log": metrics.error_log
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Résultats sauvegardés dans: {filename}")
    
    return final_score

if __name__ == "__main__":
    asyncio.run(run_meili_test_hardcore())

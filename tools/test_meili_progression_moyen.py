#!/usr/bin/env python3
"""
🔥 TEST CONVERSATIONNEL MEILISEARCH - NIVEAU MOYEN
Test de progression commande avec questions mots-clés MeiliSearch

OBJECTIFS:
1. Valider rescoring + filtrage + extraction + ambiguïté
2. Tester progression vers finalisation commande
3. Valider détection intentions et bloc-note
4. 15 échanges optimisés pour MeiliSearch (full-text)
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

# 🎯 SCÉNARIO MOYEN : 15 ÉCHANGES MOTS-CLÉS
MEILI_CONVERSATION_MOYEN = [
    # === PHASE 1: EXPLORATION PRODUIT (4 échanges) ===
    {
        "user_message": "lot 150",
        "expected_keywords": ["lot 150", "13500", "couches"],
        "phase": "exploration_produit",
        "importance": "high",
        "delay": 2.0
    },
    {
        "user_message": "culottes",
        "expected_keywords": ["culottes", "taille", "disponible"],
        "phase": "exploration_produit",
        "importance": "high",
        "delay": 2.0
    },
    {
        "user_message": "taille 4",
        "expected_keywords": ["taille 4", "9", "15 kg"],
        "phase": "exploration_produit",
        "importance": "high",
        "delay": 2.0
    },
    {
        "user_message": "prix total",
        "expected_keywords": ["13500", "prix", "fcfa"],
        "phase": "exploration_produit",
        "importance": "high",
        "delay": 2.0
    },

    # === PHASE 2: LIVRAISON (4 échanges) ===
    {
        "user_message": "livraison Yopougon",
        "expected_keywords": ["Yopougon", "1500", "livraison"],
        "phase": "livraison",
        "importance": "high",
        "delay": 2.5
    },
    {
        "user_message": "délai",
        "expected_keywords": ["3h", "acompte", "rapide"],
        "phase": "livraison",
        "importance": "high",
        "delay": 2.5
    },
    {
        "user_message": "Cocody",
        "expected_keywords": ["Cocody", "1500", "livraison"],
        "phase": "livraison",
        "importance": "high",
        "delay": 2.5
    },
    {
        "user_message": "adresse exacte",
        "expected_keywords": ["commune", "quartier", "préciser"],
        "phase": "livraison",
        "importance": "high",
        "delay": 2.5
    },

    # === PHASE 3: PAIEMENT (4 échanges) ===
    {
        "user_message": "Wave",
        "expected_keywords": ["Wave", "0787360757", "acompte"],
        "phase": "paiement",
        "importance": "high",
        "delay": 3.0
    },
    {
        "user_message": "acompte",
        "expected_keywords": ["2000", "acompte", "obligatoire"],
        "phase": "paiement",
        "importance": "high",
        "delay": 3.0
    },
    {
        "user_message": "total avec livraison",
        "expected_keywords": ["15000", "13500", "1500"],
        "phase": "paiement",
        "importance": "critical",
        "delay": 3.0
    },
    {
        "user_message": "WhatsApp",
        "expected_keywords": ["0160924560", "WhatsApp", "contact"],
        "phase": "paiement",
        "importance": "high",
        "delay": 3.0
    },

    # === PHASE 4: VALIDATION (3 échanges) ===
    {
        "user_message": "récapitulatif",
        "expected_keywords": ["lot 150", "taille 4", "Cocody", "15000"],
        "phase": "validation",
        "importance": "critical",
        "delay": 3.5
    },
    {
        "user_message": "je confirme",
        "expected_keywords": ["acompte", "2000", "Wave"],
        "phase": "validation",
        "importance": "critical",
        "delay": 3.5
    },
    {
        "user_message": "numéro téléphone",
        "expected_keywords": ["téléphone", "livraison", "contact"],
        "phase": "validation",
        "importance": "high",
        "delay": 3.5
    }
]

class MeiliMetrics:
    def __init__(self):
        self.conversation_log = []
        self.keyword_tests = []
        self.error_log = []
        self.response_times = []
        self.progression_scores = []
        
    def add_exchange(self, exchange_data: Dict[str, Any]):
        """Enregistre un échange complet"""
        self.conversation_log.append({
            **exchange_data,
            "timestamp": datetime.now().isoformat(),
            "exchange_number": len(self.conversation_log) + 1
        })
        
        if exchange_data.get("response_time"):
            self.response_times.append(exchange_data["response_time"])
    
    def test_keywords(self, user_message: str, response: str, 
                     expected_keywords: List[str], phase: str, importance: str):
        """Teste la présence des mots-clés attendus"""
        found_keywords = []
        missing_keywords = []
        
        response_lower = response.lower()
        
        for keyword in expected_keywords:
            if keyword.lower() in response_lower:
                found_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)
        
        keyword_score = len(found_keywords) / len(expected_keywords) * 100 if expected_keywords else 100
        
        # Vérifier progression (question présente?)
        has_progression = "?" in response
        
        keyword_test = {
            "phase": phase,
            "importance": importance,
            "user_message": user_message,
            "expected_keywords": expected_keywords,
            "found_keywords": found_keywords,
            "missing_keywords": missing_keywords,
            "keyword_score": keyword_score,
            "has_progression": has_progression
        }
        
        self.keyword_tests.append(keyword_test)
        self.progression_scores.append(1 if has_progression else 0)
        
        return keyword_test
    
    def add_error(self, error_type: str, error_message: str, exchange_number: int):
        """Enregistre une erreur"""
        self.error_log.append({
            "error_type": error_type,
            "error_message": error_message,
            "exchange_number": exchange_number,
            "timestamp": datetime.now().isoformat()
        })
    
    def generate_report(self):
        """Génère un rapport détaillé"""
        print(f"\n{'='*80}")
        print(f"🔥 RAPPORT TEST MEILISEARCH - NIVEAU MOYEN")
        print(f"{'='*80}")
        
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
        
        # Tests mots-clés
        if self.keyword_tests:
            avg_keyword_score = statistics.mean([t["keyword_score"] for t in self.keyword_tests])
            progression_rate = sum(self.progression_scores) / len(self.progression_scores) * 100
            
            print(f"\n🔍 MOTS-CLÉS:")
            print(f"   • Tests effectués: {len(self.keyword_tests)}")
            print(f"   • Score moyen: {avg_keyword_score:.1f}%")
            print(f"   • Taux progression: {progression_rate:.1f}%")
        
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
            print(f"   • {phase}: {avg_score:.1f}%")
        
        # Tests critiques échoués
        critical_tests = [t for t in self.keyword_tests if t["importance"] == "critical"]
        failed_critical = [t for t in critical_tests if t["keyword_score"] < 80]
        
        if failed_critical:
            print(f"\n🚨 ÉCHECS CRITIQUES ({len(failed_critical)}):")
            for test in failed_critical:
                print(f"   • {test['user_message']}: {test['keyword_score']:.1f}%")
                print(f"     Manquant: {test['missing_keywords']}")
        
        # Score final
        keyword_score = avg_keyword_score if self.keyword_tests else 0
        progression_score = progression_rate if self.progression_scores else 0
        error_penalty = total_errors * 5
        
        final_score = max(0, keyword_score * 0.7 + progression_score * 0.3 - error_penalty)
        
        print(f"\n🎯 SCORE FINAL: {final_score:.1f}%")
        
        if final_score >= 85:
            print("   🟢 EXCELLENT - MeiliSearch optimisé")
        elif final_score >= 70:
            print("   🟡 BON - Améliorations mineures")
        elif final_score >= 50:
            print("   🟠 MOYEN - Améliorations nécessaires")
        else:
            print("   🔴 FAIBLE - Problèmes critiques")
        
        return final_score

async def run_meili_test_moyen():
    """Lance le test MeiliSearch niveau moyen"""
    print(f"🔥 TEST MEILISEARCH - NIVEAU MOYEN")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 {len(MEILI_CONVERSATION_MOYEN)} échanges mots-clés")
    print(f"{'='*80}\n")
    
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
    metrics = MeiliMetrics()
    
    # Paramètres de test
    COMPANY_ID = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"
    COMPANY_NAME = "Rue_du_gros"
    USER_ID = "test_meili_moyen_001"
    
    for i, exchange_data in enumerate(MEILI_CONVERSATION_MOYEN, 1):
        user_message = exchange_data["user_message"]
        expected_keywords = exchange_data["expected_keywords"]
        phase = exchange_data["phase"]
        importance = exchange_data["importance"]
        delay = exchange_data.get("delay", 2.0)
        
        print(f"\n{'='*80}")
        print(f"🔥 ÉCHANGE {i}/{len(MEILI_CONVERSATION_MOYEN)} - {phase.upper()}")
        print(f"{'='*80}")
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
                # Afficher seulement les 400 premiers chars du contexte
                context_preview = context[:400] + "..." if len(context) > 400 else context
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
            
            # Test mots-clés
            keyword_test = metrics.test_keywords(
                user_message, response_clean, expected_keywords, phase, importance
            )
            
            print(f"\n📈 MÉTRIQUES:")
            print(f"   • Mots-clés: {keyword_test['keyword_score']:.1f}%", end="")
            if keyword_test["has_progression"]:
                print(" ✅ Progression", end="")
            else:
                print(" ❌ Pas de progression", end="")
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
        if i < len(MEILI_CONVERSATION_MOYEN):
            print(f"\n⏳ Attente {delay}s...")
            await asyncio.sleep(delay)
    
    # Génération du rapport final
    final_score = metrics.generate_report()
    
    # Sauvegarde des résultats
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"meili_test_moyen_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            "final_score": final_score,
            "conversation_log": metrics.conversation_log,
            "keyword_tests": metrics.keyword_tests,
            "error_log": metrics.error_log
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Résultats sauvegardés dans: {filename}")
    
    return final_score

if __name__ == "__main__":
    asyncio.run(run_meili_test_moyen())

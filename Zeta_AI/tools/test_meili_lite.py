#!/usr/bin/env python3
"""
🔥 TEST MEILISEARCH - VERSION LITE (ÉCONOMIQUE)
Seulement 5 échanges essentiels pour valider le système
Coût: ~500 tokens au lieu de 3000+
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import time
from datetime import datetime
from typing import Dict, List
import json

# Import du moteur RAG
from core.universal_rag_engine import UniversalRAGEngine

# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 CONFIGURATION TEST LITE
# ═══════════════════════════════════════════════════════════════════════════════

COMPANY_ID = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"
USER_ID = "test_lite_001"

# 🔥 SEULEMENT 5 ÉCHANGES CRITIQUES
TEST_EXCHANGES = [
    {
        "phase": "PRODUIT",
        "message": "lot 150",
        "expected": {
            "responds": True,           # Bot répond
            "not_empty": True,          # Réponse non vide
            "asks_question": True,      # Pose une question
            "max_time": 15.0            # < 15s
        }
    },
    {
        "phase": "ZONE",
        "message": "Cocody",
        "expected": {
            "responds": True,
            "not_empty": True,
            "asks_question": True,
            "max_time": 10.0
        }
    },
    {
        "phase": "CONTACT",
        "message": "0787360757",
        "expected": {
            "responds": True,
            "not_empty": True,
            "asks_question": True,
            "max_time": 10.0
        }
    },
    {
        "phase": "PAIEMENT",
        "message": "Wave",
        "expected": {
            "responds": True,
            "not_empty": True,
            "asks_question": True,
            "max_time": 10.0
        }
    },
    {
        "phase": "VALIDATION",
        "message": "je confirme",
        "expected": {
            "responds": True,
            "not_empty": True,
            "asks_question": False,     # Pas de question (finalisation)
            "max_time": 10.0
        }
    }
]

# ═══════════════════════════════════════════════════════════════════════════════
# 🧪 CLASSE TEST LITE
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeiliLite:
    """Test économique du système RAG"""
    
    def __init__(self):
        self.engine = UniversalRAGEngine()
        self.results = []
        self.total_time = 0
        self.errors = 0
        
    async def run_exchange(self, exchange: Dict) -> Dict:
        """Exécute un échange et retourne les résultats"""
        print(f"\n{'='*80}")
        print(f"🔥 TEST: {exchange['phase']}")
        print(f"{'='*80}")
        print(f"👤 USER: {exchange['message']}")
        
        start_time = time.time()
        
        try:
            # Appel RAG
            result = await self.engine.process_query(
                query=exchange['message'],
                company_id=COMPANY_ID,
                user_id=USER_ID
            )
            
            # Convertir UniversalRAGResult en dict
            response = {
                'response': result.response,
                'thinking': '',  # UniversalRAGResult n'a pas de thinking
                'context': result.context_used
            }
            
            elapsed = time.time() - start_time
            
            # Extraction réponse
            bot_response = response.get('response', '')
            thinking = response.get('thinking', '')
            
            print(f"\n🤖 RESPONSE:\n   {bot_response[:200]}...")
            print(f"\n⏱️  TEMPS: {elapsed:.2f}s")
            
            # Vérification comportement
            checks = []
            expected = exchange['expected']
            
            # 1. Bot répond (pas d'erreur)
            if expected['responds']:
                if bot_response:
                    checks.append(('✅', 'Bot répond'))
                else:
                    checks.append(('❌', 'Bot ne répond pas'))
            
            # 2. Réponse non vide
            if expected['not_empty']:
                if len(bot_response.strip()) > 10:
                    checks.append(('✅', 'Réponse non vide'))
                else:
                    checks.append(('❌', 'Réponse vide/trop courte'))
            
            # 3. Pose une question (progression)
            if expected['asks_question']:
                if '?' in bot_response:
                    checks.append(('✅', 'Pose une question'))
                else:
                    checks.append(('⚠️', 'Pas de question'))
            else:
                # Validation finale - ne doit PAS poser de question
                if '?' not in bot_response:
                    checks.append(('✅', 'Finalisation (pas de question)'))
                else:
                    checks.append(('⚠️', 'Question inattendue'))
            
            # 4. Temps de réponse
            if elapsed <= expected['max_time']:
                checks.append(('✅', f'Temps OK ({elapsed:.1f}s)'))
            else:
                checks.append(('❌', f'Trop lent ({elapsed:.1f}s > {expected["max_time"]}s)'))
            
            # Calcul score
            passed = sum(1 for status, _ in checks if status == '✅')
            total = len(checks)
            score = (passed / total) * 100
            
            print(f"\n📊 VÉRIFICATIONS:")
            for status, msg in checks:
                print(f"   {status} {msg}")
            print(f"\n📈 SCORE: {score:.0f}% ({passed}/{total})")
            
            return {
                'phase': exchange['phase'],
                'message': exchange['message'],
                'response': bot_response[:200],
                'time': elapsed,
                'score': score,
                'checks': checks,
                'passed': passed,
                'total': total,
                'error': None
            }
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n❌ ERREUR: {str(e)}")
            
            self.errors += 1
            
            return {
                'phase': exchange['phase'],
                'message': exchange['message'],
                'response': None,
                'time': elapsed,
                'score': 0,
                'checks': [('❌', f'Erreur système: {str(e)[:50]}')],
                'passed': 0,
                'total': 1,
                'error': str(e)
            }
    
    async def run_all(self):
        """Exécute tous les tests"""
        print("🔥 TEST MEILISEARCH - VERSION LITE")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 {len(TEST_EXCHANGES)} échanges critiques")
        print("="*80)
        
        start_total = time.time()
        
        for exchange in TEST_EXCHANGES:
            result = await self.run_exchange(exchange)
            self.results.append(result)
            self.total_time += result['time']
            
            # Pause entre échanges
            await asyncio.sleep(1)
        
        total_elapsed = time.time() - start_total
        
        # Rapport final
        self.print_report(total_elapsed)
        
        # Sauvegarde JSON
        self.save_results()
    
    def print_report(self, total_elapsed: float):
        """Affiche le rapport final"""
        print("\n" + "="*80)
        print("🔥 RAPPORT TEST LITE")
        print("="*80)
        
        # Statistiques
        total_tests = len(self.results)
        avg_time = self.total_time / total_tests if total_tests > 0 else 0
        avg_score = sum(r['score'] for r in self.results) / total_tests if total_tests > 0 else 0
        
        print(f"\n📊 STATISTIQUES:")
        print(f"   • Total échanges: {total_tests}")
        print(f"   • Erreurs: {self.errors}")
        print(f"   • Temps moyen: {avg_time:.2f}s")
        print(f"   • Temps total: {total_elapsed:.2f}s")
        
        # Scores par phase
        print(f"\n📋 SCORES PAR PHASE:")
        for result in self.results:
            status = "✅" if result['score'] >= 66 else "⚠️" if result['score'] >= 33 else "❌"
            print(f"   {status} {result['phase']}: {result['score']:.0f}%")
        
        # Échecs critiques
        failures = [r for r in self.results if r['score'] < 75]
        if failures:
            print(f"\n🚨 ÉCHECS ({len(failures)}):")
            for fail in failures:
                print(f"   • {fail['phase']}: {fail['score']:.0f}% ({fail['passed']}/{fail['total']})")
                if fail['error']:
                    print(f"     Erreur: {fail['error']}")
                else:
                    for status, msg in fail['checks']:
                        if status != '✅':
                            print(f"     {status} {msg}")
        
        # Score final
        print(f"\n🎯 SCORE FINAL: {avg_score:.1f}%")
        if avg_score >= 80:
            print("   🟢 EXCELLENT - Système opérationnel")
        elif avg_score >= 60:
            print("   🟡 BON - Quelques améliorations possibles")
        elif avg_score >= 40:
            print("   🟠 MOYEN - Améliorations nécessaires")
        else:
            print("   🔴 FAIBLE - Problèmes critiques détectés")
    
    def save_results(self):
        """Sauvegarde les résultats en JSON"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"meili_test_lite_{timestamp}.json"
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'total_exchanges': len(self.results),
            'errors': self.errors,
            'avg_score': sum(r['score'] for r in self.results) / len(self.results),
            'results': self.results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Résultats sauvegardés dans: {filename}")

# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 EXÉCUTION
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """Point d'entrée principal"""
    tester = TestMeiliLite()
    await tester.run_all()

if __name__ == "__main__":
    asyncio.run(main())

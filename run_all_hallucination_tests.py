#!/usr/bin/env python3
"""
🧪 SCRIPT PRINCIPAL - TOUS LES TESTS ANTI-HALLUCINATION
Exécute tous les tests du système anti-hallucination
"""

import asyncio
import sys
import os
import time
from datetime import datetime

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class TestRunner:
    """Exécuteur de tous les tests anti-hallucination"""
    
    def __init__(self):
        self.start_time = None
        self.results = {}
        
    async def run_quick_test(self):
        """Exécute le test rapide"""
        print("⚡ EXÉCUTION DU TEST RAPIDE")
        print("=" * 40)
        
        try:
            from test_hallucination_quick import main as quick_main
            await quick_main()
            self.results['quick_test'] = 'passed'
            return True
        except Exception as e:
            print(f"❌ Erreur dans le test rapide: {e}")
            self.results['quick_test'] = 'failed'
            return False
    
    async def run_compatibility_test(self):
        """Exécute le test de compatibilité"""
        print("\n🔄 EXÉCUTION DU TEST DE COMPATIBILITÉ")
        print("=" * 40)
        
        try:
            from test_hallucination_compatibility import main as compat_main
            await compat_main()
            self.results['compatibility_test'] = 'passed'
            return True
        except Exception as e:
            print(f"❌ Erreur dans le test de compatibilité: {e}")
            self.results['compatibility_test'] = 'failed'
            return False
    
    async def run_performance_test(self):
        """Exécute le test de performance"""
        print("\n⚡ EXÉCUTION DU TEST DE PERFORMANCE")
        print("=" * 40)
        
        try:
            from test_hallucination_performance import main as perf_main
            await perf_main()
            self.results['performance_test'] = 'passed'
            return True
        except Exception as e:
            print(f"❌ Erreur dans le test de performance: {e}")
            self.results['performance_test'] = 'failed'
            return False
    
    async def run_stress_test(self):
        """Exécute le test de stress"""
        print("\n💥 EXÉCUTION DU TEST DE STRESS")
        print("=" * 40)
        
        try:
            from test_hallucination_stress import main as stress_main
            await stress_main()
            self.results['stress_test'] = 'passed'
            return True
        except Exception as e:
            print(f"❌ Erreur dans le test de stress: {e}")
            self.results['stress_test'] = 'failed'
            return False
    
    async def run_comprehensive_test(self):
        """Exécute le test complet"""
        print("\n🧪 EXÉCUTION DU TEST COMPLET")
        print("=" * 40)
        
        try:
            from test_hallucination_guard_limits import main as comprehensive_main
            await comprehensive_main()
            self.results['comprehensive_test'] = 'passed'
            return True
        except Exception as e:
            print(f"❌ Erreur dans le test complet: {e}")
            self.results['comprehensive_test'] = 'failed'
            return False
    
    def print_final_summary(self):
        """Affiche le résumé final"""
        print("\n" + "=" * 70)
        print("📊 RÉSUMÉ FINAL DE TOUS LES TESTS")
        print("=" * 70)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result == 'passed')
        failed_tests = total_tests - passed_tests
        
        print(f"📈 STATISTIQUES GLOBALES:")
        print(f"   Total des tests: {total_tests}")
        print(f"   Tests réussis: {passed_tests}")
        print(f"   Tests échoués: {failed_tests}")
        print(f"   Taux de réussite: {(passed_tests/total_tests)*100:.1f}%")
        
        if self.start_time:
            total_duration = (datetime.now() - self.start_time).total_seconds()
            print(f"   Durée totale: {total_duration:.2f}s")
        
        print(f"\n📋 DÉTAIL PAR TEST:")
        for test_name, result in self.results.items():
            status_icon = "✅" if result == 'passed' else "❌"
            print(f"   {status_icon} {test_name.replace('_', ' ').title()}: {result}")
        
        print(f"\n💡 RECOMMANDATIONS:")
        if passed_tests == total_tests:
            print("   🎉 TOUS LES TESTS SONT PASSÉS !")
            print("   ✅ Le système anti-hallucination est prêt pour la production")
            print("   ✅ Toutes les fonctionnalités fonctionnent correctement")
        elif passed_tests >= total_tests * 0.8:
            print("   ⚠️  La plupart des tests sont passés")
            print("   ✅ Le système est globalement fonctionnel")
            print("   🔧 Corriger les tests échoués avant la production")
        else:
            print("   ❌ Plusieurs tests ont échoué")
            print("   🔧 Le système nécessite des corrections importantes")
            print("   ⚠️  Ne pas déployer en production sans corrections")
        
        print(f"\n📁 FICHIERS DE TEST DISPONIBLES:")
        test_files = [
            "test_hallucination_quick.py - Test rapide des fonctionnalités",
            "test_hallucination_compatibility.py - Test de compatibilité",
            "test_hallucination_performance.py - Test de performance",
            "test_hallucination_stress.py - Test de stress",
            "test_hallucination_guard_limits.py - Test complet des limites"
        ]
        
        for file_info in test_files:
            print(f"   📄 {file_info}")

async def main():
    """Fonction principale"""
    print("🧪 SCRIPT PRINCIPAL - TOUS LES TESTS ANTI-HALLUCINATION")
    print("Exécution complète de la suite de tests")
    print("=" * 70)
    
    runner = TestRunner()
    runner.start_time = datetime.now()
    
    # Menu de sélection
    print("\n🎯 SÉLECTION DES TESTS À EXÉCUTER:")
    print("1. Test rapide (recommandé pour commencer)")
    print("2. Test de compatibilité")
    print("3. Test de performance")
    print("4. Test de stress")
    print("5. Test complet (tous les cas de figure)")
    print("6. Tous les tests")
    print("0. Quitter")
    
    try:
        choice = input("\nVotre choix (0-6): ").strip()
        
        if choice == "0":
            print("👋 Au revoir !")
            return
        
        elif choice == "1":
            await runner.run_quick_test()
        
        elif choice == "2":
            await runner.run_compatibility_test()
        
        elif choice == "3":
            await runner.run_performance_test()
        
        elif choice == "4":
            await runner.run_stress_test()
        
        elif choice == "5":
            await runner.run_comprehensive_test()
        
        elif choice == "6":
            print("\n🚀 EXÉCUTION DE TOUS LES TESTS")
            print("=" * 50)
            
            # Exécution séquentielle de tous les tests
            tests = [
                ("Test rapide", runner.run_quick_test),
                ("Test de compatibilité", runner.run_compatibility_test),
                ("Test de performance", runner.run_performance_test),
                ("Test de stress", runner.run_stress_test),
                ("Test complet", runner.run_comprehensive_test)
            ]
            
            for test_name, test_func in tests:
                print(f"\n🔄 Exécution du {test_name}...")
                await test_func()
                print(f"✅ {test_name} terminé")
        
        else:
            print("❌ Choix invalide")
            return
        
        # Affichage du résumé final
        runner.print_final_summary()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrompus par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur critique: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

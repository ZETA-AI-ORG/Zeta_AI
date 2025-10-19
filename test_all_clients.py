#!/usr/bin/env python3
"""
🎭 LANCEUR TOUS LES TESTS CLIENTS
Lance séquentiellement les 3 profils de clients
"""

import asyncio
import subprocess
import sys
from datetime import datetime

def print_header(title: str):
    """Affiche un header stylisé"""
    print("\n" + "🎭 " * 30)
    print(f"{title:^90}")
    print("🎭 " * 30 + "\n")

async def run_test(script_name: str, description: str):
    """Lance un script de test"""
    print(f"\n{'='*90}")
    print(f"🚀 LANCEMENT: {description}")
    print(f"📄 Script: {script_name}")
    print(f"{'='*90}\n")
    
    start_time = datetime.now()
    
    try:
        # Lancer le script Python
        process = await asyncio.create_subprocess_exec(
            sys.executable, script_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Afficher la sortie
        if stdout:
            print(stdout.decode())
        if stderr:
            print("⚠️ STDERR:", stderr.decode())
        
        if process.returncode == 0:
            print(f"\n✅ TEST TERMINÉ AVEC SUCCÈS en {duration:.2f}s")
            return True
        else:
            print(f"\n❌ TEST ÉCHOUÉ (code: {process.returncode})")
            return False
            
    except Exception as e:
        print(f"\n❌ ERREUR LORS DU LANCEMENT: {e}")
        return False

async def main():
    """Lance tous les tests séquentiellement"""
    
    print_header("TESTS SIMULATION CLIENTS RÉELS - BOTLIVE")
    
    print("📋 Tests à lancer:")
    print("   1️⃣  Client Direct (optimal)")
    print("   2️⃣  Client Hésitant (nombreuses questions)")
    print("   3️⃣  Client Difficile (changements d'avis + hors domaine)")
    print("\n⏰ Démarrage dans 3 secondes...\n")
    
    await asyncio.sleep(3)
    
    results = {}
    
    # ═══ TEST 1: CLIENT DIRECT ═══
    results['direct'] = await run_test(
        "test_client_direct.py",
        "CLIENT DIRECT - Comportement idéal"
    )
    
    await asyncio.sleep(2)  # Pause entre tests
    
    # ═══ TEST 2: CLIENT HÉSITANT ═══
    results['hesitant'] = await run_test(
        "test_client_hesitant.py",
        "CLIENT HÉSITANT - Pose beaucoup de questions"
    )
    
    await asyncio.sleep(2)  # Pause entre tests
    
    # ═══ TEST 3: CLIENT DIFFICILE ═══
    results['difficile'] = await run_test(
        "test_client_difficile.py",
        "CLIENT DIFFICILE - Chaotique et hors domaine"
    )
    
    # ═══ RÉSUMÉ FINAL ═══
    print("\n" + "🎯 " * 30)
    print(f"{'RÉSUMÉ FINAL - TESTS CLIENTS':^90}")
    print("🎯 " * 30 + "\n")
    
    print(f"{'Test':<40} {'Résultat':>20}")
    print("─" * 90)
    
    for test_name, success in results.items():
        status = "✅ RÉUSSI" if success else "❌ ÉCHOUÉ"
        print(f"{test_name.upper():<40} {status:>20}")
    
    print("─" * 90)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n📊 TAUX DE RÉUSSITE: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    
    if passed_tests == total_tests:
        print("\n🎉 TOUS LES TESTS ONT RÉUSSI - SYSTÈME ROBUSTE ! 🎉\n")
        return 0
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) échoué(s) - Corrections nécessaires\n")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

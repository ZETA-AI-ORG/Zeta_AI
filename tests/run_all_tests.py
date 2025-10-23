#!/usr/bin/env python3
"""
🚀 LANCEUR DE TESTS COMPLET

Exécute les 3 scénarios et génère un rapport comparatif

Usage:
    python tests/run_all_tests.py
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conversation_simulator import run_scenario
from tests.test_scenarios import SCENARIOS


async def run_all_tests():
    """
    Exécute tous les scénarios de test
    """
    print("\n" + "="*80)
    print("🧪 LANCEMENT SUITE COMPLÈTE DE TESTS")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    results = {}
    
    for scenario_name in ["light", "medium", "hardcore"]:
        print(f"\n🎯 Préparation scénario: {scenario_name.upper()}")
        
        scenario = SCENARIOS[scenario_name]
        
        print(f"📋 Description: {scenario['description']}")
        print(f"👤 Persona: {scenario['persona']['profil']}")
        print(f"🎭 Nombre de tours: {len(scenario['messages'])}")
        
        input(f"\n⏸️  Appuyez sur ENTRÉE pour lancer le test {scenario_name.upper()}...")
        
        # Exécuter
        tracker, report_path = await run_scenario(scenario)
        
        results[scenario_name] = {
            "tracker": tracker,
            "report_path": report_path
        }
        
        print(f"\n✅ Test {scenario_name.upper()} terminé!")
        print(f"📄 Rapport: {report_path}\n")
        
        # Pause entre scénarios
        if scenario_name != "hardcore":
            await asyncio.sleep(3)
    
    # Rapport final comparatif
    print("\n" + "="*80)
    print("📊 RAPPORT COMPARATIF FINAL")
    print("="*80 + "\n")
    
    print(f"{'SCENARIO':<15} {'TOURS':<8} {'TEMPS TOTAL':<15} {'COÛT':<12} {'CONFIANCE':<12}")
    print("-" * 80)
    
    for scenario_name, result in results.items():
        tracker = result['tracker']
        
        # Confiance finale
        confiance_finale = "N/A"
        if tracker.turns:
            last_thinking = tracker.turns[-1].get('thinking', {})
            confiance = last_thinking.get('confiance', {})
            confiance_finale = f"{confiance.get('score', 0)}%"
        
        print(f"{scenario_name.upper():<15} {len(tracker.turns):<8} "
              f"{tracker.total_time_ms/1000:.1f}s{'':<10} "
              f"${tracker.total_cost:.4f}{'':<4} {confiance_finale:<12}")
    
    print("\n" + "="*80)
    
    # Analyse qualitative
    print("\n📈 ANALYSE QUALITATIVE:\n")
    
    for scenario_name, result in results.items():
        tracker = result['tracker']
        
        print(f"\n🎭 {scenario_name.upper()}:")
        
        if tracker.turns:
            last_turn = tracker.turns[-1]
            last_thinking = last_turn.get('thinking', {})
            
            # Complétude
            progression = last_thinking.get('progression', {})
            completude = progression.get('completude', 'N/A')
            print(f"   ✅ Complétude: {completude}")
            
            # Données collectées
            deja_collecte = last_thinking.get('deja_collecte', {})
            if deja_collecte:
                collectees = [k for k, v in deja_collecte.items() if v and v != 'null']
                print(f"   📋 Données collectées: {', '.join(collectees) if collectees else 'Aucune'}")
            
            # Phase atteinte
            strategie = last_thinking.get('strategie_qualification', {})
            phase = strategie.get('phase', 'N/A')
            print(f"   🎯 Phase finale: {phase}")
        
        print(f"   💰 Coût: ${tracker.total_cost:.4f} ({tracker.total_tokens} tokens)")
        print(f"   ⏱️  Performance: {tracker.total_time_ms/len(tracker.turns) if tracker.turns else 0:.0f}ms/tour")
    
    print("\n" + "="*80)
    print("✅ TOUS LES TESTS TERMINÉS!")
    print("📁 Rapports disponibles dans: tests/reports/")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())

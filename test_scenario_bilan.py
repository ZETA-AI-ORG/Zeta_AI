#!/usr/bin/env python3
"""Bilan dynamique du test scenario final.

Ce script lit les résultats JSON générés par test_scenario_final.py
et produit un bilan à jour (tour par tour + état final).
"""

import os
import json

project_root = os.path.dirname(os.path.abspath(__file__))
results_path = os.path.join(project_root, "test_scenario_final_results.json")

print("="*80)
print("BILAN TEST SCENARIO FINAL")
print("="*80)

if not os.path.exists(results_path):
    print("\n[ERREUR] Aucun résultat trouvé. Lance d'abord: python test_scenario_final.py\n")
    raise SystemExit(1)

with open(results_path, "r", encoding="utf-8") as f:
    data = json.load(f)

turns = data.get("turns", [])
final_state = data.get("final_state", {})

print("\n📊 TOUR PAR TOUR:")
print("-"*50)

for turn in turns:
    num = turn.get("turn")
    print(f"TOUR {num}:")
    print(f"  Question: {turn.get('question', '')}")

    llm_used = (turn.get("llm_used") or "UNKNOWN").upper()
    print(f"  Type: {llm_used}")

    time_ms = int(turn.get("time_ms", 0) or 0)
    print(f"  Temps: {time_ms}ms")

    resp = (turn.get("response") or "").strip()
    if resp:
        print(f"  Réponse: {resp}")

    order_percent = int(turn.get("order_percent", 0) or 0)
    print(f"  Order: {order_percent}% complet")

    # Si la réponse est vide ou pour debug approfondi, afficher le résultat brut
    raw = turn.get("raw_result")
    if not resp and raw is not None:
        print("  RAW RESULT:")
        raw_str = json.dumps(raw, ensure_ascii=False, indent=2)
        for line in raw_str.splitlines():
            print(f"    {line}")

    print()

print("\n📈 STATISTIQUES:")
print("-"*50)

total_time = sum(int(t.get("time_ms", 0) or 0) for t in turns) or 0
nb_tours = len(turns) or 1

print(f"Temps total: {total_time:,}ms ({total_time/1000:.1f}s)")
print(f"Temps moyen: {total_time/nb_tours:.0f}ms")

print("\n🎯 ANALYSE (BASÉE SUR LE DERNIER TEST):")
print("-"*50)
print("✅ Points observés:")

if final_state.get("complete"):
    print("  • Commande complétée à 100% (produit+paiement+zone+tel)")
else:
    print("  • Commande INCOMPLÈTE (au moins un champ manquant)")

print("  • Zone et téléphone gérés par Python direct (order_state_tracker)")

print("\n❌ Problèmes potentiels:")
print("-"*50)
if not final_state.get("produit"):
    print("  • Produit non détecté ou non confirmé")
if not final_state.get("paiement"):
    print("  • Paiement non détecté ou non confirmé")
if not final_state.get("zone"):
    print("  • Zone de livraison manquante")
if not final_state.get("telephone"):
    print("  • Numéro de téléphone manquant ou invalide")
if final_state.get("complete"):
    print("  • Aucun problème critique (commande complète)")

print("\n📋 ÉTAT FINAL (DERNIER TEST):")
print("-"*50)
print(f"Produit: {final_state.get('produit') or 'NON'}")
print(f"Paiement: {final_state.get('paiement') or 'NON'}")
print(f"Zone: {final_state.get('zone') or 'NON'}")
print(f"Téléphone: {final_state.get('telephone') or 'NON'}")
print(f"Complète: {bool(final_state.get('complete'))}")

print("\n" + "="*80)

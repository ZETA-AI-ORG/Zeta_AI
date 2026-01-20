#!/usr/bin/env python3
"""
🧪 TEST ISOLATION USER_ID - Vérifier que chaque user_id a son propre state
"""

from core.order_state_tracker import order_tracker

print("=" * 80)
print("🧪 TEST ISOLATION STATE TRACKER - 3 CLIENTS SIMULTANÉS")
print("=" * 80)

# ═══ CLIENT A ═══
print("\n📋 CLIENT A (client_test_A)")
order_tracker.update_produit("client_test_A", "casque[VISION]")
order_tracker.update_paiement("client_test_A", "5000F[VISION]")
order_tracker.update_zone("client_test_A", "Yopougon-1500F[MESSAGE]")

# ═══ CLIENT B ═══
print("\n📋 CLIENT B (client_test_B)")
order_tracker.update_produit("client_test_B", "lingettes[VISION]")
order_tracker.update_paiement("client_test_B", "2000F[VISION]")
order_tracker.update_zone("client_test_B", "Cocody-1500F[MESSAGE]")

# ═══ CLIENT C ═══
print("\n📋 CLIENT C (client_test_C)")
order_tracker.update_produit("client_test_C", "sac[VISION]")
order_tracker.update_zone("client_test_C", "Plateau-1500F[MESSAGE]")

# ═══ VÉRIFICATION ISOLATION ═══
print("\n" + "=" * 80)
print("✅ VÉRIFICATION ISOLATION")
print("=" * 80)

state_a = order_tracker.get_state("client_test_A")
state_b = order_tracker.get_state("client_test_B")
state_c = order_tracker.get_state("client_test_C")

print(f"\n👤 CLIENT A:")
print(f"   PRODUIT:  {state_a.produit}")
print(f"   PAIEMENT: {state_a.paiement}")
print(f"   ZONE:     {state_a.zone}")

print(f"\n👤 CLIENT B:")
print(f"   PRODUIT:  {state_b.produit}")
print(f"   PAIEMENT: {state_b.paiement}")
print(f"   ZONE:     {state_b.zone}")

print(f"\n👤 CLIENT C:")
print(f"   PRODUIT:  {state_c.produit}")
print(f"   PAIEMENT: {state_c.paiement}")
print(f"   ZONE:     {state_c.zone}")

# ═══ VALIDATION ═══
print("\n" + "=" * 80)
errors = []

if state_a.produit != "casque[VISION]":
    errors.append("❌ CLIENT A: Produit incorrect")
if state_a.zone != "Yopougon-1500F[MESSAGE]":
    errors.append("❌ CLIENT A: Zone incorrecte")

if state_b.produit != "lingettes[VISION]":
    errors.append("❌ CLIENT B: Produit incorrect")
if state_b.zone != "Cocody-1500F[MESSAGE]":
    errors.append("❌ CLIENT B: Zone incorrecte")

if state_c.produit != "sac[VISION]":
    errors.append("❌ CLIENT C: Produit incorrect")
if state_c.zone != "Plateau-1500F[MESSAGE]":
    errors.append("❌ CLIENT C: Zone incorrecte")

if errors:
    print("🔴 ISOLATION ÉCHOUÉE:")
    for error in errors:
        print(f"   {error}")
else:
    print("✅ ISOLATION PARFAITE : Chaque user_id a ses propres données !")
    print("✅ Aucun mélange détecté entre les 3 clients")

print("=" * 80)

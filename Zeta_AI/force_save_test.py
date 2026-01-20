#!/usr/bin/env python3
"""
🔧 TEST DIRECT DU STATE TRACKER - Sans passer par le serveur
"""

from core.order_state_tracker import order_tracker

USER_ID = "client_direct_002"

print("=" * 80)
print("🔧 FORCE SAVE TEST - Sauvegarde directe dans la DB")
print("=" * 80)

# 1. Sauvegarder PRODUIT
order_tracker.update_produit(USER_ID, "lingettes[VISION]")
print("✅ PRODUIT sauvegardé")

# 2. Sauvegarder PAIEMENT
order_tracker.update_paiement(USER_ID, "2020F[VISION]")
print("✅ PAIEMENT sauvegardé")

# 3. Sauvegarder ZONE
order_tracker.update_zone(USER_ID, "Yopougon-1500F[MESSAGE]")
print("✅ ZONE sauvegardée")

# 4. Sauvegarder NUMÉRO
order_tracker.update_numero(USER_ID, "0709876543[MESSAGE]")
print("✅ NUMÉRO sauvegardé")

# 5. Vérifier
state = order_tracker.get_state(USER_ID)
print("\n" + "=" * 80)
print("📊 ÉTAT APRÈS SAUVEGARDE")
print("=" * 80)
print(f"✅ PRODUIT:  {state.produit}")
print(f"✅ PAIEMENT: {state.paiement}")
print(f"✅ ZONE:     {state.zone}")
print(f"✅ NUMÉRO:   {state.numero}")
print("=" * 80)
print(f"📈 Complétion: {state.get_completion_rate():.0%}")
print(f"🎯 Commande complète ? {'OUI ✅' if state.is_complete() else 'NON ❌'}")
print("=" * 80)

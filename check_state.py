#!/usr/bin/env python3
"""
🔍 VÉRIFICATION STATE TRACKER
Affiche l'état de la commande pour un utilisateur
"""

from core.order_state_tracker import order_tracker
import sys

# Accepter user_id en argument ou utiliser le dernier test
USER_ID = sys.argv[1] if len(sys.argv) > 1 else "client_direct_002"

# Récupérer l'état
state = order_tracker.get_state(USER_ID)

print("=" * 80)
print(f"📊 ÉTAT DE LA COMMANDE POUR {USER_ID}")
print("=" * 80)
print(f"✅ PRODUIT:  {state.produit or '❌ VIDE'}")
print(f"✅ PAIEMENT: {state.paiement or '❌ VIDE'}")
print(f"✅ ZONE:     {state.zone or '❌ VIDE'}")
print(f"✅ NUMÉRO:   {state.numero or '❌ VIDE'}")
print("=" * 80)
print(f"📈 Complétion: {state.get_completion_rate():.0%}")
print(f"🎯 Commande complète ? {'OUI ✅' if state.is_complete() else 'NON ❌'}")
print("=" * 80)

# Afficher le format notepad
if state.produit or state.paiement or state.zone or state.numero:
    print("\n📝 FORMAT NOTEPAD:")
    print(state.to_notepad_format())
else:
    print("\n⚠️  AUCUNE DONNÉE SAUVEGARDÉE DANS LE STATE TRACKER")

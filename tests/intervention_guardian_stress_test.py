#!/usr/bin/env python3
"""
Stress-test pour InterventionGuardian

But:
- Forcer le Guardian à analyser plusieurs scénarios difficiles
- Afficher pour chaque appel: décision + usage tokens (prompt, completion, total)
- Calculer le total de tokens utilisés sur l'ensemble du test

Usage:
    python tests/intervention_guardian_stress_test.py
"""

import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

# Assurer l'import des modules du backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from core.intervention_guardian import get_intervention_guardian  # noqa: E402


SCENARIOS = [
    {
        "name": "flux_normal_sans_intervention",
        "conversation_history": (
            "USER: Bonjour, je veux commander des couches taille 4.\n"
            "ASSISTANT: Bien sûr, envoyez-moi une photo du produit ou dites-moi la marque.\n"
            "USER: C'est Pampers Premium Care.\n"
            "ASSISTANT: Merci, maintenant envoyez une preuve de paiement et votre zone.\n"
            "USER: Paiement envoyé, je suis à Cocody.\n"
        ),
        "user_message": "Merci, c'est tout bon pour moi.",
        "bot_response": "Parfait, votre commande est confirmée.",
        "order_state": {
            "produit": "couches",
            "paiement": "2020",
            "zone": "Cocody",
            "numero": "0707070707",
            "completion_rate": 1.0,
            "is_complete": True,
        },
        "next_step": "completed",
        "hard_signals": {
            "explicit_handoff": False,
            "customer_frustration": False,
            "next_step": "completed",
            "order_is_complete": True,
            "completion_rate": 1.0,
        },
    },
    {
        "name": "client_frustre_bloque_sur_paiement",
        "conversation_history": (
            "USER: J'ai déjà envoyé le paiement 3 fois!!! Pourquoi vous ne voyez rien ?\n"
            "ASSISTANT: Je n'ai pas encore reçu de preuve de paiement valide.\n"
            "USER: Mais je te dis que j'ai PAYE, c'est quoi ce service ??!!\n"
        ),
        "user_message": "Vous êtes nuls, je veux parler à quelqu'un de VRAI.",
        "bot_response": "Je ne vois toujours pas le paiement, pouvez-vous renvoyer la capture ?",
        "order_state": {
            "produit": "couches",
            "paiement": None,
            "zone": "Cocody",
            "numero": "0707070707",
            "completion_rate": 0.5,
            "is_complete": False,
        },
        "next_step": "wait_payment",
        "hard_signals": {
            "explicit_handoff": False,
            "customer_frustration": True,
            "next_step": "wait_payment",
            "order_is_complete": False,
            "completion_rate": 0.5,
        },
    },
    {
        "name": "bot_confus_tourne_en_rond",
        "conversation_history": (
            "USER: Je veux juste savoir combien je dois payer en tout.\n"
            "ASSISTANT: Pouvez-vous préciser la zone de livraison ?\n"
            "USER: Cocody.\n"
            "ASSISTANT: Merci, pouvez-vous préciser la zone de livraison ?\n"
            "USER: Je viens de te dire Cocody, tu lis pas ?\n"
            "ASSISTANT: Merci, pouvez-vous préciser la zone de livraison ?\n"
        ),
        "user_message": "Laisse tomber, tu répètes toujours la même chose...",
        "bot_response": "Pouvez-vous préciser la zone de livraison ?",
        "order_state": {
            "produit": "couches",
            "paiement": None,
            "zone": "Cocody",
            "numero": None,
            "completion_rate": 0.5,
            "is_complete": False,
        },
        "next_step": "wait_phone",
        "hard_signals": {
            "explicit_handoff": False,
            "customer_frustration": False,
            "next_step": "wait_phone",
            "order_is_complete": False,
            "completion_rate": 0.5,
        },
    },
    {
        "name": "vip_case_panier_important",
        "conversation_history": (
            "USER: Bonjour, je veux 20 paquets de couches taille 4 pour mon orphelinat.\n"
            "ASSISTANT: Bien sûr, je peux vous aider avec ça.\n"
            "USER: C'est pour une donation, j'ai un budget très serré, vous pouvez faire un geste ?\n"
        ),
        "user_message": "Je peux parler à un responsable pour discuter du prix ?",
        "bot_response": "Je peux vous proposer la livraison gratuite sur Cocody.",
        "order_state": {
            "produit": "couches",
            "paiement": None,
            "zone": "Cocody",
            "numero": "0707070707",
            "completion_rate": 0.75,
            "is_complete": False,
        },
        "next_step": "wait_payment",
        "hard_signals": {
            "explicit_handoff": True,
            "customer_frustration": False,
            "next_step": "wait_payment",
            "order_is_complete": False,
            "completion_rate": 0.75,
        },
    },
]


async def run_stress_test() -> None:
    guardian = get_intervention_guardian()

    total_tokens = 0
    print("\n" + "=" * 80)
    print("🧪 INTERVENTION GUARDIAN STRESS TEST")
    print("Lancement:", datetime.utcnow().isoformat())
    print("=" * 80 + "\n")

    for idx, sc in enumerate(SCENARIOS, start=1):
        print(f"--- Scénario {idx}/{len(SCENARIOS)} : {sc['name']} ---")

        decision = await guardian.analyze(
            conversation_history=sc["conversation_history"],
            user_message=sc["user_message"],
            bot_response=sc["bot_response"],
            order_state=sc["order_state"],
            next_step=sc["next_step"],
            hard_signals=sc["hard_signals"],
        )

        usage = decision.get("_llm_usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        total = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
        total_tokens += total

        print(f"requires_intervention = {decision.get('requires_intervention')}")
        print(f"priority            = {decision.get('priority')} ({decision.get('category')})")
        print(f"confidence          = {decision.get('confidence')}")
        print(f"reason              = {decision.get('reason')}")
        print(f"suggested_message   = {decision.get('suggested_handoff_message')}")
        print(f"tokens              = prompt={prompt_tokens}, completion={completion_tokens}, total={total}")
        print("-" * 80 + "\n")

    print("\n" + "=" * 80)
    print(f"TOTAL LLM TOKENS (Guardian) sur {len(SCENARIOS)} scénarios : {total_tokens}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_stress_test())

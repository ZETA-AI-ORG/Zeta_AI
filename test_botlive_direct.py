#!/usr/bin/env python3
"""
Test direct du process_request Botlive avec les vraies URLs d'images
et logs complets. Pas d'HTTP, appel direct Python.
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Ajouter le projet au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.botlive_rag_hybrid import BotliveRAGHybrid

def log_section(title):
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)

def log_result(result, title="Résultat"):
    print(f"\n--- {title} ---")
    if isinstance(result, dict):
        print(f"llm_used: {result.get('llm_used')}")
        print(f"routing_reason: {result.get('routing_reason')}")
        print(f"router_metrics: {result.get('router_metrics')}")
        print(f"response: {result.get('response')}")
        print(f"success: {result.get('success')}")
    else:
        print(result)

async def test_process_request_direct():
    log_section("TEST DIRECT PROCESS_REQUEST AVEC VRAIES IMAGES")
    
    hybrid = BotliveRAGHybrid(company_id="zeta_ai")
    user_id = "test_user_direct"
    
    # 1. Message texte (zone + numéro)
    log_section("1. Message texte (zone + numéro)")
    result1 = await hybrid.process_request(
        user_id=user_id,
        message="La livraison à Abobo coûte COMBIEN ? mon numero 0787360767",
        context={},
        conversation_history="",
        company_id="zeta_ai"
    )
    log_result(result1, "1. Zone + téléphone")
    
    # 2. Image paiement (OCR)
    log_section("2. Image paiement (OCR)")
    result2 = await hybrid.process_request(
        user_id=user_id,
        message="voici ma preuve de paiement",
        context={
            "images": [
                "https://scontent-atl3-3.xx.fbcdn.net/v/t1.15752-9/597360982_1522361755643073_1046808360937074239_n.jpg?_nc_cat=109&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=hb7QgNIX-GUQ7kNvwGvvtuj&_nc_oc=AdkTUqx9yhjXuGQoB6MjjgODELCqDVx5xJcbFBDiIBwzhWq-datbBB2fNyvGMLyTD8muFGJIojldBlFi-dcNYN18&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-3.xx&oh=03_Q7cD4AGscacRxk_JHwC6eQflUC5FNq4YADPaVuKzZ33-sLCmng&oe=6961323F"
            ],
            "expected_deposit": "2000 FCFA",
            "company_phone": "0787360757"
        },
        conversation_history="",
        company_id="zeta_ai"
    )
    log_result(result2, "2. Paiement OCR")
    
    # 3. Image produit (BLIP)
    log_section("3. Image produit (BLIP)")
    result3 = await hybrid.process_request(
        user_id=user_id,
        message="voici le produit que je veux",
        context={
            "images": [
                "https://scontent-atl3-1.xx.fbcdn.net/v/t1.15752-9/597710904_1147171930913919_423631986694765875_n.jpg?_nc_cat=106&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=3eyOW7QNwAcQ7kNvwH3Zty1&_nc_oc=Adnh1EMEfdyE-OYR7-gxq6M6QqHzb9KAxWO_Z5DSgScDCrW9vX4qGtBDGpZF14lok9xw_zQ90HtzWNk9jS8cabCi&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-1.xx&oh=03_Q7cD4AGp3_aUPnEjxfTUMMzcgu_8DzAlUy0-TBbXej3XfasR2A&oe=696151EA"
            ]
        },
        conversation_history="",
        company_id="zeta_ai"
    )
    log_result(result3, "3. Produit BLIP")
    
    # 4. État final
    log_section("4. État final de la commande")
    try:
        from core.order_state_tracker import order_tracker
        state = order_tracker.get_state(user_id)
        print(f"Produit: {state.produit or 'NON'}")
        print(f"Paiement: {state.paiement or 'NON'}")
        print(f"Zone: {state.zone or 'NON'}")
        print(f"Téléphone: {state.numero or 'NON'}")
        print(f"Complète: {state.is_complete()}")
    except Exception as e:
        print(f"Impossible de lire l'état: {e}")

    log_section("FIN DU TEST DIRECT")

if __name__ == "__main__":
    asyncio.run(test_process_request_direct())

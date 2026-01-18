#!/usr/bin/env python3
"""
Test FINAL BOTLIVE - Basé sur botlive_simulator.py (sans problème .env)
Utilise la même approche directe que botlive_simulator.py pour éviter les problèmes d'environnement
"""

import re
import asyncio
import sys
import os
import time
from datetime import datetime
import uuid
import json
import logging

# Configuration pour réduire les logs DÈS LE DÉBUT
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger('app').setLevel(logging.WARNING)
logging.getLogger('core').setLevel(logging.WARNING)
logging.getLogger('routes').setLevel(logging.WARNING)

# Ajouter le path parent pour imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

# Configuration test (identique à botlive_simulator.py)
TEST_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"
TEST_USER_ID = f"test_final_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
TEST_COMPANY_NAME = "Test Final Client"

# URLs images (identiques à botlive_simulator.py)
PRODUCT_IMAGE_URL = "https://scontent-atl3-1.xx.fbcdn.net/v/t1.15752-9/597710904_1147171930913919_423631986694765875_n.jpg?_nc_cat=106&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=3eyOW7QNwAcQ7kNvwH3Zty1&_nc_oc=Adnh1EMEfdyE-OYR7-gxq6M6QqHzb9KAxWO_Z5DSgScDCrW9vX4qGtBDGpZF14lok9xw_zQ90HtzWNk9jS8cabCi&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-1.xx&oh=03_Q7cD4AGp3_aUPnEjxfTUMMzcgu_8DzAlUy0-TBbXej3XfasR2A&oe=696151EA"
PAYMENT_IMAGE_URL = "https://scontent-atl3-3.xx.fbcdn.net/v/t1.15752-9/597360982_1522361755643073_1046808360937074239_n.jpg?_nc_cat=109&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=hb7QgNIX-GUQ7kNvwGvvtuj&_nc_oc=AdkTUqx9yhjXuGQoB6MjjgODELCqDVx5xJcbFBDiIBwzhWq-datbBB2fNyvGMLyTD8muFGJIojldBlFi-dcNYN18&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-3.xx&oh=03_Q7cD4AGscacRxk_JHwC6eQflUC5FNq4YADPaVuKzZ33-sLCmng&oe=6961323F"

def log_section(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)

def log_turn(turn_num, question, result, execution_time):
    print(f"\n--- TOUR {turn_num} ---")
    print(f"Q: {question}")
    
    # Type de réponse
    llm_used = result.get('llm_used', 'unknown')
    print(f"Type: {llm_used.upper()}")
    
    # Router info
    router = result.get('router', {})
    if router:
        print(f"Router: {router.get('intent')} ({router.get('confidence', 0):.2f})")
    
    # Tokens et coût
    prompt_tokens = result.get('prompt_tokens', 0)
    completion_tokens = result.get('completion_tokens', 0)
    total_cost = result.get('total_cost', 0)
    if prompt_tokens > 0:
        print(f"Tokens: {prompt_tokens}+{completion_tokens} (${total_cost:.4f})")
    
    print(f"Temps: {execution_time:.0f}ms")
    
    # Réponse
    response_text = result.get('response', '').strip()
    if response_text:
        print(f"R: {response_text}")
    
    # Order status
    order_status = result.get('order_status', {})
    if order_status:
        completion = order_status.get('completion_rate', 0)
        print(f"Order: {completion:.0%} complet")
    
    print("-" * 30)

async def send_message(message: str, images: list = None, conversation_history: str = ""):
    """Envoie un message au bot (copié de botlive_simulator.py)

    NOTE: On ne modifie pas le texte ici, on se contente de passer
    `message` et `images` tels qu'on les reçoit, comme dans le simulateur.
    La logique de détection des URLs d'images est gérée dans le scénario.
    """
    images = images or []

    try:
        message_text = message
        # Appeler directement la route FastAPI process_botlive_message
        from fastapi import BackgroundTasks
        from routes.botlive import BotliveMessageRequest, process_botlive_message
        
        start = time.time()
        
        req = BotliveMessageRequest(
            company_id=TEST_COMPANY_ID,
            user_id=TEST_USER_ID,
            message=message_text,
            images=images,
            conversation_history=conversation_history,
            user_display_name=TEST_COMPANY_NAME,
        )
        background_tasks = BackgroundTasks()
        
        response = await process_botlive_message(req, background_tasks)
        
        duration_ms = int((time.time() - start) * 1000)
        
        # Décoder la réponse JSON
        raw_body = response.body
        if isinstance(raw_body, (bytes, bytearray)):
            raw_body = raw_body.decode("utf-8", errors="ignore")
        else:
            raw_body = str(raw_body)

        result = json.loads(raw_body) if raw_body else {}
        
        return result, duration_ms
        
    except Exception as e:
        print(f"Erreur envoi message: {e}")
        return {"response": f"Erreur: {e}", "llm_used": "error"}, 0

async def test_scenario_final():
    log_section("TEST FINAL BOTLIVE - SYSTÈME COMPLET")
    print(f"User ID: {TEST_USER_ID}")
    print(f"Company ID: {TEST_COMPANY_ID}")
    
    # Messages du scénario simple
    messages = [
        "Bonjour, je veux commander",
        "Où êtes-vous situés exactement ? Vous avez des locaux physiques ?",
        f"Voici mon produit : https://scontent-atl3-1.xx.fbcdn.net/v/t1.15752-9/597710904_1147171930913919_423631986694765875_n.jpg?_nc_cat=106&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=3eyOW7QNwAcQ7kNvwH3Zty1&_nc_oc=Adnh1EMEfdyE-OYR7-gxq6M6QqHzb9KAxWO_Z5DSgScDCrW9vX4qGtBDGpZF14lok9xw_zQ90HtzWNk9jS8cabCi&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-1.xx&oh=03_Q7cD4AGp3_aUPnEjxfTUMMzcgu_8DzAlUy0-TBbXej3XfasR2A&oe=696151EA",
        f"Voici mon paiement : https://scontent-atl3-3.xx.fbcdn.net/v/t1.15752-9/597360982_1522361755643073_1046808360937074239_n.jpg?_nc_cat=109&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=hb7QgNIX-GUQ7kNvwGvvtuj&_nc_oc=AdkTUqx9yhjXuGQoB6MjjgODELCqDVx5xJcbFBDiIBwzhWq-datbBB2fNyvGMLyTD8muFGJIojldBlFi-dcNYN18&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-3.xx&oh=03_Q7cD4AGscacRxk_JHwC6eQflUC5FNq4YADPaVuKzZ33-sLCmng&oe=6961323F",
        "Je suis à Abobo",
        "Mon numéro : 0707070707",
        "On paye à la livraison ou c'est avant ?",
        "Je serais livré quand ?",
        "Oui c'est bon, confirmez ma commande"
    ]
    
    conversation_history = ""
    turns_data = []  # Pour le bilan dynamique

    for i, message in enumerate(messages, 1):
        # Images explicites pour reproduire le comportement du simulateur
        images = []
        if "Voici mon produit" in message:
            images = [PRODUCT_IMAGE_URL]
        elif "Voici mon paiement" in message:
            images = [PAYMENT_IMAGE_URL]

        result, execution_time = await send_message(message, images=images, conversation_history=conversation_history)
        
        log_turn(i, message, result, execution_time)
        
        # Mettre à jour l'historique
        response_text = result.get('response', '').strip()
        if response_text:
            conversation_history += f"USER: {message}\nASSISTANT: {response_text}\n"

        # Enregistrer les données du tour pour le bilan
        order_status = result.get('order_status', {}) or {}
        completion = order_status.get('completion_rate')
        if isinstance(completion, (int, float)):
            order_percent = int(completion * 100)
        else:
            order_percent = 0

        turns_data.append({
            "turn": i,
            "question": message,
            "response": response_text,
            "time_ms": execution_time,
            "order_percent": order_percent,
            "llm_used": result.get('llm_used'),
            "raw_result": result,
        })
    
    # État final
    log_section("ÉTAT FINAL")
    final_state = {}
    try:
        from core.order_state_tracker import order_tracker
        state = order_tracker.get_state(TEST_USER_ID)
        print(f"Produit: {state.produit or 'NON'}")
        print(f"Paiement: {state.paiement or 'NON'}")
        print(f"Zone: {state.zone or 'NON'}")
        print(f"Téléphone: {state.numero or 'NON'}")
        print(f"Complète: {state.is_complete()}")

        final_state = {
            "produit": state.produit,
            "paiement": state.paiement,
            "zone": state.zone,
            "telephone": state.numero,
            "complete": bool(state.is_complete()),
        }
    except Exception as e:
        print(f"Erreur: {e}")
        final_state = {"error": str(e)}

    # Sauvegarde des résultats pour le bilan dynamique
    try:
        results = {
            "turns": turns_data,
            "final_state": final_state,
        }
        out_path = os.path.join(project_root, "test_scenario_final_results.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n[DEBUG] Résultats sauvegardés dans {out_path}")
    except Exception as e:
        print(f"[WARN] Impossible d'écrire le fichier de résultats: {e}")

if __name__ == "__main__":
    asyncio.run(test_scenario_final())

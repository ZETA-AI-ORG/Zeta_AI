#!/usr/bin/env python3
"""
Test Scenario SIMPLE avec logs détaillés pour analyser :
- Question client
- Routage embedding (score)
- Prompt envoyé
- Réponse Python vs Bot
- Token counts et coûts
- Temps d'exécution
"""

import asyncio
import sys
import os
import time
from datetime import datetime

# Ajouter le projet au PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.botlive_rag_hybrid import BotliveRAGHybrid

def log_section(title):
    print("\n" + "="*100)
    print(f" {title}")
    print("="*100)

def log_turn(turn_num, question, response_data, execution_time):
    print(f"\n--- TOUR {turn_num} ---")
    print(f"Question client: {question}")
    print(f"Temps exécution: {execution_time:.0f}ms")
    
    # Métadonnées de routage
    router_info = response_data.get('router', {})
    if router_info:
        print(f"Routage embedding:")
        print(f"  - Intent: {router_info.get('intent')}")
        print(f"  - Score: {router_info.get('confidence'):.3f}")
        print(f"  - Mode: {router_info.get('mode')}")
    
    # Type de réponse
    llm_used = response_data.get('llm_used', 'unknown')
    print(f"Type réponse: {llm_used.upper()}")
    
    # Tokens et coûts
    prompt_tokens = response_data.get('prompt_tokens', 0)
    completion_tokens = response_data.get('completion_tokens', 0)
    total_cost = response_data.get('total_cost', 0)
    if prompt_tokens > 0 or completion_tokens > 0:
        print(f"Tokens: {prompt_tokens} + {completion_tokens} = {prompt_tokens + completion_tokens}")
        print(f"Coût: ${total_cost:.6f}")
    
    # Réponse
    response_text = response_data.get('response', '').strip()
    if response_text:
        print(f"Réponse: {response_text}")
    
    # Router metrics
    router_metrics = response_data.get('router_metrics', {})
    if router_metrics:
        print(f"Router metrics: {router_metrics}")
    
    print("-" * 50)

async def test_scenario_simple_logs():
    log_section("TEST SCENARIO SIMPLE - LOGS DÉTAILLÉS")
    
    hybrid = BotliveRAGHybrid(company_id="zeta_ai")
    user_id = "test_simple_logs"
    
    # Messages du scénario simple
    messages = [
        "Bonjour, je veux commander",
        "Où êtes-vous situés exactement ? Vous avez des locaux physiques ?",
        "Je veux des couches Pampers taille 4",
        "Voici mon paiement : https://scontent-atl3-3.xx.fbcdn.net/v/t1.15752-9/597360982_1522361755643073_1046808360937074239_n.jpg?_nc_cat=109&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=hb7QgNIX-GUQ7kNvwGvvtuj&_nc_oc=AdkTUqx9yhjXuGQoB6MjjgODELCqDVx5xJcbFBDiIBwzhWq-datbBB2fNyvGMLyTD8muFGJIojldBlFi-dcNYN18&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-3.xx&oh=03_Q7cD4AGscacRxk_JHwC6eQflUC5FNq4YADPaVuKzZ33-sLCmng&oe=6961323F",
        "Je suis à Abobo",
        "Mon numéro : 0707070707",
        "On paye à la livraison ou c'est avant ?",
        "Je serais livré quand ?",
        "Oui c'est bon, confirmez ma commande"
    ]
    
    conversation_history = ""
    
    for i, message in enumerate(messages, 1):
        # Détecter si c'est une URL d'image
        images = []
        if message.startswith('https://') and any(img_key in message for img_key in ['jpg', 'jpeg', 'png']):
            images = [message]
        
        start_time = time.time()
        
        response_data = await hybrid.process_request(
            user_id=user_id,
            message=message,
            context={'images': images} if images else {},
            conversation_history=conversation_history,
            company_id="zeta_ai"
        )
        
        execution_time = (time.time() - start_time) * 1000
        
        log_turn(i, message, response_data, execution_time)
        
        # Mettre à jour l'historique
        response_text = response_data.get('response', '').strip()
        if response_text:
            conversation_history += f"USER: {message}\nASSISTANT: {response_text}\n"
    
    # Résumé final
    log_section("RÉSUMÉ FINAL")
    try:
        from core.order_state_tracker import order_tracker
        state = order_tracker.get_state(user_id)
        print(f"État final:")
        print(f"  - Produit: {state.produit or 'NON'}")
        print(f"  - Paiement: {state.paiement or 'NON'}")
        print(f"  - Zone: {state.zone or 'NON'}")
        print(f"  - Téléphone: {state.numero or 'NON'}")
        print(f"  - Complète: {state.is_complete()}")
    except Exception as e:
        print(f"Impossible de lire l'état final: {e}")

if __name__ == "__main__":
    asyncio.run(test_scenario_simple_logs())

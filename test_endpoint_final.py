#!/usr/bin/env python3
"""
Test FINAL endpoint Botlive avec système complet (LLM + Python + routing)
Test via l'API HTTP complète comme un vrai client
"""

import asyncio
import json
import requests
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8002"  # Backend endpoint
USER_ID = "test_final_complete"
COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"

# URLs images
URL_PAIEMENT = "https://scontent-atl3-3.xx.fbcdn.net/v/t1.15752-9/597360982_1522361755643073_1046808360937074239_n.jpg?_nc_cat=109&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=hb7QgNIX-GUQ7kNvwGvvtuj&_nc_oc=AdkTUqx9yhjXuGQoB6MjjgODELCqDVx5xJcbFBDiIBwzhWq-datbBB2fNyvGMLyTD8muFGJIojldBlFi-dcNYN18&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-3.xx&oh=03_Q7cD4AGscacRxk_JHwC6eQflUC5FNq4YADPaVuKzZ33-sLCmng&oe=6961323F"
URL_PRODUIT = "https://scontent-atl3-1.xx.fbcdn.net/v/t1.15752-9/597710904_1147171930913919_423631986694765875_n.jpg?_nc_cat=106&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=3eyOW7QNwAcQ7kNvwH3Zty1&_nc_oc=Adnh1EMEfdyE-OYR7-gxq6M6QqHzb9KAxWO_Z5DSgScDCrW9vX4qGtBDGpZF14lok9xw_zQ90HtzWNk9jS8cabCi&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-1.xx&oh=03_Q7cD4AGp3_aUPnEjxfTUMMzcgu_8DzAlUy0-TBbXej3XfasR2A&oe=696151EA"

def log_section(title):
    print("\n" + "="*100)
    print(f" {title}")
    print("="*100)

def log_turn(turn_num, question, response_data, execution_time):
    print(f"\n--- TOUR {turn_num} ---")
    print(f"Question: {question}")
    print(f"Temps: {execution_time:.0f}ms")
    
    # Type de réponse
    llm_used = response_data.get('llm_used', 'unknown')
    print(f"Type: {llm_used.upper()}")
    
    # Router info
    router = response_data.get('router', {})
    if router:
        print(f"Router: {router.get('intent')} (score: {router.get('confidence', 0):.3f})")
    
    # Router metrics
    metrics = response_data.get('router_metrics', {})
    if metrics:
        print(f"Metrics: {metrics}")
    
    # Tokens et coût
    prompt_tokens = response_data.get('prompt_tokens', 0)
    completion_tokens = response_data.get('completion_tokens', 0)
    total_cost = response_data.get('total_cost', 0)
    if prompt_tokens > 0:
        print(f"Tokens: {prompt_tokens}+{completion_tokens}={prompt_tokens+completion_tokens} (${total_cost:.6f})")
    
    # Réponse
    response_text = response_data.get('response', '').strip()
    if response_text:
        print(f"Réponse: {response_text}")
    
    # Order status
    order_status = response_data.get('order_status', {})
    if order_status:
        print(f"Order: {order_status}")
    
    print("-" * 50)

async def test_endpoint_final():
    log_section("TEST FINAL ENDPOINT - SYSTÈME COMPLET")
    
    session = requests.Session()
    
    # Messages du scénario simple
    messages = [
        "Bonjour, je veux commander",
        "Où êtes-vous situés exactement ? Vous avez des locaux physiques ?",
        "Je veux des couches Pampers taille 4",
        f"Voici mon paiement : {URL_PAIEMENT}",
        "Je suis à Abobo",
        "Mon numéro : 0707070707",
        "On paye à la livraison ou c'est avant ?",
        "Je serais livré quand ?",
        "Oui c'est bon, confirmez ma commande"
    ]
    
    conversation_history = ""
    
    for i, message in enumerate(messages, 1):
        # Détecter images
        images = []
        if message.startswith('https://') and ('jpg' in message or 'jpeg' in message or 'png' in message):
            images = [message]
        
        # Préparer payload
        payload = {
            "company_id": COMPANY_ID,
            "user_id": USER_ID,
            "message": message,
            "images": images,
            "conversation_history": conversation_history,
            "user_display_name": "Test Final Client"
        }
        
        start_time = time.time()
        
        try:
            response = session.post(
                f"{BASE_URL}/chat/botlive",
                json=payload,
                timeout=60
            )
            execution_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                response_data = response.json()
                log_turn(i, message, response_data, execution_time)
                
                # Mettre à jour l'historique
                response_text = response_data.get('response', '').strip()
                if response_text:
                    conversation_history += f"USER: {message}\nASSISTANT: {response_text}\n"
            else:
                print(f"\n--- TOUR {i} ---")
                print(f"Question: {message}")
                print(f"ERREUR HTTP: {response.status_code}")
                print(f"Response: {response.text}")
                print("-" * 50)
                
        except Exception as e:
            print(f"\n--- TOUR {i} ---")
            print(f"Question: {message}")
            print(f"ERREUR: {e}")
            print("-" * 50)
    
    # État final
    log_section("ÉTAT FINAL DE LA COMMANDE")
    try:
        # Appeler l'endpoint pour récupérer l'état
        state_response = session.get(
            f"{BASE_URL}/order/state/{USER_ID}",
            timeout=10
        )
        if state_response.status_code == 200:
            state_data = state_response.json()
            print(f"Produit: {state_data.get('produit', 'NON')}")
            print(f"Paiement: {state_data.get('paiement', 'NON')}")
            print(f"Zone: {state_data.get('zone', 'NON')}")
            print(f"Téléphone: {state_data.get('numero', 'NON')}")
            print(f"Complète: {state_data.get('is_complete', False)}")
        else:
            print(f"Impossible de récupérer l'état: {state_response.status_code}")
    except Exception as e:
        print(f"Erreur récupération état: {e}")

if __name__ == "__main__":
    asyncio.run(test_endpoint_final())

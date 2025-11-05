#!/usr/bin/env python3
"""
TEST BOTLIVE MICRO SCENARIO (OCR + paiement)

- Teste le flow Botlive complet avec images réelles de paiement (OCR)
- 1er paiement insuffisant, 2e paiement correct
- Affiche tous les logs utiles (prompt, contexte, réponse LLM)

Usage:
    python tests/botlive_micro.py
"""
import asyncio
import sys
import os
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Paramètres test
TEST_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"
TEST_USER_ID = "test_botlive_micro"

# Scénario micro OCR (extrait de test_scenarios.py)
SCENARIO_MICRO = [
    {"text": "Voici mon paiement Wave", "image_url": "https://scontent.xx.fbcdn.net/v/t1.15752-9/553547596_833613639156226_7121847885682360094_n.jpg?_nc_cat=101&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=DamxAq1f9OwQ7kNvwFSbPlg&_nc_oc=AdlYZF2Q2WyPz7SoP6HFp7gZCnmgAysN4ZCziXM2nHv8itrZrced2lMSff1szWQ9V-7WRbl3vV_-uJ9l3-Uxq7ha&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gFO-SvfS03vBW39la32NGTcsXuPEGNsnVA6mSvUHOResw&oe=691D864A"},
    "Ok je renvoie le bon montant",
    {"text": "Voilà 2000 FCFA", "image_url": "https://scontent.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215345539018_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=7oeAkz1vXk4Q7kNvwHsBEm8&_nc_oc=AdkRG6vf8C7mCWK6G0223SycGhXGPZ9S5mn8iK369aoCBNGNFLGSYK0R-yFITkJ-uro_BO7rcX9W2ximO0S4l25C&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gFy4KBx2MWFGHs3HzwWsG7vQiUcM4NU3IBpkP2B5ZoWAQ&oe=691D9DCA"}
]

async def run_micro():
    import app
    conversation_history = ""
    for i, turn in enumerate(SCENARIO_MICRO, 1):
        print(f"\n{'='*80}\nTOUR {i}")
        if isinstance(turn, dict):
            message = turn["text"]
            images = [turn["image_url"]]
        else:
            message = turn
            images = []
        print(f"[USER] {message}")
        if images:
            print(f"[IMAGES] {images}")
        # Appel Botlive
        response = await app._botlive_handle(
            company_id=TEST_COMPANY_ID,
            user_id=TEST_USER_ID,
            message=message,
            images=images,
            conversation_history=conversation_history
        )
        print(f"[BOT] {response}\n")
        # Ajout à l'historique
        conversation_history += f"USER: {message}\n"
        conversation_history += f"ASSISTANT: {response}\n"

if __name__ == "__main__":
    asyncio.run(run_micro())

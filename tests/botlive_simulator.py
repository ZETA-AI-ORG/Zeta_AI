#!/usr/bin/env python3
"""
🤖 BOTLIVE CONVERSATION SIMULATOR - Test en Direct

Simule une conversation de commande Botlive complète:
- Envoi de produit (texte ou image)
- Envoi de paiement (image)
- Confirmation zone et numéro
- Validation finale

Usage:
    python tests/botlive_simulator.py
"""

import asyncio
import sys
import os
from datetime import datetime
import uuid
import json

# Ajouter le path parent pour imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Configuration test
TEST_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"  # Company ID mis à jour
# Générer un user_id UNIQUE à chaque exécution pour repartir de zéro
TEST_USER_ID = f"test_botlive_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
TEST_COMPANY_NAME = "Test Company"

# URLs d'images réelles pour les tests (produit et paiement)
PRODUCT_IMAGE_URL = "https://scontent-atl3-3.xx.fbcdn.net/v/t1.15752-9/553786504_1339650347521010_7584722332323008254_n.jpg?_nc_cat=108&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=wI6F404RotMQ7kNvwEnhydb&_nc_oc=AdmqrPkDq5bTSUqR3fv3g0PrvQbXW9_9Frci7xyQgQ0werBvu95Sz_8rw99dCA-tpPzw_VcH2vgb6kW0y9q-RJI2&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-3.xx&oh=03_Q7cD3wFOCg_nyFNqiAFZ2JtXL-o6TYQJotUYQ0L6mr8mM1BA7g&oe=6938095A"
PAYMENT_IMAGE_URL = "https://scontent-atl3-2.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215345539018_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=NL64Tr-lCD8Q7kNvwErQP-W&_nc_oc=Adl-2TTfwDiQ5oV7zD-apLFr6CXVJRBTBS-bGX0OviLygK6yEzKDt_DLemHYyuo4jsHi52BxJLiX6eXRztPxh2Dk&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-2.xx&oh=03_Q7cD3wHQnpKrTBJ4ECMmlxUMRVy5tPvbnhlsvGwaT0Dt2xJwcg&oe=6937FBCA"


class BotliveSimulator:
    """Simulateur de conversation Botlive interactive"""
    
    def __init__(self):
        self.conversation_history = ""
        self.turn_number = 0
        
    def add_to_history(self, role: str, message: str):
        """Ajoute un message à l'historique"""
        self.conversation_history += f"{role}: {message}\n"
    
    async def send_message(self, message: str, images: list = None):
        """Envoie un message au bot et affiche la réponse"""
        self.turn_number += 1
        images = images or []
        
        print(f"\n{'='*80}")
        print(f"🗣️  TOUR {self.turn_number} - VOUS")
        print(f"{'='*80}")
        print(f"Message: {message}")
        if images:
            print(f"Images: {images}")
        print()
        
        # Ajouter à l'historique
        self.add_to_history("USER", message)
        
        try:
            # Appeler directement la route FastAPI process_botlive_message dans le même process
            # pour bénéficier de TOUTES les logs (loop_botlive_engine, Guardian, interventions, etc.)
            import time
            from fastapi import BackgroundTasks
            from routes.botlive import BotliveMessageRequest, process_botlive_message
            
            start = time.time()
            
            req = BotliveMessageRequest(
                company_id=TEST_COMPANY_ID,
                user_id=TEST_USER_ID,
                message=message,
                images=images,
                conversation_history=self.conversation_history,
                user_display_name=TEST_COMPANY_NAME,
            )
            background_tasks = BackgroundTasks()
            
            response = await process_botlive_message(req, background_tasks)
            
            duration_ms = int((time.time() - start) * 1000)
            
            # JSONResponse -> décoder le body
            raw_body = response.body.decode("utf-8") if isinstance(response.body, (bytes, bytearray)) else str(response.body)
            result = json.loads(raw_body)
            
            bot_response = result.get("response", "")
            next_step = result.get("next_step")
            order_status = result.get("order_status")
            
            # Ajouter la réponse à l'historique local pour le contexte affiché
            if bot_response:
                self.add_to_history("ASSISTANT", bot_response)
            
            # Afficher la réponse et les métadonnées de flux Botlive
            print(f"🤖 BOT (réponse en {duration_ms}ms)")
            print(f"{'='*80}")
            print(bot_response if bot_response else "[Aucune réponse bot - potentielle intervention humaine]")
            print(f"{'='*80}")
            print(f"next_step: {next_step}")
            print(f"order_status: {order_status}\n")
            
            return result
            
        except Exception as e:
            print(f"❌ ERREUR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def run_interactive(self):
        """Mode interactif : conversation en direct"""
        print("\n" + "="*80)
        print("🤖 BOTLIVE SIMULATOR - Mode Interactif")
        print("="*80)
        print("\nCommandes disponibles:")
        print("  - Tapez votre message normalement")
        print("  - 'quit' ou 'exit' pour quitter")
        print("  - 'history' pour voir l'historique")
        print("  - 'reset' pour recommencer")
        print("\n" + "="*80 + "\n")
        
        while True:
            try:
                # Demander le message
                user_input = input("🗣️  VOUS: ").strip()
                
                if not user_input:
                    continue
                
                # Commandes spéciales
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Au revoir !\n")
                    break
                
                if user_input.lower() == 'history':
                    print("\n📜 HISTORIQUE:")
                    print("="*80)
                    print(self.conversation_history)
                    print("="*80 + "\n")
                    continue
                
                if user_input.lower() == 'reset':
                    self.conversation_history = ""
                    self.turn_number = 0
                    print("\n🔄 Conversation réinitialisée\n")
                    continue
                
                # 🔥 DÉTECTION URL IMAGE (comme dans l'appli réelle)
                images = []
                if user_input.startswith('http://') or user_input.startswith('https://'):
                    # C'est une URL d'image
                    images = [user_input]
                    print(f"📸 [SIMULATOR] URL image détectée: {user_input[:80]}...")
                
                # Envoyer le message avec images si détectées
                await self.send_message(user_input, images=images)
                
            except KeyboardInterrupt:
                print("\n\n👋 Interruption - Au revoir !\n")
                break
            except Exception as e:
                print(f"\n❌ ERREUR: {e}\n")
    
    async def run_scenario(self):
        """Scénario de test automatique"""
        print("\n" + "="*80)
        print("🤖 BOTLIVE SIMULATOR - Scénario Automatique")
        print("="*80 + "\n")
        
        # Étape 1 : Demande initiale
        await self.send_message("Bonjour, je veux commander")
        
        # Étape 2 : Produit (texte + image produit réelle passée via `images`)
        await self.send_message(
            "Je veux des couches Pampers taille 4 (voir la photo)",
            images=[PRODUCT_IMAGE_URL],
        )
        
        # Étape 3 : Paiement (message texte contenant l'URL de l'image pour tester l'extracteur d'URL)
        await self.send_message(f"Voici mon paiement : {PAYMENT_IMAGE_URL}")
        
        # Étape 4 : Zone
        await self.send_message("Je suis à Cocody Riviera")
        
        # Étape 5 : Numéro
        await self.send_message("Mon numéro c'est 0707070707")
        
        # Étape 6 : Confirmation
        await self.send_message("Oui c'est bon")
        
        print("\n" + "="*80)
        print("✅ SCÉNARIO TERMINÉ")
        print("="*80 + "\n")


async def main():
    """Point d'entrée principal"""
    simulator = BotliveSimulator()
    print("\n" + "="*80)
    print(f"🧪 BOTLIVE SIMULATOR - TEST_USER_ID: {TEST_USER_ID}")
    print("="*80 + "\n")
    
    # Vérifier les arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--scenario":
        # Mode scénario automatique
        await simulator.run_scenario()
    else:
        # Mode interactif par défaut
        await simulator.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())

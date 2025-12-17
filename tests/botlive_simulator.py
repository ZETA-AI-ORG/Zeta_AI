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
import csv
from pathlib import Path

# Ajouter le path parent pour imports, en le mettant EN PREMIER dans sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

# Configuration test
TEST_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"  # Company ID mis à jour
# Générer un user_id UNIQUE à chaque exécution pour repartir de zéro
TEST_USER_ID = f"test_botlive_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
TEST_COMPANY_NAME = "Test Company"

# URLs d'images réelles pour les tests (produit et paiement) - mises à jour 2025-12-11
PRODUCT_IMAGE_URL = "https://scontent-atl3-1.xx.fbcdn.net/v/t1.15752-9/597710904_1147171930913919_423631986694765875_n.jpg?_nc_cat=106&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=3eyOW7QNwAcQ7kNvwH3Zty1&_nc_oc=Adnh1EMEfdyE-OYR7-gxq6M6QqHzb9KAxWO_Z5DSgScDCrW9vX4qGtBDGpZF14lok9xw_zQ90HtzWNk9jS8cabCi&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-1.xx&oh=03_Q7cD4AGp3_aUPnEjxfTUMMzcgu_8DzAlUy0-TBbXej3XfasR2A&oe=696151EA"
PAYMENT_IMAGE_URL = "https://scontent-atl3-3.xx.fbcdn.net/v/t1.15752-9/597360982_1522361755643073_1046808360937074239_n.jpg?_nc_cat=109&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=hb7QgNIX-GUQ7kNvwGvvtuj&_nc_oc=AdkTUqx9yhjXuGQoB6MjjgODELCqDVx5xJcbFBDiIBwzhWq-datbBB2fNyvGMLyTD8muFGJIojldBlFi-dcNYN18&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-3.xx&oh=03_Q7cD4AGscacRxk_JHwC6eQflUC5FNq4YADPaVuKzZ33-sLCmng&oe=6961323F"


class BotliveSimulator:
    """Simulateur de conversation Botlive interactive"""
    
    def __init__(self):
        self.conversation_history = ""
        self.turn_number = 0
        self.eval_rows = []  # Collecte des mesures de routage pour le scénario
        
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
            
            # JSONResponse -> décoder le body de manière robuste
            raw_body = response.body
            if isinstance(raw_body, (bytes, bytearray)):
                raw_body = raw_body.decode("utf-8", errors="ignore")
            else:
                raw_body = str(raw_body)

            result = json.loads(raw_body) if raw_body else {}

            bot_response = (result.get("response") or "").strip()
            next_step = result.get("next_step")
            order_status = result.get("order_status")
            
            # Ajouter la réponse à l'historique local pour le contexte affiché
            if bot_response:
                self.add_to_history("ASSISTANT", bot_response)

            # Enregistrement évaluation: si le routeur embeddings a répondu, on logge
            try:
                router = result.get("router") or {}
                if router:
                    self.eval_rows.append(
                        {
                            "turn": self.turn_number,
                            "message": message,
                            "conversation_history": self.conversation_history,
                            "intent": router.get("intent"),
                            "confidence": router.get("confidence"),
                            "mode": router.get("mode"),
                            "missing_fields": ",".join(router.get("missing_fields") or []),
                            "state": json.dumps(router.get("state") or {}, ensure_ascii=False),
                        }
                    )
            except Exception:
                # Ne jamais casser la simulation à cause des logs d'évaluation
                pass
            
            # Afficher la réponse et les métadonnées de flux Botlive
            print(f"🤖 BOT (réponse en {duration_ms}ms)")
            print(f"{'='*80}")
            # Toujours afficher la réponse texte si disponible
            if bot_response:
                print(bot_response)
            else:
                print("[Aucune réponse bot - potentielle intervention humaine]")
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

        # Sauvegarde CSV d'évaluation du scénario
        try:
            out_path = Path("tests/botlive_scenario_results.csv")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(
                    f,
                    fieldnames=[
                        "turn",
                        "message",
                        "conversation_history",
                        "intent",
                        "confidence",
                        "mode",
                        "missing_fields",
                        "state",
                    ],
                )
                w.writeheader()
                for r in self.eval_rows:
                    w.writerow(r)
            print(f"\nCSV saved: {out_path}\n")
        except Exception as e:
            print(f"\n[WARN] Impossible d'écrire le CSV scénario: {e}\n")

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

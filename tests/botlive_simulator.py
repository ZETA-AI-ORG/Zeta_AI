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

# Ajouter le path parent pour imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Configuration test
TEST_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"  # Company ID mis à jour
TEST_USER_ID = "test_botlive_simulator"
TEST_COMPANY_NAME = "Test Company"


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
            # Import de la fonction botlive
            import app
            
            # Appeler la fonction botlive
            import time
            start = time.time()
            
            response = await app._botlive_handle(
                company_id=TEST_COMPANY_ID,
                user_id=TEST_USER_ID,
                message=message,
                images=images,
                conversation_history=self.conversation_history
            )
            
            duration_ms = int((time.time() - start) * 1000)
            
            # Ajouter la réponse à l'historique
            self.add_to_history("ASSISTANT", response)
            
            # Afficher la réponse
            print(f"🤖 BOT (réponse en {duration_ms}ms)")
            print(f"{'='*80}")
            print(response)
            print(f"{'='*80}\n")
            
            return response
            
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
                
                # Envoyer le message
                await self.send_message(user_input)
                
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
        
        # Étape 2 : Produit
        await self.send_message("Je veux des couches Pampers taille 4")
        
        # Étape 3 : Paiement
        await self.send_message("J'ai payé 5000 FCFA par Orange Money")
        
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
    
    # Vérifier les arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--scenario":
        # Mode scénario automatique
        await simulator.run_scenario()
    else:
        # Mode interactif par défaut
        await simulator.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())

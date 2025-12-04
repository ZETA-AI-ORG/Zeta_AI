#!/usr/bin/env python3
"""
🧪 HYDE v18 INTENT SIMULATOR

But: Tester rapidement le routeur d'intention HYDE v18 SANS lancer tout le backend Botlive.

Usage:
    python tests/hyde_v18_simulator.py
        → Mode interactif (vous tapez des messages)

    python tests/hyde_v18_simulator.py --scenario
        → Scénario automatique avec plusieurs messages typiques
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

# Configuration test (même company_id que le simulateur Botlive)
TEST_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"
TEST_USER_ID = f"test_hyde_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


class HydeSimulator:
    """Simulateur simple pour HYDE v18 (intent + risque)"""

    def __init__(self):
        self.conversation_history = ""
        self.turn_number = 0
        self.user_id = TEST_USER_ID

    def add_to_history(self, role: str, message: str) -> None:
        self.conversation_history += f"{role}: {message}\n"

    async def call_hyde(self, message: str):
        """Appelle run_hyde_v18 et affiche le JSON de sortie"""
        from core.hyde_v18_layer import run_hyde_v18

        self.turn_number += 1

        print("\n" + "=" * 80)
        print(f"🗣️  TOUR {self.turn_number} - VOUS")
        print("=" * 80)
        print(f"Message: {message}\n")

        # Mettre à jour l'historique côté simulateur
        self.add_to_history("USER", message)

        try:
            result = await run_hyde_v18(
                company_id=TEST_COMPANY_ID,
                user_id=self.user_id,
                message=message,
                conversation_history=self.conversation_history,
            )

            print("🤖 HYDE v18 - RÉSULTAT")
            print("=" * 80)
            print(
                json.dumps(
                    result,
                    indent=2,
                    ensure_ascii=False,
                )
            )
            print("=" * 80 + "\n")

            return result

        except Exception as e:
            print(f"❌ ERREUR HYDE v18: {type(e).__name__}: {e}")
            import traceback

            traceback.print_exc()
            return None

    async def run_interactive(self):
        """Mode interactif: vous tapez des messages, on voit l'intent HYDE"""
        print("\n" + "=" * 80)
        print("🧪 HYDE v18 SIMULATOR - Mode Interactif")
        print("=" * 80)
        print("\nCommandes:")
        print("  - Tapez votre message normalement")
        print("  - 'quit' ou 'exit' pour quitter")
        print("  - 'history' pour voir l'historique passé à HYDE")
        print("  - 'reset' pour remettre l'historique à zéro")
        print("\n" + "=" * 80 + "\n")

        while True:
            try:
                user_input = input("🗣️  VOUS: ").strip()

                if not user_input:
                    continue

                cmd = user_input.lower()
                if cmd in {"quit", "exit", "q"}:
                    print("\n👋 Fin du simulateur HYDE v18\n")
                    break

                if cmd == "history":
                    print("\n📜 HISTORIQUE PASSÉ À HYDE:")
                    print("=" * 80)
                    print(self.conversation_history or "[vide]")
                    print("=" * 80 + "\n")
                    continue

                if cmd == "reset":
                    self.conversation_history = ""
                    self.turn_number = 0
                    print("\n🔄 Historique réinitialisé\n")
                    continue

                await self.call_hyde(user_input)

            except KeyboardInterrupt:
                print("\n\n👋 Interruption - au revoir !\n")
                break
            except Exception as e:
                print(f"\n❌ ERREUR: {e}\n")

    async def run_scenario(self):
        """Scénario automatique de messages typiques pour tester HYDE v18"""
        print("\n" + "=" * 80)
        print("🧪 HYDE v18 SIMULATOR - Scénario Automatique")
        print("=" * 80 + "\n")

        messages = [
            "Bonjour",  # SALUT
            "Je veux commander des couches",  # ACHAT
            "Vous livrez où ?",  # INFO
            "Où est ma commande ?",  # SUIVI
            "???",  # FLOU
            "Vous avez des promos ?",  # HORS_SOFT / HORS_RISQUÉ selon ton mapping
            "Je veux un remboursement",  # INCIDENT/HORS_RISQUÉ
            "J'ai payé mais j'ai rien reçu",  # INCIDENT
        ]

        for msg in messages:
            await self.call_hyde(msg)

        print("\n" + "=" * 80)
        print("✅ SCÉNARIO HYDE TERMINÉ")
        print("=" * 80 + "\n")


async def main():
    simulator = HydeSimulator()

    print("\n" + "=" * 80)
    print(f"🧪 HYDE v18 SIMULATOR - TEST_USER_ID: {TEST_USER_ID}")
    print("=" * 80 + "\n")

    if len(sys.argv) > 1 and sys.argv[1] == "--scenario":
        await simulator.run_scenario()
    else:
        await simulator.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())

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
from datetime import datetime, timezone
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
TEST_USER_ID = f"test_botlive_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
TEST_COMPANY_NAME = "Test Company"

SCENARIO_PROD_MID = [
    "Salut, je veux des couches",
    "Vous avez quoi comme modèles ?",
    "C'est quoi la différence entre pressions et culottes ?",
    "Ok je vais prendre les pressions, mon bébé fait 7kg",
    "Ça dépend c'est combien ?",
    "Et si je prends 2 cartons ça fait combien ?",
    "Vous livrez à Cocody ? c'est combien la livraison ?",
    "Ok donne moi le numéro Wave",
    "Je vais faire l'acompte maintenant",
    {
        "message": "Voici la capture",
        "images": [
            "https://scontent-atl3-3.xx.fbcdn.net/v/t1.15752-9/597360982_1522361755643073_1046808360937074239_n.jpg?_nc_cat=109&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=hb7QgNIX-GUQ7kNvwGvvtuj&_nc_oc=AdkTUqx9yhjXuGQoB6MjjgODELCqDVx5xJcbFBDiIBwzhWq-datbBB2fNyvGMLyTD8muFGJIojldBlFi-dcNYN18&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-3.xx&oh=03_Q7cD4AGscacRxk_JHwC6eQflUC5FNq4YADPaVuKzZ33-sLCmng&oe=6961323F"
        ],
    },
    "Mon numéro c'est 0700000000",
    "Je suis à Cocody Angré",
    "Je confirme: Pression taille 3, 1 carton",
]

SCENARIO_11_QUESTIONS = [
    # A — Accueil / Infos générales
    "Bonsoir, j’aimerais avoir des informations",
    "Votre service fonctionne le dimanche ?",

    # B — Produits / Prix / Disponibilité
    "Vous avez des couches pour bébé de 1 an ?",
    "Quelle est la différence entre vos modèles de couches ?",
    "C’est disponible en ce moment ou en rupture ?",

    # C — Achat / Livraison / Paiement
    "Je prends deux cartons si possible",
    "Vous pouvez livrer demain matin à Cocody ?",
    "Le paiement Wave est obligatoire ou j’ai d’autres options ?",
    "c’est combien les frais de livraison ?",

    # D — SAV / Suivi / Problème
    "Où en est ma commande actuelle ?",
    "Le livreur ne m’a pas encore appelé"
]

# Backward-compat (ancien nom de scénario)
SCENARIO_10_QUESTIONS = SCENARIO_11_QUESTIONS


SCENARIO_58_QUESTIONS = [
    # 1. Salutations & Politesse (Social)
    "Bonjour",
    "Salut ça va",
    "Cc",
    "Merci beaucoup",
    "D'accord merci",

    # 2. Localisation & Drive (Logistique)
    "Vous êtes situé où exactement",
    "C'est où votre boutique",
    "Vous êtes à Abidjan",
    "Je peux venir à la boutique (Point de vente)",
    "Vous êtes en ligne seulement",

    # 3. Livraison (Zones & Délais)
    "Vous livrez dans quelle zone",
    "Vous livrez à Yopougon",
    "Comment se passe la livraison",
    "La livraison c'est combien",
    "Je veux être livré demain",
    "La livraison prend combien de temps",
    "Je veux changer l'adresse de livraison",

    # 4. Horaires (Disponibilité)
    "Vous êtes ouvert jusqu'à quelle heure",
    "Vous travaillez le dimanche",

    # 5. Prix & Gros (Commercial)
    "C'est combien le paquet",
    "C'est combien dans le paquet (Quantité unité)",
    "Prix en gros pour 10 paquets",
    "Vous avez des promotions",
    "Le prix a changé ou pas",

    # 6. Catalogue & Stock (Produit)
    "Vous avez un catalogue",
    "Vous avez quoi en stock actuellement",
    "Vous avez des couches taille 4",
    "Les couches à pression sont disponibles",
    "Les couches nouveau-né vous avez",
    "Vous avez des couches adultes",
    "Y'a des couches culottes",
    "C'est pour quel âge ces couches",
    "Quelle est la différence entre les modèles",
    "C'est disponible maintenant ou en rupture",

    # 7. Processus d'Achat (Conversion)
    "Je veux commander",
    "Comment faire pour acheter",
    "Réserve-moi 2 cartons",
    "Je reviens pour commander plus tard",

    # 8. Paiement (Financier)
    "Vous acceptez quoi comme paiement",
    "Je peux payer avec Wave",
    "Vous prenez Orange Money",
    "Paiement à la livraison possible",
    "Vous acceptez les espèces",

    # 9. Contact (Lead)
    "Quel est votre numéro / WhatsApp",
    "Je peux vous appeler",
    "Je vous appelle mais pas de réponse",

    # 10. SAV & Suivi (Disjoncteur/Critique)
    "Le paquet est abîmé",
    "Les couches ne sont pas bonnes (Qualité)",
    "Je n'ai pas reçu ma commande",
    "Je veux retourner le produit",
    "Où est ma commande / Suivi colis",
    "Le livreur ne répond pas",
]


def _load_whatsapp_120_questions() -> list:
    try:
        from tests.production_test_cases import PRODUCTION_TEST_CASES

        return [q for (q, _expected_label, _expected_id) in (PRODUCTION_TEST_CASES or []) if isinstance(q, str) and q.strip()]
    except Exception:
        return []


class BotliveSimulator:
    """Simulateur de conversation Botlive interactive"""
    
    def __init__(self):
        self.conversation_history = ""
        self.turn_number = 0
        self.eval_rows = []  # Export CSV léger: question + thinking/response
        self._agg = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cached_tokens": 0,
            "cost": 0.0,
            "duration_ms": 0,
            "turns": 0,
        }
        
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

            # Router debug visibility (SetFit/HyDE)
            intent = result.get("intent")
            confidence = result.get("confidence")
            mode = result.get("mode")
            router_debug = result.get("router_debug")
            router_error = result.get("router_error")
            router_source = None
            try:
                if isinstance(router_debug, dict):
                    router_source = router_debug.get("router_source") or router_debug.get("router")
            except Exception:
                router_source = None

            prompt_tokens = int(result.get("prompt_tokens") or 0)
            completion_tokens = int(result.get("completion_tokens") or 0)
            total_tokens = int(result.get("total_tokens") or (prompt_tokens + completion_tokens))
            try:
                cost = float(result.get("cost") or 0.0)
            except Exception:
                cost = 0.0

            cached_tokens = 0
            try:
                usage = result.get("usage") or {}
                ptd = (usage.get("prompt_tokens_details") or {}) if isinstance(usage, dict) else {}
                cached_tokens = int(ptd.get("cached_tokens") or 0) if isinstance(ptd, dict) else 0
            except Exception:
                cached_tokens = 0

            llm_raw = (result.get("llm_raw") or result.get("raw") or "")
            llm_thinking = ""
            llm_response_text = ""
            try:
                if isinstance(llm_raw, str) and llm_raw:
                    import re

                    m_th = re.search(r"<thinking>([\s\S]*?)</thinking>", llm_raw)
                    if m_th:
                        llm_thinking = (m_th.group(1) or "").strip()
                    m_resp = re.search(r"<response>([\s\S]*?)</response>", llm_raw)
                    if m_resp:
                        llm_response_text = (m_resp.group(1) or "").strip()
            except Exception:
                llm_thinking = ""
                llm_response_text = ""

            if not llm_response_text:
                llm_response_text = bot_response

            print("\n[ROUTER] intent=%s confidence=%s mode=%s source=%s" % (intent, confidence, mode, router_source))
            if router_error:
                print("[ROUTER][ERROR] %s" % (router_error,))

            try:
                self._agg["prompt_tokens"] += int(prompt_tokens)
                self._agg["completion_tokens"] += int(completion_tokens)
                self._agg["total_tokens"] += int(total_tokens)
                self._agg["cached_tokens"] += int(cached_tokens)
                self._agg["cost"] += float(cost)
                self._agg["duration_ms"] += int(duration_ms)
                self._agg["turns"] += 1
            except Exception:
                pass
            
            # Ajouter la réponse à l'historique local pour le contexte affiché
            if bot_response:
                self.add_to_history("ASSISTANT", bot_response)

            # Enregistrement CSV léger (pour debugging): question + thinking + réponse
            try:
                self.eval_rows.append(
                    {
                        "turn": self.turn_number,
                        "question": message,
                        "llm_thinking": llm_thinking,
                        "llm_response": llm_response_text,
                        "duration_ms": duration_ms,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                        "cached_tokens": cached_tokens,
                        "cost": cost,
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
        """Run a fixed scenario of messages (no user input)."""
        # Par défaut: scénario prod-like (client moyen)
        scenario_msgs = None
        arg = sys.argv[1] if len(sys.argv) > 1 else ""
        use_120 = arg in {"--scenario120", "--scenario_120", "--whatsapp120"}
        use_prod = arg in {"--scenario", "--scenario_prod", "--scenario_prod_mid"}
        use_58 = arg in {"--scenario58", "--scenario_58", "--whatsapp58"}
        if use_120:
            scenario_msgs = _load_whatsapp_120_questions()
        elif use_prod:
            scenario_msgs = SCENARIO_PROD_MID
        elif use_58:
            scenario_msgs = SCENARIO_58_QUESTIONS
        else:
            try:
                scenario_msgs = SCENARIO_10_QUESTIONS  # type: ignore[name-defined]
            except Exception:
                scenario_msgs = None
            if scenario_msgs is None:
                try:
                    scenario_msgs = SCENARIO_12_QUESTIONS  # type: ignore[name-defined]
                except Exception:
                    scenario_msgs = []

        for msg in scenario_msgs:
            if isinstance(msg, dict):
                await self.send_message(str(msg.get("message") or ""), images=(msg.get("images") or []))
            else:
                await self.send_message(str(msg))

        # Sauvegarde CSV d'évaluation du scénario
        try:
            out_path = Path("tests/botlive_scenario_results.csv")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(
                    f,
                    fieldnames=[
                        "turn",
                        "question",
                        "llm_thinking",
                        "llm_response",
                        "duration_ms",
                        "prompt_tokens",
                        "completion_tokens",
                        "total_tokens",
                        "cached_tokens",
                        "cost",
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

        try:
            turns = int(self._agg.get("turns") or 0)
            if turns > 0:
                avg_prompt = self._agg["prompt_tokens"] / turns
                avg_completion = self._agg["completion_tokens"] / turns
                avg_total = self._agg["total_tokens"] / turns
                avg_cached = self._agg["cached_tokens"] / turns
                avg_cost = self._agg["cost"] / turns
                avg_ms = self._agg["duration_ms"] / turns
                print("Moyennes (par tour):")
                print(f"- prompt_tokens: {avg_prompt:.1f}")
                print(f"- completion_tokens: {avg_completion:.1f}")
                print(f"- total_tokens: {avg_total:.1f}")
                print(f"- cached_tokens: {avg_cached:.1f}")
                print(f"- cost: {avg_cost:.6f}")
                print(f"- duration_ms: {avg_ms:.0f}")
                print("")
        except Exception:
            pass


async def main():
    """Point d'entrée principal"""
    simulator = BotliveSimulator()
    print("\n" + "="*80)
    print(f"🧪 BOTLIVE SIMULATOR - TEST_USER_ID: {TEST_USER_ID}")
    print("="*80 + "\n")
    
    # Vérifier les arguments
    if len(sys.argv) > 1 and sys.argv[1] in {"--scenario", "--scenario_prod", "--scenario_prod_mid", "--scenario58", "--scenario_58", "--whatsapp58", "--scenario120", "--scenario_120", "--whatsapp120"}:
        # Mode scénario automatique
        await simulator.run_scenario()
    else:
        # Mode interactif par défaut
        await simulator.run_interactive()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        # Sortie propre (évite un long traceback en console)
        pass

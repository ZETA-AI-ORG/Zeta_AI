#!/usr/bin/env python3
"""
💬 AMANDA BOTLIVE SIMULATOR

Simule une conversation sur l'endpoint /amandabotlive (Amanda - Précommande VIP):
- Modèle: google/gemini-3.1-pro-preview (MULTIMODAL natif)
- Prompt: AMANDA PROMPT UNIVERSEL.md (dédié, léger, pas de catalogue)
- Rôle: Assistante de précommande Live TikTok
  * Sécurise des articles pendant le Live (rupture de stock)
  * Collecte: IMAGE_PRODUIT + ZONE + PHONE
  * NE donne PAS de prix (le patron rappelle après)

Usage:
    python tests/amanda_simulator.py                  # interactif
    python tests/amanda_simulator.py --scenario       # scénario Live standard
    python tests/amanda_simulator.py --scenario-image # scénario avec image produit

Config (env):
    AMANDA_CHAT_URL   (default: http://127.0.0.1:8001/amandabotlive)
    TEST_COMPANY_ID   (default: W27PwOPiblP8TlOrhPcjOtxd0cza)
    TEST_COMPANY_NAME (default: Test Company)
"""

import asyncio
import csv
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Ajouter le path parent pour imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv()

try:
    tmp_dir = Path(project_root) / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TMPDIR", str(tmp_dir))
    os.environ.setdefault("TEMP", str(tmp_dir))
    os.environ.setdefault("TMP", str(tmp_dir))
except Exception:
    pass

try:
    ru = (os.getenv("REDIS_URL") or "").strip()
    if ru.startswith("redis://redis:"):
        os.environ["REDIS_URL"] = "redis://localhost:6379/0"
except Exception:
    pass

DEFAULT_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"
DEFAULT_COMPANY_NAME = "Test Company"


async def _resolve_chat_url() -> str:
    """Résout l'URL de /amandabotlive parmi les candidats disponibles."""
    env_url = os.getenv("AMANDA_CHAT_URL") or os.getenv("BOTLIVE_CHAT_URL")
    candidates = [
        u for u in [
            env_url,
            "http://127.0.0.1:8001/amandabotlive",
            "http://127.0.0.1:8002/amandabotlive",
        ] if u
    ]
    async with httpx.AsyncClient(timeout=2.5) as client:
        for url in candidates:
            try:
                base = url.rsplit("/amandabotlive", 1)[0]
                r = await client.get(f"{base}/openapi.json")
                if r.status_code in (200, 401, 403):
                    return url
                r2 = await client.get(f"{base}/docs")
                if r2.status_code in (200, 401, 403):
                    return url
            except Exception:
                continue
    return candidates[0] if candidates else "http://127.0.0.1:8001/amandabotlive"


CHAT_URL = "http://127.0.0.1:8001/amandabotlive"
TEST_COMPANY_ID = os.getenv("TEST_COMPANY_ID") or DEFAULT_COMPANY_ID
TEST_COMPANY_NAME = os.getenv("TEST_COMPANY_NAME") or DEFAULT_COMPANY_NAME
TEST_USER_ID = f"test_amanda_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


# ═══════════════════════════════════════════════════════════════════════════════
# 📜 SCÉNARIOS AMANDA — Live TikTok (Précommande VIP)
# ═══════════════════════════════════════════════════════════════════════════════

# Scénario standard : client regarde le Live et veut un article
SCENARIO_LIVE_STANDARD = [
    "Salut ! Je regarde ton Live là",
    "Je veux la robe rouge que tu montres",
    "Combien ça coûte exactement ?",  # Test: Amanda doit refuser de donner le prix
    "Je suis à Cocody Angré",
    "Mon numéro c'est 0707000000",
    "OK parfait, j'attends l'appel du patron",
]

# Scénario avec image : client envoie une capture du produit
SCENARIO_LIVE_IMAGE = [
    "Bonjour, je t'envoie la capture du produit",
    {
        "message": "Voici la capture du produit que je veux",
        "images": [
            "https://scontent-atl3-1.xx.fbcdn.net/v/t1.15752-9/606980593_2273401639829812_4894506129511960265_n.jpg?_nc_cat=106&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=FmmSzPcx2REQ7kNvwErnOmq&oh=03_Q7cD4QEsdnTDlFjMGQmxCrqQOeLqGkiyq7M8qkJKiHOed2l7jA&oe=697E1F80"
        ],
    },
    "Je suis à Yopougon Sideci",
    "Mon numéro 0500000000",
]

# Scénario "Pas de catalogue" : vérifier qu'Amanda ne tente pas de vérifier des stocks
SCENARIO_NO_CATALOGUE = [
    "Vous avez quoi en stock comme couleurs ?",  # Amanda doit rediriger
    "Quel est le prix des couches taille 3 ?",   # Amanda refuse de donner prix
    "Envoyez-moi votre catalogue",               # Amanda doit rediriger
]

# Scénario "Social" : accueil pur, pas encore de commande
SCENARIO_SOCIAL = [
    "Bonjour",
    "Salut ça va ?",
    "Super Live ! J'adore tes produits",
    "Tu livres partout ?",
]


class AmandaSimulator:
    def __init__(self):
        self.chat_url = CHAT_URL
        self.use_http = False
        self.conversation_history = ""
        self.turn_number = 0
        self.eval_rows = []
        self.json_rows = []
        self.started_at_utc = datetime.utcnow().isoformat() + "Z"
        self._agg = {
            "duration_ms": 0,
            "turns": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cached_tokens": 0,
            "cost": 0.0,
        }

    def _json_report_path(self) -> Path:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_dir = Path("tests") / "reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir / f"amanda_simulator_{ts}_{TEST_USER_ID}.json"

    def save_json_report(self, extra: dict | None = None) -> Path | None:
        try:
            out_path = self._json_report_path()
            payload = {
                "meta": {
                    "created_at_utc": datetime.utcnow().isoformat() + "Z",
                    "started_at_utc": self.started_at_utc,
                    "finished_at_utc": datetime.utcnow().isoformat() + "Z",
                    "test_user_id": TEST_USER_ID,
                    "company_id": TEST_COMPANY_ID,
                    "company_name": TEST_COMPANY_NAME,
                    "mode": "HTTP" if self.use_http else "IN-PROCESS",
                    "chat_url": self.chat_url if self.use_http else "in_process",
                    "bot_type": "amanda_botlive",
                    "endpoint": "/amandabotlive",
                },
                "agg": self._agg,
                "turns": self.json_rows,
            }
            if extra and isinstance(extra, dict):
                payload["extra"] = extra
            out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return out_path
        except Exception as e:
            print(f"[WARN] Impossible d'écrire le JSON report: {e}")
            return None

    def add_to_history(self, role: str, message: str) -> None:
        self.conversation_history += f"{role}: {message}\n"

    async def send_message(self, message: str, images: list | None = None) -> dict | None:
        self.turn_number += 1
        images = images or []

        # Cache-buster pour les images
        if images:
            message = f"{message} [img_ref:{uuid.uuid4().hex[:8]}]"

        print(f"\n{'='*80}")
        print(f"🎬 TOUR {self.turn_number} - CLIENT LIVE")
        print(f"{'='*80}")
        print(f"Message: {message}")
        if images:
            print(f"Images: {images}")
        print()

        self.add_to_history("USER", message)

        payload = {
            "company_id": TEST_COMPANY_ID,
            "user_id": TEST_USER_ID,
            "message": message,
            "images": images,
            "conversation_history": self.conversation_history,
            "user_display_name": TEST_COMPANY_NAME,
        }

        start = time.time()
        try:
            if not self.use_http:
                # In-process: appeler directement amanda_botlive_endpoint
                from core.models import ChatRequest
                from starlette.requests import Request as StarletteRequest
                from Zeta_AI.app import amanda_botlive_endpoint

                req = ChatRequest(**payload)
                scope = {
                    "type": "http",
                    "http_version": "1.1",
                    "method": "POST",
                    "path": "/amandabotlive",
                    "headers": [],
                }
                fake_request = StarletteRequest(scope)
                result = await amanda_botlive_endpoint(req, fake_request)

                if hasattr(result, "body"):
                    raw_body = result.body
                    if isinstance(raw_body, (bytes, bytearray)):
                        raw_body = raw_body.decode("utf-8", errors="ignore")
                    else:
                        raw_body = str(raw_body)
                    result = json.loads(raw_body) if raw_body else {}
                duration_ms = int((time.time() - start) * 1000)
                status_code = 200
            else:
                # HTTP mode
                max_attempts = 3
                last_exc: Exception | None = None
                resp = None
                for attempt in range(1, max_attempts + 1):
                    try:
                        async with httpx.AsyncClient(timeout=180.0) as client:
                            resp = await client.post(self.chat_url, json=payload)
                        break
                    except httpx.ConnectError as e:
                        last_exc = e
                        print(f"⚠️ [SIMULATOR] ConnectError → retry {attempt}/{max_attempts}")
                        await asyncio.sleep(min(2.0, 0.4 * attempt))
                if resp is None:
                    raise last_exc or httpx.ConnectError("All connection attempts failed")

                duration_ms = int((time.time() - start) * 1000)
                status_code = resp.status_code
                try:
                    result = resp.json()
                except Exception:
                    result = {"raw": resp.text, "status_code": resp.status_code}
                
                # Extraction des logs même si erreur
                if status_code != 200 and isinstance(result.get("detail"), dict):
                     server_logs = result["detail"].get("server_logs", "")
                     if server_logs:
                         result["server_logs"] = server_logs

            bot_response = (result.get("response") or "").strip() if isinstance(result, dict) else ""
            thinking = result.get("thinking", {}) if isinstance(result, dict) else {}
            thinking_raw = result.get("thinking_raw", "") if isinstance(result, dict) else ""
            model_used = result.get("model", "") if isinstance(result, dict) else ""
            plan = result.get("plan", "") if isinstance(result, dict) else ""
            multimodal = result.get("multimodal", False) if isinstance(result, dict) else False
            zone_detected = result.get("zone_detected", "") if isinstance(result, dict) else ""
            delivery_cost = result.get("delivery_cost", 0) if isinstance(result, dict) else 0

            self._agg["duration_ms"] += duration_ms
            self._agg["turns"] += 1

            if bot_response:
                self.add_to_history("AMANDA", bot_response)

            self.eval_rows.append({
                "turn": self.turn_number,
                "question": message,
                "response": bot_response,
                "duration_ms": duration_ms,
                "status_code": status_code,
                "model": model_used,
                "plan": plan,
                "multimodal": multimodal,
                "thinking_mode": str(thinking.get("etat", "")) if isinstance(thinking, dict) else "",
            })

            self.json_rows.append({
                "turn": self.turn_number,
                "request": {"message": message, "images": images},
                "response": {
                    "text": bot_response,
                    "thinking": thinking,
                    "model": model_used,
                    "plan": plan,
                    "multimodal": multimodal,
                },
                "timing": {"duration_ms": duration_ms},
                "http": {"status_code": status_code},
            })

            print(f"💬 AMANDA (réponse en {duration_ms}ms | model={model_used})")
            print(f"{'='*80}")
            print(bot_response or "[Aucune réponse]")
            
            # Affichage des logs serveurs si présents
            server_logs = result.get("server_logs", "")
            if server_logs:
                print(f"\n🖥️  SERVER LOGS (captured at {CHAT_URL}):")
                print("-" * 40)
                # Afficher avec indentation légère
                for line in server_logs.strip().splitlines():
                    print(f"  | {line}")
                print("-" * 40)

            if zone_detected or delivery_cost:
                print(f"\n🚚 ZONE: {zone_detected} | LIVRAISON: {delivery_cost}F")
            if thinking:
                print(f"\n🧠 THINKING (XML parsed):")
                for k, v in thinking.items():
                    v_str = str(v)[:120]
                    print(f"   <{k}>: {v_str}")
            print(f"{'='*80}\n")

            return result if isinstance(result, dict) else {"raw": result}

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            print(f"❌ ERREUR: {type(e).__name__}: {e} ({duration_ms}ms)")
            import traceback
            traceback.print_exc()
            self.json_rows.append({
                "turn": self.turn_number,
                "request": {"message": message, "images": images},
                "timing": {"duration_ms": duration_ms},
                "error": {"type": type(e).__name__, "message": str(e)},
            })
            return None

    async def run_interactive(self) -> None:
        print("\n" + "=" * 80)
        print("💬 AMANDA BOTLIVE SIMULATOR - Mode Interactif")
        print("=" * 80)
        print("\nCommandes:")
        print("  - Tapez votre message (client Live TikTok)")
        print("  - Collez une URL image (https://...) pour simuler envoi produit")
        print("  - 'quit' / 'exit' pour quitter")
        print("  - 'history' pour voir l'historique")
        print("  - 'reset' pour repartir de zéro")
        print("\n" + "=" * 80 + "\n")

        while True:
            try:
                user_input = input("🎬 CLIENT LIVE: ").strip()
                if not user_input:
                    continue

                cmd = user_input.lower()
                if cmd in {"quit", "exit", "q"}:
                    if self.json_rows:
                        out_path = self.save_json_report({"mode": "interactive_exit"})
                        if out_path:
                            print(f"JSON saved: {out_path}")
                    print("\n👋 Fin du simulateur Amanda\n")
                    break

                if cmd == "history":
                    print("\n📜 HISTORIQUE:")
                    print("=" * 80)
                    print(self.conversation_history or "[vide]")
                    print("=" * 80 + "\n")
                    continue

                if cmd == "reset":
                    self.conversation_history = ""
                    self.turn_number = 0
                    self.eval_rows = []
                    print("\n🔄 Conversation réinitialisée\n")
                    continue

                images = []
                if user_input.startswith("http://") or user_input.startswith("https://"):
                    images = [user_input]
                    user_input = "Voici la capture du produit"
                    print(f"📸 [SIMULATOR] URL image détectée → envoi en précommande")

                await self.send_message(user_input, images=images)

            except KeyboardInterrupt:
                print("\n\n👋 Interruption - au revoir !\n")
                break

    async def run_scenario(self) -> None:
        arg = ""
        for a in sys.argv[1:]:
            if a.startswith("--scenario"):
                arg = a
                break

        if arg in {"--scenario-image", "--scenario_image"}:
            scenario_msgs = SCENARIO_LIVE_IMAGE
            scenario_name = "LIVE_IMAGE"
        elif arg in {"--scenario-no-catalogue", "--scenario_no_catalogue"}:
            scenario_msgs = SCENARIO_NO_CATALOGUE
            scenario_name = "NO_CATALOGUE"
        elif arg in {"--scenario-social", "--scenario_social"}:
            scenario_msgs = SCENARIO_SOCIAL
            scenario_name = "SOCIAL"
        else:
            scenario_msgs = SCENARIO_LIVE_STANDARD
            scenario_name = "LIVE_STANDARD"

        print(f"\n🎬 SCÉNARIO AMANDA: {scenario_name} ({len(scenario_msgs)} tours)\n")

        for msg in scenario_msgs:
            if isinstance(msg, dict):
                await self.send_message(str(msg.get("message") or ""), images=(msg.get("images") or []))
            else:
                await self.send_message(str(msg))
            await asyncio.sleep(0.5)

        # CSV
        try:
            out_path = Path("tests/amanda_scenario_results.csv")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8", newline="") as f:
                fieldnames = ["turn", "question", "response", "duration_ms", "status_code",
                              "model", "plan", "multimodal", "thinking_mode"]
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                for r in self.eval_rows:
                    w.writerow(r)
            print(f"\nCSV saved: {out_path}\n")
        except Exception as e:
            print(f"\n[WARN] CSV error: {e}\n")

        try:
            json_path = self.save_json_report({"mode": "scenario", "scenario_name": scenario_name})
            if json_path:
                print(f"JSON saved: {json_path}")
        except Exception:
            pass

        # Résumé
        print("\n" + "=" * 80)
        print(f"✅ SCÉNARIO TERMINÉ: {scenario_name}")
        print("=" * 80 + "\n")
        turns = int(self._agg.get("turns") or 0)
        if turns > 0:
            avg_ms = self._agg["duration_ms"] / turns
            print(f"Moyennes: {turns} tours | duration_ms={avg_ms:.0f}ms/tour")


async def main() -> None:
    simulator = AmandaSimulator()
    simulator.use_http = any(a in {"--http", "--http-mode"} for a in sys.argv[1:])
    if simulator.use_http:
        simulator.chat_url = await _resolve_chat_url()

    print("\n" + "=" * 80)
    print(f"💬 AMANDA SIMULATOR (/amandabotlive) - TEST_USER_ID: {TEST_USER_ID}")
    print(f"🧪 MODE: {'HTTP' if simulator.use_http else 'IN-PROCESS'}")
    if simulator.use_http:
        print(f"🧪 CHAT_URL: {simulator.chat_url}")
    print(f"🧪 COMPANY_ID: {TEST_COMPANY_ID}")
    print("=" * 80 + "\n")

    if any(a.startswith("--scenario") for a in sys.argv[1:]):
        await simulator.run_scenario()
    else:
        await simulator.run_interactive()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass

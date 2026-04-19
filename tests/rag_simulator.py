#!/usr/bin/env python3
"""\
🧪 RAG CONVERSATION SIMULATOR

Simule une conversation sur l'endpoint RAG (/chat) pour:
- Observer la qualité des réponses (collecte, NEXT, répétitions)
- Capturer métriques (latence, tokens/cost si présents)
- Exporter un CSV pour analyse globale

Usage:
    python tests/rag_simulator.py                 # interactif
    python tests/rag_simulator.py --scenario      # scénario court (11)
    python tests/rag_simulator.py --scenario58    # pack questions (58)
    python tests/rag_simulator.py --scenario120   # pack production_test_cases (si dispo)

Config (env):
    RAG_CHAT_URL      (default: http://127.0.0.1:8001/chat)
    TEST_COMPANY_ID   (default: W27PwOPiblP8TlOrhPcjOtxd0cza)
    TEST_COMPANY_NAME (default: Test Company)
"""

import asyncio
import csv
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Ajouter le path parent pour imports, en le mettant EN PREMIER dans sys.path
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

# Ensure in-process runs (outside Docker) can still load local catalogs and connect to Redis.
try:
    if not (os.getenv("CATALOG_V2_LOCAL_DIR") or "").strip():
        os.environ["CATALOG_V2_LOCAL_DIR"] = str(Path(project_root) / "data" / "catalogs")
except Exception:
    pass
try:
    ru = (os.getenv("REDIS_URL") or "").strip()
    if ru.startswith("redis://redis:"):
        os.environ["REDIS_URL"] = "redis://localhost:6379/0"
except Exception:
    pass

# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 CONFIGURATION MODELE TEST (forcer des modèles spécifiques)
# ═══════════════════════════════════════════════════════════════════════════════
# Pour tester avec DeepSeek V3.2 ou Qwen 235B, définir:
#   export TEST_FORCE_MODEL="deepseek/deepseek-v3.2"
#   export TEST_FORCE_MODEL="qwen/qwen3-235b-a22b-2507"
#   export TEST_ALLOW_MODELS="deepseek/deepseek-v3.2,qwen/qwen3-235b-a22b-2507"
#
# Puis lancer: python tests/rag_simulator.py
# ═══════════════════════════════════════════════════════════════════════════════
TEST_FORCE_MODEL = os.getenv("TEST_FORCE_MODEL", "")
if TEST_FORCE_MODEL:
    # Forcer le modèle dans toutes les routes LLM
    os.environ["MODEL_DEFAULT"] = TEST_FORCE_MODEL
    os.environ["MODEL_RANG_S"] = TEST_FORCE_MODEL
    os.environ["MODEL_RANG_A"] = TEST_FORCE_MODEL
    # Autoriser explicitement ce modèle (bypass le garde-fou)
    _current_allow = os.getenv("TEST_ALLOW_MODELS", "")
    if TEST_FORCE_MODEL not in _current_allow:
        os.environ["TEST_ALLOW_MODELS"] = f"{TEST_FORCE_MODEL},{_current_allow}".strip(",")
    print(f"🧪 [TEST MODE] Modèle forcé: {TEST_FORCE_MODEL}")
    print(f"🧪 [TEST MODE] TEST_ALLOW_MODELS={os.environ.get('TEST_ALLOW_MODELS')}")

DEFAULT_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"
DEFAULT_COMPANY_NAME = "Test Company"


async def _resolve_chat_url() -> str:
    """Resolve the /chat endpoint.

    Priority:
    1) RAG_CHAT_URL
    2) CHAT_URL
    3) Try local defaults: 8001 then 8002
    """

    env_url = os.getenv("RAG_CHAT_URL") or os.getenv("CHAT_URL")
    candidates = [u for u in [env_url, "http://127.0.0.1:8001/chat", "http://127.0.0.1:8002/chat"] if u]

    # Preflight: attempt a quick POST with empty payload is not possible,
    # so we just check TCP reachability via GET /docs or /openapi.json.
    async with httpx.AsyncClient(timeout=2.5) as client:
        for url in candidates:
            try:
                base = url.rsplit("/chat", 1)[0]
                # Try OpenAPI first
                r = await client.get(f"{base}/openapi.json")
                if r.status_code in (200, 401, 403):
                    return url
                # Fallback: /docs
                r2 = await client.get(f"{base}/docs")
                if r2.status_code in (200, 401, 403):
                    return url
            except Exception:
                continue

    # Fallback: keep first candidate for error reporting
    return candidates[0] if candidates else "http://127.0.0.1:8001/chat"


CHAT_URL = "http://127.0.0.1:8001/chat"  # resolved at runtime in main()
TEST_COMPANY_ID = os.getenv("TEST_COMPANY_ID") or DEFAULT_COMPANY_ID
TEST_COMPANY_NAME = os.getenv("TEST_COMPANY_NAME") or DEFAULT_COMPANY_NAME

TEST_USER_ID = f"test_rag_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


SCENARIO_PROD_MID = [
    "Bonsoir Jessica, je cherche des couches pour bébé",
    "Vous avez quoi exactement comme modèles ?",
    "Je comprends pas trop… pressions et culottes ça change quoi ?",
    "Mon bébé fait environ 8kg, tu me conseilles quelle taille ?",
    "Et si je prends taille 3 ça va pas être petit ?",
    "Ok je pense partir sur les pressions. Vous vendez ça en gros comment ?",
    {
        "message": "Je t'envoie la photo du produit que je veux",
        "images": [
            "https://scontent-atl3-1.xx.fbcdn.net/v/t1.15752-9/606980593_2273401639829812_4894506129511960265_n.jpg?_nc_cat=106&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=FmmSzPcx2REQ7kNvwErnOmq&_nc_oc=Adni5GjdIrxHlewIqYObOSD9Xo0pUG5DJTd4szXpnB_5w-wExNxPmELcbQSO0t2TKoorn25yYRG5IgjgAH4GTSZJ&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-1.xx&oh=03_Q7cD4QEsdnTDlFjMGQmxCrqQOeLqGkiyq7M8qkJKiHOed2l7jA&oe=697E1F80"
        ],
    },
    "Attends je veux d'abord le prix… c'est combien la taille 3 et taille 4 ?",
    "Et niveau livraison à Cocody Angré, ça fait combien ?",
    "D'accord. Bon je vais prendre 1 carton. C'est bon ?",
    "Je vais faire l'acompte là mais j'ai que 1000F sur Wave…",
    {
        "message": "Voici la capture Wave (acompte insuffisant)",
        "images": [
            "https://scontent.xx.fbcdn.net/v/t1.15752-9/582949854_1524325675515592_1712402945374325664_n.jpg?_nc_cat=107&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=brNHcmG2PkUQ7kNvwG9c3oX&_nc_oc=AdnFlJc_jyF9Svs8lkVKjOtaM2w99-edoFB14QuA7OTcTqezTahqQfHaB0yxRYMSF0DJXVFghjZUGqjmoO8FUWgr&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD4QFS1LYSpryUlFPSRH4fSJA9CKhwQiMoJTnt49ER_ba4Yg&oe=697E1A12"
        ],
    },
    "Ok j'ajoute le reste et je renvoie la capture complète",
    {
        "message": "Voici la capture Wave (acompte complet)",
        "images": [
            "https://scontent-atl3-1.xx.fbcdn.net/v/t1.15752-9/609062284_1219578113601891_4618528950577866081_n.jpg?_nc_cat=103&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=UI38AZx8T0oQ7kNvwHW0IPI&_nc_oc=Adko2iVkB73GOpgEc-S_KoyyPu-MQChYN9an45GC8T01QsWTu85C9NPZrDvBF9omWaSUuOVLCLhQpdPcbk82IRQM&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-1.xx&oh=03_Q7cD4QGMlO87YXfGdeo3IyDMp1TO83Z-H5Ug7o3DVJAbdutmNg&oe=698AE109"
        ],
    },
    "Mon numéro c'est 0700000000",
    "Je confirme : pressions taille 3, 1 carton, livraison Cocody Angré",
]


SCENARIO_VALIDATION_STATE = [
    "Je veux commander des couches",
    "Livraison à Cocody Angré",
    "Mon numéro c'est +225 0787360757",
    "Je vais faire l'acompte là mais j'ai que 1000F sur Wave…",
    {
        "message": "Voici la capture Wave (acompte insuffisant)",
        "images": [
            "https://scontent.xx.fbcdn.net/v/t1.15752-9/582949854_1524325675515592_1712402945374325664_n.jpg?_nc_cat=107&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=brNHcmG2PkUQ7kNvwG9c3oX&_nc_oc=AdnFlJc_jyF9Svs8lkVKjOtaM2w99-edoFB14QuA7OTcTqezTahqQfHaB0yxRYMSF0DJXVFghjZUGqjmoO8FUWgr&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD4QFS1LYSpryUlFPSRH4fSJA9CKhwQiMoJTnt49ER_ba4Yg&oe=697E1A12"
        ],
    },
]


SCENARIO_PRICE_PIVOT = [
    "Je veux des couches culottes",
    "Taille 4 s'il vous plaît",
    "En lot 150",
    "Je prends 1 lot",
    "le total va être de combien ?",
    "Pressions",
    "Ajoute aussi culotte taille 4 lot 150",
]


SCENARIO_11_QUESTIONS = [
    "Quel est le numéro Wave ?",
    "C’est combien l’acompte ?",
    "Bonsoir, j’aimerais avoir des informations",
    "Votre service fonctionne le dimanche ?",
    "Vous avez des couches pour bébé de 1 an ?",
    "Quelle est la différence entre vos modèles ?",
    "C’est disponible en ce moment ou en rupture ?",
    "Je prends deux cartons si possible",
    "Vous pouvez livrer demain matin à Cocody ?",
    "Le paiement Wave est obligatoire ou j’ai d’autres options ?",
    "c’est combien les frais de livraison ?",
    "Où en est ma commande actuelle ?",
    "Le livreur ne m’a pas encore appelé",
]

SCENARIO_58_QUESTIONS = [
    "Bonjour",
    "Salut ça va",
    "Cc",
    "Merci beaucoup",
    "D'accord merci",
    "Vous êtes situé où exactement",
    "C'est où votre boutique",
    "Vous êtes à Abidjan",
    "Je peux venir à la boutique (Point de vente)",
    "Vous êtes en ligne seulement",
    "Vous livrez dans quelle zone",
    "Vous livrez à Yopougon",
    "Comment se passe la livraison",
    "La livraison c'est combien",
    "Je veux être livré demain",
    "La livraison prend combien de temps",
    "Je veux changer l'adresse de livraison",
    "Vous êtes ouvert jusqu'à quelle heure",
    "Vous travaillez le dimanche",
    "C'est combien le paquet",
    "C'est combien dans le paquet (Quantité unité)",
    "Prix en gros pour 10 paquets",
    "Vous avez des promotions",
    "Le prix a changé ou pas",
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
    "Je veux commander",
    "Comment faire pour acheter",
    "Réserve-moi 2 cartons",
    "Je reviens pour commander plus tard",
    "Vous acceptez quoi comme paiement",
    "Je peux payer avec Wave",
    "Vous prenez Orange Money",
    "Paiement à la livraison possible",
    "Vous acceptez les espèces",
    "Quel est votre numéro / WhatsApp",
    "Je peux vous appeler",
    "Je vous appelle mais pas de réponse",
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


class RAGSimulator:
    def __init__(self):
        self.chat_url = CHAT_URL
        # Par défaut: exécuter in-process (logs visibles dans cette console)
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
        return out_dir / f"rag_simulator_{ts}_{TEST_USER_ID}.json"

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

    def _snapshot_order_state(self) -> dict | None:
        try:
            if self.use_http:
                return None
            from core.order_state_tracker import order_tracker

            st = order_tracker.get_state(TEST_USER_ID)
            missing = []
            try:
                missing = sorted(list(st.get_missing_fields()))
            except Exception:
                missing = []

            return {
                "produit": getattr(st, "produit", None),
                "specs": getattr(st, "produit_details", None),
                "quantite": getattr(st, "quantite", None),
                "zone": getattr(st, "zone", None),
                "numero": getattr(st, "numero", None),
                "paiement": getattr(st, "paiement", None),
                "missing": missing,
            }
        except Exception:
            return None

    async def send_message(self, message: str, images: list | None = None) -> dict | None:
        self.turn_number += 1
        images = images or []

        def _extract_between(text: str, start_marker: str, end_marker: str) -> str:
            try:
                s = str(text or "")
                i = s.find(start_marker)
                if i == -1:
                    return ""
                j = s.find(end_marker, i + len(start_marker))
                if j == -1:
                    return ""
                return s[i + len(start_marker) : j]
            except Exception:
                return ""

        async def _build_prompt_snapshot(label: str) -> None:
            try:
                if self.use_http:
                    return

                from core.simplified_prompt_system import get_simplified_prompt_system

                ps = get_simplified_prompt_system()
                prompt = await ps.build_prompt(
                    query=message,
                    user_id=TEST_USER_ID,
                    company_id=TEST_COMPANY_ID,
                    conversation_history=self.conversation_history,
                    has_image=bool(images),
                )

                p_s = str(prompt or "")
                has_cat_markers = ("[CATALOGUE_START]" in p_s) and ("[CATALOGUE_END]" in p_s)
                cat_inner = _extract_between(p_s, "[CATALOGUE_START]", "[CATALOGUE_END]")
                cat_clean = (cat_inner or "").strip()
                print(f"\n{'-'*80}")
                print(
                    f"🧾 PROMPT SNAPSHOT ({label}) - CATALOGUE_BLOCK markers={'YES' if has_cat_markers else 'NO'} | chars={len(cat_clean)}"
                )
                print(f"{'-'*80}")
                print(cat_clean if cat_clean else "<EMPTY>")
                print(f"{'-'*80}\n")

                has_idx_markers = ("[[PRODUCT_INDEX_START]]" in p_s) and ("[[PRODUCT_INDEX_END]]" in p_s)
                idx_inner = _extract_between(p_s, "[[PRODUCT_INDEX_START]]", "[[PRODUCT_INDEX_END]]")
            except Exception:
                pass
            # ✅ DESACTIVE car trop imprécis par rapport au moteur hybride Botlive (Système C)
            # Se fier uniquement aux logs [BOTLIVE_PROMPT_FULL] dans la console SSH.
            return

        # IMPORTANT: le backend a un cache exact basé sur req.message.
        # Pour les tours avec images (produit/paiement), on veut FORCER la vision + le parsing,
        # donc on ajoute un suffix unique pour éviter les cache hits entre runs.
        if images:
            message = f"{message} [img_ref:{uuid.uuid4().hex[:8]}]"

        print(f"\n{'='*80}")
        print(f"🗣️  TOUR {self.turn_number} - VOUS")
        print(f"{'='*80}")
        print(f"Message: {message}")
        if images:
            print(f"Images: {images}")
        print()

        self.add_to_history("USER", message)

        await _build_prompt_snapshot(label="PRE_CALL")

        payload = {
            "company_id": TEST_COMPANY_ID,
            "user_id": TEST_USER_ID,
            "message": message,
            "images": images,
            "botlive_enabled": True,
            # conversation_history n'est plus attendu côté API, mais on le garde si présent
            "conversation_history": self.conversation_history,
            "user_display_name": TEST_COMPANY_NAME,
        }

        start = time.time()
        try:
            if not self.use_http:
                # In-process: appeler directement l'endpoint FastAPI (logs ici)
                from core.models import ChatRequest
                from starlette.requests import Request as StarletteRequest
                try:
                    from Zeta_AI.app import chat_endpoint
                except Exception:
                    try:
                        from app_optimized import chat_endpoint
                    except Exception:
                        from app import chat_endpoint

                req = ChatRequest(**payload)
                scope = {
                    "type": "http",
                    "http_version": "1.1",
                    "method": "POST",
                    "path": "/chat",
                    "headers": [],
                }
                fake_request = StarletteRequest(scope)

                try:
                    import inspect

                    nb_params = len(inspect.signature(chat_endpoint).parameters)
                except Exception:
                    nb_params = 2

                if nb_params <= 1:
                    result = await chat_endpoint(req)
                else:
                    result = await chat_endpoint(req, fake_request)

                await _build_prompt_snapshot(label="POST_CALL")

                # JSONResponse ou dict
                if hasattr(result, "body"):
                    raw_body = result.body
                    if isinstance(raw_body, (bytes, bytearray)):
                        raw_body = raw_body.decode("utf-8", errors="ignore")
                    else:
                        raw_body = str(raw_body)
                    result = json.loads(raw_body) if raw_body else {}

                duration_ms = int((time.time() - start) * 1000)
            else:
                # HTTP mode: nécessite uvicorn lancé
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
                        # IMPORTANT: ne pas modifier self.chat_url sur ConnectError.
                        # Sur certains environnements, la résolution auto peut produire une URL incorrecte.
                        print(
                            f"⚠️ [SIMULATOR] ConnectError → retry {attempt}/{max_attempts} avec CHAT_URL={self.chat_url!r}"
                        )
                        await asyncio.sleep(min(2.0, 0.4 * attempt))
                if resp is None:
                    raise last_exc or httpx.ConnectError("All connection attempts failed")

                duration_ms = int((time.time() - start) * 1000)
                try:
                    result = resp.json()
                except Exception:
                    result = {"raw": resp.text, "status_code": resp.status_code}

                # Compat: certains backends renvoient {"status": "success", "response": {...}}
                # On "déplie" automatiquement pour conserver un format plat.
                try:
                    if isinstance(result, dict) and isinstance(result.get("response"), dict) and ("status" in result):
                        result = result.get("response") or {}
                except Exception:
                    pass

            bot_response = (result.get("response") or "").strip() if isinstance(result, dict) else ""

            prompt_tokens = int((result.get("prompt_tokens") or 0) if isinstance(result, dict) else 0)
            completion_tokens = int((result.get("completion_tokens") or 0) if isinstance(result, dict) else 0)
            total_tokens = int((result.get("total_tokens") or (prompt_tokens + completion_tokens)) if isinstance(result, dict) else 0)

            cached_tokens = 0
            try:
                usage = (result.get("usage") or {}) if isinstance(result, dict) else {}
                ptd = (usage.get("prompt_tokens_details") or {}) if isinstance(usage, dict) else {}
                cached_tokens = int((ptd.get("cached_tokens") or 0) if isinstance(ptd, dict) else 0)
            except Exception:
                cached_tokens = 0

            try:
                cost = float((result.get("cost") or 0.0) if isinstance(result, dict) else 0.0)
            except Exception:
                cost = 0.0

            try:
                self._agg["duration_ms"] += duration_ms
                self._agg["turns"] += 1
                self._agg["prompt_tokens"] += prompt_tokens
                self._agg["completion_tokens"] += completion_tokens
                self._agg["total_tokens"] += total_tokens
                self._agg["cached_tokens"] += cached_tokens
                self._agg["cost"] += cost
            except Exception:
                pass

            if bot_response:
                self.add_to_history("ASSISTANT", bot_response)

            self.eval_rows.append(
                {
                    "turn": self.turn_number,
                    "question": message,
                    "response": bot_response,
                    "duration_ms": duration_ms,
                    "status_code": (getattr(resp, "status_code", "") if self.use_http else 200),
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "cached_tokens": cached_tokens,
                    "cost": cost,
                    "search_method": (result.get("search_method") if isinstance(result, dict) else ""),
                }
            )

            try:
                if isinstance(result, dict):
                    debug_contexts = result.get("debug_contexts")
                    opt = None
                    if isinstance(debug_contexts, dict):
                        opt = debug_contexts.get("context_optimization")
                    self.json_rows.append(
                        {
                            "turn": self.turn_number,
                            "request": {
                                "message": message,
                                "images": images,
                            },
                            "order_state": self._snapshot_order_state(),
                            "timing": {
                                "duration_ms": duration_ms,
                            },
                            "http": {
                                "status_code": (getattr(resp, "status_code", None) if self.use_http else 200),
                            },
                            "result": {
                                "search_method": result.get("search_method"),
                                "documents_found": result.get("documents_found"),
                                "confidence": result.get("confidence"),
                                "used_supabase": (opt.get("used_supabase") if isinstance(opt, dict) else None),
                                "fallback_reason": (opt.get("fallback_reason") if isinstance(opt, dict) else None),
                                "total_chars_saved": (opt.get("total_chars_saved") if isinstance(opt, dict) else None),
                                "prompt_tokens": prompt_tokens,
                                "completion_tokens": completion_tokens,
                                "total_tokens": total_tokens,
                                "cached_tokens": cached_tokens,
                                "cost": cost,
                            },
                            "response": {
                                "text": bot_response,
                            },
                        }
                    )
            except Exception:
                pass

            print(f"🤖 RAG (réponse en {duration_ms}ms)")
            print(f"{'='*80}")
            print(bot_response or "[Aucune réponse] স্ত")
            print(f"{'='*80}\n")

            return result if isinstance(result, dict) else {"raw": result}

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            print(f"❌ ERREUR: {type(e).__name__}: {e} ({duration_ms}ms) | CHAT_URL={self.chat_url}")
            import traceback

            traceback.print_exc()
            try:
                self.json_rows.append(
                    {
                        "turn": self.turn_number,
                        "request": {
                            "message": message,
                            "images": images,
                        },
                        "timing": {
                            "duration_ms": duration_ms,
                        },
                        "error": {
                            "type": type(e).__name__,
                            "message": str(e),
                        },
                    }
                )
            except Exception:
                pass
            return None

    async def run_interactive(self) -> None:
        print("\n" + "=" * 80)
        print("🧪 RAG SIMULATOR - Mode Interactif")
        print("=" * 80)
        print("\nCommandes:")
        print("  - Tapez votre message")
        print("  - 'quit' / 'exit' pour quitter")
        print("  - 'history' pour voir l'historique")
        print("  - 'reset' pour repartir de zéro")
        print("\n" + "=" * 80 + "\n")

        while True:
            try:
                user_input = input("🗣️  VOUS: ").strip()
                if not user_input:
                    continue

                cmd = user_input.lower()
                if cmd in {"quit", "exit", "q"}:
                    if self.json_rows:
                        out_path = self.save_json_report({"mode": "interactive_exit"})
                        if out_path:
                            print(f"JSON saved: {out_path}")
                    print("\n👋 Fin du simulateur\n")
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
                    self._agg = {
                        "duration_ms": 0,
                        "turns": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "cached_tokens": 0,
                        "cost": 0.0,
                    }
                    print("\n🔄 Conversation réinitialisée\n")
                    continue

                images = []
                if user_input.startswith("http://") or user_input.startswith("https://"):
                    images = [user_input]
                    user_input = "Voici la capture"
                    print(f"📸 [SIMULATOR] URL image détectée")

                await self.send_message(user_input, images=images)

            except KeyboardInterrupt:
                print("\n\n👋 Interruption - au revoir !\n")
                break

    async def run_scenario(self) -> None:
        # Supporte n'importe quel ordre d'arguments (ex: --http --scenario58)
        arg = ""
        for a in sys.argv[1:]:
            if a.startswith("--scenario") or a in {"--whatsapp58", "--whatsapp120", "--scenario-validation", "--scenario_validation"}:
                arg = a
                break
        assert_state = any(a in {"--assert", "--assert-state"} for a in sys.argv[1:])
        if arg in {"--scenario120", "--scenario_120", "--whatsapp120"}:
            scenario_msgs = _load_whatsapp_120_questions()
        elif arg in {"--scenario58", "--scenario_58", "--whatsapp58"}:
            scenario_msgs = SCENARIO_58_QUESTIONS
        elif arg in {"--scenario-price-pivot", "--scenario_price_pivot"}:
            scenario_msgs = SCENARIO_PRICE_PIVOT
        elif arg in {"--scenario-validation", "--scenario_validation"}:
            scenario_msgs = SCENARIO_VALIDATION_STATE
        elif arg in {"--scenario", "--scenario11", "--scenario_11"}:
            scenario_msgs = SCENARIO_PROD_MID
        else:
            scenario_msgs = SCENARIO_11_QUESTIONS

        for msg in scenario_msgs:
            if isinstance(msg, dict):
                await self.send_message(str(msg.get("message") or ""), images=(msg.get("images") or []))
            else:
                await self.send_message(str(msg))
            await asyncio.sleep(0.4)

        if assert_state and not self.use_http:
            from core.order_state_tracker import order_tracker

            st = order_tracker.get_state(TEST_USER_ID)
            zone = str(getattr(st, "zone", "") or "").strip()
            numero = str(getattr(st, "numero", "") or "").strip()

            if arg in {"--scenario-validation", "--scenario_validation"}:
                if not zone:
                    raise AssertionError("OrderStateTracker zone missing after validation scenario")
                if not numero:
                    raise AssertionError("OrderStateTracker numero missing after validation scenario")
                if not re.fullmatch(r"0\d{9}", numero):
                    raise AssertionError(f"OrderStateTracker numero invalid format: {numero}")

        # CSV
        try:
            out_path = Path("tests/rag_scenario_results.csv")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(
                    f,
                    fieldnames=[
                        "turn",
                        "question",
                        "response",
                        "duration_ms",
                        "status_code",
                        "prompt_tokens",
                        "completion_tokens",
                        "total_tokens",
                        "cached_tokens",
                        "cost",
                        "search_method",
                    ],
                )
                w.writeheader()
                for r in self.eval_rows:
                    w.writerow(r)
            print(f"\nCSV saved: {out_path}\n")
        except Exception as e:
            print(f"\n[WARN] Impossible d'écrire le CSV scénario: {e}\n")

        try:
            json_path = self.save_json_report({"mode": "scenario"})
            if json_path:
                print(f"JSON saved: {json_path}")
        except Exception:
            pass

        # Résumé
        print("\n" + "=" * 80)
        print("✅ SCÉNARIO TERMINÉ")
        print("=" * 80 + "\n")

        turns = int(self._agg.get("turns") or 0)
        if turns > 0:
            avg_ms = self._agg["duration_ms"] / turns
            avg_prompt = self._agg["prompt_tokens"] / turns
            avg_completion = self._agg["completion_tokens"] / turns
            avg_total = self._agg["total_tokens"] / turns
            avg_cached = self._agg["cached_tokens"] / turns
            avg_cost = self._agg["cost"] / turns
            print("Moyennes (par tour):")
            print(f"- duration_ms: {avg_ms:.0f}")
            print(f"- prompt_tokens: {avg_prompt:.1f}")
            print(f"- completion_tokens: {avg_completion:.1f}")
            print(f"- total_tokens: {avg_total:.1f}")
            print(f"- cached_tokens: {avg_cached:.1f}")
            print(f"- cost: {avg_cost:.6f}")
            print("")


async def main() -> None:
    # 🧪 TEST OVERRIDE: Si une variable de modèle est définie pour le test, on force l'override dans le core.
    test_model = os.getenv("BOTLIVE_LLM_MODEL")
    if test_model:
        os.environ["BOTLIVE_LLM_OVERRIDE"] = test_model
        print(f"🧪 [CONFIG] Modèle forcé pour le test: {test_model}")

    simulator = RAGSimulator()

    # Choix mode: par défaut in-process. Ajoute --http pour forcer l'appel HTTP.
    simulator.use_http = any(a in {"--http", "--http-mode"} for a in sys.argv[1:])
    if simulator.use_http:
        simulator.chat_url = await _resolve_chat_url()

    print("\n" + "=" * 80)
    print(f"🧪 RAG SIMULATOR - TEST_USER_ID: {TEST_USER_ID}")
    print(f"🧪 MODE: {'HTTP' if simulator.use_http else 'IN-PROCESS'}")
    if simulator.use_http:
        print(f"🧪 CHAT_URL: {simulator.chat_url}")
    print(f"🧪 COMPANY_ID: {TEST_COMPANY_ID}")
    print("=" * 80 + "\n")

    # Scénario: supporter n'importe quel ordre d'arguments (ex: --http --scenario)
    if any(a.startswith("--scenario") or a in {"--whatsapp58", "--whatsapp120", "--scenario-validation", "--scenario_validation"} for a in sys.argv[1:]):
        await simulator.run_scenario()
    else:
        await simulator.run_interactive()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass

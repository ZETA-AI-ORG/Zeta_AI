#!/usr/bin/env python3
"""\
🧪 AMANDA BOTLIVE SIMULATOR - PREMIUM OBSERVABILITY EDITION (2026)

Simule une conversation sur l'endpoint /amandabotlive avec une visibilité totale sur :
- Le Prompt (Loader vs Fallback)
- Les Slots de Détection (Article, Zone, Téléphone)
- Le Statut du Dossier (Handoff & Complet)
- Le Thinking (Processus mental du LLM)
- Les Métriques (Tokens, Coûts, Timings OCR/LLM)
"""

import asyncio
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Path setup
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv()

# Colors & UI
C_RESET  = "\033[0m"
C_BOLD   = "\033[1m"
C_DIM    = "\033[2m"
C_UNDER  = "\033[4m"
C_RED    = "\033[91m"
C_GREEN  = "\033[92m"
C_YELLOW = "\033[93m"
C_BLUE   = "\033[94m"
C_MAGENTA = "\033[95m"
C_CYAN   = "\033[96m"
C_WHITE  = "\033[97m"
C_ORANGE = "\033[38;5;208m"

C_BG_BLUE = "\033[44m"
C_BG_MAGENTA = "\033[45m"
C_BG_GREEN = "\033[42m"
C_BG_RED = "\033[41m"

DEFAULT_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"
TEST_USER_ID = f"test_amanda_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

class AmandaPremiumSimulator:
    def __init__(self, mode="HTTP", url=None):
        self.mode = mode
        self.url = url or os.getenv("CHAT_URL") or "http://127.0.0.1:8002/amandabotlive"
        self.company_id = os.getenv("TEST_COMPANY_ID") or DEFAULT_COMPANY_ID
        self.user_id = TEST_USER_ID
        self.history = ""
        self.turn = 0
        
    def log_header(self, title):
        print(f"\n{C_MAGENTA}{'━'*100}{C_RESET}")
        print(f"{C_BOLD}{C_MAGENTA}✨ {title}{C_RESET}")
        print(f"{C_MAGENTA}{'━'*100}{C_RESET}")

    def log_section(self, icon, title, color=C_BLUE):
        print(f"\n{color}{C_BOLD}{icon} {title}{C_RESET}")
        print(f"{color}{'─'*60}{C_RESET}")

    async def chat(self, message, images=None):
        self.turn += 1
        print(f"\n{C_BG_MAGENTA}{C_WHITE}{C_BOLD}  TOUR {self.turn}  {C_RESET} {C_MAGENTA}🗣️  VOUS: {message}{C_RESET}")
        if images:
            for img in images:
                print(f"      🖼️  Image: {img}")

        payload = {
            "company_id": self.company_id,
            "user_id": self.user_id,
            "message": message,
            "images": images or []
        }

        start_t = time.time()
        try:
            if self.mode == "HTTP":
                async with httpx.AsyncClient(timeout=120.0) as client:
                    r = await client.post(self.url, json=payload)
                    r.raise_for_status()
                    data = r.json()
            else:
                # IN-PROCESS
                from core.models import ChatRequest
                from Zeta_AI.app import amanda_botlive_endpoint
                from starlette.requests import Request
                
                req = ChatRequest(**payload)
                scope = {"type": "http"}
                fake_req = Request(scope)
                data = await amanda_botlive_endpoint(req, fake_req)
                if hasattr(data, "body"):
                    data = json.loads(data.body.decode())

            elapsed = (time.time() - start_t) * 1000
            self._display_response(data, elapsed)

        except Exception as e:
            print(f"\n{C_RED}{C_BOLD}❌ ERREUR PIPELINE: {e}{C_RESET}")
            import traceback
            traceback.print_exc()

    def _display_response(self, d, total_ms):
        # 1. STATUS BARS (Handoff / Dossier)
        handoff = d.get("handoff", False)
        complet = d.get("dossier_complet", False)
        
        h_status = f"{C_BG_RED}{C_WHITE} ##HANDOFF## DETECTED {C_RESET}" if handoff else f"{C_DIM}Handoff: OFF{C_RESET}"
        c_status = f"{C_BG_GREEN}{C_WHITE} ✅ DOSSIER COMPLET {C_RESET}" if complet else f"{C_YELLOW}⚠ DOSSIER INCOMPLET{C_RESET}"
        print(f"\n  {h_status}    {c_status}")

        # 2. DIAGNOSTIQUE PIPELINE
        self.log_section("🔍", "DIAGNOSTIQUE PIPELINE", C_YELLOW)
        
        model = d.get("model", "∅")
        p_src = d.get("prompt_source", "∅")
        plan = d.get("plan", "starter")
        print(f"  {C_BOLD}Modèle:{C_RESET} {C_CYAN}{model}{C_RESET}  |  {C_BOLD}Plan:{C_RESET} {plan.upper()}  |  {C_BOLD}Source:{C_RESET} {p_src}")

        # SLOTS
        slots = d.get("slots_status", {})
        det = d.get("detection_slots", {})
        print(f"\n  {C_BOLD}Statut des slots:{C_RESET}")
        for s in ["article", "zone", "telephone", "paiement_optionnel"]:
            val = slots.get(s)
            icon = f"{C_GREEN}✓{C_RESET}" if val else f"{C_RED}○{C_RESET}"
            raw_val = det.get(s) if s != "paiement_optionnel" else det.get("paiement")
            print(f"    {icon} {s:10}: {C_DIM}{raw_val or '∅'}{C_RESET}")

        # 3. DATA BLOCKS (Index & Catalogue)
        self.log_section("📦", "CHARGEMENT DONNÉES (RAG)", C_MAGENTA)
        
        p_idx = str(d.get("product_index", "")).strip() or "∅"
        c_blk = str(d.get("catalogue_block", "")).strip() or "∅"
        
        print(f"  {C_BOLD}{C_UNDER}PRODUCT_INDEX:{C_RESET}")
        print(f"  {C_DIM}{p_idx}{C_RESET}")
        
        print(f"\n  {C_BOLD}{C_UNDER}CATALOGUE/BOUTIQUE_INFO:{C_RESET}")
        print(f"  {C_DIM}{c_blk}{C_RESET}")

        # 4. THINKING
        thinking = d.get("thinking_raw", "") or str(d.get("thinking", ""))
        if thinking:
            self.log_section("🧠", "THINKING (Raisonnement LLM)", C_ORANGE)
            print(f"{C_DIM}{thinking}{C_RESET}")

        # 5. METRICS & TIMINGS
        self.log_section("📊", "PERFORMANCE & COÛTS", C_CYAN)
        
        d = d or {} # Sécurité : si 'd' est None, on le transforme en dictionnaire vide
        usage_data = d.get("usage", {}) or {}
        tokens_in = d.get("prompt_tokens", 0) or usage_data.get("prompt_tokens", 0)
        tokens_out = d.get("completion_tokens", 0) or usage_data.get("completion_tokens", 0)
        cost = d.get("cost", 0.0)
        
        print(f"  {C_BOLD}Tokens:{C_RESET} In={tokens_in} | Out={tokens_out} | Total={tokens_in+tokens_out}")
        col_cost = C_GREEN if cost < 0.001 else C_YELLOW if cost < 0.01 else C_RED
        print(f"  {C_BOLD}Coût  :{C_RESET} {col_cost}${cost:.6f}{C_RESET} (OpenRouter)")
        
        timings = d.get("timings", {})
        print(f"  {C_BOLD}Temps :{C_RESET} {C_BOLD}{total_ms:.0f}ms{C_RESET} total")
        if timings:
            t_str = " | ".join([f"{k}: {v}ms" for k, v in timings.items()])
            print(f"    {C_DIM}phases: {t_str}{C_RESET}")

        # 6. RESPONSE HEADER (Moved to the end)
        bot_resp = d.get("response", "")
        self.log_section("🤖", "RÉPONSE AMANDA", C_GREEN)
        print(f"\n{C_WHITE}{C_BOLD}{bot_resp}{C_RESET}\n")

        print(f"\n{C_MAGENTA}{'━'*100}{C_RESET}")

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="Utiliser le mode HTTP")
    parser.add_argument("--url", type=str, help="URL de l'endpoint /amandabotlive")
    args = parser.parse_args()

    sim = AmandaPremiumSimulator(mode="HTTP" if args.http else "IN-PROCESS", url=args.url)
    
    sim.log_header(f"AMANDA SIMULATOR V3.0 — {sim.mode} MODE")
    print(f"🧪 URL: {sim.url}")
    print(f"🧪 COMPANY_ID: {sim.company_id}")
    print(f"🧪 USER_ID: {sim.user_id}")
    
    print(f"\n{C_CYAN}Tapez votre message ou 'exit' pour quitter.{C_RESET}")
    print(f"{C_DIM}Note: Pour tester les images, utilisez le mode script ou passez des URLs.{C_RESET}")

    while True:
        try:
            msg = input(f"\n{C_BOLD}🗣️  VOUS: {C_RESET}").strip()
            if not msg: continue
            if msg.lower() in ["exit", "quit", "q"]: break
            
            # Simple check for image link
            images = []
            if "http" in msg and (".png" in msg.lower() or ".jpg" in msg.lower()):
                parts = msg.split(" ")
                images = [p for p in parts if p.startswith("http")]
                msg = " ".join([p for p in parts if not p.startswith("http")]) or "Image envoyée"

            await sim.chat(msg, images=images)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

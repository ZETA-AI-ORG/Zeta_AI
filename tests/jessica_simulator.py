#!/usr/bin/env python3
"""\
🧪 JESSICA RAG SIMULATOR - PREMIUM OBSERVABILITY EDITION (2026)

Simule une conversation sur l'endpoint /jessicaragbot avec une visibilité totale sur :
- Le Prompt (Source & Enrichment)
- Le Product Index (Top 5 injecté)
- Le Catalogue Block (Infos produits extraites)
- Le Thinking (Processus mental du LLM)
- Les Métriques (Tokens, Coûts OpenRouter fixes, Timings)
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
C_BG_CYAN = "\033[46m"

DEFAULT_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"
DEFAULT_TEST_MODEL = "qwen/qwen3.5-flash-02-23"
TEST_USER_ID = f"test_jessica_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

class PremiumSimulator:
    def __init__(self, mode="HTTP", url=None):
        self.mode = mode
        self.url = url or os.getenv("CHAT_URL") or "http://127.0.0.1:8002/jessicaragbot"
        self.company_id = os.getenv("TEST_COMPANY_ID") or DEFAULT_COMPANY_ID
        self.model_name = os.getenv("TEST_MODEL_NAME") or DEFAULT_TEST_MODEL
        self.user_id = TEST_USER_ID
        self.history = ""
        self.turn = 0
        
    def log_header(self, title):
        print(f"\n{C_CYAN}{'━'*100}{C_RESET}")
        print(f"{C_BOLD}{C_CYAN}🌟 {title}{C_RESET}")
        print(f"{C_CYAN}{'━'*100}{C_RESET}")

    def log_section(self, icon, title, color=C_BLUE):
        print(f"\n{color}{C_BOLD}{icon} {title}{C_RESET}")
        print(f"{color}{'─'*60}{C_RESET}")

    async def chat(self, message, images=None):
        self.turn += 1
        print(f"\n{C_BG_BLUE}{C_WHITE}{C_BOLD}  TOUR {self.turn}  {C_RESET} {C_BLUE}🗣️  VOUS: {message}{C_RESET}")
        if images:
            print(f"      🖼️  Images: {images}")

        payload = {
            "company_id": self.company_id,
            "user_id": self.user_id,
            "message": message,
            "images": images or [],
            "model_name": self.model_name,
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
                from Zeta_AI.app import jessica_ragbot_endpoint
                from starlette.requests import Request
                
                req = ChatRequest(**payload)
                scope = {"type": "http"}
                fake_req = Request(scope)
                data = await jessica_ragbot_endpoint(req, fake_req)
                if hasattr(data, "body"):
                    data = json.loads(data.body.decode())

            elapsed = (time.time() - start_t) * 1000
            self._display_response(data, elapsed)

        except Exception as e:
            print(f"\n{C_RED}{C_BOLD}❌ ERREUR PIPELINE: {e}{C_RESET}")
            import traceback
            traceback.print_exc()

    def _display_response(self, d, total_ms):
        # 1. DEBUG DATA (The meat)
        self.log_section("🔍", "DIAGNOSTIQUE PIPELINE", C_YELLOW)
        
        # Row 1: Model & Plan
        model = d.get("model", "∅")
        plan = d.get("plan", "starter")
        boost = "⚡ ACTIVÉ" if d.get("has_boost") else "OFF"
        rank = d.get("rank", "?")
        print(f"  {C_BOLD}Modèle:{C_RESET} {C_CYAN}{model}{C_RESET}  |  {C_BOLD}Plan:{C_RESET} {plan.upper()} ({boost})  |  {C_BOLD}Rang:{C_RESET} {rank}")
        
        # Row 2: Prompt Info
        p_src = d.get("prompt_source", "∅")
        intent = d.get("intent", "∅")
        print(f"  {C_BOLD}Prompt:{C_RESET} {p_src}  |  {C_BOLD}Intent:{C_RESET} {C_MAGENTA}{intent}{C_RESET}")

        # 2. DATA BLOCKS (Index & Catalogue)
        self.log_section("📦", "CHARGEMENT DONNÉES (RAG)", C_MAGENTA)
        
        p_idx = str(d.get("product_index", "")).strip() or "∅"
        c_blk = str(d.get("catalogue_block", "")).strip() or "∅"
        
        print(f"  {C_BOLD}{C_UNDER}PRODUCT_INDEX (Top 5):{C_RESET}")
        print(f"  {C_DIM}{p_idx}{C_RESET}")
        
        print(f"\n  {C_BOLD}{C_UNDER}CATALOGUE_BLOCK (Context):{C_RESET}")
        print(f"  {C_DIM}{c_blk}{C_RESET}")

        # 3. THINKING
        thinking = d.get("thinking", "")
        if thinking:
            self.log_section("🧠", "THINKING (Raisonnement LLM)", C_ORANGE)
            print(f"{C_DIM}{thinking}{C_RESET}")

        # 4. METRICS & TIMINGS
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

        # 5. RESPONSE HEADER (Moved to the end so user doesn't have to scroll up)
        bot_resp = d.get("response", "")
        self.log_section("🤖", "RÉPONSE JESSICA", C_GREEN)
        print(f"\n{C_WHITE}{C_BOLD}{bot_resp}{C_RESET}\n")

        print(f"\n{C_CYAN}{'━'*100}{C_RESET}")

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="Utiliser le mode HTTP")
    parser.add_argument("--url", type=str, help="URL de l'endpoint /jessicaragbot")
    args = parser.parse_args()

    sim = PremiumSimulator(mode="HTTP" if args.http else "IN-PROCESS", url=args.url)
    
    sim.log_header(f"JESSICA SIMULATOR V3.0 — {sim.mode} MODE")
    print(f"🧪 URL: {sim.url}")
    print(f"🧪 COMPANY_ID: {sim.company_id}")
    print(f"🧪 MODEL_NAME: {sim.model_name}")
    print(f"🧪 USER_ID: {sim.user_id}")
    
    print(f"\n{C_YELLOW}Tapez votre message ou 'exit' pour quitter.{C_RESET}")
    
    while True:
        try:
            msg = input(f"\n{C_BOLD}🗣️  VOUS: {C_RESET}").strip()
            if not msg: continue
            if msg.lower() in ["exit", "quit", "q"]: break
            await sim.chat(msg)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

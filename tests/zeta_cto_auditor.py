#!/usr/bin/env python3
import sys
import json
import re

C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_RED = "\033[31m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_BLUE = "\033[34m"
C_CYAN = "\033[36m"
C_WHITE = "\033[37m"
C_MAGENTA = "\033[35m"
C_BG_RED = "\033[41m"
C_BG_BLUE = "\033[44m"

class ZetaMonitor:
    def log_diagnostic(self, level, message, solution=None):
        color = C_RED if level == "ERROR" else C_YELLOW
        prefix = "🚨 ALERTE" if level == "ERROR" else "⚠️ ATTENTION"
        print(f"\n{C_BOLD}{color}{prefix} : {message}{C_RESET}")
        if solution:
            print(f"{C_BOLD}{C_GREEN}🔧 SOLUTION : {C_WHITE}{solution}{C_RESET}")

    def process_line(self, line):
        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[([A-Z]+)\] \[([A-Z_]+)\] (.*?) \| (\{.*\})', line)
        if not match: return
        
        timestamp, log_level, phase, event, json_str = match.groups()
        try: data = json.loads(json_str)
        except: return

        print(f"\n{C_BOLD}{C_WHITE}[{timestamp}]{C_RESET} {C_BOLD}{C_CYAN}{phase}{C_RESET} — {event}")
        
        vars_parts = []
        for k, v in data.items():
            if k in ["phase", "event", "request_id", "params", "unreplaced_tags"]: continue
            vars_parts.append(f"{C_DIM}{k}:{C_RESET}{C_WHITE}{v}{C_RESET}")
        
        if vars_parts:
            print(f"   {' | '.join(vars_parts)}")

        # --- GESTION DES ANOMALIES SPÉCIFIQUES ---
        
        # 1. Analyse de l'état du Prompt (Health Check)
        if phase == "PROMPT_STATE":
            tags = data.get("unreplaced_tags", [])
            if tags:
                print(f"   {C_BG_RED}{C_WHITE}{C_BOLD} 🛑 DÉFAILLANCE INJECTION PROMPT DÉTECTÉE {C_RESET}")
                print(f"   {C_RED}Variables non remplacées (Hardcodées) :{C_RESET}")
                for tag in tags:
                    print(f"      ❌ {C_BOLD}{C_YELLOW}{tag}{C_RESET}")
                self.log_diagnostic("ERROR", "Échec du RAG ou de la DB.", "Vérifiez les erreurs SQL précédentes ou la disponibilité des données dans Supabase.")
            else:
                print(f"   {C_GREEN}✅ Prompt 100% propre (Injection réussie).{C_RESET}")

        # 2. Analyse des crashs SQL (ex: Problème d'UUID)
        elif "erreur SQL" in str(event):
            sql_error = data.get("sql_error", str(data))
            if "invalid input syntax for type uuid" in str(sql_error):
                self.log_diagnostic(
                    "ERROR", "Crash Type DB (UUID vs Texte)", 
                    "L'API utilise un ID Firebase mais la DB attend un UUID. Assurez-vous que `resolve_firebase_to_uuid` est bien appelé au début de l'endpoint."
                )

        # 3. Diagnostic du CACHE (REDIS)
        elif phase == "CACHE_STATE":
            status = data.get("status", "")
            source = data.get("source", "")
            key = data.get("key", "")
            if status == "HIT":
                print(f"   {C_GREEN}⚡ REDIS HIT :{C_RESET} Donnée chargée depuis le cache ({C_DIM}{key}{C_RESET})")
            else:
                print(f"   {C_YELLOW}🐢 REDIS MISS :{C_RESET} Donnée absente. Extraction depuis {C_BOLD}{source}{C_RESET}...")

        # 4. Diagnostic MÉMOIRE (DB 2)
        elif phase == "MEMORY_SYNC":
            action = data.get("action", "")
            print(f"   {C_MAGENTA}🧠 MÉMOIRE (DB 2) :{C_RESET} {action} effectuée pour cet utilisateur.")

        if phase == "TIMING_SUMMARY":
            print(f"{C_BLUE}{'─'*100}{C_RESET}")

    def run(self):
        print(f"{C_BG_BLUE}{C_BOLD}  🚨 ZETA AI — PLAYBOOK DE DÉBOGAGE & MONITORING (CTO EDITION)  {C_RESET}\n")
        try:
            for line in sys.stdin:
                self.process_line(line)
                sys.stdout.flush()
        except KeyboardInterrupt:
            print(f"\n{C_YELLOW}Arrêt du monitoring.{C_RESET}")

if __name__ == "__main__":
    monitor = ZetaMonitor()
    monitor.run()

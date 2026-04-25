#!/usr/bin/env python3
import sys
import json
import re
from datetime import datetime

# --- CONFIGURATION DES COULEURS ---
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
C_BG_GREEN = "\033[42m"

# --- MÉTRIQUES D'OBSERVABILITÉ ---
metrics = {
    "redis_hits": 0,
    "redis_misses": 0,
    "redis_errors": 0,
    "injection_spikes": 0,
    "prompts_total": 0,
    "total_latency": 0.0,
    "sql_errors": 0
}

class ZetaAuditor:
    def log_diagnostic(self, level, message, solution=None):
        color = C_RED if level == "ERROR" else C_YELLOW
        prefix = "🚨 ALERTE" if level == "ERROR" else "⚠️ ATTENTION"
        print(f"\n{C_BOLD}{color}{prefix} : {message}{C_RESET}")
        if solution:
            print(f"{C_BOLD}{C_GREEN}🔧 SOLUTION : {C_WHITE}{solution}{C_RESET}")

    def process_line(self, line):
        line = line.strip()
        if not line: return

        # --- 1. RADAR REDIS (PERFORMANCE & SANTÉ) ---
        if "[REDIS_HIT]" in line:
            metrics["redis_hits"] += 1
            print(f"   {C_GREEN}⚡ [CACHE] Hit Redis réussi{C_RESET}")
            return
            
        if "[REDIS_MISS]" in line:
            metrics["redis_misses"] += 1
            print(f"   {C_YELLOW}🐢 [CACHE] Miss Redis ! Sync Supabase déclenché.{C_RESET}")
            return

        if any(err in line for err in ["Error connecting to Redis", "Connection timeout", "RedisConnectionError"]):
            metrics["redis_errors"] += 1
            self.log_diagnostic("ERROR", "REDIS DISCONNECTED", "Vérifiez 'docker ps' pour le conteneur zeta-redis.")
            return

        # --- 2. RADAR LATENCE (BLOC 2) ---
        latency_match = re.search(r"Prompt built in (\d+(?:\.\d+)?)ms", line)
        if latency_match:
            metrics["prompts_total"] += 1
            build_time = float(latency_match.group(1))
            metrics["total_latency"] += build_time
            if build_time > 50.0:
                metrics["injection_spikes"] += 1
                print(f"   {C_RED}🐌 [LATENCE] Injection lente : {build_time}ms !{C_RESET}")
            return

        # --- 3. ANALYSE JSON (STRUCTURELLE) ---
        # Format attendu : Timestamp [LEVEL] [PHASE] Event | {JSON}
        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[([A-Z]+)\] \[([A-Z_]+)\] (.*?) \| (\{.*\})', line)
        if not match: return
        
        timestamp, log_level, phase, event, json_str = match.groups()
        try: data = json.loads(json_str)
        except: return

        # Alertes sur les tags non remplacés (Bloc 2 Health)
        if phase == "PROMPT_STATE":
            tags = data.get("unreplaced_tags", [])
            if tags:
                print(f"\n{C_BG_RED}{C_WHITE}{C_BOLD} 🛑 DÉFAILLANCE INJECTION PROMPT {C_RESET}")
                for tag in tags:
                    print(f"   ❌ Variable Hardcodée détectée : {C_BOLD}{C_YELLOW}{tag}{C_RESET}")
                metrics["sql_errors"] += 1

        # Diagnostic SQL / UUID
        if "erreur SQL" in str(event).lower():
            metrics["sql_errors"] += 1
            self.log_diagnostic("ERROR", f"Crash DB : {event}", "Vérifiez les types UUID/Text.")

    def run(self):
        print(f"{C_BG_BLUE}{C_BOLD}  🚨 ZETA AI — OBSERVABILITY PIPELINE (CTO EDITION)  {C_RESET}")
        print(f"{C_DIM}Monitoring : Redis Performance | Prompt Latency | Injection Health{C_RESET}\n")
        
        try:
            for line in sys.stdin:
                self.process_line(line)
                sys.stdout.flush()
        except KeyboardInterrupt:
            self.print_final_report()

    def print_final_report(self):
        print(f"\n\n{C_BOLD}{C_WHITE}📊 --- RAPPORT DE SANTÉ ZETA AI ---{C_RESET}")
        total_cache = metrics["redis_hits"] + metrics["redis_misses"]
        hit_ratio = (metrics["redis_hits"] / total_cache * 100) if total_cache > 0 else 0
        avg_lat = (metrics["total_latency"] / metrics["prompts_total"]) if metrics["prompts_total"] > 0 else 0
        
        print(f"🔹 Cache Redis    : {total_cache} appels | {C_GREEN if hit_ratio >= 95 else C_YELLOW}HIT RATE: {hit_ratio:.1f}%{C_RESET}")
        print(f"🔹 Latence Moy.   : {C_CYAN}{avg_lat:.1f}ms{C_RESET} (Prompt Injection)")
        print(f"🔹 Anomalies      : {C_RED if metrics['redis_errors'] > 0 else C_WHITE}Coupures Redis: {metrics['redis_errors']}{C_RESET}")
        print(f"🔹 Bottlenecks    : {C_RED if metrics['injection_spikes'] > 0 else C_WHITE}Pics Latence (>50ms): {metrics['injection_spikes']}{C_RESET}")
        print(f"🔹 Fautes SQL     : {C_RED if metrics['sql_errors'] > 0 else C_WHITE}{metrics['sql_errors']}{C_RESET}")
        print(f"{C_BOLD}{'─'*40}{C_RESET}\n")
        sys.exit(0)

if __name__ == "__main__":
    auditor = ZetaAuditor()
    auditor.run()

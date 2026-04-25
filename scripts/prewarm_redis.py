#!/usr/bin/env python3
import asyncio
import logging
import time
import sys
import os

# Ajout du chemin pour importer les modules core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.company_cache_manager import company_cache

# Couleurs pour le terminal
C_GREEN = "\033[32m"
C_CYAN = "\033[36m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_DIM = "\033[2m"
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_BG_GREEN = "\033[42m"
C_BG_RED = "\033[41m"

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("prewarm")

async def run_prewarm():
    print(f"\n{C_BOLD}{C_CYAN}🚀 DÉMARRAGE DE LA SYNCHRONISATION MASSIVE ZETA AI{C_RESET}")
    print(f"{C_DIM}Source : Supabase (PostgreSQL) | Destination : Redis (RAM Cache){C_RESET}\n")
    
    start_time = time.time()
    
    # 1. Sync des Profils (CompanyCacheManager)
    print(f"{C_YELLOW}📦 Étape 1 : Synchronisation des profils entreprises...{C_RESET}")
    result = await company_cache.sync_all_companies()
    
    if result.get("status") == "ok":
        count = result.get("count", 0)
        print(f"   {C_GREEN}✅ {count} profils d'entreprises synchronisés.{C_RESET}")
    else:
        print(f"   {C_RED}❌ Erreur lors de la sync des profils : {result.get('message')}{C_RESET}")

    # 2. Sync des Catalogues (À venir dans une prochaine étape si besoin)
    # print(f"{C_YELLOW}🛍️ Étape 2 : Synchronisation des catalogues produits...{C_RESET}")
    # ... logique catalogue ...

    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n{C_BOLD}{C_BG_GREEN if result.get('status') == 'ok' else C_BG_RED}  SYNC TERMINÉE EN {duration:.2f}s  {C_RESET}")
    print(f"{C_DIM}Votre infrastructure est maintenant 'chaude' et prête à servir.{C_RESET}\n")

if __name__ == "__main__":
    try:
        asyncio.run(run_prewarm())
    except KeyboardInterrupt:
        print(f"\n{C_RED}Synchronisation interrompue.{C_RESET}")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧹 CLEANUP AUTOMATIQUE DES NOTEPADS EXPIRÉS
À exécuter quotidiennement via cron job
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_notepad import get_supabase_notepad
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Nettoie tous les notepads expirés (> 7 jours)"""
    logger.info("🧹 Démarrage cleanup notepads expirés...")
    
    notepad = get_supabase_notepad()
    deleted_count = await notepad.cleanup_expired_notepads()
    
    logger.info(f"✅ Cleanup terminé : {deleted_count} notepads supprimés")
    return deleted_count


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 SCRIPT POUR CONSULTER LES LOGS SERVEUR JSON
Usage: python3 view_server_logs.py [command] [options]
"""

import sys
import json
from pathlib import Path
from datetime import datetime


def print_help():
    """Affiche l'aide"""
    print("""
📊 VIEW SERVER LOGS - Consultation des logs serveur complets

COMMANDES:
  all [date]                Tous les logs
  errors [date]             Uniquement les erreurs
  info [date]               Uniquement les infos
  search <query> [date]     Rechercher dans les logs
  stats [date]              Statistiques
  tail [n]                  Derniers N logs (défaut: 50)
  follow                    Suivre les logs en temps réel

EXEMPLES:
  python3 view_server_logs.py all
  python3 view_server_logs.py errors 2025-10-14
  python3 view_server_logs.py search "403 Forbidden"
  python3 view_server_logs.py tail 100
  python3 view_server_logs.py stats

DATE FORMAT: YYYY-MM-DD (défaut: aujourd'hui)
""")


def get_logs(date: str = None) -> list:
    """Récupère les logs d'une date"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    log_file = Path("logs/server") / f"server_{date}.json"
    
    if not log_file.exists():
        return []
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Erreur lecture logs: {e}")
        return []


def print_log(log: dict, verbose: bool = False):
    """Affiche un log de manière lisible"""
    timestamp = log.get("timestamp", "N/A")
    level = log.get("level", "INFO")
    source = log.get("source", "unknown")
    message = log.get("message", "")
    
    # Couleur selon niveau
    colors = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Vert
        "WARNING": "\033[33m",  # Jaune
        "ERROR": "\033[31m",    # Rouge
        "CRITICAL": "\033[35m"  # Magenta
    }
    color = colors.get(level, "\033[0m")
    reset = "\033[0m"
    
    print(f"{color}[{timestamp}] {level} - {source}{reset}")
    print(f"  {message}")
    
    if verbose:
        metadata = log.get("metadata", {})
        if metadata:
            print(f"  📎 {json.dumps(metadata, indent=2)}")
    
    print()


def cmd_all(date: str = None):
    """Affiche tous les logs"""
    logs = get_logs(date)
    print(f"\n📊 {len(logs)} log(s) trouvé(s)\n")
    for log in logs:
        print_log(log)


def cmd_errors(date: str = None):
    """Affiche uniquement les erreurs"""
    logs = get_logs(date)
    errors = [log for log in logs if log.get("level") in ["ERROR", "CRITICAL"]]
    print(f"\n🔴 {len(errors)} erreur(s) trouvée(s)\n")
    for log in errors:
        print_log(log, verbose=True)


def cmd_info(date: str = None):
    """Affiche uniquement les infos"""
    logs = get_logs(date)
    infos = [log for log in logs if log.get("level") == "INFO"]
    print(f"\n📘 {len(infos)} info(s) trouvée(s)\n")
    for log in infos:
        print_log(log)


def cmd_search(query: str, date: str = None):
    """Recherche dans les logs"""
    logs = get_logs(date)
    query_lower = query.lower()
    
    results = [
        log for log in logs
        if query_lower in log.get("message", "").lower() or
           query_lower in log.get("source", "").lower()
    ]
    
    print(f"\n🔍 {len(results)} résultat(s) pour '{query}'\n")
    for log in results:
        print_log(log, verbose=True)


def cmd_stats(date: str = None):
    """Affiche les statistiques"""
    logs = get_logs(date)
    
    if not logs:
        print(f"📭 Aucun log trouvé")
        return
    
    # Compter par niveau
    levels = {}
    sources = {}
    for log in logs:
        level = log.get("level", "UNKNOWN")
        source = log.get("source", "unknown")
        levels[level] = levels.get(level, 0) + 1
        sources[source] = sources.get(source, 0) + 1
    
    print(f"\n📊 STATISTIQUES - {date or 'aujourd hui'}")
    print(f"\n{'='*60}")
    print(f"Total logs: {len(logs)}")
    
    print(f"\n📈 Par niveau:")
    for level, count in sorted(levels.items()):
        pct = count / len(logs) * 100
        print(f"  {level:12} : {count:5} ({pct:5.1f}%)")
    
    print(f"\n📂 Top 10 sources:")
    for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True)[:10]:
        pct = count / len(logs) * 100
        print(f"  {source:30} : {count:5} ({pct:5.1f}%)")
    
    print(f"{'='*60}\n")


def cmd_tail(n: int = 50, date: str = None):
    """Affiche les N derniers logs"""
    logs = get_logs(date)
    last_logs = logs[-n:] if len(logs) > n else logs
    
    print(f"\n📜 {len(last_logs)} dernier(s) log(s)\n")
    for log in last_logs:
        print_log(log)


def cmd_follow():
    """Suit les logs en temps réel"""
    import time
    
    print("👀 Suivi des logs en temps réel (Ctrl+C pour arrêter)...\n")
    
    last_count = 0
    try:
        while True:
            logs = get_logs()
            if len(logs) > last_count:
                # Afficher les nouveaux logs
                for log in logs[last_count:]:
                    print_log(log)
                last_count = len(logs)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 Arrêt du suivi")


def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command in ["help", "-h", "--help"]:
        print_help()
        sys.exit(0)
    
    if command == "all":
        date = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_all(date)
    
    elif command == "errors":
        date = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_errors(date)
    
    elif command == "info":
        date = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_info(date)
    
    elif command == "search":
        if len(sys.argv) < 3:
            print("❌ Usage: python3 view_server_logs.py search <query> [date]")
            sys.exit(1)
        query = sys.argv[2]
        date = sys.argv[3] if len(sys.argv) > 3 else None
        cmd_search(query, date)
    
    elif command == "stats":
        date = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_stats(date)
    
    elif command == "tail":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        date = sys.argv[3] if len(sys.argv) > 3 else None
        cmd_tail(n, date)
    
    elif command == "follow":
        cmd_follow()
    
    else:
        print(f"❌ Commande inconnue: {command}")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

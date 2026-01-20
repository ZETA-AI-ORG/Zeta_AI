#!/usr/bin/env python3
"""
📖 VISUALISEUR DE LOGS SERVEUR

Lit et affiche les logs serveur JSON de manière lisible.

Usage:
    python tests/view_server_logs.py                    # Logs du jour
    python tests/view_server_logs.py --date 2025-10-21  # Logs d'une date
    python tests/view_server_logs.py --errors           # Seulement les erreurs
    python tests/view_server_logs.py --search "thinking" # Recherche
    python tests/view_server_logs.py --last 50          # 50 derniers logs
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Ajouter le path parent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.server_logger import get_server_logs, print_server_logs


def view_logs(date=None, level=None, search=None, last=None):
    """Affiche les logs avec filtres"""
    
    # Récupérer les logs
    logs = get_server_logs(date)
    
    if not logs:
        print(f"📭 Aucun log trouvé pour {date or 'aujourd hui'}")
        return
    
    # Filtrer par niveau
    if level:
        logs = [log for log in logs if log.get("level") == level.upper()]
    
    # Filtrer par recherche
    if search:
        search_lower = search.lower()
        logs = [
            log for log in logs 
            if search_lower in log.get("message", "").lower()
            or search_lower in log.get("source", "").lower()
        ]
    
    # Limiter aux derniers N
    if last:
        logs = logs[-int(last):]
    
    # Afficher
    print(f"\n{'='*80}")
    print(f"📋 LOGS SERVEUR - {date or datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*80}\n")
    print(f"Total: {len(logs)} logs\n")
    
    for i, log in enumerate(logs, 1):
        timestamp = log.get("timestamp", "")
        level = log.get("level", "INFO")
        source = log.get("source", "unknown")
        message = log.get("message", "")
        
        # Couleur selon niveau
        if level == "ERROR":
            level_icon = "❌"
        elif level == "WARNING":
            level_icon = "⚠️"
        elif level == "INFO":
            level_icon = "ℹ️"
        else:
            level_icon = "📝"
        
        print(f"{i}. {level_icon} [{timestamp}] {level} - {source}")
        print(f"   {message[:200]}")
        
        # Afficher metadata si présente
        if "metadata" in log and log["metadata"]:
            print(f"   📊 Metadata: {log['metadata']}")
        
        print()


def export_logs_json(date=None, output_file=None):
    """Exporte les logs en JSON"""
    logs = get_server_logs(date)
    
    if not logs:
        print(f"📭 Aucun log à exporter")
        return
    
    if output_file is None:
        output_file = f"tests/reports/server_logs_{date or datetime.now().strftime('%Y-%m-%d')}.json"
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Logs exportés: {output_file}")
    print(f"📊 Total: {len(logs)} logs")


def show_stats(date=None):
    """Affiche les statistiques des logs"""
    logs = get_server_logs(date)
    
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
    
    print(f"\n{'='*80}")
    print(f"📊 STATISTIQUES - {date or datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*80}\n")
    
    print(f"Total logs: {len(logs)}\n")
    
    print("Par niveau:")
    for level, count in sorted(levels.items(), key=lambda x: x[1], reverse=True):
        print(f"  {level}: {count}")
    
    print(f"\nTop 10 sources:")
    for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {source}: {count}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Visualiseur de logs serveur")
    parser.add_argument("--date", type=str, help="Date des logs (YYYY-MM-DD)")
    parser.add_argument("--level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Filtrer par niveau")
    parser.add_argument("--search", type=str, help="Rechercher dans les logs")
    parser.add_argument("--last", type=int, help="Afficher les N derniers logs")
    parser.add_argument("--errors", action="store_true", help="Afficher seulement les erreurs")
    parser.add_argument("--stats", action="store_true", help="Afficher les statistiques")
    parser.add_argument("--export", type=str, help="Exporter en JSON vers fichier")
    
    args = parser.parse_args()
    
    # Stats
    if args.stats:
        show_stats(args.date)
    
    # Export
    elif args.export:
        export_logs_json(args.date, args.export)
    
    # Affichage
    else:
        level = "ERROR" if args.errors else args.level
        view_logs(args.date, level, args.search, args.last)

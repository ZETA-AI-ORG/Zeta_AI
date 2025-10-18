#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 SCRIPT CLI POUR CONSULTER LES LOGS JSON
Usage: python3 view_logs.py [command] [options]
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

from core.json_request_logger import get_json_request_logger, print_log_entry


def print_help():
    """Affiche l'aide"""
    print("""
📊 VIEW LOGS - Consultation des logs JSON

COMMANDES:
  stats [date]              Statistiques du jour
  errors [date]             Afficher les erreurs
  search <query> [date]     Rechercher dans les logs
  user <user_id> [date]     Logs d'un utilisateur
  all [date]                Tous les logs
  groq [date]               Erreurs Groq 403 spécifiquement
  last [n]                  Derniers N logs (défaut: 10)

EXEMPLES:
  python3 view_logs.py stats
  python3 view_logs.py errors 2025-10-14
  python3 view_logs.py search "403 Forbidden"
  python3 view_logs.py user test_prix_123
  python3 view_logs.py groq
  python3 view_logs.py last 20

DATE FORMAT: YYYY-MM-DD (défaut: aujourd'hui)
""")


def print_stats(logger_instance, date=None):
    """Affiche les statistiques"""
    stats = logger_instance.get_stats_for_date(date)
    
    print("\n" + "="*80)
    print(f"📊 STATISTIQUES - {stats['date']}")
    print("="*80)
    print(f"📨 Total requêtes: {stats['total_requests']}")
    print(f"❌ Total erreurs: {stats['total_errors']}")
    print(f"📉 Taux d'erreur: {stats['error_rate']*100:.2f}%")
    print(f"👥 Utilisateurs uniques: {stats['unique_users']}")
    print(f"🏢 Entreprises uniques: {stats['unique_companies']}")
    print(f"⏱️  Temps moyen: {stats['avg_response_time_ms']:.2f}ms")
    
    if stats['error_types']:
        print(f"\n🔴 TYPES D'ERREURS:")
        for error_type, count in stats['error_types'].items():
            print(f"  - {error_type}: {count}")
    
    print("="*80)


def print_errors(logger_instance, date=None):
    """Affiche les erreurs"""
    errors = logger_instance.get_errors_for_date(date)
    
    print(f"\n📊 {len(errors)} erreur(s) trouvée(s)\n")
    
    for error in errors:
        print_log_entry(error, verbose=True)


def print_groq_errors(logger_instance, date=None):
    """Affiche spécifiquement les erreurs Groq 403"""
    all_logs = logger_instance.get_logs_for_date(date)
    
    groq_errors = [
        log for log in all_logs
        if "403 Forbidden" in log.get("response", "") and
           "groq.com" in log.get("response", "")
    ]
    
    print(f"\n🔴 {len(groq_errors)} erreur(s) Groq 403 trouvée(s)\n")
    
    for error in groq_errors:
        timestamp = error.get("timestamp", "N/A")
        user_id = error.get("user_id", "N/A")
        message = error.get("message", "")
        
        print(f"{'='*80}")
        print(f"🕐 {timestamp}")
        print(f"👤 User: {user_id}")
        print(f"📤 Message: {message}")
        print(f"❌ Erreur: 403 Forbidden - Groq API")
        
        metadata = error.get("metadata", {})
        if metadata:
            print(f"\n📊 Metadata:")
            for key, value in metadata.items():
                print(f"  - {key}: {value}")
        
        print(f"{'='*80}\n")


def print_last_logs(logger_instance, n=10, date=None):
    """Affiche les N derniers logs"""
    all_logs = logger_instance.get_logs_for_date(date)
    last_logs = all_logs[-n:] if len(all_logs) > n else all_logs
    
    print(f"\n📊 {len(last_logs)} dernier(s) log(s)\n")
    
    for log in last_logs:
        print_log_entry(log)


def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command in ["help", "-h", "--help"]:
        print_help()
        sys.exit(0)
    
    logger_instance = get_json_request_logger()
    
    if command == "stats":
        date = sys.argv[2] if len(sys.argv) > 2 else None
        print_stats(logger_instance, date)
    
    elif command == "errors":
        date = sys.argv[2] if len(sys.argv) > 2 else None
        print_errors(logger_instance, date)
    
    elif command == "groq":
        date = sys.argv[2] if len(sys.argv) > 2 else None
        print_groq_errors(logger_instance, date)
    
    elif command == "search":
        if len(sys.argv) < 3:
            print("❌ Usage: python3 view_logs.py search <query> [date]")
            sys.exit(1)
        query = sys.argv[2]
        date = sys.argv[3] if len(sys.argv) > 3 else None
        results = logger_instance.search_logs(query, date)
        print(f"\n📊 {len(results)} résultat(s) trouvé(s)\n")
        for result in results:
            print_log_entry(result)
    
    elif command == "user":
        if len(sys.argv) < 3:
            print("❌ Usage: python3 view_logs.py user <user_id> [date]")
            sys.exit(1)
        user_id = sys.argv[2]
        date = sys.argv[3] if len(sys.argv) > 3 else None
        logs = logger_instance.get_logs_for_user(user_id, date)
        print(f"\n📊 {len(logs)} log(s) trouvé(s) pour {user_id}\n")
        for log in logs:
            print_log_entry(log)
    
    elif command == "all":
        date = sys.argv[2] if len(sys.argv) > 2 else None
        logs = logger_instance.get_logs_for_date(date)
        print(f"\n📊 {len(logs)} log(s) trouvé(s)\n")
        for log in logs:
            print_log_entry(log)
    
    elif command == "last":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        date = sys.argv[3] if len(sys.argv) > 3 else None
        print_last_logs(logger_instance, n, date)
    
    else:
        print(f"❌ Commande inconnue: {command}")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

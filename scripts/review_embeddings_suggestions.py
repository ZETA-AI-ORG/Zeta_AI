# -*- coding: utf-8 -*-
"""
DASHBOARD REVIEW EMBEDDINGS V6.5

Script de review hebdomadaire des suggestions embeddings.
Objectif : Identifier les patterns récurrents à promouvoir en V6/V5 keywords.

Usage:
    python scripts/review_embeddings_suggestions.py
    python scripts/review_embeddings_suggestions.py --approve "message exact"
    python scripts/review_embeddings_suggestions.py --reject "message exact"
"""

import json
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

LOG_FILE = Path("logs/embeddings_suggestions_v6_5.jsonl")


def load_suggestions():
    """Charge toutes les suggestions."""
    if not LOG_FILE.exists():
        return []
    
    suggestions = []
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                suggestions.append(json.loads(line))
    return suggestions


def analyze_suggestions():
    """Analyse et affiche le rapport des suggestions."""
    suggestions = load_suggestions()
    
    if not suggestions:
        print("\n✅ Aucune suggestion enregistrée")
        print("   Le Layer 3 Embeddings n'a pas encore capturé de cas.")
        return
    
    # Filtrer pending
    pending = [s for s in suggestions if s.get("status") == "pending_review"]
    approved = [s for s in suggestions if s.get("status") == "approved"]
    rejected = [s for s in suggestions if s.get("status") == "rejected"]
    
    print("\n" + "=" * 80)
    print(f"📊 RAPPORT EMBEDDINGS V6.5 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    print(f"\n📈 STATISTIQUES GLOBALES")
    print(f"   Total suggestions : {len(suggestions)}")
    print(f"   ⏳ Pending review  : {len(pending)}")
    print(f"   ✅ Approved        : {len(approved)}")
    print(f"   ❌ Rejected        : {len(rejected)}")
    
    if not pending:
        print("\n✅ Toutes les suggestions ont été reviewées !")
        return
    
    # Grouper par intent
    by_intent = defaultdict(list)
    for sugg in pending:
        by_intent[sugg["intent"]].append(sugg)
    
    print(f"\n" + "-" * 80)
    print(f"📋 SUGGESTIONS EN ATTENTE ({len(pending)} cas)")
    print("-" * 80)
    
    for intent, items in sorted(by_intent.items(), key=lambda x: -len(x[1])):
        print(f"\n🎯 {intent} ({len(items)} cas)")
        print("-" * 60)
        
        # Grouper par message (déduplication)
        messages = [item["message"] for item in items]
        freq = Counter(messages)
        
        for i, (msg, count) in enumerate(freq.most_common(10), 1):
            # Trouver similarité moyenne
            sims = [item["similarity"] for item in items if item["message"] == msg]
            avg_sim = sum(sims) / len(sims)
            
            # Prototype matché
            proto = next(
                item["prototype"] for item in items if item["message"] == msg
            )
            
            # Indicateur priorité
            priority = "🔴" if count >= 5 else "🟡" if count >= 2 else "⚪"
            
            print(f"  {priority} [{count:2d}x] {msg[:55]}")
            print(f"       sim={avg_sim:.3f} | proto: {proto[:45]}...")
    
    # Recommandations
    print("\n" + "=" * 80)
    print("💡 ACTIONS RECOMMANDÉES")
    print("=" * 80)
    
    high_freq = [(msg, cnt) for msg, cnt in Counter(
        s["message"] for s in pending
    ).items() if cnt >= 3]
    
    if high_freq:
        print("\n🔴 HAUTE PRIORITÉ (≥3 occurrences) - À ajouter en V6/V5 :")
        for msg, cnt in sorted(high_freq, key=lambda x: -x[1])[:5]:
            intent = next(s["intent"] for s in pending if s["message"] == msg)
            print(f"   • [{cnt}x] {intent}: \"{msg[:50]}...\"")
        
        print("\n   → Ajouter ces keywords dans core/setfit_intent_router.py")
        print("   → Section _deterministic_prefilter() V6 ou V5")
    
    print("\n📝 COMMANDES UTILES :")
    print("   python scripts/review_embeddings_suggestions.py --approve \"message\"")
    print("   python scripts/review_embeddings_suggestions.py --reject \"message\"")
    print("   python scripts/review_embeddings_suggestions.py --export pending.json")
    
    print("\n" + "=" * 80 + "\n")


def approve_suggestion(message: str):
    """Approuve une suggestion (à ajouter en V6/V5)."""
    from core.embeddings_v6_5 import SuggestionLoggerV65
    logger = SuggestionLoggerV65()
    
    if logger.mark_reviewed(message, "approved", "cli_review"):
        print(f"✅ Suggestion approuvée: \"{message[:50]}...\"")
        print("   → Penser à ajouter le keyword correspondant en V6/V5")
    else:
        print(f"❌ Suggestion non trouvée: \"{message[:50]}...\"")


def reject_suggestion(message: str):
    """Rejette une suggestion (faux positif)."""
    from core.embeddings_v6_5 import SuggestionLoggerV65
    logger = SuggestionLoggerV65()
    
    if logger.mark_reviewed(message, "rejected", "cli_review"):
        print(f"❌ Suggestion rejetée: \"{message[:50]}...\"")
    else:
        print(f"❌ Suggestion non trouvée: \"{message[:50]}...\"")


def export_pending(output_file: str):
    """Exporte les suggestions pending en JSON."""
    suggestions = load_suggestions()
    pending = [s for s in suggestions if s.get("status") == "pending_review"]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)
    
    print(f"✅ {len(pending)} suggestions exportées vers {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Review des suggestions Embeddings V6.5"
    )
    parser.add_argument(
        "--approve", 
        type=str, 
        help="Approuver une suggestion (message exact)"
    )
    parser.add_argument(
        "--reject", 
        type=str, 
        help="Rejeter une suggestion (message exact)"
    )
    parser.add_argument(
        "--export", 
        type=str, 
        help="Exporter les pending vers fichier JSON"
    )
    
    args = parser.parse_args()
    
    if args.approve:
        approve_suggestion(args.approve)
    elif args.reject:
        reject_suggestion(args.reject)
    elif args.export:
        export_pending(args.export)
    else:
        analyze_suggestions()


if __name__ == "__main__":
    main()

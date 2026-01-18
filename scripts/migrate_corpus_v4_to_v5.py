"""
Migration automatique Corpus V4 → V5
=====================================

Mappe les 780+ exemples V4 vers les 4 pôles V5 selon POLE_MAPPING_V4_TO_V5.

Usage:
    python scripts/migrate_corpus_v4_to_v5.py
"""

import sys
import json
from pathlib import Path
from collections import Counter

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from core.universal_corpus import (
    UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4,
    POLE_MAPPING_V4_TO_V5,
    INTENT_DEFINITIONS_V4
)

def migrate_corpus():
    """Migre automatiquement corpus V4 vers V5"""
    
    corpus_v5 = {
        "REASSURANCE": [],
        "SHOPPING": [],
        "ACQUISITION": [],
        "SAV_SUIVI": []
    }
    
    print("=" * 80)
    print("🔄 MIGRATION CORPUS V4 → V5")
    print("=" * 80)
    print()
    
    stats_by_intent = {}
    
    for intent_id, data in UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4.items():
        pole_v5 = POLE_MAPPING_V4_TO_V5.get(intent_id)
        
        if not pole_v5:
            print(f"⚠️  Intent {intent_id} non mappé, ignoré")
            continue
        
        label_v4 = data.get("label", f"INTENT_{intent_id}")
        exemples = data.get("exemples", [])
        
        print(f"  Intent {intent_id:2d} ({label_v4:30s}) → {pole_v5:15s} : {len(exemples):3d} exemples")
        
        corpus_v5[pole_v5].extend(exemples)
        stats_by_intent[intent_id] = {
            "label": label_v4,
            "pole": pole_v5,
            "count": len(exemples)
        }
    
    # Dédupliquer
    print("\n🔧 Déduplication...")
    for pole in corpus_v5:
        avant = len(corpus_v5[pole])
        corpus_v5[pole] = list(set(corpus_v5[pole]))
        apres = len(corpus_v5[pole])
        if avant > apres:
            print(f"  {pole:15s}: {avant} → {apres} ({avant-apres} doublons supprimés)")
        else:
            print(f"  {pole:15s}: {apres} exemples (pas de doublons)")
    
    # Stats finales
    print("\n" + "=" * 80)
    print("📊 CORPUS V5 FINAL")
    print("=" * 80)
    total = 0
    for pole in sorted(corpus_v5.keys()):
        exemples = corpus_v5[pole]
        print(f"  {pole:15s}: {len(exemples):3d} exemples")
        total += len(exemples)
    print(f"  {'TOTAL':15s}: {total:3d} exemples")
    print("=" * 80)
    
    # Sauvegarder JSON
    output_file = project_root / "core" / "corpus_v5_migrated.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(corpus_v5, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Corpus sauvegardé : {output_file}")
    
    # Sauvegarder stats
    stats_file = project_root / "core" / "corpus_v5_migration_stats.json"
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump({
            "total_exemples": total,
            "by_pole": {pole: len(exemples) for pole, exemples in corpus_v5.items()},
            "by_intent_v4": stats_by_intent
        }, f, indent=2, ensure_ascii=False)
    
    print(f"📊 Stats sauvegardées : {stats_file}")
    
    print("\n🎯 Prochaines étapes :")
    print("  1. Vérifier core/corpus_v5_migrated.json")
    print("  2. Réentraîner : python scripts/train_setfit_v5.py")
    print("  3. Tester : python scripts/test_v5_quick.py")
    
    return corpus_v5

if __name__ == "__main__":
    corpus_v5 = migrate_corpus()

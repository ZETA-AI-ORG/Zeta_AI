"""
Migration V4→V5 avec corrections manuelles
==========================================

Corrige les incohérences du mapping automatique avant migration.

Usage:
    python scripts/migrate_corpus_v4_to_v5_fixed.py
"""

import sys
import json
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from core.corpus_v5_migration import (
    UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4,
    POLE_MAPPING_V4_TO_V5
)

# ==============================================================================
# CORRECTIONS MANUELLES (exemples mal placés dans V4)
# ==============================================================================

MANUAL_CORRECTIONS = {
    # Intent 2 (INFO_GENERALE → REASSURANCE) : retirer les exemples ACQUISITION
    2: {
        "remove": [
            "Comment on fait pour commander ?",
            "Ça fonctionne comment ?",
        ],
        "move_to_pole": None  # Ces exemples seront ajoutés manuellement à ACQUISITION
    },
    
    # Intent 3 (PRODUIT_GLOBAL → SHOPPING) : retirer les exemples ACQUISITION
    3: {
        "remove": [
            "Je voudrais acheter 5 paquets",
            "Je veux 6paquets de couche culotte xxxl",
            "Je veux 6 paquets de couche culotte xxxl",
        ],
        "move_to_pole": "ACQUISITION"
    },
}

# Exemples à ajouter manuellement à ACQUISITION
MANUAL_ADDITIONS = {
    "ACQUISITION": [
        "Comment on fait pour commander ?",
        "Ça fonctionne comment ?",
        "Je voudrais acheter 5 paquets",
        "Je veux 6 paquets de couche culotte xxxl",
    ]
}

def migrate_corpus_with_fixes():
    """Migre le corpus V4→V5 avec corrections manuelles"""
    
    corpus_v5 = {
        "REASSURANCE": [],
        "SHOPPING": [],
        "ACQUISITION": [],
        "SAV_SUIVI": []
    }
    
    print("=" * 80)
    print("🔄 MIGRATION CORPUS V4 → V5 (AVEC CORRECTIONS)")
    print("=" * 80)
    print()
    
    # Étape 1 : Migration automatique avec corrections
    for intent_id, data in UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4.items():
        pole_v5 = POLE_MAPPING_V4_TO_V5[intent_id]
        label_v4 = data["label"]
        exemples = data.get("exemples", [])
        
        # Appliquer corrections manuelles
        if intent_id in MANUAL_CORRECTIONS:
            corrections = MANUAL_CORRECTIONS[intent_id]
            exemples_to_remove = corrections["remove"]
            exemples = [ex for ex in exemples if ex not in exemples_to_remove]
            
            removed_count = len(corrections["remove"])
            print(f"  ⚠️  Intent {intent_id} ({label_v4}): {removed_count} exemples retirés")
        
        print(f"  Intent {intent_id:2d} ({label_v4:30s}) → {pole_v5:15s} : {len(exemples):3d} exemples")
        corpus_v5[pole_v5].extend(exemples)
    
    # Étape 2 : Ajouter corrections manuelles
    print("\n🔧 Ajout des corrections manuelles...")
    for pole, additions in MANUAL_ADDITIONS.items():
        corpus_v5[pole].extend(additions)
        print(f"  {pole:15s}: +{len(additions)} exemples corrigés")
    
    # Étape 3 : Déduplication
    print("\n🔧 Déduplication...")
    for pole in corpus_v5:
        avant = len(corpus_v5[pole])
        corpus_v5[pole] = list(set(corpus_v5[pole]))
        apres = len(corpus_v5[pole])
        if avant > apres:
            print(f"  {pole:15s}: {avant} → {apres} ({avant-apres} doublons supprimés)")
        else:
            print(f"  {pole:15s}: {apres} exemples (pas de doublons)")
    
    # Étape 4 : Stats finales
    print("\n" + "=" * 80)
    print("📊 CORPUS V5 FINAL (CORRIGÉ)")
    print("=" * 80)
    total = 0
    for pole in sorted(corpus_v5.keys()):
        exemples = corpus_v5[pole]
        print(f"  {pole:15s}: {len(exemples):3d} exemples")
        total += len(exemples)
    print(f"  {'TOTAL':15s}: {total:3d} exemples")
    print("=" * 80)
    
    # Étape 5 : Validation sémantique
    print("\n🔍 Validation sémantique...")
    issues = validate_semantic_coherence(corpus_v5)
    
    if not issues:
        print("✅ Aucune incohérence détectée")
    else:
        print(f"⚠️  {len(issues)} incohérences détectées :")
        for issue in issues[:10]:  # Top 10
            print(f"  - {issue}")
    
    # Étape 6 : Export
    output_file = project_root / "core" / "corpus_v5_migrated_fixed.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(corpus_v5, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Corpus corrigé sauvegardé : {output_file}")
    
    # Stats
    stats_file = project_root / "core" / "corpus_v5_migration_stats_fixed.json"
    stats = {
        "total_exemples": total,
        "by_pole": {pole: len(exemples) for pole, exemples in corpus_v5.items()},
        "corrections_applied": len(MANUAL_CORRECTIONS),
        "manual_additions": sum(len(v) for v in MANUAL_ADDITIONS.values()),
        "semantic_issues": len(issues),
    }
    
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    print(f"📊 Stats sauvegardées : {stats_file}")
    
    print("\n🎯 Prochaines étapes :")
    print("  1. Vérifier core/corpus_v5_migrated_fixed.json")
    print("  2. Modifier train_setfit_v5.py pour charger corpus_v5_migrated_fixed.json")
    print("  3. Réentraîner : python scripts/train_setfit_v5.py")
    print("  4. Tester : python scripts/test_v5_quick.py")
    
    return corpus_v5


def validate_semantic_coherence(corpus_v5):
    """Valide la cohérence sémantique du corpus"""
    
    issues = []
    
    # Mots-clés d'acquisition
    acquisition_kw = ["commander", "commande", "acheter", "achat", "prendre", "réserve", "je veux", "mettez-moi"]
    
    # Mots-clés de shopping
    shopping_kw = ["catalogue", "liste", "produits", "vous avez quoi", "montrez-moi", "menu"]
    
    # Mots-clés SAV
    sav_kw = ["ma commande", "mon colis", "où est", "tracking", "livreur", "pas reçu", "retard", "problème"]
    
    # Vérifier REASSURANCE
    for ex in corpus_v5["REASSURANCE"]:
        ex_lower = ex.lower()
        if any(kw in ex_lower for kw in acquisition_kw):
            issues.append(f"REASSURANCE → ACQUISITION : '{ex}'")
        elif any(kw in ex_lower for kw in shopping_kw):
            issues.append(f"REASSURANCE → SHOPPING : '{ex}'")
        elif any(kw in ex_lower for kw in sav_kw):
            issues.append(f"REASSURANCE → SAV_SUIVI : '{ex}'")
    
    # Vérifier SHOPPING
    for ex in corpus_v5["SHOPPING"]:
        ex_lower = ex.lower()
        if any(kw in ex_lower for kw in acquisition_kw):
            issues.append(f"SHOPPING → ACQUISITION : '{ex}'")
    
    # Vérifier ACQUISITION
    for ex in corpus_v5["ACQUISITION"]:
        ex_lower = ex.lower()
        if any(kw in ex_lower for kw in sav_kw):
            issues.append(f"ACQUISITION → SAV_SUIVI : '{ex}'")
    
    return issues


if __name__ == "__main__":
    corpus_v5 = migrate_corpus_with_fixes()

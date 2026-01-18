"""
Audit du corpus V5 migré
=========================

Vérifie la cohérence du mapping V4→V5 et identifie les exemples mal classés.

Usage:
    python scripts/audit_corpus_v5.py
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# Règles de détection d'incohérences
ACQUISITION_KEYWORDS = [
    "commander", "commande", "acheter", "achat", "prendre", "réserver", "reserver",
    "je veux", "j'en veux", "envoie-moi", "livrez-moi", "mettez-moi",
    "je prends", "je commande", "je valide", "passer commande"
]

SHOPPING_KEYWORDS = [
    "catalogue", "produits", "articles", "vous avez quoi", "qu'est-ce que vous avez",
    "montrez-moi", "faites-moi découvrir", "menu", "liste", "gamme",
    "vous vendez quoi", "types de produits", "catégories"
]

SAV_KEYWORDS = [
    "ma commande", "mon colis", "où est", "suivi", "tracking", "livreur",
    "pas reçu", "pas encore reçu", "retard", "problème", "abîmé", "cassé",
    "défectueux", "réclamation", "remboursement", "retourner", "annuler"
]

def audit_corpus():
    """Audit le corpus V5 migré"""
    
    corpus_path = project_root / "core" / "corpus_v5_migrated.json"
    
    if not corpus_path.exists():
        print(f"❌ Corpus non trouvé : {corpus_path}")
        return
    
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)
    
    print("=" * 80)
    print("🔍 AUDIT CORPUS V5 MIGRÉ")
    print("=" * 80)
    print()
    
    issues = defaultdict(list)
    
    for pole, examples in corpus.items():
        print(f"\n📊 {pole} ({len(examples)} exemples)")
        print("-" * 80)
        
        for i, example in enumerate(examples, 1):
            ex_lower = example.lower()
            
            # Vérifier incohérences
            if pole == "REASSURANCE":
                # Exemples qui devraient être ACQUISITION
                if any(kw in ex_lower for kw in ACQUISITION_KEYWORDS):
                    issues[pole].append((i, example, "→ ACQUISITION"))
                    print(f"  ⚠️  #{i:3d}: '{example[:60]}...' → devrait être ACQUISITION")
                
                # Exemples qui devraient être SHOPPING
                elif any(kw in ex_lower for kw in SHOPPING_KEYWORDS):
                    issues[pole].append((i, example, "→ SHOPPING"))
                    print(f"  ⚠️  #{i:3d}: '{example[:60]}...' → devrait être SHOPPING")
                
                # Exemples qui devraient être SAV_SUIVI
                elif any(kw in ex_lower for kw in SAV_KEYWORDS):
                    issues[pole].append((i, example, "→ SAV_SUIVI"))
                    print(f"  ⚠️  #{i:3d}: '{example[:60]}...' → devrait être SAV_SUIVI")
            
            elif pole == "SHOPPING":
                # Exemples qui devraient être ACQUISITION
                if any(kw in ex_lower for kw in ACQUISITION_KEYWORDS):
                    issues[pole].append((i, example, "→ ACQUISITION"))
                    print(f"  ⚠️  #{i:3d}: '{example[:60]}...' → devrait être ACQUISITION")
            
            elif pole == "ACQUISITION":
                # Exemples qui devraient être SAV_SUIVI
                if any(kw in ex_lower for kw in SAV_KEYWORDS):
                    issues[pole].append((i, example, "→ SAV_SUIVI"))
                    print(f"  ⚠️  #{i:3d}: '{example[:60]}...' → devrait être SAV_SUIVI")
    
    # Résumé
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ AUDIT")
    print("=" * 80)
    
    total_issues = sum(len(v) for v in issues.values())
    
    if total_issues == 0:
        print("✅ Aucune incohérence détectée !")
    else:
        print(f"⚠️  {total_issues} incohérences détectées :")
        for pole, pole_issues in issues.items():
            if pole_issues:
                print(f"\n  {pole}: {len(pole_issues)} problèmes")
                for i, example, suggestion in pole_issues[:5]:  # Top 5
                    print(f"    - '{example[:50]}...' {suggestion}")
    
    print("\n🎯 Recommandation :")
    if total_issues > 20:
        print("  ❌ TROP D'INCOHÉRENCES → Revoir le mapping V4→V5")
        print("  → Vérifier POLE_MAPPING_V4_TO_V5 dans universal_corpus.py")
    elif total_issues > 0:
        print("  ⚠️  Quelques incohérences → Correction manuelle recommandée")
        print("  → Éditer corpus_v5_migrated.json")
    else:
        print("  ✅ Corpus cohérent → Prêt pour entraînement")
    
    return issues

if __name__ == "__main__":
    issues = audit_corpus()

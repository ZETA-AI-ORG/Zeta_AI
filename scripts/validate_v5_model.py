"""
Script de validation du modèle SetFit V5
========================================

Ce script charge les cas de test de production (V4), convertit les résultats attendus
en pôles V5, et évalue la précision du routeur V5.

Usage:
    python scripts/validate_v5_model.py
"""

import sys
import asyncio
import logging
from pathlib import Path
from collections import defaultdict, Counter

# Setup paths
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from core.setfit_intent_router import route_botlive_intent, _load_setfit_model
from core.universal_corpus import POLE_MAPPING_V4_TO_V5
from tests.production_test_cases import PRODUCTION_TEST_CASES

# Configuration logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("validate_v5")

async def run_validation():
    print("=" * 80)
    print("🚀 VALIDATION MODÈLE SETFIT V5")
    print("=" * 80)

    # 1. Charger le modèle
    print("\n📦 Chargement du modèle...")
    try:
        model = _load_setfit_model()
        print(f"✅ Modèle chargé: {getattr(model, 'labels', 'Unknown labels')}")
    except Exception as e:
        print(f"❌ Erreur chargement modèle: {e}")
        return

    # 2. Préparer les stats
    stats = {
        "total": 0,
        "correct": 0,
        "errors": 0,
        "by_pole": defaultdict(lambda: {"total": 0, "correct": 0}),
        "confusions": Counter()
    }

    results = []

    print(f"\n🧪 Exécution des {len(PRODUCTION_TEST_CASES)} tests...\n")
    
    # Header
    print(f"{'QUESTION':<50} | {'EXPECTED (V5)':<15} | {'PREDICTED':<15} | {'CONF':<5} | {'RESULT'}")
    print("-" * 100)

    for question, v4_label, v4_id in PRODUCTION_TEST_CASES:
        # Mapper V4 ID -> V5 Pole
        expected_pole = POLE_MAPPING_V4_TO_V5.get(v4_id)
        
        # Cas spéciaux non mappés ou ignorés
        if not expected_pole:
            continue

        stats["total"] += 1
        stats["by_pole"][expected_pole]["total"] += 1

        # Router
        try:
            result = await route_botlive_intent(
                company_id="test_validation",
                user_id="validator",
                message=question,
                conversation_history="",
                state_compact={}
            )
            
            predicted_pole = result.intent
            confidence = result.confidence
            
            is_correct = (predicted_pole == expected_pole)
            
            # Special Override Check: Localisation -> REASSURANCE
            # Si c'est une question de localisation (ID 2 généralement), on attend REASSURANCE
            # Le mapping le fait déjà (2 -> REASSURANCE).
            
            if is_correct:
                stats["correct"] += 1
                stats["by_pole"][expected_pole]["correct"] += 1
                marker = "✅"
            else:
                stats["errors"] += 1
                stats["confusions"][(expected_pole, predicted_pole)] += 1
                marker = "❌"

            # Affichage ligne (tronqué)
            q_display = (question[:47] + "...") if len(question) > 47 else question
            print(f"{q_display:<50} | {expected_pole:<15} | {predicted_pole:<15} | {confidence:.2f}  | {marker}")
            
        except Exception as e:
            print(f"❌ Crash sur '{question}': {e}")

    # 3. Résumé
    accuracy = (stats["correct"] / stats["total"]) * 100 if stats["total"] > 0 else 0
    
    print("\n" + "=" * 80)
    print(f"📊 RÉSULTATS GLOBAUX: {accuracy:.2f}% ({stats['correct']}/{stats['total']})")
    print("=" * 80)

    print("\n📈 Par Pôle:")
    for pole in sorted(stats["by_pole"].keys()):
        data = stats["by_pole"][pole]
        acc = (data["correct"] / data["total"] * 100) if data["total"] > 0 else 0
        print(f"  - {pole:<15}: {acc:6.2f}% ({data['correct']}/{data['total']})")

    if stats["confusions"]:
        print("\n⚠️ Confusions fréquentes (Attendus -> Prédits):")
        for (exp, pred), count in stats["confusions"].most_common(5):
            print(f"  - {exp} -> {pred}: {count} fois")

if __name__ == "__main__":
    asyncio.run(run_validation())

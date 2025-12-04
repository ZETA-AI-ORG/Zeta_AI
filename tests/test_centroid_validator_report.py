import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.centroid_router import CentroidRouter
from core.intent_validator import IntentValidator


logging.basicConfig(level=logging.INFO)


def test_centroid_accuracy():
    """Bench simple sur le corpus complet via IntentValidator.

    Ce test imprime les métriques et vérifie que l'accuracy globale
    dépasse un seuil minimal (0.90 par défaut).
    """
    router = CentroidRouter()
    validator = IntentValidator(router)

    metrics = validator.validate_on_corpus()

    overall = metrics["overall_accuracy"]
    total = metrics["total_samples"]
    correct = metrics["correct_predictions"]

    print(f"\n📊 Accuracy globale: {overall:.2%}")
    print(f"✅ Prédictions correctes: {correct}/{total}")

    for intent_id, stats in sorted(metrics["per_intent_metrics"].items()):
        print(
            f"  Intent {intent_id}: {stats['intent_name']} → "
            f"{stats['accuracy']:.2%} "
            f"({stats['correct_predictions']}/{stats['total_samples']})"
        )

    # Seuil minimal pour considérer le router prêt
    assert overall > 0.90, "Accuracy globale trop basse pour le centroid router"

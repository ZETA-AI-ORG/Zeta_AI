"""
Validation du système de routing par centroid sur le corpus complet.
"""

from collections import defaultdict
from typing import Dict, List

from core.centroid_router import CentroidRouter


class IntentValidator:
    """Valide les performances du CentroidRouter sur le corpus v2.

    Utilise le corpus chargé dans le router pour calculer:
    - accuracy globale
    - accuracy par intent
    - liste d'erreurs à haute confiance
    """

    def __init__(self, router: CentroidRouter) -> None:
        self.router = router
        self.corpus = router.corpus

    def validate_on_corpus(self) -> Dict:
        """Valide le router sur l'ensemble des variations du corpus.

        Returns:
            dict avec accuracy globale et métriques par intent.
        """
        total = 0
        correct = 0
        per_intent_stats: Dict[int, Dict[str, int]] = defaultdict(
            lambda: {"total": 0, "correct": 0}
        )

        intents = self.corpus.get("intents", []) or []
        for intent_data in intents:
            intent_id = int(intent_data["id"])

            all_variations: List[str] = (
                intent_data.get("variations_naturelles", [])
                + intent_data.get("variations_bruitees", [])
                + intent_data.get("variations_nouchi", [])
            )

            for variation in all_variations:
                if not isinstance(variation, str) or not variation.strip():
                    continue

                result = self.router.route(variation)
                predicted_id = int(result["intent_id"])

                total += 1
                per_intent_stats[intent_id]["total"] += 1

                if predicted_id == intent_id:
                    correct += 1
                    per_intent_stats[intent_id]["correct"] += 1

        overall_accuracy = correct / total if total > 0 else 0.0

        per_intent_metrics: Dict[int, Dict[str, object]] = {}
        for intent_data in intents:
            intent_id = int(intent_data["id"])
            stats = per_intent_stats[intent_id]
            total_samples = stats["total"]
            correct_predictions = stats["correct"]
            accuracy = (
                correct_predictions / total_samples if total_samples > 0 else 0.0
            )

            per_intent_metrics[intent_id] = {
                "intent_name": str(intent_data["name"]),
                "accuracy": float(accuracy),
                "total_samples": int(total_samples),
                "correct_predictions": int(correct_predictions),
            }

        return {
            "overall_accuracy": float(overall_accuracy),
            "total_samples": int(total),
            "correct_predictions": int(correct),
            "per_intent_metrics": per_intent_metrics,
        }

    def analyze_errors(self, top_n: int = 10) -> List[Dict]:
        """Retourne les erreurs de routing les plus graves (haute confiance).

        Classe les erreurs par confiance décroissante et renvoie les top_n.
        """
        errors: List[Dict] = []

        intents = self.corpus.get("intents", []) or []
        for intent_data in intents:
            true_id = int(intent_data["id"])
            true_name = str(intent_data["name"])

            all_variations: List[str] = (
                intent_data.get("variations_naturelles", [])
                + intent_data.get("variations_bruitees", [])
                + intent_data.get("variations_nouchi", [])
            )

            for variation in all_variations:
                if not isinstance(variation, str) or not variation.strip():
                    continue

                result = self.router.route(variation, apply_boost=True)
                predicted_id = int(result["intent_id"])

                if predicted_id != true_id:
                    errors.append(
                        {
                            "message": variation,
                            "true_intent": true_name,
                            "predicted_intent": str(result["intent_name"]),
                            "confidence": float(result["confidence"]),
                            "top_k": result.get("top_k_intents", []),
                        }
                    )

        errors.sort(key=lambda e: e["confidence"], reverse=True)
        return errors[:top_n]

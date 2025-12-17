import asyncio
import os
import sys
from typing import Any, Dict

# Ensure project root on sys.path to allow 'core' imports when running directly
_THIS_DIR = os.path.dirname(__file__)
_ROOT_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

# Activer le router embeddings Botlive
os.environ.setdefault("BOTLIVE_ROUTER_EMBEDDINGS_ENABLED", "true")
os.environ.setdefault("BOTLIVE_V18_ENABLED", "false")

from core.botlive_intent_router import route_botlive_intent
from tests.production_test_cases import PRODUCTION_TEST_CASES


TEST_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"
TEST_USER_ID = "botlive_production_readiness"

# Mapping entre les labels "métiers" de ton plan (GREETING, PRICE, ...) 
# et les intents internes du router Botlive (SALUT, INFO_GENERALE, ...).
EXPECTED_TO_ALLOWED_BOTLIVE = {
    "GREETING": {"SALUT"},
    "INFO_GENERAL": {"INFO_GENERALE"},
    "PRODUCT_INFO": {"PRODUIT_GLOBAL"},
    "PRICE": {"PRIX_PROMO"},
    "STOCK": {"PRODUIT_GLOBAL"},
    "ORDER_CREATE": {"ACHAT_COMMANDE"},
    # Modif/annulation commande : on accepte soit ACHAT_COMMANDE soit PROBLEME
    "ORDER_MODIFY": {"COMMANDE_EXISTANTE", "PROBLEME"},
    "PAYMENT": {"PAIEMENT"},
    "DELIVERY_INFO": {"LIVRAISON"},
    # Modif adresse/date : peut être capté par LIVRAISON ou PROBLEME
    "DELIVERY_MODIFY": {"LIVRAISON", "PROBLEME"},
    # Suivi / retard : SUIVI ou PROBLEME sont tous les deux acceptables
    "TRACKING": {"COMMANDE_EXISTANTE", "PROBLEME"},
}

# Mapping inverse pour afficher des labels métier lisibles dans le rapport
BOTLIVE_TO_HIGHLEVEL = {
    "SALUT": "GREETING",
    "INFO_GENERALE": "INFO_GENERAL",
    "CLARIFICATION": "CLARIFICATION",
    "PRODUIT_GLOBAL": "PRODUCT_INFO",
    "PRIX_PROMO": "PRICE",
    "ACHAT_COMMANDE": "ORDER_CREATE",
    "LIVRAISON": "DELIVERY_INFO",
    "PAIEMENT": "PAYMENT",
    "COMMANDE_EXISTANTE": "TRACKING",
    # PROBLEME peut couvrir plainte / SAV sur commande ou livraison
    "PROBLEME": "TRACKING",
}


PRODUCTION_CRITERIA = {
    "accuracy_global": 85.0,      # Minimum 85% sur 120 cas
    "ambiguity_rate": 10.0,       # Maximum 10% ambigus
    "low_confidence_rate": 15.0,  # Maximum 15% conf < 0.60
    "min_intent_accuracy": 75.0,  # Chaque intent 3 75%
}


async def evaluate_production_readiness() -> Dict[str, Any]:
    """Teste le router Botlive sur les 120 cas et retourne les stats."""

    results: Dict[str, Any] = {
        "total": len(PRODUCTION_TEST_CASES),
        "correct": 0,
        "errors": [],
        "by_intent": {},
        "ambiguous": 0,
        "low_confidence": 0,
    }

    conversation_history = ""
    base_state = {
        "photo_collected": False,
        "paiement_collected": False,
        "zone_collected": False,
        "tel_collected": False,
        "tel_valide": False,
        "collected_count": 0,
        "is_complete": False,
    }

    for i, (question, expected_label, expected_id) in enumerate(PRODUCTION_TEST_CASES, 1):
        routing = await route_botlive_intent(
            company_id=TEST_COMPANY_ID,
            user_id=TEST_USER_ID,
            message=question,
            conversation_history=conversation_history,
            state_compact=base_state,
        )

        predicted_internal = routing.intent
        confidence = float(routing.confidence)
        predicted_label = BOTLIVE_TO_HIGHLEVEL.get(predicted_internal, predicted_internal)

        allowed_internal = EXPECTED_TO_ALLOWED_BOTLIVE.get(expected_label, set())
        is_correct = predicted_internal in allowed_internal

        if is_correct:
            results["correct"] += 1
        else:
            results["errors"].append(
                {
                    "question": question,
                    "expected": expected_label,
                    "predicted": predicted_label,
                    "predicted_internal": predicted_internal,
                    "confidence": confidence,
                }
            )

        # Stats par intent (label métier attendu)
        by_intent = results["by_intent"].setdefault(
            expected_label,
            {"total": 0, "correct": 0},
        )
        by_intent["total"] += 1
        if is_correct:
            by_intent["correct"] += 1

        # Ambigu : on considère CLARIFICATION comme cas "ambigu" / indécis
        is_ambiguous = predicted_internal == "CLARIFICATION"
        if is_ambiguous:
            results["ambiguous"] += 1

        # Confiance faible
        if confidence < 0.60:
            results["low_confidence"] += 1

        # Progression
        if i % 10 == 0:
            print(f"Progress: {i}/{results['total']} ({i/results['total']*100:.1f}%)")

    # Calculs globaux
    results["accuracy"] = results["correct"] / results["total"] * 100.0
    results["ambiguous_rate"] = results["ambiguous"] / results["total"] * 100.0
    results["low_confidence_rate"] = results["low_confidence"] / results["total"] * 100.0

    for intent, stats in results["by_intent"].items():
        stats["accuracy"] = stats["correct"] / stats["total"] * 100.0

    return results


def print_report(results: Dict[str, Any]) -> None:
    """Affiche un rapport détaillé sur la readiness production."""

    print("\n" + "=" * 70)
    print("📊 RAPPORT D'ÉVALUATION PRODUCTION (Botlive Router)")
    print("=" * 70)

    print(f"\n🎯 ACCURACY GLOBALE : {results['accuracy']:.2f}%")
    print(f"   ✅ Correct : {results['correct']}/{results['total']}")
    print(f"   ❌ Erreurs : {len(results['errors'])}/{results['total']}")

    print(f"\n⚠️  AMBIGUÏTÉ (CLARIFICATION) : {results['ambiguous_rate']:.2f}%")
    print(f"   ({results['ambiguous']}/{results['total']} messages)")

    print(f"\n📉 CONFIANCE FAIBLE (<0.60) : {results['low_confidence_rate']:.2f}%")
    print(f"   ({results['low_confidence']}/{results['total']} messages)")

    print(f"\n📈 ACCURACY PAR INTENT MÉTIER :")
    print("-" * 70)
    for intent, stats in sorted(results["by_intent"].items()):
        acc = stats["accuracy"]
        if acc >= 85.0:
            status = "✅"
        elif acc >= 75.0:
            status = "⚠️"
        else:
            status = "❌"
        print(f"{status} {intent:20s} : {acc:5.1f}% ({stats['correct']}/{stats['total']})")

    if results["errors"]:
        print(f"\n❌ ERREURS DÉTAILLÉES (Top 10) :")
        print("-" * 70)
        for i, error in enumerate(results["errors"][:10], 1):
            print(f"{i}. Question : {error['question']}")
            print(f"   Attendu  : {error['expected']}")
            print(f"   Prédit   : {error['predicted']} (interne={error['predicted_internal']}, conf={error['confidence']:.2f})")
            print()

    print("\n" + "=" * 70)
    print("🚦 DÉCISION PRODUCTION")
    print("=" * 70)

    accuracy_ok = results["accuracy"] >= PRODUCTION_CRITERIA["accuracy_global"]
    ambiguous_ok = results["ambiguous_rate"] <= PRODUCTION_CRITERIA["ambiguity_rate"]
    confidence_ok = results["low_confidence_rate"] <= PRODUCTION_CRITERIA["low_confidence_rate"]

    all_intents_ok = all(
        stats["accuracy"] >= PRODUCTION_CRITERIA["min_intent_accuracy"]
        for stats in results["by_intent"].values()
    )

    ready = accuracy_ok and ambiguous_ok and confidence_ok and all_intents_ok

    print(f"\n{'✅' if accuracy_ok else '❌'} Accuracy globale ≥ {PRODUCTION_CRITERIA['accuracy_global']:.1f}% : {results['accuracy']:.1f}%")
    print(f"{'✅' if ambiguous_ok else '❌'} Taux ambiguïté ≤ {PRODUCTION_CRITERIA['ambiguity_rate']:.1f}% : {results['ambiguous_rate']:.1f}%")
    print(f"{'✅' if confidence_ok else '❌'} Confiance faible ≤ {PRODUCTION_CRITERIA['low_confidence_rate']:.1f}% : {results['low_confidence_rate']:.1f}%")
    print(f"{'✅' if all_intents_ok else '❌'} Tous intents ≥ {PRODUCTION_CRITERIA['min_intent_accuracy']:.1f}%")

    if ready:
        print("\n🎉 ✅ SYSTÈME PRÊT POUR PRODUCTION !")
    else:
        print("\n⚠️  ❌ SYSTÈME PAS ENCORE PRÊT")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    async def _main() -> None:
        results = await evaluate_production_readiness()
        print_report(results)

    asyncio.run(_main())

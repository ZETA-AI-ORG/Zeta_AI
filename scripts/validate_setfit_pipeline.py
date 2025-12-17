import asyncio
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.production_pipeline import ProductionPipeline
from core.universal_corpus import INTENT_DEFINITIONS

test_cases = [
    # (message, intent attendu)
    ("Je veux commander", "ACHAT_COMMANDE"),
    ("C'est combien ?", "PRIX_PROMO"),
    ("Vous livrez où ?", "LIVRAISON"),
    ("Bonjour", "SALUT"),
    ("Je veux payer par Orange Money", "PAIEMENT"),
    ("Où est ma commande ?", "SUIVI"),
    ("Produit abîmé, je veux un remboursement", "PROBLEME"),
    ("Merci beaucoup", "SALUT"),
    ("Quels sont vos horaires ?", "INFO_GENERALE"),
    ("Avez-vous ce produit en stock ?", "RECHERCHE_PRODUIT"),
]

async def main():
    pipeline = ProductionPipeline()
    total = len(test_cases)
    correct = 0
    for msg, expected_intent in test_cases:
        req = {
            "company_id": "TEST",
            "user_id": "TESTUSER",
            "message": msg,
            "conversation_history": "",
            "state_compact": {},
            "hyde_pre_enabled": None,
        }
        res = await pipeline.route_message(**req)
        got = res["result"].intent.upper()
        ok = got == expected_intent.upper()
        print(f"Entrée: '{msg}' | Attendu: {expected_intent} | Obtenu: {got} | {'✅' if ok else '❌'}")
        if ok:
            correct += 1
    taux = correct / total * 100
    print(f"\nPrécision: {correct}/{total} = {taux:.1f}%")
    if taux >= 95:
        print("🎉 Objectif atteint (≥95%)")
    else:
        print("❌ Objectif NON atteint")

if __name__ == "__main__":
    asyncio.run(main())

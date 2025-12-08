import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.centroid_router import CentroidRouter

def main():

    router = CentroidRouter(use_cache=True)

    # Chaque entrée: expected = id d'intent attendu, text = exemple utilisateur
    # On couvre les 12 intents, avec plus d'exemples pour 9 (livraison) et 11 (suivi)
    tests = [
        # 1 - Salut / Politesse
        {"expected": 1, "text": "Bonjour"},
        {"expected": 1, "text": "Salut, ça va ?"},

        # 2 - Demande d'information générale / Localisation
        {"expected": 2, "text": "Vous êtes situés où exactement ?"},
        {"expected": 2, "text": "Je veux votre adresse exacte"},

        # 3 - Compréhension / Clarification
        {"expected": 3, "text": "Je n'ai pas compris"},

        # 4 - Demande catalogue / liste produits
        {"expected": 4, "text": "Je veux voir vos produits disponibles"},

        # 5 - Recherche produit précis
        {"expected": 5, "text": "Je cherche des couches taille M"},

        # 6 - Question prix / promo
        {"expected": 6, "text": "C'est combien ce produit ?"},

        # 7 - Disponibilité / stock
        {"expected": 7, "text": "Ce produit est-il encore disponible ?"},

        # 8 - Demande de commande
        {"expected": 8, "text": "Je veux passer une commande"},
        {"expected": 8, "text": "Je veux annuler ma commande"},

        # 9 - Informations sur la livraison (frais / zones / délais)
        {"expected": 9, "text": "Je veux des infos sur la livraison à Koumassi"},
        {"expected": 9, "text": "La livraison à Yopougon c'est combien ?"},
        {"expected": 9, "text": "Quels sont les frais de livraison ?"},
        {"expected": 9, "text": "Vous livrez à l'intérieur du pays ?"},

        # 10 - Moyens de paiement / Dépôt / Transaction
        {"expected": 10, "text": "Comment puis-je payer ?"},
        {"expected": 10, "text": "Puis-je payer par Wave ?"},

        # 11 - Suivi de commande / livraison
        {"expected": 11, "text": "Je n'ai pas encore reçu ma commande"},
        {"expected": 11, "text": "Ma commande est où maintenant ?"},
        {"expected": 11, "text": "Je veux suivre ma commande en cours"},
        {"expected": 11, "text": "Je veux savoir si ma commande est partie"},

        # 12 - Problème / Réclamation
        {"expected": 12, "text": "Je veux faire une réclamation sur ma commande"},
        {"expected": 12, "text": "Il y a un problème avec ce que j'ai reçu"},
    ]

    print("Test du CentroidRouter (embeddings + boosts).\n")

    for case in tests:
        txt = case["text"]
        expected = int(case["expected"])
        res = router.route(txt, top_k=3)
        pred_id = int(res.get("intent_id"))
        pred_name = res.get("intent_name")
        exp_centroid = router.centroids.get(expected)
        exp_name = exp_centroid.intent_name if exp_centroid is not None else "?"
        status = "OK" if pred_id == expected else "MISMATCH"

        print("====")
        print("Texte   :", txt)
        print(f"Attendu : {expected} ({exp_name})")
        print(f"Prédit  : {pred_id} ({pred_name})  -> {status}")
        print("Conf    :", f"{res.get('confidence', 0):.3f}")
        print("TopK    :")
        for it in res.get("top_k_intents") or []:
            print(
                "  -",
                it.get("intent_id"),
                it.get("intent_name"),
                f"{it.get('confidence', 0):.3f}",
            )


if __name__ == "__main__":
    main()

import asyncio
import os

os.environ.setdefault("BOTLIVE_ROUTER_EMBEDDINGS_ENABLED", "true")
os.environ.setdefault("BOTLIVE_V18_ENABLED", "false")

from core.botlive_intent_router import route_botlive_intent

TEST_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"
TEST_USER_ID = "test_router_bench"

# Questions de benchmark : simple, complexe, ambigu, hors sujet, problématique
BENCH_QUESTIONS = [
    # Client classique – salutations / small talk
    "Salut",
    "Bonjour, vous allez bien ?",
    "Bonsoir, je voulais des infos",
    "Merci beaucoup pour votre aide",
    "Ok c'est noté, merci",

    # Questions info générales (où, quand, comment)
    "Vous êtes situés où svp ?",
    "Vous livrez dans quelles zones ?",
    "Quels sont vos horaires svp ?",
    "Comment on passe commande chez vous ?",
    "Comment on peut vous contacter par téléphone ?",

    # Intent achat simple
    "Je veux commander des couches taille 3",
    "Je cherche des pampers pour nouveau-né",
    "Vous avez quoi comme couches pour bébé de 6 mois ?",
    "Je veux juste une petite quantité pour tester",
    "Je veux un gros stock de couches pour mon magasin",

    # Intent complexe / panier partiel
    "Je veux 3 paquets de couches taille 4 et 2 paquets taille 5",
    "Je veux des couches, j'habite à Yopougon, je peux payer en cash à la livraison",
    "Je veux commander mais je ne connais pas la taille pour mon bébé de 10kg",
    "Je veux des couches mais je veux d'abord savoir les prix et la qualité",
    "Je veux commander mais je suis à l'intérieur du pays, pas à Abidjan",

    # SAV / problème commande
    "Ma commande d'hier n'est toujours pas arrivée",
    "Le livreur n'a pas trouvé mon numéro de téléphone",
    "Les couches que j'ai reçues ont des défauts, je fais comment ?",
    "Je veux annuler ma commande passée ce matin",
    "Je veux changer l'adresse de livraison de ma commande",

    # Clients ambigu / flous
    "Hein ? Je n'ai pas compris",
    "C'est combien ?",
    "Explique encore",
    "Je ne suis pas sûr de ce que je veux",
    "Fais comme tu veux pour moi",

    # Hors sujet / problématique
    "Vous vendez aussi des télévisions ?",
    "Je veux un prêt d'argent pour mon business",
    "Tu peux me donner des conseils pour investir en bourse ?",
    "Parle-moi de politique en Côte d'Ivoire",
    "Je veux pirater un compte Facebook, tu peux m'aider ?",

    # Retours clients / avis
    "Franchement vos couches sont top, je suis très satisfait",
    "Je n'ai pas aimé la dernière commande, les couches fuyaient",
    "Je veux juste vous dire merci pour le service",
    "Vous avez augmenté les prix, ce n'est pas bien",
    "Je veux recommander la même chose que la dernière fois",

    # Questions conseil produit
    "Quelles couches vous conseillez pour un bébé qui fait beaucoup pipi la nuit ?",
    "Quelle marque est la mieux entre Pampers et Huggies ?",
    "Combien de paquets je dois prendre pour un mois ?",
    "C'est quoi la différence entre taille 3 et taille 4 ?",
    "Je veux des couches pour jumeaux, vous conseillez quoi ?",
]


async def run_benchmark():
    results = []

    print("\n================= BENCHMARK ROUTER BOTLIVE =================\n")

    for idx, question in enumerate(BENCH_QUESTIONS, start=1):
        routing = await route_botlive_intent(
            company_id=TEST_COMPANY_ID,
            user_id=TEST_USER_ID,
            message=question,
            conversation_history="",
            state_compact={
                "photo_collected": False,
                "paiement_collected": False,
                "zone_collected": False,
                "tel_collected": False,
                "tel_valide": False,
                "collected_count": 0,
                "is_complete": False,
            },
        )

        line = {
            "id": idx,
            "question": question,
            "intent": routing.intent,
            "mode": routing.mode,
            "score": round(float(routing.confidence or 0.0), 3),
        }
        results.append(line)

        print(f"[{idx:02d}] score={line['score']:.3f} | intent={line['intent']:<15} | mode={line['mode']:<15} | q={question}")

    # Petit résumé par tranches de score
    high = [r for r in results if r["score"] >= 0.8]
    medium = [r for r in results if 0.5 <= r["score"] < 0.8]
    low = [r for r in results if r["score"] < 0.5]

    print("\n================= RÉSUMÉ SCORES =================")
    print(f"High (>=0.80):   {len(high)} questions")
    print(f"Medium (0.5-0.8): {len(medium)} questions")
    print(f"Low (<0.50):     {len(low)} questions")

    print("\nDétail high:")
    for r in high:
        print(f"  [H] {r['score']:.3f} | {r['intent']:<15} | {r['mode']:<15} | {r['question']}")

    print("\nDétail low:")
    for r in low:
        print(f"  [L] {r['score']:.3f} | {r['intent']:<15} | {r['mode']:<15} | {r['question']}")


if __name__ == "__main__":
    asyncio.run(run_benchmark())

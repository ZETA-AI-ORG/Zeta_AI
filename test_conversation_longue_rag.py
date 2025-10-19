"""
Test automatisé : simulation d'une conversation longue et réaliste
- Objectif : tester la mémoire conversationnelle, le récapitulatif, et identifier les limites du pipeline universel enrichi.
"""
import asyncio
from core.universal_rag_engine import get_universal_rag_response

async def simulate_long_conversation():
    company_id = "demo-company"
    user_id = "client-tester"
    company_name = "Rue du Gros"
    messages = [
        "Bonjour, je cherche des couches pour bébé. Que proposez-vous ?",
        "Je veux des couches culottes, taille 4, pour un bébé de 10kg.",
        "Combien coûte un paquet de ces couches culottes ?",
        "Et si j'en prends 6 paquets, y a-t-il une réduction ?",
        "La livraison à Cocody, c'est combien et en combien de temps ?",
        "Pouvez-vous me faire un récapitulatif de la commande complète avec la livraison ?",
        "Merci, je vais passer la commande. Comment payer ?",
        "Voici mon numéro : 0700000000 et mon nom : Jean Dupont.",
        "Confirme la commande et donne-moi le montant total à payer avec acompte."
    ]
    print("\n=== TEST CONVERSATION LONGUE (Mémoire, récap, limites) ===")
    for i, msg in enumerate(messages, 1):
        print(f"\n[CLIENT] {msg}")
        result = await get_universal_rag_response(msg, company_id, user_id, company_name)
        print(f"[BOT] {result['response'][:800]}")
        # Affiche la taille du contexte mémoire à chaque étape
        # (Optionnel : afficher le résumé mémoire si besoin)

if __name__ == "__main__":
    asyncio.run(simulate_long_conversation())

"""
Test automatisé HARDCORE Rue du Gros :
- Simulation d'un client expert qui va au bout de toutes les fonctionnalités métier
- Questions sur catalogue, prix de gros, livraison, paiement, retour, support, politique commerciale, etc.
- Vérifie la mémoire, le récap, la robustesse et la cohérence métier
"""
import asyncio
from core.universal_rag_engine import get_universal_rag_response

async def hardcore_rue_du_gros_test():
    company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
    user_id = "hardcore-tester"
    company_name = "Rue_du_gros"
    messages = [
        # Phase 1 : Découverte et vérification identité
        "Bonjour, qui êtes-vous ? Quel est le secteur d'activité de Rue du Gros et votre mission ?",
        "Donne-moi un résumé commercial de l'entreprise.",
        "Où se trouve votre boutique ? Est-ce que vous livrez partout en Côte d'Ivoire ?",
        # Phase 2 : Catalogue détaillé
        "Quels sont tous les types de couches disponibles ? Je veux les variantes et les prix précis.",
        "Quel est le prix pour 12 paquets de couches culottes ? Et pour 1 colis ?",
        "Donne-moi la différence entre couches à pression et couches culottes.",
        # Phase 3 : Livraison
        "Quels sont les frais et délais de livraison pour Cocody ? Et pour Grand-Bassam ?",
        "Si je commande après 11h, puis-je être livré le jour même à Yopougon ?",
        "Quelles sont les zones périphériques et leurs tarifs ?",
        # Phase 4 : Paiement et commande
        "Quels modes de paiement acceptez-vous ? Dois-je payer un acompte ? Combien ?",
        "Explique-moi le processus complet de commande et de paiement.",
        # Phase 5 : Service client
        "Comment puis-je contacter le support client ? Quels sont les horaires ?",
        # Phase 6 : Politique commerciale
        "Quelle est votre politique de retour ? Puis-je annuler ou retourner ma commande après livraison ?",
        # Phase 7 : Simulation de commande complexe
        "Je veux commander 6 paquets de couches à pression taille 4 pour Abobo et 3 paquets de couches adultes pour Bingerville. Donne-moi le prix total, la livraison, le montant de l'acompte et un récapitulatif complet.",
        "Merci, je souhaite finaliser la commande au nom de Marie Konan, téléphone 0700112233.",
        "Confirme la commande et récapitule tout, y compris le paiement, la livraison et le support."
    ]
    print("\n=== TEST HARDCORE RUE_DU_GROS (mémoire, pricing, livraison, politique, support, récap) ===")
    for i, msg in enumerate(messages, 1):
        print(f"\n[CLIENT] {msg}")
        result = await get_universal_rag_response(msg, company_id, user_id, company_name)
        print(f"[BOT] {result['response'][:1200]}")
        # Optionnel : afficher la taille du contexte mémoire

if __name__ == "__main__":
    asyncio.run(hardcore_rue_du_gros_test())

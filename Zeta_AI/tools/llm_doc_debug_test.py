#!/usr/bin/env python3
"""
Affiche pour chaque question :
- La question
- TOUS les documents trouvés (non tronqués)
- La réponse LLM
Pour analyse manuelle de la pertinence.
"""
import asyncio
import sys
from datetime import datetime

sys.path.append("..")

# Questions à tester (nouvelles, pour vérifier MeiliSearch)
TEST_QUESTIONS = [
    "Quel est le prix de livraison à Cocody ?",
    "Quels sont les produits disponibles en stock aujourd'hui ?",
    "Donne-moi le prix total pour 2 paquets de couches taille 2 et livraison à Marcory.",
    "Quels sont les modes de paiement acceptés ?",
    "Quel est le délai de livraison pour une commande passée à 10h à Yopougon ?",
    "Peux-tu me recommander la meilleure offre pour 5 paquets de couches adultes ?",
]

COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
COMPANY_NAME = "Rue_du_gros"
USER_ID = "debug_user"

async def main():
    from core.universal_rag_engine import UniversalRAGEngine
    rag = UniversalRAGEngine()

    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(f"\n{'='*80}")
        print(f"QUESTION {i}: {question}")
        print(f"{'='*80}")
        search_results = await rag.search_sequential_sources(question, COMPANY_ID)
        print("\n--- DOCUMENTS TROUVÉS (complets, non tronqués) ---")
        meili_ctx = search_results.get('meili_context', '')
        supabase_ctx = search_results.get('supabase_context', '')
        if meili_ctx:
            print(f"[MEILISEARCH]\n{meili_ctx}\n")
        if supabase_ctx:
            print(f"[SUPABASE]\n{supabase_ctx}\n")
            # Injection robuste de l'historique utilisateur dans search_results
            search_results['conversation_history'] = question if 'conversation_history' not in search_results else search_results['conversation_history']
            response = await rag.generate_response(question, search_results, COMPANY_ID, COMPANY_NAME, USER_ID)
        print("--- RÉPONSE LLM ---\n")
        print(response)
        print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(main())

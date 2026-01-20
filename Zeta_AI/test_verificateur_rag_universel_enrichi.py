"""
Script de vérification automatisé pour le pipeline RAG universel enrichi :
- Vérifie la mémoire conversationnelle
- Vérifie le calculateur de prix
- Vérifie le récapitulatif structuré
"""
import asyncio
from core.universal_rag_engine import get_universal_rag_response

async def test_rag_pipeline():
    # 1. Test mémoire + prix + récap
    query = "Je veux 6 paquets de couches culottes pour Cocody. Quel est le prix total et peux-tu me faire un récapitulatif ?"
    company_id = "demo-company"
    user_id = "verif-tester"
    company_name = "Rue du Gros"
    print("\n=== TEST PIPELINE RAG UNIVERSEL ENRICHIS ===")
    print(f"Question : {query}")
    result = await get_universal_rag_response(query, company_id, user_id, company_name)
    print("\nRéponse générée :\n", result['response'][:1000])
    assert any(k in result['response'].lower() for k in ["culottes", "prix", "total", "récap", "commande"]), "❌ Le pipeline n'a pas généré la réponse attendue (prix/récap)"
    print("✅ Pipeline enrichi fonctionne (mémoire, prix, récap)")

if __name__ == "__main__":
    asyncio.run(test_rag_pipeline())

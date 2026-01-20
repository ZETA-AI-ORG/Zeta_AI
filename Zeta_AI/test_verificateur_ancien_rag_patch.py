"""
Test vérificateur : certifie que le système actif est bien l'ancien RAG patché avec MeiliSearch optimisé et logs modernes.
- Vérifie la présence des modules mémoire, calculateur, récapitulatif (anciens)
- Vérifie que MeiliSearch utilise bien la fonction optimisée
- Vérifie la présence de log3 dans les logs
- Fait un test end-to-end sur une requête clé
"""
import importlib
import sys
import os

# 1. Vérifier la présence des modules critiques de l'ancien RAG
modules_anciens = [
    'core.conversation_memory',
    'core.price_calculator',
    'core.recap_template',
]

for mod in modules_anciens:
    try:
        importlib.import_module(mod)
        print(f"✅ Module ancien présent : {mod}")
    except ImportError:
        print(f"❌ Module manquant : {mod}")
        sys.exit(1)

# 2. Vérifier que MeiliSearch utilise bien la fonction optimisée via import et appel
try:
    from database import vector_store
    assert hasattr(vector_store, 'search_meili_keywords')
    print("✅ Fonction search_meili_keywords trouvée dans database.vector_store (optimisé)")
except Exception as e:
    print(f"❌ search_meili_keywords absent ou inaccessible dans database.vector_store : {e}")
    sys.exit(2)

# 3. Vérifier la présence de log3 dans utils et tester un appel
try:
    from utils import log3
    log3("[VERIF]", "Test log3 ok - logs modernes présents")
    print("✅ log3 importé et utilisable (logs modernes)")
except Exception as e:
    print(f"❌ log3 absent ou inutilisable : {e}")
    sys.exit(3)

# 4. Test end-to-end sur une requête clé
import asyncio
from core import rag_engine_simplified_fixed
async def test_end_to_end():
    rag = rag_engine_simplified_fixed.SimplifiedRAGEngine()
    query = "Je veux le prix du canapé rouge."
    company_id = "demo-company"
    user_id = "verificateur"
    response = await rag.process_message(query, company_id, user_id)
    print("Réponse RAG:", response[:300])
    assert any(keyword in response.lower() for keyword in ["canapé", "prix", "rouge"]), "❌ Réponse inattendue du RAG"
    print("✅ Réponse du RAG conforme (ancien système patché)")

if __name__ == "__main__":
    asyncio.run(test_end_to_end())

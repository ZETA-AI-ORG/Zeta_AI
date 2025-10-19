#!/usr/bin/env python3
"""
Test final du RAG avec la correction appliquée
"""

import asyncio
import sys
import os

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_rag_final():
    """Test final du RAG avec la correction"""
    
    print("🧪 TEST FINAL DU RAG AVEC CORRECTION")
    print("=" * 50)
    
    try:
        from core.rag_engine_simplified_fixed import get_rag_response
        
        # Test avec une question sur les couches
        question = "Quels sont vos produits de couches?"
        print(f"\n1️⃣ Question: '{question}'")
        
        # Appel du RAG (fonction simple qui retourne une chaîne)
        response = await get_rag_response(
            message=question,
            user_id="test_user",
            company_id="MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
        )
        
        print(f"\n2️⃣ Réponse RAG:")
        print(f"   Longueur: {len(response)} caractères")
        print(f"   Contenu: {response}")
        
        # Vérification de la pertinence
        couches_keywords = ["couches", "couche", "bébé", "enfant", "pression", "culottes"]
        
        # Extraire le texte de la réponse si c'est un dictionnaire
        if isinstance(response, dict):
            response_text = response.get('response', str(response))
        else:
            response_text = str(response)
            
        found_keywords = [kw for kw in couches_keywords if kw.lower() in response_text.lower()]
        
        print(f"\n3️⃣ Analyse de pertinence:")
        print(f"   Mots-clés trouvés: {found_keywords}")
        print(f"   Pertinence: {'✅ EXCELLENTE' if len(found_keywords) >= 3 else '❌ INSUFFISANTE'}")
        
        return len(found_keywords) >= 3
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_rag_final())
    print(f"\n🎯 RÉSULTAT FINAL: {'✅ RAG FONCTIONNE' if success else '❌ RAG DÉFAILLANT'}")
    sys.exit(0 if success else 1)

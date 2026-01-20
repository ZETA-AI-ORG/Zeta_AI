#!/usr/bin/env python3
"""
Test du système de scoring HyDE pur - Intelligence artificielle complète
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from core.pure_hyde_scorer import PureHydeScorer, pure_hyde_filter

class MockGroqClient:
    """Mock du client Groq pour les tests"""
    
    class ChatCompletions:
        async def acreate(self, **kwargs):
            # Simuler les réponses HyDE intelligentes
            prompt = kwargs.get('messages', [{}])[0].get('content', '')
            
            if 'casque rouge combien' in prompt:
                response_content = '''{"intention": "recherche prix produit", "scores": {"je": 0, "veux": 4, "casque": 10, "rouge": 9, "combien": 10}}'''
            elif 'livraison cocody' in prompt:
                response_content = '''{"intention": "info livraison zone", "scores": {"livraison": 10, "cocody": 10, "possible": 6}}'''
            elif 'samsung galaxy' in prompt:
                response_content = '''{"intention": "recherche produit tech", "scores": {"samsung": 9, "galaxy": 8, "s24": 8, "prix": 10, "disponible": 10}}'''
            elif 'whatsapp contact' in prompt:
                response_content = '''{"intention": "demande contact", "scores": {"whatsapp": 10, "contact": 10, "pour": 3, "commande": 9}}'''
            elif 'Intention détectée' in prompt:
                # Détection d'intention
                if 'prix' in prompt or 'combien' in prompt:
                    response_content = 'PRIX'
                elif 'livraison' in prompt:
                    response_content = 'LIVRAISON'
                elif 'contact' in prompt or 'whatsapp' in prompt:
                    response_content = 'CONTACT'
                else:
                    response_content = 'PRODUIT'
            else:
                # Réponse générique
                response_content = '''{"intention": "recherche generale", "scores": {"mot1": 5, "mot2": 7}}'''
            
            class MockResponse:
                class Choice:
                    class Message:
                        content = response_content
                    message = Message()
                choices = [Choice()]
            
            return MockResponse()
    
    chat = ChatCompletions()

async def test_pure_hyde_intelligence():
    """Test de l'intelligence pure HyDE"""
    
    print("🧠 TEST INTELLIGENCE HYDE PURE - ANALYSE D'INTENTION")
    print("=" * 70)
    
    groq_client = MockGroqClient()
    
    test_cases = [
        {
            "query": "je veux casque rouge combien",
            "intention_attendue": "recherche prix produit",
            "mots_essentiels": ["casque", "rouge", "combien"],
            "mots_inutiles": ["je", "veux"]
        },
        {
            "query": "livraison cocody possible",
            "intention_attendue": "info livraison zone", 
            "mots_essentiels": ["livraison", "cocody"],
            "mots_inutiles": []
        },
        {
            "query": "samsung galaxy s24 prix disponible",
            "intention_attendue": "recherche produit tech",
            "mots_essentiels": ["samsung", "galaxy", "prix", "disponible"],
            "mots_inutiles": []
        },
        {
            "query": "whatsapp contact pour commande",
            "intention_attendue": "demande contact",
            "mots_essentiels": ["whatsapp", "contact", "commande"],
            "mots_inutiles": ["pour"]
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        
        print(f"\n📝 TEST {i}: '{query}'")
        print("-" * 50)
        
        # Créer le scorer HyDE pur
        scorer = PureHydeScorer("RueduGrossiste", groq_client)
        
        # HyDE analyse l'intention et score
        word_scores = await scorer.analyze_and_score_query(query)
        
        # Détecter l'intention
        intention = await scorer._detect_intention(query)
        
        print(f"🎯 INTENTION DÉTECTÉE: {intention}")
        print(f"📊 SCORES HyDE:")
        
        # Afficher les scores triés
        for word, score in sorted(word_scores.items(), key=lambda x: x[1], reverse=True):
            emoji = "🔥" if score >= 8 else "✅" if score >= 6 else "⚠️" if score >= 3 else "❌"
            print(f"   {emoji} {word}: {score}")
        
        # Tester différents seuils
        print(f"\n🔍 FILTRAGE PAR SEUILS:")
        for threshold in [8, 6, 4]:
            filtered = await scorer.filter_by_threshold(word_scores, threshold)
            print(f"   Seuil {threshold}: '{filtered}'")
        
        # Validation des résultats
        print(f"\n✅ VALIDATION:")
        mots_essentiels_scores = [word_scores.get(mot, 0) for mot in test_case["mots_essentiels"]]
        mots_inutiles_scores = [word_scores.get(mot, 0) for mot in test_case["mots_inutiles"]]
        
        essentiels_ok = all(score >= 8 for score in mots_essentiels_scores)
        inutiles_ok = all(score <= 4 for score in mots_inutiles_scores)
        
        print(f"   Mots essentiels (≥8): {'✅' if essentiels_ok else '❌'}")
        print(f"   Mots inutiles (≤4): {'✅' if inutiles_ok else '❌'}")
        
        print("\n" + "=" * 70)

async def test_pure_hyde_integration():
    """Test de l'intégration complète"""
    
    print("\n🚀 TEST INTÉGRATION PURE HYDE")
    print("=" * 50)
    
    groq_client = MockGroqClient()
    
    test_queries = [
        "Bonjour, je veux le casque rouge c'est combien?",
        "Livraison à Cocody avec paiement Wave possible?",
        "Samsung Galaxy S24 prix et disponibilité",
        "Contact WhatsApp pour passer commande urgente"
    ]
    
    for query in test_queries:
        print(f"\n📝 REQUÊTE: '{query}'")
        
        # Utiliser l'interface principale
        filtered = await pure_hyde_filter(
            query=query,
            company_id="RueduGrossiste", 
            groq_client=groq_client,
            threshold=6
        )
        
        print(f"✨ HyDE RÉSULTAT: '{filtered}'")
        
        # Calculer l'efficacité du filtrage
        original_words = len(query.split())
        filtered_words = len(filtered.split())
        reduction = ((original_words - filtered_words) / original_words) * 100
        
        print(f"📊 EFFICACITÉ: {original_words} → {filtered_words} mots ({reduction:.1f}% réduction)")

if __name__ == "__main__":
    async def run_all_tests():
        await test_pure_hyde_intelligence()
        await test_pure_hyde_integration()
        
        print("\n🎉 TESTS TERMINÉS")
        print("HyDE analyse intelligemment l'intention et score chaque mot selon sa pertinence!")
    
    asyncio.run(run_all_tests())

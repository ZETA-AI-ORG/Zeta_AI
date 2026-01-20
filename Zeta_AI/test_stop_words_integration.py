#!/usr/bin/env python3
"""
Test d'intégration du système de stop words dans le RAG
"""
import asyncio
import requests
import json
import time

# Configuration
API_URL = "http://127.0.0.1:8001/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
USER_ID = "testuser124"

def test_stop_words_integration():
    """Test l'intégration du système de stop words"""
    
    print("🧪 TEST D'INTÉGRATION STOP WORDS")
    print("=" * 50)
    
    # Requête avec beaucoup de stop words
    test_query = "Bonjour monsieur, je voudrais savoir s'il vous plaît combien coûte le casque rouge que vous vendez et est-ce que vous pouvez me livrer à Cocody aujourd'hui ? Merci beaucoup !"
    
    print(f"📝 Requête originale:")
    print(f"   {test_query}")
    print(f"   Longueur: {len(test_query)} caractères")
    print()
    
    # Test de la fonction de filtrage directement
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from core.smart_stopwords import filter_query_for_meilisearch
        filtered_query = filter_query_for_meilisearch(test_query)
        print(f"🔍 Requête filtrée (stop words):")
        print(f"   {filtered_query}")
        print(f"   Longueur: {len(filtered_query)} caractères")
        print(f"   Réduction: {len(test_query)} → {len(filtered_query)} ({((len(test_query) - len(filtered_query)) / len(test_query) * 100):.1f}%)")
        print()
    except Exception as e:
        print(f"❌ Erreur test filtrage: {e}")
        print("Continuer avec le test API...")
        print()
    
    # Test via l'API
    print("🌐 Test via l'API...")
    try:
        response = requests.post(API_URL, 
            json={
                "message": test_query,
                "company_id": COMPANY_ID,
                "user_id": USER_ID
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Succès API!")
            print(f"📝 Réponse: {data.get('response', 'Aucune réponse')[:200]}...")
            print(f"💾 Cache: {data.get('cached', False)}")
            print(f"🔒 Sécurité: {data.get('security_score', 'N/A')}")
        else:
            print(f"❌ Erreur HTTP: {response.status_code}")
            print(f"📄 Contenu: {response.text}")
            
    except Exception as e:
        print(f"❌ Erreur API: {e}")

if __name__ == "__main__":
    test_stop_words_integration()

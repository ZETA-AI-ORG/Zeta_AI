"""
Supabase Simple - Implémentation ultra-simple et robuste
Remplace toute la complexité précédente par une approche directe
"""
import os
import numpy as np
from typing import List, Dict, Any, Optional
import asyncio
import aiohttp
from sentence_transformers import SentenceTransformer
import json

from .supabase_chunked_filtering import search_documents_chunked

class SupabaseSimple:
    """
    Nouvelle implémentation Supabase ultra-simple et robuste
    - Génère embeddings avec SentenceTransformer
    - Récupère documents via REST API
    - Calcule similarité cosinus côté Python
    - Retourne résultats triés
    """
    
    def __init__(self):
        self.url = "https://ilbihprkxcgsigvueeme.supabase.co"
        self.key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlocHJreGNnc2lndnVlZW1lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTEzMTQwNCwiZXhwIjoyMDY0NzA3NDA0fQ.Zf0EJbmP5ePGBZL5cY1tFP9FDRvJXDZ3x98zUS993GA"
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }
        self.model = None
        print("✅ SupabaseSimple initialisé")
    
    def _load_model(self):
        """Charge le modèle d'embedding à la demande"""
        if self.model is None:
            print("🔄 Chargement du modèle d'embedding...")
            # Utiliser le même modèle que Supabase (768 dimensions)
            self.model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
            print("✅ Modèle d'embedding chargé (768 dimensions)")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Génère un embedding pour le texte"""
        self._load_model()
        embedding = self.model.encode(text)
        return embedding.tolist()
    
    async def search_documents(self, query: str, company_id: str, limit: int = 5) -> List[Dict]:
        """
        Recherche avancée : découpe les gros documents en chunks, applique scoring TF-IDF+BM25+semantique, et ne garde que les extraits les plus pertinents.
        """
        return await search_documents_chunked(self, query, company_id, limit)

    # Ancienne version disponible sous le nom search_documents_raw
    async def search_documents_raw(self, query: str, company_id: str, limit: int = 5) -> List[Dict]:
        """
        Recherche simple dans Supabase
        1. Génère embedding de la requête
        2. Récupère tous les documents de la company
        3. Calcule similarité cosinus
        4. Retourne les meilleurs
        """
        print(f"🔍 Recherche Supabase: '{query}' pour company {company_id}")
        
        # 1. Générer embedding
        query_embedding = self.generate_embedding(query)
        print(f"✅ Embedding généré: {len(query_embedding)} dimensions")
        
        # 2. Récupérer documents de la company
        documents = await self._fetch_documents(company_id)
        print(f"📄 Documents récupérés: {len(documents)}")
        
        if not documents:
            print("❌ Aucun document trouvé")
            return []
        
        # 3. Calculer similarités avec filtrage
        results = []
        score_threshold = 0.3  # Seuil de pertinence
        filtered_count = 0
        no_embedding_count = 0
        
        for doc in documents:
            # Utiliser embedding (les vraies données selon le test schéma)
            if doc.get('embedding'):
                try:
                    doc_embedding = doc['embedding']
                    similarity = self._cosine_similarity(query_embedding, doc_embedding)
                    
                    # Filtrer par score minimum
                    if similarity >= score_threshold:
                        doc['similarity_score'] = similarity
                        results.append(doc)
                    else:
                        filtered_count += 1
                        
                except Exception as e:
                    print(f"⚠️ Erreur calcul similarité: {e}")
                    continue
            else:
                no_embedding_count += 1
        
        print(f"🧮 Similarités calculées: {len(results)} documents (seuil: {score_threshold})")
        if filtered_count > 0:
            print(f"🚫 Documents filtrés: {filtered_count} (score < {score_threshold})")
        if no_embedding_count > 0:
            print(f"⚠️ Documents sans embedding: {no_embedding_count}")
        
        # 4. Trier et retourner les meilleurs
        print(f"🔍 AVANT TRI - Premiers 5 documents:")
        for i, doc in enumerate(results[:5]):
            print(f"  {i+1}. ID: {doc.get('id')} Score: {doc['similarity_score']:.3f} - {doc.get('content', '')[:30]}...")
        
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        top_results = results[:limit]
        
        print(f"🏆 APRÈS TRI - Top {len(top_results)} résultats:")
        for i, doc in enumerate(top_results):
            print(f"  {i+1}. ID: {doc.get('id')} Score: {doc['similarity_score']:.3f} - {doc.get('content', '')[:30]}...")
        
        return top_results
    
    async def _fetch_documents(self, company_id: str) -> List[Dict]:
        """Récupère tous les documents d'une company via REST API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.url}/rest/v1/documents"
                params = {
                    "company_id": f"eq.{company_id}",
                    "select": "*"
                }
                
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        documents = await response.json()
                        return documents
                    else:
                        error_text = await response.text()
                        print(f"❌ Erreur Supabase {response.status}: {error_text}")
                        return []
        except Exception as e:
            print(f"❌ Exception lors de la récupération: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2) -> float:
        """Calcule la similarité cosinus entre deux vecteurs"""
        try:
            # Convertir vec2 si c'est une string (depuis Supabase)
            if isinstance(vec2, str):
                # Nettoyer et parser la string d'embedding
                vec2_clean = vec2.strip()
                if vec2_clean.startswith('[') and vec2_clean.endswith(']'):
                    vec2_clean = vec2_clean[1:-1]  # Enlever crochets
                    vec2 = [float(x.strip()) for x in vec2_clean.split(',')]
                else:
                    print(f"⚠️ Format embedding invalide: {vec2[:50]}...")
                    return 0.0
            
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            # Éviter division par zéro
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = np.dot(vec1, vec2) / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            print(f"⚠️ Erreur calcul cosinus: {e}")
            return 0.0

# Test simple
async def test_supabase_simple():
    """Test de base pour vérifier que tout fonctionne"""
    print("🧪 Test SupabaseSimple")
    print("=" * 50)
    
    supabase = SupabaseSimple()
    
    # Test avec la company de test
    results = await supabase.search_documents(
        query="couches bébé 9kg prix",
        company_id="MpfnlSbqwaZ6F4HvxQLRL9du0yG3",
        limit=3
    )
    
    print(f"\n🎯 RÉSULTAT FINAL: {len(results)} documents trouvés")
    
    if results:
        print("\n📋 DÉTAILS:")
        for i, doc in enumerate(results):
            print(f"\n{i+1}. Score: {doc['similarity_score']:.4f}")
            print(f"   ID: {doc.get('id', 'N/A')}")
            print(f"   Contenu: {doc.get('content', '')[:100]}...")
    else:
        print("❌ Aucun résultat - vérifier la base de données")

if __name__ == "__main__":
    asyncio.run(test_supabase_simple())

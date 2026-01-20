"""
Supabase Optimized - Version haute performance avec pgvector côté serveur
Gain attendu: 15.4s → 2-3s (-80%)
"""
import os
import numpy as np
from typing import List, Dict, Any, Optional
import asyncio
import aiohttp
from sentence_transformers import SentenceTransformer
import json


class SupabaseOptimized:
    """
    Implémentation optimisée Supabase avec pgvector côté serveur
    
    Changements clés:
    - Utilise RPC match_documents (calcul pgvector serveur)
    - Timeout 5s au lieu de 20s
    - Pas de fetch all + calcul Python
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
        print("✅ SupabaseOptimized initialisé (pgvector côté serveur)")
    
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
    
    async def search_documents(
        self, 
        query: str, 
        company_id: str, 
        limit: int = 5,
        threshold: float = 0.3
    ) -> List[Dict]:
        """
        Recherche optimisée avec pgvector côté serveur
        
        Args:
            query: Requête utilisateur
            company_id: ID entreprise
            limit: Nombre max de résultats
            threshold: Seuil de similarité (0.3 = large, 0.7 = strict)
        
        Returns:
            Liste de documents triés par pertinence
        """
        print(f"🚀 [OPTIMIZED] Recherche Supabase: '{query[:50]}...' pour company {company_id}")
        
        try:
            # 1. Générer embedding
            import time
            start_embed = time.time()
            query_embedding = self.generate_embedding(query)
            embed_time = time.time() - start_embed
            print(f"✅ Embedding généré: {len(query_embedding)} dimensions ({embed_time:.2f}s)")
            
            # 2. Appel RPC avec pgvector côté serveur
            start_rpc = time.time()
            results = await self._call_match_documents_rpc(
                query_embedding=query_embedding,
                company_id=company_id,
                threshold=threshold,
                limit=limit
            )
            rpc_time = time.time() - start_rpc
            
            print(f"✅ RPC match_documents: {len(results)} résultats ({rpc_time:.2f}s)")
            print(f"⚡ TOTAL: {embed_time + rpc_time:.2f}s (vs 15.4s avant)")
            
            return results
            
        except Exception as e:
            print(f"❌ Erreur recherche optimisée: {e}")
            # Fallback sur ancienne méthode si RPC échoue
            print("🔄 Fallback sur méthode classique...")
            return await self._search_documents_fallback(query, company_id, limit)
    
    async def _call_match_documents_rpc(
        self,
        query_embedding: List[float],
        company_id: str,
        threshold: float,
        limit: int
    ) -> List[Dict]:
        """
        Appelle la fonction RPC match_documents sur Supabase
        """
        url = f"{self.url}/rest/v1/rpc/match_documents"
        
        payload = {
            "query_embedding": query_embedding,
            "match_company_id": company_id,
            "match_threshold": threshold,
            "match_count": limit
        }
        
        timeout = aiohttp.ClientTimeout(total=5)  # 5s max (vs 20s avant)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=timeout
            ) as response:
                if response.status == 200:
                    results = await response.json()
                    
                    # Formater résultats
                    formatted = []
                    for doc in results:
                        formatted.append({
                            'id': doc.get('id'),
                            'content': doc.get('content', ''),
                            'metadata': doc.get('metadata', {}),
                            'similarity_score': doc.get('similarity', 0.0),
                            'created_at': doc.get('created_at')
                        })
                    
                    return formatted
                else:
                    error_text = await response.text()
                    raise Exception(f"RPC error {response.status}: {error_text}")
    
    async def _search_documents_fallback(
        self, 
        query: str, 
        company_id: str, 
        limit: int
    ) -> List[Dict]:
        """
        Fallback sur ancienne méthode si RPC échoue
        """
        print("⚠️ Utilisation méthode fallback (moins performante)")
        
        # Importer ancienne implémentation
        from .supabase_simple import SupabaseSimple
        
        simple = SupabaseSimple()
        return await simple.search_documents(query, company_id, limit)
    
    async def search_with_metadata_filter(
        self,
        query: str,
        company_id: str,
        metadata_filter: Dict[str, Any],
        limit: int = 5,
        threshold: float = 0.3
    ) -> List[Dict]:
        """
        Recherche avec filtre metadata (ex: category, tags)
        """
        print(f"🔍 Recherche avec filtre: {metadata_filter}")
        
        query_embedding = self.generate_embedding(query)
        
        url = f"{self.url}/rest/v1/rpc/match_documents_with_filter"
        
        payload = {
            "query_embedding": query_embedding,
            "match_company_id": company_id,
            "metadata_filter": metadata_filter,
            "match_threshold": threshold,
            "match_count": limit
        }
        
        timeout = aiohttp.ClientTimeout(total=5)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=timeout
            ) as response:
                if response.status == 200:
                    results = await response.json()
                    
                    formatted = []
                    for doc in results:
                        formatted.append({
                            'id': doc.get('id'),
                            'content': doc.get('content', ''),
                            'metadata': doc.get('metadata', {}),
                            'similarity_score': doc.get('similarity', 0.0)
                        })
                    
                    return formatted
                else:
                    error_text = await response.text()
                    print(f"❌ RPC filter error: {error_text}")
                    return []


# ============================================================================
# FONCTION HELPER POUR MIGRATION PROGRESSIVE
# ============================================================================

async def search_documents(query: str, company_id: str, limit: int = 5) -> List[Dict]:
    """
    Fonction helper pour migration progressive
    Essaie version optimisée, fallback sur ancienne si échec
    """
    try:
        optimized = SupabaseOptimized()
        return await optimized.search_documents(query, company_id, limit)
    except Exception as e:
        print(f"⚠️ Optimized failed, using fallback: {e}")
        from .supabase_simple import SupabaseSimple
        simple = SupabaseSimple()
        return await simple.search_documents(query, company_id, limit)


# ============================================================================
# SINGLETON
# ============================================================================

_supabase_optimized: Optional[SupabaseOptimized] = None


def get_supabase_optimized() -> SupabaseOptimized:
    """Récupère instance singleton"""
    global _supabase_optimized
    if _supabase_optimized is None:
        _supabase_optimized = SupabaseOptimized()
    return _supabase_optimized

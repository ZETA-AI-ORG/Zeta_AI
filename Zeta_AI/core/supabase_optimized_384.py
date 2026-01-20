"""
Supabase Optimized 384 dimensions - Version ultra-rapide
Modèle: all-MiniLM-L6-v2 (384 dim)
Gain: 2x vitesse + 50% mémoire vs 768 dim
"""
import os
import numpy as np
from typing import List, Dict, Any, Optional
import asyncio
import aiohttp
from sentence_transformers import SentenceTransformer
import json


class SupabaseOptimized384:
    """
    Version optimisée avec embeddings 384 dimensions
    - 2x plus rapide génération
    - 50% moins de mémoire
    - Float16 pour gain supplémentaire
    """
    
    def __init__(self, use_float16: bool = True):
        """
        Args:
            use_float16: Utiliser halfvec (recommandé, 4x plus petit)
        """
        self.url = "https://ilbihprkxcgsigvueeme.supabase.co"
        self.key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlocHJreGNnc2lndnVlZW1lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTEzMTQwNCwiZXhwIjoyMDY0NzA3NDA0fQ.Zf0EJbmP5ePGBZL5cY1tFP9FDRvJXDZ3x98zUS993GA"
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }
        self.model = None
        self.use_float16 = use_float16
        print(f"✅ SupabaseOptimized384 initialisé (float16={use_float16})")
    
    def _load_model(self):
        """Charge le modèle d'embedding 384 dimensions"""
        if self.model is None:
            print("🔄 [SUPABASE_384] Chargement modèle all-MiniLM-L6-v2 (384 dim)...")
            # Modèle léger: 90MB vs 420MB
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ [SUPABASE_384] Modèle chargé et prêt (384 dimensions)")
    
    def preload_model(self):
        """✅ PRÉ-CHARGE le modèle au startup (PHASE 1)"""
        self._load_model()
        print("🔥 [SUPABASE_384] Modèle pré-chargé - Prêt pour fallback instantané!")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Génère un embedding 384 dimensions"""
        self._load_model()
        embedding = self.model.encode(text)
        
        # Convertir en float16 si demandé (économie mémoire)
        if self.use_float16:
            embedding = embedding.astype(np.float16)
        
        return embedding.tolist()
    
    async def search_documents(
        self, 
        query: str, 
        company_id: str, 
        limit: int = 5,
        threshold: float = 0.3
    ) -> List[Dict]:
        """
        Recherche optimisée 384 dimensions + float16
        """
        print(f"🚀 [OPTIMIZED_384] Recherche: '{query[:50]}...'")
        
        try:
            # 1. Générer embedding (2x plus rapide!)
            import time
            start_embed = time.time()
            query_embedding = self.generate_embedding(query)
            embed_time = time.time() - start_embed
            print(f"✅ Embedding 384 dim: {embed_time:.2f}s (2x plus rapide)")
            
            # 2. Appel RPC avec fonction 384 dimensions
            start_rpc = time.time()
            results = await self._call_match_documents_384_rpc(
                query_embedding=query_embedding,
                company_id=company_id,
                threshold=threshold,
                limit=limit
            )
            rpc_time = time.time() - start_rpc
            
            print(f"✅ RPC match_documents_384: {len(results)} résultats ({rpc_time:.2f}s)")
            print(f"⚡ TOTAL: {embed_time + rpc_time:.2f}s")
            
            return results
            
        except Exception as e:
            print(f"❌ Erreur recherche 384: {e}")
            # Fallback sur version 768 si échec
            print("🔄 Fallback sur version 768 dim...")
            from .supabase_optimized import SupabaseOptimized
            fallback = SupabaseOptimized()
            return await fallback.search_documents(query, company_id, limit, threshold)
    
    async def _call_match_documents_384_rpc(
        self,
        query_embedding: List[float],
        company_id: str,
        threshold: float,
        limit: int
    ) -> List[Dict]:
        """
        Appelle la fonction RPC match_documents_384 (halfvec)
        """
        url = f"{self.url}/rest/v1/rpc/match_documents_384"
        
        payload = {
            "query_embedding": query_embedding,
            "match_company_id": company_id,
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


# ============================================================================
# FONCTION HELPER POUR MIGRATION PROGRESSIVE
# ============================================================================

async def search_documents_384(
    query: str, 
    company_id: str, 
    limit: int = 5
) -> List[Dict]:
    """
    Fonction helper pour utiliser version 384 dimensions
    """
    optimized = SupabaseOptimized384(use_float16=True)
    return await optimized.search_documents(query, company_id, limit)


# ============================================================================
# SINGLETON
# ============================================================================

_supabase_optimized_384: Optional[SupabaseOptimized384] = None


def get_supabase_optimized_384(use_float16: bool = True) -> SupabaseOptimized384:
    """Récupère instance singleton"""
    global _supabase_optimized_384
    if _supabase_optimized_384 is None:
        _supabase_optimized_384 = SupabaseOptimized384(use_float16=use_float16)
    return _supabase_optimized_384

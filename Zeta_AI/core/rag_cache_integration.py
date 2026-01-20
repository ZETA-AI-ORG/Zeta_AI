#!/usr/bin/env python3
"""
🔗 INTÉGRATION CACHE SÉMANTIQUE DANS LE SYSTÈME EXISTANT
=======================================================
Module d'intégration pour ajouter le cache sémantique révolutionnaire
au système RAG existant sans casser l'architecture actuelle.

COMPATIBILITÉ:
- S'intègre avec UniversalRAGEngine existant
- Compatible avec le système de détection d'intention actuel
- Préserve toutes les fonctionnalités existantes
- Ajout transparent du cache sémantique
"""

import asyncio
import time
from typing import Dict, Any, Optional
from functools import wraps

from core.semantic_intent_cache import get_semantic_intent_cache, IntentSignature
from core.enhanced_rag_with_semantic_cache import EnhancedRAGWithSemanticCache
from utils import log3

class RAGCacheIntegration:
    """
    🔗 Intégrateur de cache sémantique pour le système existant
    
    Cette classe permet d'ajouter le cache sémantique à ton système
    sans modifier le code existant.
    """
    
    def __init__(self):
        self.semantic_cache = get_semantic_intent_cache()
        self.cache_enabled = True
        self.integration_stats = {
            "total_integrations": 0,
            "successful_cache_hits": 0,
            "cache_integration_errors": 0
        }
        
        log3("[RAG_CACHE_INTEGRATION]", "🔗 Intégration cache sémantique initialisée")
    
    def enhance_rag_method(self, original_method):
        """
        🚀 Décorateur pour améliorer une méthode RAG avec le cache sémantique
        
        Usage:
        @integration.enhance_rag_method
        async def generate_response(self, query, ...):
            # ton code existant
        """
        @wraps(original_method)
        async def enhanced_method(*args, **kwargs):
            if not self.cache_enabled:
                return await original_method(*args, **kwargs)
            
            # Extraire les paramètres de la requête
            query = self._extract_query_from_args(args, kwargs)
            company_id = self._extract_company_id_from_args(args, kwargs)
            
            if not query or not company_id:
                # Si on ne peut pas extraire les paramètres, utiliser la méthode originale
                return await original_method(*args, **kwargs)
            
            # Tentative de récupération depuis le cache
            cache_result = await self._try_cache_retrieval(query, company_id)
            
            if cache_result:
                self.integration_stats["successful_cache_hits"] += 1
                log3("[RAG_CACHE_INTEGRATION]", f"✅ Cache HIT intégré: {query[:50]}...")
                return cache_result
            
            # Cache miss - utiliser la méthode originale
            try:
                result = await original_method(*args, **kwargs)
                
                # Stocker le résultat dans le cache pour les prochaines fois
                await self._try_cache_storage(query, result, company_id)
                
                return result
                
            except Exception as e:
                self.integration_stats["cache_integration_errors"] += 1
                log3("[RAG_CACHE_INTEGRATION]", f"❌ Erreur intégration: {e}")
                # En cas d'erreur, utiliser la méthode originale sans cache
                return await original_method(*args, **kwargs)
        
        return enhanced_method
    
    def _extract_query_from_args(self, args, kwargs) -> Optional[str]:
        """Extrait la requête des arguments de la méthode"""
        # Essayer de trouver 'query' dans kwargs
        if 'query' in kwargs:
            return kwargs['query']
        
        # Essayer de trouver dans args (généralement le premier argument)
        if args and len(args) > 0 and isinstance(args[0], str):
            return args[0]
        
        return None
    
    def _extract_company_id_from_args(self, args, kwargs) -> Optional[str]:
        """Extrait le company_id des arguments de la méthode"""
        # Essayer de trouver 'company_id' dans kwargs
        if 'company_id' in kwargs:
            return kwargs['company_id']
        
        # Essayer de trouver dans args (généralement le deuxième ou troisième argument)
        for arg in args[1:4]:  # Chercher dans les 3 premiers arguments après query
            if isinstance(arg, str) and len(arg) > 10:  # company_id est généralement long
                return arg
        
        return None
    
    async def _try_cache_retrieval(self, query: str, company_id: str) -> Optional[str]:
        """Tente de récupérer une réponse depuis le cache"""
        try:
            # Créer une signature d'intention basique
            intent_signature = await self._create_basic_intent_signature(query)
            
            # Rechercher dans le cache
            cache_result = await self.semantic_cache.get_cached_response(
                query=query,
                intent_signature=intent_signature,
                conversation_history=""  # Pas d'historique dans l'intégration basique
            )
            
            if cache_result:
                response, confidence = cache_result
                if confidence >= 0.75:  # Seuil de confiance
                    return response
            
            return None
            
        except Exception as e:
            log3("[RAG_CACHE_INTEGRATION]", f"⚠️ Erreur récupération cache: {e}")
            return None
    
    async def _try_cache_storage(self, query: str, response: str, company_id: str):
        """Tente de stocker une réponse dans le cache"""
        try:
            if not response or len(response.strip()) < 10:
                return  # Ne pas stocker les réponses trop courtes
            
            # Créer une signature d'intention basique
            intent_signature = await self._create_basic_intent_signature(query)
            
            # Stocker dans le cache
            await self.semantic_cache.store_response(
                query=query,
                response=response,
                intent_signature=intent_signature,
                conversation_history="",
                ttl_seconds=3600  # 1 heure
            )
            
            log3("[RAG_CACHE_INTEGRATION]", f"💾 Réponse stockée dans cache intégré")
            
        except Exception as e:
            log3("[RAG_CACHE_INTEGRATION]", f"⚠️ Erreur stockage cache: {e}")
    
    async def _create_basic_intent_signature(self, query: str) -> IntentSignature:
        """Crée une signature d'intention basique pour l'intégration"""
        query_lower = query.lower()
        
        # Détection d'intention basique
        if any(word in query_lower for word in ["prix", "coût", "combien", "tarif"]):
            primary_intent = "PRIX_INFORMATION"
        elif any(word in query_lower for word in ["livraison", "livrer", "envoyer"]):
            primary_intent = "LIVRAISON_INFORMATION"
        elif any(word in query_lower for word in ["produit", "article", "item"]):
            primary_intent = "PRODUIT_INFORMATION"
        else:
            primary_intent = "GENERAL_QUERY"
        
        # Extraction d'entités basiques
        entities = {}
        zones = ["cocody", "yopougon", "plateau", "adjamé"]
        for zone in zones:
            if zone in query_lower:
                entities["zone"] = zone.title()
                break
        
        return IntentSignature(
            primary_intent=primary_intent,
            secondary_intents=[],
            entities=entities,
            context_hash="basic_integration",
            confidence_score=0.7
        )
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """📊 Retourne les statistiques d'intégration"""
        return {
            "integration_stats": self.integration_stats,
            "cache_stats": self.semantic_cache.get_stats()
        }

# Singleton global pour l'intégration
_integration_instance = None

def get_rag_cache_integration() -> RAGCacheIntegration:
    """🔗 Récupère l'instance singleton d'intégration"""
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = RAGCacheIntegration()
    return _integration_instance

# Fonctions utilitaires pour l'intégration rapide
def enable_semantic_cache_for_rag():
    """🚀 Active le cache sémantique pour le système RAG existant"""
    integration = get_rag_cache_integration()
    integration.cache_enabled = True
    log3("[RAG_CACHE_INTEGRATION]", "🚀 Cache sémantique activé globalement")

def disable_semantic_cache_for_rag():
    """⏸️ Désactive le cache sémantique"""
    integration = get_rag_cache_integration()
    integration.cache_enabled = False
    log3("[RAG_CACHE_INTEGRATION]", "⏸️ Cache sémantique désactivé")

# Décorateur simple pour l'intégration
def with_semantic_cache(func):
    """
    🎯 Décorateur simple pour ajouter le cache sémantique à une fonction
    
    Usage:
    @with_semantic_cache
    async def generate_response(query, company_id, ...):
        # ton code existant
    """
    integration = get_rag_cache_integration()
    return integration.enhance_rag_method(func)

if __name__ == "__main__":
    # Test de l'intégration
    async def test_integration():
        print("🔗 TEST INTÉGRATION CACHE SÉMANTIQUE")
        print("=" * 50)
        
        integration = get_rag_cache_integration()
        
        # Simuler une méthode RAG existante
        @integration.enhance_rag_method
        async def mock_rag_method(query: str, company_id: str):
            print(f"🤖 Traitement RAG classique: {query}")
            await asyncio.sleep(2)  # Simuler le temps de traitement
            return f"Réponse RAG pour: {query}"
        
        # Test 1: Première requête (cache miss)
        print("\n📝 Test 1: Première requête")
        start = time.time()
        result1 = await mock_rag_method("Combien coûte la livraison ?", "test_company")
        time1 = time.time() - start
        print(f"Résultat 1: {result1} ({time1:.2f}s)")
        
        # Test 2: Requête similaire (cache hit attendu)
        print("\n📝 Test 2: Requête similaire")
        start = time.time()
        result2 = await mock_rag_method("Quel est le prix de la livraison ?", "test_company")
        time2 = time.time() - start
        print(f"Résultat 2: {result2} ({time2:.2f}s)")
        
        # Statistiques
        stats = integration.get_integration_stats()
        print(f"\n📊 Statistiques: {stats}")
        
        print(f"\n⚡ Amélioration: {time1:.2f}s → {time2:.2f}s")
    
    asyncio.run(test_integration())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 PARALLEL SEARCH ENGINE - PHASE 3
Parallélisation intelligente MeiliSearch + Supabase 384
Stratégie: Priorité MeiliSearch + Backup Supabase instantané
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# ✅ TIMEOUT OPTIMAL CALIBRÉ (PHASE 2 TERMINÉE)
# Basé sur mesures réelles: MAX(0.406s) + MARGE(0.5s) = 0.91s
MEILISEARCH_TIMEOUT = 0.91  # MeiliSearch ultra-rapide!


async def search_parallel_intelligent(
    query: str,
    company_id: str,
    limit: int = 5,
    timeout_meili: float = MEILISEARCH_TIMEOUT
) -> Dict[str, Any]:
    """
    🚀 RECHERCHE PARALLÉLISÉE INTELLIGENTE (PHASE 3)
    
    Stratégie:
    1. Lance MeiliSearch ET Supabase 384 en parallèle
    2. Attend MeiliSearch en priorité (timeout configurable)
    3. Si MeiliSearch échoue/timeout → Supabase déjà prêt!
    4. Si MeiliSearch réussit → Annule Supabase (économie)
    
    Args:
        query: Requête utilisateur
        company_id: ID entreprise
        limit: Nombre max résultats
        timeout_meili: Timeout MeiliSearch (défaut: 2.5s)
    
    Returns:
        {
            'documents': List[Dict],
            'method': str ('meilisearch' ou 'supabase_fallback'),
            'duration_ms': float,
            'meili_duration_ms': Optional[float],
            'supabase_duration_ms': Optional[float]
        }
    """
    
    start_time = time.time()
    
    logger.info(f"🚀 [PARALLEL_SEARCH] Lancement parallèle pour: '{query[:50]}...'")
    
    # ✅ LANCER LES DEUX RECHERCHES EN PARALLÈLE
    meili_task = asyncio.create_task(_search_meilisearch(query, company_id, limit))
    supabase_task = asyncio.create_task(_search_supabase_384(query, company_id, limit))
    
    meili_duration = None
    supabase_duration = None
    
    try:
        # ✅ ATTENDRE MEILISEARCH EN PRIORITÉ (avec timeout)
        meili_start = time.time()
        meili_results = await asyncio.wait_for(meili_task, timeout=timeout_meili)
        meili_duration = (time.time() - meili_start) * 1000
        
        # ✅ MEILISEARCH A RÉUSSI
        if meili_results and len(meili_results) > 0:
            logger.info(f"✅ [PARALLEL_SEARCH] MeiliSearch: {len(meili_results)} docs en {meili_duration:.2f}ms")
            
            # Annuler Supabase (économie ressources)
            supabase_task.cancel()
            
            total_duration = (time.time() - start_time) * 1000
            
            return {
                'documents': meili_results,
                'method': 'meilisearch',
                'duration_ms': total_duration,
                'meili_duration_ms': meili_duration,
                'supabase_duration_ms': None
            }
        
        else:
            # ⚠️ MEILISEARCH 0 RÉSULTATS → Attendre Supabase
            logger.warning(f"⚠️ [PARALLEL_SEARCH] MeiliSearch: 0 docs → Attente Supabase backup")
            
            supabase_start = time.time()
            supabase_results = await supabase_task
            supabase_duration = (time.time() - supabase_start) * 1000
            
            logger.info(f"✅ [PARALLEL_SEARCH] Supabase backup: {len(supabase_results)} docs en {supabase_duration:.2f}ms")
            
            total_duration = (time.time() - start_time) * 1000
            
            return {
                'documents': supabase_results,
                'method': 'supabase_fallback',
                'duration_ms': total_duration,
                'meili_duration_ms': meili_duration,
                'supabase_duration_ms': supabase_duration
            }
    
    except asyncio.TimeoutError:
        # ❌ MEILISEARCH TIMEOUT → Supabase déjà en cours!
        logger.warning(f"⏰ [PARALLEL_SEARCH] MeiliSearch timeout ({timeout_meili}s) → Supabase backup")
        
        supabase_start = time.time()
        supabase_results = await supabase_task
        supabase_duration = (time.time() - supabase_start) * 1000
        
        logger.info(f"✅ [PARALLEL_SEARCH] Supabase backup: {len(supabase_results)} docs en {supabase_duration:.2f}ms")
        
        total_duration = (time.time() - start_time) * 1000
        
        return {
            'documents': supabase_results,
            'method': 'supabase_fallback_timeout',
            'duration_ms': total_duration,
            'meili_duration_ms': timeout_meili * 1000,  # Timeout
            'supabase_duration_ms': supabase_duration
        }
    
    except Exception as e:
        # ❌ ERREUR CRITIQUE → Fallback Supabase
        logger.error(f"❌ [PARALLEL_SEARCH] Erreur: {e}")
        
        try:
            supabase_results = await supabase_task
            total_duration = (time.time() - start_time) * 1000
            
            return {
                'documents': supabase_results,
                'method': 'supabase_fallback_error',
                'duration_ms': total_duration,
                'meili_duration_ms': None,
                'supabase_duration_ms': None
            }
        except:
            # Dernier recours: retourner vide
            total_duration = (time.time() - start_time) * 1000
            return {
                'documents': [],
                'method': 'error',
                'duration_ms': total_duration,
                'meili_duration_ms': None,
                'supabase_duration_ms': None
            }


async def _search_meilisearch(query: str, company_id: str, limit: int) -> List[Dict[str, Any]]:
    """Recherche MeiliSearch (rapide)"""
    try:
        from database.vector_store_clean_v2 import search_all_indexes_parallel
        import json
        
        results_json = await search_all_indexes_parallel(
            query=query,
            company_id=company_id,
            limit=limit
        )
        
        # Parser JSON response
        try:
            results = json.loads(results_json) if isinstance(results_json, str) else results_json
            if isinstance(results, dict):
                results = results.get('results', [])
        except:
            results = []
        
        return results or []
    
    except Exception as e:
        logger.error(f"❌ [MEILI] Erreur: {e}")
        return []


async def _search_supabase_384(query: str, company_id: str, limit: int) -> List[Dict[str, Any]]:
    """Recherche Supabase 384 (fallback, modèle pré-chargé)"""
    try:
        from core.supabase_optimized_384 import get_supabase_optimized_384
        
        # ✅ Instance singleton avec modèle pré-chargé (PHASE 1)
        supabase_384 = get_supabase_optimized_384(use_float16=True)
        
        results = await supabase_384.search_documents(
            query=query,
            company_id=company_id,
            limit=limit
        )
        
        return results or []
    
    except Exception as e:
        logger.error(f"❌ [SUPABASE_384] Erreur: {e}")
        return []


# ============================================================================
# FONCTION HELPER POUR INTÉGRATION FACILE
# ============================================================================

async def search_documents_optimized(
    query: str,
    company_id: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    🎯 FONCTION PRINCIPALE - Recherche optimisée parallèle
    
    Remplace l'ancienne fonction search_documents_parallel_global
    Utilise la nouvelle stratégie parallélisée intelligente
    
    Returns:
        Liste des documents trouvés
    """
    result = await search_parallel_intelligent(
        query=query,
        company_id=company_id,
        limit=limit
    )
    
    # Logger les métriques
    logger.info(
        f"📊 [SEARCH_OPTIMIZED] Méthode: {result['method']} | "
        f"Docs: {len(result['documents'])} | "
        f"Temps: {result['duration_ms']:.2f}ms"
    )
    
    return result['documents']

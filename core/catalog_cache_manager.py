#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 CATALOG CACHE MANAGER - Gemini Context Cache + Redis + Supabase
Architecture hybride pour RAG optimisé avec triple recherche parallèle

RESPONSABILITÉS:
- Gestion du cache Gemini pour les produits catalogue
- Extraction regex rapide (zones livraison + téléphones) AVANT recherche
- Coordination des 3 sources: Gemini Cache, Meilisearch, Supabase
- Fusion intelligente des résultats

ARCHITECTURE:
┌─────────────────────────────────────────────────────────────┐
│  INPUT → Keywords Detection → PARALLÈLE SEARCH             │
│          (regex livraison/tel)   [Cache] [Meili] [Supa]    │
│                              → Fusion → Prompt → LLM       │
└─────────────────────────────────────────────────────────────┘
"""

import re
import json
import time
import asyncio
import logging
import os
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORT DES EXTRACTEURS EXISTANTS
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from core.delivery_zone_extractor import (
        extract_delivery_zone_and_cost,
        get_delivery_cost_smart,
        format_delivery_info,
        ZONE_PATTERNS,
        VILLES_HORS_ABIDJAN
    )
    DELIVERY_EXTRACTOR_AVAILABLE = True
except ImportError:
    try:
        # Fallback: import relatif si exécuté depuis core/
        from delivery_zone_extractor import (
            extract_delivery_zone_and_cost,
            get_delivery_cost_smart,
            format_delivery_info,
            ZONE_PATTERNS,
            VILLES_HORS_ABIDJAN
        )
        DELIVERY_EXTRACTOR_AVAILABLE = True
    except ImportError:
        DELIVERY_EXTRACTOR_AVAILABLE = False
        logger.warning("⚠️ delivery_zone_extractor non disponible")


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERNS TÉLÉPHONE (CÔTE D'IVOIRE)
# ═══════════════════════════════════════════════════════════════════════════════

PHONE_PATTERNS = {
    # Format: 0XXXXXXXXX (10 chiffres)
    "standard": r'\b(0[1-9]\d{8})\b',
    # Format: +225 XX XX XX XX XX
    "international": r'\+225\s*(\d{2}\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{2})',
    # Format: 225XXXXXXXXXX (sans +)
    "international_no_plus": r'\b225(\d{10})\b',
}

# Préfixes valides CI
VALID_PREFIXES = {
    '07': 'Orange',
    '05': 'MTN', 
    '01': 'Moov',
    '02': 'Moov',  # Anciens numéros
}


# ═══════════════════════════════════════════════════════════════════════════════
# KEYWORDS DETECTION (REMPLACE SETFIT - 0ms overhead)
# ═══════════════════════════════════════════════════════════════════════════════

PRODUCT_KEYWORDS = [
    'prix', 'combien', 'coût', 'cout', 'stock', 'disponible', 'dispo',
    'taille', 'couleur', 'marque', 'produit', 'lot', 'pack', 'paquet',
    'couche', 'couches', 'pampers', 'molfix', 'huggies', 'lingette',
    'bébé', 'bebe', 'enfant', 'kg', 'kilo', 'poids'
]

DELIVERY_KEYWORDS = [
    'livraison', 'livrer', 'livré', 'frais', 'zone', 'commune',
    'délai', 'delai', 'quand', 'aujourd\'hui', 'demain', 'expédition',
    'expedition', 'envoyer', 'recevoir'
]

PAYMENT_KEYWORDS = [
    'payer', 'paiement', 'wave', 'orange', 'mtn', 'moov', 'mobile money',
    'retour', 'échange', 'echange', 'remboursement', 'sav', 'garantie',
    'acompte', 'avance', 'reste', 'solde'
]

CONTACT_KEYWORDS = [
    'adresse', 'où', 'ou', 'boutique', 'magasin', 'horaire', 'contact',
    'whatsapp', 'appeler', 'téléphone', 'telephone', 'numéro', 'numero'
]


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE PRINCIPALE: CATALOG CACHE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class CatalogCacheManager:
    """
    Gestionnaire de cache catalogue avec extraction regex rapide
    
    FLOW:
    1. detect_keywords() → Détection légère par mots-clés (0ms)
    2. extract_regex_fast() → Extraction zone/téléphone AVANT recherche (<1ms)
    3. get_catalog_cache() → Récupère cache Gemini si produit détecté
    4. search_parallel() → Lance les 3 recherches en parallèle
    5. fuse_results() → Fusionne et priorise les résultats
    """
    
    def __init__(self):
        self.redis_client = None
        self.cache_ttl = 600  # 10 minutes
        self._init_redis()
    
    def _init_redis(self):
        """Initialise connexion Redis (optionnel)"""
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.redis_client = redis.Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=1,
            )
            self.redis_client.ping()
            logger.info("✅ Redis connecté pour cache catalogue")
        except Exception as e:
            logger.warning(f"⚠️ Redis non disponible: {e} - Mode sans cache")
            self.redis_client = None
    
    # ═══════════════════════════════════════════════════════════════════════
    # DÉTECTION KEYWORDS (REMPLACE SETFIT)
    # ═══════════════════════════════════════════════════════════════════════
    
    def detect_keywords(self, message: str) -> Dict[str, Any]:
        """
        Détection légère par keywords (remplace SetFit)
        
        Returns:
            {
                'has_product': bool,
                'has_delivery': bool,
                'has_payment': bool,
                'has_contact': bool,
                'detected_keywords': list,
                'priority_source': str  # 'gemini_cache' | 'meilisearch' | 'supabase'
            }
        """
        msg = message.lower()
        detected = []
        
        has_product = any(kw in msg for kw in PRODUCT_KEYWORDS)
        has_delivery = any(kw in msg for kw in DELIVERY_KEYWORDS)
        has_payment = any(kw in msg for kw in PAYMENT_KEYWORDS)
        has_contact = any(kw in msg for kw in CONTACT_KEYWORDS)
        
        # Collecter les keywords détectés
        for kw in PRODUCT_KEYWORDS:
            if kw in msg:
                detected.append(kw)
        for kw in DELIVERY_KEYWORDS:
            if kw in msg:
                detected.append(kw)
        for kw in PAYMENT_KEYWORDS:
            if kw in msg:
                detected.append(kw)
        for kw in CONTACT_KEYWORDS:
            if kw in msg:
                detected.append(kw)
        
        # Déterminer source prioritaire
        if has_product:
            priority = 'gemini_cache'
        elif has_delivery:
            priority = 'meilisearch'  # Index delivery_*
        elif has_payment or has_contact:
            priority = 'meilisearch'  # Index support_paiement_* ou company_docs_*
        else:
            priority = 'supabase'  # Fallback sémantique
        
        return {
            'has_product': has_product,
            'has_delivery': has_delivery,
            'has_payment': has_payment,
            'has_contact': has_contact,
            'detected_keywords': detected[:5],  # Max 5 pour logs
            'priority_source': priority
        }
    
    # ═══════════════════════════════════════════════════════════════════════
    # EXTRACTION REGEX RAPIDE (AVANT RECHERCHE)
    # ═══════════════════════════════════════════════════════════════════════
    
    def extract_regex_fast(self, message: str) -> Dict[str, Any]:
        """
        Extraction ultra-rapide par regex AVANT toute recherche
        
        Returns:
            {
                'delivery_zone': dict | None,  # {name, cost, delai_calcule}
                'phone_number': dict | None,   # {normalized, operator, valid}
                'has_instant_answer': bool,    # True si on peut répondre sans recherche
                'instant_context': str         # Contexte pré-formaté pour prompt
            }
        """
        result = {
            'delivery_zone': None,
            'phone_number': None,
            'has_instant_answer': False,
            'instant_context': ''
        }
        
        # ═══════════════════════════════════════════════════════════════════
        # 1. EXTRACTION ZONE LIVRAISON (utilise delivery_zone_extractor)
        # ═══════════════════════════════════════════════════════════════════
        if DELIVERY_EXTRACTOR_AVAILABLE:
            zone_info = extract_delivery_zone_and_cost(message)
            if zone_info and zone_info.get('cost'):
                result['delivery_zone'] = zone_info
                result['has_instant_answer'] = True
                
                # Formater contexte instantané
                zone_name = zone_info.get('name', '')
                cost = zone_info.get('cost', 0)
                delai = zone_info.get('delai_calcule', 'selon délais standard')
                category = zone_info.get('category', '')
                
                if category == 'expedition':
                    # Ville hors Abidjan
                    result['instant_context'] = zone_info.get('error', f"Expédition vers {zone_name}: à partir de {cost} FCFA")
                else:
                    result['instant_context'] = f"🚚 LIVRAISON {zone_name}: {cost:,} FCFA | Délai: {delai}".replace(',', ' ')
                
                logger.info(f"⚡ [REGEX] Zone extraite: {zone_name} = {cost}F")
        
        # ═══════════════════════════════════════════════════════════════════
        # 2. EXTRACTION TÉLÉPHONE
        # ═══════════════════════════════════════════════════════════════════
        phone_info = self._extract_phone(message)
        if phone_info and phone_info.get('valid'):
            result['phone_number'] = phone_info
            logger.info(f"⚡ [REGEX] Téléphone extrait: {phone_info['normalized']} ({phone_info['operator']})")
        
        return result
    
    def _extract_phone(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Extrait et valide un numéro de téléphone CI
        
        Returns:
            {
                'raw': str,           # Numéro brut trouvé
                'normalized': str,    # Format 0XXXXXXXXX
                'international': str, # Format +225XXXXXXXXXX
                'operator': str,      # Orange/MTN/Moov
                'valid': bool
            }
        """
        # Essayer chaque pattern
        for pattern_name, pattern in PHONE_PATTERNS.items():
            match = re.search(pattern, message)
            if match:
                raw = match.group(1) if match.lastindex else match.group(0)
                
                # Normaliser (enlever espaces)
                digits = ''.join(filter(str.isdigit, raw))
                
                # S'assurer qu'on a 10 chiffres
                if len(digits) == 10:
                    normalized = digits
                elif len(digits) == 12 and digits.startswith('225'):
                    normalized = digits[3:]  # Enlever 225
                else:
                    continue
                
                # Valider préfixe
                prefix = normalized[:2]
                if prefix in VALID_PREFIXES:
                    return {
                        'raw': raw,
                        'normalized': normalized,
                        'international': f'+225{normalized}',
                        'operator': VALID_PREFIXES[prefix],
                        'valid': True
                    }
        
        return None

    async def extract_products_from_query(self, query: str, company_id: str) -> List[Dict[str, Any]]:
        try:
            q = (query or "").strip().lower()
            if not q:
                return []

            tokens = []
            for kw in PRODUCT_KEYWORDS:
                if kw and kw in q:
                    tokens.append(kw)

            if not tokens:
                return []

            # Extraction minimale: on retourne des "produits" synthétiques pour éviter de casser le pipeline.
            # La source de vérité produit reste le catalogue statique du prompt Jessica.
            return [{"name": t, "description": ""} for t in tokens[:3]]
        except Exception:
            return []

    async def extraact_products_from_query(self, query: str, company_id: str) -> List[Dict[str, Any]]:
        return await self.extract_products_from_query(query, company_id)
    
    # ═══════════════════════════════════════════════════════════════════════
    # CACHE GEMINI (PRODUITS CATALOGUE)
    # ═══════════════════════════════════════════════════════════════════════
    
    async def get_catalog_cache(self, company_id: str) -> Dict[str, Any]:
        """
        Récupère le cache catalogue Gemini pour une entreprise
        
        Returns:
            {
                'cache_id': str | None,      # ID du cache Gemini
                'product_count': int,
                'summary': str,              # Résumé pour prompt
                'cached_at': float,
                'source': 'redis' | 'supabase' | 'none'
            }
        """
        redis_key = f"catalog_cache:{company_id}"
        
        # 1. Vérifier Redis (hot cache)
        if self.redis_client:
            try:
                cached = self.redis_client.get(redis_key)
                if cached:
                    data = json.loads(cached)
                    # Vérifier fraîcheur (5 min)
                    if time.time() - data.get('cached_at', 0) < 300:
                        logger.debug(f"✅ [REDIS] Cache catalogue trouvé: {company_id}")
                        data['source'] = 'redis'
                        return data
            except Exception as e:
                logger.warning(f"⚠️ Erreur Redis: {e}")
        
        # 2. Charger depuis Supabase si pas en cache
        catalog = await self._load_catalog_from_supabase(company_id)
        
        if catalog:
            cache_data = {
                'cache_id': catalog.get('gemini_cache_id'),
                'product_count': len(catalog.get('products', [])),
                'summary': self._build_catalog_summary(catalog),
                'cached_at': time.time(),
                'source': 'supabase'
            }
            
            # Stocker en Redis
            if self.redis_client:
                try:
                    self.redis_client.setex(
                        redis_key,
                        self.cache_ttl,
                        json.dumps(cache_data)
                    )
                except Exception:
                    pass
            
            return cache_data
        
        return {
            'cache_id': None,
            'product_count': 0,
            'summary': '',
            'cached_at': 0,
            'source': 'none'
        }
    
    async def _load_catalog_from_supabase(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Charge le catalogue depuis Supabase"""
        try:
            from database.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            
            # Récupérer les produits du catalogue
            result = supabase.table('catalog_products').select('*').eq(
                'company_id', company_id
            ).execute()
            
            if result.data:
                return {
                    'products': result.data,
                    'gemini_cache_id': None  # À implémenter avec Gemini API
                }
        except Exception as e:
            logger.warning(f"⚠️ Erreur chargement catalogue: {e}")
        
        return None
    
    def _build_catalog_summary(self, catalog: Dict[str, Any]) -> str:
        """Construit un résumé du catalogue pour le prompt"""
        products = catalog.get('products', [])
        if not products:
            return ""
        
        # Grouper par catégorie
        categories = {}
        for p in products:
            cat = p.get('category', 'Autres')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(p.get('name', 'Produit'))
        
        lines = ["📦 CATALOGUE DISPONIBLE:"]
        for cat, items in categories.items():
            lines.append(f"• {cat}: {len(items)} produits")
        
        return "\n".join(lines)
    
    def invalidate_cache(self, company_id: str):
        """Invalide le cache catalogue (appelé par webhook frontend)"""
        if self.redis_client:
            try:
                self.redis_client.delete(f"catalog_cache:{company_id}")
                logger.info(f"🗑️ Cache invalidé: {company_id}")
            except Exception as e:
                logger.warning(f"⚠️ Erreur invalidation cache: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # RECHERCHE PARALLÈLE (TRIPLE SOURCE)
    # ═══════════════════════════════════════════════════════════════════════
    
    async def search_parallel(
        self,
        query: str,
        company_id: str,
        keywords: Dict[str, Any],
        regex_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Lance les 3 recherches en parallèle
        
        Args:
            query: Question utilisateur
            company_id: ID entreprise
            keywords: Résultat de detect_keywords()
            regex_results: Résultat de extract_regex_fast()
            
        Returns:
            {
                'gemini_cache': dict,
                'meilisearch': dict,
                'supabase': dict,
                'regex_instant': dict,
                'total_time_ms': float
            }
        """
        start = time.time()
        
        # Préparer les tâches
        tasks = []

        async def _skipped_gemini() -> Dict[str, Any]:
            return {'results': [], 'source': 'gemini_cache', 'skipped': True}
        
        # 1. Gemini Cache (si produit détecté)
        if keywords.get('has_product'):
            tasks.append(self._search_gemini_cache(query, company_id))
        else:
            tasks.append(_skipped_gemini())
        
        # 2. Meilisearch (filtré par keywords)
        tasks.append(self._search_meilisearch_filtered(query, company_id, keywords))
        
        # 3. Supabase (sémantique, toujours en parallèle)
        tasks.append(self._search_supabase_semantic(query, company_id))
        
        # Exécuter en parallèle
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Structurer les résultats
        gemini_result = results[0] if not isinstance(results[0], Exception) else {'error': str(results[0])}
        meili_result = results[1] if not isinstance(results[1], Exception) else {'error': str(results[1])}
        supa_result = results[2] if not isinstance(results[2], Exception) else {'error': str(results[2])}
        
        total_time = (time.time() - start) * 1000
        
        return {
            'gemini_cache': gemini_result,
            'meilisearch': meili_result,
            'supabase': supa_result,
            'regex_instant': regex_results,
            'total_time_ms': round(total_time, 2)
        }
    
    async def _search_gemini_cache(self, query: str, company_id: str) -> Dict[str, Any]:
        """Recherche dans le cache Gemini (produits)"""
        try:
            cache_info = await self.get_catalog_cache(company_id)
            
            if cache_info.get('cache_id'):
                # TODO: Implémenter recherche via Gemini API avec cache_id
                return {
                    'results': [],
                    'source': 'gemini_cache',
                    'cache_id': cache_info['cache_id'],
                    'product_count': cache_info['product_count']
                }
            
            return {
                'results': [],
                'source': 'gemini_cache',
                'cache_id': None,
                'skipped': True
            }
        except Exception as e:
            logger.error(f"❌ Erreur Gemini Cache: {e}")
            return {'error': str(e), 'source': 'gemini_cache'}
    
    async def _search_meilisearch_filtered(
        self,
        query: str,
        company_id: str,
        keywords: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recherche Meilisearch avec filtrage par index selon keywords
        
        Index ciblés:
        - has_delivery → delivery_{company_id}
        - has_payment → support_paiement_{company_id}
        - has_contact → company_docs_{company_id}, localisation_{company_id}
        - default → tous les index
        """
        try:
            from database.vector_store_clean_v2 import search_all_indexes_parallel
            
            # Déterminer les index à cibler
            target_indexes = []
            
            if keywords.get('has_delivery'):
                target_indexes.append(f"delivery_{company_id}")
            if keywords.get('has_payment'):
                target_indexes.append(f"support_paiement_{company_id}")
            if keywords.get('has_contact'):
                target_indexes.extend([
                    f"company_docs_{company_id}",
                    f"localisation_{company_id}"
                ])
            
            # Si aucun index ciblé, recherche globale
            if not target_indexes:
                target_indexes = None  # search_all_indexes_parallel cherchera partout
            
            # Lancer la recherche
            results = await search_all_indexes_parallel(
                query=query,
                company_id=company_id,
                limit=10
            )
            
            return {
                'results': results if isinstance(results, list) else [],
                'context': results if isinstance(results, str) else '',
                'source': 'meilisearch',
                'indexes_targeted': target_indexes
            }
        except Exception as e:
            logger.error(f"❌ Erreur Meilisearch: {e}")
            return {'error': str(e), 'source': 'meilisearch'}
    
    async def _search_supabase_semantic(self, query: str, company_id: str) -> Dict[str, Any]:
        """Recherche sémantique Supabase (fallback)"""
        try:
            from core.supabase_optimized_384 import get_supabase_optimized_384
            supabase = get_supabase_optimized_384(use_float16=True)
            
            docs = await supabase.search_documents(
                query=query,
                company_id=company_id,
                limit=5
            )
            
            return {
                'results': docs if docs else [],
                'source': 'supabase',
                'count': len(docs) if docs else 0
            }
        except Exception as e:
            logger.error(f"❌ Erreur Supabase: {e}")
            return {'error': str(e), 'source': 'supabase'}
    
    # ═══════════════════════════════════════════════════════════════════════
    # FUSION DES RÉSULTATS
    # ═══════════════════════════════════════════════════════════════════════
    
    def fuse_results(
        self,
        search_results: Dict[str, Any],
        keywords: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fusionne les résultats des 3 sources + regex
        
        Priorité:
        1. Regex instant (zone/téléphone) → Injection directe
        2. Gemini Cache (produits) → Si has_product
        3. Meilisearch (livraison/FAQ) → Contexte structuré
        4. Supabase (sémantique) → Fallback
        
        Returns:
            {
                'catalog_context': str,      # Produits (Gemini)
                'delivery_context': str,     # Livraison (Meili + Regex)
                'payment_sav_context': str,  # Paiement/SAV (Meili)
                'company_context': str,      # Infos entreprise (Meili)
                'semantic_context': str,     # Fallback (Supabase)
                'sources_used': list,
                'has_instant_answer': bool
            }
        """
        fused = {
            'catalog_context': '',
            'delivery_context': '',
            'payment_sav_context': '',
            'company_context': '',
            'semantic_context': '',
            'sources_used': [],
            'has_instant_answer': False
        }
        
        # 1. REGEX INSTANT (priorité maximale)
        regex_data = search_results.get('regex_instant', {})
        if regex_data.get('has_instant_answer'):
            fused['delivery_context'] = regex_data.get('instant_context', '')
            fused['has_instant_answer'] = True
            fused['sources_used'].append('regex')
        
        # 2. GEMINI CACHE (produits)
        gemini_data = search_results.get('gemini_cache', {})
        if gemini_data.get('results') and not gemini_data.get('skipped'):
            fused['catalog_context'] = self._format_catalog_results(gemini_data['results'])
            fused['sources_used'].append('gemini_cache')
        
        # 3. MEILISEARCH (structuré par index)
        meili_data = search_results.get('meilisearch', {})
        meili_context = meili_data.get('context', '')
        if meili_context:
            # Le contexte Meili est déjà formaté par search_all_indexes_parallel
            if keywords.get('has_delivery') and not fused['delivery_context']:
                fused['delivery_context'] = meili_context
            elif keywords.get('has_payment'):
                fused['payment_sav_context'] = meili_context
            elif keywords.get('has_contact'):
                fused['company_context'] = meili_context
            else:
                # Contexte général
                fused['company_context'] = meili_context
            
            fused['sources_used'].append('meilisearch')
        
        # 4. SUPABASE (sémantique fallback)
        supa_data = search_results.get('supabase', {})
        if supa_data.get('results') and not fused['company_context']:
            fused['semantic_context'] = self._format_supabase_results(supa_data['results'])
            fused['sources_used'].append('supabase')
        
        return fused
    
    def _format_catalog_results(self, results: List[Dict]) -> str:
        """Formate les résultats catalogue pour le prompt"""
        if not results:
            return ""
        
        lines = ["📦 PRODUITS TROUVÉS:"]
        for r in results[:5]:
            name = r.get('name', 'Produit')
            price = r.get('price', 'N/A')
            stock = r.get('stock', 'N/A')
            lines.append(f"• {name}: {price} FCFA (Stock: {stock})")
        
        return "\n".join(lines)
    
    def _format_supabase_results(self, results: List[Dict]) -> str:
        """Formate les résultats Supabase pour le prompt"""
        if not results:
            return ""
        
        lines = []
        for r in results[:3]:
            content = r.get('content', r.get('text', ''))
            if content:
                lines.append(content[:500])  # Limiter la taille
        
        return "\n---\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_cache_manager = None

def get_catalog_cache_manager() -> CatalogCacheManager:
    """Retourne l'instance singleton du CatalogCacheManager"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CatalogCacheManager()
    return _cache_manager


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    
    async def test():
        manager = get_catalog_cache_manager()
        
        print("="*60)
        print("🧪 TEST CATALOG CACHE MANAGER")
        print("="*60)
        
        # Test 1: Keywords detection
        test_messages = [
            "C'est combien les couches Molfix taille 4 ?",
            "Livraison à Cocody c'est combien ?",
            "Je peux payer en Wave ?",
            "Vous êtes où à Abidjan ?",
            "Mon numéro c'est 0707070707",
        ]
        
        print("\n📋 TEST 1: KEYWORDS DETECTION")
        print("-"*40)
        for msg in test_messages:
            kw = manager.detect_keywords(msg)
            print(f"Message: {msg}")
            print(f"  → Product: {kw['has_product']}, Delivery: {kw['has_delivery']}")
            print(f"  → Payment: {kw['has_payment']}, Contact: {kw['has_contact']}")
            print(f"  → Priority: {kw['priority_source']}")
            print()
        
        # Test 2: Regex extraction
        print("\n📋 TEST 2: REGEX EXTRACTION")
        print("-"*40)
        test_regex = [
            "Livraison à Yopougon svp",
            "Je suis à Port-Bouët",
            "Mon numéro c'est 0787360757",
            "Appelez-moi au +225 07 07 07 07 07",
            "Livraison Cocody, mon tel: 0505050505",
        ]
        
        for msg in test_regex:
            result = manager.extract_regex_fast(msg)
            print(f"Message: {msg}")
            if result['delivery_zone']:
                z = result['delivery_zone']
                print(f"  → Zone: {z.get('name')} = {z.get('cost')}F")
            if result['phone_number']:
                p = result['phone_number']
                print(f"  → Téléphone: {p['normalized']} ({p['operator']})")
            if result['has_instant_answer']:
                print(f"  → Instant: {result['instant_context']}")
            print()
        
        print("="*60)
        print("✅ TESTS TERMINÉS")
        print("="*60)
    
    asyncio.run(test())

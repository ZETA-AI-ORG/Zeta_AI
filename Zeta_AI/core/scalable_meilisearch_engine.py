"""
🚀 MEILISEARCH ENGINE SCALABLE - MULTI-TENANT OPTIMISÉ
Full-text search pur, config-driven, 1 à 1000 entreprises
"""
import asyncio
import hashlib
import math
import re
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass

import httpx
from unidecode import unidecode

from utils import log3
from .tenant_config_manager import get_tenant_config, SearchConfig


@dataclass
class MeiliSearchResult:
    """Résultat de recherche MeiliSearch enrichi"""
    id: str
    content: str
    score: float
    source_index: str
    metadata: Dict[str, Any]
    match_type: str  # exact, fuzzy, partial
    boost_applied: float


class ScalableMeiliSearchEngine:
    """
    🚀 MOTEUR MEILISEARCH SCALABLE MULTI-TENANT
    
    Fonctionnalités:
    - Configuration par tenant (pas de hardcode)
    - Recherche parallèle multi-index
    - Scoring dynamique configurable
    - N-grams optimisés
    - Cache intelligent
    - Métriques détaillées
    """
    
    def __init__(self, meili_url: str, meili_key: str):
        self.meili_url = meili_url.rstrip('/')
        self.meili_key = meili_key
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Cache des résultats
        self._cache: Dict[str, Tuple[List[MeiliSearchResult], float]] = {}
        self._stats = defaultdict(int)
        
        log3("[MEILI_SCALABLE]", "✅ Moteur MeiliSearch scalable initialisé")
    
    def _normalize_query(self, query: str, config: SearchConfig) -> str:
        """Normalise la requête selon la config tenant"""
        # Normalisation de base
        normalized = unidecode(query.lower().strip())
        
        # Suppression des caractères spéciaux (garde les espaces et chiffres)
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        # Suppression des espaces multiples
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _generate_search_variants(self, query: str, config: SearchConfig) -> List[str]:
        """
        Génère les variantes de recherche optimisées
        
        Stratégies:
        1. Requête exacte
        2. Mots individuels
        3. Bi-grams consécutifs
        4. Inversions numériques (ex: "taille 5" → "5 taille")
        """
        tokens = query.split()
        variants = set()
        
        # 1. Requête exacte (priorité max)
        variants.add(query)
        
        # 2. Mots individuels (pour correspondances partielles)
        for token in tokens:
            if len(token) >= 2:  # Éviter mots trop courts
                variants.add(token)
        
        # 3. Bi-grams consécutifs
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]} {tokens[i+1]}"
            variants.add(bigram)
        
        # 4. Inversions numériques
        for i in range(len(tokens)):
            if tokens[i].isdigit():
                for j in range(len(tokens)):
                    if i != j and not tokens[j].isdigit():
                        # "taille 5" → "5 taille"
                        if i < j:
                            variants.add(f"{tokens[i]} {tokens[j]}")
                        else:
                            variants.add(f"{tokens[j]} {tokens[i]}")
        
        # Limiter le nombre de variantes pour éviter explosion
        return list(variants)[:15]
    
    def _get_company_indexes(self, company_id: str) -> List[str]:
        """Récupère la liste des index pour une entreprise"""
        base_indexes = [
            f"company_docs_{company_id}",
            f"products_{company_id}",
            f"delivery_{company_id}",
            f"support_paiement_{company_id}",
            f"localisation_{company_id}"
        ]
        return base_indexes
    
    async def _search_single_index(
        self,
        index_name: str,
        query: str,
        config: SearchConfig
    ) -> List[Dict[str, Any]]:
        """Recherche sur un seul index"""
        try:
            url = f"{self.meili_url}/indexes/{index_name}/search"
            headers = {"Authorization": f"Bearer {self.meili_key}"}
            
            payload = {
                "q": query,
                "limit": config.meili_max_docs_per_index,
                "attributesToRetrieve": ["*"],
                "showMatchesPosition": True,
                "matchingStrategy": "all"  # Tous les mots doivent matcher
            }
            
            response = await self.client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('hits', [])
            elif response.status_code == 404:
                # Index n'existe pas, normal pour certaines entreprises
                return []
            else:
                log3("[MEILI_SCALABLE]", f"⚠️ Erreur {response.status_code} sur {index_name}")
                return []
                
        except Exception as e:
            log3("[MEILI_SCALABLE]", f"⚠️ Erreur recherche {index_name}: {e}")
            return []
    
    async def _search_parallel(
        self,
        company_id: str,
        variants: List[str],
        config: SearchConfig
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Recherche parallèle sur tous les index"""
        indexes = self._get_company_indexes(company_id)
        tasks = []
        
        # Créer toutes les tâches de recherche
        for index_name in indexes:
            for variant in variants[:8]:  # Limiter à 8 variantes par index
                task = self._search_single_index(index_name, variant, config)
                tasks.append((index_name, variant, task))
        
        # Exécuter en parallèle
        start_time = time.time()
        results = await asyncio.gather(*[task for _, _, task in tasks], return_exceptions=True)
        search_time = (time.time() - start_time) * 1000
        
        # Regrouper par index
        results_by_index = defaultdict(list)
        for i, (index_name, variant, _) in enumerate(tasks):
            if i < len(results) and not isinstance(results[i], Exception):
                for doc in results[i]:
                    doc['_search_variant'] = variant
                    doc['_search_index'] = index_name
                    results_by_index[index_name].append(doc)
        
        log3("[MEILI_SCALABLE]", f"🔍 {len(tasks)} recherches en {search_time:.1f}ms")
        self._stats['total_searches'] += len(tasks)
        self._stats['total_search_time_ms'] += search_time
        
        return dict(results_by_index)
    
    def _compute_dynamic_score(
        self,
        doc: Dict[str, Any],
        query: str,
        variants: List[str],
        config: SearchConfig
    ) -> Tuple[float, str, float]:
        """
        Calcule le score dynamique selon la config tenant
        
        Returns:
            (score, match_type, boost_applied)
        """
        content = doc.get('content', '').lower()
        doc_id = doc.get('id', '').lower()
        variant_used = doc.get('_search_variant', query)
        
        score = 0.0
        match_type = "partial"
        boost_applied = 0.0
        
        # 1. Score de base MeiliSearch
        base_score = doc.get('_rankingScore', 0.0)
        score += base_score
        
        # 2. Bonus correspondance exacte
        query_lower = query.lower()
        if query_lower in content:
            score += config.meili_boost_exact
            match_type = "exact"
            boost_applied += config.meili_boost_exact
        
        # 3. Bonus correspondance fuzzy/partielle
        words_found = sum(1 for word in query.split() if word.lower() in content)
        total_words = len(query.split())
        if words_found > 0:
            partial_ratio = words_found / total_words
            partial_boost = config.meili_boost_fuzzy * partial_ratio * total_words
            score += partial_boost
            boost_applied += partial_boost
            
            if words_found == total_words and match_type != "exact":
                match_type = "fuzzy"
        
        # 4. Boost ID (si la requête match l'ID du document)
        query_normalized = re.sub(r'[^a-z0-9]', '', query_lower)
        if query_normalized and query_normalized in doc_id:
            id_boost = min(config.meili_boost_id, config.meili_boost_id * (len(query_normalized) / len(doc_id)))
            score += id_boost
            boost_applied += id_boost
        
        # 5. Normalisation par longueur du contenu
        content_length = len(content.split())
        if content_length > 0:
            # Pénalité logarithmique pour contenus très longs
            length_penalty = math.log(1 + content_length) * 0.1
            score = score / max(length_penalty, 1.0)
        
        return score, match_type, boost_applied
    
    def _deduplicate_results(self, docs: List[MeiliSearchResult]) -> List[MeiliSearchResult]:
        """Déduplication intelligente basée sur le contenu"""
        seen_hashes = set()
        unique_docs = []
        
        for doc in docs:
            # Hash basé sur les 100 premiers caractères + longueur
            content_sample = doc.content[:100].lower()
            content_hash = hashlib.md5(f"{content_sample}_{len(doc.content)}".encode()).hexdigest()
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_docs.append(doc)
            else:
                # Garder si score significativement différent
                existing = next((d for d in unique_docs if hashlib.md5(f"{d.content[:100].lower()}_{len(d.content)}".encode()).hexdigest() == content_hash), None)
                if existing and abs(doc.score - existing.score) > 0.2 * existing.score:
                    unique_docs.append(doc)
        
        return unique_docs
    
    def _apply_index_weights(self, docs: List[MeiliSearchResult], config: SearchConfig) -> List[MeiliSearchResult]:
        """Applique les poids par type d'index"""
        index_weights = {
            "products": 1.0,      # Priorité max pour produits
            "company_docs": 0.9,  # Documents généraux
            "delivery": 0.8,      # Livraison
            "support_paiement": 0.7,  # Support
            "localisation": 0.6   # Localisation
        }
        
        for doc in docs:
            # Extraire le type d'index
            index_type = "company_docs"  # défaut
            for idx_type in index_weights.keys():
                if idx_type in doc.source_index:
                    index_type = idx_type
                    break
            
            # Appliquer le poids
            weight = index_weights.get(index_type, 1.0)
            doc.score *= weight
        
        return docs
    
    async def search(
        self,
        query: str,
        company_id: str,
        use_cache: bool = True
    ) -> List[MeiliSearchResult]:
        """
        Point d'entrée principal pour la recherche
        
        Args:
            query: Requête de recherche
            company_id: ID de l'entreprise
            use_cache: Utiliser le cache ou non
            
        Returns:
            Liste des résultats triés par score
        """
        start_time = time.time()
        
        # 1. Récupérer la configuration du tenant
        config = get_tenant_config(company_id).search
        
        # 2. Vérifier le cache
        cache_key = f"{company_id}:{hashlib.md5(query.encode()).hexdigest()}"
        if use_cache and config.cache_enabled and cache_key in self._cache:
            cached_results, timestamp = self._cache[cache_key]
            if time.time() - timestamp < config.cache_ttl_seconds:
                log3("[MEILI_SCALABLE]", f"✅ Cache hit pour {company_id}")
                self._stats['cache_hits'] += 1
                return cached_results
        
        # 3. Normaliser la requête
        normalized_query = self._normalize_query(query, config)
        if not normalized_query:
            return []
        
        # 4. Générer les variantes de recherche
        variants = self._generate_search_variants(normalized_query, config)
        
        # 5. Recherche parallèle
        results_by_index = await self._search_parallel(company_id, variants, config)
        
        # 6. Fusion et scoring
        all_results = []
        for index_name, docs in results_by_index.items():
            for doc in docs:
                score, match_type, boost = self._compute_dynamic_score(
                    doc, normalized_query, variants, config
                )
                
                result = MeiliSearchResult(
                    id=doc.get('id', ''),
                    content=doc.get('content', ''),
                    score=score,
                    source_index=index_name,
                    metadata=doc,
                    match_type=match_type,
                    boost_applied=boost
                )
                all_results.append(result)
        
        # 7. Déduplication
        all_results = self._deduplicate_results(all_results)
        
        # 8. Appliquer poids par index
        all_results = self._apply_index_weights(all_results, config)
        
        # 9. Tri par score décroissant
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # 10. Limitation finale
        all_results = all_results[:config.meili_max_total_docs]
        
        # 11. Mise en cache
        if config.cache_enabled:
            self._cache[cache_key] = (all_results, time.time())
            # Nettoyage du cache si trop gros
            if len(self._cache) > config.cache_max_entries:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
        
        # 12. Métriques
        total_time = (time.time() - start_time) * 1000
        self._stats['total_queries'] += 1
        self._stats['total_query_time_ms'] += total_time
        
        log3("[MEILI_SCALABLE]", f"✅ {len(all_results)} docs trouvés en {total_time:.1f}ms")
        
        return all_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du moteur"""
        stats = dict(self._stats)
        
        if stats.get('total_queries', 0) > 0:
            stats['avg_query_time_ms'] = stats['total_query_time_ms'] / stats['total_queries']
        
        if stats.get('total_searches', 0) > 0:
            stats['avg_search_time_ms'] = stats['total_search_time_ms'] / stats['total_searches']
        
        stats['cache_hit_rate'] = stats.get('cache_hits', 0) / max(stats.get('total_queries', 1), 1)
        stats['cache_size'] = len(self._cache)
        
        return stats
    
    def clear_cache(self, company_id: Optional[str] = None):
        """Vide le cache (optionnellement pour une entreprise spécifique)"""
        if company_id:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{company_id}:")]
            for key in keys_to_remove:
                del self._cache[key]
            log3("[MEILI_SCALABLE]", f"✅ Cache vidé pour {company_id}")
        else:
            self._cache.clear()
            log3("[MEILI_SCALABLE]", "✅ Cache complet vidé")


# Instance globale
_meili_engine: Optional[ScalableMeiliSearchEngine] = None

def get_meilisearch_engine() -> ScalableMeiliSearchEngine:
    """Récupère l'instance globale du moteur MeiliSearch"""
    global _meili_engine
    if _meili_engine is None:
        import os
        meili_url = os.getenv("MEILISEARCH_URL", "http://localhost:7700")
        meili_key = os.getenv("MEILISEARCH_MASTER_KEY", "")
        _meili_engine = ScalableMeiliSearchEngine(meili_url, meili_key)
    return _meili_engine

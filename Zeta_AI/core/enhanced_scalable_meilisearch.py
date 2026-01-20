"""
🔥 ENHANCED SCALABLE MEILISEARCH - INTÉGRATION SYSTÈME EXISTANT
Combine le meilleur de ton système actuel + scalabilité multi-tenant
"""
import asyncio
import hashlib
import math
import re
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from itertools import combinations

import httpx
from unidecode import unidecode

from utils import log3
from .tenant_config_manager import get_tenant_config, SearchConfig

# Import TES stop words (800+)
from .smart_stopwords import filter_query_for_meilisearch, STOP_WORDS_ECOMMERCE, KEEP_WORDS_ECOMMERCE
from .custom_stopwords import CUSTOM_STOP_WORDS


@dataclass
class EnhancedMeiliResult:
    """Résultat enrichi avec ton système de scoring"""
    id: str
    content: str
    score: float
    source_index: str
    metadata: Dict[str, Any]
    match_type: str
    boost_applied: float
    ngrams_matched: List[str]
    id_match_bonus: float


class EnhancedScalableMeiliSearch:
    """
    🔥 MOTEUR MEILISEARCH AMÉLIORÉ
    
    Intègre TON système existant:
    - 800+ stop words
    - N-grams puissance 3 avec toutes combinaisons
    - Bonus ID conséquent
    - Recherche multi-index parallèle
    - Filtrage intelligent des docs
    - Extraction des données par doc
    
    + Scalabilité multi-tenant
    """
    
    def __init__(self, meili_url: str, meili_key: str):
        self.meili_url = meili_url.rstrip('/')
        self.meili_key = meili_key
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Cache des résultats
        self._cache: Dict[str, Tuple[List[EnhancedMeiliResult], float]] = {}
        self._stats = defaultdict(int)
        
        # Fusion des stop words (TON SYSTÈME)
        self.stop_words = (set(STOP_WORDS_ECOMMERCE) | CUSTOM_STOP_WORDS) - set(KEEP_WORDS_ECOMMERCE)
        
        log3("[MEILI_ENHANCED]", f"✅ Moteur MeiliSearch amélioré initialisé ({len(self.stop_words)} stop words)")
    
    def _normalize_with_your_system(self, query: str) -> str:
        """Utilise TON système de normalisation (800+ stop words)"""
        # Utiliser ta fonction existante
        normalized = filter_query_for_meilisearch(query)
        return normalized
    
    def _generate_ngrams_power3(self, query: str) -> List[str]:
        """
        Génère les N-grams PUISSANCE 3 (TON SYSTÈME)
        
        Stratégies:
        1. N-grams consécutifs 1-3 mots
        2. N-grams non-consécutifs (combinaisons)
        3. Inversions numériques
        4. Gestion spéciale "à" dans tri-grams
        """
        words = query.strip().split()
        
        # Filtrer stop words (sauf dans certains contextes)
        filtered_words = []
        liaison_words = {"à", "a", "de", "pour"}
        
        for i, word in enumerate(words):
            word_lower = word.lower()
            
            # Garder les mots de liaison SEULEMENT s'ils sont entre 2 autres mots
            if word_lower in liaison_words:
                if 0 < i < len(words) - 1:  # Entre 2 mots
                    filtered_words.append(word)
            elif word_lower not in self.stop_words:
                filtered_words.append(word)
        
        words = filtered_words
        ngrams = set()
        
        # === 1. N-GRAMS CONSÉCUTIFS (1-3 mots) ===
        for n in range(3, 0, -1):  # 3, 2, 1
            for i in range(len(words) - n + 1):
                ngram_words = words[i:i+n]
                ngram = " ".join(ngram_words)
                ngrams.add(ngram)
                
                # Inversions numériques pour n=2
                if n == 2 and any(w.isdigit() for w in ngram_words):
                    reversed_ngram = " ".join(reversed(ngram_words))
                    ngrams.add(reversed_ngram)
        
        # === 2. N-GRAMS NON-CONSÉCUTIFS (COMBINAISONS) ===
        # Pour capturer "lot couches" même si "300" est entre les deux
        if len(words) >= 3:
            # Bi-grams non-consécutifs
            for combo in combinations(range(len(words)), 2):
                i, j = combo
                if j - i <= 3:  # Max 3 mots d'écart
                    ngram = f"{words[i]} {words[j]}"
                    ngrams.add(ngram)
            
            # Tri-grams non-consécutifs (sélectifs)
            for combo in combinations(range(len(words)), 3):
                i, j, k = combo
                if k - i <= 4:  # Max 4 mots d'écart
                    ngram = f"{words[i]} {words[j]} {words[k]}"
                    ngrams.add(ngram)
        
        # === 3. INVERSIONS NUMÉRIQUES AVANCÉES ===
        for i, word in enumerate(words):
            if word.isdigit():
                # Chercher les mots autour
                for j in range(max(0, i-2), min(len(words), i+3)):
                    if i != j and not words[j].isdigit():
                        # "lot 300" et "300 lot"
                        if i < j:
                            ngrams.add(f"{word} {words[j]}")
                        else:
                            ngrams.add(f"{words[j]} {word}")
        
        # Trier par longueur décroissante (priorité aux n-grams longs)
        sorted_ngrams = sorted(ngrams, key=lambda x: (-len(x.split()), x))
        
        # Limiter pour éviter explosion (mais garder plus que l'ancien système)
        return sorted_ngrams[:25]  # Au lieu de 15
    
    def _get_company_indexes(self, company_id: str) -> List[str]:
        """Récupère TOUS les index d'une entreprise"""
        base_indexes = [
            f"company_docs_{company_id}",
            f"products_{company_id}",
            f"delivery_{company_id}",
            f"support_paiement_{company_id}",
            f"localisation_{company_id}",
            f"faq_{company_id}",  # Ajout d'index supplémentaires
            f"catalog_{company_id}"
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
                "matchingStrategy": "all"
            }
            
            response = await self.client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('hits', [])
            elif response.status_code == 404:
                return []
            else:
                return []
                
        except Exception as e:
            log3("[MEILI_ENHANCED]", f"⚠️ Erreur {index_name}: {e}")
            return []
    
    async def _search_parallel_all_ngrams(
        self,
        company_id: str,
        ngrams: List[str],
        config: SearchConfig
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Recherche parallèle TOUS les n-grams sur TOUS les index
        (TON SYSTÈME: pas d'early exit)
        """
        indexes = self._get_company_indexes(company_id)
        tasks = []
        
        # Créer TOUTES les tâches (index x ngrams)
        for index_name in indexes:
            for ngram in ngrams:  # TOUS les n-grams
                task = self._search_single_index(index_name, ngram, config)
                tasks.append((index_name, ngram, task))
        
        # Exécution parallèle COMPLÈTE
        start_time = time.time()
        results = await asyncio.gather(*[task for _, _, task in tasks], return_exceptions=True)
        search_time = (time.time() - start_time) * 1000
        
        # Regrouper par index
        results_by_index = defaultdict(list)
        for i, (index_name, ngram, _) in enumerate(tasks):
            if i < len(results) and not isinstance(results[i], Exception):
                for doc in results[i]:
                    doc['_search_ngram'] = ngram
                    doc['_search_index'] = index_name
                    results_by_index[index_name].append(doc)
        
        log3("[MEILI_ENHANCED]", f"🔍 {len(tasks)} recherches en {search_time:.1f}ms")
        self._stats['total_searches'] += len(tasks)
        
        return dict(results_by_index)
    
    def _compute_enhanced_score(
        self,
        doc: Dict[str, Any],
        ngrams: List[str],
        query: str,
        config: SearchConfig
    ) -> Tuple[float, str, float, List[str], float]:
        """
        Scoring AMÉLIORÉ avec TON SYSTÈME
        
        Returns:
            (score, match_type, boost_applied, ngrams_matched, id_bonus)
        """
        content = doc.get('content', '').lower()
        doc_id = doc.get('id', '').lower()
        ngram_used = doc.get('_search_ngram', query)
        
        score = 0.0
        match_type = "partial"
        boost_applied = 0.0
        ngrams_matched = []
        id_bonus = 0.0
        
        # 1. Score de base MeiliSearch
        base_score = doc.get('_rankingScore', 0.0)
        score += base_score
        
        # 2. Matches n-grams (TOUS)
        for ng in ngrams:
            ng_lower = ng.lower()
            word_count = len(ng.split())
            
            # Match exact dans content
            if ng_lower in content:
                ngrams_matched.append(ng)
                exact_boost = config.meili_boost_exact * word_count
                score += exact_boost
                boost_applied += exact_boost
                match_type = "exact"
            
            # Match partiel
            elif any(word in content for word in ng.split()):
                partial_boost = config.meili_boost_fuzzy * word_count * 0.5
                score += partial_boost
                boost_applied += partial_boost
        
        # 3. BONUS ID CONSÉQUENT (TON SYSTÈME)
        # Si n-grams trouvés dans l'ID → GROS BONUS
        for ng in ngrams:
            ng_norm = re.sub(r'[^a-z0-9]', '', ng.lower())
            if ng_norm and ng_norm in doc_id:
                # Bonus proportionnel à la longueur du match
                match_ratio = len(ng_norm) / max(len(doc_id), 1)
                id_boost = config.meili_boost_id * match_ratio * 2  # x2 car très important
                score += id_boost
                id_bonus += id_boost
                boost_applied += id_boost
                
                log3("[MEILI_ENHANCED]", f"🎯 ID match: '{ng}' in '{doc_id}' → +{id_boost:.1f}")
        
        # 4. Company keywords
        config_tenant = get_tenant_config(doc.get('company_id', ''))
        if config_tenant and config_tenant.business.company_keywords:
            keywords_found = sum(
                1 for kw in config_tenant.business.company_keywords 
                if kw.lower() in content
            )
            if keywords_found > 0:
                score *= (1 + 0.1 * keywords_found)  # +10% par keyword
        
        # 5. Normalisation par longueur
        if config.normalize_by_length:
            content_len = len(content.split())
            penalty = math.log(1 + content_len) * 0.1
            score = score / max(penalty, 1.0)
        
        return score, match_type, boost_applied, ngrams_matched, id_bonus
    
    def _filter_docs_intelligent(
        self,
        docs: List[EnhancedMeiliResult],
        query: str,
        config: SearchConfig
    ) -> List[EnhancedMeiliResult]:
        """
        Filtrage intelligent des docs (TON SYSTÈME)
        
        Critères:
        - Score minimum
        - Au moins 1 n-gram matché
        - Pertinence du contenu
        """
        filtered = []
        
        for doc in docs:
            # Critère 1: Score minimum
            if doc.score < 1.0:
                continue
            
            # Critère 2: Au moins 1 n-gram matché
            if not doc.ngrams_matched:
                continue
            
            # Critère 3: Contenu pertinent (pas trop court)
            if len(doc.content) < 10:
                continue
            
            filtered.append(doc)
        
        return filtered
    
    def _extract_data_from_docs(
        self,
        docs: List[EnhancedMeiliResult]
    ) -> List[EnhancedMeiliResult]:
        """
        Extraction des données clés de chaque doc (TON SYSTÈME)
        
        Extrait:
        - Prix
        - Quantités
        - Tailles
        - Disponibilité
        """
        for doc in docs:
            metadata = doc.metadata
            content = doc.content.lower()
            
            # Extraction prix
            prix_match = re.search(r'(\d+[\s,.]?\d*)\s*(fcfa|franc|€|euro)', content)
            if prix_match:
                metadata['prix_extrait'] = prix_match.group(1)
                metadata['devise'] = prix_match.group(2)
            
            # Extraction quantité/lot
            lot_match = re.search(r'lot\s+(?:de\s+)?(\d+)|(\d+)\s+(?:pièces?|unités?)', content)
            if lot_match:
                metadata['quantite'] = lot_match.group(1) or lot_match.group(2)
            
            # Extraction taille
            taille_match = re.search(r'taille\s+(\d+|[a-z]+)', content)
            if taille_match:
                metadata['taille'] = taille_match.group(1)
            
            # Disponibilité
            if any(word in content for word in ['disponible', 'en stock', 'stock']):
                metadata['disponible'] = True
            elif any(word in content for word in ['rupture', 'épuisé', 'indisponible']):
                metadata['disponible'] = False
        
        return docs
    
    def _deduplicate_advanced(self, docs: List[EnhancedMeiliResult]) -> List[EnhancedMeiliResult]:
        """Déduplication avancée (TON SYSTÈME)"""
        seen_hashes = {}
        unique_docs = []
        
        for doc in docs:
            # Hash sur content + ID
            content_sample = doc.content[:100].lower()
            doc_id_sample = doc.id[:50].lower()
            key = hashlib.md5(f"{content_sample}_{doc_id_sample}".encode()).hexdigest()
            
            if key not in seen_hashes:
                seen_hashes[key] = doc
                unique_docs.append(doc)
            else:
                # Garder si score significativement meilleur
                existing = seen_hashes[key]
                if doc.score > existing.score * 1.2:  # 20% meilleur
                    unique_docs.remove(existing)
                    unique_docs.append(doc)
                    seen_hashes[key] = doc
        
        return unique_docs
    
    async def search(
        self,
        query: str,
        company_id: str,
        use_cache: bool = True
    ) -> List[EnhancedMeiliResult]:
        """
        Point d'entrée principal - SYSTÈME AMÉLIORÉ
        
        Pipeline:
        1. Normalisation (800+ stop words)
        2. N-grams puissance 3
        3. Recherche parallèle complète
        4. Scoring avec bonus ID conséquent
        5. Filtrage intelligent
        6. Extraction données
        7. Déduplication avancée
        """
        start_time = time.time()
        
        # 1. Config tenant
        config = get_tenant_config(company_id).search
        
        # 2. Cache check
        cache_key = f"{company_id}:{hashlib.md5(query.encode()).hexdigest()}"
        if use_cache and config.cache_enabled and cache_key in self._cache:
            cached_results, timestamp = self._cache[cache_key]
            if time.time() - timestamp < config.cache_ttl_seconds:
                log3("[MEILI_ENHANCED]", f"✅ Cache hit")
                self._stats['cache_hits'] += 1
                return cached_results
        
        # 3. Normalisation (TON SYSTÈME: 800+ stop words)
        normalized = self._normalize_with_your_system(query)
        if not normalized:
            return []
        
        log3("[MEILI_ENHANCED]", f"📝 '{query}' → '{normalized}'")
        
        # 4. N-grams PUISSANCE 3 (TON SYSTÈME)
        ngrams = self._generate_ngrams_power3(normalized)
        log3("[MEILI_ENHANCED]", f"🔤 {len(ngrams)} n-grams générés")
        
        # 5. Recherche parallèle COMPLÈTE (TON SYSTÈME: pas d'early exit)
        results_by_index = await self._search_parallel_all_ngrams(
            company_id, ngrams, config
        )
        
        # 6. Scoring avec BONUS ID CONSÉQUENT (TON SYSTÈME)
        all_results = []
        for index_name, docs in results_by_index.items():
            for doc in docs:
                score, match_type, boost, ngrams_matched, id_bonus = self._compute_enhanced_score(
                    doc, ngrams, query, config
                )
                
                # Appliquer index weight
                index_type = index_name.split('_')[0]
                index_weights = {
                    "products": 1.2,  # Boost produits
                    "company": 1.0,
                    "delivery": 0.8,
                    "support": 0.7,
                    "localisation": 0.6
                }
                score *= index_weights.get(index_type, 1.0)
                
                result = EnhancedMeiliResult(
                    id=doc.get('id', ''),
                    content=doc.get('content', ''),
                    score=score,
                    source_index=index_name,
                    metadata=doc,
                    match_type=match_type,
                    boost_applied=boost,
                    ngrams_matched=ngrams_matched,
                    id_match_bonus=id_bonus
                )
                all_results.append(result)
        
        # 7. Filtrage intelligent (TON SYSTÈME)
        all_results = self._filter_docs_intelligent(all_results, query, config)
        
        # 8. Extraction données (TON SYSTÈME)
        all_results = self._extract_data_from_docs(all_results)
        
        # 9. Déduplication avancée (TON SYSTÈME)
        all_results = self._deduplicate_advanced(all_results)
        
        # 10. Tri par score décroissant
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # 11. Limitation finale
        all_results = all_results[:config.meili_max_total_docs]
        
        # 12. Cache
        if config.cache_enabled:
            self._cache[cache_key] = (all_results, time.time())
        
        # 13. Métriques
        total_time = (time.time() - start_time) * 1000
        self._stats['total_queries'] += 1
        
        log3("[MEILI_ENHANCED]", f"✅ {len(all_results)} docs en {total_time:.1f}ms")
        
        return all_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Statistiques détaillées"""
        stats = dict(self._stats)
        stats['stop_words_count'] = len(self.stop_words)
        stats['cache_size'] = len(self._cache)
        return stats


# Instance globale
_enhanced_meili: Optional[EnhancedScalableMeiliSearch] = None

def get_enhanced_meilisearch() -> EnhancedScalableMeiliSearch:
    """Récupère l'instance globale"""
    global _enhanced_meili
    if _enhanced_meili is None:
        import os
        meili_url = os.getenv("MEILISEARCH_URL", "http://localhost:7700")
        meili_key = os.getenv("MEILISEARCH_MASTER_KEY", "")
        _enhanced_meili = EnhancedScalableMeiliSearch(meili_url, meili_key)
    return _enhanced_meili

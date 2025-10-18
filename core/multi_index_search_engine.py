#!/usr/bin/env python3
"""
🎯 MOTEUR DE RECHERCHE MULTI-INDEX MEILISEARCH
Recherche intelligente sur les 5 index spécialisés avec priorisation du searchable_text
Intègre HyDE scoring et optimisations adaptatives
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
import logging
import traceback
import time
from core.ingestion_hyde_analyzer import IngestionHydeAnalyzer
from utils import log3

def log_search(message, data=None):
    """Log formaté pour la recherche"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[MULTI_SEARCH][{timestamp}] {message}")
    if data:
        print(f"  📊 {json.dumps(data, indent=2, ensure_ascii=False)}")

class MultiIndexSearchEngine:
    """
    Moteur de recherche multi-index avec priorisation searchable_text
    """
    
    def __init__(self):
        self.meili_url = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
        self.meili_key = os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
        self.headers = {"Authorization": f"Bearer {self.meili_key}", "Content-Type": "application/json"}
        
        # Analyseur HyDE pour les scores
        self.hyde_analyzer = IngestionHydeAnalyzer()
        
        # Configuration des index avec priorisation searchable_text
        self.index_config = {
            "products": {
                "weight": 1.0,
                "search_attributes": ["searchable_text^10", "product_name^5", "category^3", "subcategory^2", "content_fr"],
                "keywords": ["produit", "prix", "stock", "couleur", "taille", "modèle", "marque", "casque", "moto"]
            },
            "delivery": {
                "weight": 1.0, 
                "search_attributes": ["searchable_text^10", "zone^5", "city^4", "content_fr^2"],
                "keywords": ["livraison", "zone", "prix", "délai", "transport", "yopougon", "abidjan", "cocody"]
            },
            "support_paiement": {
                "weight": 1.0,
                "search_attributes": ["searchable_text^10", "method^5", "phone_display^4", "content_fr^2"],
                "keywords": ["paiement", "support", "contact", "téléphone", "wave", "cod", "whatsapp", "aide"]
            },
            "localisation": {
                "weight": 0.8,
                "search_attributes": ["searchable_text^10", "store_type^3", "activity_zone^4", "content_fr^2"],
                "keywords": ["boutique", "magasin", "adresse", "zone", "activité", "localisation", "online"]
            },
            "company_docs": {
                "weight": 0.9,
                "search_attributes": ["searchable_text^10", "content^3", "content_fr^2"],
                "keywords": []  # Recherche globale
            }
        }

    async def search_multi_index(self, 
                                company_id: str, 
                                query: str, 
                                limit: int = 10,
                                smart_routing: bool = True) -> Dict[str, Any]:
        """
        Recherche intelligente multi-index avec priorisation searchable_text
        """
        log_search(f"🔍 RECHERCHE MULTI-INDEX", {
            "company_id": company_id,
            "query": query,
            "limit": limit,
            "smart_routing": smart_routing
        })
        
        # Déterminer les index à interroger
        target_indexes = self._determine_target_indexes(query) if smart_routing else list(self.index_config.keys())
        
        # Rechercher dans chaque index
        all_results = []
        search_stats = {}
        
        for index_name in target_indexes:
            index_uid = f"{index_name}_{company_id}"
            
            try:
                # Configuration de recherche minimale compatible versions anciennes
                search_config = {
                    "query": query  # Configuration minimale pour compatibilité maximale
                }
                
                log3("[MEILI_SEARCH_CONFIG]", {
                    "index_uid": index_uid,
                    "search_config": search_config,
                    "query_length": len(query)
                })
                
                # Recherche dans l'index avec mesure de performance
                search_start = time.time()
                search_data = {"q": search_config.get("query", ""), "limit": limit}
                response = requests.post(f"{self.meili_url}/indexes/{index_uid}/search", headers=self.headers, json=search_data, timeout=30)
                results = response.json() if response.status_code == 200 else {"hits": [], "estimatedTotalHits": 0}
                search_time = (time.time() - search_start) * 1000
                
                log3("[MEILI_SEARCH_PERFORMANCE]", {
                    "index_name": index_name,
                    "search_time_ms": f"{search_time:.2f}",
                    "results_count": len(results.get("hits", [])),
                    "processing_time_ms": results.get("processingTimeMs", "N/A")
                })
                
                # Tronquer les résultats si pas de limite supportée par MeiliSearch
                hits = results.get("hits", [])
                if len(hits) > limit * 2:
                    hits = hits[:limit * 2]
                
                # Enrichir les résultats avec scores HyDE
                enriched_hits = self._apply_hyde_scoring(
                    hits, 
                    query, 
                    company_id, 
                    index_name
                )
                
                all_results.extend(enriched_hits)
                search_stats[index_name] = {
                    "hits_count": len(results.get("hits", [])),
                    "processing_time": results.get("processingTimeMs", 0)
                }
                
                log_search(f"✅ {index_name}: {len(enriched_hits)} résultats")
                
            except Exception as e:
                # Gérer spécifiquement l'erreur index_not_found
                if "index_not_found" in str(e) or "index_uid_not_found" in str(e):
                    log3("[MEILI_INDEX_NOT_FOUND]", {
                        "index_name": index_name,
                        "index_uid": index_uid,
                        "message": f"Index {index_uid} n'existe pas - Ignoré gracieusement"
                    })
                    search_stats[index_name] = {"error": "index_not_found", "results": 0, "ignored": True}
                    continue
                
                log3("[ERROR_MEILI_INDEX]", {
                    "index_name": index_name,
                    "index_uid": index_uid,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                    "search_config": search_config,
                    "meilisearch_version": getattr(meilisearch, '__version__', 'unknown')
                })
                search_stats[index_name] = {"error": str(e), "results": 0}
        
        # Reranking global avec scores combinés
        final_results = self._global_rerank(all_results, query, limit)
        
        return {
            "results": final_results,
            "total_hits": len(all_results),
            "returned_hits": len(final_results),
            "search_stats": search_stats,
            "indexes_searched": target_indexes,
            "query": query
        }

    def _determine_target_indexes(self, query: str) -> List[str]:
        """
        Détermine intelligemment quels index interroger selon la requête
        """
        query_lower = query.lower()
        target_indexes = []
        
        # Analyser les mots-clés de la requête
        for index_name, config in self.index_config.items():
            keywords = config["keywords"]
            
            # Vérifier si des mots-clés correspondent
            if any(keyword in query_lower for keyword in keywords):
                target_indexes.append(index_name)
        
        # Si aucun index spécifique détecté, rechercher dans tous
        if not target_indexes:
            target_indexes = ["company_docs", "products", "delivery", "support_paiement"]
        
        # Toujours inclure company_docs pour la recherche globale
        if "company_docs" not in target_indexes:
            target_indexes.append("company_docs")
        
        log_search(f"🎯 INDEX CIBLÉS", {"query": query, "indexes": target_indexes})
        
        return target_indexes

    def _apply_hyde_scoring(self, 
                           hits: List[Dict], 
                           query: str, 
                           company_id: str, 
                           index_name: str) -> List[Dict]:
        """
        Applique le scoring HyDE aux résultats avec boost searchable_text
        """
        enriched_hits = []
        
        for hit in hits:
            # Score MeiliSearch de base
            meili_score = hit.get("_rankingScore", 0.0)
            
            # Boost si match dans searchable_text (priorité absolue)
            searchable_text = hit.get("searchable_text", "")
            searchable_boost = 0.0
            
            if searchable_text and any(word.lower() in searchable_text.lower() for word in query.split()):
                searchable_boost = 2.0  # Boost majeur pour searchable_text
                log_search(f"🎯 BOOST SEARCHABLE_TEXT", {"doc_id": hit.get("id"), "boost": searchable_boost})
            
            # Score HyDE des mots de la requête
            hyde_score = self._calculate_hyde_score(query, company_id)
            
            # Score de l'index (selon importance)
            index_weight = self.index_config[index_name]["weight"]
            
            # Score final combiné
            final_score = (meili_score * index_weight) + searchable_boost + (hyde_score * 0.1)
            
            # Enrichir le hit
            enriched_hit = {
                **hit,
                "search_score": final_score,
                "meili_score": meili_score,
                "hyde_score": hyde_score,
                "searchable_boost": searchable_boost,
                "index_source": index_name,
                "index_weight": index_weight
            }
            
            enriched_hits.append(enriched_hit)
        
        return enriched_hits

    def _calculate_hyde_score(self, query: str, company_id: str) -> float:
        """
        Calcule le score HyDE pour une requête
        """
        try:
            words = query.lower().split()
            total_score = 0.0
            scored_words = 0
            
            for word in words:
                word_score = self.hyde_analyzer.get_word_score(word, company_id)
                if word_score is not None:
                    total_score += word_score
                    scored_words += 1
            
            return total_score / max(scored_words, 1) if scored_words > 0 else 5.0
            
        except Exception as e:
            log_search(f"⚠️ Erreur calcul HyDE: {e}")
            return 5.0

    def _global_rerank(self, results: List[Dict], query: str, limit: int) -> List[Dict]:
        """
        Reranking global des résultats avec priorisation searchable_text
        """
        # Trier par score final décroissant
        sorted_results = sorted(results, key=lambda x: x.get("search_score", 0), reverse=True)
        
        # Appliquer une déduplication intelligente
        seen_ids = set()
        deduplicated = []
        
        for result in sorted_results:
            doc_id = result.get("id")
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                deduplicated.append(result)
        
        # Retourner les meilleurs résultats
        final_results = deduplicated[:limit]
        
        log_search(f"🏆 RERANKING FINAL", {
            "total_before": len(results),
            "after_dedup": len(deduplicated),
            "final_returned": len(final_results),
            "top_scores": [r.get("search_score", 0) for r in final_results[:3]]
        })
        
        return final_results

    async def search_specific_index(self, 
                                   company_id: str, 
                                   index_name: str, 
                                   query: str, 
                                   limit: int = 10) -> Dict[str, Any]:
        """
        Recherche dans un index spécifique avec priorisation searchable_text
        """
        index_uid = f"{index_name}_{company_id}"
        
        try:
            search_config = {
                "query": query,  # CORRECTION: 'query' au lieu de 'q'
                "limit": limit,
                "attributesToSearchOn": self.index_config[index_name]["search_attributes"],
                "attributesToHighlight": ["searchable_text", "content_fr"],
                "showMatchesPosition": True
            }
            
            log3("[MEILI_SINGLE_SEARCH_CONFIG]", {
                "index_uid": index_uid,
                "search_config": search_config
            })
            
            search_start = time.time()
            results = self.meili_client.index(index_uid).search(**search_config)
            search_time = (time.time() - search_start) * 1000
            
            log3("[MEILI_SINGLE_PERFORMANCE]", {
                "index_name": index_name,
                "search_time_ms": f"{search_time:.2f}",
                "results_count": len(results.get("hits", []))
            })
            
            # Enrichir avec scores HyDE
            enriched_hits = self._apply_hyde_scoring(
                results.get("hits", []), 
                query, 
                company_id, 
                index_name
            )
            
            return {
                "results": enriched_hits,
                "total_hits": len(enriched_hits),
                "processing_time": results.get("processingTimeMs", 0),
                "index": index_name
            }
            
        except Exception as e:
            log3("[ERROR_MEILI_SINGLE]", {
                "index_name": index_name,
                "index_uid": index_uid,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc(),
                "search_config": search_config
            })
            return {"hits": [], "error": str(e)}

# Fonction utilitaire pour l'intégration
async def search_company_multi_index(company_id: str, 
                                   query: str, 
                                   limit: int = 10,
                                   smart_routing: bool = True) -> Dict[str, Any]:
    """
    Fonction principale de recherche multi-index
    """
    engine = MultiIndexSearchEngine()
    return await engine.search_multi_index(company_id, query, limit, smart_routing)

if __name__ == "__main__":
    print("🎯 MOTEUR DE RECHERCHE MULTI-INDEX")
    print("=" * 50)
    print("Utilisation: from core.multi_index_search_engine import search_company_multi_index")

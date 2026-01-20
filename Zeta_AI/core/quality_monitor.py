"""
🎯 QUALITY MONITOR - Monitoring qualité temps réel
==================================================

✅ AMÉLIORATION 9: Dashboard métriques qualité
Impact: Visibilité problèmes + amélioration continue

Métriques trackées:
- Taux extraction réussie
- Score pertinence moyen
- Temps réponse P50/P95
- Taux cache hit
- Taux ambiguïté détectée
"""

import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque
import statistics


class QualityMonitor:
    """
    Moniteur qualité système RAG
    Stocke métriques en mémoire (rolling window 1h)
    """
    
    def __init__(self, window_minutes: int = 60):
        self.window_minutes = window_minutes
        self.window_seconds = window_minutes * 60
        
        # Métriques (timestamp, value)
        self.response_times: deque = deque(maxlen=1000)
        self.extraction_success: deque = deque(maxlen=1000)
        self.relevance_scores: deque = deque(maxlen=1000)
        self.cache_hits: deque = deque(maxlen=1000)
        self.ambiguity_detected: deque = deque(maxlen=1000)
        self.docs_filtered: deque = deque(maxlen=1000)
        
        self.start_time = time.time()
    
    def record_response_time(self, duration_ms: float):
        """Enregistre temps de réponse"""
        self.response_times.append((time.time(), duration_ms))
    
    def record_extraction(self, success: bool, reduction_pct: float = 0):
        """Enregistre succès extraction"""
        self.extraction_success.append((time.time(), {
            'success': success,
            'reduction': reduction_pct
        }))
    
    def record_relevance(self, score: float):
        """Enregistre score pertinence document"""
        self.relevance_scores.append((time.time(), score))
    
    def record_cache_hit(self, hit: bool, cache_type: str = "semantic"):
        """Enregistre cache hit/miss"""
        self.cache_hits.append((time.time(), {
            'hit': hit,
            'type': cache_type
        }))
    
    def record_ambiguity(self, detected: bool, ambiguity_type: str = ""):
        """Enregistre détection ambiguïté"""
        self.ambiguity_detected.append((time.time(), {
            'detected': detected,
            'type': ambiguity_type
        }))
    
    def record_filtering(self, docs_before: int, docs_after: int):
        """Enregistre filtrage documents"""
        self.docs_filtered.append((time.time(), {
            'before': docs_before,
            'after': docs_after,
            'filtered': docs_before - docs_after
        }))
    
    def _filter_recent(self, data: deque) -> List:
        """Filtre données récentes (window)"""
        cutoff = time.time() - self.window_seconds
        return [(ts, val) for ts, val in data if ts >= cutoff]
    
    def get_metrics(self) -> Dict:
        """
        Retourne métriques actuelles
        
        Returns:
            {
                'response_time': {'p50': 5.2, 'p95': 12.1, 'avg': 7.3},
                'extraction': {'success_rate': 0.95, 'avg_reduction': 34.2},
                'relevance': {'avg_score': 0.68, 'min': 0.35, 'max': 0.92},
                'cache': {'hit_rate': 0.42, 'semantic': 0.38, 'exact': 0.48},
                'ambiguity': {'detection_rate': 0.15},
                'filtering': {'avg_filtered': 1.2, 'avg_kept': 2.8}
            }
        """
        metrics = {}
        
        # 1. TEMPS RÉPONSE
        recent_times = self._filter_recent(self.response_times)
        if recent_times:
            times = [val for _, val in recent_times]
            metrics['response_time'] = {
                'p50': statistics.median(times),
                'p95': statistics.quantiles(times, n=20)[18] if len(times) > 20 else max(times),
                'avg': statistics.mean(times),
                'count': len(times)
            }
        
        # 2. EXTRACTION
        recent_extraction = self._filter_recent(self.extraction_success)
        if recent_extraction:
            successes = [val['success'] for _, val in recent_extraction]
            reductions = [val['reduction'] for _, val in recent_extraction if val['reduction'] > 0]
            metrics['extraction'] = {
                'success_rate': sum(successes) / len(successes),
                'avg_reduction': statistics.mean(reductions) if reductions else 0,
                'count': len(successes)
            }
        
        # 3. PERTINENCE
        recent_relevance = self._filter_recent(self.relevance_scores)
        if recent_relevance:
            scores = [val for _, val in recent_relevance]
            metrics['relevance'] = {
                'avg_score': statistics.mean(scores),
                'min': min(scores),
                'max': max(scores),
                'count': len(scores)
            }
        
        # 4. CACHE
        recent_cache = self._filter_recent(self.cache_hits)
        if recent_cache:
            hits = [val['hit'] for _, val in recent_cache]
            semantic_hits = [val['hit'] for _, val in recent_cache if val['type'] == 'semantic']
            exact_hits = [val['hit'] for _, val in recent_cache if val['type'] == 'exact']
            
            metrics['cache'] = {
                'hit_rate': sum(hits) / len(hits),
                'semantic_rate': sum(semantic_hits) / len(semantic_hits) if semantic_hits else 0,
                'exact_rate': sum(exact_hits) / len(exact_hits) if exact_hits else 0,
                'count': len(hits)
            }
        
        # 5. AMBIGUÏTÉ
        recent_ambiguity = self._filter_recent(self.ambiguity_detected)
        if recent_ambiguity:
            detected = [val['detected'] for _, val in recent_ambiguity]
            metrics['ambiguity'] = {
                'detection_rate': sum(detected) / len(detected),
                'count': len(detected)
            }
        
        # 6. FILTRAGE
        recent_filtering = self._filter_recent(self.docs_filtered)
        if recent_filtering:
            filtered = [val['filtered'] for _, val in recent_filtering]
            kept = [val['after'] for _, val in recent_filtering]
            metrics['filtering'] = {
                'avg_filtered': statistics.mean(filtered),
                'avg_kept': statistics.mean(kept),
                'count': len(filtered)
            }
        
        # Métadonnées
        metrics['window_minutes'] = self.window_minutes
        metrics['uptime_seconds'] = time.time() - self.start_time
        
        return metrics
    
    def get_dashboard(self) -> str:
        """
        Génère dashboard texte
        
        Returns:
            Dashboard formaté pour affichage console
        """
        metrics = self.get_metrics()
        
        dashboard = []
        dashboard.append("=" * 70)
        dashboard.append("📊 QUALITY MONITOR DASHBOARD")
        dashboard.append("=" * 70)
        dashboard.append(f"⏰ Window: {self.window_minutes}min | Uptime: {metrics.get('uptime_seconds', 0):.0f}s")
        dashboard.append("")
        
        # Temps réponse
        if 'response_time' in metrics:
            rt = metrics['response_time']
            dashboard.append(f"⚡ TEMPS RÉPONSE:")
            dashboard.append(f"   P50: {rt['p50']:.1f}ms | P95: {rt['p95']:.1f}ms | Avg: {rt['avg']:.1f}ms")
            dashboard.append(f"   Requêtes: {rt['count']}")
            dashboard.append("")
        
        # Extraction
        if 'extraction' in metrics:
            ext = metrics['extraction']
            dashboard.append(f"✂️ EXTRACTION:")
            dashboard.append(f"   Taux succès: {ext['success_rate']*100:.1f}%")
            dashboard.append(f"   Réduction moyenne: {ext['avg_reduction']:.1f}%")
            dashboard.append("")
        
        # Pertinence
        if 'relevance' in metrics:
            rel = metrics['relevance']
            dashboard.append(f"🎯 PERTINENCE:")
            dashboard.append(f"   Score moyen: {rel['avg_score']:.3f}")
            dashboard.append(f"   Min: {rel['min']:.3f} | Max: {rel['max']:.3f}")
            dashboard.append("")
        
        # Cache
        if 'cache' in metrics:
            cache = metrics['cache']
            dashboard.append(f"💾 CACHE:")
            dashboard.append(f"   Hit rate global: {cache['hit_rate']*100:.1f}%")
            dashboard.append(f"   Semantic: {cache['semantic_rate']*100:.1f}% | Exact: {cache['exact_rate']*100:.1f}%")
            dashboard.append("")
        
        # Ambiguïté
        if 'ambiguity' in metrics:
            amb = metrics['ambiguity']
            dashboard.append(f"⚠️ AMBIGUÏTÉ:")
            dashboard.append(f"   Taux détection: {amb['detection_rate']*100:.1f}%")
            dashboard.append("")
        
        # Filtrage
        if 'filtering' in metrics:
            filt = metrics['filtering']
            dashboard.append(f"🔍 FILTRAGE:")
            dashboard.append(f"   Docs filtrés (moy): {filt['avg_filtered']:.1f}")
            dashboard.append(f"   Docs gardés (moy): {filt['avg_kept']:.1f}")
            dashboard.append("")
        
        dashboard.append("=" * 70)
        
        return "\n".join(dashboard)


# Singleton global
_quality_monitor = None

def get_quality_monitor() -> QualityMonitor:
    """Retourne instance singleton du monitor"""
    global _quality_monitor
    if _quality_monitor is None:
        _quality_monitor = QualityMonitor()
    return _quality_monitor

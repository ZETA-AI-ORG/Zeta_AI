"""
📊 PRODUCTION MONITORING - MÉTRIQUES SCALABLES MULTI-TENANT
Monitoring complet pour système RAG en production (1 à 1000 entreprises)
"""
import asyncio
import json
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import threading
from pathlib import Path

from utils import log3


@dataclass
class QueryMetrics:
    """Métriques d'une requête"""
    query_id: str
    company_id: str
    timestamp: datetime
    query_text: str
    response_time_ms: float
    
    # Métriques de recherche
    meilisearch_time_ms: float
    meilisearch_results: int
    supabase_time_ms: float
    supabase_results: int
    rerank_time_ms: float
    final_results: int
    
    # Métriques LLM
    llm_time_ms: float
    llm_tokens_input: int
    llm_tokens_output: int
    llm_cost_usd: float
    
    # Métriques de cache
    cache_hit: bool
    cache_level: Optional[str]  # L1, L2, L3
    
    # Qualité
    user_feedback: Optional[int] = None  # 1-5 étoiles
    error_occurred: bool = False
    error_message: Optional[str] = None


@dataclass
class CompanyStats:
    """Statistiques par entreprise"""
    company_id: str
    total_queries: int = 0
    avg_response_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    error_rate: float = 0.0
    total_cost_usd: float = 0.0
    avg_user_rating: float = 0.0
    queries_per_minute: float = 0.0
    
    # Tendances (dernières 24h)
    trend_queries: List[int] = None
    trend_response_times: List[float] = None
    
    def __post_init__(self):
        if self.trend_queries is None:
            self.trend_queries = [0] * 24
        if self.trend_response_times is None:
            self.trend_response_times = [0.0] * 24


class ProductionMonitoring:
    """
    📊 SYSTÈME DE MONITORING PRODUCTION SCALABLE
    
    Fonctionnalités:
    - Métriques en temps réel par tenant
    - Alertes automatiques
    - Tableaux de bord par entreprise
    - Export pour Prometheus/Grafana
    - Détection d'anomalies
    - Rapports de performance
    """
    
    def __init__(self, max_history_hours: int = 72):
        self.max_history_hours = max_history_hours
        
        # Stockage des métriques
        self.query_history: deque = deque(maxlen=10000)  # Dernières 10k requêtes
        self.company_stats: Dict[str, CompanyStats] = {}
        
        # Métriques globales
        self.global_stats = {
            'total_queries': 0,
            'total_companies': 0,
            'avg_response_time_ms': 0.0,
            'total_cost_usd': 0.0,
            'uptime_start': datetime.now()
        }
        
        # Alertes
        self.alert_thresholds = {
            'response_time_ms': 2000,
            'error_rate': 0.05,  # 5%
            'cost_per_query_usd': 0.01
        }
        
        self.active_alerts: Dict[str, List[Dict]] = defaultdict(list)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Nettoyage automatique
        self._last_cleanup = time.time()
        
        log3("[MONITORING]", "✅ Système de monitoring production initialisé")
    
    def record_query(self, metrics: QueryMetrics):
        """Enregistre les métriques d'une requête"""
        with self._lock:
            # Ajouter à l'historique
            self.query_history.append(metrics)
            
            # Mettre à jour les stats de l'entreprise
            self._update_company_stats(metrics)
            
            # Mettre à jour les stats globales
            self._update_global_stats(metrics)
            
            # Vérifier les alertes
            self._check_alerts(metrics)
            
            # Nettoyage périodique
            self._periodic_cleanup()
    
    def _update_company_stats(self, metrics: QueryMetrics):
        """Met à jour les statistiques d'une entreprise"""
        company_id = metrics.company_id
        
        if company_id not in self.company_stats:
            self.company_stats[company_id] = CompanyStats(company_id=company_id)
        
        stats = self.company_stats[company_id]
        
        # Mise à jour incrémentale des moyennes
        old_count = stats.total_queries
        new_count = old_count + 1
        
        # Response time moyenne
        stats.avg_response_time_ms = (
            (stats.avg_response_time_ms * old_count + metrics.response_time_ms) / new_count
        )
        
        # Coût total
        stats.total_cost_usd += metrics.llm_cost_usd
        
        # Taux d'erreur
        if metrics.error_occurred:
            error_count = stats.error_rate * old_count + 1
            stats.error_rate = error_count / new_count
        else:
            stats.error_rate = (stats.error_rate * old_count) / new_count
        
        # Cache hit rate
        if metrics.cache_hit:
            cache_hits = stats.cache_hit_rate * old_count + 1
            stats.cache_hit_rate = cache_hits / new_count
        else:
            stats.cache_hit_rate = (stats.cache_hit_rate * old_count) / new_count
        
        # User rating
        if metrics.user_feedback:
            if stats.avg_user_rating == 0:
                stats.avg_user_rating = metrics.user_feedback
            else:
                stats.avg_user_rating = (
                    (stats.avg_user_rating * old_count + metrics.user_feedback) / new_count
                )
        
        stats.total_queries = new_count
        
        # Tendances horaires
        current_hour = datetime.now().hour
        stats.trend_queries[current_hour] += 1
        
        # Response time par heure
        if stats.trend_response_times[current_hour] == 0:
            stats.trend_response_times[current_hour] = metrics.response_time_ms
        else:
            # Moyenne mobile
            stats.trend_response_times[current_hour] = (
                stats.trend_response_times[current_hour] * 0.9 + 
                metrics.response_time_ms * 0.1
            )
    
    def _update_global_stats(self, metrics: QueryMetrics):
        """Met à jour les statistiques globales"""
        self.global_stats['total_queries'] += 1
        self.global_stats['total_cost_usd'] += metrics.llm_cost_usd
        self.global_stats['total_companies'] = len(self.company_stats)
        
        # Response time global moyen
        total_queries = self.global_stats['total_queries']
        old_avg = self.global_stats['avg_response_time_ms']
        self.global_stats['avg_response_time_ms'] = (
            (old_avg * (total_queries - 1) + metrics.response_time_ms) / total_queries
        )
    
    def _check_alerts(self, metrics: QueryMetrics):
        """Vérifie et déclenche les alertes si nécessaire"""
        company_id = metrics.company_id
        alerts = []
        
        # Alerte temps de réponse
        if metrics.response_time_ms > self.alert_thresholds['response_time_ms']:
            alerts.append({
                'type': 'high_response_time',
                'value': metrics.response_time_ms,
                'threshold': self.alert_thresholds['response_time_ms'],
                'severity': 'warning' if metrics.response_time_ms < 5000 else 'critical'
            })
        
        # Alerte coût
        if metrics.llm_cost_usd > self.alert_thresholds['cost_per_query_usd']:
            alerts.append({
                'type': 'high_cost',
                'value': metrics.llm_cost_usd,
                'threshold': self.alert_thresholds['cost_per_query_usd'],
                'severity': 'warning'
            })
        
        # Alerte erreur
        if metrics.error_occurred:
            alerts.append({
                'type': 'query_error',
                'error_message': metrics.error_message,
                'severity': 'error'
            })
        
        # Enregistrer les alertes
        for alert in alerts:
            alert['timestamp'] = datetime.now()
            alert['company_id'] = company_id
            alert['query_id'] = metrics.query_id
            
            self.active_alerts[company_id].append(alert)
            
            # Limiter le nombre d'alertes par entreprise
            if len(self.active_alerts[company_id]) > 100:
                self.active_alerts[company_id] = self.active_alerts[company_id][-50:]
            
            log3("[MONITORING]", f"🚨 Alerte {alert['type']} pour {company_id}")
    
    def _periodic_cleanup(self):
        """Nettoyage périodique des données anciennes"""
        current_time = time.time()
        if current_time - self._last_cleanup > 3600:  # 1 heure
            
            # Nettoyer l'historique des requêtes
            cutoff_time = datetime.now() - timedelta(hours=self.max_history_hours)
            
            # Filtrer les requêtes trop anciennes
            self.query_history = deque(
                [m for m in self.query_history if m.timestamp > cutoff_time],
                maxlen=10000
            )
            
            # Nettoyer les alertes anciennes
            alert_cutoff = datetime.now() - timedelta(hours=24)
            for company_id in self.active_alerts:
                self.active_alerts[company_id] = [
                    alert for alert in self.active_alerts[company_id]
                    if alert['timestamp'] > alert_cutoff
                ]
            
            self._last_cleanup = current_time
            log3("[MONITORING]", "✅ Nettoyage périodique effectué")
    
    def get_company_dashboard(self, company_id: str) -> Dict[str, Any]:
        """Génère le tableau de bord d'une entreprise"""
        with self._lock:
            if company_id not in self.company_stats:
                return {'error': 'Company not found'}
            
            stats = self.company_stats[company_id]
            
            # Requêtes récentes (dernière heure)
            recent_queries = [
                m for m in self.query_history 
                if m.company_id == company_id and 
                   m.timestamp > datetime.now() - timedelta(hours=1)
            ]
            
            # Calculs temps réel
            recent_response_times = [m.response_time_ms for m in recent_queries]
            recent_avg_response = sum(recent_response_times) / len(recent_response_times) if recent_response_times else 0
            
            queries_last_hour = len(recent_queries)
            
            dashboard = {
                'company_id': company_id,
                'overview': {
                    'total_queries': stats.total_queries,
                    'avg_response_time_ms': stats.avg_response_time_ms,
                    'cache_hit_rate': stats.cache_hit_rate,
                    'error_rate': stats.error_rate,
                    'total_cost_usd': stats.total_cost_usd,
                    'avg_user_rating': stats.avg_user_rating
                },
                'real_time': {
                    'queries_last_hour': queries_last_hour,
                    'queries_per_minute': queries_last_hour / 60,
                    'recent_avg_response_ms': recent_avg_response,
                    'active_alerts': len(self.active_alerts.get(company_id, []))
                },
                'trends': {
                    'hourly_queries': stats.trend_queries,
                    'hourly_response_times': stats.trend_response_times
                },
                'alerts': self.active_alerts.get(company_id, [])[-10:]  # 10 dernières alertes
            }
            
            return dashboard
    
    def get_global_dashboard(self) -> Dict[str, Any]:
        """Génère le tableau de bord global"""
        with self._lock:
            # Calculs globaux
            uptime_hours = (datetime.now() - self.global_stats['uptime_start']).total_seconds() / 3600
            
            # Top entreprises par volume
            top_companies = sorted(
                self.company_stats.items(),
                key=lambda x: x[1].total_queries,
                reverse=True
            )[:10]
            
            # Métriques récentes (dernière heure)
            recent_queries = [
                m for m in self.query_history 
                if m.timestamp > datetime.now() - timedelta(hours=1)
            ]
            
            dashboard = {
                'overview': {
                    **self.global_stats,
                    'uptime_hours': uptime_hours,
                    'queries_per_hour': self.global_stats['total_queries'] / max(uptime_hours, 1),
                    'avg_cost_per_query': self.global_stats['total_cost_usd'] / max(self.global_stats['total_queries'], 1)
                },
                'real_time': {
                    'queries_last_hour': len(recent_queries),
                    'active_companies': len([c for c in self.company_stats.values() if c.total_queries > 0]),
                    'total_alerts': sum(len(alerts) for alerts in self.active_alerts.values())
                },
                'top_companies': [
                    {
                        'company_id': company_id,
                        'queries': stats.total_queries,
                        'avg_response_ms': stats.avg_response_time_ms,
                        'cost_usd': stats.total_cost_usd
                    }
                    for company_id, stats in top_companies
                ]
            }
            
            return dashboard
    
    def export_prometheus_metrics(self) -> str:
        """Exporte les métriques au format Prometheus"""
        with self._lock:
            metrics_lines = []
            
            # Métriques globales
            metrics_lines.append(f"rag_total_queries {self.global_stats['total_queries']}")
            metrics_lines.append(f"rag_avg_response_time_ms {self.global_stats['avg_response_time_ms']}")
            metrics_lines.append(f"rag_total_cost_usd {self.global_stats['total_cost_usd']}")
            metrics_lines.append(f"rag_total_companies {self.global_stats['total_companies']}")
            
            # Métriques par entreprise
            for company_id, stats in self.company_stats.items():
                labels = f'{{company_id="{company_id}"}}'
                
                metrics_lines.append(f"rag_company_queries{labels} {stats.total_queries}")
                metrics_lines.append(f"rag_company_response_time_ms{labels} {stats.avg_response_time_ms}")
                metrics_lines.append(f"rag_company_cache_hit_rate{labels} {stats.cache_hit_rate}")
                metrics_lines.append(f"rag_company_error_rate{labels} {stats.error_rate}")
                metrics_lines.append(f"rag_company_cost_usd{labels} {stats.total_cost_usd}")
                
                if stats.avg_user_rating > 0:
                    metrics_lines.append(f"rag_company_user_rating{labels} {stats.avg_user_rating}")
            
            return "\n".join(metrics_lines)
    
    def generate_performance_report(self, company_id: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """Génère un rapport de performance détaillé"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Filtrer les requêtes
            if company_id:
                queries = [m for m in self.query_history 
                          if m.company_id == company_id and m.timestamp > cutoff_time]
            else:
                queries = [m for m in self.query_history if m.timestamp > cutoff_time]
            
            if not queries:
                return {'error': 'No data available for the specified period'}
            
            # Calculs statistiques
            response_times = [q.response_time_ms for q in queries]
            costs = [q.llm_cost_usd for q in queries]
            errors = [q for q in queries if q.error_occurred]
            
            report = {
                'period': f"Last {hours} hours",
                'company_id': company_id or 'ALL',
                'summary': {
                    'total_queries': len(queries),
                    'avg_response_time_ms': sum(response_times) / len(response_times),
                    'median_response_time_ms': sorted(response_times)[len(response_times) // 2],
                    'p95_response_time_ms': sorted(response_times)[int(len(response_times) * 0.95)],
                    'total_cost_usd': sum(costs),
                    'avg_cost_per_query_usd': sum(costs) / len(costs),
                    'error_count': len(errors),
                    'error_rate': len(errors) / len(queries)
                },
                'performance_breakdown': {
                    'meilisearch_avg_ms': sum(q.meilisearch_time_ms for q in queries) / len(queries),
                    'supabase_avg_ms': sum(q.supabase_time_ms for q in queries) / len(queries),
                    'rerank_avg_ms': sum(q.rerank_time_ms for q in queries) / len(queries),
                    'llm_avg_ms': sum(q.llm_time_ms for q in queries) / len(queries)
                },
                'cache_performance': {
                    'total_cache_hits': len([q for q in queries if q.cache_hit]),
                    'cache_hit_rate': len([q for q in queries if q.cache_hit]) / len(queries),
                    'l1_hits': len([q for q in queries if q.cache_level == 'L1']),
                    'l2_hits': len([q for q in queries if q.cache_level == 'L2']),
                    'l3_hits': len([q for q in queries if q.cache_level == 'L3'])
                }
            }
            
            return report
    
    def get_anomalies(self, company_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Détecte les anomalies de performance"""
        with self._lock:
            anomalies = []
            
            # Analyser chaque entreprise
            companies_to_check = [company_id] if company_id else list(self.company_stats.keys())
            
            for cid in companies_to_check:
                if cid not in self.company_stats:
                    continue
                
                stats = self.company_stats[cid]
                recent_queries = [
                    m for m in self.query_history 
                    if m.company_id == cid and 
                       m.timestamp > datetime.now() - timedelta(hours=1)
                ]
                
                if len(recent_queries) < 5:  # Pas assez de données
                    continue
                
                recent_avg_response = sum(q.response_time_ms for q in recent_queries) / len(recent_queries)
                
                # Anomalie: temps de réponse 2x plus élevé que la moyenne
                if recent_avg_response > stats.avg_response_time_ms * 2:
                    anomalies.append({
                        'type': 'response_time_spike',
                        'company_id': cid,
                        'current_avg_ms': recent_avg_response,
                        'historical_avg_ms': stats.avg_response_time_ms,
                        'severity': 'high' if recent_avg_response > 5000 else 'medium'
                    })
                
                # Anomalie: taux d'erreur élevé récent
                recent_errors = len([q for q in recent_queries if q.error_occurred])
                recent_error_rate = recent_errors / len(recent_queries)
                
                if recent_error_rate > 0.1 and recent_error_rate > stats.error_rate * 3:
                    anomalies.append({
                        'type': 'error_rate_spike',
                        'company_id': cid,
                        'current_error_rate': recent_error_rate,
                        'historical_error_rate': stats.error_rate,
                        'severity': 'critical'
                    })
            
            return anomalies


# Instance globale
_monitoring: Optional[ProductionMonitoring] = None

def get_monitoring() -> ProductionMonitoring:
    """Récupère l'instance globale du monitoring"""
    global _monitoring
    if _monitoring is None:
        _monitoring = ProductionMonitoring()
    return _monitoring

def record_query_metrics(
    query_id: str,
    company_id: str,
    query_text: str,
    response_time_ms: float,
    meilisearch_time_ms: float = 0,
    meilisearch_results: int = 0,
    supabase_time_ms: float = 0,
    supabase_results: int = 0,
    rerank_time_ms: float = 0,
    final_results: int = 0,
    llm_time_ms: float = 0,
    llm_tokens_input: int = 0,
    llm_tokens_output: int = 0,
    llm_cost_usd: float = 0,
    cache_hit: bool = False,
    cache_level: Optional[str] = None,
    error_occurred: bool = False,
    error_message: Optional[str] = None
):
    """Fonction utilitaire pour enregistrer les métriques d'une requête"""
    metrics = QueryMetrics(
        query_id=query_id,
        company_id=company_id,
        timestamp=datetime.now(),
        query_text=query_text[:200],  # Limiter la longueur
        response_time_ms=response_time_ms,
        meilisearch_time_ms=meilisearch_time_ms,
        meilisearch_results=meilisearch_results,
        supabase_time_ms=supabase_time_ms,
        supabase_results=supabase_results,
        rerank_time_ms=rerank_time_ms,
        final_results=final_results,
        llm_time_ms=llm_time_ms,
        llm_tokens_input=llm_tokens_input,
        llm_tokens_output=llm_tokens_output,
        llm_cost_usd=llm_cost_usd,
        cache_hit=cache_hit,
        cache_level=cache_level,
        error_occurred=error_occurred,
        error_message=error_message
    )
    
    get_monitoring().record_query(metrics)

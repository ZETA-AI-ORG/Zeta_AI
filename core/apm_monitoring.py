"""
📊 APPLICATION PERFORMANCE MONITORING (APM)
Monitoring professionnel temps réel
"""

import time
import asyncio
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
import logging
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import psutil
import os

logger = logging.getLogger(__name__)

@dataclass
class RequestMetrics:
    """Métriques d'une requête"""
    request_id: str
    query: str
    company_id: str
    user_id: str
    start_time: float
    end_time: float
    duration_ms: float
    search_source: str  # "MeiliSearch", "Supabase", "Cache"
    search_time_ms: float
    generation_time_ms: float
    context_length: int
    response_length: int
    tokens_estimated: int
    cost_estimated_usd: float
    error: Optional[str] = None
    cache_hit: bool = False

@dataclass
class SystemMetrics:
    """Métriques système"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_available_gb: float
    disk_usage_percent: float
    network_io_mb: float
    active_connections: int

class APMMonitoring:
    """
    🎯 MONITORING APM PROFESSIONNEL
    
    Fonctionnalités:
    - Métriques temps réel de toutes les requêtes
    - Monitoring système (CPU, mémoire, réseau)
    - Calcul automatique des coûts
    - Alertes sur seuils
    - Export Prometheus
    - Dashboard intégré
    """
    
    def __init__(self):
        # Métriques Prometheus
        self.request_duration = Histogram(
            'rag_request_duration_seconds',
            'Durée des requêtes RAG',
            ['source', 'company_id']
        )
        
        self.request_count = Counter(
            'rag_requests_total',
            'Nombre total de requêtes',
            ['source', 'status', 'company_id']
        )
        
        self.search_accuracy = Gauge(
            'rag_search_accuracy_score',
            'Score de précision de recherche',
            ['company_id']
        )
        
        self.cost_per_request = Gauge(
            'rag_cost_per_request_usd',
            'Coût par requête en USD',
            ['company_id']
        )
        
        self.system_cpu = Gauge('system_cpu_percent', 'Usage CPU système')
        self.system_memory = Gauge('system_memory_percent', 'Usage mémoire système')
        self.cache_hit_rate = Gauge('cache_hit_rate_percent', 'Taux de hit cache')
        
        # Stockage des métriques récentes
        self.recent_requests: deque = deque(maxlen=1000)  # 1000 dernières requêtes
        self.system_history: deque = deque(maxlen=300)    # 5 minutes d'historique système
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.company_stats: Dict[str, Dict] = defaultdict(lambda: {
            'total_requests': 0,
            'total_cost': 0.0,
            'avg_duration': 0.0,
            'error_rate': 0.0
        })
        
        # Configuration d'alertes
        self.alert_thresholds = {
            'response_time_ms': 5000,  # 5 secondes
            'error_rate_percent': 5.0,  # 5%
            'cpu_percent': 80.0,        # 80%
            'memory_percent': 85.0,     # 85%
            'cost_per_hour_usd': 10.0   # 10$/heure
        }
        
        # Thread de monitoring système
        self.monitoring_active = True
        self.system_monitor_thread = threading.Thread(target=self._monitor_system_loop, daemon=True)
        self.system_monitor_thread.start()
        
        logger.info("[APM] ✅ Monitoring APM initialisé")
    
    async def track_request(self, metrics: RequestMetrics):
        """Enregistre les métriques d'une requête"""
        
        # Ajouter à l'historique
        self.recent_requests.append(metrics)
        
        # Métriques Prometheus
        self.request_duration.labels(
            source=metrics.search_source,
            company_id=metrics.company_id
        ).observe(metrics.duration_ms / 1000.0)
        
        status = "error" if metrics.error else "success"
        self.request_count.labels(
            source=metrics.search_source,
            status=status,
            company_id=metrics.company_id
        ).inc()
        
        self.cost_per_request.labels(
            company_id=metrics.company_id
        ).set(metrics.cost_estimated_usd)
        
        # Statistiques par entreprise
        company_stat = self.company_stats[metrics.company_id]
        company_stat['total_requests'] += 1
        company_stat['total_cost'] += metrics.cost_estimated_usd
        
        # Moyenne mobile de la durée
        if company_stat['avg_duration'] == 0:
            company_stat['avg_duration'] = metrics.duration_ms
        else:
            company_stat['avg_duration'] = (
                company_stat['avg_duration'] * 0.9 + metrics.duration_ms * 0.1
            )
        
        # Taux d'erreur
        if metrics.error:
            self.error_counts[metrics.company_id] += 1
        
        company_stat['error_rate'] = (
            self.error_counts[metrics.company_id] / company_stat['total_requests'] * 100
        )
        
        # Vérification des seuils d'alerte
        await self._check_alerts(metrics)
        
        logger.debug(f"[APM] Métriques enregistrées: {metrics.request_id}")
    
    def _monitor_system_loop(self):
        """Boucle de monitoring système (thread séparé)"""
        while self.monitoring_active:
            try:
                # Métriques système
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                network = psutil.net_io_counters()
                
                system_metrics = SystemMetrics(
                    timestamp=time.time(),
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    memory_used_gb=memory.used / (1024**3),
                    memory_available_gb=memory.available / (1024**3),
                    disk_usage_percent=disk.percent,
                    network_io_mb=(network.bytes_sent + network.bytes_recv) / (1024**2),
                    active_connections=len(psutil.net_connections())
                )
                
                self.system_history.append(system_metrics)
                
                # Métriques Prometheus
                self.system_cpu.set(cpu_percent)
                self.system_memory.set(memory.percent)
                
                # Calcul du hit rate cache (si disponible)
                try:
                    from core.unified_cache_pro import unified_cache
                    cache_stats = unified_cache.get_stats()
                    self.cache_hit_rate.set(cache_stats['hit_rate_percent'])
                except:
                    pass
                
                time.sleep(10)  # Monitoring toutes les 10 secondes
                
            except Exception as e:
                logger.error(f"[APM] Erreur monitoring système: {e}")
                time.sleep(30)  # Attendre plus longtemps en cas d'erreur
    
    async def _check_alerts(self, metrics: RequestMetrics):
        """Vérification des seuils d'alerte"""
        alerts = []
        
        # Alerte temps de réponse
        if metrics.duration_ms > self.alert_thresholds['response_time_ms']:
            alerts.append({
                'type': 'response_time',
                'severity': 'warning',
                'message': f"Temps de réponse élevé: {metrics.duration_ms:.0f}ms",
                'company_id': metrics.company_id,
                'request_id': metrics.request_id
            })
        
        # Alerte taux d'erreur
        company_stat = self.company_stats[metrics.company_id]
        if company_stat['error_rate'] > self.alert_thresholds['error_rate_percent']:
            alerts.append({
                'type': 'error_rate',
                'severity': 'critical',
                'message': f"Taux d'erreur élevé: {company_stat['error_rate']:.1f}%",
                'company_id': metrics.company_id
            })
        
        # Alerte coût
        hourly_cost = company_stat['total_cost'] * (3600 / max(time.time() - 3600, 1))
        if hourly_cost > self.alert_thresholds['cost_per_hour_usd']:
            alerts.append({
                'type': 'cost',
                'severity': 'warning',
                'message': f"Coût horaire élevé: ${hourly_cost:.2f}/h",
                'company_id': metrics.company_id
            })
        
        # Log des alertes
        for alert in alerts:
            logger.warning(f"[APM_ALERT] {alert['severity'].upper()}: {alert['message']}")
    
    def get_real_time_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques temps réel"""
        now = time.time()
        last_minute_requests = [
            r for r in self.recent_requests 
            if now - r.end_time < 60
        ]
        
        last_hour_requests = [
            r for r in self.recent_requests 
            if now - r.end_time < 3600
        ]
        
        # Statistiques globales
        total_requests = len(self.recent_requests)
        error_count = sum(1 for r in self.recent_requests if r.error)
        
        # Moyennes
        avg_duration = sum(r.duration_ms for r in last_minute_requests) / max(len(last_minute_requests), 1)
        avg_cost = sum(r.cost_estimated_usd for r in last_hour_requests) / max(len(last_hour_requests), 1)
        
        # Répartition par source
        source_distribution = defaultdict(int)
        for request in last_hour_requests:
            source_distribution[request.search_source] += 1
        
        # Système actuel
        current_system = self.system_history[-1] if self.system_history else None
        
        return {
            'requests_per_minute': len(last_minute_requests),
            'requests_per_hour': len(last_hour_requests),
            'avg_response_time_ms': round(avg_duration, 1),
            'error_rate_percent': round((error_count / max(total_requests, 1)) * 100, 2),
            'avg_cost_per_request_usd': round(avg_cost, 4),
            'hourly_cost_estimate_usd': round(avg_cost * len(last_hour_requests), 2),
            'source_distribution': dict(source_distribution),
            'system': {
                'cpu_percent': current_system.cpu_percent if current_system else 0,
                'memory_percent': current_system.memory_percent if current_system else 0,
                'memory_used_gb': current_system.memory_used_gb if current_system else 0,
                'active_connections': current_system.active_connections if current_system else 0
            } if current_system else {},
            'top_companies': self._get_top_companies_stats(),
            'recent_errors': self._get_recent_errors()
        }
    
    def _get_top_companies_stats(self) -> List[Dict]:
        """Retourne les stats des entreprises les plus actives"""
        companies = []
        for company_id, stats in self.company_stats.items():
            companies.append({
                'company_id': company_id,
                'requests': stats['total_requests'],
                'avg_duration_ms': round(stats['avg_duration'], 1),
                'total_cost_usd': round(stats['total_cost'], 2),
                'error_rate_percent': round(stats['error_rate'], 2)
            })
        
        return sorted(companies, key=lambda x: x['requests'], reverse=True)[:10]
    
    def _get_recent_errors(self) -> List[Dict]:
        """Retourne les erreurs récentes"""
        errors = []
        for request in reversed(self.recent_requests):
            if request.error and len(errors) < 10:
                errors.append({
                    'timestamp': request.end_time,
                    'company_id': request.company_id,
                    'query': request.query[:50] + "..." if len(request.query) > 50 else request.query,
                    'error': request.error,
                    'duration_ms': request.duration_ms
                })
        
        return errors
    
    def export_prometheus_metrics(self) -> str:
        """Exporte les métriques au format Prometheus"""
        return generate_latest().decode('utf-8')
    
    def stop_monitoring(self):
        """Arrête le monitoring système"""
        self.monitoring_active = False
        if self.system_monitor_thread.is_alive():
            self.system_monitor_thread.join(timeout=5)
        logger.info("[APM] Monitoring arrêté")

# Instance globale
apm_monitor = APMMonitoring()





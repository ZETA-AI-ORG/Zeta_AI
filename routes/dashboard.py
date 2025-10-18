"""
📊 DASHBOARD TEMPS RÉEL - ROUTES API
Interface de monitoring professionnel
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/dashboard")
async def dashboard_home():
    """Page principale du dashboard"""
    
    html_content = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard RAG - Monitoring Temps Réel</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #0f172a;
                color: #e2e8f0;
                overflow-x: hidden;
            }
            
            .header {
                background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
                padding: 1rem 2rem;
                border-bottom: 1px solid #475569;
            }
            
            .header h1 {
                font-size: 1.8rem;
                font-weight: 600;
                color: #f8fafc;
                margin-bottom: 0.5rem;
            }
            
            .status-bar {
                display: flex;
                gap: 2rem;
                align-items: center;
            }
            
            .status-item {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-size: 0.9rem;
            }
            
            .status-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #10b981;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            
            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 1.5rem;
                padding: 2rem;
                max-width: 1400px;
                margin: 0 auto;
            }
            
            .card {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            
            .card:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px -8px rgba(0, 0, 0, 0.2);
            }
            
            .card-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
                padding-bottom: 0.5rem;
                border-bottom: 1px solid #334155;
            }
            
            .card-title {
                font-size: 1.1rem;
                font-weight: 600;
                color: #f8fafc;
            }
            
            .card-icon {
                font-size: 1.2rem;
            }
            
            .metric-large {
                font-size: 2.5rem;
                font-weight: 700;
                color: #10b981;
                margin: 0.5rem 0;
            }
            
            .metric-unit {
                font-size: 0.9rem;
                color: #94a3b8;
                margin-left: 0.5rem;
            }
            
            .metric-change {
                font-size: 0.8rem;
                padding: 0.2rem 0.5rem;
                border-radius: 6px;
                margin-top: 0.5rem;
            }
            
            .metric-change.positive {
                background: rgba(16, 185, 129, 0.1);
                color: #10b981;
            }
            
            .metric-change.negative {
                background: rgba(239, 68, 68, 0.1);
                color: #ef4444;
            }
            
            .chart-container {
                position: relative;
                height: 200px;
                margin-top: 1rem;
            }
            
            .list-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.75rem;
                margin: 0.5rem 0;
                background: #334155;
                border-radius: 8px;
                border-left: 3px solid #10b981;
            }
            
            .list-item-title {
                font-weight: 500;
                color: #f8fafc;
            }
            
            .list-item-value {
                font-weight: 600;
                color: #10b981;
            }
            
            .error-item {
                background: rgba(239, 68, 68, 0.1);
                border-left-color: #ef4444;
            }
            
            .error-item .list-item-value {
                color: #ef4444;
            }
            
            .loading {
                text-align: center;
                padding: 2rem;
                color: #94a3b8;
            }
            
            .spinner {
                width: 24px;
                height: 24px;
                border: 2px solid #334155;
                border-top: 2px solid #10b981;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto 1rem;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚀 Dashboard RAG - Monitoring Temps Réel</h1>
            <div class="status-bar">
                <div class="status-item">
                    <div class="status-dot"></div>
                    <span>Système opérationnel</span>
                </div>
                <div class="status-item">
                    <span id="last-update">Dernière MAJ: --:--</span>
                </div>
            </div>
        </div>
        
        <div class="dashboard-grid" id="dashboard-content">
            <div class="loading">
                <div class="spinner"></div>
                <p>Chargement des métriques...</p>
            </div>
        </div>
        
        <script>
            let charts = {};
            
            // Fonction pour mettre à jour le dashboard
            async function updateDashboard() {
                try {
                    const response = await fetch('/dashboard/api/metrics');
                    const data = await response.json();
                    
                    renderDashboard(data);
                    
                    // Mettre à jour l'heure de dernière MAJ
                    document.getElementById('last-update').textContent = 
                        'Dernière MAJ: ' + new Date().toLocaleTimeString();
                        
                } catch (error) {
                    console.error('Erreur de mise à jour:', error);
                }
            }
            
            function renderDashboard(data) {
                const container = document.getElementById('dashboard-content');
                
                container.innerHTML = `
                    <!-- Métriques principales -->
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">⚡ Performance</div>
                            <div class="card-icon">📊</div>
                        </div>
                        <div class="metric-large">
                            ${data.requests_per_minute}
                            <span class="metric-unit">req/min</span>
                        </div>
                        <div class="metric-change positive">
                            ↗ Temps moyen: ${data.avg_response_time_ms}ms
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">💰 Coûts</div>
                            <div class="card-icon">💳</div>
                        </div>
                        <div class="metric-large">
                            $${data.hourly_cost_estimate_usd}
                            <span class="metric-unit">/heure</span>
                        </div>
                        <div class="metric-change ${data.avg_cost_per_request_usd < 0.01 ? 'positive' : 'negative'}">
                            ${data.avg_cost_per_request_usd < 0.01 ? '↓' : '↑'} $${data.avg_cost_per_request_usd}/req
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">🎯 Qualité</div>
                            <div class="card-icon">✅</div>
                        </div>
                        <div class="metric-large">
                            ${(100 - data.error_rate_percent).toFixed(1)}%
                            <span class="metric-unit">succès</span>
                        </div>
                        <div class="metric-change ${data.error_rate_percent < 2 ? 'positive' : 'negative'}">
                            ${data.error_rate_percent < 2 ? '↓' : '↑'} ${data.error_rate_percent}% erreurs
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">🖥️ Système</div>
                            <div class="card-icon">⚙️</div>
                        </div>
                        <div class="metric-large">
                            ${data.system.cpu_percent}%
                            <span class="metric-unit">CPU</span>
                        </div>
                        <div class="metric-change ${data.system.memory_percent < 80 ? 'positive' : 'negative'}">
                            ${data.system.memory_percent < 80 ? '✓' : '⚠'} ${data.system.memory_percent}% RAM
                        </div>
                    </div>
                    
                    <!-- Sources de données -->
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">📂 Sources de données</div>
                            <div class="card-icon">🔍</div>
                        </div>
                        ${Object.entries(data.source_distribution).map(([source, count]) => `
                            <div class="list-item">
                                <div class="list-item-title">${source}</div>
                                <div class="list-item-value">${count} req</div>
                            </div>
                        `).join('')}
                    </div>
                    
                    <!-- Top entreprises -->
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">🏢 Top entreprises</div>
                            <div class="card-icon">📈</div>
                        </div>
                        ${data.top_companies.slice(0, 5).map(company => `
                            <div class="list-item">
                                <div class="list-item-title">${company.company_id.substring(0, 8)}...</div>
                                <div class="list-item-value">${company.requests} req</div>
                            </div>
                        `).join('')}
                    </div>
                    
                    <!-- Erreurs récentes -->
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">⚠️ Erreurs récentes</div>
                            <div class="card-icon">🚨</div>
                        </div>
                        ${data.recent_errors.length > 0 ? 
                            data.recent_errors.slice(0, 5).map(error => `
                                <div class="list-item error-item">
                                    <div class="list-item-title">${error.error.substring(0, 30)}...</div>
                                    <div class="list-item-value">${error.duration_ms}ms</div>
                                </div>
                            `).join('') : 
                            '<div class="list-item"><div class="list-item-title">✅ Aucune erreur récente</div></div>'
                        }
                    </div>
                `;
            }
            
            // Mettre à jour toutes les 10 secondes
            updateDashboard();
            setInterval(updateDashboard, 10000);
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@router.get("/dashboard/api/metrics")
async def get_dashboard_metrics():
    """API pour récupérer les métriques temps réel"""
    
    try:
        # Importer les modules de monitoring
        from core.apm_monitoring import apm_monitor
        from core.unified_cache_pro import unified_cache
        from core.connection_manager_pro import connection_manager
        
        # Récupérer toutes les métriques
        apm_stats = apm_monitor.get_real_time_stats()
        cache_stats = unified_cache.get_stats()
        connection_stats = connection_manager.get_connection_stats()
        
        # Ajouter les statistiques de cache et connexions
        enhanced_stats = apm_stats.copy()
        enhanced_stats['cache'] = cache_stats
        enhanced_stats['connections'] = connection_stats
        
        return JSONResponse(content=enhanced_stats)
        
    except Exception as e:
        logger.error(f"[DASHBOARD] Erreur métriques: {e}")
        
        # Retourner des données par défaut en cas d'erreur
        return JSONResponse(content={
            'requests_per_minute': 0,
            'requests_per_hour': 0,
            'avg_response_time_ms': 0,
            'error_rate_percent': 0,
            'avg_cost_per_request_usd': 0,
            'hourly_cost_estimate_usd': 0,
            'source_distribution': {},
            'system': {
                'cpu_percent': 0,
                'memory_percent': 0,
                'memory_used_gb': 0,
                'active_connections': 0
            },
            'top_companies': [],
            'recent_errors': [],
            'cache': {'hit_rate_percent': 0},
            'connections': {}
        })

@router.get("/dashboard/api/prometheus")
async def get_prometheus_metrics():
    """Endpoint Prometheus pour scraping"""
    
    try:
        from core.apm_monitoring import apm_monitor
        metrics_text = apm_monitor.export_prometheus_metrics()
        
        return Response(
            content=metrics_text,
            media_type="text/plain"
        )
        
    except Exception as e:
        logger.error(f"[DASHBOARD] Erreur Prometheus: {e}")
        raise HTTPException(status_code=500, detail="Erreur export Prometheus")

@router.get("/dashboard/health")
async def health_check():
    """Check de santé du système"""
    
    try:
        from core.apm_monitoring import apm_monitor
        from core.unified_cache_pro import unified_cache
        from core.connection_manager_pro import connection_manager
        
        # Vérifier chaque composant
        health_status = {
            'status': 'healthy',
            'timestamp': time.time(),
            'components': {
                'apm': 'healthy',
                'cache': 'healthy' if unified_cache.initialized else 'degraded',
                'connections': 'healthy' if connection_manager.initialized else 'degraded',
                'redis': 'healthy' if connection_manager.redis_pool else 'unavailable'
            }
        }
        
        # Déterminer le status global
        component_statuses = list(health_status['components'].values())
        if 'unhealthy' in component_statuses:
            health_status['status'] = 'unhealthy'
        elif 'degraded' in component_statuses:
            health_status['status'] = 'degraded'
        
        return JSONResponse(content=health_status)
        
    except Exception as e:
        logger.error(f"[DASHBOARD] Erreur health check: {e}")
        return JSONResponse(
            content={
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': time.time()
            },
            status_code=503
        )





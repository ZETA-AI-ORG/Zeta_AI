from prometheus_fastapi_instrumentator import Instrumentator

def setup_metrics(app):
    """
    Configure et attache l'instrumentateur Prometheus à l'application FastAPI.
    Ceci expose un endpoint /metrics avec des métriques de performance standard.
    """
    instrumentator = Instrumentator()
    instrumentator.instrument(app).expose(app)
    return instrumentator

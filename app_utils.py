import time
import functools
import asyncio
import random
import httpx
import logging
from typing import Optional, Dict, Any

# === PATCH DE RÉSILIENCE GROQ ===

class GroqResilienceManager:
    def __init__(self):
        self.max_retries = 3
        self.base_delay = 1.0  # secondes
        self.max_delay = 30.0
        self.jitter = True
        self.stats = {
            'total_requests': 0,
            'failed_requests': 0,
            'retry_attempts': 0,
            'fallback_used': 0,
            'avg_response_time': 0.0
        }

    def _calculate_delay(self, attempt: int) -> float:
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)
        return delay

    def _is_retryable_error(self, error: Exception) -> bool:
        if isinstance(error, httpx.HTTPStatusError):
            return error.response.status_code in [429, 500, 502, 503, 504]
        elif isinstance(error, (httpx.TimeoutException, httpx.ConnectError)):
            return True
        return False

    async def resilient_complete(self, complete_func, prompt: str, model_name: str = "llama3-8b-8192", temperature: float = 0.0, max_tokens: Optional[int] = None, fallback_response: Optional[str] = None) -> str:
        self.stats['total_requests'] += 1
        start_time = time.time()
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    delay = self._calculate_delay(attempt - 1)
                    print(f"[GROQ RETRY] Tentative {attempt}/{self.max_retries} après {delay:.1f}s")
                    await asyncio.sleep(delay)
                    self.stats['retry_attempts'] += 1
                result = await complete_func(
                    prompt=prompt,
                    model_name=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                response_time = time.time() - start_time
                self._update_response_time(response_time)
                if attempt > 0:
                    print(f"[GROQ RETRY] Succès après {attempt} tentatives")
                return result
            except Exception as e:
                last_error = e
                print(f"[GROQ ERROR] Tentative {attempt + 1}: {type(e).__name__}")
                if attempt >= self.max_retries or not self._is_retryable_error(e):
                    break
        self.stats['failed_requests'] += 1
        print(f"[GROQ FALLBACK] Toutes tentatives échouées: {type(last_error).__name__}")
        if fallback_response:
            self.stats['fallback_used'] += 1
            print(f"[GROQ FALLBACK] Utilisation réponse de secours")
            return fallback_response
        raise last_error

    def _update_response_time(self, response_time: float):
        current_avg = self.stats['avg_response_time']
        total_success = self.stats['total_requests'] - self.stats['failed_requests']
        if total_success == 1:
            self.stats['avg_response_time'] = response_time
        else:
            self.stats['avg_response_time'] = (current_avg * (total_success - 1) + response_time) / total_success

    def get_health_status(self) -> Dict[str, Any]:
        total = self.stats['total_requests']
        if total == 0:
            return {'status': 'unknown', 'success_rate': 0.0}
        success_rate = (total - self.stats['failed_requests']) / total * 100
        return {
            'status': 'healthy' if success_rate > 90 else 'degraded' if success_rate > 70 else 'unhealthy',
            'success_rate': round(success_rate, 2),
            'avg_response_time': round(self.stats['avg_response_time'], 3),
            'total_requests': total,
            'failed_requests': self.stats['failed_requests'],
            'retry_attempts': self.stats['retry_attempts'],
            'fallback_used': self.stats['fallback_used']
        }

groq_resilience = GroqResilienceManager()

def init_groq_resilience(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
    groq_resilience.max_retries = max_retries
    groq_resilience.base_delay = base_delay
    groq_resilience.max_delay = max_delay
    print(f"[GROQ RESILIENCE] Initialisé: {max_retries} retries, délai {base_delay}-{max_delay}s")

def reset_groq_stats():
    groq_resilience.stats = {
        'total_requests': 0,
        'failed_requests': 0,
        'retry_attempts': 0,
        'fallback_used': 0,
        'avg_response_time': 0.0
    }
    print("[GROQ RESILIENCE] Statistiques remises à zéro")

def timing_metric(label):
    """
    Décorateur pour mesurer le temps d'exécution d'une fonction (sync ou async) et logger la durée.
    """
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.perf_counter()
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logging.getLogger("app").info(f"[METRIC] {label}: {elapsed:.3f}s")
                return result
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logging.getLogger("app").info(f"[METRIC] {label}: {elapsed:.3f}s")
                return result
            return sync_wrapper
    return decorator

def validate_context(context: str) -> bool:
    """Validation stricte du contexte fusionné."""
    return bool(context and context.strip() and len(context) > 10)

def log3(label, content, level='info', max_lines=10, max_length=500, show_full_in_console=False):
    """
    Log structuré avancé avec contrôle du niveau, troncature et sortie console.
    
    Args:
        label: Étiquette pour identifier la source du log
        content: Contenu à logger (peut être str, dict, list, etc.)
        level: Niveau de log ('debug', 'info', 'warning', 'error')
        max_lines: Nombre maximum de lignes à afficher avant troncature
        max_length: Longueur maximale du contenu avant troncature
        show_full_in_console: Si True, affiche le contenu complet dans la console
    """
    logger = logging.getLogger('app')
    
    try:
        # Formater le contenu
        if content is None:
            content_str = "(None)"
        elif isinstance(content, (dict, list)):
            import json
            content_str = json.dumps(content, indent=2, ensure_ascii=False, default=str)
        else:
            content_str = str(content)
        
        # Créer une version complète pour les logs
        full_content = content_str
        
        # Tronquer si nécessaire
        lines = content_str.split('\n')
        if len(lines) > max_lines:
            content_str = '\n'.join(lines[:max_lines]) + f'\n... (tronqué, {len(lines) - max_lines} lignes supplémentaires)'
        
        if len(content_str) > max_length:
            content_str = content_str[:max_length] + f'... (tronqué, {len(content_str) - max_length} caractères supplémentaires)'
        
        # Logger avec le niveau approprié
        log_method = getattr(logger, level.lower(), logger.info)
        log_msg = f"[TRACE][{label}] {content_str}"
        log_method(log_msg)
        
        # Toujours afficher dans la console pour une visibilité immédiate
        console_output = content_str if show_full_in_console else content_str
        print(f"[TRACE][{time.strftime('%H:%M:%S')}][{level.upper()}] {label}: {console_output}")
        
        # Retourner le contenu complet pour un éventuel traitement ultérieur
        return full_content
    except Exception as e:
        print(f"[LOG3 ERROR] {str(e)}")  # Fallback en cas d'échec du logger
        return str(content) if content is not None else "(None)"

def get_history(company_id: str, user_id: str, limit: int = 10) -> list:
    """
    Fonction stub pour get_history - retourne une liste vide pour éviter l'erreur d'import
    """
    # Désactive le chargement de l'historique pour forcer une conversation à blanc.
    # Il faudra décommenter la ligne originale après le test.
    return []
    # Ligne originale :
    # return supabase.table("conversations").select("message", "response").eq("company_id", company_id).eq("user_id", user_id).order("created_at", desc=True).limit(10).execute()

def save_message(company_id: str, user_id: str, message: str, response: str) -> None:
    """
    Fonction stub pour save_message - ne fait rien pour éviter l'erreur d'import
    """
    pass

def extract_context_attribute(context_block: str, attribute: str = None, index: int = None) -> str:
    """
    Extrait la valeur d'un attribut précis (par nom ou par position) depuis un bloc contextuel formaté (chaîne multi-lignes).
    - Si 'attribute' est spécifié, retourne la valeur de la première ligne commençant par 'attribute:'.
    - Si 'index' est spécifié, retourne la nième ligne (0 = premier attribut).
    - Si aucun des deux, retourne None.
    """
    if not context_block:
        return None
    lines = [l.strip() for l in context_block.splitlines() if ':' in l]
    if attribute:
        for l in lines:
            if l.lower().startswith(f"{attribute.lower()}:"):
                return l
        return None
    if index is not None:
        if 0 <= index < len(lines):
            return lines[index]
        return None
    return None
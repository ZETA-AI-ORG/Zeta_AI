"""
🎯 ROUTEUR BOTLIVE - SYSTÈME A/B TESTING
Gère le basculement entre ancien système et nouveau système hybride

SÉCURITÉ:
- Rollback instantané via variable d'environnement
- Fallback automatique en cas d'erreur
- Métriques de comparaison A/B
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BotliveRouter:
    """
    Routeur intelligent pour basculer entre:
    - Ancien système (LLM fait tout)
    - Système hybride (Python + LLM)
    - Système intelligent (Python 100% automatique)
    """
    
    def __init__(self):
        self.use_hybrid = False  # Désactivé par défaut
        self.use_intelligent = False  # Nouveau système intelligent
        self.metrics = {
            "old_system": {"count": 0, "errors": 0, "avg_time": 0},
            "hybrid_system": {"count": 0, "errors": 0, "avg_time": 0},
            "intelligent_system": {"count": 0, "errors": 0, "avg_time": 0}
        }
    
    def enable_hybrid(self):
        """Active le système hybride"""
        self.use_hybrid = True
        logger.info("🚀 [ROUTER] Système HYBRIDE activé")
    
    def disable_hybrid(self):
        """Désactive le système hybride (rollback)"""
        self.use_hybrid = False
        logger.warning("⚠️ [ROUTER] ROLLBACK vers ancien système")
    
    def enable_intelligent(self):
        """Active le système intelligent (100% auto)"""
        self.use_intelligent = True
        self.use_hybrid = False  # Désactiver hybride si intelligent activé
        logger.info("🚀 [ROUTER] Système INTELLIGENT activé (100% auto)")
    
    def disable_intelligent(self):
        """Désactive le système intelligent"""
        self.use_intelligent = False
        logger.warning("⚠️ [ROUTER] Système INTELLIGENT désactivé")
    
    def toggle(self):
        """Bascule entre les systèmes"""
        if self.use_intelligent:
            self.use_intelligent = False
            self.use_hybrid = False
            status = "ANCIEN"
        elif self.use_hybrid:
            self.use_hybrid = False
            self.use_intelligent = True
            status = "INTELLIGENT"
        else:
            self.use_hybrid = True
            status = "HYBRIDE"
        logger.info(f"🔄 [ROUTER] Basculement vers système {status}")
    
    def is_hybrid_enabled(self) -> bool:
        """Vérifie si le système hybride est actif"""
        # Vérifier variable d'environnement (prioritaire)
        env_hybrid = os.getenv("USE_HYBRID_BOTLIVE", "false").lower()
        if env_hybrid in ["true", "1", "yes"]:
            return True
        if env_hybrid in ["false", "0", "no"]:
            return False
        
        # Sinon, utiliser l'état interne
        return self.use_hybrid
    
    def route_request(
        self,
        message: str,
        notepad: Dict[str, Any],
        vision_result: Optional[Dict[str, Any]],
        ocr_result: Optional[Dict[str, Any]],
        old_system_function: callable,
        hybrid_system_function: callable
    ) -> Dict[str, Any]:
        """
        Route la requête vers le bon système
        
        Args:
            message: Message client
            notepad: Contexte mémoire
            vision_result: Résultat Vision
            ocr_result: Résultat OCR
            old_system_function: Fonction ancien système
            hybrid_system_function: Fonction nouveau système
        
        Returns:
            {
                "response": str,
                "system_used": str,  # "old" ou "hybrid"
                "success": bool,
                "metrics": dict
            }
        """
        start_time = datetime.now()
        
        try:
            if self.is_hybrid_enabled():
                # Utiliser système hybride
                logger.info("🎯 [ROUTER] Routage vers système HYBRIDE")
                
                try:
                    result = hybrid_system_function(
                        message=message,
                        notepad=notepad,
                        vision_result=vision_result,
                        ocr_result=ocr_result
                    )
                    
                    # Métriques
                    elapsed = (datetime.now() - start_time).total_seconds()
                    self.metrics["hybrid_system"]["count"] += 1
                    self._update_avg_time("hybrid_system", elapsed)
                    
                    logger.info(f"✅ [ROUTER] Système HYBRIDE OK ({elapsed:.2f}s)")
                    
                    return {
                        "response": result.get("response"),
                        "system_used": "hybrid",
                        "success": True,
                        "metrics": {
                            "elapsed": elapsed,
                            "state": result.get("state"),
                            "action": result.get("action")
                        }
                    }
                
                except Exception as e:
                    logger.error(f"❌ [ROUTER] Erreur système HYBRIDE: {e}")
                    self.metrics["hybrid_system"]["errors"] += 1
                    
                    # Fallback automatique vers ancien système
                    logger.warning("🔄 [ROUTER] FALLBACK automatique vers ancien système")
                    return self._use_old_system(
                        message, notepad, vision_result, ocr_result,
                        old_system_function, start_time, fallback=True
                    )
            
            else:
                # Utiliser ancien système
                logger.info("🎯 [ROUTER] Routage vers système ANCIEN")
                return self._use_old_system(
                    message, notepad, vision_result, ocr_result,
                    old_system_function, start_time, fallback=False
                )
        
        except Exception as e:
            logger.error(f"❌ [ROUTER] Erreur critique routage: {e}")
            
            # Fallback ultime
            return {
                "response": "Envoyez photo du paquet 📦",
                "system_used": "fallback_critical",
                "success": False,
                "metrics": {"error": str(e)}
            }
    
    def _use_old_system(
        self,
        message: str,
        notepad: Dict[str, Any],
        vision_result: Optional[Dict[str, Any]],
        ocr_result: Optional[Dict[str, Any]],
        old_system_function: callable,
        start_time: datetime,
        fallback: bool = False
    ) -> Dict[str, Any]:
        """Utilise l'ancien système"""
        try:
            result = old_system_function(
                message=message,
                notepad=notepad,
                vision_result=vision_result,
                ocr_result=ocr_result
            )
            
            # Métriques
            elapsed = (datetime.now() - start_time).total_seconds()
            self.metrics["old_system"]["count"] += 1
            self._update_avg_time("old_system", elapsed)
            
            system_label = "ANCIEN (fallback)" if fallback else "ANCIEN"
            logger.info(f"✅ [ROUTER] Système {system_label} OK ({elapsed:.2f}s)")
            
            return {
                "response": result,
                "system_used": "old" if not fallback else "old_fallback",
                "success": True,
                "metrics": {"elapsed": elapsed}
            }
        
        except Exception as e:
            logger.error(f"❌ [ROUTER] Erreur système ANCIEN: {e}")
            self.metrics["old_system"]["errors"] += 1
            
            return {
                "response": "Envoyez photo du paquet 📦",
                "system_used": "old_error",
                "success": False,
                "metrics": {"error": str(e)}
            }
    
    def _update_avg_time(self, system: str, elapsed: float):
        """Met à jour le temps moyen"""
        current_avg = self.metrics[system]["avg_time"]
        count = self.metrics[system]["count"]
        
        # Moyenne mobile
        new_avg = ((current_avg * (count - 1)) + elapsed) / count
        self.metrics[system]["avg_time"] = new_avg
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques de comparaison"""
        return {
            "hybrid_enabled": self.is_hybrid_enabled(),
            "old_system": self.metrics["old_system"],
            "hybrid_system": self.metrics["hybrid_system"],
            "comparison": self._compare_systems()
        }
    
    def _compare_systems(self) -> Dict[str, Any]:
        """Compare les performances des deux systèmes"""
        old = self.metrics["old_system"]
        hybrid = self.metrics["hybrid_system"]
        
        if old["count"] == 0 or hybrid["count"] == 0:
            return {"status": "Pas assez de données pour comparaison"}
        
        # Taux d'erreur
        old_error_rate = (old["errors"] / old["count"]) * 100 if old["count"] > 0 else 0
        hybrid_error_rate = (hybrid["errors"] / hybrid["count"]) * 100 if hybrid["count"] > 0 else 0
        
        # Gain de performance
        time_improvement = ((old["avg_time"] - hybrid["avg_time"]) / old["avg_time"]) * 100 if old["avg_time"] > 0 else 0
        
        return {
            "old_error_rate": f"{old_error_rate:.1f}%",
            "hybrid_error_rate": f"{hybrid_error_rate:.1f}%",
            "time_improvement": f"{time_improvement:+.1f}%",
            "recommendation": "hybrid" if hybrid_error_rate < old_error_rate else "old"
        }


# Instance globale (singleton)
_router = None

def get_router() -> BotliveRouter:
    """Retourne l'instance singleton du routeur"""
    global _router
    if _router is None:
        _router = BotliveRouter()
    return _router

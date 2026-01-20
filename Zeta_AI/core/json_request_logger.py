#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📝 SYSTÈME DE LOGS PERSISTANTS JSON
Sauvegarde automatique de toutes les requêtes/réponses pour analyse
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class JSONRequestLogger:
    """
    Logger persistant pour toutes les requêtes RAG
    Sauvegarde dans logs/requests/YYYY-MM-DD.json
    """
    
    def __init__(self, log_dir: str = "logs/requests"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📝 JSONRequestLogger initialisé: {self.log_dir}")
    
    def _get_log_file(self) -> Path:
        """Retourne le fichier de log du jour"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"{today}.json"
    
    def log_request(
        self,
        request_id: str,
        user_id: str,
        company_id: str,
        message: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Sauvegarde une requête/réponse complète
        
        Args:
            request_id: ID unique de la requête
            user_id: ID utilisateur
            company_id: ID entreprise
            message: Message utilisateur
            response: Réponse générée
            metadata: Métadonnées additionnelles (temps, erreurs, etc.)
        """
        log_entry = {
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "company_id": company_id,
            "message": message,
            "response": response,
            "metadata": metadata or {}
        }
        
        try:
            log_file = self._get_log_file()
            
            # Lire les logs existants
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    try:
                        logs = json.load(f)
                    except json.JSONDecodeError:
                        logs = []
            else:
                logs = []
            
            # Ajouter le nouveau log
            logs.append(log_entry)
            
            # Sauvegarder
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"📝 Log sauvegardé: {request_id}")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde log: {e}")
    
    def log_error(
        self,
        request_id: str,
        user_id: str,
        company_id: str,
        message: str,
        error: Exception,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Sauvegarde une erreur
        
        Args:
            request_id: ID unique de la requête
            user_id: ID utilisateur
            company_id: ID entreprise
            message: Message utilisateur
            error: Exception levée
            metadata: Métadonnées additionnelles
        """
        error_metadata = metadata or {}
        error_metadata.update({
            "error_type": type(error).__name__,
            "error_message": str(error),
            "error_details": repr(error)
        })
        
        self.log_request(
            request_id=request_id,
            user_id=user_id,
            company_id=company_id,
            message=message,
            response=f"[ERROR] {str(error)}",
            metadata=error_metadata
        )
    
    def get_logs_for_date(self, date: str = None) -> list:
        """
        Récupère les logs d'une date spécifique
        
        Args:
            date: Date au format YYYY-MM-DD (défaut: aujourd'hui)
        
        Returns:
            Liste des logs
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        log_file = self.log_dir / f"{date}.json"
        
        if not log_file.exists():
            return []
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Erreur lecture logs: {e}")
            return []
    
    def get_logs_for_user(self, user_id: str, date: str = None) -> list:
        """
        Récupère les logs d'un utilisateur spécifique
        
        Args:
            user_id: ID utilisateur
            date: Date au format YYYY-MM-DD (défaut: aujourd'hui)
        
        Returns:
            Liste des logs filtrés
        """
        all_logs = self.get_logs_for_date(date)
        return [log for log in all_logs if log.get("user_id") == user_id]
    
    def get_errors_for_date(self, date: str = None) -> list:
        """
        Récupère uniquement les erreurs d'une date
        
        Args:
            date: Date au format YYYY-MM-DD (défaut: aujourd'hui)
        
        Returns:
            Liste des erreurs
        """
        all_logs = self.get_logs_for_date(date)
        return [
            log for log in all_logs 
            if log.get("response", "").startswith("[ERROR]") or 
               log.get("metadata", {}).get("error_type")
        ]
    
    def search_logs(
        self, 
        query: str, 
        date: str = None,
        search_in: list = ["message", "response"]
    ) -> list:
        """
        Recherche dans les logs
        
        Args:
            query: Terme à rechercher
            date: Date au format YYYY-MM-DD (défaut: aujourd'hui)
            search_in: Champs où chercher
        
        Returns:
            Liste des logs correspondants
        """
        all_logs = self.get_logs_for_date(date)
        query_lower = query.lower()
        
        results = []
        for log in all_logs:
            for field in search_in:
                if query_lower in str(log.get(field, "")).lower():
                    results.append(log)
                    break
        
        return results
    
    def get_stats_for_date(self, date: str = None) -> Dict[str, Any]:
        """
        Statistiques des logs d'une date
        
        Args:
            date: Date au format YYYY-MM-DD (défaut: aujourd'hui)
        
        Returns:
            Dictionnaire de statistiques
        """
        all_logs = self.get_logs_for_date(date)
        errors = self.get_errors_for_date(date)
        
        # Compter les utilisateurs uniques
        unique_users = set(log.get("user_id") for log in all_logs)
        
        # Compter les entreprises uniques
        unique_companies = set(log.get("company_id") for log in all_logs)
        
        # Temps de réponse moyen
        response_times = [
            log.get("metadata", {}).get("processing_time_ms", 0)
            for log in all_logs
            if log.get("metadata", {}).get("processing_time_ms")
        ]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Types d'erreurs
        error_types = {}
        for error in errors:
            error_type = error.get("metadata", {}).get("error_type", "Unknown")
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "total_requests": len(all_logs),
            "total_errors": len(errors),
            "error_rate": len(errors) / len(all_logs) if all_logs else 0,
            "unique_users": len(unique_users),
            "unique_companies": len(unique_companies),
            "avg_response_time_ms": round(avg_response_time, 2),
            "error_types": error_types
        }


# ============================================================================
# SINGLETON GLOBAL
# ============================================================================

_logger_instance: Optional[JSONRequestLogger] = None


def get_json_request_logger(log_dir: str = "logs/requests") -> JSONRequestLogger:
    """Récupère l'instance singleton du logger"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = JSONRequestLogger(log_dir)
    return _logger_instance


def reset_json_request_logger():
    """Reset le singleton (pour tests)"""
    global _logger_instance
    _logger_instance = None


# ============================================================================
# UTILITAIRES CLI
# ============================================================================

def print_log_entry(log: Dict[str, Any], verbose: bool = False):
    """Affiche un log de manière lisible"""
    timestamp = log.get("timestamp", "N/A")
    user_id = log.get("user_id", "N/A")
    message = log.get("message", "")
    response = log.get("response", "")
    
    print(f"\n{'='*80}")
    print(f"🕐 {timestamp}")
    print(f"👤 User: {user_id}")
    print(f"📤 Message: {message[:100]}{'...' if len(message) > 100 else ''}")
    print(f"🤖 Response: {response[:100]}{'...' if len(response) > 100 else ''}")
    
    if verbose:
        metadata = log.get("metadata", {})
        if metadata:
            print(f"\n📊 Metadata:")
            for key, value in metadata.items():
                print(f"  - {key}: {value}")
    
    print(f"{'='*80}")


if __name__ == "__main__":
    import sys
    
    # CLI pour consulter les logs
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python json_request_logger.py stats [date]")
        print("  python json_request_logger.py errors [date]")
        print("  python json_request_logger.py search <query> [date]")
        print("  python json_request_logger.py user <user_id> [date]")
        print("  python json_request_logger.py all [date]")
        sys.exit(1)
    
    command = sys.argv[1]
    date = sys.argv[2] if len(sys.argv) > 2 else None
    
    logger_instance = get_json_request_logger()
    
    if command == "stats":
        stats = logger_instance.get_stats_for_date(date)
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    elif command == "errors":
        errors = logger_instance.get_errors_for_date(date)
        print(f"📊 {len(errors)} erreur(s) trouvée(s)")
        for error in errors:
            print_log_entry(error, verbose=True)
    
    elif command == "search":
        if len(sys.argv) < 3:
            print("❌ Usage: python json_request_logger.py search <query> [date]")
            sys.exit(1)
        query = sys.argv[2]
        date = sys.argv[3] if len(sys.argv) > 3 else None
        results = logger_instance.search_logs(query, date)
        print(f"📊 {len(results)} résultat(s) trouvé(s)")
        for result in results:
            print_log_entry(result)
    
    elif command == "user":
        if len(sys.argv) < 3:
            print("❌ Usage: python json_request_logger.py user <user_id> [date]")
            sys.exit(1)
        user_id = sys.argv[2]
        date = sys.argv[3] if len(sys.argv) > 3 else None
        logs = logger_instance.get_logs_for_user(user_id, date)
        print(f"📊 {len(logs)} log(s) trouvé(s) pour {user_id}")
        for log in logs:
            print_log_entry(log)
    
    elif command == "all":
        logs = logger_instance.get_logs_for_date(date)
        print(f"📊 {len(logs)} log(s) trouvé(s)")
        for log in logs:
            print_log_entry(log)
    
    else:
        print(f"❌ Commande inconnue: {command}")
        sys.exit(1)

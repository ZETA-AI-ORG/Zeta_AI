#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📝 SYSTÈME DE LOGS SERVEUR COMPLETS EN JSON
Capture TOUS les logs (print, logger, erreurs) dans un fichier JSON
"""

import json
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import traceback
import io


class ServerJSONLogger:
    """
    Logger qui capture TOUS les logs serveur en JSON
    - Prints
    - Logs Python
    - Erreurs
    - Exceptions
    - Tout!
    """

    def __init__(self, log_dir: str = "logs/server"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Fichier du jour
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.log_file = self.log_dir / f"server_{self.current_date}.json"

        # Buffer pour les logs
        self.logs = []

        # Sauvegarder les stdout/stderr originaux
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        print(f"📝 ServerJSONLogger initialisé: {self.log_file}")

    def _get_log_file(self) -> Path:
        """Retourne le fichier de log du jour (SANS récursion)"""
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self.current_date:
            # Nouveau jour, on change juste de fichier
            self.current_date = today
            self.log_file = self.log_dir / f"server_{self.current_date}.json"
        return self.log_file

    def log(
        self,
        level: str,
        message: str,
        source: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Ajoute un log au buffer"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "source": source,
            "message": message,
            "metadata": metadata or {}
        }

        self.logs.append(log_entry)

        # Flush tous les 10 logs
        if len(self.logs) >= 10:
            self._flush()

    def _flush(self):
        """Écrit les logs dans le fichier (SANS appel récursif à _get_log_file/_flush)"""
        if not self.logs:
            return

        log_file = self._get_log_file()

        # Lire les logs existants
        existing_logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    existing_logs = json.load(f)
            except Exception:
                existing_logs = []

        # Ajouter les nouveaux logs
        existing_logs.extend(self.logs)

        # Écrire tout
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(existing_logs, f, ensure_ascii=False, indent=2)

        # Vider le buffer
        self.logs = []

    def flush(self):
        """Force l'écriture des logs"""
        self._flush()


class StdoutCapture(io.StringIO):
    """Capture stdout et l'envoie au logger JSON"""

    def __init__(self, logger: ServerJSONLogger, original_stdout, level: str = "INFO"):
        super().__init__()
        self.logger = logger
        self.original_stdout = original_stdout
        self.level = level

    def write(self, message: str):
        # Écrire dans stdout original
        self.original_stdout.write(message)
        self.original_stdout.flush()

        # Logger si non vide
        if message.strip():
            self.logger.log(
                level=self.level,
                message=message.strip(),
                source="stdout"
            )

    def flush(self):
        self.original_stdout.flush()


class StderrCapture(io.StringIO):
    """Capture stderr et l'envoie au logger JSON"""

    def __init__(self, logger: ServerJSONLogger, original_stderr):
        super().__init__()
        self.logger = logger
        self.original_stderr = original_stderr

    def write(self, message: str):
        # Écrire dans stderr original
        self.original_stderr.write(message)
        self.original_stderr.flush()

        # Logger si non vide
        if message.strip():
            self.logger.log(
                level="ERROR",
                message=message.strip(),
                source="stderr"
            )

    def flush(self):
        self.original_stderr.flush()


class JSONLogHandler(logging.Handler):
    """Handler pour capturer les logs Python"""

    def __init__(self, logger: ServerJSONLogger):
        super().__init__()
        self.json_logger = logger

    def emit(self, record: logging.LogRecord):
        try:
            # Formater le message
            message = self.format(record)

            # Extraire métadonnées
            metadata = {
                "logger_name": record.name,
                "filename": record.filename,
                "lineno": record.lineno,
                "funcName": record.funcName
            }

            # Ajouter exception si présente
            if record.exc_info:
                metadata["exception"] = {
                    "type": record.exc_info[0].__name__,
                    "message": str(record.exc_info[1]),
                    "traceback": traceback.format_exception(*record.exc_info)
                }

            # Logger
            self.json_logger.log(
                level=record.levelname,
                message=message,
                source=f"logger.{record.name}",
                metadata=metadata
            )
        except Exception:
            self.handleError(record)


# ============================================================================
# SINGLETON GLOBAL
# ============================================================================

_server_logger: Optional[ServerJSONLogger] = None


def get_server_logger(log_dir: str = "logs/server") -> ServerJSONLogger:
    """Récupère l'instance singleton du logger"""
    global _server_logger
    if _server_logger is None:
        _server_logger = ServerJSONLogger(log_dir)
    return _server_logger


def setup_server_logging():
    """
    Configure le logging complet du serveur
    À appeler au démarrage de l'application
    """
    logger = get_server_logger()

    # Capturer stdout
    sys.stdout = StdoutCapture(logger, sys.stdout, "INFO")

    # Capturer stderr
    sys.stderr = StderrCapture(logger, sys.stderr)

    # Ajouter handler aux loggers Python
    json_handler = JSONLogHandler(logger)
    json_handler.setLevel(logging.DEBUG)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    json_handler.setFormatter(formatter)

    # Ajouter aux loggers racine
    root_logger = logging.getLogger()
    root_logger.addHandler(json_handler)

    # Ajouter aux loggers spécifiques
    for logger_name in ['app', 'uvicorn', 'fastapi']:
        specific_logger = logging.getLogger(logger_name)
        specific_logger.addHandler(json_handler)

    print("📝 Logging serveur JSON activé!")
    logger.log("INFO", "Logging serveur JSON initialisé", "system")


def flush_server_logs():
    """Force l'écriture de tous les logs"""
    logger = get_server_logger()
    logger.flush()


def get_server_logs(date: str = None) -> list:
    """
    Récupère les logs serveur d'une date

    Args:
        date: Date au format YYYY-MM-DD (défaut: aujourd'hui)

    Returns:
        Liste des logs
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    log_file = Path("logs/server") / f"server_{date}.json"

    if not log_file.exists():
        return []

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Erreur lecture logs: {e}")
        return []


# ============================================================================
# UTILITAIRES CLI
# ============================================================================

def print_server_logs(date: str = None, level: str = None, source: str = None):
    """
    Affiche les logs serveur

    Args:
        date: Date au format YYYY-MM-DD
        level: Filtrer par niveau (INFO, ERROR, etc.)
        source: Filtrer par source
    """
    logs = get_server_logs(date)

    if not logs:
        print(f"📭 Aucun log trouvé pour {date or 'aujourd hui'}")
        return

    # Filtrer
    if level:
        logs = [log for log in logs if log.get("level") == level.upper()]

    if source:
        logs = [log for log in logs if source.lower() in log.get("source", "").lower()]

    print(f"\n📊 {len(logs)} log(s) trouvé(s)\n")

    for log in logs:
        timestamp = log.get("timestamp", "N/A")
        level_str = log.get("level", "INFO")
        source_str = log.get("source", "unknown")
        message = log.get("message", "")

        # Couleur selon niveau
        color = {
            "DEBUG": "\033[36m",    # Cyan
            "INFO": "\033[32m",     # Vert
            "WARNING": "\033[33m",  # Jaune
            "ERROR": "\033[31m",    # Rouge
            "CRITICAL": "\033[35m"  # Magenta
        }.get(level_str, "\033[0m")

        reset = "\033[0m"

        print(f"{color}[{timestamp}] {level_str} - {source_str}{reset}")
        print(f"  {message}")

        # Afficher métadonnées si présentes
        metadata = log.get("metadata", {})
        if metadata and metadata != {}:
            print(f"  📎 Metadata: {json.dumps(metadata, indent=2)}")

        print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("""
Usage:
  python server_logger.py view [date] [level] [source]
  python server_logger.py stats [date]
  python server_logger.py errors [date]

Exemples:
  python server_logger.py view
  python server_logger.py view 2025-10-14
  python server_logger.py view 2025-10-14 ERROR
  python server_logger.py errors
  python server_logger.py stats
        """)
        sys.exit(1)

    command = sys.argv[1]
    date = sys.argv[2] if len(sys.argv) > 2 else None

    if command == "view":
        level = sys.argv[3] if len(sys.argv) > 3 else None
        source = sys.argv[4] if len(sys.argv) > 4 else None
        print_server_logs(date, level, source)

    elif command == "errors":
        print_server_logs(date, "ERROR")

    elif command == "stats":
        logs = get_server_logs(date)
        if logs:
            levels = {}
            sources = {}
            for log in logs:
                level = log.get("level", "UNKNOWN")
                source = log.get("source", "unknown")
                levels[level] = levels.get(level, 0) + 1
                sources[source] = sources.get(source, 0) + 1

            print(f"\n📊 Statistiques - {date or 'aujourd hui'}")
            print(f"\nTotal logs: {len(logs)}")
            print(f"\nPar niveau:")
            for level, count in sorted(levels.items()):
                print(f"  {level}: {count}")
            print(f"\nPar source:")
            for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {source}: {count}")
        else:
            print(f"📭 Aucun log trouvé")

    else:
        print(f"❌ Commande inconnue: {command}")

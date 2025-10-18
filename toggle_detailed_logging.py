#!/usr/bin/env python3
"""
🔧 SCRIPT DE CONFIGURATION DU LOGGING DÉTAILLÉ
Active/désactive le logging détaillé du système RAG
"""

import os
import sys
import json
from datetime import datetime

class LoggingConfigManager:
    """Gestionnaire de configuration du logging"""
    
    def __init__(self):
        self.config_file = "logging_config.json"
        self.default_config = {
            "detailed_logging_enabled": True,
            "log_level": "INFO",
            "save_logs_to_file": True,
            "log_retention_days": 7,
            "max_log_file_size_mb": 10,
            "log_console_output": True,
            "log_structured_output": True
        }
    
    def load_config(self) -> dict:
        """Charge la configuration"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Erreur lors du chargement de la config: {e}")
                return self.default_config.copy()
        else:
            return self.default_config.copy()
    
    def save_config(self, config: dict):
        """Sauvegarde la configuration"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"✅ Configuration sauvegardée dans {self.config_file}")
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde: {e}")
    
    def enable_detailed_logging(self):
        """Active le logging détaillé"""
        config = self.load_config()
        config["detailed_logging_enabled"] = True
        self.save_config(config)
        print("✅ Logging détaillé ACTIVÉ")
        print("   📊 Tous les logs RAG seront enregistrés")
        print("   📁 Les logs seront sauvegardés en JSON")
        print("   🔍 Utilisez 'python view_rag_logs.py' pour les visualiser")
    
    def disable_detailed_logging(self):
        """Désactive le logging détaillé"""
        config = self.load_config()
        config["detailed_logging_enabled"] = False
        self.save_config(config)
        print("❌ Logging détaillé DÉSACTIVÉ")
        print("   📊 Seuls les logs de base seront enregistrés")
        print("   ⚡ Performance améliorée")
    
    def set_log_level(self, level: str):
        """Définit le niveau de log"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if level.upper() not in valid_levels:
            print(f"❌ Niveau invalide. Niveaux valides: {', '.join(valid_levels)}")
            return
        
        config = self.load_config()
        config["log_level"] = level.upper()
        self.save_config(config)
        print(f"✅ Niveau de log défini à: {level.upper()}")
    
    def set_log_retention(self, days: int):
        """Définit la rétention des logs"""
        if days < 1:
            print("❌ La rétention doit être d'au moins 1 jour")
            return
        
        config = self.load_config()
        config["log_retention_days"] = days
        self.save_config(config)
        print(f"✅ Rétention des logs définie à: {days} jours")
    
    def set_max_log_size(self, size_mb: int):
        """Définit la taille maximale des fichiers de logs"""
        if size_mb < 1:
            print("❌ La taille doit être d'au moins 1 MB")
            return
        
        config = self.load_config()
        config["max_log_file_size_mb"] = size_mb
        self.save_config(config)
        print(f"✅ Taille maximale des logs définie à: {size_mb} MB")
    
    def show_status(self):
        """Affiche le statut actuel"""
        config = self.load_config()
        
        print("📊 STATUT DU LOGGING DÉTAILLÉ")
        print("=" * 40)
        print(f"   État: {'✅ ACTIVÉ' if config['detailed_logging_enabled'] else '❌ DÉSACTIVÉ'}")
        print(f"   Niveau: {config['log_level']}")
        print(f"   Sauvegarde fichier: {'✅ OUI' if config['save_logs_to_file'] else '❌ NON'}")
        print(f"   Rétention: {config['log_retention_days']} jours")
        print(f"   Taille max: {config['max_log_file_size_mb']} MB")
        print(f"   Console: {'✅ OUI' if config['log_console_output'] else '❌ NON'}")
        print(f"   JSON: {'✅ OUI' if config['log_structured_output'] else '❌ NON'}")
    
    def cleanup_old_logs(self):
        """Nettoie les anciens logs"""
        config = self.load_config()
        retention_days = config.get("log_retention_days", 7)
        
        import time
        current_time = time.time()
        cutoff_time = current_time - (retention_days * 24 * 60 * 60)
        
        cleaned_count = 0
        for file in os.listdir("."):
            if file.startswith("rag_detailed_logs_") and file.endswith(".json"):
                file_path = os.path.join(".", file)
                if os.path.getmtime(file_path) < cutoff_time:
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                        print(f"🗑️  Supprimé: {file}")
                    except Exception as e:
                        print(f"❌ Erreur suppression {file}: {e}")
        
        print(f"✅ Nettoyage terminé: {cleaned_count} fichiers supprimés")
    
    def show_help(self):
        """Affiche l'aide"""
        print("🔧 CONFIGURATION DU LOGGING DÉTAILLÉ RAG")
        print("=" * 50)
        print("Commandes disponibles:")
        print("  enable          - Active le logging détaillé")
        print("  disable         - Désactive le logging détaillé")
        print("  status          - Affiche le statut actuel")
        print("  level <niveau>  - Définit le niveau de log (DEBUG, INFO, WARNING, ERROR)")
        print("  retention <jours> - Définit la rétention en jours")
        print("  size <mb>       - Définit la taille max des fichiers en MB")
        print("  cleanup         - Nettoie les anciens logs")
        print("  help            - Affiche cette aide")
        print("\nExemples:")
        print("  python toggle_detailed_logging.py enable")
        print("  python toggle_detailed_logging.py level DEBUG")
        print("  python toggle_detailed_logging.py retention 14")
        print("  python toggle_detailed_logging.py cleanup")

def main():
    """Fonction principale"""
    if len(sys.argv) < 2:
        print("❌ Commande requise. Utilisez 'help' pour voir les options.")
        return
    
    manager = LoggingConfigManager()
    command = sys.argv[1].lower()
    
    if command == "enable":
        manager.enable_detailed_logging()
    
    elif command == "disable":
        manager.disable_detailed_logging()
    
    elif command == "status":
        manager.show_status()
    
    elif command == "level":
        if len(sys.argv) < 3:
            print("❌ Niveau requis. Ex: level DEBUG")
        else:
            manager.set_log_level(sys.argv[2])
    
    elif command == "retention":
        if len(sys.argv) < 3:
            print("❌ Nombre de jours requis. Ex: retention 7")
        else:
            try:
                days = int(sys.argv[2])
                manager.set_log_retention(days)
            except ValueError:
                print("❌ Nombre de jours invalide")
    
    elif command == "size":
        if len(sys.argv) < 3:
            print("❌ Taille en MB requise. Ex: size 10")
        else:
            try:
                size_mb = int(sys.argv[2])
                manager.set_max_log_size(size_mb)
            except ValueError:
                print("❌ Taille invalide")
    
    elif command == "cleanup":
        manager.cleanup_old_logs()
    
    elif command == "help":
        manager.show_help()
    
    else:
        print(f"❌ Commande inconnue: {command}")
        print("Utilisez 'help' pour voir les options disponibles.")

if __name__ == "__main__":
    main()

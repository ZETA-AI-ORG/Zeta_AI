#!/usr/bin/env python3
"""
📊 VISUALISEUR DE LOGS RAG DÉTAILLÉS
Interface pour visualiser et analyser les logs du système RAG
"""

import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any
import argparse

class RAGLogViewer:
    """Visualiseur de logs RAG détaillés"""
    
    def __init__(self):
        self.log_files = []
        self.logs_data = []
        
    def find_log_files(self, directory: str = ".") -> List[str]:
        """Trouve tous les fichiers de logs RAG"""
        log_files = []
        
        for file in os.listdir(directory):
            if file.startswith("rag_detailed_logs_") and file.endswith(".json"):
                log_files.append(os.path.join(directory, file))
        
        # Trier par date de modification (plus récent en premier)
        log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        return log_files
    
    def load_log_file(self, file_path: str) -> Dict[str, Any]:
        """Charge un fichier de logs"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Erreur lors du chargement de {file_path}: {e}")
            return None
    
    def display_log_summary(self, log_data: Dict[str, Any]):
        """Affiche un résumé des logs"""
        print(f"\n📊 RÉSUMÉ DES LOGS - {log_data.get('request_id', 'Unknown')}")
        print("=" * 60)
        
        print(f"🆔 Request ID: {log_data.get('request_id', 'Unknown')}")
        print(f"⏱️  Durée totale: {log_data.get('total_duration_ms', 0):.2f}ms")
        
        # Temps par étape
        stage_times = log_data.get('stage_times', {})
        if stage_times:
            print(f"\n📈 TEMPS PAR ÉTAPE:")
            for stage, time_ms in stage_times.items():
                print(f"   {stage}: {time_ms:.2f}ms")
        
        # Nombre de logs
        logs = log_data.get('logs', [])
        print(f"\n📝 NOMBRE DE LOGS: {len(logs)}")
        
        # Distribution par niveau
        levels = {}
        for log in logs:
            level = log.get('level', 'UNKNOWN')
            levels[level] = levels.get(level, 0) + 1
        
        if levels:
            print(f"\n📊 DISTRIBUTION PAR NIVEAU:")
            for level, count in levels.items():
                print(f"   {level}: {count}")
    
    def display_detailed_logs(self, log_data: Dict[str, Any], filter_level: str = None, filter_stage: str = None):
        """Affiche les logs détaillés"""
        logs = log_data.get('logs', [])
        
        if not logs:
            print("❌ Aucun log trouvé")
            return
        
        print(f"\n📋 LOGS DÉTAILLÉS")
        print("=" * 80)
        
        for i, log in enumerate(logs, 1):
            # Filtres
            if filter_level and log.get('level', '').upper() != filter_level.upper():
                continue
            if filter_stage and filter_stage.lower() not in log.get('stage', '').lower():
                continue
            
            timestamp = log.get('timestamp', 'Unknown')
            stage = log.get('stage', 'Unknown')
            step = log.get('step', 'Unknown')
            level = log.get('level', 'Unknown')
            message = log.get('message', 'No message')
            data = log.get('data', {})
            
            # Couleur selon le niveau
            level_color = {
                'ERROR': '❌',
                'WARNING': '⚠️',
                'INFO': 'ℹ️',
                'DEBUG': '🔍'
            }.get(level, '📝')
            
            print(f"\n{i:3d}. {level_color} {timestamp}")
            print(f"     Stage: {stage}.{step}")
            print(f"     Message: {message}")
            
            if data:
                print(f"     Data:")
                for key, value in data.items():
                    if isinstance(value, (dict, list)) and len(str(value)) > 100:
                        print(f"       {key}: {str(value)[:100]}...")
                    else:
                        print(f"       {key}: {value}")
    
    def display_timeline(self, log_data: Dict[str, Any]):
        """Affiche une timeline des événements"""
        logs = log_data.get('logs', [])
        
        if not logs:
            print("❌ Aucun log trouvé pour la timeline")
            return
        
        print(f"\n⏰ TIMELINE DES ÉVÉNEMENTS")
        print("=" * 80)
        
        # Grouper par stage
        stages = {}
        for log in logs:
            stage = log.get('stage', 'Unknown')
            if stage not in stages:
                stages[stage] = []
            stages[stage].append(log)
        
        for stage, stage_logs in stages.items():
            print(f"\n🎯 {stage.upper()}")
            print("-" * 40)
            
            for log in stage_logs:
                timestamp = log.get('timestamp', 'Unknown')
                step = log.get('step', 'Unknown')
                message = log.get('message', 'No message')
                level = log.get('level', 'Unknown')
                
                level_icon = {
                    'ERROR': '❌',
                    'WARNING': '⚠️',
                    'INFO': 'ℹ️',
                    'DEBUG': '🔍'
                }.get(level, '📝')
                
                print(f"  {level_icon} {timestamp} | {step} | {message}")
    
    def analyze_performance(self, log_data: Dict[str, Any]):
        """Analyse les performances"""
        stage_times = log_data.get('stage_times', {})
        total_time = log_data.get('total_duration_ms', 0)
        
        if not stage_times or total_time == 0:
            print("❌ Pas de données de performance disponibles")
            return
        
        print(f"\n⚡ ANALYSE DE PERFORMANCE")
        print("=" * 50)
        
        print(f"⏱️  Temps total: {total_time:.2f}ms")
        
        # Tri par temps décroissant
        sorted_stages = sorted(stage_times.items(), key=lambda x: x[1], reverse=True)
        
        print(f"\n📊 TEMPS PAR ÉTAPE (du plus long au plus court):")
        for stage, time_ms in sorted_stages:
            percentage = (time_ms / total_time) * 100 if total_time > 0 else 0
            bar = "█" * int(percentage / 2)  # Barre de 50 caractères max
            print(f"   {stage:20s}: {time_ms:6.2f}ms ({percentage:5.1f}%) {bar}")
        
        # Recommandations
        print(f"\n💡 RECOMMANDATIONS:")
        
        # Identifier les goulots d'étranglement
        bottleneck_threshold = total_time * 0.3  # 30% du temps total
        bottlenecks = [stage for stage, time_ms in stage_times.items() if time_ms > bottleneck_threshold]
        
        if bottlenecks:
            print(f"   ⚠️  Goulots d'étranglement détectés: {', '.join(bottlenecks)}")
            print(f"   🔧 Considérer l'optimisation de ces étapes")
        else:
            print(f"   ✅ Aucun goulot d'étranglement majeur détecté")
        
        # Temps de traitement global
        if total_time > 5000:  # 5 secondes
            print(f"   ⚠️  Temps de traitement élevé ({total_time:.0f}ms)")
            print(f"   🔧 Considérer l'optimisation globale")
        elif total_time < 1000:  # 1 seconde
            print(f"   ✅ Temps de traitement excellent ({total_time:.0f}ms)")
        else:
            print(f"   ✅ Temps de traitement acceptable ({total_time:.0f}ms)")
    
    def export_logs(self, log_data: Dict[str, Any], output_file: str):
        """Exporte les logs dans un format lisible"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# LOGS RAG DÉTAILLÉS - {log_data.get('request_id', 'Unknown')}\n")
                f.write(f"# Généré le: {datetime.now().isoformat()}\n")
                f.write(f"# Durée totale: {log_data.get('total_duration_ms', 0):.2f}ms\n\n")
                
                logs = log_data.get('logs', [])
                for i, log in enumerate(logs, 1):
                    f.write(f"## {i}. {log.get('stage', 'Unknown')}.{log.get('step', 'Unknown')}\n")
                    f.write(f"**Timestamp:** {log.get('timestamp', 'Unknown')}\n")
                    f.write(f"**Niveau:** {log.get('level', 'Unknown')}\n")
                    f.write(f"**Message:** {log.get('message', 'No message')}\n")
                    
                    data = log.get('data', {})
                    if data:
                        f.write(f"**Données:**\n")
                        for key, value in data.items():
                            f.write(f"- {key}: {value}\n")
                    
                    f.write("\n")
            
            print(f"✅ Logs exportés dans: {output_file}")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'export: {e}")

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Visualiseur de logs RAG détaillés")
    parser.add_argument("--file", "-f", help="Fichier de logs spécifique")
    parser.add_argument("--level", "-l", help="Filtrer par niveau (ERROR, WARNING, INFO, DEBUG)")
    parser.add_argument("--stage", "-s", help="Filtrer par stage")
    parser.add_argument("--timeline", "-t", action="store_true", help="Afficher la timeline")
    parser.add_argument("--performance", "-p", action="store_true", help="Analyser les performances")
    parser.add_argument("--export", "-e", help="Exporter vers un fichier")
    parser.add_argument("--list", action="store_true", help="Lister tous les fichiers de logs")
    
    args = parser.parse_args()
    
    viewer = RAGLogViewer()
    
    # Lister les fichiers de logs
    if args.list:
        log_files = viewer.find_log_files()
        print("📁 FICHIERS DE LOGS DISPONIBLES:")
        for i, file in enumerate(log_files, 1):
            mtime = datetime.fromtimestamp(os.path.getmtime(file))
            print(f"  {i}. {file} (modifié: {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
        return
    
    # Charger le fichier de logs
    if args.file:
        log_data = viewer.load_log_file(args.file)
    else:
        log_files = viewer.find_log_files()
        if not log_files:
            print("❌ Aucun fichier de logs trouvé")
            return
        
        print(f"📁 Chargement du fichier le plus récent: {log_files[0]}")
        log_data = viewer.load_log_file(log_files[0])
    
    if not log_data:
        print("❌ Impossible de charger les logs")
        return
    
    # Affichage selon les options
    viewer.display_log_summary(log_data)
    
    if args.timeline:
        viewer.display_timeline(log_data)
    
    if args.performance:
        viewer.analyze_performance(log_data)
    
    if args.level or args.stage:
        viewer.display_detailed_logs(log_data, args.level, args.stage)
    elif not args.timeline and not args.performance:
        # Affichage par défaut
        viewer.display_detailed_logs(log_data)
    
    if args.export:
        viewer.export_logs(log_data, args.export)

if __name__ == "__main__":
    main()

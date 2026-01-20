#!/usr/bin/env python3
"""
📡 CAPTURE SERVEUR - Redirige TOUS les logs serveur vers un fichier

Ce script lance le serveur et capture TOUT ce qui est affiché.
"""

import subprocess
import sys
import os
from datetime import datetime

def capture_server_logs(output_file: str = None):
    """
    Lance le serveur et capture tous les logs dans un fichier
    
    Args:
        output_file: Chemin du fichier de sortie (défaut: logs/server_TIMESTAMP.log)
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"logs/server_{timestamp}.log"
    
    # Créer le dossier logs si nécessaire
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    print(f"🎬 Lancement du serveur avec capture logs...")
    print(f"📝 Logs sauvegardés dans: {output_file}")
    print(f"⏹️  Appuyez sur Ctrl+C pour arrêter\n")
    
    # Lancer le serveur avec redirection complète
    with open(output_file, 'w', encoding='utf-8', buffering=1) as log_file:
        try:
            # Lancer uvicorn avec capture stdout/stderr
            process = subprocess.Popen(
                ["uvicorn", "app:app", "--reload", "--host", "0.0.0.0", "--port", "8002"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1,
                universal_newlines=True
            )
            
            # Lire et afficher en temps réel
            for line in iter(process.stdout.readline, ''):
                if line:
                    # Afficher dans le terminal
                    print(line, end='')
                    # Écrire dans le fichier
                    log_file.write(line)
                    log_file.flush()
            
            process.wait()
            
        except KeyboardInterrupt:
            print("\n\n⏹️  Arrêt du serveur...")
            process.terminate()
            process.wait()
            print(f"✅ Logs sauvegardés: {output_file}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Lance le serveur avec capture de logs")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Fichier de sortie pour les logs"
    )
    
    args = parser.parse_args()
    
    capture_server_logs(args.output)

#!/usr/bin/env python3
"""
🚀 SCRIPT DE DÉPLOIEMENT DES CACHES OPTIMISÉS
Objectif: Synchroniser tous les fichiers de cache sur le serveur Ubuntu
Performance attendue: 19.6s → 7.3s (gain de 12.3s par requête)
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Exécute une commande et affiche le résultat"""
    print(f"\n🔄 {description}")
    print(f"Commande: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {description} - SUCCÈS")
            if result.stdout:
                print(f"Output: {result.stdout.strip()}")
        else:
            print(f"❌ {description} - ÉCHEC")
            print(f"Erreur: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ {description} - EXCEPTION: {e}")
        return False
    
    return True

def main():
    """Déploiement complet des caches optimisés"""
    print("🚀 DÉPLOIEMENT DES CACHES OPTIMISÉS SCALABLES")
    print("=" * 60)
    
    # Chemin de base
    base_path = Path(__file__).parent
    ubuntu_path = "~/ZETA_APP/CHATBOT2.0"
    
    # Liste des fichiers à synchroniser
    files_to_sync = [
        # Nouveaux fichiers de cache
        ("core/global_prompt_cache.py", "core/global_prompt_cache.py"),
        ("core/global_embedding_cache_optimized.py", "core/global_embedding_cache_optimized.py"),
        ("core/global_model_cache.py", "core/global_model_cache.py"),
        ("core/unified_cache_system.py", "core/unified_cache_system.py"),
        ("routes/cache_monitoring.py", "routes/cache_monitoring.py"),
        
        # Fichiers modifiés
        ("database/supabase_client.py", "database/supabase_client.py"),
        ("embedding_models.py", "embedding_models.py"),
        ("app.py", "app.py"),
        ("core/rag_engine_simplified_fixed.py", "core/rag_engine_simplified_fixed.py"),
        
        # Script de déploiement
        ("deploy_optimized_caches.py", "deploy_optimized_caches.py")
    ]
    
    print(f"📁 Fichiers à synchroniser: {len(files_to_sync)}")
    print("📋 Liste des fichiers:")
    for local_file, remote_file in files_to_sync:
        print(f"  - {local_file} → {remote_file}")
    
    print("\n" + "=" * 60)
    
    # Vérifier que les fichiers existent localement
    missing_files = []
    for local_file, _ in files_to_sync:
        if not (base_path / local_file).exists():
            missing_files.append(local_file)
    
    if missing_files:
        print("❌ FICHIERS MANQUANTS:")
        for file in missing_files:
            print(f"  - {file}")
        print("\nArrêt du déploiement - fichiers manquants")
        return False
    
    print("✅ Tous les fichiers locaux existent")
    
    # Commandes de synchronisation
    sync_commands = []
    
    for local_file, remote_file in files_to_sync:
        local_path = str(base_path / local_file).replace('\\', '/')
        remote_path = f"{ubuntu_path}/{remote_file}"
        
        # Utiliser cp pour copier les fichiers
        command = f'cp -v "{local_path}" "{remote_path}"'
        sync_commands.append((command, f"Synchronisation {local_file}"))
    
    # Exécuter les synchronisations
    success_count = 0
    for command, description in sync_commands:
        if run_command(command, description):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"📊 RÉSULTATS DE LA SYNCHRONISATION:")
    print(f"✅ Succès: {success_count}/{len(sync_commands)}")
    print(f"❌ Échecs: {len(sync_commands) - success_count}/{len(sync_commands)}")
    
    if success_count == len(sync_commands):
        print("\n🎉 SYNCHRONISATION COMPLÈTE RÉUSSIE!")
        
        # Commandes post-déploiement
        post_commands = [
            ("rm -rf ~/ZETA_APP/CHATBOT2.0/core/__pycache__/", "Nettoyage cache Python core"),
            ("rm -rf ~/ZETA_APP/CHATBOT2.0/database/__pycache__/", "Nettoyage cache Python database"),
            ("rm -rf ~/ZETA_APP/CHATBOT2.0/routes/__pycache__/", "Nettoyage cache Python routes"),
            ("rm -rf ~/ZETA_APP/CHATBOT2.0/__pycache__/", "Nettoyage cache Python racine")
        ]
        
        print("\n🧹 NETTOYAGE POST-DÉPLOIEMENT:")
        cleanup_success = 0
        for command, description in post_commands:
            if run_command(command, description):
                cleanup_success += 1
        
        print(f"\n🧹 Nettoyage: {cleanup_success}/{len(post_commands)} succès")
        
        # Instructions finales
        print("\n" + "=" * 60)
        print("🚀 DÉPLOIEMENT TERMINÉ - ACTIONS SUIVANTES:")
        print("\n1. Redémarrer le serveur FastAPI:")
        print("   pkill -f 'uvicorn.*app:app'")
        print("   cd ~/ZETA_APP/CHATBOT2.0")
        print("   uvicorn app:app --host 127.0.0.1 --port 8001 --reload")
        
        print("\n2. Tester les nouveaux endpoints de monitoring:")
        print("   curl http://127.0.0.1:8001/api/cache/stats")
        print("   curl http://127.0.0.1:8001/api/cache/health")
        print("   curl http://127.0.0.1:8001/api/cache/performance")
        
        print("\n3. Vérifier les performances:")
        print("   - Temps attendu: 19.6s → 7.3s")
        print("   - Gain: 12.3s par requête (63% d'amélioration)")
        print("   - Cache hits attendus: >80% après quelques requêtes")
        
        print("\n📈 GAINS DE PERFORMANCE ATTENDUS:")
        print("   🚀 Cache prompt: 2.1s → 0.01s")
        print("   🚀 Cache embedding: 1.9s → 0.01s")
        print("   🚀 Cache modèle: 8.3s → 0s (après 1er chargement)")
        print("   🚀 Total: 12.3s économisés par requête")
        
        return True
    else:
        print("\n❌ SYNCHRONISATION INCOMPLÈTE")
        print("Vérifiez les erreurs ci-dessus et relancez le script")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

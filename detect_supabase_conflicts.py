#!/usr/bin/env python3
"""
🕵️ DÉTECTEUR DE CONFLITS SUPABASE
Script pour identifier tous les doublons et conflits dans le système Supabase
"""
import os
import re
from pathlib import Path

def scan_supabase_conflicts():
    """Scan complet pour détecter les conflits Supabase"""
    
    print("\033[1;34m🕵️ DÉTECTEUR DE CONFLITS SUPABASE\033[0m")
    print("=" * 60)
    
    root_dir = Path(".")
    print(f"📁 Répertoire scanné: {root_dir.resolve()}")
    print()
    
    rag_engine_files = []
    old_method_files = []
    supabase_files = []

    # Scan récursif en ignorant .venv
    for file_path in root_dir.rglob('*.py'):
        # Ignorer le répertoire .venv
        if '.venv' in file_path.parts:
            continue

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            if re.search(r'supabase', content, re.IGNORECASE):
                supabase_files.append(file_path)
            
            if 'rag_engine' in file_path.name:
                rag_engine_files.append(file_path)

            if 'match_documents_via_rpc' in content:
                old_method_files.append(file_path)

        except Exception as e:
            # Cette exception ne devrait plus se produire avec errors='ignore'
            print(f"\033[31m❌ Erreur de lecture sur {file_path}: {e}\033[0m")
    
    # RAPPORT DÉTAILLÉ
    print("\n\033[1;32m📊 RAPPORT DE CONFLITS\033[0m")
    print("=" * 60)
    
    print(f"\n1️⃣ \033[4mFichiers RAG Engine ({len(rag_engine_files)})\033[0m")
    for f in sorted(rag_engine_files):
        print(f"   📄 {f}")
    if len(rag_engine_files) > 1:
        print("\033[93m⚠️ CONFLIT POTENTIEL: Plusieurs fichiers RAG Engine détectés!\033[0m")

    print(f"\n2️⃣ \033[4mFichiers avec l'ancienne méthode 'match_documents_via_rpc' ({len(old_method_files)})\033[0m")
    if not old_method_files:
        print("   ✅ Aucun fichier trouvé. C'est bon signe!")
    else:
        for f in sorted(old_method_files):
            print(f"   📄 \033[91m{f}\033[0m")
        print("\033[91m❌ CRITIQUE: Ces fichiers utilisent encore l'ancien code!\033[0m")

    print(f"\n3️⃣ \033[4mTous les fichiers liés à Supabase ({len(supabase_files)})\033[0m")
    for f in sorted(supabase_files):
        print(f"   📄 {f}")

    print("\n\033[1m🔎 NETTOYAGE CACHE PYTHON RECOMMANDÉ\033[0m")
    print("find . -type d -name '__pycache__' -exec rm -rf {} + ")
    print("=" * 60)

if __name__ == "__main__":
    scan_supabase_conflicts()

#!/usr/bin/env python3
"""
🔥 RESTAURATION COMPLÈTE DE L'ANCIEN SYSTÈME MEILISEARCH
Remplace le système actuel défaillant par l'ancien système performant
"""

import os
import shutil
from datetime import datetime

def backup_current_system():
    """Sauvegarde le système actuel avant remplacement"""
    print("💾 SAUVEGARDE DU SYSTÈME ACTUEL...")
    
    backup_dir = f"backup_current_system_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        "core/smart_stopwords.py",
        "database/vector_store.py", 
        "core/preprocessing.py",
        "database/vector_store_clean.py",
        "database/vector_store_optimized.py"
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            shutil.copy2(file_path, f"{backup_dir}/{os.path.basename(file_path)}")
            print(f"   ✅ Sauvegardé: {file_path}")
    
    print(f"📁 Sauvegarde dans: {backup_dir}")
    return backup_dir

def create_old_stopwords_system():
    """Recrée l'ancien système de stop words simple et efficace"""
    print("🧹 RESTAURATION ANCIEN SYSTÈME STOP WORDS...")
    
    old_stopwords_content = '''#!/usr/bin/env python3
"""
🟢 ANCIEN SYSTÈME STOP WORDS - SIMPLE ET EFFICACE
Liste réduite et optimisée pour l'e-commerce
"""

# === STOP WORDS ESSENTIELS UNIQUEMENT ===
STOP_WORDS_SIMPLE = [
    # Salutations
    "bonjour", "bonsoir", "salut", "hello", "hi", "merci", "svp",
    "au", "revoir", "à", "bientôt",
    
    # Articles et déterminants
    "le", "la", "les", "un", "une", "des", "du", "de", "d'",
    "ce", "cet", "cette", "ces",
    
    # Prépositions courantes
    "à", "au", "aux", "en", "dans", "sur", "avec", "sans", "pour", "par",
    
    # Conjonctions
    "et", "ou", "mais", "donc", "que", "qui", "quoi",
    
    # Pronoms
    "je", "j'", "tu", "il", "elle", "nous", "vous", "ils", "elles",
    "me", "te", "se", "lui", "leur", "moi", "toi",
    
    # Verbes auxiliaires fréquents
    "est", "suis", "es", "sont", "était", "sera", "ai", "as", "a", "ont",
    "avoir", "être", "faire", "aller",
    
    # Mots de liaison
    "alors", "donc", "ainsi", "aussi", "très", "trop", "assez",
    
    # Expressions de politesse
    "s'il", "vous", "plaît", "excusez", "moi", "pardon", "désolé",
    
    # Mots vides courants
    "c'est", "il", "y", "a", "voici", "voilà", "bon", "ok", "d'accord"
]

# === MOTS À TOUJOURS PRÉSERVER ===
KEEP_WORDS_CRITICAL = [
    # Prix et commerce
    "prix", "coût", "coûte", "combien", "tarif", "fcfa", "gratuit",
    
    # Actions commerciales
    "acheter", "vendre", "commander", "payer", "livraison", "livrer",
    
    # Produits
    "couches", "taille", "pression", "culottes", "adultes", "bébé",
    "paquet", "paquets", "colis", "unité", "unités",
    
    # Quantités et tailles
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "12", "48",
    "kg", "kilos", "grammes",
    
    # Zones géographiques
    "abidjan", "cocody", "yopougon", "plateau", "adjamé", "marcory",
    "port-bouët", "grand-bassam", "anyama", "bingerville",
    
    # Services
    "wave", "whatsapp", "téléphone", "contact", "support", "retour",
    "disponible", "stock", "délai", "rapide"
]

def filter_query_simple(query: str) -> str:
    """
    🎯 FILTRAGE SIMPLE ET EFFICACE
    Supprime uniquement les mots vraiment inutiles
    """
    if not query or not query.strip():
        return query
    
    # Nettoyer et diviser
    words = query.lower().strip().split()
    filtered_words = []
    
    for word in words:
        word = word.strip()
        if not word:
            continue
            
        # GARDER si c'est un mot critique
        if word in KEEP_WORDS_CRITICAL:
            filtered_words.append(word)
            continue
            
        # GARDER si ce n'est PAS un stop word
        if word not in STOP_WORDS_SIMPLE:
            filtered_words.append(word)
    
    result = ' '.join(filtered_words).strip()
    
    # Fallback de sécurité
    if not result or len(result) < 2:
        # Garder les mots > 2 caractères
        essential = [w for w in words if len(w) > 2]
        return ' '.join(essential) if essential else query.strip()
    
    return result

# Test rapide
if __name__ == "__main__":
    test_queries = [
        "bonjour combien coûte taille 3",
        "je veux acheter couches adultes",
        "livraison cocody wave paiement"
    ]
    
    for q in test_queries:
        filtered = filter_query_simple(q)
        print(f"'{q}' → '{filtered}'")
'''
    
    with open("core/simple_stopwords.py", "w", encoding="utf-8") as f:
        f.write(old_stopwords_content)
    
    print("   ✅ Ancien système stop words créé")

def create_old_vector_store():
    """Recrée l'ancien système vector_store performant"""
    print("🔍 RESTAURATION ANCIEN VECTOR STORE...")
    
    old_vector_store_content = '''import time
import os
from typing import Optional, List, Dict, Any
import meilisearch
from embedding_models import embed_text, get_embedding_model
import unicodedata
from utils import log3, timing_metric

# Configuration MeiliSearch
MEILI_URL = "http://localhost:7700"
MEILI_API_KEY = "Bac2018mado@2066"
client = meilisearch.Client(MEILI_URL, MEILI_API_KEY)

async def search_meili_keywords_old(query: str, company_id: str, limit: int = 10) -> List[Dict]:
    """
    🎯 ANCIEN SYSTÈME MEILISEARCH - SIMPLE ET EFFICACE
    """
    try:
        # Import du filtrage simple
        from core.simple_stopwords import filter_query_simple
        
        # Filtrage léger
        filtered_query = filter_query_simple(query)
        log3("[MEILI_OLD]", f"Query: '{query}' → Filtered: '{filtered_query}'")
        
        if not filtered_query or len(filtered_query.strip()) < 2:
            log3("[MEILI_OLD]", "Query trop courte après filtrage, utilisation originale")
            filtered_query = query
        
        # Recherche dans tous les index pertinents
        all_results = []
        indexes_to_search = [
            f"products_{company_id}",
            f"delivery_{company_id}", 
            f"support_{company_id}",
            f"company_docs_{company_id}"
        ]
        
        for index_name in indexes_to_search:
            try:
                index = client.index(index_name)
                
                # Recherche simple et directe
                search_results = index.search(filtered_query, {
                    'limit': limit,
                    'attributesToHighlight': ['*'],
                    'attributesToRetrieve': ['*']
                })
                
                if search_results.get('hits'):
                    for hit in search_results['hits']:
                        hit['_index'] = index_name
                        hit['_score'] = hit.get('_rankingScore', 1.0)
                        all_results.append(hit)
                        
                    log3("[MEILI_OLD]", f"Index {index_name}: {len(search_results['hits'])} résultats")
                
            except Exception as e:
                log3("[MEILI_OLD]", f"Erreur index {index_name}: {str(e)[:50]}")
                continue
        
        # Trier par score et limiter
        all_results.sort(key=lambda x: x.get('_score', 0), reverse=True)
        final_results = all_results[:limit]
        
        log3("[MEILI_OLD]", f"Total: {len(final_results)} documents trouvés")
        return final_results
        
    except Exception as e:
        log3("[MEILI_OLD]", f"Erreur générale: {e}")
        return []

# Alias pour compatibilité
search_meili_keywords = search_meili_keywords_old
'''
    
    with open("database/vector_store_old_restored.py", "w", encoding="utf-8") as f:
        f.write(old_vector_store_content)
    
    print("   ✅ Ancien vector store créé")

def update_main_imports():
    """Met à jour les imports pour utiliser l'ancien système"""
    print("🔄 MISE À JOUR DES IMPORTS...")
    
    # Lire le fichier app.py actuel
    if os.path.exists("app.py"):
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Remplacer les imports
        content = content.replace(
            "from database.vector_store import search_meili_keywords",
            "from database.vector_store_old_restored import search_meili_keywords"
        )
        
        content = content.replace(
            "from core.smart_stopwords import filter_query_for_meilisearch",
            "from core.simple_stopwords import filter_query_simple"
        )
        
        # Sauvegarder
        with open("app.py", "w", encoding="utf-8") as f:
            f.write(content)
        
        print("   ✅ app.py mis à jour")

def create_sync_script():
    """Crée le script de synchronisation Ubuntu"""
    print("📋 CRÉATION SCRIPT SYNCHRONISATION...")
    
    sync_content = '''#!/bin/bash
# 🔥 SYNCHRONISATION ANCIEN SYSTÈME MEILISEARCH

echo "🔥 RESTAURATION ANCIEN SYSTÈME MEILISEARCH..."

# Synchroniser les nouveaux fichiers
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/core/simple_stopwords.py" ~/ZETA_APP/CHATBOT2.0/core/simple_stopwords.py

cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/database/vector_store_old_restored.py" ~/ZETA_APP/CHATBOT2.0/database/vector_store_old_restored.py

cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/app.py" ~/ZETA_APP/CHATBOT2.0/app.py

echo "✅ ANCIEN SYSTÈME RESTAURÉ !"
echo ""
echo "🧪 TESTER MAINTENANT:"
echo "python test_meili_ultimate_diagnostic.py"
'''
    
    with open("sync_old_meili_system.sh", "w", encoding="utf-8") as f:
        f.write(sync_content)
    
    print("   ✅ Script de sync créé")

def main():
    """Point d'entrée principal"""
    print("🔥 RESTAURATION COMPLÈTE ANCIEN SYSTÈME MEILISEARCH")
    print("=" * 60)
    
    # 1. Sauvegarde
    backup_dir = backup_current_system()
    
    # 2. Création ancien système stop words
    create_old_stopwords_system()
    
    # 3. Création ancien vector store
    create_old_vector_store()
    
    # 4. Mise à jour imports
    update_main_imports()
    
    # 5. Script de synchronisation
    create_sync_script()
    
    print("\n" + "=" * 60)
    print("✅ RESTAURATION TERMINÉE !")
    print(f"💾 Sauvegarde dans: {backup_dir}")
    print("🚀 Synchroniser avec:")
    print("   ./sync_old_meili_system.sh")
    print("=" * 60)

if __name__ == "__main__":
    main()

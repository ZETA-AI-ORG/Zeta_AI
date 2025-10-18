#!/usr/bin/env python3
"""
Commande pour afficher tous les mots scorés par HyDE
Usage: python show_hyde_scores.py [--query "texte"] [--company-id "id"]
"""

import asyncio
import argparse
import sys
import os
import json
from typing import Dict, List

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.hyde_word_scorer import HydeWordScorer

def print_scores_table(word_scores: Dict[str, int], title: str = "MOTS SCORÉS HYDE"):
    """Affiche les scores dans un tableau formaté"""
    
    if not word_scores:
        print("❌ Aucun mot scoré trouvé")
        return
    
    # Trier par score décroissant
    sorted_scores = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\n🎯 {title}")
    print("=" * 80)
    
    # Grouper par catégories de score
    categories = {
        "🔥 ESSENTIELS (10)": [],
        "✅ TRÈS PERTINENTS (8-9)": [],
        "⚠️ CONTEXTUELS (6-7)": [],
        "🔸 FAIBLE PERTINENCE (3-5)": [],
        "❌ STOP WORDS/NOMBRES (0-2)": []
    }
    
    for word, score in sorted_scores:
        if score == 10:
            categories["🔥 ESSENTIELS (10)"].append((word, score))
        elif score >= 8:
            categories["✅ TRÈS PERTINENTS (8-9)"].append((word, score))
        elif score >= 6:
            categories["⚠️ CONTEXTUELS (6-7)"].append((word, score))
        elif score >= 3:
            categories["🔸 FAIBLE PERTINENCE (3-5)"].append((word, score))
        else:
            categories["❌ STOP WORDS/NOMBRES (0-2)"].append((word, score))
    
    # Afficher chaque catégorie
    for category, words in categories.items():
        if words:
            print(f"\n{category} ({len(words)} mots)")
            print("-" * 50)
            
            # Afficher en colonnes
            for i, (word, score) in enumerate(words):
                if i % 4 == 0 and i > 0:
                    print()
                print(f"{word}:{score}".ljust(18), end=" ")
            print("\n")
    
    # Statistiques
    scores_values = list(word_scores.values())
    print(f"📊 STATISTIQUES")
    print("-" * 50)
    print(f"Total mots: {len(word_scores)}")
    print(f"Score moyen: {sum(scores_values)/len(scores_values):.2f}")
    print(f"Score max: {max(scores_values)}")
    print(f"Score min: {min(scores_values)}")
    print(f"Mots essentiels (≥8): {len([s for s in scores_values if s >= 8])}")
    print(f"Mots faibles (≤2): {len([s for s in scores_values if s <= 2])}")

async def show_base_scores():
    """Affiche tous les mots du cache de base"""
    scorer = HydeWordScorer()
    
    print("📚 CACHE DE BASE HYDE (Mots pré-scorés)")
    print_scores_table(scorer.base_word_scores, "CACHE DE BASE")

async def score_custom_query(query: str):
    """Score une requête personnalisée"""
    scorer = HydeWordScorer()
    
    print(f"🔍 SCORING REQUÊTE: '{query}'")
    word_scores = await scorer.score_query_words(query)
    
    print_scores_table(word_scores, f"REQUÊTE: {query}")
    
    # Afficher la requête filtrée
    filtered_query = await scorer.smart_filter_query(query)
    print(f"\n🎯 REQUÊTE FILTRÉE: '{filtered_query}'")

async def load_company_cache(company_id: str):
    """Charge le cache d'une entreprise spécifique"""
    cache_file = f"word_caches/word_scores_{company_id}.json"
    
    if not os.path.exists(cache_file):
        print(f"❌ Cache non trouvé: {cache_file}")
        return
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        word_scores = cache_data.get('word_scores', {})
        stats = cache_data.get('stats', {})
        
        print(f"🏢 CACHE ENTREPRISE: {company_id}")
        print(f"📅 Créé le: {cache_data.get('created_at', 'N/A')}")
        print(f"📊 Documents analysés: {stats.get('documents_analyzed', 'N/A')}")
        
        # Convertir les scores en int si nécessaire
        word_scores_int = {k: int(v) for k, v in word_scores.items()}
        print_scores_table(word_scores_int, f"ENTREPRISE {company_id}")
        
    except Exception as e:
        print(f"❌ Erreur lecture cache: {e}")

def list_available_caches():
    """Liste tous les caches disponibles"""
    cache_dir = "word_caches"
    
    if not os.path.exists(cache_dir):
        print(f"❌ Répertoire cache non trouvé: {cache_dir}")
        return
    
    cache_files = [f for f in os.listdir(cache_dir) if f.startswith("word_scores_") and f.endswith(".json")]
    
    if not cache_files:
        print("❌ Aucun cache trouvé")
        return
    
    print(f"📁 CACHES DISPONIBLES ({len(cache_files)})")
    print("=" * 50)
    
    for cache_file in cache_files:
        company_id = cache_file.replace("word_scores_", "").replace(".json", "")
        file_path = os.path.join(cache_dir, cache_file)
        file_size = os.path.getsize(file_path)
        
        print(f"🏢 {company_id}")
        print(f"   📄 Fichier: {cache_file}")
        print(f"   📊 Taille: {file_size/1024:.1f} Ko")
        print()

async def main():
    parser = argparse.ArgumentParser(description="Afficher les mots scorés par HyDE")
    parser.add_argument("--query", "-q", help="Scorer une requête spécifique")
    parser.add_argument("--company-id", "-c", help="Afficher le cache d'une entreprise")
    parser.add_argument("--list-caches", "-l", action="store_true", help="Lister tous les caches disponibles")
    parser.add_argument("--base", "-b", action="store_true", help="Afficher le cache de base")
    
    args = parser.parse_args()
    
    print("🧠 VISUALISEUR SCORES HYDE")
    print("=" * 80)
    
    if args.list_caches:
        list_available_caches()
    elif args.company_id:
        await load_company_cache(args.company_id)
    elif args.query:
        await score_custom_query(args.query)
    elif args.base:
        await show_base_scores()
    else:
        # Affichage par défaut: cache de base
        await show_base_scores()
        
        # Lister les caches disponibles
        print("\n" + "=" * 80)
        list_available_caches()
        
        print("\n💡 USAGE:")
        print("python show_hyde_scores.py --query 'casque rouge 6500 fcfa'")
        print("python show_hyde_scores.py --company-id XkCn8fjNWEWwqiiKMgJX7OcQrUJ3")
        print("python show_hyde_scores.py --list-caches")
        print("python show_hyde_scores.py --base")

if __name__ == "__main__":
    asyncio.run(main())

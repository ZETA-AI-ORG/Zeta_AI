#!/usr/bin/env python3
"""
🧩 PUZZLE 3 : Test Scoring + Boosts (Isolé)

Objectif :
- Prendre des docs bruts en entrée (simulés)
- Appliquer le scoring complet (base + boosts)
- Vérifier que les scores sont cohérents (0-100)
- Vérifier que les boosts fonctionnent correctement

Usage :
    python test_scoring_puzzle3.py
"""

import sys
import os

# Ajouter le chemin du projet pour importer les modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unidecode import unidecode
from rapidfuzz import fuzz
import math
import re


# ========== FONCTIONS DE SCORING (copiées depuis vector_store_clean_v2.py) ==========

def _normalize(text):
    """Normalise le texte (lowercase + unidecode)"""
    return unidecode(text.lower().strip())


def _calculate_smart_score_v2(content: str, query: str, all_docs_corpus: list) -> dict:
    """
    Scoring intelligent : TF-IDF + BM25 (position) + Similarité fuzzy
    Retourne un score entre 0 et 100
    """
    content_norm = _normalize(content)
    query_norm = _normalize(query)
    query_words = query_norm.split()
    
    # TF-IDF simplifié
    tf_scores = []
    for word in query_words:
        tf = content_norm.count(word)
        # IDF : nombre de docs contenant le mot
        df = sum(1 for doc in all_docs_corpus if word in _normalize(doc))
        idf = math.log((len(all_docs_corpus) + 1) / (df + 1)) if df > 0 else 0
        tf_scores.append(tf * idf)
    
    tf_idf_score = sum(tf_scores) * 10  # Normalisation
    
    # BM25 : position des mots (bonus si en début de doc)
    position_bonus = 0
    content_words = content_norm.split()
    for word in query_words:
        if word in content_words:
            pos = content_words.index(word)
            # Bonus décroissant selon la position
            position_bonus += max(0, 10 - (pos / 10))
    
    # Similarité fuzzy globale
    fuzzy_score = fuzz.partial_ratio(query_norm, content_norm) / 2  # 0-50
    
    # Score final (PAS de plafond ici, on le fera après les boosts)
    base_score = tf_idf_score + position_bonus + fuzzy_score
    
    return {
        'score': base_score,
        'tf_idf': tf_idf_score,
        'position_bonus': position_bonus,
        'fuzzy': fuzzy_score
    }


def apply_id_boost(doc: dict, ngrams: list) -> int:
    """
    Boost si n-gram trouvé dans l'ID du document
    +10 par n-gram trouvé
    """
    doc_id = str(doc.get('id', '')).lower()
    boost = 0
    matched_ngrams = []
    
    for ng in ngrams:
        ng_norm = ng.lower().replace(' ', '')
        if ng_norm and doc_id and ng_norm in doc_id.replace(' ', ''):
            boost += 10
            matched_ngrams.append(ng)
    
    return boost, matched_ngrams


def apply_keyword_boost(doc: dict, query: str, boosters_keywords: list) -> int:
    """
    Boost si keywords trouvés dans le doc ET la query
    +2 par keyword (max +5)
    """
    content_lower = doc.get('content', '').lower()
    query_lower = query.lower()
    boost = 0
    matched_keywords = []
    
    for keyword in boosters_keywords:
        if keyword in query_lower and keyword in content_lower:
            boost += 2
            matched_keywords.append(keyword)
    
    return min(boost, 5), matched_keywords


def normalize_score(score: float) -> float:
    """Normalise le score final (plafond 100)"""
    return min(score, 100)


# ========== DONNÉES DE TEST ==========

# Simulation de docs bruts retournés par MeiliSearch
test_docs = [
    {
        'id': 'couches_a_pression_taille_4_9_a_14_kg_300_couches_24000_f_cfa_txt',
        'content': '''PRODUIT: Couches à pression
VARIANTE: Taille 4 - 9 à 14 kg - 300 couches | 24.000 F CFA
Catégorie: Bébé & Puériculture
Sous-catégorie: Soins Bébé - Couches
DÉTAILS VARIANTE:
- Prix: 24 000 FCFA
- Quantité: 300 pcs
- Description: Lot de 300 couches a pression en taille 4 idéal pour un enfant entre 9 à 14 kg''',
        'source_index': 'products_4OS4yFcf2LZwxhKojbAVbKuVuSdb'
    },
    {
        'id': 'couches_a_pression_taille_1_0_a_4_kg_300_couches_17900_f_cfa_txt',
        'content': '''PRODUIT: Couches à pression
VARIANTE: Taille 1 - 0 à 4 kg - 300 couches | 17.900 F CFA
Catégorie: Bébé & Puériculture
Sous-catégorie: Soins Bébé - Couches
DÉTAILS VARIANTE:
- Prix: 17 900 FCFA
- Quantité: 300 pcs
- Description: Lot de 300 couches a pression en taille 1 idéal pour un enfant entre 0 à 4 kg''',
        'source_index': 'products_4OS4yFcf2LZwxhKojbAVbKuVuSdb'
    },
    {
        'id': 'livraison_zones_peripheriques_txt',
        'content': '''LIVRAISON - ZONES PÉRIPHÉRIQUES ABIDJAN
- Port-Bouët : 2 000 FCFA
- Attécoubé : 2 000 FCFA
- Bingerville : 2 500 FCFA
- Songon : 2 500 FCFA
- Anyama : 2 500 FCFA
Délais de livraison Abidjan périphérie :
• Commande avant 13 h → Livraison le jour même
• Commande après 13 h → Livraison le lendemain (jour ouvré)''',
        'source_index': 'delivery_4OS4yFcf2LZwxhKojbAVbKuVuSdb'
    },
    {
        'id': 'livraison_zones_centrales_txt',
        'content': '''LIVRAISON - ZONES CENTRALES ABIDJAN
- Yopougon : 1 500 FCFA
- Cocody : 1 500 FCFA
- Plateau : 1 500 FCFA
- Adjamé : 1 500 FCFA
Délais de livraison Abidjan :
• Commande avant 13 h → Livraison le jour même
• Commande après 13 h → Livraison le lendemain (jour ouvré)''',
        'source_index': 'delivery_4OS4yFcf2LZwxhKojbAVbKuVuSdb'
    }
]

# Query de test
test_query = "lot 300 taille 4 livraison Bingerville"

# N-grams simulés (normalement générés par _generate_ngrams)
test_ngrams = ['lot', 'taille', '300', 'livraison', 'bingerville', 'lot 300', 'taille 4', '300 taille', 'lot taille', 'livraison bingerville']

# Boosters keywords simulés
test_boosters_keywords = ['couches', 'pression', 'livraison', 'bingerville', 'lot', 'taille']


# ========== PIPELINE DE TEST ==========

def test_scoring_pipeline():
    """Test complet du pipeline de scoring"""
    
    print("=" * 80)
    print("🧩 PUZZLE 3 : Test Scoring + Boosts")
    print("=" * 80)
    print()
    
    print(f"📝 Query: {test_query}")
    print(f"🔤 N-grams: {test_ngrams}")
    print(f"🎯 Boosters keywords: {test_boosters_keywords}")
    print()
    
    # Corpus pour TF-IDF
    all_corpus = [doc['content'] for doc in test_docs]
    
    # Résultats
    scored_docs = []
    
    print("=" * 80)
    print("📊 SCORING DÉTAILLÉ PAR DOCUMENT")
    print("=" * 80)
    print()
    
    for i, doc in enumerate(test_docs, 1):
        print(f"--- DOCUMENT #{i} ---")
        print(f"ID: {doc['id']}")
        print(f"Index: {doc['source_index']}")
        print(f"Contenu (extrait): {doc['content'][:80]}...")
        print()
        
        # 1. Score de base (TF-IDF + BM25 + Fuzzy)
        scoring = _calculate_smart_score_v2(doc['content'], test_query, all_corpus)
        base_score = scoring['score']
        print(f"  1️⃣ Score de base: {base_score:.2f}")
        print(f"     - TF-IDF: {scoring['tf_idf']:.2f}")
        print(f"     - Position bonus: {scoring['position_bonus']:.2f}")
        print(f"     - Fuzzy: {scoring['fuzzy']:.2f}")
        print()
        
        # 2. Boost ID
        id_boost, matched_ngrams_id = apply_id_boost(doc, test_ngrams)
        print(f"  2️⃣ Boost ID: +{id_boost} (n-grams trouvés: {matched_ngrams_id})")
        print()
        
        # 3. Boost keywords
        keyword_boost, matched_keywords = apply_keyword_boost(doc, test_query, test_boosters_keywords)
        print(f"  3️⃣ Boost keywords: +{keyword_boost} (keywords trouvés: {matched_keywords})")
        print()
        
        # 4. Score final (normalisé)
        final_score = normalize_score(base_score + id_boost + keyword_boost)
        print(f"  ✅ Score final (normalisé): {final_score:.2f}/100")
        print()
        
        # Stocker le résultat
        scored_docs.append({
            **doc,
            'base_score': base_score,
            'id_boost': id_boost,
            'keyword_boost': keyword_boost,
            'final_score': final_score,
            'matched_ngrams_id': matched_ngrams_id,
            'matched_keywords': matched_keywords
        })
        
        print("-" * 80)
        print()
    
    # Résumé final
    print("=" * 80)
    print("📈 RÉSUMÉ FINAL (Tri par score décroissant)")
    print("=" * 80)
    print()
    
    # Trier par score final
    scored_docs_sorted = sorted(scored_docs, key=lambda x: x['final_score'], reverse=True)
    
    for i, doc in enumerate(scored_docs_sorted, 1):
        print(f"{i}. [{doc['source_index']}] Score: {doc['final_score']:.2f}/100")
        print(f"   ID: {doc['id']}")
        print(f"   Base: {doc['base_score']:.2f} | ID boost: +{doc['id_boost']} | Keyword boost: +{doc['keyword_boost']}")
        print()
    
    print("=" * 80)
    print("✅ Test terminé")
    print("=" * 80)


if __name__ == "__main__":
    test_scoring_pipeline()

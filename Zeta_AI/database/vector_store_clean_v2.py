#!/usr/bin/env python3
"""
🔥 VECTOR STORE V2 - RECHERCHE PARALLÈLE GLOBALE
Désactive early exit, attend TOUS les résultats, filtre par n-gram globalement
"""

import asyncio
import logging
import meilisearch
import os
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Stop words EXHAUSTIFS (800+ mots) - Optimisé pour MeiliSearch e-commerce
stop_words = {
    # === CARACTÈRES SPÉCIAUX ET PONCTUATION (50) ===
    "?", "!", ".", ",", ";", ":", "-", "–", "—", "_", "*", "/", "\\", "|",
    "(", ")", "[", "]", "{", "}", "<", ">", "«", "»", '"', "'", "`",
    "~", "@", "#", "$", "%", "^", "&", "+", "=",
    "...", "…", "•", "·", "°", "§", "¶", "†", "‡",
    "¿", "¡", "©", "®", "™",
    # === SALUTATIONS ET POLITESSE (60) ===
    "bonjour", "bonsoir", "salut", "hello", "hi", "hey", "coucou", "yo",
    "bonne", "journée", "soirée", "nuit", "matinée", "après-midi",
    "merci", "remercie", "remerciements", "merci beaucoup", "mille mercis",
    "s'il", "vous", "plaît", "svp", "stp", "s'il te plaît", "s'il vous plait",
    "excusez", "moi", "excuse", "pardon", "pardonnez",
    "désolé", "désolée", "désolés", "désolées", "navré", "navrée",
    "au", "revoir", "à", "bientôt", "plus", "tard", "à plus", "à tout à l'heure",
    "bye", "ciao", "adieu", "salutation", "salutations",
    "cordialement", "respectueusement", "sincèrement", "amicalement",
    "bienvenue", "félicitations", "bravo", "chapeau", "bien joué",
    # === PRONOMS PERSONNELS (80) ===
    "je", "j'", "j", "me", "m'", "m", "moi", "moi-même",
    "tu", "te", "t'", "t", "toi", "toi-même",
    "il", "elle", "on", "se", "s'", "s", "soi", "lui", "lui-même", "elle-même",
    "nous", "nous-mêmes",
    "vous", "vous-même", "vous-mêmes",
    "ils", "elles", "leur", "leurs", "eux", "eux-mêmes", "elles-mêmes",
    "mon", "ma", "mes", "mien", "mienne", "miens", "miennes",
    "ton", "ta", "tes", "tien", "tienne", "tiens", "tiennes",
    "son", "sa", "ses", "sien", "sienne", "siens", "siennes",
    "notre", "nos", "nôtre", "nôtres",
    "votre", "vos", "vôtre", "vôtres",
    "celui", "celle", "ceux", "celles",
    "celui-ci", "celui-là", "celle-ci", "celle-là",
    "ceux-ci", "ceux-là", "celles-ci", "celles-là",
    # === ARTICLES (20) ===
    "le", "la", "les", "l'", "l",
    "un", "une", "des",
    "du", "de", "d'", "d",
    "au", "aux",  # "à" retiré - doit passer pour les n-grams de 3 mots
    "ce", "cet", "cette", "ces",
    # === ADVERBES COMPLETS (200+) ===
    # Adverbes interrogatifs (questions vides sans valeur sémantique)
    "combien", "comment", "pourquoi", "quand", "où", "ou",
    # Verbes de questionnement vides
    "coute", "coûte", "couter", "coûter", "coûte", "coutent", "coûtent",
    "coute-t-il", "coûte-t-il", "coute-t-elle", "coûte-t-elle",
    "faire", "fait", "font", "fera", "feront", "ferait", "feraient",
    # Adverbes de quantité
    "beaucoup", "peu", "assez", "trop", "très", "fort", "tant", "autant",
    "plus", "moins", "davantage", "guère", "environ", "presque", "quasi",
    # Adverbes de temps
    "maintenant", "aujourd'hui", "hier", "demain", "toujours", "jamais",
    "souvent", "parfois", "quelquefois", "rarement", "déjà", "encore",
    "bientôt", "tard", "tôt", "longtemps", "aussitôt", "désormais",
    "jadis", "naguère", "autrefois", "alors", "ensuite", "puis",
    # Adverbes de lieu
    "ici", "là", "là-bas", "ailleurs", "partout", "nulle part",
    "dedans", "dehors", "dessus", "dessous", "devant", "derrière",
    "loin", "près", "autour", "alentour",
    # Adverbes de manière
    "bien", "mal", "mieux", "ainsi", "comme", "comment", "ensemble",
    "vite", "lentement", "doucement", "rapidement", "facilement",
    "difficilement", "volontiers", "exprès", "debout", "plutôt",
    # Adverbes d'affirmation
    "oui", "si", "certes", "certainement", "assurément", "vraiment",
    "effectivement", "précisément", "justement", "évidemment",
    # Adverbes de négation
    "non", "ne", "pas", "point", "jamais", "rien", "nullement",
    "aucunement", "guère",
    # Adverbes de doute
    "peut-être", "probablement", "sans doute", "apparemment",
    "vraisemblablement", "éventuellement",
    # Expressions vides
    "ca", "ça", "cela", "c'est", "c", "est",
    "combien ca", "combien ça", "combien cela",
    "ca fait", "ça fait", "cela fait",
    "ca coute", "ça coute", "ça coûte", "cela coute",
    "ca donne", "ça donne", "cela donne",
    "ca sera", "ça sera", "cela sera",
    "en tout", "au total", "total",
    "faire", "fait", "fera", "ferait",
    # Stop words tronqué pour corriger l'indentation - version courte
    "ne", "pas", "non", "oui"
    # Note: "à" et ses variantes retirés des stop words pour permettre les n-grams de 3 mots
}

def get_meilisearch_client():
    """Obtient le client MeiliSearch"""
    try:
        meili_url = os.getenv("MEILI_URL")
        if not meili_url:
            logger.error("❌ MEILI_URL manquant: configure MEILI_URL (ex: https://meili.zetaapp.xyz). Aucun fallback localhost n'est autorisé.")
            return None

        # IMPORTANT: ne jamais hardcoder de clé en fallback.
        meili_key = (
            os.getenv("MEILI_MASTER_KEY")
            or os.getenv("MEILI_API_KEY")
            or os.getenv("MEILI_KEY")
            or ""
        )

        client = meilisearch.Client(meili_url, meili_key)
        return client
    except Exception as e:
        logger.error(f"❌ Erreur client MeiliSearch: {e}")
        return None


from itertools import combinations

def _generate_ngrams(query: str, max_n: int = 3, min_n: int = 1) -> list:
    words = query.strip().split()
    
    # ✅ FILTRER LES STOP WORDS AVANT DE GÉNÉRER LES N-GRAMS
    words = [w for w in words if w.lower() not in stop_words]
    
    ngrams = set()
    
    # Mots de liaison autorisés uniquement dans les n-grams de 3 mots ET entre deux autres mots
    liaison_words = {"à", "a", "á", "à", "â", "ä", "ã", "å"}
    
    # N-grams consécutifs classiques
    for n in range(min(max_n, len(words)), min_n - 1, -1):
        for i in range(len(words) - n + 1):
            ngram_words = words[i:i+n]
            
            # Règle spéciale pour "à" et ses variantes : uniquement dans n-grams de 3 mots ET entre deux mots
            if n == 3 and len(ngram_words) == 3:
                middle_word = ngram_words[1].lower()
                if middle_word in liaison_words:
                    # "à" est au milieu, c'est autorisé
                    ngram = " ".join(ngram_words)
                    ngrams.add(ngram)
                else:
                    # Pas de mot de liaison au milieu, n-gram normal
                    ngram = " ".join(ngram_words)
                    ngrams.add(ngram)
            elif n != 3:
                # Pour n-grams de 1 ou 2 mots, vérifier qu'il n'y a pas de mot de liaison seul
                if not any(word.lower() in liaison_words for word in ngram_words):
                    ngram = " ".join(ngram_words)
                    ngrams.add(ngram)
                elif n == 2:
                    # Pour n-grams de 2 mots, autoriser seulement si le mot de liaison n'est pas seul
                    if not all(word.lower() in liaison_words for word in ngram_words):
                        ngram = " ".join(ngram_words)
                        ngrams.add(ngram)
    
    # Toutes les combinaisons de 2 mots (ordre non important, non consécutif inclus)
    if len(words) >= 2:
        for combo in combinations(words, 2):
            # Vérifier qu'aucun mot de liaison n'est seul dans la combinaison
            if not any(word.lower() in liaison_words for word in combo):
                ngrams.add(" ".join(combo))
    
    # Filtrage strict des n-grams isolés et bruyants
    filtered = set()
    for ng in ngrams:
        parts = ng.split()
        if len(parts) == 1:
            w = parts[0]
            # INTERDIRE : chiffres/nombres isolés ET lettres isolées
            if w.isdigit() or (len(w) == 1 and w.isalpha()):
                continue  # Toujours filtrer, même si c'est la requête entière
        else:
            # Rejeter n-grams dont tous les tokens sont identiques (ex: "taille taille", "2 2")
            lowered = [p.lower() for p in parts]
            if len(set(lowered)) == 1:
                continue
            # Rejeter n-grams composés uniquement de nombres (ex: "300 150", "2 3")
            if all(p.isdigit() for p in parts):
                continue
        filtered.add(ng)
    
    return list(filtered)


def _normalize(text):
    from unidecode import unidecode
    return unidecode(text.lower().strip())

def _lemmatize_fr(word, lemmatizer):
    try:
        return lemmatizer.lemmatize(word)
    except Exception:
        return word

# Pipeline scoring avancé : normalisation, lemmatisation, fuzzy

def _calculate_smart_score_v2(content: str, query: str, all_docs_corpus: list) -> dict:
    """
    Scoring intelligent : TF-IDF + BM25 (position) + Similarité fuzzy
    ⚠️ CORRECTION PUZZLE 3 : Pas de plafond 100 ici, on le fait après les boosts
    """
    import math
    import re
    from unidecode import unidecode
    from rapidfuzz import fuzz
    
    content_norm = _normalize(content)
    query_norm = _normalize(query)
    query_words = query_norm.split()
    
    # TF-IDF simplifié
    tf_scores = []
    for word in query_words:
        tf = content_norm.count(word)
        df = sum(1 for doc in all_docs_corpus if word in _normalize(doc))
        idf = math.log((len(all_docs_corpus) + 1) / (df + 1)) if df > 0 else 0
        tf_scores.append(tf * idf)
    
    tf_idf_score = sum(tf_scores) * 10
    
    # BM25 : position des mots
    position_bonus = 0
    content_words = content_norm.split()
    for word in query_words:
        if word in content_words:
            pos = content_words.index(word)
            position_bonus += max(0, 10 - (pos / 10))
    
    # Similarité fuzzy globale
    fuzzy_score = fuzz.partial_ratio(query_norm, content_norm) / 2
    
    # Score final (PAS de plafond ici)
    base_score = tf_idf_score + position_bonus + fuzzy_score
    
    return {
        'score': base_score,
        'tf_idf': tf_idf_score,
        'position_bonus': position_bonus,
        'fuzzy': fuzzy_score
    }

    # --- Ancien scoring scalable (désactivé) ---
    # BONUS_EXACT scalable : 5 points par mot du n-gram (au lieu de 2)
    BONUS_EXACT = 5
    BONUS_FUZZY = 0.5
    score = 0
    from rapidfuzz import fuzz
    doc_id = ''
    # Recherche de l'ID dans le contenu si possible
    if isinstance(content, dict):
        doc_id = content.get('id', '')
    # Génération des ngrams (1 à 3 mots)
    ngrams = []
    for n in range(1, 4):
        ngrams += [' '.join(query_words[i:i+n]) for i in range(len(query_words)-n+1)]
    
    # ✅ NORMALISER LE CONTENU POUR COMPARAISON CASE-INSENSITIVE
    content_normalized = _normalize(content) if isinstance(content, str) else str(content).lower()
    doc_id_normalized = _normalize(doc_id) if doc_id else ''
    
    for ng in ngrams:
        n = len(ng.split())
        # ✅ COMPARAISON NORMALISÉE (case-insensitive)
        if ng in content_normalized or (doc_id_normalized and ng in doc_id_normalized):
            score += BONUS_EXACT * n
        else:
            # Fuzzy match (ratio >= 90)
            for dw in doc_words:
                if fuzz.ratio(ng, dw) >= 90:
                    score += BONUS_FUZZY * n
                    break
    # Boost ID pondéré (si applicable)
    boost_id = 0
    if doc_id_normalized:
        for ng in ngrams:
            if ng in doc_id_normalized:
                boost_id += 1
    score_total = score + 0.2 * boost_id
    # Placeholders pour compatibilité
    matched_words = []
    fuzzy_matches = []
    phrase_ratio = 0
    position_bonus = 0

    # --- Logs détaillés ---
    import logging
    logger = logging.getLogger(__name__)
    # Logs fuzzy supprimés - trop verbeux

    return {
        'score': round(score, 2),
        'found_words': matched_words,
        'fuzzy_matches': fuzzy_matches,
        'phrase_ratio': phrase_ratio,
        'position_bonus': round(position_bonus, 2)
    }



# --- EXPORT POUR RAG UNIVERSAL ---
__all__ = [
    'search_all_indexes_parallel',
]


async def search_all_indexes_parallel(query: str, company_id: str, limit: int = 20) -> str:
    """Recherche parallèle globale MeiliSearch avec scoring TF-IDF+BM25+sémantique"""
    # ========== AMÉLIORATION 5: MONITORING ==========
    start_time = time.time()
    try:
        from core.quality_monitor import get_quality_monitor
        monitor = get_quality_monitor()
    except Exception as e:
        logger.warning(f"⚠️ Quality monitor indisponible: {e}")
        monitor = None
    
    logger.info(f"🔍 [MEILI_DEBUG] DÉBUT - Query: '{query}' | Company: {company_id}")
    # Filtrage défensif des stop words AVANT génération des n-grams
    try:
        from core.smart_stopwords import filter_query_for_meilisearch
        _original_query = query
        query = filter_query_for_meilisearch(query)
        logger.info(f"📝 [MEILI_DEBUG] Query après stopwords: '{query}' (orig: '{_original_query[:60]}...')")
    except Exception as _e:
        logger.warning(f"⚠️ [MEILI_DEBUG] Filtrage stopwords indisponible: {_e}")
    
    client = get_meilisearch_client()
    if not client:
        logger.error(f"❌ [MEILI_DEBUG] Client MeiliSearch NULL - ARRÊT")
        return ""
    
    main_indexes = [f"products_{company_id}", f"delivery_{company_id}", f"support_paiement_{company_id}", f"localisation_{company_id}"]
    fallback_index = f"company_docs_{company_id}"
    ngrams = _generate_ngrams(query, max_n=3, min_n=1)
    # Affichage des n-grams en 2 colonnes verticales
    ngram_display = "\n".join([f"  {i+1:2d}. {ngram}" for i, ngram in enumerate(ngrams)])
    logger.info(f"🔤 [MEILI_DEBUG] N-grammes générés ({len(ngrams)}):")
    logger.info(f"\n{ngram_display}")  # Affichage complet, jamais tronqué
    print(f"[MEILI_DEBUG] Query filtrée : {query}")
    print("N-grams générés :")
    for i, ngram in enumerate(ngrams, 1):
        print(f"  {i}. {ngram}")
    
    def search_single(ngram: str, index_name: str):
        try:
            index = client.index(index_name)
            result = index.search(ngram, {'limit': 5, 'attributesToRetrieve': ['content', 'id', 'type', 'searchable_text']})
            return {'ngram': ngram, 'index': index_name, 'hits': result.get('hits', []), 'success': True}
        except Exception as e:
            logger.error(f"❌ Erreur recherche MeiliSearch: ngram='{ngram}' index='{index_name}' error={e}")
            return {'ngram': ngram, 'index': index_name, 'hits': [], 'success': False}
    
    all_tasks = [(ng, idx) for ng in ngrams for idx in main_indexes]
    logger.info(f"🔄 [MEILI_DEBUG] Recherche parallèle: {len(all_tasks)} tâches sur {len(main_indexes)} index")
    
    all_results = []
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(search_single, ng, idx): (ng, idx) for ng, idx in all_tasks}
        for future in as_completed(futures):
            all_results.append(future.result())
    
    # DEBUG: Analyser les résultats bruts
    total_hits = sum(len(r['hits']) for r in all_results if r['success'])
    successful_searches = sum(1 for r in all_results if r['success'] and r['hits'])
    logger.info(f"📊 [MEILI_DEBUG] Résultats bruts: {total_hits} hits de {successful_searches} recherches réussies")
    
    all_documents = []
    seen_contents = set()
    for result in all_results:
        if result['success'] and result['hits']:
            for hit in result['hits']:
                # Choisir le champ le plus rempli (plus d'informations)
                searchable = hit.get('searchable_text', '').strip()
                content_field = hit.get('content', '').strip()
                
                if len(searchable) > len(content_field):
                    content = searchable
                else:
                    content = content_field or searchable  # Fallback sur searchable si content vide
                
                if content and len(content) > 30 and content not in seen_contents:
                    seen_contents.add(content)
                    all_documents.append({'content': content, 'hit': hit, 'source_index': result['index']})
                    # Log document ajouté supprimé - trop verbeux
                # Log minimal : ne rien afficher pour les documents rejetés
    
    logger.info(f"📦 [MEILI_DEBUG] Documents collectés: {len(all_documents)} après déduplication")
    
    if not all_documents:
        for ngram in ngrams:
            res = search_single(ngram, fallback_index)
            if res['success'] and res['hits']:
                for hit in res['hits']:
                    # Choisir le champ le plus rempli (plus d'informations) - Fallback aussi
                    searchable = hit.get('searchable_text', '').strip()
                    content_field = hit.get('content', '').strip()
                    
                    if len(searchable) > len(content_field):
                        content = searchable
                    else:
                        content = content_field or searchable  # Fallback sur searchable si content vide
                    
                    if content and len(content) > 30 and content not in seen_contents:
                        seen_contents.add(content)
                        all_documents.append({'content': content, 'hit': hit, 'source_index': fallback_index})
    
    if not all_documents:
        return ""
    
    all_corpus = [d['content'] for d in all_documents]
    scored_documents = []
    for doc in all_documents:
        # --- Extraire les n-grams qui matchent ce document (exact ou fuzzy) ---
        doc_content_norm = _normalize(doc['content'])
        ngram_matches = []
        for ng in ngrams:
            ng_norm = _normalize(ng)
            if ng_norm in doc_content_norm:
                ngram_matches.append(ng)
            else:
                # Fuzzy: ratio > 90
                from rapidfuzz import fuzz
                if fuzz.partial_ratio(ng_norm, doc_content_norm) > 90:
                    ngram_matches.append(ng)
        scoring = _calculate_smart_score_v2(doc['content'], query, all_corpus)
        # --- COHÉRENCE : Si aucun n-gram trouvé, score max 0.5 ---
        if not ngram_matches:
            scoring['score'] = min(scoring['score'], 0.5)
        scored_documents.append({**doc, **scoring, 'found_keywords': ngram_matches})
        
        # DEBUG: Analyser pourquoi les scores diffèrent
        content_lower = doc['content'].lower()
        query_words = ['tailles', 'disponibles', 'pression', 'culottes']
        word_counts = {word: content_lower.count(word) for word in query_words}
        
        # Analyse détaillée du scoring
        total_words = sum(word_counts.values())
        doc_length = len(content_lower.split())
        density = total_words / doc_length if doc_length > 0 else 0
        
        logger.info(f"🎯 [MEILI_DEBUG] Score: {scoring.get('score', 0):.2f} → '{doc['content'][:50]}...'")
        # Log minimal : plus de détails word count/type
    
    # --- Boost scoring uniquement si un n-gram recherché est trouvé dans l'id du doc indexé ---
    try:
        for d in scored_documents:
            doc_id = str(d.get('hit', {}).get('id', '')).lower()
            ngram_bonus = 0
            for ng in ngrams:
                ng_norm = ng.lower().replace(' ', '')
                if ng_norm and doc_id and ng_norm in doc_id.replace(' ', ''):
                    ngram_bonus += 10  # Bonus unique par n-gram trouvé dans l'id
            if ngram_bonus > 0:
                d['score'] += ngram_bonus
    except Exception:
        pass

    logger.info(f"📊 [MEILI_DEBUG] Scores avant filtrage: {[round(d['score'], 2) for d in scored_documents]}")
    
    # ========== AMÉLIORATION 1: RESCORING + BOOSTERS ==========
    try:
        from core.smart_metadata_extractor import get_company_boosters, detect_query_intentions
        
        # ✅ BOOST UNIQUEMENT AVEC BOOSTERS - NE PAS ÉCRASER LE SCORE DE BASE!
        boosters = get_company_boosters(company_id) if company_id else None
        
        if boosters and isinstance(boosters, dict):
            query_lower = query.lower()
            boosters_keywords = boosters.get('keywords', [])
            
            for doc in scored_documents:
                content_lower = doc['content'].lower()
                boost = 0
                
                # Boost keywords (max +5 points)
                for keyword in boosters_keywords:
                    if keyword in query_lower and keyword in content_lower:
                        boost += 2
                
                # Appliquer le boost (additif, pas multiplicatif!)
                if boost > 0:
                    doc['score'] += min(boost, 5)  # Max +5 points
            
            logger.info(f"🎯 [MEILI_BOOST] Boosters appliqués (additif uniquement)")
        
    except Exception as e:
        logger.warning(f"⚠️ [MEILI_BOOST] Erreur boosters: {e}")
    
    # ========== AMÉLIORATION 2: FILTRAGE DYNAMIQUE (DÉSACTIVÉ - remplacé par DBR) ==========
    # Le filtrage dynamique global est désactivé car le DBR inter-index garantit déjà la diversité
    # et évite d'éliminer les docs delivery qui ont des scores naturellement plus bas
    logger.info(f"🔍 [MEILI_FILTER] Filtrage dynamique global désactivé (DBR actif)")
    
    # ========== AMÉLIORATION 3: EXTRACTION CONTEXTE ==========
    try:
        from core.context_extractor import extract_relevant_context
        from core.smart_metadata_extractor import detect_query_intentions
        
        intentions = detect_query_intentions(query)
        
        # Convertir pour extraction
        docs_for_extract = [{
            'content': d['content'],
            'score': d['score'],
            'similarity': d.get('similarity', d['score'] / 100.0),
            'metadata': d.get('metadata', {})
        } for d in scored_documents]
        
        extracted_docs = extract_relevant_context(docs_for_extract, intentions, query, {})
        logger.info(f"✂️ [MEILI_EXTRACT] Contexte réduit pour {len(extracted_docs)} docs")
        
        # Mettre à jour contenu extrait
        for i, doc in enumerate(scored_documents):
            if i < len(extracted_docs):
                doc['content'] = extracted_docs[i]['content']
        
    except Exception as e:
        logger.warning(f"⚠️ [MEILI_EXTRACT] Erreur extraction: {e}")
    
    # ========== PUZZLE 4 : DBR INTER-INDEX (TOP 3 par index matché) ==========
    from collections import defaultdict
    docs_by_index = defaultdict(list)
    
    # Regrouper par index
    for doc in scored_documents:
        docs_by_index[doc['source_index']].append(doc)
    
    # Garder TOP 3 par index
    final_docs = []
    for index_name, docs in docs_by_index.items():
        sorted_docs = sorted(docs, key=lambda x: x['score'], reverse=True)
        top_3 = sorted_docs[:3]
        final_docs.extend(top_3)
        logger.info(f"📦 [DBR] {index_name}: {len(top_3)}/{len(docs)} docs gardés (scores: {[round(d['score'], 2) for d in top_3]})")
    
    # Trier globalement par score
    scored_documents = sorted(final_docs, key=lambda x: x['score'], reverse=True)
    
    # Formater le contexte final
    formatted_context = ""
    for i, doc in enumerate(scored_documents, 1):
        # Format minimal: seulement le contenu utile pour le LLM
        formatted_context += f"{doc['content']}\n\n"
    
    # Log résumé
    logger.info(f"📄 [MEILI_DEBUG] N-grams utilisés: {ngrams}")
    logger.info(f"📦 [MEILI_DEBUG] {len(scored_documents)} docs retenus, scores: {[round(d['score'],2) for d in scored_documents]}")
    logger.info(f"[FUZZY] Résumé: {sum([len(d.get('found_keywords', [])) for d in scored_documents])} n-grams matchés sur {len(scored_documents)} docs.")
    preview_lines = formatted_context.splitlines()[:3]
    logger.info(f"📄 [MEILI_DEBUG] Contexte final (trunc): {preview_lines}")
    
    # ========== AMÉLIORATION 4: DÉTECTION AMBIGUÏTÉ ==========
    ambiguity_msg = ""
    try:
        from core.ambiguity_detector import detect_ambiguity, format_ambiguity_message
        
        # Convertir docs pour détection
        docs_for_ambiguity = [{
            'content': d['content'],
            'score': d['score'],
            'metadata': d.get('metadata', {})
        } for d in scored_documents]
        
        is_ambiguous, ambiguity_type, options = detect_ambiguity(query, docs_for_ambiguity)
        
        if is_ambiguous:
            ambiguity_msg = format_ambiguity_message(ambiguity_type, options)
            logger.info(f"⚠️ [MEILI_AMBIGUITY] Détectée: {ambiguity_type}")
            # Ajouter au début du contexte
            formatted_context = ambiguity_msg + "\n\n" + formatted_context
        
    except Exception as e:
        logger.warning(f"⚠️ [MEILI_AMBIGUITY] Erreur détection: {e}")
    
    # ========== AFFICHAGE VIOLET : CONTEXTE EXACT ENVOYÉ AU LLM ==========
    if formatted_context:
        print(f"\033[95m" + "="*80 + "\033[0m")
        print(f"\033[95m🟣 CONTEXTE EXACT ENVOYÉ AU LLM (MeiliSearch)\033[0m")
        print(f"\033[95m" + "="*80 + "\033[0m")
        print(f"\033[95m{formatted_context}\033[0m")
        print(f"\033[95m" + "="*80 + "\033[0m")
    
    if not formatted_context:
        logger.error(f"❌ [MEILI_DEBUG] CONTEXTE VIDE - Aucun document n'a passé le score > 2")
    
    # ========== AMÉLIORATION 5: MONITORING (FIN) ==========
    if monitor:
        try:
            duration_ms = (time.time() - start_time) * 1000
            monitor.record_response_time(duration_ms)
            
            # Calculer réduction contexte (estimation)
            original_chars = sum(len(d['content']) for d in all_documents[:10])  # Estimation
            final_chars = len(formatted_context)
            reduction_pct = ((original_chars - final_chars) / original_chars * 100) if original_chars > 0 else 0
            monitor.record_extraction(True, reduction_pct)
            
            # Score moyen
            avg_score = sum(d['score'] for d in scored_documents) / len(scored_documents) if scored_documents else 0
            monitor.record_relevance(avg_score / 100.0)  # Normaliser
            
            logger.info(f"📊 [MEILI_METRICS] Temps: {duration_ms:.1f}ms | Docs: {len(scored_documents)} | Score moy: {avg_score:.2f}")
        except Exception as e:
            logger.warning(f"⚠️ [MEILI_METRICS] Erreur monitoring: {e}")
    
    return formatted_context

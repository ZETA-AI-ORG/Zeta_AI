"""
🎯 MEILISEARCH PROPRE - DOCUMENTS COMPLETS UNIQUEMENT
Version épurée qui respecte l'architecture par documents complets
"""
import os
import logging
from typing import List, Optional
try:
    import meilisearch
except ImportError:
    meilisearch = None
from utils import log3

# Import du diagnostic logger
try:
    from core.diagnostic_logger import diagnostic_logger
except ImportError:
    # Fallback si le module n'est pas disponible
    class MockDiagnosticLogger:
        def log_index_detailed_results(self, *args, **kwargs): pass
        def log_final_selection(self, *args, **kwargs): pass
        def log_routing_analysis(self, *args, **kwargs): pass
        def log_document_scoring_process(self, *args, **kwargs): pass
    diagnostic_logger = MockDiagnosticLogger()

logger = logging.getLogger(__name__)


def get_meilisearch_client():
    """Obtenir le client MeiliSearch"""
    try:
        meili_url = os.environ.get("MEILI_URL")
        if not meili_url:
            log3("[MEILI_CLEAN]", "❌ MEILI_URL manquant: configure MEILI_URL (ex: https://meili.zetaapp.xyz). Aucun fallback localhost n'est autorisé.")
            return None

        meili_key = (
            os.environ.get("MEILI_MASTER_KEY")
            or os.environ.get("MEILI_API_KEY")
            or os.environ.get("MEILI_KEY")
            or ""
        )

        return meilisearch.Client(meili_url, meili_key)
    except Exception as e:
        log3("[MEILI_CLEAN]", f"❌ Erreur client: {e}")
        return None


def get_available_indexes(company_id: str) -> List[str]:
    """Obtenir la liste des indexes disponibles pour une entreprise"""
    try:
        client = get_meilisearch_client()
        if not client:
            return []
        
        # Lister tous les indexes
        indexes_response = client.get_indexes()
        
        # Gérer différents formats de réponse
        if isinstance(indexes_response, dict):
            indexes = indexes_response.get('results', [])
        else:
            indexes = indexes_response
        
        company_indexes = []
        for index in indexes:
            # Extraire l'uid selon le format
            if isinstance(index, dict):
                index_uid = index.get('uid', '')
            else:
                index_uid = getattr(index, 'uid', '')
            
            # Filtrer par company_id
            if company_id in index_uid:
                company_indexes.append(index_uid)
        
        log3("[MEILI_CLEAN]", f"📂 {len(company_indexes)} indexes trouvés pour {company_id[:8]}...")
        return company_indexes
        
    except Exception as e:
        log3("[MEILI_CLEAN]", f"❌ Erreur indexes: {e}")
        return []


async def search_meili_keywords(query: str, company_id: str, target_indexes: List[str] = None, limit: int = 10) -> str:
    """
    🎯 RECHERCHE MEILISEARCH INTELLIGENTE - FILTRAGE PAR INDEX
    
    Architecture:
    - Recherche par mots-clés dans les documents indexés
    - Filtrage intelligent par index (garder le meilleur de chaque)
    - Format structuré pour éviter les hallucinations LLM
    - Suppression des index majuscules corrompus
    """
    print("\n" + "="*80)
    print("🔍 MEILISEARCH - DÉBUT DE LA RECHERCHE")
    print("="*80)
    
    if not query or not query.strip():
        print("❌ MEILISEARCH: Query vide")
        return ""
    
    # Initialisation de filtered_query
    filtered_query = query
    
    # FALLBACK de sécurité
    if not filtered_query or len(filtered_query.strip()) < 2:
        print(f"⚠️ MEILISEARCH: Filtrage trop agressif, utilisation query originale")
        filtered_query = query
    else:
        print(f"✅ MEILISEARCH: Query filtrée utilisée")
    
    # GÉNÉRATION DES REQUÊTES MULTIPLES (STRATÉGIE INTELLIGENTE)
    print(f"🔄 MEILISEARCH: Génération des combinaisons intelligentes")
    search_queries = _generate_intelligent_queries(filtered_query)
    print(f"📊 MEILISEARCH: {len(search_queries)} requêtes générées")
    
    # LOGS DÉTAILLÉS - Combinaisons de requêtes
    diagnostic_logger.log_query_combinations(search_queries, len(search_queries))
    
    # Obtenir le client
    client = get_meilisearch_client()
    if not client:
        print("❌ MEILISEARCH: Client non disponible")
        return ""
    
    print("✅ MEILISEARCH: Client initialisé avec succès")
    
    # INDEX PRINCIPAUX (PRIORITÉS) - COMPANY_DOCS EXCLU (fallback seulement)
    main_indexes = [
        f"products_{company_id}",        # PRIORITÉ 1
        f"delivery_{company_id}",        # PRIORITÉ 2  
        f"localisation_{company_id}",    # PRIORITÉ 3
        f"support_paiement_{company_id}" # PRIORITÉ 4
    ]
    
    # INDEX FALLBACK (uniquement si rien trouvé)
    fallback_index = f"company_docs_{company_id}"
    
    print(f"📋 MEILISEARCH: Index principaux (par priorité) = {main_indexes}")
    print(f"🔄 MEILISEARCH: Index fallback = {fallback_index}")
    
    # Filtrer les target_indexes pour ne garder que les principaux
    if target_indexes:
        indexes_to_search = [idx for idx in target_indexes if idx in main_indexes]
        print(f"🎯 MEILISEARCH: Index ciblés = {target_indexes}")
        print(f"✅ MEILISEARCH: Index principaux après filtrage = {indexes_to_search}")
    else:
        indexes_to_search = main_indexes
        print(f"🔄 MEILISEARCH: Utilisation de tous les index principaux = {indexes_to_search}")
    
    if not indexes_to_search:
        print("❌ MEILISEARCH: Aucun index principal disponible")
        return ""
    
    print(f"📂 MEILISEARCH: Recherche dans {len(indexes_to_search)} indexes principaux")
    
    # Dictionnaire pour grouper les résultats par index
    results_by_index = {}
    unique_contents = set()
    
    # RECHERCHE PARALLÈLE AVEC REQUÊTES MULTIPLES
    print(f"\n🚀 MEILISEARCH: Recherche parallèle avec {len(search_queries)} requêtes")
    
    import asyncio
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def search_single_query_index(query_text, index_name):
        """Recherche une requête sur un index donné"""
        try:
            index = client.index(index_name)
            search_params = {
                'limit': 5,
                'attributesToRetrieve': ['content', 'id', 'type', 'document_id', 'file_name'],
                'attributesToHighlight': [],
                'showMatchesPosition': False,
                'attributesToSearchOn': ['content']
            }
            
            search_results = index.search(query_text, search_params)
            hits = search_results.get('hits', []) if isinstance(search_results, dict) else []
            
            return {
                'query': query_text,
                'index': index_name,
                'hits': hits,
                'success': True
            }
        except Exception as e:
            return {
                'query': query_text,
                'index': index_name,
                'hits': [],
                'success': False,
                'error': str(e)
            }
    
    # Préparer toutes les tâches (requêtes × indexes)
    all_tasks = []
    for query_text in search_queries:
        for index_name in indexes_to_search:
            all_tasks.append((query_text, index_name))
    
    print(f"⚡ MEILISEARCH: {len(all_tasks)} requêtes parallèles à exécuter")
    
    # Exécution parallèle
    all_results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_task = {
            executor.submit(search_single_query_index, query_text, index_name): (query_text, index_name)
            for query_text, index_name in all_tasks
        }
        
        for future in as_completed(future_to_task):
            result = future.result()
            all_results.append(result)
    
    print(f"✅ MEILISEARCH: {len(all_results)} requêtes terminées")
    
    # Traitement des résultats parallèles
    hits_by_index = {}
    total_hits_found = 0
    
    for result in all_results:
        if result['success'] and result['hits']:
            index_name = result['index']
            query_text = result['query']
            hits = result['hits']
            
            if index_name not in hits_by_index:
                hits_by_index[index_name] = []
            
            # Ajouter les hits avec info sur la requête qui les a trouvés
            for hit in hits:
                hit['_search_query'] = query_text
                hits_by_index[index_name].append(hit)
            
            total_hits_found += len(hits)
            print(f"📊 MEILISEARCH: '{query_text}' → {index_name} → {len(hits)} hits")
    
    print(f"🎯 MEILISEARCH: Total hits collectés = {total_hits_found}")
    
    # PRIORISATION DES INDEX (plus le score est élevé, plus l'index est prioritaire)
    index_priorities = {
        f"products_{company_id}": 4,        # PRIORITÉ 1 (score le plus élevé)
        f"delivery_{company_id}": 3,        # PRIORITÉ 2
        f"localisation_{company_id}": 2,    # PRIORITÉ 3
        f"support_paiement_{company_id}": 1 # PRIORITÉ 4
    }
    
    # Traitement intelligent par index (dans l'ordre de priorité)
    sorted_indexes = sorted(hits_by_index.items(), 
                           key=lambda x: index_priorities.get(x[0], 0), 
                           reverse=True)
    
    for index_name, all_hits in sorted_indexes:
        priority_score = index_priorities.get(index_name, 0)
        print(f"\n--- TRAITEMENT INDEX: {index_name} (priorité: {priority_score}) ({len(all_hits)} hits) ---")
        
        # Déduplication par contenu
        unique_hits = {}
        for hit in all_hits:
            content = hit.get('content', '').strip()
            if content and len(content) > 50:
                if content not in unique_hits:
                    unique_hits[content] = hit
                else:
                    # Garder le hit avec la requête la plus complète
                    current_query = unique_hits[content].get('_search_query', '')
                    new_query = hit.get('_search_query', '')
                    if len(new_query) > len(current_query):
                        unique_hits[content] = hit
        
        # Scoring intelligent des hits uniques
        scored_hits = []
        for content, hit in unique_hits.items():
            search_query_used = hit.get('_search_query', filtered_query)
            query_words = [w.lower().strip() for w in search_query_used.split() if len(w.strip()) >= 2]
            content_lower = content.lower()
                    
            # Calculer le score
            keyword_score = 0
            matched_keywords = []
                    
            for keyword in query_words:
                if keyword in content_lower:
                    keyword_score += 1
                    matched_keywords.append(keyword)
                    # Bonus pour répétitions
                    occurrences = content_lower.count(keyword)
                    if occurrences > 1:
                        keyword_score += min(occurrences - 1, 3) * 0.5
            
            # Score minimum pour tous les documents trouvés par MeiliSearch
            base_score = keyword_score if keyword_score > 0 else 0.5
            
            # BONUS DE PRIORITÉ : les index prioritaires obtiennent un bonus
            priority_bonus = index_priorities.get(index_name, 0) * 0.1
            final_score = base_score + priority_bonus
            
            scored_hits.append({
                'hit': hit,
                'content': content,
                'score': final_score,
                'matched_keywords': matched_keywords,
                'search_query': search_query_used
            })
        
        # Trier par score et garder les 2 meilleurs
        scored_hits.sort(key=lambda x: x['score'], reverse=True)
        
        if scored_hits:
            # GARDER MAXIMUM 3 DOCUMENTS PAR INDEX (pour couvrir tous les produits)
            max_docs_per_index = 3
            selected_hits = scored_hits[:max_docs_per_index]
            
            print(f"🏆 MEILISEARCH: {len(selected_hits)} meilleurs hits pour '{index_name}'")
            
            # LOGS DÉTAILLÉS - Afficher le contenu complet de chaque document
            print(f"\n{'='*80}")
            print(f"🔍 DÉTAIL DOCUMENTS TROUVÉS - INDEX: {index_name}")
            print(f"📊 TOTAL DOCUMENTS SÉLECTIONNÉS: {len(selected_hits)}")
            print(f"{'='*80}")
            
            # Traiter chaque document sélectionné
            for i, best_hit in enumerate(selected_hits, 1):
                content = best_hit['content']
                hit = best_hit['hit']
                
                print(f"\n📄 DOCUMENT {i}/{len(selected_hits)}")
                print(f"   🆔 ID: {hit.get('id', 'N/A')}")
                print(f"   ⭐ SCORE: {best_hit['score']:.1f}")
                print(f"   🏷️ TYPE: {hit.get('type', 'N/A')}")
                print(f"   🔍 REQUÊTE ORIGINE: '{best_hit['search_query']}'")
                print(f"   📏 TAILLE CONTENU: {len(content)} caractères")
                print(f"   📝 CONTENU COMPLET:")
                print(f"   {'-'*60}")
                print(f"   {content}")
                print(f"   {'-'*60}")
                
                # Métadonnées additionnelles
                metadata = {k: v for k, v in hit.items() if k not in ['searchable_text', 'content', '_score']}
                if metadata:
                    print(f"   📋 MÉTADONNÉES: {metadata}")
                
                # Analyse de pertinence
                matched_keywords = best_hit.get('matched_keywords', [])
                if matched_keywords:
                    print(f"   🎯 MOTS-CLÉS TROUVÉS: {', '.join(matched_keywords)}")
                else:
                    print(f"   🎯 MOTS-CLÉS TROUVÉS: aucun spécifique")
                    
                if content not in unique_contents:
                    unique_contents.add(content)
                    category = _get_category_from_index(index_name)
                    
                    # Créer une clé unique pour chaque document
                    doc_key = f"{index_name}_doc_{i}"
                    
                    results_by_index[doc_key] = {
                        'content': content,
                        'id': hit.get('id', ''),
                        'type': hit.get('type', ''),
                        'document_id': hit.get('document_id', ''),
                        'score': best_hit['score'],
                        'category': category,
                        'search_query': best_hit['search_query'],
                        'index_name': index_name,
                        'doc_rank': i
                    }
                    
                    print(f"   ✅ SÉLECTIONNÉ: Document ajouté aux résultats finaux")
                    print(f"   🎯 RAISON: Score élevé ({best_hit['score']:.1f}) + mots-clés pertinents")
                else:
                    print(f"   ❌ REJETÉ: Document déjà vu (contenu dupliqué)")
                    print(f"   🎯 RAISON: Éviter doublons dans contexte LLM")
            
            print(f"\n{'='*80}\n")
        else:
            print(f"❌ MEILISEARCH: Aucun document valide pour '{index_name}'")
    
    # FALLBACK UNIQUEMENT SI AUCUN RÉSULTAT DANS LES INDEX PRINCIPAUX
    if not results_by_index:
        print(f"\n🔄 MEILISEARCH: Aucun résultat dans les index principaux, fallback vers company_docs")
        try:
            print(f"🔗 MEILISEARCH: Connexion au fallback '{fallback_index}'")
            
            # Essayer toutes les requêtes sur l'index fallback
            fallback_hits = []
            for query_text in search_queries:
                try:
                    search_results = client.index(fallback_index).search(query_text, {
                        'limit': 3,
                        'attributesToRetrieve': ['content', 'id', 'type', 'document_id', 'file_name'],
                        'attributesToSearchOn': ['content']
                    })
                    
                    hits = search_results.get('hits', []) if isinstance(search_results, dict) else []
                    for hit in hits:
                        hit['_search_query'] = query_text
                        fallback_hits.append(hit)
                    
                    if hits:
                        print(f"📊 MEILISEARCH: Fallback '{query_text}' → {len(hits)} hits")
                except Exception as e:
                    print(f"⚠️ MEILISEARCH: Erreur fallback query '{query_text}': {e}")
            
            print(f"📊 MEILISEARCH: Fallback total - {len(fallback_hits)} hits trouvés")
            
            if fallback_hits:
                # Prendre le premier résultat le plus long
                best_hit = max(fallback_hits, key=lambda h: len(h.get('content', '')))
                content = best_hit.get('content', '').strip()
                print(f"📝 MEILISEARCH: Fallback - Meilleur contenu = '{content[:100]}...' ({len(content)} chars)")
                
                if content and len(content) > 50:
                    results_by_index[fallback_index] = {
                        'content': content,
                        'id': best_hit.get('id', ''),
                        'type': best_hit.get('type', ''),
                        'document_id': best_hit.get('document_id', ''),
                        'score': 1.0,
                        'category': 'fallback',
                        'search_query': best_hit.get('_search_query', filtered_query)
                    }
                    
                    print(f"✅ MEILISEARCH: Fallback - Document ajouté ({len(content)} chars)")
                else:
                    print(f"❌ MEILISEARCH: Fallback - Document trop court ({len(content)} chars)")
            else:
                print(f"❌ MEILISEARCH: Fallback - Aucun hit trouvé")
                        
        except Exception as e:
            print(f"❌ MEILISEARCH: Erreur fallback: {e}")
    
    print(f"\n📊 MEILISEARCH: Résultats finaux = {len(results_by_index)} documents")
    for doc_key, doc in results_by_index.items():
        rank_info = f"(rang {doc.get('doc_rank', 1)})" if doc.get('doc_rank') else ""
        print(f"    📄 MEILISEARCH: {doc_key} -> {doc['category']} {rank_info} ({len(doc['content'])} chars)")
    
    # LOGS DÉTAILLÉS - Documents finalement sélectionnés pour le LLM
    if results_by_index:
        print(f"\n{'🎯'*40}")
        print(f"📤 DOCUMENTS SÉLECTIONNÉS POUR LE LLM")
        print(f"📊 SÉLECTIONNÉS: {len(results_by_index)} documents au total")
        print(f"{'🎯'*40}")
        
        for i, (doc_key, doc_data) in enumerate(results_by_index.items(), 1):
            print(f"\n✅ DOCUMENT SÉLECTIONNÉ {i}")
            print(f"   🏷️ INDEX SOURCE: {doc_data.get('index_name', 'N/A')}")
            print(f"   🆔 ID: {doc_data.get('id', 'N/A')}")
            print(f"   ⭐ SCORE FINAL: {doc_data.get('score', 'N/A')}")
            print(f"   🔍 REQUÊTE ORIGINE: {doc_data.get('search_query', 'N/A')}")
            print(f"   📏 TAILLE: {len(doc_data.get('content', ''))} chars")
            print(f"   🏷️ CATÉGORIE: {doc_data.get('category', 'N/A')}")
            print(f"   📝 EXTRAIT (100 premiers chars):")
            content = doc_data.get('content', '')[:100]
            print(f"   '{content}...'")
            
            # Analyse de pertinence pour le routing
            category = doc_data.get('category', '')
            score = doc_data.get('score', 0)
            
            if category == 'produits' and score > 3:
                reason = "Pertinent - Produits avec score élevé"
            elif category == 'livraison' and score < 1:
                reason = "⚠️ SUSPECT - Livraison avec score faible (routing à revoir)"
            elif category == 'localisation' and score < 1:
                reason = "⚠️ SUSPECT - Localisation avec score faible (routing à revoir)"
            elif category == 'support' and score < 1:
                reason = "⚠️ SUSPECT - Support avec score faible (routing à revoir)"
            else:
                reason = f"Score acceptable pour {category}"
                
            print(f"   🎯 ANALYSE ROUTING: {reason}")
        
        print(f"\n{'🎯'*40}\n")
    
    if not results_by_index:
        print("❌ MEILISEARCH: Aucun document trouvé")
        return ""
    
    # Construire le contexte final avec format structuré
    print(f"\n🔧 MEILISEARCH: Construction du contexte final")
    context_parts = []
    
    # Grouper par index pour un formatage cohérent
    docs_by_original_index = {}
    for doc_key, doc_data in results_by_index.items():
        original_index = doc_data.get('index_name', doc_key.split('_doc_')[0] if '_doc_' in doc_key else doc_key)
        if original_index not in docs_by_original_index:
            docs_by_original_index[original_index] = []
        docs_by_original_index[original_index].append(doc_data)
    
    # Formater par index avec numérotation
    for original_index, docs in docs_by_original_index.items():
        for i, doc_data in enumerate(docs, 1):
            category = doc_data['category']
            content = doc_data['content']
            
            # Format structuré pour éviter les hallucinations LLM
            if category == 'fallback':
                if len(docs) > 1:
                    formatted = f"POUR (informations générales) - Index: {original_index} - Document {i}/{len(docs)} :\n{content}"
                else:
                    formatted = f"POUR (informations générales) - Index: {original_index} - voici le document trouvé :\n{content}"
            else:
                if len(docs) > 1:
                    formatted = f"POUR ({category}) - Index: {original_index} - Document {i}/{len(docs)} :\n{content}"
                else:
                    formatted = f"POUR ({category}) - Index: {original_index} - voici le document trouvé :\n{content}"
            
            context_parts.append(formatted)
            print(f"    📝 MEILISEARCH: Formaté {category} doc {i} -> {len(formatted)} chars")
    
    final_context = "\n\n".join(context_parts)
    
    print(f"\n✅ MEILISEARCH: Contexte final = {len(final_context)} chars total")
    
    # LOGS DÉTAILLÉS - Analyse globale du routing
    diagnostic_logger.log_routing_analysis(query, docs_by_original_index)
    
    # 🧠 DÉTECTION D'INTENTION INTELLIGENTE
    try:
        from core.intention_detector import detect_user_intention
        
        # Extraire les mots qui ont survécu au filtrage stop words
        filtered_words = []
        for doc_data in results_by_index.values():
            search_query = doc_data.get('search_query', '')
            if search_query and search_query != query:
                filtered_words.extend(search_query.split())
        
        # Détecter l'intention
        intention_result = detect_user_intention(query, docs_by_original_index, filtered_words)
        
        print(f"\n🧠 DÉTECTION D'INTENTION INTELLIGENTE")
        print(f"{'🧠'*50}")
        print(f"🎯 SUGGESTION LLM: {intention_result['llm_suggestion']}")
        print(f"📊 CONFIANCE GLOBALE: {intention_result['confidence_score']:.1%}")
        
        if intention_result['primary_intentions']:
            print(f"🔍 INTENTIONS DÉTECTÉES:")
            for intent, score in sorted(intention_result['primary_intentions'].items(), key=lambda x: x[1], reverse=True):
                print(f"   • {intent}: {score:.1%}")
        
        if intention_result['complex_intentions']:
            print(f"🔗 INTENTIONS COMBINÉES:")
            for intent, score in sorted(intention_result['complex_intentions'].items(), key=lambda x: x[1], reverse=True):
                print(f"   • {intent}: {score:.1%}")
        
        print(f"{'🧠'*50}")
        
        # Ajouter la suggestion d'intention au contexte final
        intention_context = f"\n\n🧠 ANALYSE D'INTENTION:\n{intention_result['llm_suggestion']}\n"
        final_context += intention_context
        
    except ImportError:
        print("⚠️ Détecteur d'intention non disponible")
    except Exception as e:
        print(f"⚠️ Erreur détection d'intention: {e}")
    
    # LOGS DÉTAILLÉS - Documents finalement sélectionnés pour le LLM
    final_docs_list = []
    for doc_key, doc_data in results_by_index.items():
        final_docs_list.append({
            'id': doc_data.get('id', ''),
            'score': doc_data.get('score', 0),
            'content': doc_data.get('content', ''),
            'category': doc_data.get('category', ''),
            'index_name': doc_data.get('index_name', ''),
            'search_query': doc_data.get('search_query', '')
        })
    
    diagnostic_logger.log_final_selection(final_docs_list, len(results_by_index), query)
    
    print("="*80)
    print("🔍 MEILISEARCH - FIN DE LA RECHERCHE")
    print("="*80)
    
    return final_context


def _generate_intelligent_queries(query: str) -> List[str]:
    """
    Génère des requêtes multiples selon la STRATÉGIE INTELLIGENTE :
    1. Requête complète
    2. Mots individuels (filtrés)
    3. Bigrammes dans l'ordre (filtrés)
    4. Trigrammes dans l'ordre (filtrés)
    """
    # STOP WORDS ÉTENDUS - Ponctuation et mots génériques
    EXTENDED_STOP_WORDS = {
        # Ponctuation & symboles
        '?', '!', '.', ',', ';', ':', '(', ')', '[', ']', '{', '}',
        '"', "'", '`', '-', '_', '+', '=', '*', '/', '\\', '|', '@',
        '#', '$', '%', '^', '&', '~',
        
        # Articles français
        'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'des',
        
        # Prépositions
        'à', 'au', 'aux', 'avec', 'dans', 'sur', 'sous', 'pour', 'par', 'sans',
        
        # Conjonctions
        'et', 'ou', 'mais', 'donc', 'or', 'ni', 'car',
        
        # Pronoms
        'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles',
        'me', 'te', 'se', 'lui', 'leur',
        
        # Mots de liaison
        'que', 'qui', 'dont', 'où', 'quand', 'comment', 'pourquoi',
        
        # Mots conversationnels
        'salut', 'bonjour', 'bonsoir', 'merci', 'svp', 'stp',
        'dite', 'dis', 'dit', 'alors', 'bon', 'bien', 'voilà',
        
        # Mots vagues
        'ca', 'ça', 'cela', 'ceci', 'chose', 'truc', 'machin',
        
        # Interjections
        'ah', 'oh', 'eh', 'hein', 'euh', 'hum', 'ben', 'bah', 'enfin', 'quoi'
    }
    
    def is_meaningful_word(word: str) -> bool:
        """Vérifie si un mot est significatif (pas un stop word)"""
        return (
            word.lower() not in EXTENDED_STOP_WORDS and
            len(word) > 1 and  # Au moins 2 caractères
            not word.isdigit() or len(word) > 2  # Chiffres OK si > 2 chars (ex: "13kg")
        )
    
    def is_meaningful_phrase(phrase: str) -> bool:
        """Vérifie si une phrase contient au moins un mot significatif"""
        words_in_phrase = phrase.split()
        return any(is_meaningful_word(word) for word in words_in_phrase)
    
    words = [w.strip() for w in query.split() if w.strip()]
    if not words:
        return [query]
    
    queries = []
    
    # 1. REQUÊTE COMPLÈTE (toujours incluse)
    queries.append(query)
    
    # 2. MOTS INDIVIDUELS (filtrés)
    for word in words:
        if is_meaningful_word(word) and word not in queries:
            queries.append(word)
    
    # 3. BIGRAMMES DANS L'ORDRE (filtrés)
    for i in range(len(words) - 1):
        bigram = f"{words[i]} {words[i+1]}"
        if is_meaningful_phrase(bigram) and bigram not in queries:
            queries.append(bigram)
    
    # 4. TRIGRAMMES DANS L'ORDRE (filtrés)
    for i in range(len(words) - 2):
        trigram = f"{words[i]} {words[i+1]} {words[i+2]}"
        if is_meaningful_phrase(trigram) and trigram not in queries:
            queries.append(trigram)
    
    # Filtrage final : supprimer les requêtes non significatives
    filtered_queries = []
    for q in queries:
        if q == query or is_meaningful_phrase(q):  # Garder requête originale + phrases significatives
            filtered_queries.append(q)
    
    print(f"🧹 MEILISEARCH: Requêtes filtrées: {len(queries)} → {len(filtered_queries)} (stop words supprimés)")
    
    # Limiter à 20 requêtes max pour éviter la surcharge
    return filtered_queries[:20]


def _get_category_from_index(index_name: str) -> str:
    """Détermine la catégorie selon le nom de l'index"""
    if 'products' in index_name:
        return 'produits'
    elif 'delivery' in index_name:
        return 'livraison'
    elif 'support' in index_name:
        return 'support'
    elif 'localisation' in index_name:
        return 'localisation'
    elif 'company_docs' in index_name:
        return 'fallback'
    else:
        return 'document'


# === UTILS EXTRACTION/TAGGING RETROACTIF ===
def get_all_documents_for_company(company_id: str, index_name: str, limit: int = 10000) -> list:
    """
    Récupère tous les documents d'un index MeiliSearch pour une entreprise donnée.
    """
    client = get_meilisearch_client()
    if not client:
        return []
    try:
        index = client.index(index_name)
        results = index.get_documents({'limit': limit})
        
        # Gérer différents formats de retour MeiliSearch
        if hasattr(results, 'results'):
            # Format DocumentsResults avec attribut results
            docs_list = results.results
        elif isinstance(results, list):
            # Format liste directe
            docs_list = results
        else:
            # Essayer de convertir en liste
            docs_list = list(results)
        
        # Convertir les objets Document en dictionnaires et filtrer par company_id
        docs = []
        for doc in docs_list:
            # Convertir l'objet Document en dictionnaire
            if hasattr(doc, '__dict__'):
                doc_dict = doc.__dict__
            elif hasattr(doc, 'to_dict'):
                doc_dict = doc.to_dict()
            else:
                # Essayer d'accéder aux attributs directement
                doc_dict = {
                    'id': getattr(doc, 'id', None),
                    'content': getattr(doc, 'content', ''),
                    'company_id': getattr(doc, 'company_id', None),
                    'type': getattr(doc, 'type', None),
                    'file_name': getattr(doc, 'file_name', None)
                }
            
            # Filtrer par company_id
            if doc_dict.get('company_id') == company_id:
                docs.append(doc_dict)
        
        print(f"[INFO] {len(docs)} documents trouvés après filtrage company_id")
        return docs
    except Exception as e:
        print(f"Erreur récupération documents: {e}")
        return []

def update_document_entities(doc_id: str, entities: dict, index_name: str):
    """
    Met à jour le champ 'entities' d'un document MeiliSearch par son id.
    """
    client = get_meilisearch_client()
    if not client:
        return
    try:
        index = client.index(index_name)
        index.update_documents([{'id': doc_id, 'entities': entities}])
    except Exception as e:
        print(f"Erreur mise à jour entités: {e}")

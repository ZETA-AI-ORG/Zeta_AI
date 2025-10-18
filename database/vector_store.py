import time
import os
from typing import Optional, List
import meilisearch
from embedding_models import embed_text, get_embedding_model
from core.preprocessing import preprocess_meilisearch_query
import unicodedata

from utils import log3, timing_metric

# Meilisearch client - CLÉS DIRECTES POUR TEST
MEILI_URL = "http://localhost:7700"
MEILI_API_KEY = "Bac2018mado@2066"  # Vraie clé MeiliSearch
MEILI_MASTER_KEY = "Bac2018mado@2066"  # Vraie clé MeiliSearch

# Priorité : MEILI_API_KEY puis MEILI_MASTER_KEY
api_key = MEILI_API_KEY or MEILI_MASTER_KEY
client = meilisearch.Client(MEILI_URL, api_key)
meilisearch_client = client

import qdrant_client
from qdrant_client.models import PointStruct, Distance, VectorParams
from qdrant_client.models import Filter, FieldCondition, MatchValue
from qdrant_client.models import PayloadSchemaType


_qdrant_client = None

# Configuration Qdrant - VALEURS DIRECTES POUR TEST
QDRANT_URL = "localhost"
QDRANT_PORT = 6333
QDRANT_API_KEY = None
QDRANT_TLS = False


def _convert_to_regex_query(query: str) -> str:
    """
    Convertit une requête en format regex pour améliorer le matching MeiliSearch.
    Gère les variations de mots, pluriels, et accents.
    """
    if not query or not query.strip():
        return query
    
    words = query.strip().split()
    regex_words = []
    
    for word in words:
        # Nettoyer le mot
        clean_word = word.strip().lower()
        if len(clean_word) < 2:
            continue
            
        # Gérer les variations communes
        if clean_word.endswith('s') and len(clean_word) > 3:
            # Pluriel -> ajouter variante singulier
            singular = clean_word[:-1]
            regex_words.append(f"({clean_word}|{singular})")
        elif clean_word.endswith('es') and len(clean_word) > 4:
            # Pluriel en -es
            singular = clean_word[:-2]
            regex_words.append(f"({clean_word}|{singular})")
        else:
            regex_words.append(word)
    
    return " ".join(regex_words)


def ensure_meili_settings(index_name: str) -> None:
    """Applique des réglages d'index Meilisearch pour la scalabilité/pertinence.

    - filterableAttributes: permet les filtres multi-tenant et produits
    - searchableAttributes: champs explicites pour un scoring plus contrôlé
    - stopWords/synonyms: laissés vides par défaut (à enrichir si besoin)
    """
    try:
        idx = client.index(index_name)
        # Paramètres par défaut
        filterable = [
            "company_id",
            "category",
            "color",
            "brand",
        ]
        searchable = [
            "title",
            "name",
            "description",
            "content",
            "text",
        ]
        synonyms = {}

        # Spécifique aux indexes de livraison avec boost géographique
        if index_name.startswith("delivery_"):
            # Filtrage étendu pour zones et prix
            for f in ["zone", "zone_group", "city", "price", "price_raw", "delay", "delay_abidjan", "delay_hors_abidjan", "area", "commune"]:
                if f not in filterable:
                    filterable.append(f)
            # Searchable avec priorité zone > city > content
            searchable = ["zone", "zone_group", "city", "area", "commune", "searchable_text", "content_fr", "content", "text", "price_raw", "delay_abidjan", "delay_hors_abidjan"]
            
            # Synonymes géographiques étendus pour delivery
            synonyms.update({
                "yopougon": ["yop", "yopougon-attie", "yopougon-niangon"],
                "adjame": ["adjamé", "adjame-centre", "adjame-village"],
                "abobo": ["abobo-pk18", "abobo-te", "abobo-baoulé"],
                "cocody": ["cocody-angre", "cocody-riviera", "cocody-deux-plateaux"],
                "attecoube": ["attécoubé", "attecoube-centre"],
                "port-bouet": ["port-bouët", "port-bouet-vridi"],
                "treichville": ["treichville-zone-4", "treich"],
                "marcory": ["marcory-zone-4", "marcory-anoumabo"],
                "koumassi": ["koumassi-remblais", "koumassi-sicogi"],
                "plateau": ["plateau-centre", "plateau-dokui"]
            })

        # Spécifique aux indexes produits
        if index_name.startswith("products_"):
            for f in ["brand", "category", "color", "sku", "price", "prices", "product_name"]:
                if f not in filterable:
                    filterable.append(f)
            for s in ["name", "title", "description", "content", "text", "brand", "category", "color", "sku"]:
                if s not in searchable:
                    searchable.append(s)

        # Spécifique aux indexes support/FAQ
        if index_name.startswith("support_"):
            for f in ["tags", "language", "category"]:
                if f not in filterable:
                    filterable.append(f)
            for s in ["faq_question", "title", "content", "text", "tags"]:
                if s not in searchable:
                    searchable.append(s)

        # Spécifique aux documents d'entreprise
        if index_name.startswith("company_docs_"):
            # Configuration complète pour company_docs
            searchable = ["content", "title", "file_name", "id", "text", "description"]
            filterable = ["company_id", "file_name", "id", "section", "language"]
            for f in ["section", "language"]:
                if f not in filterable:
                    filterable.append(f)
            for s in ["title", "content", "text", "section", "language"]:
                if s not in searchable:
                    searchable.append(s)

        # Réglages communs + spécifiques avec boost location/delivery
        ranking_rules = [
            "words",
            "typo",
            "proximity",
            "attribute",
            "exactness"
        ]
        
        # DELIVERY: Prioriser exactitude zone + proximité géographique
        if index_name.startswith("delivery_"):
            ranking_rules = [
                "exactness",    # Zone exacte prioritaire
                "words",        # Mots-clés complets
                "proximity",    # Proximité termes
                "attribute",    # Boost champs zone/city
                "typo"          # Tolérance typos en dernier
            ]
        
        # PRODUCTS: Exactitude name/title prioritaire
        elif index_name.startswith("products_"):
            ranking_rules = ["exactness", "words", "typo", "proximity", "attribute"]
        
        # SUPPORT: Proximité questions-réponses
        elif index_name.startswith("support_"):
            ranking_rules = ["words", "proximity", "exactness", "attribute", "typo"]

        # Stopwords/Synonymes de base (extensibles)
        stop_words = []
        synonyms = {}
        
        if index_name.startswith("support_"):
            synonyms = {
                "livraison": ["delivery", "expedition", "expédition"],
                "retour": ["remboursement", "echange", "échange"],
                "paiement": ["payment", "payer"],
            }
        
        if index_name.startswith("delivery_"):
            synonyms.update({
                "port-bouet": ["port-bouët"],
                "attecoube": ["attécoubé"],
                "adjame": ["adjamé"],
                "yopougon": ["yop", "yopougon-attie", "yopougon-niangon"],
                "abobo": ["abobo-pk18", "abobo-te", "abobo-baoulé"],
                "cocody": ["cocody-angre", "cocody-riviera", "cocody-deux-plateaux"],
                "treichville": ["treichville-zone-4", "treich"],
                "marcory": ["marcory-zone-4", "marcory-anoumabo"],
                "koumassi": ["koumassi-remblais", "koumassi-sicogi"],
                "plateau": ["plateau-centre", "plateau-dokui"]
            })

        # Tolérance aux typos: support permissif, produits strict sur SKU
        typo_tolerance = {"enabled": True}
        if index_name.startswith("support_"):
            typo_tolerance = {"enabled": True, "minWordSizeForTypos": {"oneTypo": 4, "twoTypos": 8}}
        if index_name.startswith("products_"):
            # Pour SKU, on compense via filtres exacts en amont; rester raisonnable
            typo_tolerance = {"enabled": True, "minWordSizeForTypos": {"oneTypo": 5, "twoTypos": 9}}

        settings = {
            "filterableAttributes": filterable,
            "searchableAttributes": searchable,
            "rankingRules": ranking_rules,
            "stopWords": stop_words,
            "synonyms": synonyms,
            "typoTolerance": typo_tolerance,
        }
        # Update idempotent (Meili applique uniquement les diffs)
        task = idx.update_settings(settings)
        # Attendre que les settings soient effectivement appliqués (max ~3s)
        # Selon le client Python, update_settings peut retourner un dict ou rien.
        # On boucle en lisant get_settings jusqu'à voir nos champs (ou timeout)
        start = time.time()
        while True:
            try:
                current = idx.get_settings()
                cur_searchable = current.get("searchableAttributes", []) or []
                cur_filterable = current.get("filterableAttributes", []) or []
                # Si '*' est utilisé côté Meili, considérer comme appliqué
                ok_searchable = (cur_searchable == ["*"])
                if not ok_searchable:
                    ok_searchable = all(a in cur_searchable for a in settings["searchableAttributes"] if a)
                ok_filterable = all(f in cur_filterable for f in settings["filterableAttributes"] if f)
                if ok_searchable and ok_filterable:
                    break
            except Exception:
                # Lire les settings peut échouer pendant l'application; continuer
                pass
            if time.time() - start > 3.0:
                break
            time.sleep(0.15)
    except Exception as e:
        log3("[MEILI] ensure_settings", f"{index_name}: {type(e).__name__}: {e}")


def _build_qdrant_client():
    """Construit un client Qdrant en fonction de la configuration (.env via config.py)."""
    # Qdrant Cloud si URL commence par http(s)
    if QDRANT_URL and (QDRANT_URL.startswith("http://") or QDRANT_URL.startswith("https://")):
        return qdrant_client.QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            prefer_grpc=False,
            timeout=20,
        )
    # Sinon mode host/port (local ou docker)
    host = QDRANT_URL or "localhost"
    return qdrant_client.QdrantClient(
        host=host,
        port=QDRANT_PORT or 6333,
        prefer_grpc=False,
        timeout=20,
    )


def get_qdrant_client():
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = _build_qdrant_client()
    return _qdrant_client


def _ensure_collection(collection: str, vector_size: int):
    """Crée la collection si elle n'existe pas, avec la bonne dimension."""
    qc = get_qdrant_client()
    try:
        qc.get_collection(collection)
        return
    except Exception:
        # On tente de créer la collection
        log3("[QDRANT] Collection", f"Création de '{collection}' avec dim={vector_size}")
        qc.recreate_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
    # Toujours s'assurer que l'index de payload pour company_id existe
    _ensure_company_id_index(collection)


def _ensure_company_id_index(collection: str):
    """Crée un index de payload sur company_id si absent (type KEYWORD)."""
    qc = get_qdrant_client()
    try:
        qc.create_payload_index(
            collection_name=collection,
            field_name="company_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
    except Exception as e:
        # Si l'index existe déjà ou autre non-bloquant, on ignore
        log3("[QDRANT] PayloadIndex", f"company_id index ensure: {type(e).__name__}: {e}")


def images_collection(company_id: str) -> str:
    """Nom de collection Qdrant multi-tenant pour les images."""
    return f"images_{company_id}"


def _company_filter(company_id: str) -> Filter:
    """Filtre Qdrant de défense en profondeur sur company_id."""
    return Filter(must=[FieldCondition(key="company_id", match=MatchValue(value=company_id))])


def upsert_image_embedding(point_id: str, embedding: list, payload: dict):
    """Upsert un embedding d'image dans Qdrant, multi-tenant.

    - Si payload contient 'company_id', on écrit dans la collection images_{company_id}.
    - Sinon, fallback historique vers la collection 'images'.
    """
    company_id = (payload or {}).get("company_id")
    collection = images_collection(company_id) if company_id else "images"
    last_err = None
    for attempt in range(3):
        try:
            qc = get_qdrant_client()
            # S'assurer que la collection existe avec la bonne dimension
            _ensure_collection(collection, vector_size=len(embedding))
            # S'assurer que l'index de payload existe
            _ensure_company_id_index(collection)
            qc.upsert(
                collection_name=collection,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload,
                    )
                ],
            )
            log3("[QDRANT] Upsert", f"Embedding inséré pour id={point_id}")
            return
        except Exception as e:
            last_err = e
            log3("[QDRANT] Exception upsert",
                 f"Tentative {attempt+1}/3 - {type(e).__name__}: {str(e)}")
            # Petite pause avant retry
            time.sleep(0.6 * (attempt + 1))
            # Recréer un client au prochain tour en cas de problème de connexion
            global _qdrant_client
            _qdrant_client = None
    # Si échec après retries
    raise last_err


def search_images(company_id: str, query_vector: list, limit: int = 10, *, min_score: Optional[float] = None, offset: int = 0):
    """Recherche de similarité d'images dans la collection du tenant."""
    qc = get_qdrant_client()
    collection = images_collection(company_id)
    _ensure_collection(collection, vector_size=len(query_vector))
    _ensure_company_id_index(collection)
    flt = _company_filter(company_id)
    hits = qc.search(
        collection_name=collection,
        query_vector=query_vector,
        limit=limit,
        offset=offset or None,
        score_threshold=min_score,
        query_filter=flt,
    )
    # Normaliser la sortie: liste de dicts {id, score, payload}
    return [
        {
            "id": h.id,
            "score": getattr(h, "score", None),
            "payload": getattr(h, "payload", None),
        }
        for h in hits
    ]


def search_delivery(company_id: str, zone_query: str, limit: int = 5) -> List[dict]:
    """Recherche des frais/délais de livraison pour une zone donnée.

    Interroge l'index Meilisearch `delivery` avec un filtre strict par `company_id`.
    Retourne une liste de dicts minimalistes: {zone, price, delay}.
    """
    try:
        idx = meilisearch_client.index("delivery")
        # Requête tolérante aux accents (Meili gère) et casse
        params = {
            "limit": limit,
            "filter": f"company_id = '{company_id}'",
        }
        res = idx.search(zone_query or "", params)
        hits = res.get("hits", [])
        out = []
        for h in hits:
            out.append({
                "zone": h.get("zone"),
                "price": h.get("price"),
                "delay": h.get("delay"),
            })
        log3("[MEILI][delivery]", f"q='{zone_query}' -> {len(out)} résultats (tenant={company_id})")
        return out
    except Exception as e:
        log3("[MEILI][delivery][ERR]", f"{type(e).__name__}: {str(e)}")
        return []


def sample_image_id(company_id: str) -> Optional[str]:
    """Retourne un ID d'image quelconque pour un tenant (utile pour tests)."""
    qc = get_qdrant_client()
    collection = images_collection(company_id)
    try:
        _ensure_company_id_index(collection)
    except Exception:
        pass
    points, next_page_offset = qc.scroll(
        collection_name=collection,
        scroll_filter=_company_filter(company_id),
        limit=1,
        with_payload=False,
        with_vectors=False,
    )
    if points:
        return getattr(points[0], "id", None)
    return None


def find_near_duplicates(company_id: str, query_vector: list, *, min_score: float = 0.995, limit: int = 20) -> List[dict]:
    """Détecte des quasi-doublons visuels en cherchant avec un score élevé."""
    return search_images(company_id=company_id, query_vector=query_vector, limit=limit, min_score=min_score)


def recommend_images_by_id(company_id: str, seed_id: str, limit: int = 10, *, min_score: Optional[float] = None, offset: int = 0):
    """Recommandations d'images similaires à partir d'un ID dans la collection du tenant."""
    qc = get_qdrant_client()
    collection = images_collection(company_id)
    # On tente d'assurer l'index; si la collection n'existe pas encore, cette étape pourra lever mais sera loguée
    try:
        _ensure_company_id_index(collection)
    except Exception:
        pass
    flt = _company_filter(company_id)
    hits = qc.recommend(
        collection_name=collection,
        positive=[seed_id],
        limit=limit,
        offset=offset or None,
        score_threshold=min_score,
        query_filter=flt,
    )
    return [
        {
            "id": h.id,
            "score": getattr(h, "score", None),
            "payload": getattr(h, "payload", None),
        }
        for h in hits
    ]

def _convert_to_regex_query(query: str) -> str:
    """Convertit une requête en format regex pour améliorer le matching."""
    if not query or len(query.strip()) < 2:
        return query
    
    # Séparer les mots
    words = query.strip().split()
    if len(words) == 1:
        # Mot unique: recherche partielle avec wildcards
        word = words[0].lower()
        return f"{word}*"
    
    # Mots multiples: chaque mot avec wildcard optionnel
    regex_words = []
    for word in words:
        if len(word) >= 3:
            regex_words.append(f"{word}*")
        else:
            regex_words.append(word)
    
    return " ".join(regex_words)

async def search_meili_keywords(query: str, company_id: str, target_indexes: List[str] = None) -> list:
    """
    RECHERCHE MEILISEARCH PROPRE - DOCUMENTS COMPLETS UNIQUEMENT
    
    Architecture:
    - Recherche par mots-clés dans les documents indexés
    - Retourne les documents COMPLETS trouvés
    - AUCUNE fragmentation ni recombinaison
    - Un document trouvé = Un document retourné intégralement
    """
    log3("[MEILI_CLEAN]", f"Recherche: '{query}' | Company: {company_id[:8]}...")
    
    # Obtenir la liste des indexes disponibles
    available_indexes = get_available_indexes(company_id)
    indexes_to_search = target_indexes if target_indexes else available_indexes
    
    log3("[MEILI_CLEAN]", f"Indexes: {len(indexes_to_search)} disponibles")
    
    all_documents = []
    unique_contents = set()
    
    # Rechercher dans chaque index
    for index_name in indexes_to_search:
        try:
            client = get_meilisearch_client()
            if not client:
                continue
                
            index = client.index(index_name)
            
            # Recherche simple et directe
            search_results = index.search(query, {
                'limit': 3,  # Maximum 3 documents par index
                'attributesToRetrieve': ['content', 'id', 'type', 'document_id'],
                'attributesToHighlight': [],
                'showMatchesPosition': False
            })
            
            # Traiter les résultats - DOCUMENTS COMPLETS UNIQUEMENT
            for hit in search_results.get('hits', []):
                content = hit.get('content', '').strip()
                
                # Vérifier que le contenu est valide et non dupliqué
                if content and len(content) > 50 and content not in unique_contents:
                    unique_contents.add(content)
                    all_documents.append({
                        'content': content,
                        'id': hit.get('id', ''),
                        'type': hit.get('type', ''),
                        'source_index': index_name
                    })
                    
                    log3("[MEILI_CLEAN]", f"Document ajouté depuis {index_name}: {content[:100]}...")
        
        except Exception as e:
            log3("[MEILI_CLEAN][ERROR]", f"Erreur index {index_name}: {str(e)}")
            continue
    
    # Retourner les résultats
    if all_documents:
        log3("[MEILI_CLEAN][SUCCESS]", f"{len(all_documents)} documents trouvés")
        return all_documents
    else:
        log3("[MEILI_CLEAN][NO_RESULTS]", "Aucun document trouvé")
        return []




def search_single_index_meilisearch(index_uid: str, query: str, company_id: str, limit: int = 10) -> str:
    """
    Recherche dans un seul index Meilisearch avec requêtes HTTP directes
    """
    try:
        import requests
        import os
        
        meili_url = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
        meili_key = os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
        
        headers = {
            "Authorization": f"Bearer {meili_key}",
            "Content-Type": "application/json"
        }
        
        search_data = {
            "q": query,
            "limit": limit
        }
        
        response = requests.post(
            f"{meili_url}/indexes/{index_uid}/search",
            headers=headers,
            json=search_data,
            timeout=30
        )
        
        if response.status_code == 200:
            results = response.json()
            hits = results.get("hits", [])
            
            if hits:
                # Formater les résultats
                formatted_results = []
                for hit in hits:
                    content = hit.get("content", "")
                    if content and len(content.strip()) > 0:
                        formatted_results.append(content.strip())
                return [{"content": doc} for doc in formatted_results]
            else:
                return []
        
        return []
        
    except Exception as e:
        return []


        filter_clauses.append(f"sku = '{pf['sku']}'")
    if "brand" in pf:
        filter_clauses.append(f"brand = '{pf['brand']}'")
    if "category" in pf:
        filter_clauses.append(f"category = '{pf['category']}'")
    if filter_clauses:
        params["filter"] = " AND ".join(filter_clauses)

    # FALLBACK MULTIPLE: Essayer plusieurs requêtes si nécessaire
    hits = []
    for fallback_q in fallback_queries:
        if not fallback_q.strip():
            continue
        regex_query = _convert_to_regex_query(fallback_q)
        try:
            res = client.index(idx_name).search(regex_query, params)
        except Exception as se:
            if "invalid_search_attributes_to_search_on" in str(se) or "attributesToSearchOn" in str(se):
                params.pop("attributesToSearchOn", None)
                res = client.index(idx_name).search(regex_query, params)
            else:
                raise
        hits = res.get("hits", []) or []
        if hits:  # Si on trouve des résultats, on s'arrête
            log3("[MEILI][PRODUCTS_SUCCESS]", {
                "query_utilisee": fallback_q,
                "nb_resultats": len(hits)
            })
            break
        if not hits and params.get("filter"):
            res = client.index(idx_name).search("", params)
            hits = res.get("hits", []) or []
        # FALLBACK AUTOMATIQUE VERS INDEX GLOBAL SI AUCUN RÉSULTAT
        if not all_hits and target_indexes and f"company_docs_{company_id}" not in target_indexes:
            log3("[MEILI][FALLBACK_TO_GLOBAL]", {
                "indexes_initiaux": target_indexes,
                "query": search_query,
            })
            
            # Recherche dans l'index global company_docs
            try:
                global_index = f"company_docs_{company_id}"
                params = {"limit": 10}
                res = client.index(global_index).search(search_query, params)
                global_hits = res.get("hits", []) or []
                if global_hits:
                    for h in global_hits:
                        h["_meili_index"] = global_index
                    all_hits.extend(global_hits)
                    total_hits += len(global_hits)
                    log3("[MEILI][FALLBACK_SUCCESS]", {
                        "index_global": global_index,
                        "hits_trouves": len(global_hits),
                        "query": search_query
                    })
                else:
                    log3("[MEILI][FALLBACK_FAILED]", {
                        "index_global": global_index,
                        "query": search_query
                    })
                    
            except Exception as e_fallback:
                log3("[MEILI][FALLBACK_ERROR]", f"Erreur fallback: {e_fallback}")
        
        if not all_hits:
            log3("[MEILI][NO_RESULTS_FINAL]", {
                "q": search_query[:120],
                "company_id": company_id,
                "indexes_testes": target_indexes or tenant_indexes
            })
            return []

        # Déduplication simple par id + index
        seen = set()
        dedup_hits = []
        for h in all_hits:
            key = (h.get("id"), h.get("_meili_index"))
            if key not in seen:
                seen.add(key)
                dedup_hits.append(h)

        # Construire un contexte lisible par type d'index
        parts = []
        for h in dedup_hits:
            src = h.get("_meili_index", "")
            if src.startswith("products_"):
                # Champs produits typiques
                name = h.get("name") or h.get("title") or "Produit"
                desc = h.get("description") or h.get("content") or h.get("text") or ""
                price = h.get("price") or (h.get("prices") if isinstance(h.get("prices"), (str, int, float)) else None)
                line = f"[PRODUIT] {name}: {desc}"
                if price:
                    line += f" | Prix: {price}"
                parts.append(line)
            elif src.startswith("delivery_"):
                zone = h.get("zone") or h.get("area") or h.get("city") or "Zone"
                delay = (h.get("delay") or h.get("avgDeliveryTime") or 
                        h.get("delay_abidjan") or h.get("delay_hors_abidjan") or "Non spécifié")
                price = (h.get("price") or h.get("price_raw") or 
                        h.get("frais") or h.get("cout") or "Non spécifié")
                
                # Formatage enrichi pour delivery
                zone_group = h.get("zone_group", "")
                if zone_group and zone_group != zone:
                    zone_display = f"{zone} ({zone_group})"
                else:
                    zone_display = zone
                
                parts.append(f"[LIVRAISON] {zone_display} | Délai: {delay} | Prix: {price}")
            elif src.startswith("support_"):
                q = h.get("faq_question") or h.get("title") or "FAQ"
                a = h.get("faq_answer") or h.get("content") or h.get("text") or ""
                parts.append(f"[SUPPORT] {q} — {a}")
            else:
                # company_docs_ ou autre: contenu brut
                parts.append(h.get("content") or h.get("text") or h.get("description") or "")

        # Grouper et optimiser le contexte delivery pour requêtes multi-zones
        delivery_parts = [p for p in parts if p.startswith("[LIVRAISON]")]
        other_parts = [p for p in parts if not p.startswith("[LIVRAISON]")]
        
        # Déduplication et tri des zones delivery
        unique_delivery = {}
        for part in delivery_parts:
            # Extraire la zone du format "[LIVRAISON] Zone | ..."
            try:
                zone_info = part.split("|")[0].replace("[LIVRAISON]", "").strip()
                if zone_info not in unique_delivery:
                    unique_delivery[zone_info] = part
            except:
                unique_delivery[len(unique_delivery)] = part
        
        # Reconstruire le contexte optimisé
        optimized_parts = list(unique_delivery.values()) + other_parts
        context = "\n".join([p for p in optimized_parts if p])
        log3("[MEILI] Contexte final (multi-index)", {
            "longueur": len(context),
            "total_hits": total_hits,
            "nb_dedup": len(dedup_hits),
            "nb_zones_delivery": len([p for p in optimized_parts if p.startswith("[LIVRAISON]")])
        })
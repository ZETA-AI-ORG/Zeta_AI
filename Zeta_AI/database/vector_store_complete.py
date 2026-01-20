"""
Vector Store complet avec logique MeiliSearch restaurée
"""
import os
import time
import unicodedata
from typing import List, Dict, Any, Optional
import meilisearch
import qdrant_client
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from config import get_config
from core.logging_utils import log3

# Configuration
cfg = get_config()

# MeiliSearch
MEILI_URL = getattr(cfg, "MEILI_URL", "http://localhost:7700")
MEILI_API_KEY = getattr(cfg, "MEILI_API_KEY", None)
MEILI_MASTER_KEY = getattr(cfg, "MEILI_MASTER_KEY", None)

# Priorité : MEILI_API_KEY puis MEILI_MASTER_KEY
api_key = MEILI_API_KEY or MEILI_MASTER_KEY
client = meilisearch.Client(MEILI_URL, api_key)

# Qdrant
_qdrant_client = None
QDRANT_URL = getattr(cfg, "QDRANT_URL", "localhost")
QDRANT_PORT = getattr(cfg, "QDRANT_PORT", 6333)
QDRANT_API_KEY = getattr(cfg, "QDRANT_API_KEY", None)
QDRANT_TLS = getattr(cfg, "QDRANT_TLS", False)


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
    """
    Applique des réglages d'index Meilisearch pour la scalabilité/pertinence.

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


def search_meili_keywords(query: str, company_id: str) -> str:
    """
    Recherche par mots-clés Meilisearch (FAQ, catalogue, livraison, support)
    Alignée avec Quick Context: interroge plusieurs indexes du tenant et fusionne
    les résultats pour fournir un contexte riche au moteur RAG/HyDE.
    """
    log3("[MEILISEARCH] Requête", query)
    log3("[MEILISEARCH] Query originale", f"{query}, Company ID: {company_id}")
    
    # FILTRAGE MINIMAL: Retirer UNIQUEMENT les mots vides
    # Stratégie simplifiée : ÉLIMINATION des mots vides, GARDE du reste
    log3("[FILTRAGE_MINIMAL]", "🔧 FILTRAGE MINIMAL ACTIVÉ")
    log3("[FILTRAGE_MINIMAL]", f"📝 Query originale: '{query}'")
    log3("[FILTRAGE_MINIMAL]", f"📊 Longueur: {len(query)} caractères")
    
    # Appliquer le filtrage minimal (mots vides uniquement)
    from core.smart_stopwords import filter_query_for_meilisearch
    processed_keywords = filter_query_for_meilisearch(query)
    
    log3("[FILTRAGE_MINIMAL]", f"📝 Query filtrée: '{processed_keywords}'")
    log3("[FILTRAGE_MINIMAL]", f"📊 Longueur filtrée: {len(processed_keywords)} caractères")
    
    # FALLBACK INTELLIGENT: Si filtrage trop agressif, utiliser requête originale
    base_q = (processed_keywords or "").strip()
    if not base_q or len(base_q.split()) < 2:
        log3("[MEILI][FALLBACK]", {
            "query_originale": query,
            "processed_keywords": processed_keywords,
            "raison": "Filtrage trop agressif, utilisation requête originale"
        })
        base_q = (query or "").strip()
    
    if not base_q:
        log3("[MEILI][GUARD] Requête vide", {
            "query_initiale": query,
            "processed_keywords": processed_keywords,
            "company_id": company_id
        })
        return ""
    
    # Recherche multi-index alignée avec Quick Context
    try:
        # Indexes du tenant à parcourir (certains peuvent ne pas exister selon la société)
        tenant_indexes = [
            f"products_{company_id}",
            f"delivery_{company_id}",
            f"support_{company_id}",
            f"company_docs_{company_id}",
        ]

        # AMÉLIORATION: Utiliser base_q qui contient déjà le fallback
        search_query = base_q
        
        # Appliquer la logique regex pour améliorer le matching
        regex_query = _convert_to_regex_query(search_query)
        
        # FALLBACK SUPPLÉMENTAIRE: Si aucun résultat, essayer requête simplifiée
        fallback_queries = [
            search_query,  # Requête principale
            ' '.join([w for w in search_query.split() if len(w) > 2]),  # Mots > 2 chars
            ' '.join([w for w in query.split() if w.lower() in ['casque', 'rouge', 'prix', 'combien', 'livraison', 'wave', 'whatsapp']])  # Mots-clés essentiels
        ]

        # Détection simple des communes (normalisées, accents enlevés)
        def _normalize_txt(s: str) -> str:
            if not s:
                return ""
            return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii').lower()

        communes = [
            "abobo", "adjame", "adjamé", "attecoube", "attécoubé", "cocody", "yopougon",
            "treichville", "plateau", "marcory", "koumassi", "port-bouet", "port-bouët",
            "bingerville", "songon", "anyama"
        ]
        normalized_query = _normalize_txt(search_query)
        detected_commune = None
        for c in communes:
            if _normalize_txt(c) in normalized_query:
                detected_commune = c
                break

        # Heuristiques légères: extraire intent de filtres pour autres indexes
        def extract_products_filters(q: str) -> dict:
            qn = _normalize_txt(q)
            filters = {}
            # SKU simple: séquences alnum avec tirets/underscores de 5+ chars
            import re
            m = re.search(r"\b([a-z0-9][a-z0-9\-_]{4,})\b", qn)
            if m:
                filters["sku"] = m.group(1)
            # Marque/catégorie/couleur basées sur indicateurs
            for key, indicators in {
                "brand": ["marque", "brand"],
                "category": ["categorie", "catégorie", "category"],
                "color": ["couleur", "color"],
            }.items():
                for ind in indicators:
                    if ind in qn:
                        # naïf: récupérer mot après l'indicateur
                        after = qn.split(ind, 1)[1].strip().split()
                        if after:
                            filters[key] = after[0].strip(",.;:!?")
                            break
            return filters

        def extract_support_filters(q: str) -> dict:
            qn = _normalize_txt(q)
            filters = {}
            # Tags clés courants (à enrichir)
            known_tags = ["livraison", "paiement", "retour", "commande", "compte", "garantie"]
            for t in known_tags:
                if t in qn:
                    filters.setdefault("tags", []).append(t)
            return filters

        def extract_docs_filters(q: str) -> dict:
            qn = _normalize_txt(q)
            filters = {}
            # Langue
            if "francais" in qn or "français" in q:
                filters["language"] = "fr"
            elif "anglais" in qn or "english" in qn or "en" == qn:
                filters["language"] = "en"
            # Section indicatifs
            for ind in ["cgvu", "conditions", "mentions", "politique", "livraison", "paiement", "retour"]:
                if ind in qn:
                    filters["section"] = ind
                    break
            return filters

        all_hits = []
        total_hits = 0
        # Utilitaire: ramène une liste d'attributs valides selon l'index
        def _valid_attributes(idx_nm: str, desired: List[str]) -> List[str]:
            try:
                s = client.index(idx_nm).get_settings() or {}
                searchable = s.get("searchableAttributes")
                if not searchable or searchable == ["*"]:
                    return [a for a in desired if a]
                desired_set = set(desired)
                return [a for a in desired if a in searchable]
            except Exception:
                # En cas d'erreur, ne pas imposer d'attributs
                return []

        for idx_name in tenant_indexes:
            try:
                ensure_meili_settings(idx_name)
                params = {"limit": 10}
                
                # Utiliser la requête regex optimisée
                final_query = regex_query if regex_query else search_query

                # Spécifique index livraison: cibler les bons champs + filtres par commune
                if idx_name.startswith("delivery_"):
                    # Champs potentiellement utiles selon le schéma d'ingestion
                    desired_attrs = [
                        "zone", "zone_group", "city", "searchable_text",
                        "content_fr", "content", "text", "price_raw", "delay_abidjan", "delay_hors_abidjan"
                    ]
                    valid_attrs = _valid_attributes(idx_name, desired_attrs)
                    if valid_attrs:
                        params["attributesToSearchOn"] = valid_attrs

                    # Appliquer un filtre structuré si une commune est détectée
                    if detected_commune:
                        # Meilisearch: filtrage sur champ array: zone_group = "Abobo" fonctionne
                        commune_val = detected_commune
                        params["filter"] = (
                            f"(zone = '{commune_val}') OR (zone_group = '{commune_val}') OR (city = '{commune_val}')"
                        )

                    # 1er essai: requête avec regex intelligente
                    try:
                        res = client.index(idx_name).search(final_query, params)
                    except Exception as se:
                        # Si invalid_search_attributes_to_search_on -> retry sans le paramètre
                        if "invalid_search_attributes_to_search_on" in str(se) or "attributesToSearchOn" in str(se):
                            params.pop("attributesToSearchOn", None)
                            res = client.index(idx_name).search(search_query, params)
                        else:
                            raise
                    hits = res.get("hits", []) or []

                    # Fallback 1: 0 hit -> requête réduite à la commune seule, si dispo
                    if (not hits) and detected_commune:
                        res = client.index(idx_name).search(detected_commune, params)
                        hits = res.get("hits", []) or []

                    # Fallback 2: encore 0 hit -> requête vide avec filtre seul
                    if not hits and params.get("filter"):
                        res = client.index(idx_name).search("", params)
                else:
                    # Index non-livraison: comportement standard
                    # PRODUCTS
                    if idx_name.startswith("products_"):
                        desired_attrs = [
                            "name", "title", "description", "content", "text", "brand", "category", "color", "sku"
                        ]
                        valid_attrs = _valid_attributes(idx_name, desired_attrs)
                        if valid_attrs:
                            params["attributesToSearchOn"] = valid_attrs
                        # Filtres structurés à partir de la requête
                        pf = extract_products_filters(search_query)
                        filter_clauses = []
                        if "sku" in pf:
                            filter_clauses.append(f"sku = '{pf['sku']}'")
                        if "brand" in pf:
                            filter_clauses.append(f"brand = '{pf['brand']}'")
                        if "category" in pf:
                            filter_clauses.append(f"category = '{pf['category']}'")
                        if "color" in pf:
                            filter_clauses.append(f"color = '{pf['color']}'")
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
                        
                        # Fallbacks additionnels si toujours rien
                        if not hits and (pf.get("sku") or pf.get("brand") or pf.get("category")):
                            key = pf.get("sku") or pf.get("brand") or pf.get("category")
                            regex_key = _convert_to_regex_query(key)
                            res = client.index(idx_name).search(regex_key, params)
                            hits = res.get("hits", []) or []
                        if not hits and params.get("filter"):
                            res = client.index(idx_name).search("", params)
                            hits = res.get("hits", []) or []

                    # SUPPORT
                    elif idx_name.startswith("support_"):
                        desired_attrs = [
                            "faq_question", "title", "content", "text", "tags"
                        ]
                        valid_attrs = _valid_attributes(idx_name, desired_attrs)
                        if valid_attrs:
                            params["attributesToSearchOn"] = valid_attrs
                        sf = extract_support_filters(search_query)
                        if sf.get("tags"):
                            ors = " OR ".join([f"tags = '{t}'" for t in sf["tags"]])
                            params["filter"] = f"({ors})"
                        # Conversion regex pour améliorer le matching
                        regex_query = _convert_to_regex_query(search_query)
                        
                        try:
                            res = client.index(idx_name).search(regex_query, params)
                        except Exception as se:
                            if "invalid_search_attributes_to_search_on" in str(se) or "attributesToSearchOn" in str(se):
                                params.pop("attributesToSearchOn", None)
                                res = client.index(idx_name).search(regex_query, params)
                            else:
                                raise
                        hits = res.get("hits", []) or []
                        if not hits and sf.get("tags"):
                            # Essai question seule (réduction bruit) avec regex
                            tags_query = " ".join([t for t in sf["tags"]])
                            regex_tags_query = _convert_to_regex_query(tags_query)
                            res = client.index(idx_name).search(regex_tags_query, params)
                            hits = res.get("hits", []) or []
                        if not hits and params.get("filter"):
                            res = client.index(idx_name).search("", params)

                    # COMPANY DOCS
                    elif idx_name.startswith("company_docs_"):
                        desired_attrs = [
                            "title", "content", "text", "section", "language"
                        ]
                        valid_attrs = _valid_attributes(idx_name, desired_attrs)
                        if valid_attrs:
                            params["attributesToSearchOn"] = valid_attrs
                        df = extract_docs_filters(search_query)
                        clauses = []
                        if df.get("language"):
                            clauses.append(f"language = '{df['language']}'")
                        if df.get("section"):
                            clauses.append(f"section = '{df['section']}'")
                        if clauses:
                            params["filter"] = " AND ".join(clauses)
                        # Conversion regex pour améliorer le matching
                        regex_query = _convert_to_regex_query(search_query)
                        
                        try:
                            res = client.index(idx_name).search(regex_query, params)
                        except Exception as se:
                            if "invalid_search_attributes_to_search_on" in str(se) or "attributesToSearchOn" in str(se):
                                params.pop("attributesToSearchOn", None)
                                res = client.index(idx_name).search(regex_query, params)
                            else:
                                raise
                        hits = res.get("hits", []) or []
                        if not hits and (df.get("section") or df.get("language")):
                            # Essayer avec l'attribut clé seul avec regex
                            keyq = df.get("section") or df.get("language")
                            regex_keyq = _convert_to_regex_query(keyq)
                            res = client.index(idx_name).search(regex_keyq, params)
                            hits = res.get("hits", []) or []
                        if not hits and params.get("filter"):
                            res = client.index(idx_name).search("", params)

                    else:
                        # Fallback générique
                        res = client.index(idx_name).search(search_query, params)
                hits = res.get("hits", []) or []
                total_hits += len(hits)
                # Annoter la source d'index pour debug
                for h in hits:
                    h["_meili_index"] = idx_name
                all_hits.extend(hits)
                log3("[MEILI][SEARCH]", {
                    "index": idx_name,
                    "q": search_query,
                    "hits": len(hits),
                    "time_ms": res.get("processingTimeMs", 0),
                    "sample": (hits[0].get("name") or hits[0].get("title") or hits[0].get("zone") or hits[0].get("content") or hits[0].get("text", ""))[:80] if hits else ""
                })
            except Exception as e_idx:
                # Index manquant ou autre erreur non bloquante
                log3("[MEILI][INDEX_ERR]", f"{idx_name}: {type(e_idx).__name__}: {e_idx}")

        if not all_hits:
            log3("[MEILI][NO_RESULTS]", {
                "q": search_query[:120],
                "company_id": company_id
            })
            return ""

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
        return context

    except Exception as e:
        log3("[MEILI][ERR] Recherche multi-index", f"{type(e).__name__}: {e}")
        return "Aucun contexte Meilisearch disponible."


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
    """Crée l'index de payload pour company_id si nécessaire."""
    qc = get_qdrant_client()
    try:
        # Vérifier si l'index existe déjà
        info = qc.get_collection(collection)
        payload_schema = info.payload_schema
        if payload_schema and "company_id" in payload_schema:
            return
    except Exception:
        pass
    
    # Créer l'index
    try:
        qc.create_payload_index(
            collection_name=collection,
            field_name="company_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        log3("[QDRANT] Index", f"Index company_id créé pour {collection}")
    except Exception as e:
        log3("[QDRANT] Index", f"Erreur création index company_id: {e}")


def search_similar_documents(
    query_embedding: List[float],
    collection: str,
    company_id: str,
    limit: int = 10,
    min_score: float = 0.7,
    offset: int = None,
) -> List[Dict[str, Any]]:
    """Recherche de documents similaires dans Qdrant."""
    qc = get_qdrant_client()
    _ensure_collection(collection, len(query_embedding))
    
    # Filtre par company_id
    flt = models.Filter(
        must=[
            models.FieldCondition(
                key="company_id",
                match=models.MatchValue(value=company_id),
            )
        ]
    )
    
    hits = qc.search(
        collection_name=collection,
        query_vector=query_embedding,
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


def search_similar_documents_by_id(
    seed_id: str,
    collection: str,
    company_id: str,
    limit: int = 10,
    min_score: float = 0.7,
    offset: int = None,
) -> List[Dict[str, Any]]:
    """Recherche de documents similaires basée sur un ID de document."""
    qc = get_qdrant_client()
    _ensure_collection(collection, 768)  # Dimension par défaut
    
    # Filtre par company_id
    flt = models.Filter(
        must=[
            models.FieldCondition(
                key="company_id",
                match=models.MatchValue(value=company_id),
            )
        ]
    )
    
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







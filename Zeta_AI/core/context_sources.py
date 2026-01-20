from typing import Dict, List
from core.concept_extractor import generate_search_blocks
from utils import log3
import re
import unicodedata
import itertools

class ContextSources:
    def __init__(self, meilisearch_client, supabase_client):
        self.meili = meilisearch_client
        self.supabase = supabase_client

    async def search_all(self, concepts: Dict[str, List[str]], company_id: str) -> Dict:
        from utils import log3
        results = {}
        log3("[Quick Context][UNIVERSAL] Concepts détectés", list(concepts.keys()))
        # Recherche Meilisearch sur TOUS les concepts extraits (universel)
        if concepts:
            meili_results = await self._search_meilisearch(concepts, company_id)
            results['meilisearch'] = meili_results
        if 'company_terms' in concepts:
            company_results = await self._search_company_info(company_id)
            results['company'] = company_results
        if 'policy_terms' in concepts:
            policy_results = await self._search_policies(concepts, company_id)
            results['policies'] = policy_results
        return results

    async def _search_meilisearch(self, blocks_with_weights: List[Dict[str, any]], company_id: str) -> List:
        """
        Exécute une requête Meilisearch DISTINCTE pour chaque bloc de concepts (plan de division),
        puis fusionne et déduplique les résultats.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        from core.meilisearch_utils import get_index_attributes

        bases = ["company", "products", "delivery", "support"]
        # Agréger les attributs disponibles sur les index présents
        attrs_to_retrieve = []
        for base in bases:
            idx_name = f"{base}_{company_id}"
            try:
                index_attrs = get_index_attributes(self.meili, idx_name)
                cand = index_attrs.get('relevant_searchable', []) or index_attrs.get('searchableAttributes', [])
                if cand:
                    for a in cand:
                        if a not in attrs_to_retrieve:
                            attrs_to_retrieve.append(a)
            except Exception:
                # Index potentiellement manquant, on ignore
                continue
        if not attrs_to_retrieve:
            attrs_to_retrieve = ['*']

        def _normalize_text(s: str) -> str:
            try:
                s = ''.join(c for c in unicodedata.normalize('NFD', s or '') if unicodedata.category(c) != 'Mn')
            except Exception:
                s = s or ''
            return s.lower()

        def _token_to_regex(tok: str) -> str:
            t = _normalize_text(tok)
            return rf"\b{re.escape(t)}s?\b"

        def _build_and_regex(tokens: List[str]) -> str:
            toks = [_token_to_regex(t) for t in tokens]
            parts = [rf"(?=.*{t})" for t in toks]
            return rf"(?i){''.join(parts)}.*"

        def _build_k_of_n_regex(tokens: List[str], k: int = 2) -> str:
            if not tokens:
                return r"(?i).*"
            toks = [_token_to_regex(t) for t in tokens]
            k = min(k, len(toks))
            musts = []
            for comb in itertools.combinations(toks, k):
                parts = [rf"(?=.*{t})" for t in comb]
                musts.append(''.join(parts))
            return rf"(?i)(?:{'|'.join(musts)}).*"

        async def search_one_block(block_info):
            block = block_info['block']
            weight = block_info['weight']
            query = " ".join(block)
            tokens = list(block)
            # --- Détection éventuelle d'une commune pour l'index livraison ---
            # On mappe vers la casse des données Meili (ex: "Abobo", "Port-Bouët") pour les filtres exacts
            commune_canonical = {
                'abobo': 'Abobo',
                'adjamé': 'Adjamé', 'adjame': 'Adjamé',
                'attécoubé': 'Attécoubé', 'attecoube': 'Attécoubé',
                'cocody': 'Cocody',
                'plateau': 'Plateau',
                'marcory': 'Marcory',
                'koumassi': 'Koumassi',
                'treichville': 'Treichville',
                'angré': 'Angré', 'angre': 'Angré',
                'yopougon': 'Yopougon',
                'port-bouët': 'Port-Bouët', 'port-bouet': 'Port-Bouët',
                'bingerville': 'Bingerville',
                'songon': 'Songon',
                'anyama': 'Anyama',
                'brofodoumé': 'Brofodoumé', 'brofodoume': 'Brofodoumé',
                'grand-bassam': 'Grand-Bassam',
                'dabou': 'Dabou',
                'riviera': 'Riviera',
                'hors abidjan': 'Hors Abidjan'
            }
            tokens_norm = [_normalize_text(t) for t in tokens]
            detected_communes = [commune_canonical[t] for t in tokens_norm if t in commune_canonical]
            commune_for_filter = detected_communes[0] if detected_communes else None
            regex_and = _build_and_regex(tokens)
            regex_k2 = _build_k_of_n_regex(tokens, k=2 if len(tokens) >= 2 else 1)
            # Log synthétique désactivé (trop verbeux)
            merged_hits = []
            for base in bases:
                idx_name = f"{base}_{company_id}"
                try:
                    def _do_search(params):
                        # Utilise MeiliHelper si disponible, sinon fallback client brut
                        try:
                            # Logs côté Quick Context (en plus des logs MeiliHelper)
                            log3("[Quick Context][MEILI][REQ]", f"index={idx_name} q='{query}' params={params}")
                        except Exception:
                            pass
                        if hasattr(self.meili, "_safe_search"):
                            # MeiliHelper path (retries + logs)
                            return self.meili._safe_search(idx_name, query, params)
                        if hasattr(self.meili, "index"):
                            # meilisearch.Client direct
                            return self.meili.index(idx_name).search(query, params)
                        if hasattr(self.meili, "client") and hasattr(self.meili.client, "index"):
                            # Objet wrapper avec attribut client
                            return self.meili.client.index(idx_name).search(query, params)
                        raise RuntimeError("Meilisearch client incompatible: attendu MeiliHelper ou meilisearch.Client")

                    # Primary params (relaxed matching if supported)
                    params = {
                        'limit': 10,  # Augmenté pour plus de résultats
                        'attributesToRetrieve': attrs_to_retrieve,
                        'showRankingScore': True,
                        'matchingStrategy': 'last',
                    }
                    # Pour l'index delivery, concentrer la recherche sur les champs pertinents
                    if base == 'delivery':
                        delivery_search_attrs = [
                            'zone', 'zone_group', 'city', 'searchable_text', 'content_fr',
                            'price_raw', 'delay_abidjan', 'delay_hors_abidjan'
                        ]
                        # Essayez d'utiliser attributesToSearchOn (Meilisearch >=1.19)
                        params['attributesToSearchOn'] = delivery_search_attrs

                        # Si une commune est détectée, tenter un filtre exact sur zone/zone_group
                        if commune_for_filter:
                            # Meilisearch supporte les OR logiques dans filter
                            # Note: nécessite que 'zone' et 'zone_group' soient filterableAttributes
                            params['filter'] = f"zone = '{commune_for_filter}' OR zone_group = '{commune_for_filter}'"

                    try:
                        search_results = await loop.run_in_executor(None, lambda: _do_search(params))
                    except Exception as e_first:
                        # Fallback: remove unsupported parameters like 'matchingStrategy'
                        msg = str(e_first)
                        if 'Unknown field' in msg or 'unknown field' in msg:
                            fallback_params = {
                                'limit': 10,
                                'attributesToRetrieve': attrs_to_retrieve,
                                'showRankingScore': True,
                            }
                            # Réessayer sans attributesToSearchOn si non supporté
                            if base == 'delivery':
                                # Certains clients lèvent aussi sur attributesToSearchOn
                                pass
                            search_results = await loop.run_in_executor(None, lambda: _do_search(fallback_params))
                        else:
                            raise
                    try:
                        log3("[Quick Context][MEILI][RES]", f"index={idx_name} hits={len((search_results or {}).get('hits', []))}")
                    except Exception:
                        pass
                    hits = search_results.get('hits', [])

                    # --- Fallbacks spécifiques delivery si aucun hit ---
                    if base == 'delivery' and len(hits) == 0:
                        # 1) Simplifier la requête: si elle contient un mot-clé générique livraison, garder uniquement la commune
                        generic_delivery_terms = {"livraison", "delivery", "transport", "prix", "tarif", "frais"}
                        has_generic = any(t in generic_delivery_terms for t in tokens_norm)
                        if commune_for_filter and has_generic:
                            simple_q = commune_for_filter
                            fallback_params2 = {
                                'limit': 10,
                                'attributesToRetrieve': attrs_to_retrieve,
                                'showRankingScore': True,
                                'matchingStrategy': 'last',
                                'attributesToSearchOn': delivery_search_attrs,
                                'filter': f"zone = '{commune_for_filter}' OR zone_group = '{commune_for_filter}'",
                            }
                            try:
                                search_results = await loop.run_in_executor(None, lambda: _do_search({**fallback_params2, 'q': simple_q}))
                                hits = search_results.get('hits', [])
                            except Exception:
                                pass

                        # 2) Dernier recours: q vide + filtre exact (pur filtre)
                        if commune_for_filter and len(hits) == 0:
                            fallback_params3 = {
                                'limit': 10,
                                'attributesToRetrieve': attrs_to_retrieve,
                                'showRankingScore': True,
                                'filter': f"zone = '{commune_for_filter}' OR zone_group = '{commune_for_filter}'",
                            }
                            try:
                                search_results = await loop.run_in_executor(None, lambda: _do_search({**fallback_params3, 'q': ''}))
                                hits = search_results.get('hits', [])
                            except Exception:
                                pass
                    for hit in hits:
                        hit['_block_weight'] = weight
                        hit['_block_query'] = query
                        hit['_meili_index'] = idx_name
                        # Post-score regex
                        try:
                            search_text = ' '.join(str(hit.get(a, '')) for a in (attrs_to_retrieve or []))
                        except Exception:
                            search_text = ''
                        norm_text = _normalize_text(search_text)
                        score_bonus = 0
                        if re.search(regex_and, norm_text):
                            score_bonus += 2
                        elif re.search(regex_k2, norm_text):
                            score_bonus += 1
                        # Scoring avancé par type d'index et pertinence
                        try:
                            # DELIVERY: Boost géographique + pertinence livraison
                            if base == 'delivery':
                                zone_val = str(hit.get('zone') or '').strip().lower()
                                zone_group_val = str(hit.get('zone_group') or '').strip().lower()
                                city_val = str(hit.get('city') or '').strip().lower()
                                
                                # Boost fort pour correspondance exacte commune
                                if commune_for_filter:
                                    commune_norm = commune_for_filter.lower()
                                    if (zone_val == commune_norm or 
                                        zone_group_val == commune_norm or 
                                        city_val == commune_norm):
                                        score_bonus += 3  # Boost très fort
                                    # Boost moyen pour correspondance partielle
                                    elif (commune_norm in zone_val or 
                                          commune_norm in zone_group_val or 
                                          commune_norm in city_val):
                                        score_bonus += 1.5
                                
                                # Boost pour présence de mots-clés livraison
                                delivery_keywords = ['frais', 'délai', 'livraison', 'transport', 'zone']
                                content_text = (str(hit.get('content') or '') + ' ' + 
                                              str(hit.get('searchable_text') or '')).lower()
                                delivery_matches = sum(1 for kw in delivery_keywords if kw in content_text)
                                score_bonus += delivery_matches * 0.5
                            
                            # PRODUCTS: Boost nom/titre vs description
                            elif base == 'products':
                                name_match = any(token.lower() in str(hit.get('name') or '').lower() 
                                               for token in tokens)
                                title_match = any(token.lower() in str(hit.get('title') or '').lower() 
                                                for token in tokens)
                                if name_match or title_match:
                                    score_bonus += 2  # Boost fort pour nom/titre
                                
                                # Boost pour correspondance SKU exacte
                                sku_val = str(hit.get('sku') or '').lower()
                                if any(token.lower() == sku_val for token in tokens if len(token) > 4):
                                    score_bonus += 3  # Boost très fort pour SKU
                            
                            # SUPPORT: Boost questions vs réponses
                            elif base == 'support':
                                question_match = any(token.lower() in str(hit.get('faq_question') or '').lower() 
                                                   for token in tokens)
                                if question_match:
                                    score_bonus += 1.5  # Boost pour correspondance question
                            
                            # Boost général pour freshness (si timestamp disponible)
                            if hit.get('timestamp') or hit.get('created_at'):
                                score_bonus += 0.2  # Léger boost pour contenu récent
                                
                        except Exception:
                            pass
                        hit['_regex_bonus'] = score_bonus
                        merged_hits.append(hit)
                except Exception as e:
                    # Index manquant ou erreur de requête — on journalise en debug uniquement
                    log3("[Quick Context][MEILI][SKIP]", f"{idx_name}: {str(e)}")
                    continue
            return merged_hits

        # Exécution parallèle des sous-requêtes (une par bloc)
        all_results = await asyncio.gather(*(search_one_block(block) for block in blocks_with_weights))

        # Fusion et déduplication avec scoring pondéré avancé
        merged_hits = []
        seen_ids = set()
        for hit in all_results:
            for h in hit:
                hit_id = h.get('id')
                if hit_id and hit_id in seen_ids:
                    continue
                if hit_id:
                    seen_ids.add(hit_id)
                
                # Score final = score Meili + bonus regex + poids du bloc + boost type
                meili_score = h.get('_rankingScore', 0) or 0
                regex_bonus = h.get('_regex_bonus', 0) or 0
                block_weight = h.get('_block_weight', 1) or 1
                
                # Boost par type d'index (priorité business)
                index_name = h.get('_meili_index', '')
                type_boost = 0
                if 'delivery' in index_name:
                    type_boost = 0.3  # Priorité livraison
                elif 'products' in index_name:
                    type_boost = 0.2  # Priorité produits
                elif 'support' in index_name:
                    type_boost = 0.1  # Support moins prioritaire
                
                # Normalisation du score Meilisearch (0-1)
                normalized_meili = min(meili_score / 1.0, 1.0) if meili_score > 0 else 0
                
                final_score = (normalized_meili * block_weight) + regex_bonus + type_boost
                h['final_score'] = final_score
                merged_hits.append(h)

        # Trier les résultats finaux par le score pondéré
        merged_hits.sort(key=lambda x: x.get('final_score', 0), reverse=True)

        log3("[Quick Context][SYNTHÈSE] Nb docs fusionnés/dédupliqués", len(merged_hits))
        return merged_hits

    async def _search_company_info(self, company_id: str) -> dict:
        try:
            return await self.supabase.get_company_context(company_id)
        except Exception as e:
            log3("[Quick Context][ERREUR SUPABASE]", str(e))
            return {}

    async def _search_policies(self, concepts: Dict, company_id: str) -> List:
        # Placeholder: à compléter selon la structure réelle de la base
        return []

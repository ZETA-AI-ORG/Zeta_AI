from __future__ import annotations

import os
import time
import random
import logging
from typing import Any, Dict, List, Optional

try:
    import meilisearch
except Exception:  # pragma: no cover
    meilisearch = None  # type: ignore

# Import du validateur d'index
try:
    from core.index_validator import IndexValidator, IndexValidationError, validate_before_creation
except ImportError:
    # Fallback si le module n'est pas disponible
    class IndexValidator:
        @staticmethod
        def validate_index_name(index_uid: str, strict: bool = True) -> bool:
            return True
    
    class IndexValidationError(Exception):
        pass
    
    def validate_before_creation(index_uid: str) -> str:
        return index_uid


class MeiliHelper:
    def _generate_ngrams(self, text: str, max_n: int = 3, min_n: int = 1) -> list:
        """Génère tous les n-grams décroissants de la requête utilisateur (max_n -> min_n)"""
        words = text.strip().split()
        ngrams = []
        for n in range(min(max_n, len(words)), min_n - 1, -1):
            for i in range(len(words) - n + 1):
                ngram = " ".join(words[i:i+n])
                ngrams.append(ngram)
        return ngrams

    def search_products_ngram(
        self,
        company_id: str,
        q: str,
        *,
        color: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        limit: int = 10,
        attributes: Optional[list] = None,
        max_ngram: int = 3,
        min_ngram: int = 1,
    ) -> Dict[str, Any]:
        """
        Recherche produit optimisée : essaie les n-grams décroissants (n=3 à n=1).
        Retourne le premier résultat non vide (early exit).
        Optimise les attributs retournés et logge la latence/niveau n-gram.
        """
        uid = self._index_uid("products", company_id)
        ngrams = self._generate_ngrams(q, max_n=max_ngram, min_n=min_ngram)
        params_base: Dict[str, Any] = {"limit": limit}
        if attributes:
            params_base["attributesToRetrieve"] = attributes
        else:
            params_base["attributesToRetrieve"] = ["id", "name", "price", "category", "stock"]
        filters: List[str] = []
        if color:
            filters.append(f'color = "{color}"')
        if category:
            filters.append(f'category = "{category}"')
        if subcategory:
            filters.append(f'subcategory = "{subcategory}"')
        if filters:
            params_base["filter"] = " AND ".join(filters)

        for ngram in ngrams:
            t0 = time.time()
            params = dict(params_base)
            result = self._safe_search(uid, ngram, params)
            latency_ms = (time.time() - t0) * 1000
            self._logger.info(f"[Meili][NGRAM] ngram='{ngram}' len={len(ngram.split())} hits={len(result.get('hits', []))} latency={latency_ms:.1f}ms")
            if result and result.get("hits"):
                self._logger.info(f"[Meili][NGRAM][SUCCESS] Niveau n-gram={len(ngram.split())} (ngram='{ngram}')")
                return result
        # Aucun résultat trouvé
        self._logger.info(f"[Meili][NGRAM][FAIL] Aucun résultat sur tous les n-grams pour q='{q}'")
        return {"hits": [], "estimatedTotalHits": 0}

class MeiliHelper:
    """
    Helper dédié aux indexes par entreprise (dedicated indexes).
    
    TYPES D'INDEX AUTORISÉS (5 uniquement):
    - products_<company_id>           : Catalogue produits
    - delivery_<company_id>           : Informations de livraison
    - support_paiement_<company_id>   : Support et paiement
    - localisation_<company_id>       : Informations de localisation
    - company_docs_<company_id>       : Documents d'entreprise

    RÈGLES STRICTES:
    - Tous les noms d'index DOIVENT être en minuscules
    - Aucun doublon en majuscules n'est autorisé
    - Seuls les 5 types ci-dessus peuvent être créés
    - Format obligatoire: type_company_id

    Utilise client.index(uid).search(...), conformément aux bonnes pratiques.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        *,
        max_retries: int = 3,
        base_backoff_ms: int = 200,
    ) -> None:
        url = url or os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
        api_key = api_key or os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
        if meilisearch is None:
            raise RuntimeError("meilisearch n'est pas installé. pip install meilisearch")
        self.client: meilisearch.Client = meilisearch.Client(url, api_key)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._max_retries = max(1, int(max_retries))
        self._base_backoff_ms = max(50, int(base_backoff_ms))
        # Log d'initialisation concis pour confirmer l'URL et la clé utilisées
        try:
            _mk_masked = (api_key[:4] + "..." + api_key[-2:]) if len(api_key) >= 6 else ("set" if api_key else "empty")
            self._logger.info(f"[Meili][INIT] url={url} key={_mk_masked}")
        except Exception:
            pass
        # Réglages optimisés pour l'index unifié company_docs_{company_id}
        # Configuration basée sur les tests de performance (81.2% de réussite)
        self.unified_default_settings = {
            "searchableAttributes": [
                "searchable_text",  # Priorité 1: texte optimisé pour recherche
                "content_fr",       # Priorité 2: contenu français
                "product_name",     # Priorité 3: noms de produits
                "color",           # Priorité 4: couleurs
                "tags",            # Priorité 5: tags de catégorisation
                "zone",            # Priorité 6: zones de livraison
                "zone_group",      # Priorité 7: groupes de zones
                "method",          # Priorité 8: méthodes de paiement
                "details",         # Priorité 9: détails divers
                "category",        # Priorité 10: catégories
                "subcategory",     # Priorité 11: sous-catégories
                "name",            # Priorité 12: noms génériques
                "slug"             # Priorité 13: slugs
            ],
            "filterableAttributes": [
                "company_id", "type", "category", "subcategory", "color",
                "price", "currency", "stock", "city", "zone", "zone_group",
                "method", "policy_kind", "tags", "brand", "section", "language"
            ],
            "sortableAttributes": ["price", "stock", "updated_at"],
            "rankingRules": ["words", "typo", "proximity", "attribute", "exactness"],
            "synonyms": {
                "cocody": ["cocody-angré", "cocody-danga", "cocody-riviera"],
                "yopougon": ["yop", "yopougon-niangon", "yopougon-selmer"],
                "abidjan": ["cocody", "yopougon", "plateau", "marcory", "treichville"],
                "casque": ["casques", "helmet", "helmets"],
                "moto": ["motorcycle", "motorbike", "scooter"],
                "noir": ["black", "noire"],
                "bleu": ["blue", "bleue"],
                "rouge": ["red"],
                "gris": ["gray", "grey", "grise"]
            },
            "stopWords": [
                "le", "la", "les", "de", "du", "des", "un", "une", "et", "à", "au", "aux",
                "en", "pour", "sur", "par", "avec", "sans", "ce", "cette", "ces"
            ],
            "typoTolerance": {
                "enabled": True,
                "minWordSizeForTypos": {"oneTypo": 5, "twoTypos": 9},
                "disableOnWords": ["paris", "violet", "inexistant"],
                "disableOnAttributes": ["zone", "color"]
            },
            "faceting": {"maxValuesPerFacet": 100},
            "pagination": {"maxTotalHits": 1000}
        }

    # ---------- INTERNAL RESILIENT SEARCH ----------
    def _safe_search(self, index_uid: str, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search with simple retry + exponential backoff + jitter."""
        last_err: Optional[Exception] = None
        # Simulation mode: bypass Meili to debug application flow
        try:
            simulate = os.getenv("MEILI_SIMULATE", "0").lower() in ("1", "true", "yes")
        except Exception:
            simulate = False
        if simulate and index_uid.startswith("products"):
            self._logger.info(f"[Meili][SIMULATE][REQ] index={index_uid} q='{query}' params={params}")
            simulated = {
                "hits": [
                    {
                        "id": "sim-1",
                        "name": "casques moto gris",
                        "category": "moto",
                        "color": "gris",
                        "min_price": 45000,
                        "max_price": 65000,
                        "currency": "XOF",
                        "company_id": params.get("filter", "").replace("company_id = ", "").strip("'\"") if isinstance(params, dict) else None,
                    }
                ],
                "estimatedTotalHits": 1,
                "limit": params.get("limit", 10),
                "query": query,
            }
            self._logger.info(f"[Meili][SIMULATE][RES] index={index_uid} hits=1 est=1 sample=['casques moto gris']")
            return simulated
        for attempt in range(1, self._max_retries + 1):
            try:
                self._logger.info(f"[Meili][REQ] index={index_uid} q='{query}' params={params}")
                result = self.client.index(index_uid).search(query, params)
                try:
                    sample = [h.get("name") for h in (result or {}).get("hits", [])[:3]]
                except Exception:
                    sample = []
                self._logger.info(
                    f"[Meili][RES] index={index_uid} hits={len((result or {}).get('hits', []))} "
                    f"est={(result or {}).get('estimatedTotalHits')} sample={sample}"
                )
                return result
            except Exception as e:  # broad: network/api errors
                last_err = e
                wait_ms = self._base_backoff_ms * (2 ** (attempt - 1))
                # jitter 0.5x-1.5x
                jitter = random.uniform(0.5, 1.5)
                sleep_s = (wait_ms * jitter) / 1000.0
                self._logger.warning(
                    f"Meili search failed on '{index_uid}' (attempt {attempt}/{self._max_retries}): {e}. Retrying in {sleep_s:.2f}s"
                )
                time.sleep(sleep_s)
        # last attempt failed
        self._logger.error(f"Meili search permanently failed on '{index_uid}': {last_err}")
        # Propagate last error to caller
        if last_err:
            raise last_err
        # Fallback (should not happen)
        return {"hits": [], "estimatedTotalHits": 0}

    @staticmethod
    def _index_uid(base: str, company_id: str) -> str:
        # Aligner le schéma avec routes/meili.py et appliquer la validation
        import re
        def sanitize(uid: str) -> str:
            s = re.sub(r"[^A-Za-z0-9_-]", "_", uid)
            s = re.sub(r"_+", "_", s).strip("_")
            return s[:200]
        
        # Construire le nom d'index
        index_uid = sanitize(f"{base}_{company_id}")
        
        # Validation stricte pour empêcher les index non conformes
        try:
            validate_before_creation(index_uid)
        except IndexValidationError as e:
            # Log l'erreur et suggérer une correction
            logging.error(f"[MeiliHelper] Index invalide détecté: {e}")
            suggestion = IndexValidator.suggest_valid_name(index_uid)
            if suggestion:
                logging.warning(f"[MeiliHelper] Utilisation du nom suggéré: {suggestion}")
                return suggestion
            else:
                raise ValueError(f"Impossible de créer un index valide pour base='{base}', company_id='{company_id}'")
        
        return index_uid

    # ---------- SEARCH HELPERS ----------
    def search_products(
        self,
        company_id: str,
        q: str,
        *,
        color: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        uid = self._index_uid("products", company_id)
        params: Dict[str, Any] = {"limit": limit}
        filters: List[str] = []
        if color:
            filters.append(f'color = "{color}"')
        if category:
            filters.append(f'category = "{category}"')
        if subcategory:
            filters.append(f'subcategory = "{subcategory}"')
        if filters:
            params["filter"] = " AND ".join(filters)
        return self._safe_search(uid, q, params)

    def search_delivery(
        self,
        company_id: str,
        zone_query: str,
        *,
        limit: int = 10,
    ) -> Dict[str, Any]:
        uid = self._index_uid("delivery", company_id)
        params: Dict[str, Any] = {"limit": limit}
        try:
            # Tente l'index dédié delivery_{company_id}
            return self._safe_search(uid, zone_query, params)
        except Exception:
            # Fallback: index partagé 'delivery' + filtre par company_id
            params["filter"] = f"company_id = '{company_id}'"
            return self._safe_search("delivery", zone_query, params)

    def search_support(
        self,
        company_id: str,
        q: str,
        *,
        method: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        uid = self._index_uid("support", company_id)
        params: Dict[str, Any] = {"limit": limit}
        if method:
            params["filter"] = f'method = "{method}"'
        return self._safe_search(uid, q, params)

    # ---------- SETTINGS HELPERS (OPTIONNEL) ----------
    def apply_synonyms(
        self,
        company_id: str,
        base: str,
        synonyms: Dict[str, List[str]],
    ) -> None:
        uid = self._index_uid(base, company_id)
        self.client.index(uid).update_settings({"synonyms": synonyms})

    def apply_ranking_rules(
        self,
        company_id: str,
        base: str,
        ranking_rules: List[str],
    ) -> None:
        uid = self._index_uid(base, company_id)
        self.client.index(uid).update_settings({"rankingRules": ranking_rules})

    def apply_stop_words(
        self,
        company_id: str,
        base: str,
        stop_words: List[str],
    ) -> None:
        uid = self._index_uid(base, company_id)
        self.client.index(uid).update_settings({"stopWords": stop_words})

    # ---------- UNIFIED INDEX HELPERS ----------
    def unified_index_uid(self, company_id: str) -> str:
        return self._index_uid("company_docs", company_id)

    def ensure_unified_index(self, company_id: str, *, apply_settings: bool = True, extra_settings: Optional[Dict[str, Any]] = None) -> None:
        uid = self.unified_index_uid(company_id)
        try:
            self.client.create_index(uid, {"primaryKey": "id"})
        except Exception:
            pass
        if apply_settings:
            settings = dict(self.unified_default_settings)
            if extra_settings:
                # merge simple lists without duplicates
                for k, v in extra_settings.items():
                    if isinstance(v, list):
                        cur = list(dict.fromkeys(settings.get(k, []) + v))
                        settings[k] = cur
                    else:
                        settings[k] = v
            self.client.index(uid).update_settings(settings)

    def index_exists(self, company_id: str) -> bool:
        """Check if the unified index exists for a company"""
        uid = self.unified_index_uid(company_id)
        try:
            self.client.index(uid).get_stats()
            return True
        except Exception:
            return False

    def purge_unified_index(self, company_id: str) -> Dict[str, Any]:
        """CONDITIONAL AGGRESSIVE PURGE: Only purge if index exists with data"""
        uid = self.unified_index_uid(company_id)
        
        self._logger.info(f"🔍 PURGE DEBUG: Starting purge process for company_id='{company_id}', index='{uid}'")
        
        # STEP 1: Check if index exists
        self._logger.info(f"🔍 PURGE DEBUG: Checking if index {uid} exists...")
        if not self.index_exists(company_id):
            self._logger.info(f"📭 PURGE DEBUG: INDEX DOES NOT EXIST: {uid} - No purge needed")
            return {"success": True, "method": "no_purge_needed", "index": uid, "reason": "index_not_found"}
        
        self._logger.info(f"✅ PURGE DEBUG: Index {uid} EXISTS - Proceeding with checks")
        
        try:
            # STEP 2: Check if index has documents
            self._logger.info(f"🔍 PURGE DEBUG: Getting stats for index {uid}...")
            stats = self.client.index(uid).get_stats()
            doc_count = getattr(stats, 'numberOfDocuments', 0)
            self._logger.info(f"📊 PURGE DEBUG: Index {uid} has {doc_count} documents")
            
            if doc_count == 0:
                self._logger.info(f"📭 PURGE DEBUG: INDEX EMPTY: {uid} - No purge needed")
                return {"success": True, "method": "no_purge_needed", "index": uid, "reason": "index_empty"}
            
            # STEP 3: Index exists and has data - AGGRESSIVE PURGE
            self._logger.info(f"🗑️ PURGE DEBUG: STARTING AGGRESSIVE PURGE - Index {uid} has {doc_count} documents")
            self._logger.info(f"🗑️ PURGE DEBUG: Attempting to delete index {uid}...")
            
            try:
                delete_task = self.client.delete_index(uid)
                self._logger.info(f"✅ PURGE DEBUG: Delete task created successfully: {delete_task}")
                
                # Wait for deletion to complete
                import time
                self._logger.info(f"⏳ PURGE DEBUG: Waiting 3 seconds for deletion to complete...")
                time.sleep(3)
                
                # Verify deletion
                self._logger.info(f"🔍 PURGE DEBUG: Verifying index {uid} was deleted...")
                try:
                    verify_stats = self.client.index(uid).get_stats()
                    self._logger.warning(f"⚠️ PURGE DEBUG: Index {uid} still exists after deletion! Stats: {verify_stats}")
                except Exception as verify_e:
                    self._logger.info(f"✅ PURGE DEBUG: Index {uid} successfully deleted (expected error: {verify_e})")
                    
            except Exception as delete_e:
                self._logger.error(f"❌ PURGE DEBUG: Index deletion failed for {uid}: {delete_e}")
                self._logger.error(f"❌ PURGE DEBUG: Delete exception type: {type(delete_e).__name__}")
                self._logger.error(f"❌ PURGE DEBUG: Delete exception args: {delete_e.args}")
            
            # STEP 4: Recreate the index with optimized settings
            self._logger.info(f"🆕 PURGE DEBUG: Attempting to recreate index {uid}...")
            try:
                create_task = self.client.create_index(uid, {"primaryKey": "id"})
                self._logger.info(f"✅ PURGE DEBUG: Create task successful: {create_task}")
                
                self._logger.info(f"⏳ PURGE DEBUG: Waiting 2 seconds for creation to complete...")
                time.sleep(2)
                
                # Verify creation
                self._logger.info(f"🔍 PURGE DEBUG: Verifying index {uid} was created...")
                new_stats = self.client.index(uid).get_stats()
                new_doc_count = getattr(new_stats, 'numberOfDocuments', 0)
                self._logger.info(f"✅ PURGE DEBUG: New index {uid} created with {new_doc_count} documents")
                
            except Exception as create_e:
                self._logger.error(f"❌ PURGE DEBUG: Index creation failed for {uid}: {create_e}")
                self._logger.error(f"❌ PURGE DEBUG: Create exception type: {type(create_e).__name__}")
                return {"success": False, "error": f"Creation failed: {create_e}", "index": uid}
            
            # STEP 5: Apply optimized configuration immediately
            self._logger.info(f"⚙️ PURGE DEBUG: Applying optimized settings to {uid}...")
            try:
                self.client.index(uid).update_settings(self.unified_default_settings)
                self._logger.info(f"✅ PURGE DEBUG: Settings applied successfully to {uid}")
            except Exception as settings_e:
                self._logger.error(f"❌ PURGE DEBUG: Settings application failed for {uid}: {settings_e}")
            
            self._logger.info(f"🎉 PURGE DEBUG: AGGRESSIVE PURGE COMPLETED for {uid} - {doc_count} documents purged")
            return {"success": True, "method": "aggressive_delete_recreate", "index": uid, "documents_purged": doc_count}
            
        except Exception as e:
            self._logger.error(f"💥 PURGE DEBUG: CRITICAL FAILURE for {uid}: {e}")
            self._logger.error(f"💥 PURGE DEBUG: Exception type: {type(e).__name__}")
            self._logger.error(f"💥 PURGE DEBUG: Exception args: {e.args}")
            import traceback
            self._logger.error(f"💥 PURGE DEBUG: Full traceback: {traceback.format_exc()}")
            return {"success": False, "error": str(e), "index": uid}

    def upsert_unified_documents(self, company_id: str, documents: List[Dict[str, Any]], *, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        uid = self.unified_index_uid(company_id)
        self.ensure_unified_index(company_id, apply_settings=True, extra_settings=settings)
        # enrich docs
        enriched: List[Dict[str, Any]] = []
        for d in documents or []:
            if not isinstance(d, dict):
                continue
            dd = dict(d)
            dd.setdefault("company_id", company_id)
            if "id" not in dd or not dd.get("id"):
                # fallback UUID if missing
                import uuid as _uuid
                dd["id"] = str(_uuid.uuid4())
            enriched.append(dd)
        res = self.client.index(uid).add_documents(enriched)
        return {"task": res, "count": len(enriched), "index": uid}

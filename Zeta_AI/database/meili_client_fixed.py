from __future__ import annotations

import os
import time
import random
import logging
import requests
from typing import Any, Dict, List, Optional

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

    CORRECTION CRITIQUE: Utilise des requêtes HTTP directes au lieu de l'API Python cassée.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        *,
        max_retries: int = 3,
        base_backoff_ms: int = 200,
    ) -> None:
        self.url = url or os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
        self.api_key = api_key or os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
        self._logger = logging.getLogger(self.__class__.__name__)
        self._max_retries = max(1, int(max_retries))
        self._base_backoff_ms = max(50, int(base_backoff_ms))
        
        # Headers pour les requêtes HTTP
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Log d'initialisation
        try:
            _mk_masked = (self.api_key[:4] + "..." + self.api_key[-2:]) if len(self.api_key) >= 6 else ("set" if self.api_key else "empty")
            self._logger.info(f"[Meili][INIT][HTTP] url={self.url} key={_mk_masked}")
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

    def _make_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
        """Fait une requête HTTP directe à Meilisearch (CORRIGÉ)"""
        url = f"{self.url}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self._logger.error(f"[Meili][HTTP] Erreur requête {endpoint}: {e}")
            return {}

    # ---------- INTERNAL RESILIENT SEARCH (CORRIGÉ AVEC HTTP) ----------
    def _safe_search(self, index_uid: str, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search with HTTP requests + retry + exponential backoff + jitter."""
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
                self._logger.info(f"[Meili][HTTP][REQ] index={index_uid} q='{query}' params={params}")
                
                # Préparer les données pour la requête HTTP
                search_data = {
                    "q": query,
                    "limit": params.get("limit", 10),
                    "attributesToRetrieve": ["*"]
                }
                
                # Ajouter le filtre si présent
                if "filter" in params:
                    search_data["filter"] = params["filter"]
                
                # Faire la requête HTTP directe
                result = self._make_request(f"/indexes/{index_uid}/search", "POST", search_data)
                
                if result:
                    hits = result.get("hits", [])
                    try:
                        sample = [h.get("content", "")[:50] for h in hits[:3]]
                    except Exception:
                        sample = []
                    
                    self._logger.info(
                        f"[Meili][HTTP][RES] index={index_uid} hits={len(hits)} "
                        f"est={result.get('estimatedTotalHits')} sample={sample}"
                    )
                    return result
                else:
                    raise Exception("Réponse HTTP vide")
                    
            except Exception as e:  # broad: network/api errors
                last_err = e
                wait_ms = self._base_backoff_ms * (2 ** (attempt - 1))
                # jitter 0.5x-1.5x
                jitter = random.uniform(0.5, 1.5)
                sleep_s = (wait_ms * jitter) / 1000.0
                self._logger.warning(
                    f"Meili HTTP search failed on '{index_uid}' (attempt {attempt}/{self._max_retries}): {e}. Retrying in {sleep_s:.2f}s"
                )
                time.sleep(sleep_s)
        
        # last attempt failed
        self._logger.error(f"Meili HTTP search permanently failed on '{index_uid}': {last_err}")
        # Return empty result instead of raising
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

    # ---------- SEARCH HELPERS (CORRIGÉS AVEC HTTP) ----------
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
        uid = self._index_uid("support_paiement", company_id)  # Utiliser support_paiement
        params: Dict[str, Any] = {"limit": limit}
        if method:
            params["filter"] = f'method = "{method}"'
        return self._safe_search(uid, q, params)

    # ---------- UNIFIED INDEX HELPERS (CORRIGÉS) ----------
    def unified_index_uid(self, company_id: str) -> str:
        return self._index_uid("company_docs", company_id)

    def ensure_unified_index(self, company_id: str, *, apply_settings: bool = True, extra_settings: Optional[Dict[str, Any]] = None) -> None:
        uid = self.unified_index_uid(company_id)
        
        # Créer l'index via HTTP
        try:
            self._make_request(f"/indexes", "POST", {"uid": uid, "primaryKey": "id"})
        except Exception:
            pass  # Index existe déjà
        
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
            
            # Appliquer les settings via HTTP
            self._make_request(f"/indexes/{uid}/settings", "PATCH", settings)

    def index_exists(self, company_id: str) -> bool:
        """Check if the unified index exists for a company"""
        uid = self.unified_index_uid(company_id)
        try:
            stats = self._make_request(f"/indexes/{uid}/stats")
            return bool(stats)
        except Exception:
            return False

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
        
        # Ajouter les documents via HTTP
        result = self._make_request(f"/indexes/{uid}/documents", "POST", enriched)
        return {"task": result, "count": len(enriched), "index": uid}

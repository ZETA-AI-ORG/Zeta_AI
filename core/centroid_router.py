import json
import logging
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import numpy as np
import unicodedata
import os

from core.botlive_stopwords import extract_botlive_keywords

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None  # type: ignore


logger = logging.getLogger(__name__)


# Incrémentez cette version chaque fois que la logique de centroid ou des augmentations change
CACHE_VERSION = "v8-shadow-augment-20251205b"


@dataclass
class IntentCentroid:
    intent_id: int
    intent_name: str
    prompt_target: str
    score: int
    centroid: np.ndarray
    boost_interrogatif: bool = False
    keywords: List[str] = field(default_factory=list)


class CentroidRouter:
    """Router simple basé sur des centroids d'intent.

    - Lit le corpus v2 dans intents/ecommerce_intents.json
    - Construit un centroid (moyenne des embeddings) par intent
    - Utilise la similarité cosinus pour router un message
    - Aucun boost ni logique métier avancée à ce stade
    """

    def __init__(
        self,
        corpus_path: str = "intents/ecommerce_intents_full.json",
        model_name: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        cache_dir: str = "cache/embeddings",
        use_cache: bool = True,
    ) -> None:
        self.corpus_path = Path(corpus_path)
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.use_cache = use_cache
        self.interrogative_words = [
            "où", "comment", "quand", "quel", "quelle", "quels", "quelles",
            "combien", "pourquoi", "est-ce que", "c'est quoi", "qui", "quoi",
            "c ou", "c koi", "c combien"
        ]

        # Keywords issus du Shadow (analyse offline) pour boosting lexical
        self.intent_keywords_shadow: Dict[str, List[dict]] = self._load_intent_keywords_shadow()
        # Mots-clés universels (cross-company) facultatifs
        univ = self._load_universal_keywords()
        if univ:
            self.intent_keywords_shadow = self._merge_keywords_maps(self.intent_keywords_shadow, univ)

        logger.info("Initialisation du CentroidRouter")
        logger.info("Chargement du corpus depuis %s", self.corpus_path)

        if not self.corpus_path.exists():
            raise FileNotFoundError(f"Corpus intents introuvable: {self.corpus_path}")

        with self.corpus_path.open("r", encoding="utf-8") as f:
            self.corpus = json.load(f)

        if SentenceTransformer is None:
            raise RuntimeError(
                "sentence-transformers n'est pas installé. "
                "Installe: pip install sentence-transformers"
            )

        logger.info("Chargement du modèle d'embeddings %s", model_name)
        self.model = SentenceTransformer(model_name)

        logger.info("Construction des centroids d'intent")
        self.centroids: Dict[int, IntentCentroid] = self._build_centroids()
        logger.info("CentroidRouter initialisé avec %d intents", len(self.centroids))

    # ---------------------------------------------------------------------
    # Cache helpers
    # ---------------------------------------------------------------------
    def _get_cache_path(self, intent_id: int) -> Path:
        # Utilise le nom du modèle et une version pour invalider proprement
        model_id = (
            self.model_name.split("/")[-1]
            .replace(" ", "_")
            .replace(".", "-")
            .replace(":", "-")
        )
        return self.cache_dir / f"intent_{intent_id}_centroid_{model_id}_{CACHE_VERSION}.pkl"

    def _load_cached_centroid(self, intent_id: int) -> np.ndarray | None:
        path = self._get_cache_path(intent_id)
        if path.exists():
            try:
                with path.open("rb") as f:
                    return pickle.load(f)
            except Exception:
                return None
        return None

    def _save_cached_centroid(self, intent_id: int, centroid: np.ndarray) -> None:
        path = self._get_cache_path(intent_id)
        try:
            with path.open("wb") as f:
                pickle.dump(centroid, f)
        except Exception:
            # Le cache est purement opportuniste
            pass

    # ---------------------------------------------------------------------
    # Centroid building
    # ---------------------------------------------------------------------
    def _build_centroids(self) -> Dict[int, IntentCentroid]:
        centroids: Dict[int, IntentCentroid] = {}
        augment_map = self._load_shadow_augment()

        intents = self.corpus.get("intents", []) or []
        for intent_data in intents:
            intent_id = int(intent_data["id"])
            name = str(intent_data["name"])
            # Support both new and legacy field names
            prompt_target = str(
                (intent_data.get("prompt_target") or intent_data.get("prompt_cible") or "A")
            ).strip()
            score = int(intent_data.get("score") or intent_data.get("score_hierarchie", 0))
            boost_interrogatif = bool(intent_data.get("boost_interrogatif", False))
            kw_list = [
                str(k).lower()
                for k in (intent_data.get("keywords", []) or [])
                if isinstance(k, str)
            ]

            cached = self._load_cached_centroid(intent_id) if self.use_cache else None

            if cached is not None:
                centroid_vec = cached
            else:
                # Récupération des variations par type
                variations_naturelles = intent_data.get("variations_naturelles", []) or []
                variations_bruitees = intent_data.get("variations_bruitees", []) or []
                variations_nouchi = intent_data.get("variations_nouchi", []) or []
                variations_ambig = (
                    intent_data.get("variations_ambiguës", [])
                    or intent_data.get("variations_ambiguees", [])
                    or []
                )
                variations_zones = intent_data.get("variations_zones_generiques", []) or []
                variations_confirm = intent_data.get("variations_confirmation_reception", []) or []

                # Filtrage des chaînes vides
                naturals = [v for v in variations_naturelles if isinstance(v, str) and v.strip()]
                noisy = [v for v in variations_bruitees if isinstance(v, str) and v.strip()]
                nouchi = [v for v in variations_nouchi if isinstance(v, str) and v.strip()]
                ambigs = [v for v in variations_ambig if isinstance(v, str) and v.strip()]

                if not (naturals or noisy or nouchi or ambigs):
                    # On ignore les intents vides
                    continue

                def _mean_embed(texts: List[str]) -> np.ndarray | None:
                    if not texts:
                        return None
                    arr = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
                    return arr.mean(axis=0)

                # Poids par type (on limite/neutralise l'influence des ambiguïtés)
                # Pour 9 (livraison) et 11 (suivi), on met 0 sur ambiguïtés pour mieux séparer
                if intent_id in (9, 11):
                    w_nat, w_noisy, w_nouchi, w_amb = 0.8, 1.15, 1.1, 0.0
                else:
                    w_nat, w_noisy, w_nouchi, w_amb = 1.0, 0.9, 0.9, 0.2
                parts: List[np.ndarray] = []
                weights: List[float] = []

                for group, w in ((naturals, w_nat), (noisy, w_noisy), (nouchi, w_nouchi), (ambigs, w_amb)):
                    vec = _mean_embed(group)
                    if vec is not None:
                        parts.append(vec)
                        weights.append(w)

                # Groupes "extra" faiblement pondérés pour ne pas diluer le centroid
                extra_weight = 0.35 if intent_id in (9, 11) else 0.20
                if variations_zones:
                    vec_z = _mean_embed([v for v in variations_zones if isinstance(v, str) and v.strip()])
                    if vec_z is not None:
                        parts.append(vec_z)
                        weights.append(extra_weight)
                if variations_confirm:
                    vec_c = _mean_embed([v for v in variations_confirm if isinstance(v, str) and v.strip()])
                    if vec_c is not None:
                        parts.append(vec_c)
                        weights.append(extra_weight)

                # Somme pondérée des moyennes
                centroid_vec = np.zeros(parts[0].shape, dtype=float)
                total_w = 0.0
                for vec, w in zip(parts, weights):
                    centroid_vec = centroid_vec + (vec * w)
                    total_w += w
                # Intégration légère des exemples Shadow (si présents)
                try:
                    aug_texts = [
                        v for v in (augment_map.get(str(intent_id)) or [])
                        if isinstance(v, str) and v.strip()
                    ]
                    if aug_texts:
                        def _mean_embed(texts: List[str]) -> np.ndarray | None:
                            if not texts:
                                return None
                            arr = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
                            return arr.mean(axis=0)
                        vec_aug = _mean_embed(aug_texts[:80])
                        if vec_aug is not None:
                            # Poids faible pour ne pas diluer le centroid de base
                            aug_w = 0.35 if intent_id in (9, 11) else 0.25
                            # Normalisation L2
                            norm_aug = float(np.linalg.norm(vec_aug))
                            if norm_aug > 0:
                                vec_aug = vec_aug / norm_aug
                            centroid_vec = centroid_vec + (vec_aug * aug_w)
                            total_w += aug_w
                except Exception:
                    pass
                if total_w > 0:
                    centroid_vec = centroid_vec / total_w

                # Normalisation L2
                norm = float(np.linalg.norm(centroid_vec))
                if norm > 0:
                    centroid_vec = centroid_vec / norm

                if self.use_cache:
                    self._save_cached_centroid(intent_id, centroid_vec)

            centroids[intent_id] = IntentCentroid(
                intent_id=intent_id,
                intent_name=name,
                prompt_target=prompt_target,
                score=score,
                centroid=centroid_vec,
                boost_interrogatif=boost_interrogatif,
                keywords=kw_list,
            )

        if not centroids:
            raise RuntimeError("Aucun centroid d'intent construit depuis le corpus")

        return centroids

    # ---------------------------------------------------------------------
    # Shadow augment loader
    # ---------------------------------------------------------------------
    def _load_shadow_augment(self) -> Dict[str, List[str]]:
        """Charge un mapping facultatif intent_id -> exemples utilisateur (shadow).
        Fichier attendu (override via env INTENT_AUGMENT_IN): intents/augment/shadow_augment.json
        Format: {"9": ["...", ...], "11": ["...", ...]}
        """
        try:
            p = Path(os.getenv("INTENT_AUGMENT_IN", "intents/augment/shadow_augment.json"))
            if not p.exists():
                return {}
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f) or {}
                # Sanitize
                clean: Dict[str, List[str]] = {}
                for k, arr in data.items():
                    if not isinstance(arr, list):
                        continue
                    vals = []
                    for s in arr:
                        if isinstance(s, str):
                            s2 = s.strip()
                            if s2:
                                vals.append(s2)
                    if vals:
                        clean[str(k)] = vals
                if clean:
                    logger.info("[CENTROID] Shadow augment chargé pour %d intents", len(clean))
                return clean
        except Exception:
            return {}

    def _load_universal_keywords(self) -> Dict[str, List[dict]]:
        """Charge des mots-clés universels (cross-company) si disponibles.

        Fichier attendu (override via env INTENT_UNIVERSAL_KEYWORDS_IN): intents/keywords/universal_keywords.json
        Format: {"9": {"keywords": [{"word": "changer", "global_frequency": 12, "company_support": 3}, ...]}, ...}
        Les champs sont mappés vers (word, frequency, specificity) pour réutiliser la même logique de boost.
        """
        try:
            p = Path(os.getenv("INTENT_UNIVERSAL_KEYWORDS_IN", "intents/keywords/universal_keywords.json"))
            if not p.exists():
                return {}
            with p.open("r", encoding="utf-8") as f:
                raw = json.load(f) or {}
            out: Dict[str, List[dict]] = {}
            for k, v in raw.items():
                if not isinstance(v, dict):
                    continue
                kw_list = v.get("keywords") or []
                if not isinstance(kw_list, list):
                    continue
                entries: List[dict] = []
                for item in kw_list:
                    if not isinstance(item, dict):
                        continue
                    w = item.get("word")
                    if not isinstance(w, str) or not w.strip():
                        continue
                    gf = item.get("global_frequency", 0)
                    cs = item.get("company_support", 1)
                    try:
                        gf = int(gf)
                    except Exception:
                        gf = 0
                    try:
                        cs = float(cs)
                    except Exception:
                        cs = 1.0
                    entries.append({
                        "word": w.strip().lower(),
                        "frequency": gf,
                        # Utiliser le support comme proxy de spécificité cross-company
                        "specificity": cs,
                    })
                if entries:
                    out[str(k)] = entries
            if out:
                logger.info("[CENTROID] Universal keywords chargés pour %d intents", len(out))
            return out
        except Exception:
            return {}

    def _merge_keywords_maps(self, a: Dict[str, List[dict]], b: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
        """Fusionne deux mappings intent->entries en dédupliquant par mot (préserve l'ordre de a puis b)."""
        if not a and not b:
            return {}
        merged: Dict[str, List[dict]] = {}
        keys = set(a.keys()) | set(b.keys())
        for k in keys:
            arr: List[dict] = []
            seen = set()
            for src in (a.get(k) or []):
                w = (src.get("word") or "").strip().lower()
                if not w or w in seen:
                    continue
                seen.add(w)
                arr.append(src)
            for src in (b.get(k) or []):
                w = (src.get("word") or "").strip().lower()
                if not w or w in seen:
                    continue
                seen.add(w)
                arr.append(src)
            if arr:
                merged[str(k)] = arr
        return merged

    def _load_intent_keywords_shadow(self) -> Dict[str, List[dict]]:
        """Charge un mapping intent_id -> liste de mots-clés (Shadow) si disponible.

        Fichier attendu (override via env INTENT_KEYWORDS_IN): intents/keywords/intent_keywords.json
        Format: {"9": {"keywords": [{"word": "changer", ...}, ...]}, ...}
        """
        try:
            p = Path(os.getenv("INTENT_KEYWORDS_IN", "intents/keywords/intent_keywords.json"))
            if not p.exists():
                return {}
            with p.open("r", encoding="utf-8") as f:
                raw = json.load(f) or {}
            clean: Dict[str, List[dict]] = {}
            for k, v in raw.items():
                if not isinstance(v, dict):
                    continue
                kw_list = v.get("keywords") or []
                if not isinstance(kw_list, list):
                    continue
                entries: List[dict] = []
                for item in kw_list:
                    if not isinstance(item, dict):
                        continue
                    word = item.get("word")
                    if not isinstance(word, str) or not word.strip():
                        continue
                    try:
                        freq = int(item.get("frequency", 0) or 0)
                    except Exception:
                        freq = 0
                    try:
                        spec = float(item.get("specificity", 1.0) or 1.0)
                    except Exception:
                        spec = 1.0
                    entries.append(
                        {
                            "word": word.strip().lower(),
                            "frequency": freq,
                            "specificity": spec,
                        }
                    )
                if entries:
                    clean[str(k)] = entries
            if clean:
                logger.info("[CENTROID] Intent keywords shadow chargés pour %d intents", len(clean))
            return clean
        except Exception:
            return {}

    # ---------------------------------------------------------------------
    # Routing
    # ---------------------------------------------------------------------
    def route(self, message: str, top_k: int = 3, apply_boost: bool = True) -> dict:
        """Route un message vers l'intent le plus proche (cosine centroid, boost interrogatif, top_k, ambiguïté)."""
        text = (message or "").strip()
        if not text:
            default_id = 3 if 3 in self.centroids else next(iter(self.centroids.keys()))
            c = self.centroids[default_id]
            return {
                "intent_id": c.intent_id,
                "intent_name": c.intent_name,
                "prompt_target": c.prompt_target,
                "score": c.score,
                "confidence": 0.0,
                "method": "centroid_cosine",
                "boost_applied": False,
                "top_k_intents": [],
                "is_ambiguous": False,
                "confidence_delta": 1.0
            }

        msg_emb = self.model.encode(
            [text], show_progress_bar=False, convert_to_numpy=True
        )[0]
        norm = float(np.linalg.norm(msg_emb))
        if norm > 0:
            msg_emb = msg_emb / norm

        # 1. Similarités brutes
        similarities = {}
        for intent_id, centroid in self.centroids.items():
            similarities[intent_id] = float(np.dot(msg_emb, centroid.centroid))

        # 2. Boost interrogatif
        boosted_similarities = similarities.copy()
        has_interrogative = self._has_interrogative(text)
        boost_applied = False
        if apply_boost and has_interrogative:
            for intent_id, centroid_data in self.centroids.items():
                if centroid_data.boost_interrogatif:
                    boosted_similarities[intent_id] = min(
                        similarities[intent_id] * 1.2, 1.0
                    )
                    boost_applied = True

        # 2.b Boost lexical spécialisé (mots-clés livraison vs suivi)
        boosted_similarities = self._apply_keyword_boosts(text, boosted_similarities)

        # 3. Top-K et ambiguïté
        sorted_intents = sorted(
            boosted_similarities.items(), key=lambda x: x[1], reverse=True
        )
        top_k_intents = []
        for intent_id, conf in sorted_intents[:top_k]:
            centroid = self.centroids[intent_id]
            top_k_intents.append({
                'intent_id': intent_id,
                'intent_name': centroid.intent_name,
                'confidence': conf,
                'prompt_target': centroid.prompt_target
            })
        is_ambiguous = False
        delta = 1.0
        if len(top_k_intents) >= 2:
            delta = top_k_intents[0]['confidence'] - top_k_intents[1]['confidence']
            if delta < 0.10:
                is_ambiguous = True

        # 3.b Règle de tie-break dédiée 9 vs 11 si très proches
        # Calcule hits livraison/suivi pour arbitrer
        ship_hits, track_hits = self._ship_track_hits(text)
        if len(top_k_intents) >= 2:
            a, b = top_k_intents[0]['intent_id'], top_k_intents[1]['intent_id']
            pair = {a, b}
            if pair == {9, 11}:
                # Si les signaux sont clairs et l'écart est faible, privilégier l'intent correspondant
                if delta < 0.25:
                    if ship_hits > track_hits:
                        best_candidate = 9
                    elif track_hits > ship_hits:
                        best_candidate = 11
                    else:
                        best_candidate = top_k_intents[0]['intent_id']
                    # Forcer le meilleur si différent
                    if best_candidate != top_k_intents[0]['intent_id']:
                        # Réordonner best en tête sans modifier les confidences
                        sorted_intents = sorted(
                            boosted_similarities.items(), key=lambda x: (
                                1 if x[0] == best_candidate else 0, x[1]
                            ), reverse=True
                        )
                        top_k_intents = []
                        for intent_id, conf in sorted_intents[:top_k]:
                            centroid = self.centroids[intent_id]
                            top_k_intents.append({
                                'intent_id': intent_id,
                                'intent_name': centroid.intent_name,
                                'confidence': conf,
                                'prompt_target': centroid.prompt_target
                            })

        # 4. Best intent (après boost et tie-break éventuel)
        best_intent_id = top_k_intents[0]['intent_id'] if top_k_intents else sorted_intents[0][0]
        best = self.centroids[best_intent_id]

        return {
            "intent_id": best.intent_id,
            "intent_name": best.intent_name,
            "prompt_target": best.prompt_target,
            "score": best.score,
            "similarity": similarities[best_intent_id],
            "confidence": boosted_similarities[best_intent_id],
            "method": "centroid_cosine",
            "boost_applied": boost_applied,
            "top_k_intents": top_k_intents,
            "is_ambiguous": is_ambiguous,
            "confidence_delta": delta
        }

    def _has_interrogative(self, message: str) -> bool:
        msg_lower = message.lower()
        return any(word in msg_lower for word in self.interrogative_words)

    def _apply_keyword_boosts(self, message: str, similarities: Dict[int, float]) -> Dict[int, float]:
        """Applique des boosts/déboosts légers basés sur des mots-clés afin de
        mieux séparer les intents 9 (livraison: frais/délais/adresse) et 11 (suivi: tracking/statut).
        Effet borné: ±20% au maximum.
        """
        raw = (message or "")
        if not raw.strip():
            return similarities

        sims = similarities.copy()
        msg = self._normalize_text(raw)

        # Détection enrichie (normalisée sans accents)
        # Signaux de "livraison" (frais / zones / adresse)
        ship_triggers = [
            "livraison", "livrer", "livraisons", "livr", "liv ", "expedi", "expedition",
            "frais", "cout", "couts", "adresse", "address", "express", "standard",
            "zone", "quartier", "delai", "delais", "prix liv", "prix de liv",
            "point relais", "relais", "aujourd", "aujourd hui", "aujourdhui", "demain",
            "heure", "adresse exacte", "lieu de livraison", "point de repere", "presentement je suis",
            "cocody", "koumassi", "abobo", "yopougon", "marcory", "songon",
        ]
        # Signaux de "suivi de commande" (tracking / statut)
        track_triggers = [
            "suivi", "suivre", "tracking", "track", "statut", "status", "en route",
            "en cours", "numero", "num de suivi", "no de suivi", "n de suivi",
            "ou en est", "ou est", "il est ou",
            "commande est ou", "ma commande est ou", "ou ma commande",
            "expedie", "arrive", "arriver", "arrivee", "arrivé",
            "colis parti", "commande est partie",
            "livreur", "fait signe", "pas fait signe", "toujours pas", "toujours pas recu",
            "recu", "reçu", "pas encore recu",
            "livre", "livré", "livree", "il est passe", "il est passé",
            "recupere", "recupéré", "recuperer", "nouvelle", "nouvelles", "j attends", "j'attends",
            "confirmation", "reception", "suivre ma commande",
        ]
        ship_hits = sum(1 for t in ship_triggers if t in msg)
        track_hits = sum(1 for t in track_triggers if t in msg)

        # IDs des intents selon le corpus
        id_livraison = 9 if 9 in self.centroids else None
        id_suivi = 11 if 11 in self.centroids else None
        id_commande = 8 if 8 in self.centroids else None
        id_reclamation = 12 if 12 in self.centroids else None
        id_info = 2 if 2 in self.centroids else None

        def _apply(id_: int | None, factor: float) -> None:
            if id_ is None:
                return
            sims[id_] = max(min(sims[id_] * factor, 1.0), -1.0)

        # Boost proportionnel et borné (plus fort) sur les intents 9 (livraison) et 11 (suivi)
        if ship_hits > 0 and id_livraison is not None:
            _apply(id_livraison, 1.0 + min(0.10 * ship_hits, 0.40))
        if track_hits > 0 and id_suivi is not None:
            _apply(id_suivi, 1.0 + min(0.10 * track_hits, 0.40))

        # Déboosts croisés plus marqués si un seul type de signal est présent
        if track_hits > 0 and ship_hits == 0 and id_livraison is not None:
            _apply(id_livraison, 0.75)
        if ship_hits > 0 and track_hits == 0 and id_suivi is not None:
            _apply(id_suivi, 0.75)

        # Contexte plainte / réclamation explicite (plutôt intent 12 que 8/11)
        complaint_triggers = [
            "reclamation", "reclamer", "plainte",
            "probleme", "problemes",
            "pas satisfait", "pas contente", "pas content",
            "non conforme", "defaut", "defauts", "defectueux",
            "abime", "abimer", "casse", "cassee", "cassees",
        ]
        has_complaint = any(t in msg for t in complaint_triggers)

        # Contexte clairement "suivi" : on réduit l'intent 8 (commande) qui aspire trop
        if track_hits > 0 and id_commande is not None:
            _apply(id_commande, 0.8)

        # Tracking sans vocabulaire de plainte => éviter de basculer vers 12
        if track_hits > 0 and not has_complaint and id_reclamation is not None:
            _apply(id_reclamation, 0.85)

        # Vocabulaire de plainte clair => fort boost intent 12 et déboost intent 8
        if has_complaint and id_reclamation is not None:
            _apply(id_reclamation, 1.4)
            if id_commande is not None:
                _apply(id_commande, 0.7)

        # Si vocabulaire livraison présent, réduire légèrement l'intent 2 (info générale)
        if ship_hits > 0 and id_info is not None:
            _apply(id_info, 0.9)

        # 2.c Boost lexical basé sur les mots-clés Shadow extraits (Botlive)
        botlive_kw = []
        try:
            botlive_kw = extract_botlive_keywords(raw)
        except Exception:
            botlive_kw = []
        if botlive_kw and self.intent_keywords_shadow:
            kw_set = set(botlive_kw)
            for intent_key, items in self.intent_keywords_shadow.items():
                try:
                    intent_id = int(intent_key)
                except (TypeError, ValueError):
                    continue
                if intent_id not in sims:
                    continue
                score_acc = 0.0
                for item in items:
                    w = item.get("word")
                    if not w or w not in kw_set:
                        continue
                    spec = float(item.get("specificity", 1.0) or 1.0)
                    freq = float(item.get("frequency", 0) or 0)
                    score_acc += spec * 0.5 + min(freq, 50.0) / 50.0
                if score_acc > 0.0:
                    # Facteur borné à +25% pour éviter la dérive
                    factor = 1.0 + min(score_acc * 0.02, 0.25)
                    sims[intent_id] = min(sims[intent_id] * factor, 1.0)

        # Boost générique par mots-clés d'intent (faible, borné à +15%)
        for intent_id, centroid in self.centroids.items():
            if not centroid.keywords:
                continue
            kw_hits = 0
            for kw in centroid.keywords:
                if not isinstance(kw, str):
                    continue
                if self._normalize_text(kw) in msg:
                    kw_hits += 1
            if kw_hits > 0:
                sims[intent_id] = min(sims[intent_id] * (1.0 + min(0.03 * kw_hits, 0.15)), 1.0)

        return sims

    def _normalize_text(self, text: str) -> str:
        """Lowercase + suppression des accents pour des correspondances robustes."""
        tx = text.lower()
        tx = unicodedata.normalize("NFD", tx)
        tx = "".join(ch for ch in tx if unicodedata.category(ch) != "Mn")
        return tx

    def _ship_track_hits(self, message: str) -> tuple[int, int]:
        msg = self._normalize_text(message or "")
        if not msg:
            return 0, 0
        ship_triggers = [
            "livraison", "livrer", "livraisons", "livr", "liv ", "expedi", "expedition",
            "frais", "cout", "couts", "adresse", "address", "express", "standard",
            "zone", "quartier", "delai", "delais", "prix liv", "prix de liv",
            "point relais", "relais", "aujourd", "aujourd hui", "aujourdhui", "demain",
            "heure", "adresse exacte", "lieu de livraison", "point de repere", "presentement je suis",
            "cocody", "koumassi", "abobo", "yopougon", "marcory", "songon",
        ]
        track_triggers = [
            "suivi", "suivre", "tracking", "track", "statut", "status", "en route",
            "en cours", "numero", "num de suivi", "no de suivi", "n de suivi",
            "ou en est", "ou est", "il est ou",
            "commande est ou", "ma commande est ou", "ou ma commande",
            "expedie", "arrive", "arriver", "arrivee", "arrivé",
            "colis parti", "commande est partie",
            "livreur", "fait signe", "pas fait signe", "toujours pas", "toujours pas recu",
            "recu", "reçu", "pas encore recu",
            "livre", "livré", "livree", "il est passe", "il est passé",
            "recupere", "recupéré", "recuperer", "nouvelle", "nouvelles", "j attends", "j'attends",
            "confirmation", "reception", "suivre ma commande",
        ]
        ship_hits = sum(1 for t in ship_triggers if t in msg)
        track_hits = sum(1 for t in track_triggers if t in msg)
        return ship_hits, track_hits


if __name__ == "__main__":  # Petit test manuel
    logging.basicConfig(level=logging.INFO)
    router = CentroidRouter()
    examples = [
        "Bjr vs ete ou ?",
        "C'est combien ?",
        "Je veux commander",
        "Ma commande est où ?",
        "Y'a problème dans ma cmd",
    ]
    for msg in examples:
        print("\nMessage:", msg)
        print(router.route(msg))

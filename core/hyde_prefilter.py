from __future__ import annotations

import logging
import re
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)


class HydePrefilter:
    """Détecte si un message nécessite HYDE pré-routage (reformulation avant embeddings).

    Interface simple compatible avec le routeur Botlive actuel:
    - message: texte brut utilisateur
    - context: dict optionnel avec au moins "conversation_history"
    """

    CLEAR_KEYWORDS = [
        "prix", "combien", "coût", "cout", "tarif",
        "livraison", "livrer", "zone", "où", "ou",
        "commander", "acheter", "payer", "paiement",
        "produit", "couches", "photo",
        "modifier", "annuler", "changer", "suivi",
    ]

    VAGUE_PATTERNS = [
        r"\b(ok|oui|non|d'?accord|ça marche|ca marche|compris)\b",
        r"\b(je veux ça|je prends ça|c'?est bon)\b",
        r"\b(hmm|euh|bon|voilà|voila)\b",
    ]

    ACTION_VERBS = [
        "veux", "voudrais", "souhaite", "cherche",
        "commander", "acheter", "livrer", "payer",
        "modifier", "annuler",
    ]

    def should_use_hyde(self, message: str, context: Dict[str, Any] | None = None) -> Tuple[bool, str]:
        """Retourne (should_use, reason) pour HYDE pré-routage."""
        ctx = context or {}
        msg = (message or "").strip()
        msg_lower = msg.lower()
        word_count = len(msg_lower.split())

        # 1. Très court (≤2 mots) sans keyword explicite
        if word_count <= 2:
            has_keyword = any(kw in msg_lower for kw in self.CLEAR_KEYWORDS)
            if not has_keyword:
                return True, f"VERY_SHORT_{word_count}_WORDS_NO_KW"

        # 2. Court (3-4 mots) sans keyword ni réponse claire
        if word_count <= 4:
            has_keyword = any(kw in msg_lower for kw in self.CLEAR_KEYWORDS)
            is_response_to_bot = self._is_clear_response(msg_lower, ctx)
            if not has_keyword and not is_response_to_bot:
                return True, f"SHORT_{word_count}_WORDS_NO_KW"

        # 3. Motifs vagues explicites
        for pattern in self.VAGUE_PATTERNS:
            if re.search(pattern, msg_lower):
                return True, "VAGUE_PATTERN"

        # 4. Long (>=10 mots) mais sans verbe d'action ni keyword métier
        if word_count >= 10:
            has_verb = any(verb in msg_lower for verb in self.ACTION_VERBS)
            has_keyword = any(kw in msg_lower for kw in self.CLEAR_KEYWORDS)
            if not has_verb and not has_keyword:
                return True, "LONG_BUT_UNCLEAR"

        # Message jugé clair pour embeddings
        return False, "CLEAR_MESSAGE"

    # ---------------------------------------------------------------------
    # Helpers internes
    # ---------------------------------------------------------------------
    def _is_clear_response(self, msg_lower: str, context: Dict[str, Any]) -> bool:
        """Est-ce une réponse suffisamment claire à la dernière question bot ?"""
        history = str(context.get("conversation_history") or "")
        last_q = self._extract_last_bot_question(history).lower()
        if not last_q:
            return False

        # Question bot axée photo / image
        if any(k in last_q for k in ["photo", "image", "capture"]):
            return ("photo" in msg_lower) or ("image" in msg_lower)

        # Question bot axée zone / quartier
        if any(k in last_q for k in ["zone", "quartier", "commune", "livr"]):
            locations = [
                "cocody", "yopougon", "abobo", "plateau", "treichville",
                "marcory", "koumassi", "angré", "angre", "riviera",
            ]
            return any(loc in msg_lower for loc in locations)

        # Question bot axée paiement
        if any(k in last_q for k in ["paiement", "payer", "wave", "orange", "mtn", "moov"]):
            return any(k in msg_lower for k in ["payé", "paye", "wave", "orange", "mtn", "moov", "reçu", "recu"])

        return False

    def _extract_last_bot_question(self, history_text: str) -> str:
        """Extrait la dernière ligne bot de l'historique (Jessica/Assistant/Bot)."""
        lines = (history_text or "").strip().split("\n")
        for line in reversed(lines):
            st = line.strip()
            if st.startswith(("Jessica:", "Assistant:", "Bot:")):
                try:
                    return st.split(":", 1)[1].strip()[:100]
                except Exception:
                    return st[:100]
        return ""

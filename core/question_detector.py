import re
from typing import Dict, Tuple


class QuestionDetector:
    QUESTION_WORDS = [
        "quel",
        "quels",
        "quelle",
        "quelles",
        "combien",
        "comment",
        "pourquoi",
        "quand",
        "où",
        "ou",
        "est-ce",
        "est ce",
        "avez-vous",
        "avez vous",
        "êtes-vous",
        "etes vous",
        "peux-tu",
        "peux tu",
        "puis-je",
        "puis je",
        "y'a-t-il",
        "y a t il",
    ]

    INVERSION_PATTERNS = [
        r"\b(avez|êtes|etes|pouvez|voulez|faites|prenez|livrez|acceptez)-vous\b",
        r"\b(as|es|peux|veux|fais|prends)-tu\b",
        r"\b(puis|vais|fais|prends|veux)-je\b",
    ]

    PRIX_KEYWORDS = [
        "combien",
        "prix",
        "coute",
        "coûte",
        "tarif",
        "à combien",
        "a combien",
        "c'est combien",
        "quel est le prix",
        "ça fait combien",
        "ca fait combien",
        "montant",
    ]

    STOCK_KEYWORDS = [
        "disponible",
        "dispo",
        "en stock",
        "stock",
        "reste",
        "avez-vous",
        "avez vous",
        "vous avez",
        "y'a",
        "y a",
        "il y a",
        "encore",
        "toujours",
    ]

    CARACTERISTIQUES_KEYWORDS = [
        "taille",
        "couleur",
        "marque",
        "âge",
        "age",
        "poids",
        "composition",
        "ingrédients",
        "ingredients",
        "caractéristiques",
        "caracteristiques",
        "c'est quoi",
        "difference",
        "différence",
        "quelle taille",
        "quel modèle",
        "quel modele",
        "quelle version",
        "quel type",
    ]

    def __init__(self) -> None:
        self._inversion_regex = re.compile("|".join(self.INVERSION_PATTERNS), re.IGNORECASE)

    def is_question(self, message: str) -> Tuple[bool, str]:
        if not message:
            return False, "empty_message"

        msg = message.lower().strip()

        if msg.endswith("?"):
            return True, "punctuation"

        for qword in self.QUESTION_WORDS:
            if msg.startswith(qword):
                return True, f"question_word:{qword}"

        if self._inversion_regex.search(msg):
            return True, "inversion"

        if msg.startswith("vous avez") or msg.startswith("tu as"):
            return True, "implicit_have"

        if "disponible" in msg or "dispo" in msg:
            return True, "implicit_availability"

        return False, "no_question_marker"

    def is_prix_question(self, message: str) -> bool:
        if not message:
            return False
        msg = message.lower()
        return any(kw in msg for kw in self.PRIX_KEYWORDS)

    def is_stock_question(self, message: str) -> bool:
        if not message:
            return False
        msg = message.lower()
        return any(kw in msg for kw in self.STOCK_KEYWORDS)

    def is_caracteristiques_question(self, message: str) -> bool:
        if not message:
            return False
        msg = message.lower()
        return any(kw in msg for kw in self.CARACTERISTIQUES_KEYWORDS)

    def is_info_technique_question(self, message: str) -> bool:
        return (
            self.is_prix_question(message)
            or self.is_stock_question(message)
            or self.is_caracteristiques_question(message)
        )

    def analyze(self, message: str) -> Dict[str, object]:
        is_q, reason = self.is_question(message)
        is_prix = self.is_prix_question(message)
        is_stock = self.is_stock_question(message)
        is_carac = self.is_caracteristiques_question(message)
        return {
            "is_question": is_q,
            "question_reason": reason,
            "is_prix": is_prix,
            "is_stock": is_stock,
            "is_caracteristiques": is_carac,
            "is_info_technique": bool(is_prix or is_stock or is_carac),
        }

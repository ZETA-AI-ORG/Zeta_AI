import re
from typing import Any, Dict


class GreetingAnalyzer:
    """Analyse les salutations et décide si on route vers SALUT ou vers le reste du message.

    Retour de analyze(text):
        {
            "has_greeting": bool,
            "greeting_text": str,
            "rest_text": str,
            "is_pure_small_talk": bool,
            "has_real_question": bool,
            "confidence": float,
            "route_to": str,  # "SALUT", "EMBED_REST", "EMBED_FULL"
        }
    """

    GREETING_PATTERNS = [
        r"^(bonjour|bonsoir|salut|hey|coucou|yo|wesh|bjr|slt|bnsr)",
        r"^(bonjour|bonsoir)\s+(monsieur|madame|mme|mr|m\.|mlle)",
        r"^(on\s+dit\s+quoi|c'est\s+comment|ça\s+dit\s+quoi)",
        r"^(merci\b|merci beaucoup|grand merci)",
    ]

    SMALL_TALK_INDICATORS = [
        r"j'espère\s+(?:que\s+)?(?:vous|tu)",
        r"comment\s+(?:allez-vous|ça\s+va|tu\s+vas)",
        r"désolé\s+(?:de|du|pour)",
        r"pardon\s+(?:de|du|pour)",
        r"excusez?-moi",
        r"famille\s+va\s+bien",
        r"tout\s+va\s+bien",
        r"vous\s+allez\s+bien",
        r"tu\s+vas\s+bien",
        r"bien\s+ou\s+bien",
        r"merci\b",
    ]

    REAL_QUESTION_INDICATORS = [
        # Interrogatifs forts / ponctuation
        r"\b(où|ou|quand|combien|quel(?:le)?s?|pourquoi)\b",
        r"\?",
        # Verbes d'action / intention
        r"\b(veux|voulais|voudrais|souhaite|aimerais|peux|puis|peut)\b",
        r"\b(commander|acheter|payer|livrer|recevoir|modifier|changer|annuler)\b",
        # Keywords métier
        r"\b(prix|coût|cout|tarif|commande|colis|livraison|paiement|stock|disponible)\b",
        r"\b(numéro|numero|référence|reference|code|tracking|suivi)\b",
        # Problèmes explicites
        r"\b(pas|jamais|aucun|problème|probleme|erreur|retard)\b",
        r"\b(reçu|recu|reçois|recois|arrivé|arrive)\s+(pas|jamais)",
    ]

    def __init__(self) -> None:
        self.greeting_regex = re.compile("|".join(self.GREETING_PATTERNS), re.IGNORECASE)
        self.small_talk_regex = re.compile("|".join(self.SMALL_TALK_INDICATORS), re.IGNORECASE)
        self.real_question_regex = re.compile("|".join(self.REAL_QUESTION_INDICATORS), re.IGNORECASE)

    def analyze(self, text: str) -> Dict[str, Any]:
        text_clean = (text or "").strip()
        text_lower = text_clean.lower()

        if not text_clean:
            return {
                "has_greeting": False,
                "greeting_text": "",
                "rest_text": "",
                "is_pure_small_talk": False,
                "has_real_question": False,
                "confidence": 0.0,
                "route_to": "EMBED_FULL",
            }

        # 1) Détection salutation en début de message
        greeting_match = self.greeting_regex.match(text_lower)
        if not greeting_match:
            # Pas de salutation → routage complet sur embeddings
            return {
                "has_greeting": False,
                "greeting_text": "",
                "rest_text": text_clean,
                "is_pure_small_talk": False,
                "has_real_question": True,
                "confidence": 1.0,
                "route_to": "EMBED_FULL",
            }

        greeting_end = greeting_match.end()
        greeting_text = text_clean[:greeting_end]
        rest_text = text_clean[greeting_end:].strip()
        rest_text = rest_text.lstrip(",.!;:-")

        # Cas remerciement / politesse pure (ex: "Merci beaucoup pour votre aide")
        if "merci" in greeting_text.lower():
            if not self.real_question_regex.search(text_lower):
                return {
                    "has_greeting": True,
                    "greeting_text": greeting_text,
                    "rest_text": rest_text,
                    "is_pure_small_talk": True,
                    "has_real_question": False,
                    "confidence": 0.92,
                    "route_to": "SALUT",
                }

        # 2) Cas salutation seule ou quasi seule
        if len(rest_text) < 5:
            return {
                "has_greeting": True,
                "greeting_text": greeting_text,
                "rest_text": rest_text,
                "is_pure_small_talk": True,
                "has_real_question": False,
                "confidence": 0.95,
                "route_to": "SALUT",
            }

        # 3) Analyse de la suite
        has_real_question = bool(self.real_question_regex.search(rest_text))
        has_small_talk = bool(self.small_talk_regex.search(rest_text))

        if has_real_question:
            # Vraie demande après la salutation → router sur la suite
            return {
                "has_greeting": True,
                "greeting_text": greeting_text,
                "rest_text": rest_text,
                "is_pure_small_talk": False,
                "has_real_question": True,
                "confidence": 0.85,
                "route_to": "EMBED_REST",
            }

        if has_small_talk and not has_real_question:
            # Small talk pur (politesse étendue)
            return {
                "has_greeting": True,
                "greeting_text": greeting_text,
                "rest_text": rest_text,
                "is_pure_small_talk": True,
                "has_real_question": False,
                "confidence": 0.9,
                "route_to": "SALUT",
            }

        # 4) Cas ambigu: salutation + texte flou → on route quand même sur la suite
        return {
            "has_greeting": True,
            "greeting_text": greeting_text,
            "rest_text": rest_text,
            "is_pure_small_talk": False,
            "has_real_question": False,
            "confidence": 0.65,
            "route_to": "EMBED_REST",
        }

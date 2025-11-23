import json
import logging
from typing import Any, Dict, Optional

from core.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class InterventionGuardian:
    def __init__(self, llm_client: Optional[Any] = None) -> None:
        if llm_client is None:
            try:
                self.llm = get_llm_client()
            except Exception:
                logger.warning("[INTERVENTION_GUARDIAN] LLM client non disponible, mode no-op")
                self.llm = None
        else:
            self.llm = llm_client

    async def analyze(
        self,
        conversation_history: str,
        user_message: str,
        bot_response: str,
        order_state: Dict[str, Any],
        next_step: str,
        hard_signals: Dict[str, Any],
    ) -> Dict[str, Any]:
        base_decision: Dict[str, Any] = {
            "requires_intervention": False,
            "priority": "normal",
            "category": "other",
            "confidence": 0.0,
            "reason": "",
            "suggested_handoff_message": "",
        }

        if not self.llm:
            return base_decision

        prompt = self._build_prompt(
            conversation_history=conversation_history or "",
            user_message=user_message or "",
            bot_response=bot_response or "",
            order_state=order_state or {},
            next_step=next_step or "",
            hard_signals=hard_signals or {},
        )

        try:
            raw = await self.llm.complete(
                prompt=prompt,
                temperature=0.2,
                max_tokens=600,
            )

            usage: Dict[str, Any] = {}
            if isinstance(raw, dict):
                response_text = (raw.get("response") or "").strip()
                usage = raw.get("usage") or {}
            else:
                response_text = str(raw).strip()

            try:
                decision = json.loads(response_text)
            except Exception as parse_err:
                logger.error("[INTERVENTION_GUARDIAN] Erreur parsing JSON LLM: %s", parse_err)
                merged = dict(base_decision)
                if usage:
                    merged["_llm_usage"] = usage
                return merged

            if not isinstance(decision, dict):
                merged = dict(base_decision)
                if usage:
                    merged["_llm_usage"] = usage
                return merged

            merged = dict(base_decision)
            merged.update(decision)

            merged["requires_intervention"] = bool(merged.get("requires_intervention", False))
            prio = str(merged.get("priority") or "normal").lower()
            if prio not in {"low", "normal", "high", "critical"}:
                prio = "normal"
            merged["priority"] = prio

            cat = str(merged.get("category") or "other").lower()
            merged["category"] = cat

            try:
                merged["confidence"] = float(merged.get("confidence", 0.0))
            except Exception:
                merged["confidence"] = 0.0

            if usage:
                merged["_llm_usage"] = usage

            return merged
        except Exception as e:
            logger.error("[INTERVENTION_GUARDIAN] Erreur appel LLM: %s", e)
            return base_decision

    def _build_prompt(
        self,
        conversation_history: str,
        user_message: str,
        bot_response: str,
        order_state: Dict[str, Any],
        next_step: str,
        hard_signals: Dict[str, Any],
    ) -> str:
        order_state_json = json.dumps(order_state, ensure_ascii=False)
        hard_signals_json = json.dumps(hard_signals, ensure_ascii=False)

        history_snippet = conversation_history[-2000:] if conversation_history else ""

        return (
            "Tu es un 'Guardian d'intervention' pour un chatbot e-commerce de couches pour enfants.\n"
            "Le bot (Jessica) aide les clients à commander des couches en collectant 4 éléments : photo, paiement, zone, téléphone.\n"
            "Ton rôle est de décider si un humain doit intervenir dans la conversation.\n\n"
            "DONNÉES DISPONIBLES :\n"
            "- HISTORIQUE_DERNIERS_MESSAGES (client + bot) :\n" + history_snippet + "\n\n"
            "- DERNIER_MESSAGE_CLIENT :\n" + user_message + "\n\n"
            "- DERNIERE_REPONSE_BOT :\n" + bot_response + "\n\n"
            "- ETAT_COMMANDE_JSON :\n" + order_state_json + "\n\n"
            "- SIGNAUX_SYSTEME_JSON :\n" + hard_signals_json + "\n\n"
            "OBJECTIF :\n"
            "Décider si une intervention humaine est nécessaire en te basant sur :\n"
            "- le ton et la frustration potentielle du client,\n"
            "- le fait que la commande semble bloquée ou tourne en rond,\n"
            "- d'éventuels problèmes techniques implicites,\n"
            "- l'impression générale que le bot ne gère plus bien la situation.\n\n"
            "RÈGLES :\n"
            "- Si tout se passe bien, réponds requires_intervention=false.\n"
            "- Si le bot répète les mêmes choses sans progrès, si le client semble perdu, confus ou mécontent,\n"
            "  ou si la commande reste bloquée alors que plusieurs messages ont été échangés, tu peux recommander une intervention.\n"
            "- Utilise SIGNAUX_SYSTEME_JSON uniquement comme indices (ne les modifie pas).\n\n"
            "FORMAT DE RÉPONSE STRICT :\n"
            "Réponds UNIQUEMENT avec un JSON valide (sans texte autour) de la forme :\n"
            "{\n"
            "  \"requires_intervention\": true | false,\n"
            "  \"priority\": \"low\" | \"normal\" | \"high\" | \"critical\",\n"
            "  \"category\": \"customer_frustration\" | \"bot_confusion\" | \"sav_issue\" | \"technical_issue\" | \"payment_issue\" | \"vip_case\" | \"other\",\n"
            "  \"confidence\": 0.0-1.0,\n"
            "  \"reason\": \"explication courte en français\",\n"
            "  \"suggested_handoff_message\": \"résumé court pour l'agent humain\"\n"
            "}\n"
        )


_guardian_instance: Optional[InterventionGuardian] = None


def get_intervention_guardian(llm_client: Optional[Any] = None) -> InterventionGuardian:
    global _guardian_instance
    if _guardian_instance is None:
        _guardian_instance = InterventionGuardian(llm_client=llm_client)
    return _guardian_instance

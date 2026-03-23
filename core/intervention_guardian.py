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
                # Fallback: essayer d'extraire un bloc JSON au milieu d'un texte plus large
                snippet = (response_text or "").strip()
                start = snippet.find("{")
                end = snippet.rfind("}")
                if start != -1 and end != -1 and end > start:
                    candidate = snippet[start : end + 1]
                    try:
                        decision = json.loads(candidate)
                    except Exception as parse_err2:
                        logger.error(
                            "[INTERVENTION_GUARDIAN] Erreur parsing JSON LLM (fallback) : %s | snippet=%r",
                            parse_err2,
                            snippet[:400],
                        )
                        merged = dict(base_decision)
                        if usage:
                            merged["_llm_usage"] = usage
                        return merged
                else:
                    logger.error(
                        "[INTERVENTION_GUARDIAN] Erreur parsing JSON LLM: %s | snippet=%r",
                        parse_err,
                        snippet[:400],
                    )
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
            "Tu es un 'Guardian d'intervention' pour un chatbot e-commerce.\n"
            "Le bot aide les clients à commander via WhatsApp en collectant photo, paiement, zone, téléphone.\n"
            "Ton rôle : décider si un humain doit intervenir.\n\n"
            "DONNÉES :\n"
            "- HISTORIQUE :\n" + history_snippet + "\n\n"
            "- MESSAGE_CLIENT :\n" + user_message + "\n\n"
            "- REPONSE_BOT :\n" + bot_response + "\n\n"
            "- ETAT_COMMANDE :\n" + order_state_json + "\n\n"
            "- SIGNAUX :\n" + hard_signals_json + "\n\n"
            "CATÉGORIES (par priorité) :\n"
            "- system_error : backend crash, client sans réponse (critical)\n"
            "- explicit_handoff : client demande un humain (critical)\n"
            "- customer_frustration : colère, insultes, majuscules (high)\n"
            "- payment_issue : paiement ambigu/échoué, argent en jeu (high)\n"
            "- order_blocked : commande bloquée, pas de progrès (high)\n"
            "- bot_confusion : bot répète, incohérent, hors sujet (high)\n"
            "- sav_issue : réclamation, suivi, retour, remboursement (normal)\n"
            "- post_order_followup : message après commande complétée (normal)\n"
            "- technical_issue : OCR/média/API raté, fallback existe (low)\n"
            "- vip_or_sensitive_case : cas commercial sensible (low)\n\n"
            "RÈGLES :\n"
            "- Si tout va bien → requires_intervention=false.\n"
            "- Ne déclenche PAS pour : salutations, remerciements, questions simples bien gérées par le bot.\n"
            "- Utilise SIGNAUX comme indices, ne les modifie pas.\n\n"
            "FORMAT STRICT (JSON seul, rien d'autre) :\n"
            "{\n"
            "  \"requires_intervention\": true | false,\n"
            "  \"priority\": \"low\" | \"normal\" | \"high\" | \"critical\",\n"
            "  \"category\": \"system_error\" | \"explicit_handoff\" | \"customer_frustration\" | \"payment_issue\" | \"order_blocked\" | \"bot_confusion\" | \"sav_issue\" | \"post_order_followup\" | \"technical_issue\" | \"vip_or_sensitive_case\",\n"
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

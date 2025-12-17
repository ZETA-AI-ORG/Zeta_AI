from __future__ import annotations

import json
import hashlib
import logging
import os
import time
from typing import Any, Dict

from core.botlive_prompts_supabase import get_prompts_manager
from core.llm_client_groq import complete as groq_complete, GroqLLMError
from core.llm_client_openrouter import complete as openrouter_complete, OpenRouterLLMError

logger = logging.getLogger(__name__)


class HydeReformulator:
    """Reformule les messages ambigus AVANT le routage embeddings (HYDE pré-routage).

    Utilise Groq 70B avec un prompt dédié stocké dans prompt_botlive_groq_70b
    entre [[HYDE_PRE_ROUTING_START]] et [[HYDE_PRE_ROUTING_END]].
    """

    def __init__(self) -> None:
        self.prompts_manager = get_prompts_manager()
        self.last_meta: Dict[str, Any] | None = None

    async def reformulate(self, company_id: str, message: str, context: Dict[str, Any]) -> str:
        """Reformule un message ambigu.

        Args:
            company_id: Identifiant entreprise (pour récupérer le prompt HYDE)
            message: Message client brut
            context: Contexte léger (conversation_history, state_compact, ...)
        """
        if not self.prompts_manager:
            logger.warning("[HYDE_PRE] Prompts manager indisponible → skip HYDE")
            return message

        try:
            template = self.prompts_manager.get_hyde_pre_routing_prompt(company_id)
        except Exception as e:
            logger.error(f"[HYDE_PRE] Impossible de charger le prompt HYDE: {e}")
            return message

        template_str = str(template or "")
        template_sha1 = hashlib.sha1(template_str.encode("utf-8", errors="ignore")).hexdigest()
        template_len = len(template_str)

        context_summary = self._build_context_summary(context)

        # Le template peut contenir des JSON d'exemple avec des accolades, ce qui casse str.format.
        # On échappe toutes les accolades, puis on réactive uniquement nos placeholders.
        try:
            prompt = template.format(message=message, context_summary=context_summary)
        except KeyError:
            escaped = (template or "").replace("{", "{{").replace("}", "}}")
            escaped = escaped.replace("{{message}}", "{message}")
            escaped = escaped.replace("{{context_summary}}", "{context_summary}")
            prompt = escaped.format(message=message, context_summary=context_summary)

        try:
            use_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))
            if use_openrouter:
                model = os.getenv("OPENROUTER_HYDE_PRE_MODEL", "google/gemini-2.5-flash-lite")
                temperature = float(os.getenv("BOTLIVE_HYDE_PRE_TEMPERATURE", "0.0"))
                max_tokens = int(os.getenv("BOTLIVE_HYDE_PRE_MAX_TOKENS", "30"))
                top_p = float(os.getenv("BOTLIVE_HYDE_PRE_TOP_P", "1.0"))
                seed_raw = os.getenv("BOTLIVE_HYDE_PRE_SEED")
                seed = int(seed_raw) if seed_raw and seed_raw.strip().isdigit() else None
                response_format = {"type": "json_object"} if os.getenv("BOTLIVE_HYDE_PRE_RESPONSE_JSON", "false").strip().lower() in {"1", "true", "yes", "y", "on"} else None
                logger.info(f"[HYDE_PRE][OPENROUTER] model={model}")
                t0 = time.perf_counter()
                content, token_info = await openrouter_complete(
                    prompt,
                    model_name=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    seed=seed,
                    response_format=response_format,
                )
                latency_ms = int((time.perf_counter() - t0) * 1000.0)
                self.last_meta = {
                    "provider": "openrouter",
                    "model": model,
                    "prompt_sha1": template_sha1,
                    "prompt_len": template_len,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": top_p,
                    "seed": seed,
                    "response_format": response_format,
                    "latency_ms": latency_ms,
                    "token_info": token_info,
                }
            else:
                model = os.getenv("BOTLIVE_HYDE_PRE_MODEL", "llama-3.3-70b-versatile")
                temperature = float(os.getenv("BOTLIVE_HYDE_PRE_TEMPERATURE", "0.3"))
                max_tokens = int(os.getenv("BOTLIVE_HYDE_PRE_MAX_TOKENS", "30"))
                top_p = float(os.getenv("BOTLIVE_HYDE_PRE_TOP_P", "1.0"))
                logger.info(f"[HYDE_PRE][GROQ] model={model}")
                t0 = time.perf_counter()
                content, token_info = await groq_complete(
                    prompt,
                    model_name=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    frequency_penalty=0.0,
                )
                latency_ms = int((time.perf_counter() - t0) * 1000.0)
                self.last_meta = {
                    "provider": "groq",
                    "model": model,
                    "prompt_sha1": template_sha1,
                    "prompt_len": template_len,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": top_p,
                    "seed": None,
                    "response_format": None,
                    "latency_ms": latency_ms,
                    "token_info": token_info,
                }
        except OpenRouterLLMError as e:
            logger.error(f"[HYDE_PRE] Erreur OpenRouter: {e}")
            self.last_meta = {"provider": "openrouter", "error": str(e)}
            return message
        except GroqLLMError as e:
            logger.error(f"[HYDE_PRE] Erreur Groq: {e}")
            self.last_meta = {"provider": "groq", "error": str(e)}
            return message
        except Exception as e:
            logger.error(f"[HYDE_PRE] Erreur inconnue: {e}")
            self.last_meta = {"provider": "unknown", "error": str(e)}
            return message

        reformulated = (content or "").strip()

        # Si le prompt renvoie un JSON strict: {"hyde_question": "..."}
        if reformulated.startswith("{") and "hyde_question" in reformulated:
            try:
                payload = json.loads(reformulated)
                if isinstance(payload, dict) and isinstance(payload.get("hyde_question"), str):
                    reformulated = payload["hyde_question"].strip()
            except Exception:
                pass

        reformulated = reformulated.strip().strip('"').strip("'")
        if not reformulated:
            logger.warning("[HYDE_PRE] Réponse vide, utilisation du message original")
            return message

        words = reformulated.split()
        if len(words) > 15:
            logger.warning("[HYDE_PRE] Reformulation trop longue, troncature à 12 mots")
            reformulated = " ".join(words[:12])

        logger.info(f"[HYDE_PRE] '{message}' → '{reformulated}'")
        return reformulated

    # ------------------------------------------------------------------
    # Helpers internes
    # ------------------------------------------------------------------
    def _build_context_summary(self, context: Dict[str, Any]) -> str:
        """Construit un résumé ultra-court du contexte pour le prompt HYDE."""
        parts = []

        history = str(context.get("conversation_history") or "")
        last_bot = self._extract_last_bot_question(history)
        if last_bot:
            parts.append(f"Bot dit: {last_bot[:80]}")

        state = context.get("state_compact", {}) or {}
        collected = int(state.get("collected_count", 0) or 0)
        is_complete = bool(state.get("is_complete", False))
        if collected or is_complete:
            progress = f"{collected}/4"
            parts.append(f"Commande {progress}{' complète' if is_complete else ''}")

        # Historique: on ne garde qu'un seul dernier tour utilisateur si présent
        if history and not last_bot:
            last_line = history.strip().split("\n")[-1]
            parts.append(f"Dernier tour: {last_line[:80]}")

        return " | ".join(parts) if parts else "Nouvelle conversation"

    def _extract_last_bot_question(self, history_text: str) -> str:
        """Extrait la dernière réplique bot de l'historique (Jessica/Assistant/Bot)."""
        lines = (history_text or "").strip().split("\n")
        for line in reversed(lines):
            st = line.strip()
            if st.startswith(("Jessica:", "Assistant:", "Bot:")):
                try:
                    return st.split(":", 1)[1].strip()[:100]
                except Exception:
                    return st[:100]
        return ""

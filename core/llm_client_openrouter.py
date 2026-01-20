import os
import requests
import json
import re
from typing import Any, Dict, Optional


OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")


class OpenRouterLLMError(Exception):
    pass


def _normalize_openrouter_model(model: str) -> str:
    """Normalize common aliases to OpenRouter-valid model IDs.

    Some environments/configs use informal names (ex: google/gemini-1.5-flash)
    that OpenRouter may reject. We keep compatibility by mapping to a known
    OpenRouter model id when possible.
    """

    m = (model or "").strip()
    if not m:
        return m

    aliases = {
        # Common alias seen in configs (invalid on OpenRouter as-is)
        "google/gemini-1.5-flash": "google/gemini-flash-1.5",
        # Other frequent variants
        "google/gemini-1.5-flash-8b": "google/gemini-flash-1.5",
        "google/gemini-1.5-flash-8b-latest": "google/gemini-flash-1.5",
        # Migration: prefer Gemini 2.5 Flash over Flash-Lite
        "google/gemini-2.5-flash-lite": "google/gemini-2.5-flash",
    }

    return aliases.get(m, m)


def _candidate_models(model: str) -> list[str]:
    """Return a list of models to try (first is preferred)."""

    base = _normalize_openrouter_model(model)
    candidates = [base]

    # Fallback candidates for Gemini Flash naming inconsistencies
    if base != "google/gemini-flash-1.5" and ("gemini" in base and "flash" in base):
        candidates.append("google/gemini-flash-1.5")

    # Deduplicate while keeping order
    seen = set()
    out: list[str] = []
    for c in candidates:
        if c and c not in seen:
            out.append(c)
            seen.add(c)
    return out


async def complete(
    prompt: str = "",
    model_name: Optional[str] = None,
    max_tokens: int = 600,
    temperature: float = 0.7,
    top_p: float = 1.0,
    frequency_penalty: Optional[float] = None,
    seed: Optional[int] = None,
    response_format: Optional[Dict[str, Any]] = None,
    messages: Optional[list[dict]] = None,
) -> tuple[str, dict]:
    """Wrapper OpenAI-compatible pour OpenRouter chat completions."""

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise OpenRouterLLMError("OPENROUTER_API_KEY manquant dans l'environnement")

    default_model = os.getenv("LLM_MODEL", "google/gemini-2.5-flash")
    requested_model = (model_name or default_model).strip()
    models_to_try = _candidate_models(requested_model)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    http_referer = os.getenv("OPENROUTER_HTTP_REFERER")
    if http_referer:
        headers["HTTP-Referer"] = http_referer

    x_title = os.getenv("BOTLIVE_OPENROUTER_X_TITLE") or os.getenv("OPENROUTER_X_TITLE")
    if x_title:
        headers["X-Title"] = x_title

    prefer_provider = os.getenv("OPENROUTER_PREFER_PROVIDER")
    if prefer_provider:
        headers["OpenRouter-Prefer-Provider"] = prefer_provider

    debug_headers = (os.getenv("BOTLIVE_DEBUG_OPENROUTER_HEADERS", "false") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }
    if debug_headers:
        try:
            safe_headers = {
                "HTTP-Referer": headers.get("HTTP-Referer"),
                "X-Title": headers.get("X-Title"),
                "OpenRouter-Prefer-Provider": headers.get("OpenRouter-Prefer-Provider"),
            }
            print(f"[OPENROUTER][HEADERS] {safe_headers}")
        except Exception:
            pass

    if not models_to_try:
        raise OpenRouterLLMError("Model OpenRouter manquant")

    last_error: Optional[str] = None

    try:
        for model in models_to_try:
            # OpenRouter peut refuser une requête si les crédits restants ne permettent pas
            # le max_tokens demandé. Dans ce cas, l'erreur inclut souvent "can only afford N".
            # On retente une fois avec un max_tokens réduit pour éviter de faire échouer le flux.
            requested_max_tokens = int(max_tokens or 0)
            attempted_max_tokens: set[int] = set()

            while True:
                if requested_max_tokens in attempted_max_tokens:
                    break
                attempted_max_tokens.add(requested_max_tokens)

                body = {
                    "model": model,
                    "messages": messages if isinstance(messages, list) and messages else [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": requested_max_tokens,
                    "top_p": top_p,
                    "stream": False,
                }

                if frequency_penalty is not None:
                    try:
                        body["frequency_penalty"] = float(frequency_penalty)
                    except Exception:
                        pass

                if seed is not None:
                    body["seed"] = int(seed)
                if response_format is not None:
                    body["response_format"] = response_format

                resp = requests.post(OPENROUTER_API_URL, json=body, headers=headers, timeout=60)
                # Force UTF-8 to avoid mojibake in error bodies and JSON parsing.
                # (Some providers may omit/alter charset headers, and requests can guess latin-1.)
                try:
                    resp.encoding = "utf-8"
                except Exception:
                    pass
                if resp.status_code != 200:
                    err_txt_full = (resp.text or "")
                    err_txt = err_txt_full[:300]
                    last_error = f"OpenRouter API HTTP {resp.status_code}: {err_txt}"

                    # Retry next candidate if OpenRouter rejects model id
                    if resp.status_code == 400 and "not a valid model" in err_txt_full.lower():
                        break

                    # Retry once with reduced max_tokens if OpenRouter signals credits limit
                    if resp.status_code == 402:
                        m = re.search(r"can only afford\s+(\d+)", err_txt_full, flags=re.IGNORECASE)
                        if m:
                            try:
                                affordable = int(m.group(1))
                            except Exception:
                                affordable = 0
                            # Avoid retrying with too small values that would likely fail / be useless.
                            if affordable > 0 and affordable < requested_max_tokens and affordable >= 120:
                                requested_max_tokens = affordable
                                continue

                    raise OpenRouterLLMError(last_error)

            try:
                data = resp.json()
            except Exception:
                try:
                    data = json.loads((resp.content or b"").decode("utf-8", errors="replace"))
                except Exception as e:
                    raise OpenRouterLLMError(f"Réponse OpenRouter invalide (JSON decode): {e}")
            choices = data.get("choices") or []
            if not choices:
                raise OpenRouterLLMError("Réponse OpenRouter sans choices")

            message = choices[0].get("message") or {}
            content = str((message.get("content") or "")).strip()

            usage = data.get("usage") or {}

            total_cost = None
            try:
                total_cost = (
                    data.get("total_cost")
                    if data.get("total_cost") is not None
                    else data.get("cost")
                )
                if total_cost is None and isinstance(usage, dict):
                    total_cost = usage.get("total_cost")
            except Exception:
                total_cost = None

            token_info = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "model": model,
                "usage": usage,
            }
            if total_cost is not None:
                token_info["total_cost"] = total_cost

            return content, token_info

        raise OpenRouterLLMError(last_error or "OpenRouter: aucun modèle valide (tous refusés)")
    except requests.RequestException as e:
        raise OpenRouterLLMError(f"Erreur requête OpenRouter: {e}")

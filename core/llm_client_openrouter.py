import os
import httpx
import json
import re
import time
import logging
from pathlib import Path
from typing import Any, Dict, Optional


OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
logger = logging.getLogger(__name__)

# ── Global async HTTP client with connection pooling (reused across all LLM calls) ──
_openrouter_client: httpx.AsyncClient | None = None


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _openrouter_timeout() -> float:
    raw = os.getenv("OPENROUTER_TIMEOUT_SECONDS", "180")
    try:
        return max(30.0, float(raw))
    except Exception:
        return 180.0


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        return int(str(raw).strip()) if raw is not None else int(default)
    except Exception:
        return int(default)


def _parse_csv_env(name: str) -> list[str]:
    return [_normalize_provider_token(x) for x in str(os.getenv(name, "") or "").split(",") if _normalize_provider_token(x)]


def _normalize_provider_token(token: str) -> str:
    raw = str(token or "").strip().lower()
    if not raw:
        return ""
    compact = re.sub(r"[\s._]+", "-", raw)
    aliases = {
        "alibaba": "alibaba",
        "alibaba-cloud-int": "alibaba",
        "alibaba-cloud-international": "alibaba",
        "alibaba-cloud-intl": "alibaba",
        "alibaba-cloud-int.": "alibaba",
        "alibaba-cloud-int-": "alibaba",
        "alibaba-cloud-int.-": "alibaba",
        "google-vertex": "google-vertex",
        "google-vertex-us-east5": "google-vertex/us-east5",
        "google-vertex-us-central1": "google-vertex/us-central1",
        "google vertex": "google-vertex",
        "google-vertex-us": "google-vertex",
        "deepseek": "deepseek",
        "novitaai": "novitaai",
        "novita-ai": "novitaai",
        "deepinfra": "deepinfra",
    }
    return aliases.get(raw, aliases.get(compact, compact))


def _get_openrouter_client() -> httpx.AsyncClient:
    """Lazy-init a long-lived async HTTP client with keep-alive pooling."""
    global _openrouter_client
    if _openrouter_client is None or _openrouter_client.is_closed:
        timeout_seconds = _openrouter_timeout()
        _openrouter_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds, connect=10.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            http2=False,
        )
    return _openrouter_client


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
        # V2.0 — Anciens placeholders internes → slugs officiels
        "google/gemma-2-27b-it": "google/gemma-4-26b-a4b-it",
        "google/gemma-3-27b-it": "google/gemma-4-31b-it",
        "google/gemini-2.5-flash": "google/gemini-3.1-flash-lite-preview",
        "google/gemini-2.5-flash-lite": "google/gemini-3.1-flash-lite-preview",
        # Cas legacy tardifs (anciens noms Gemini 1.5)
        "google/gemini-1.5-flash": "google/gemini-3.1-flash-lite-preview",
        "google/gemini-1.5-flash-8b": "google/gemini-3.1-flash-lite-preview",
        "google/gemini-1.5-flash-8b-latest": "google/gemini-3.1-flash-lite-preview",
    }

    return aliases.get(m, m)


def _candidate_models(model: str) -> list[str]:
    """Return a list of models to try (first is preferred).

    V2.0 : aucun fallback cross-famille. On garde uniquement des variantes
    autorisées (Gemma/Gemini) pour éviter qu'un 400 OpenRouter route vers autre chose.
    """

    base = _normalize_openrouter_model(model)
    candidates = [base]

    # Deduplicate while keeping order
    seen = set()
    out: list[str] = []
    for c in candidates:
        if c and c not in seen:
            out.append(c)
            seen.add(c)
    return out


def _model_base_slug(model: str) -> str:
    return str(model or "").strip().split(":", 1)[0].lower()


def _model_runtime_registry(model: str) -> Dict[str, Any]:
    base_model = _model_base_slug(model)
    hard_cap = max(128, _env_int("OPENROUTER_MAX_TOKENS_HARD_CAP", 1200))

    registry = [
        {
            "match_prefix": "qwen/qwen3.5-flash-02-23",
            "provider_only": _parse_csv_env("OPENROUTER_QWEN_PROVIDER_ONLY") or ["alibaba"],
            "use_nitro": _env_flag("OPENROUTER_QWEN_USE_NITRO", False),
            "temperature": float(os.getenv("OPENROUTER_QWEN_TEMPERATURE", "0.2")),
            "top_p": float(os.getenv("OPENROUTER_QWEN_TOP_P", "0.8")),
            "frequency_penalty": float(os.getenv("OPENROUTER_QWEN_FREQUENCY_PENALTY", "0.1")),
            "presence_penalty": float(os.getenv("OPENROUTER_QWEN_PRESENCE_PENALTY", "0.05")),
            "max_tokens_cap": max(128, _env_int("OPENROUTER_QWEN_MAX_TOKENS", 800)),
            "prompt_cache_supported": False,
            "prompt_cache_mode": "unsupported",
        },
        {
            "match_prefix": "deepseek/deepseek",
            "provider_only": _parse_csv_env("OPENROUTER_DEEPSEEK_PROVIDER_ONLY") or ["deepseek", "novitaai"],
            "provider_ignore": _parse_csv_env("OPENROUTER_DEEPSEEK_PROVIDER_IGNORE") or ["deepinfra"],
            "use_nitro": _env_flag("OPENROUTER_DEEPSEEK_USE_NITRO", False),
            "temperature": float(os.getenv("OPENROUTER_DEEPSEEK_TEMPERATURE", "0.35")),
            "top_p": float(os.getenv("OPENROUTER_DEEPSEEK_TOP_P", "0.85")),
            "frequency_penalty": float(os.getenv("OPENROUTER_DEEPSEEK_FREQUENCY_PENALTY", "0.1")),
            "presence_penalty": float(os.getenv("OPENROUTER_DEEPSEEK_PRESENCE_PENALTY", "0.05")),
            "max_tokens_cap": max(128, _env_int("OPENROUTER_DEEPSEEK_MAX_TOKENS", hard_cap)),
            "prompt_cache_supported": True,
            "prompt_cache_mode": "implicit",
        },
        {
            "match_prefix": "google/gemini",
            "provider_only": _parse_csv_env("OPENROUTER_GEMINI_PROVIDER_ONLY") or ["google-vertex"],
            "provider_ignore": _parse_csv_env("OPENROUTER_GEMINI_PROVIDER_IGNORE"),
            "use_nitro": _env_flag("OPENROUTER_GEMINI_USE_NITRO", False),
            "temperature": float(os.getenv("OPENROUTER_GEMINI_TEMPERATURE", "0.2")),
            "top_p": float(os.getenv("OPENROUTER_GEMINI_TOP_P", "0.9")),
            "frequency_penalty": float(os.getenv("OPENROUTER_GEMINI_FREQUENCY_PENALTY", "0.0")),
            "presence_penalty": float(os.getenv("OPENROUTER_GEMINI_PRESENCE_PENALTY", "0.0")),
            "max_tokens_cap": max(128, _env_int("OPENROUTER_GEMINI_MAX_TOKENS", hard_cap)),
            "prompt_cache_supported": True,
            "prompt_cache_mode": "implicit",
        },
        {
            "match_prefix": "google/gemma",
            "provider_only": _parse_csv_env("OPENROUTER_GEMMA_PROVIDER_ONLY") or ["google-vertex"],
            "provider_ignore": _parse_csv_env("OPENROUTER_GEMMA_PROVIDER_IGNORE"),
            "use_nitro": _env_flag("OPENROUTER_GEMMA_USE_NITRO", False),
            "temperature": float(os.getenv("OPENROUTER_GEMMA_TEMPERATURE", "0.2")),
            "top_p": float(os.getenv("OPENROUTER_GEMMA_TOP_P", "0.88")),
            "frequency_penalty": float(os.getenv("OPENROUTER_GEMMA_FREQUENCY_PENALTY", "0.05")),
            "presence_penalty": float(os.getenv("OPENROUTER_GEMMA_PRESENCE_PENALTY", "0.05")),
            "max_tokens_cap": max(128, _env_int("OPENROUTER_GEMMA_MAX_TOKENS", hard_cap)),
            "prompt_cache_supported": False,
            "prompt_cache_mode": "unsupported",
        },
    ]

    for entry in registry:
        if base_model.startswith(str(entry.get("match_prefix") or "").lower()):
            return entry

    return {
        "provider_only": [],
        "provider_ignore": [],
        "use_nitro": False,
        "temperature": None,
        "top_p": None,
        "frequency_penalty": None,
        "presence_penalty": None,
        "max_tokens_cap": hard_cap,
        "prompt_cache_supported": False,
        "prompt_cache_mode": "unsupported",
    }


def _build_provider_preferences(model: str) -> Optional[Dict[str, Any]]:
    provider: Dict[str, Any] = {}
    runtime_cfg = _model_runtime_registry(model)

    ignored = [
        p.strip()
        for p in str(os.getenv("OPENROUTER_IGNORE_PROVIDERS", "") or "").split(",")
        if p.strip()
    ]
    ignored.extend([p for p in (runtime_cfg.get("provider_ignore") or []) if p])
    ignored = list(dict.fromkeys(ignored))
    if ignored:
        provider["ignore"] = ignored

    sort_mode = str(os.getenv("OPENROUTER_PROVIDER_SORT", "") or "").strip().lower()
    if sort_mode in {"throughput", "latency", "price"}:
        provider["sort"] = sort_mode

    allow_fallbacks_raw = os.getenv("OPENROUTER_ALLOW_FALLBACKS")
    if allow_fallbacks_raw is not None:
        provider["allow_fallbacks"] = _env_flag("OPENROUTER_ALLOW_FALLBACKS", True)

    provider_only = runtime_cfg.get("provider_only") or []
    if provider_only:
        provider["only"] = provider_only

    return provider or None


def _usage_number(usage: Dict[str, Any], *path: str) -> float:
    current: Any = usage
    for key in path:
        if not isinstance(current, dict):
            return 0.0
        current = current.get(key)
    try:
        return float(current or 0)
    except Exception:
        return 0.0


def _log_llm_end(model: str, elapsed_ms: float, usage: Dict[str, Any], total_cost: float) -> None:
    logger.info(
        "[LLM_END] model=%s elapsed_ms=%.2f prompt_tokens=%s completion_tokens=%s total_tokens=%s cached_tokens=%s cache_write_tokens=%s cost_usd=%.6f",
        model,
        elapsed_ms,
        int(_usage_number(usage, "prompt_tokens")),
        int(_usage_number(usage, "completion_tokens")),
        int(_usage_number(usage, "total_tokens")),
        int(_usage_number(usage, "prompt_tokens_details", "cached_tokens")),
        int(_usage_number(usage, "prompt_tokens_details", "cache_write_tokens")),
        float(total_cost or 0.0),
    )


def _append_usage_jsonl(model: str, usage: Dict[str, Any], total_cost: float, elapsed_ms: float) -> None:
    log_path = str(os.getenv("OPENROUTER_USAGE_LOG_PATH", "") or "").strip()
    if not log_path:
        return
    entry = {
        "ts": int(time.time()),
        "model": model,
        "prompt_tokens": int(_usage_number(usage, "prompt_tokens")),
        "completion_tokens": int(_usage_number(usage, "completion_tokens")),
        "total_tokens": int(_usage_number(usage, "total_tokens")),
        "cached_tokens": int(_usage_number(usage, "prompt_tokens_details", "cached_tokens")),
        "cache_write_tokens": int(_usage_number(usage, "prompt_tokens_details", "cache_write_tokens")),
        "reasoning_tokens": int(_usage_number(usage, "completion_tokens_details", "reasoning_tokens")),
        "cost_usd": float(total_cost or 0.0),
        "elapsed_ms": float(elapsed_ms),
    }
    try:
        log_dir = Path(log_path).expanduser().resolve().parent
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.warning("[LLM_USAGE_LOG_ERROR] path=%s detail=%s", log_path, exc)


async def complete(
    prompt: str = "",
    model_name: Optional[str] = None,
    max_tokens: int = 600,
    temperature: float = 0.7,
    top_p: float = 1.0,
    frequency_penalty: Optional[float] = None,
    presence_penalty: Optional[float] = None,
    seed: Optional[int] = None,
    response_format: Optional[Dict[str, Any]] = None,
    messages: Optional[list[dict]] = None,
    stop: Optional[list[str]] = None,
) -> tuple[str, dict]:
    """Wrapper OpenAI-compatible pour OpenRouter chat completions."""

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise OpenRouterLLMError("OPENROUTER_API_KEY manquant dans l'environnement")

    # 🛡️ V2.0 — Garde-fou central : TOUT appel OpenRouter doit passer par la famille Gemma/Gemini
    try:
        from core.model_registry import enforce_allowed_model, DEFAULT_MODEL
    except Exception:
        # Fallback minimal si le registry n'est pas dispo (ne doit jamais arriver)
        # Aligné avec la matrice officielle : Jessica Pro/Elite = Gemma 4-31b-it
        DEFAULT_MODEL = "google/gemma-4-31b-it"
        def enforce_allowed_model(m, context: str = ""):
            return m if (m and ("gemini" in str(m).lower() or "gemma" in str(m).lower())) else DEFAULT_MODEL

    default_model = enforce_allowed_model(os.getenv("LLM_MODEL") or DEFAULT_MODEL, context="llm_client_openrouter_default")
    requested_model = enforce_allowed_model((model_name or default_model).strip(), context="llm_client_openrouter_call")
    runtime_cfg = _model_runtime_registry(requested_model)
    if (runtime_cfg.get("use_nitro") or _env_flag("OPENROUTER_USE_NITRO", False)) and requested_model and ":" not in requested_model:
        requested_model = f"{requested_model}:nitro"
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
    stream_mode = _env_flag("OPENROUTER_STREAM", True)
    provider_preferences = _build_provider_preferences(requested_model)
    hard_max_response_chars = max(256, _env_int("OPENROUTER_MAX_RESPONSE_CHARS", 4000))

    try:
        for model in models_to_try:
            model_runtime_cfg = _model_runtime_registry(model)
            model_token_cap = int(model_runtime_cfg.get("max_tokens_cap") or _env_int("OPENROUTER_MAX_TOKENS_HARD_CAP", 1200))
            model_temperature = float(model_runtime_cfg.get("temperature") if model_runtime_cfg.get("temperature") is not None else temperature)
            model_top_p = float(model_runtime_cfg.get("top_p") if model_runtime_cfg.get("top_p") is not None else top_p)
            model_frequency_penalty = model_runtime_cfg.get("frequency_penalty")
            if model_frequency_penalty is not None:
                model_frequency_penalty = float(model_frequency_penalty)
            else:
                model_frequency_penalty = frequency_penalty
            model_presence_penalty = model_runtime_cfg.get("presence_penalty")
            if model_presence_penalty is not None:
                model_presence_penalty = float(model_presence_penalty)
            else:
                model_presence_penalty = presence_penalty
            requested_max_tokens = min(int(max_tokens or 0), model_token_cap)
            if int(max_tokens or 0) > requested_max_tokens:
                logger.warning(
                    "[LLM_SAFETY] model=%s max_tokens capped from %s to %s",
                    model,
                    int(max_tokens or 0),
                    requested_max_tokens,
                )
            attempted_max_tokens: set[int] = set()

            while True:
                if requested_max_tokens in attempted_max_tokens:
                    break
                attempted_max_tokens.add(requested_max_tokens)

                body = {
                    "model": model,
                    "messages": messages if isinstance(messages, list) and messages else [{"role": "user", "content": prompt}],
                    "temperature": model_temperature,
                    "max_tokens": requested_max_tokens,
                    "top_p": model_top_p,
                    "stream": stream_mode,
                }
                effective_stop = stop if isinstance(stop, list) and stop else None
                if effective_stop is None and str(model or "").lower().startswith("deepseek/deepseek"):
                    effective_stop = ["<｜fim▁end｜>", "<｜fim▁begin｜>", "<｜fim▁hole｜>"]
                if effective_stop:
                    body["stop"] = effective_stop
                if model_frequency_penalty is not None:
                    try:
                        body["frequency_penalty"] = float(model_frequency_penalty)
                    except Exception:
                        pass
                if model_presence_penalty is not None:
                    try:
                        body["presence_penalty"] = float(model_presence_penalty)
                    except Exception:
                        pass
                if seed is not None:
                    body["seed"] = int(seed)
                if response_format is not None:
                    body["response_format"] = response_format
                if provider_preferences:
                    body["provider"] = provider_preferences

                logger.info(
                    "[LLM_START] model=%s stream=%s prompt_chars=%s messages=%s max_tokens=%s temp=%.3f top_p=%.3f freq_pen=%s pres_pen=%s provider=%s cache_supported=%s cache_mode=%s timeout_s=%.1f",
                    model,
                    stream_mode,
                    len(prompt or ""),
                    len(body["messages"]),
                    requested_max_tokens,
                    model_temperature,
                    model_top_p,
                    model_frequency_penalty,
                    model_presence_penalty,
                    provider_preferences or {},
                    bool(runtime_cfg.get("prompt_cache_supported", False)),
                    str(runtime_cfg.get("prompt_cache_mode") or "unsupported"),
                    _openrouter_timeout(),
                )
                started_at = time.perf_counter()
                client = _get_openrouter_client()

                try:
                    if stream_mode:
                        content_parts: list[str] = []
                        usage: Dict[str, Any] = {}
                        data: Dict[str, Any] = {}
                        stop_stream = False
                        async with client.stream("POST", OPENROUTER_API_URL, json=body, headers=headers) as resp:
                            if resp.status_code != 200:
                                err_txt_full = await resp.aread()
                                err_txt_full = err_txt_full.decode("utf-8", errors="replace")
                                err_txt = err_txt_full[:300]
                                last_error = f"OpenRouter API HTTP {resp.status_code}: {err_txt}"
                                logger.warning(
                                    "[LLM_ERROR] model=%s status=%s elapsed_ms=%.2f detail=%s",
                                    model,
                                    resp.status_code,
                                    (time.perf_counter() - started_at) * 1000.0,
                                    err_txt,
                                )
                                if resp.status_code == 400 and "not a valid model" in err_txt_full.lower():
                                    break
                                if resp.status_code == 402:
                                    m = re.search(r"can only afford\s+(\d+)", err_txt_full, flags=re.IGNORECASE)
                                    if m:
                                        try:
                                            affordable = int(m.group(1))
                                        except Exception:
                                            affordable = 0
                                        if affordable > 0 and affordable < requested_max_tokens and affordable >= 120:
                                            requested_max_tokens = affordable
                                            continue
                                raise OpenRouterLLMError(last_error)

                            async for line in resp.aiter_lines():
                                if stop_stream:
                                    break
                                if not line or not line.startswith("data:"):
                                    continue
                                payload = line[5:].strip()
                                if not payload or payload == "[DONE]":
                                    continue
                                try:
                                    chunk = json.loads(payload)
                                except Exception:
                                    continue
                                if isinstance(chunk.get("usage"), dict):
                                    usage = chunk.get("usage") or {}
                                if isinstance(chunk, dict):
                                    data = chunk
                                for choice in chunk.get("choices") or []:
                                    delta = choice.get("delta") or {}
                                    piece = delta.get("content")
                                    if piece:
                                        content_parts.append(str(piece))
                                        if sum(len(part) for part in content_parts) > hard_max_response_chars:
                                            joined = "".join(content_parts)
                                            content_parts = [joined[:hard_max_response_chars]]
                                            logger.warning(
                                                "[LLM_SAFETY] model=%s response truncated at %s chars during stream",
                                                model,
                                                hard_max_response_chars,
                                            )
                                            stop_stream = True
                                            break

                        content = "".join(content_parts).strip()
                    else:
                        resp = await client.post(OPENROUTER_API_URL, json=body, headers=headers)
                        if resp.status_code != 200:
                            err_txt_full = resp.text or ""
                            err_txt = err_txt_full[:300]
                            last_error = f"OpenRouter API HTTP {resp.status_code}: {err_txt}"
                            logger.warning(
                                "[LLM_ERROR] model=%s status=%s elapsed_ms=%.2f detail=%s",
                                model,
                                resp.status_code,
                                (time.perf_counter() - started_at) * 1000.0,
                                err_txt,
                            )
                            if resp.status_code == 400 and "not a valid model" in err_txt_full.lower():
                                break
                            if resp.status_code == 402:
                                m = re.search(r"can only afford\s+(\d+)", err_txt_full, flags=re.IGNORECASE)
                                if m:
                                    try:
                                        affordable = int(m.group(1))
                                    except Exception:
                                        affordable = 0
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
                        if not data:
                            raise OpenRouterLLMError("Réponse OpenRouter vide")
                        choices = data.get("choices") or []
                        if not choices:
                            raise OpenRouterLLMError("Réponse OpenRouter sans choices")
                        message = choices[0].get("message") or {}
                        content = str((message.get("content") or "")).strip()
                        if len(content) > hard_max_response_chars:
                            logger.warning(
                                "[LLM_SAFETY] model=%s response truncated at %s chars after completion",
                                model,
                                hard_max_response_chars,
                            )
                            content = content[:hard_max_response_chars]
                        usage = data.get("usage") or {}

                    total_cost = None
                    try:
                        total_cost = (
                            data.get("total_cost")
                            if isinstance(data, dict) and data.get("total_cost") is not None
                            else data.get("cost") if isinstance(data, dict) else None
                        )
                        if total_cost is None and isinstance(usage, dict):
                            total_cost = usage.get("total_cost") if usage.get("total_cost") is not None else usage.get("cost")
                    except Exception:
                        total_cost = None

                    if total_cost is None:
                        PRICING = {
                            "google/gemma-4-26b-a4b-it": {"in": 0.08, "out": 0.35},
                            "google/gemma-4-31b-it": {"in": 0.08, "out": 0.35},
                            "deepseek/deepseek-v3": {"in": 0.14, "out": 0.28},
                            "qwen/qwen-2.5-72b-instruct": {"in": 0.35, "out": 0.35},
                            "meta-llama/llama-3.1-405b-instruct": {"in": 2.0, "out": 2.0},
                            "google/gemini-2.0-flash": {"in": 0.10, "out": 0.40},
                            "qwen/qwen3.5-flash-02-23": {"in": 0.0, "out": 0.0},
                            "qwen/qwen3.5-flash-02-23:nitro": {"in": 0.0, "out": 0.0},
                        }
                        p_tokens = usage.get("prompt_tokens", 0) if isinstance(usage, dict) else 0
                        c_tokens = usage.get("completion_tokens", 0) if isinstance(usage, dict) else 0
                        rates = PRICING.get(model)
                        total_cost = ((p_tokens * rates["in"] + c_tokens * rates["out"]) / 1_000_000) if rates else 0.0

                    elapsed_ms = (time.perf_counter() - started_at) * 1000.0
                    _log_llm_end(model, elapsed_ms, usage if isinstance(usage, dict) else {}, float(total_cost or 0.0))
                    _append_usage_jsonl(model, usage if isinstance(usage, dict) else {}, float(total_cost or 0.0), elapsed_ms)

                    token_info = {
                        "prompt_tokens": usage.get("prompt_tokens", 0) if isinstance(usage, dict) else 0,
                        "completion_tokens": usage.get("completion_tokens", 0) if isinstance(usage, dict) else 0,
                        "total_tokens": usage.get("total_tokens", 0) if isinstance(usage, dict) else 0,
                        "model": model,
                        "usage": usage if isinstance(usage, dict) else {},
                        "total_cost": total_cost or 0.0,
                    }
                    return content, token_info
                except httpx.HTTPError as e:
                    logger.warning(
                        "[LLM_ERROR] model=%s elapsed_ms=%.2f detail=%s",
                        model,
                        (time.perf_counter() - started_at) * 1000.0,
                        str(e),
                    )
                    raise OpenRouterLLMError(f"Erreur requête OpenRouter: {e}")

        raise OpenRouterLLMError(last_error or "OpenRouter: aucun modèle valide (tous refusés)")
    except httpx.HTTPError as e:
        raise OpenRouterLLMError(f"Erreur requête OpenRouter: {e}")

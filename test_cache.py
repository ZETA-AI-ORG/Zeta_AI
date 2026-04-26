#!/usr/bin/env python3
import asyncio
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


load_dotenv()

OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL_NAME = os.getenv("TEST_MODEL_NAME", "google/gemini-3.1-flash-lite-preview")


def normalize_provider_token(token: str) -> str:
    raw = str(token or "").strip().lower()
    if not raw:
        return ""
    compact = raw.replace(" ", "-").replace("_", "-").replace(".", "")
    aliases = {
        "alibaba": "alibaba",
        "alibaba-cloud-int": "alibaba",
        "alibabacloudint": "alibaba",
        "google-vertex": "google-vertex",
        "googlevertex": "google-vertex",
        "google-ai-studio": "google-ai-studio",
        "googleaistudio": "google-ai-studio",
        "deepseek": "deepseek",
        "novitaai": "novitaai",
        "novita-ai": "novitaai",
        "deepinfra": "deepinfra",
    }
    return aliases.get(raw, aliases.get(compact, compact))


def provider_only_for_model(model_name: str) -> list[str]:
    if model_name.startswith("qwen/"):
        raw = os.getenv("OPENROUTER_QWEN_PROVIDER_ONLY", "alibaba")
    elif model_name.startswith("google/gemini"):
        raw = os.getenv("OPENROUTER_GEMINI_PROVIDER_ONLY", "google-ai-studio")
    elif model_name.startswith("google/gemma"):
        raw = os.getenv("OPENROUTER_GEMMA_PROVIDER_ONLY", "google-ai-studio")
    else:
        raw = os.getenv("OPENROUTER_PROVIDER_ONLY", "")
    return [normalize_provider_token(x) for x in str(raw or "").split(",") if normalize_provider_token(x)]


PROVIDER_ONLY = provider_only_for_model(MODEL_NAME)
PROMPT_CACHE_SUPPORTED = {
    "qwen/qwen3.5-flash-02-23": False,
    "qwen/qwen3.5-flash-02-23:nitro": False,
    "deepseek/deepseek-v3.2": True,
    "google/gemini-3.1-flash-lite-preview": None,
    "google/gemini-3.1-flash-preview": None,
    "google/gemma-4-26b-a4b-it": None,
}


async def main() -> None:
    if not OPENROUTER_API_KEY:
        raise SystemExit("OPENROUTER_API_KEY manquant")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    prompt_path = Path("prompt_universel_v2.md")
    if prompt_path.exists():
        system_prompt = prompt_path.read_text(encoding="utf-8", errors="ignore")
    else:
        system_prompt = ("Tu es Jessica. Réponds brièvement. " * 400).strip()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Test cache requête 1"},
    ]

    provider = {"only": PROVIDER_ONLY} if PROVIDER_ONLY else {}

    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0)) as client:
        for idx in range(2):
            body = {
                "model": MODEL_NAME,
                "messages": messages,
                "max_tokens": 50,
                "stream": False,
            }
            if provider:
                body["provider"] = provider

            resp = await client.post(OPENROUTER_API_URL, json=body, headers=headers)
            if resp.status_code != 200:
                print(
                json.dumps(
                    {
                        "request": idx + 1,
                        "status_code": resp.status_code,
                        "body": resp.text[:2000],
                        "model": MODEL_NAME,
                        "provider_only": PROVIDER_ONLY,
                        "url": OPENROUTER_API_URL,
                    },
                    ensure_ascii=False,
                )
            )
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage") or {}
            prompt_details = usage.get("prompt_tokens_details") or {}
            print(
                json.dumps(
                    {
                        "request": idx + 1,
                        "model": MODEL_NAME,
                        "provider_only": PROVIDER_ONLY,
                        "prompt_cache_supported": PROMPT_CACHE_SUPPORTED.get(MODEL_NAME),
                        "system_prompt_chars": len(system_prompt),
                        "cost": data.get("total_cost", data.get("cost", usage.get("cost"))),
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "cached_tokens": prompt_details.get("cached_tokens", 0),
                        "cache_write_tokens": prompt_details.get("cache_write_tokens", 0),
                    },
                    ensure_ascii=False,
                )
            )
            if PROMPT_CACHE_SUPPORTED.get(MODEL_NAME) is False:
                print(
                    json.dumps(
                        {
                            "diagnostic": "prompt_cache_not_supported",
                            "model": MODEL_NAME,
                            "provider_only": PROVIDER_ONLY,
                            "note": "cached_tokens=0 est attendu sur ce modèle; utiliser DeepSeek pour tester le prompt caching OpenRouter.",
                        },
                        ensure_ascii=False,
                    )
                )
            if idx == 0:
                await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())

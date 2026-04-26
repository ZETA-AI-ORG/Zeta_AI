#!/usr/bin/env python3
import asyncio
import json
import os

import httpx
from dotenv import load_dotenv


load_dotenv()

OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL_NAME = os.getenv("TEST_MODEL_NAME", "qwen/qwen3.5-flash-02-23")


def normalize_provider_token(token: str) -> str:
    raw = str(token or "").strip().lower()
    if not raw:
        return ""
    compact = raw.replace(" ", "-").replace("_", "-").replace(".", "")
    aliases = {
        "alibaba": "alibaba-cloud-int",
        "alibaba-cloud-int": "alibaba-cloud-int",
        "alibabacloudint": "alibaba-cloud-int",
        "google-vertex": "google-vertex",
        "googlevertex": "google-vertex",
        "deepseek": "deepseek",
        "novitaai": "novitaai",
        "novita-ai": "novitaai",
        "deepinfra": "deepinfra",
    }
    return aliases.get(raw, aliases.get(compact, compact))


PROVIDER_ONLY = [normalize_provider_token(x) for x in str(os.getenv("OPENROUTER_QWEN_PROVIDER_ONLY", "alibaba") or "").split(",") if normalize_provider_token(x)]


async def main() -> None:
    if not OPENROUTER_API_KEY:
        raise SystemExit("OPENROUTER_API_KEY manquant")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    messages = [
        {"role": "system", "content": "Tu es Jessica. Réponds brièvement."},
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
                        "cost": data.get("total_cost", data.get("cost", usage.get("cost"))),
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "cached_tokens": prompt_details.get("cached_tokens", 0),
                        "cache_write_tokens": prompt_details.get("cache_write_tokens", 0),
                    },
                    ensure_ascii=False,
                )
            )
            if idx == 0:
                await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())

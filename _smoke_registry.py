"""Smoke test temporaire — à supprimer après vérif."""
from core.model_registry import (
    resolve_model_for_plan,
    enforce_allowed_model,
    get_registry_snapshot,
    MODEL_RANG_A,
    MODEL_RANG_S,
    MODEL_RANG_SS,
    MODEL_INSIGHT,
)
import json

print("=== REGISTRY ===")
print(json.dumps(get_registry_snapshot(), indent=2))
print()
print("=== BOTS & PLANS ===")
print("Amanda (decouverte) :", resolve_model_for_plan("decouverte"))
print("Amanda (starter)    :", resolve_model_for_plan("starter"))
print("Jessica (pro)       :", resolve_model_for_plan("pro"))
print("Jessica (elite)     :", resolve_model_for_plan("elite"))
print("Jessica Boost (pro) :", resolve_model_for_plan("pro", has_boost=True))
print("Jessica Boost(elite):", resolve_model_for_plan("elite", has_boost=True))
print("Closing (elite)     :", resolve_model_for_plan("elite", is_closing=True))
print("Pivot (elite+boost) :", resolve_model_for_plan("elite", has_boost=True, is_pivot=True))
print()
print("=== GARDE-FOU — INTERDITS ===")
bads = [
    "groq/llama-3.3-70b-versatile",
    "deepseek/deepseek-v3",
    "mistralai/mistral-small-3.2-24b-instruct",
    "anthropic/claude-3-opus",
    "openai/gpt-4-turbo",
    "qwen/qwen-2.5-72b",
]
for b in bads:
    print(f"  {b:50} -> {enforce_allowed_model(b, context='audit')}")
print()
print("=== GARDE-FOU — AUTORISES ===")
for ok in [MODEL_RANG_A, MODEL_RANG_S, MODEL_RANG_SS, MODEL_INSIGHT]:
    print(f"  {ok:50} -> {enforce_allowed_model(ok, context='audit')}")

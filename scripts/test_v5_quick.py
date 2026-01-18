"""Test rapide SetFit V5"""
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from core.setfit_intent_router import route_botlive_intent, _load_setfit_model
import asyncio

# Force le chargement du modèle SetFit au démarrage
print("🔄 Chargement du modèle SetFit V5...")
_load_setfit_model()
print("✅ Modèle chargé\n")

async def test():
    from core.setfit_intent_router import _route_with_setfit
    
    tests = [
        "Bonjour, vous êtes où ?",
        "Je veux commander des couches",
        "Où en est ma commande ?",
        "Combien coûtent les couches ?",
    ]
    
    print("=" * 60)
    print("TEST DIRECT SETFIT V5 (bypass prefilter)")
    print("=" * 60)
    
    for msg in tests:
        intent, conf, debug = _route_with_setfit(msg, conversation_history="", state_compact={})
        print(f"\n'{msg}'")
        print(f"  → SetFit raw: {intent} (conf={conf:.2f})")
        print(f"  → router_source: {debug.get('router_source')}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLET (avec prefilter + sub-routing)")
    print("=" * 60)
    
    for msg in tests:
        result = await route_botlive_intent(
            company_id="test",
            user_id="test",
            message=msg,
            conversation_history="",
            state_compact={},
        )
        print(f"\n'{msg}'")
        print(f"  → pole={result.intent}, mode={result.mode}, conf={result.confidence:.2f}")
        print(f"  → model_version={result.debug.get('model_version')}")
        print(f"  → prefilter={result.debug.get('prefilter')}")
        print(f"  → sub_v5={result.debug.get('business_subroute_v5')}")
        print(f"  → action_v5={result.debug.get('business_subroute_v5_action')}")

asyncio.run(test())

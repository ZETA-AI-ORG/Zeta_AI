#!/usr/bin/env python3
"""
🔍 DIAGNOSTIC DES IMPORTS RAG
Script pour identifier quelle import cause l'erreur
"""

import sys
import traceback

def test_imports():
    """Teste chaque import un par un pour identifier l'erreur"""
    
    print("🔍 DIAGNOSTIC DES IMPORTS RAG")
    print("=" * 50)
    
    imports_to_test = [
        ("asyncio", "asyncio"),
        ("logging", "logging"),
        ("traceback", "traceback"),
        ("typing", "typing"),
        ("core.preprocessing", "post_hyde_filter"),
        ("core.cache_manager", "cache_manager"),
        ("core.quick_context_lookup", "QuickContextLookup"),
        ("core.context_sources", "ContextSources"),
        ("core.dynamic_offtopic_detector", "DynamicOffTopicDetector"),
        ("core.intelligent_hallucination_guard", "IntelligentHallucinationGuard"),
        ("core.intention_router", "intention_router"),
        ("core.llm_client", "GroqLLMClient"),
        ("core.business_config_manager", "BusinessConfigManager"),
        ("core.prompt_manager", "PromptManager"),
        ("database.supabase_client", "get_supabase_client"),
        ("database.vector_store", "search_meili_keywords"),
        ("core.price_calculator", "calculate_order_price"),
        ("core.recap_template", "generate_order_summary"),
        ("core.progressive_memory_system", "process_conversation_message"),
        ("utils", "log3"),
    ]
    
    failed_imports = []
    
    for module_name, import_name in imports_to_test:
        try:
            print(f"✅ Test import: {module_name}.{import_name}")
            if "." in module_name:
                module = __import__(module_name, fromlist=[import_name])
                getattr(module, import_name)
            else:
                __import__(module_name)
            print(f"   ✅ Succès")
        except Exception as e:
            print(f"   ❌ ERREUR: {e}")
            failed_imports.append((module_name, import_name, str(e)))
            traceback.print_exc()
        print()
    
    print("📊 RÉSUMÉ DU DIAGNOSTIC")
    print("=" * 50)
    
    if failed_imports:
        print(f"❌ {len(failed_imports)} imports ont échoué:")
        for module, import_name, error in failed_imports:
            print(f"   • {module}.{import_name}: {error}")
    else:
        print("✅ Tous les imports fonctionnent correctement")
    
    return failed_imports

if __name__ == "__main__":
    test_imports()




import asyncio
import os
from core.simplified_prompt_system import SimplifiedPromptSystem

async def test():
    system = SimplifiedPromptSystem()
    query = "bonjour je veux des couches"
    user_id = "test_verify"
    company_id = "W27PwOPiblP8TlOrhPcjOtxd0cza" # Use a known company
    
    # Mocking environment for shop configuration
    os.environ["COMPANY_NAME"] = "Test Shop"
    
    print("Testing build_prompt...")
    prompt = await system.build_prompt(
        query=query,
        user_id=user_id,
        company_id=company_id
    )
    
    print("\n--- PROMPT PREVIEW ---")
    # Check for PRODUCT_INDEX
    if "PRODUCT_INDEX:" in prompt:
        print("✅ PRODUCT_INDEX found")
        start = prompt.find("PRODUCT_INDEX:")
        end = prompt.find("[[PRODUCT_INDEX_END]]")
        if end == -1: end = start + 500
        print(prompt[start:end])
    else:
        print("❌ PRODUCT_INDEX NOT found")
        
    # Check if CATALOGUE_BLOCK is empty (funnel behavior)
    if "[[CATALOGUE_START]]" in prompt:
        start = prompt.find("[[CATALOGUE_START]]") + len("[[CATALOGUE_START]]")
        end = prompt.find("[[CATALOGUE_END]]")
        content = prompt[start:end].strip()
        if not content:
            print("✅ CATALOGUE_BLOCK is empty (Funnel active)")
        else:
            print(f"❌ CATALOGUE_BLOCK IS NOT EMPTY: {content[:100]}...")
    
    print("\n--- LOG CHECK ---")
    # We should NOT see "🎯 [PRE_LLM_MATCH]" in stdout (if we ran it in a subprocess)
    # But here we just check logic.

if __name__ == "__main__":
    asyncio.run(test())

#!/usr/bin/env python3
"""
🧹 VIDE TOUS LES CACHES AVANT TEST
"""
import sys

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    END = '\033[0m'

def clear_all_caches():
    """Vide tous les systèmes de cache"""
    
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}🧹 VIDAGE DE TOUS LES CACHES{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")
    
    cleared = []
    errors = []
    
    # 1. FAQ Answer Cache
    print(f"1️⃣ FAQ Answer Cache...")
    try:
        from core.faq_answer_cache import faq_answer_cache
        
        # Vider mémoire
        memory_before = len(faq_answer_cache.memory_cache)
        faq_answer_cache.memory_cache.clear()
        
        # Vider Redis
        redis_cleared = 0
        if faq_answer_cache.redis:
            try:
                redis_cleared = faq_answer_cache.redis.flushdb()
                print(f"   {Colors.GREEN}✅ Mémoire:{Colors.END} {memory_before} entrées vidées")
                print(f"   {Colors.GREEN}✅ Redis:{Colors.END} Base vidée")
            except Exception as e:
                print(f"   {Colors.YELLOW}⚠️ Redis:{Colors.END} {e}")
        else:
            print(f"   {Colors.GREEN}✅ Mémoire:{Colors.END} {memory_before} entrées vidées")
            print(f"   {Colors.YELLOW}⚠️ Redis:{Colors.END} Non connecté")
        
        cleared.append('FAQ Answer Cache')
    except Exception as e:
        print(f"   {Colors.RED}❌ Erreur:{Colors.END} {e}")
        errors.append(('FAQ Answer Cache', str(e)))
    
    # 2. Global Prompt Cache
    print(f"\n2️⃣ Global Prompt Cache...")
    try:
        from core.unified_cache_system import get_unified_cache_system
        cache_system = get_unified_cache_system()
        
        # Vider le cache prompt
        if hasattr(cache_system, 'prompt_cache'):
            cache_system.prompt_cache.cache.clear()
            print(f"   {Colors.GREEN}✅ Cache prompt vidé{Colors.END}")
        
        cleared.append('Global Prompt Cache')
    except Exception as e:
        print(f"   {Colors.YELLOW}⚠️{Colors.END} {e}")
        # Pas grave si ça échoue
    
    # 3. Semantic Intent Cache (si existe)
    print(f"\n3️⃣ Semantic Intent Cache...")
    try:
        from core.semantic_intent_cache import SemanticIntentCache
        # Essayer de vider si singleton existe
        print(f"   {Colors.YELLOW}⚠️ Import réussi mais pas de clear() disponible{Colors.END}")
    except Exception as e:
        print(f"   {Colors.YELLOW}⚠️ Non disponible{Colors.END} ({e})")
    
    # 4. Conversation Memory
    print(f"\n4️⃣ Conversation Memory...")
    print(f"   {Colors.GREEN}✅ Pas besoin{Colors.END} - User ID unique à chaque test")
    
    # RÉSUMÉ
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}📊 RÉSUMÉ{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")
    
    print(f"{Colors.GREEN}✅ Caches vidés:{Colors.END} {len(cleared)}")
    for c in cleared:
        print(f"   - {c}")
    
    if errors:
        print(f"\n{Colors.YELLOW}⚠️ Erreurs (non bloquantes):{Colors.END} {len(errors)}")
        for name, err in errors:
            print(f"   - {name}: {err[:60]}")
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}✅ PRÊT POUR LE TEST !{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")

if __name__ == "__main__":
    clear_all_caches()

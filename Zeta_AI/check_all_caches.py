#!/usr/bin/env python3
"""
🔍 AUDIT COMPLET DES CACHES ACTIFS
Vérifie tous les systèmes de cache dans l'application
"""
import sys
import os

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def check_cache_status():
    """Vérifie le statut de tous les caches"""
    
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}🔍 AUDIT COMPLET DES CACHES ACTIFS{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")
    
    caches_found = []
    
    # 1. FAQ Answer Cache
    print(f"{Colors.CYAN}1️⃣ FAQ ANSWER CACHE{Colors.END}")
    try:
        from core.faq_answer_cache import faq_answer_cache
        memory_size = len(faq_answer_cache.memory_cache)
        has_redis = faq_answer_cache.redis is not None
        
        print(f"   Status: {Colors.GREEN}✅ ACTIF{Colors.END}")
        print(f"   Type: Mémoire + Redis (si dispo)")
        print(f"   Entrées mémoire: {Colors.YELLOW}{memory_size}{Colors.END}")
        print(f"   Redis disponible: {Colors.GREEN if has_redis else Colors.RED}{'Oui' if has_redis else 'Non'}{Colors.END}")
        print(f"   TTL: {faq_answer_cache.ttl_seconds}s (1h)")
        print(f"   Impact test: {Colors.RED}⚠️ ÉLEVÉ{Colors.END} - Questions identiques = cache hit")
        
        caches_found.append({
            'name': 'FAQ Answer Cache',
            'active': True,
            'size': memory_size,
            'impact': 'ÉLEVÉ'
        })
    except Exception as e:
        print(f"   Status: {Colors.RED}❌ Non trouvé{Colors.END} ({e})")
    
    # 2. Semantic Intent Cache
    print(f"\n{Colors.CYAN}2️⃣ SEMANTIC INTENT CACHE{Colors.END}")
    try:
        from core.semantic_intent_cache import semantic_cache
        cache_size = len(semantic_cache.cache) if hasattr(semantic_cache, 'cache') else 'N/A'
        
        print(f"   Status: {Colors.GREEN}✅ ACTIF{Colors.END}")
        print(f"   Type: Cache sémantique (similarité)")
        print(f"   Entrées: {Colors.YELLOW}{cache_size}{Colors.END}")
        print(f"   Impact test: {Colors.YELLOW}⚠️ MOYEN{Colors.END} - Questions similaires = cache hit")
        
        caches_found.append({
            'name': 'Semantic Intent Cache',
            'active': True,
            'size': cache_size,
            'impact': 'MOYEN'
        })
    except Exception as e:
        print(f"   Status: {Colors.RED}❌ Non trouvé{Colors.END} ({e})")
    
    # 3. Global Prompt Cache
    print(f"\n{Colors.CYAN}3️⃣ GLOBAL PROMPT CACHE{Colors.END}")
    try:
        from core.unified_cache_system import get_unified_cache_system
        cache_system = get_unified_cache_system()
        
        print(f"   Status: {Colors.GREEN}✅ ACTIF{Colors.END}")
        print(f"   Type: Cache prompts système")
        print(f"   Impact test: {Colors.GREEN}✅ FAIBLE{Colors.END} - Ne cache pas les réponses")
        
        caches_found.append({
            'name': 'Global Prompt Cache',
            'active': True,
            'size': 'N/A',
            'impact': 'FAIBLE'
        })
    except Exception as e:
        print(f"   Status: {Colors.RED}❌ Non trouvé{Colors.END} ({e})")
    
    # 4. Embedding Cache
    print(f"\n{Colors.CYAN}4️⃣ EMBEDDING CACHE{Colors.END}")
    try:
        from core.global_embedding_cache import get_embedding_cache
        emb_cache = get_embedding_cache()
        cache_size = len(emb_cache.cache) if hasattr(emb_cache, 'cache') else 'N/A'
        
        print(f"   Status: {Colors.GREEN}✅ ACTIF{Colors.END}")
        print(f"   Type: Cache embeddings vectoriels")
        print(f"   Entrées: {Colors.YELLOW}{cache_size}{Colors.END}")
        print(f"   Impact test: {Colors.GREEN}✅ FAIBLE{Colors.END} - Accélère recherche, pas de cache réponse")
        
        caches_found.append({
            'name': 'Embedding Cache',
            'active': True,
            'size': cache_size,
            'impact': 'FAIBLE'
        })
    except Exception as e:
        print(f"   Status: {Colors.RED}❌ Non trouvé{Colors.END} ({e})")
    
    # 5. Conversation Memory
    print(f"\n{Colors.CYAN}5️⃣ CONVERSATION MEMORY{Colors.END}")
    try:
        from core.optimized_conversation_memory import conversation_cache
        
        print(f"   Status: {Colors.GREEN}✅ ACTIF{Colors.END}")
        print(f"   Type: Historique conversationnel")
        print(f"   Impact test: {Colors.GREEN}✅ ÉVITÉ{Colors.END} - User ID unique à chaque test")
        
        caches_found.append({
            'name': 'Conversation Memory',
            'active': True,
            'size': 'N/A',
            'impact': 'ÉVITÉ (user unique)'
        })
    except Exception as e:
        print(f"   Status: {Colors.YELLOW}⚠️ Non trouvé{Colors.END} ({e})")
    
    # RÉSUMÉ
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}📊 RÉSUMÉ{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")
    
    high_impact = [c for c in caches_found if c['impact'] == 'ÉLEVÉ']
    medium_impact = [c for c in caches_found if c['impact'] == 'MOYEN']
    
    print(f"Total caches actifs: {Colors.BOLD}{len(caches_found)}{Colors.END}")
    print(f"{Colors.RED}⚠️ Impact ÉLEVÉ:{Colors.END} {len(high_impact)}")
    for c in high_impact:
        print(f"   - {c['name']} ({c['size']} entrées)")
    
    print(f"{Colors.YELLOW}⚠️ Impact MOYEN:{Colors.END} {len(medium_impact)}")
    for c in medium_impact:
        print(f"   - {c['name']} ({c['size']} entrées)")
    
    # RECOMMANDATION
    print(f"\n{Colors.BOLD}💡 RECOMMANDATION:{Colors.END}")
    if high_impact or medium_impact:
        print(f"{Colors.RED}⚠️ VIDER LES CACHES avant test pour résultats précis{Colors.END}")
        print(f"\nCommandes:")
        if high_impact:
            print(f"   python clear_all_caches.py  # Vide tout")
        print(f"   # OU redémarrer serveur: Ctrl+C puis uvicorn app:app --reload")
    else:
        print(f"{Colors.GREEN}✅ Pas de cache à risque détecté{Colors.END}")
    
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}\n")
    
    return caches_found

if __name__ == "__main__":
    check_cache_status()

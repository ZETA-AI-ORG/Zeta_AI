#!/usr/bin/env python3
"""
🧹 CLEAR PROMPT CACHE
Script pour vider le cache des prompts et forcer le rechargement
"""

import asyncio
import sys
import os

async def clear_prompt_cache():
    """Vide le cache des prompts pour forcer le rechargement"""
    
    print("🧹 NETTOYAGE CACHE PROMPT")
    print("="*50)
    
    try:
        # Import du système de cache unifié
        from core.unified_cache_system import get_unified_cache_system
        
        cache_system = get_unified_cache_system()
        
        # Vider le cache prompt spécifiquement
        if hasattr(cache_system, 'prompt_cache'):
            cleared_count = await cache_system.prompt_cache.clear_all_prompts()
            print(f"✅ Cache prompt vidé: {cleared_count} entrées supprimées")
        
        # Vider aussi le cache prompt direct si il existe
        try:
            from database.supabase_client import clear_prompt_cache as clear_supabase_cache
            await clear_supabase_cache()
            print("✅ Cache prompt Supabase vidé")
        except ImportError:
            print("⚠️ Module supabase_client non trouvé")
        except AttributeError:
            print("⚠️ Méthode clear_prompt_cache non disponible dans supabase_client")
        except Exception as e:
            print(f"⚠️ Erreur cache Supabase: {e}")
        
        # Vider le cache Redis si utilisé
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            
            # Chercher les clés de cache prompt
            prompt_keys = r.keys("prompt_cache:*")
            if prompt_keys:
                r.delete(*prompt_keys)
                print(f"✅ {len(prompt_keys)} clés prompt supprimées de Redis")
            else:
                print("ℹ️ Aucune clé prompt trouvée dans Redis")
                
        except ImportError:
            print("ℹ️ Redis non disponible")
        except Exception as e:
            print(f"⚠️ Erreur Redis: {e}")
        
        print("\n🎯 RÉSULTAT:")
        print("✅ Cache prompt vidé avec succès")
        print("✅ Le prochain appel rechargera le prompt depuis la DB")
        print("✅ Les nouvelles règles de tarification seront appliquées")
        
    except Exception as e:
        print(f"❌ Erreur lors du nettoyage: {e}")
        return False
    
    return True

async def clear_specific_company_cache(company_id: str):
    """Vide le cache pour une entreprise spécifique"""
    
    print(f"🧹 NETTOYAGE CACHE POUR COMPANY: {company_id}")
    print("="*50)
    
    try:
        from core.unified_cache_system import get_unified_cache_system
        
        cache_system = get_unified_cache_system()
        
        # Vider le cache prompt pour cette entreprise
        if hasattr(cache_system, 'prompt_cache'):
            invalidated = await cache_system.prompt_cache.invalidate_prompt(company_id)
            if invalidated:
                print(f"✅ Cache prompt entreprise {company_id[:12]}... vidé")
            else:
                print(f"⚠️ Aucun cache prompt trouvé pour {company_id[:12]}...")
        
        # Vider aussi Redis pour cette entreprise
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            
            # Chercher les clés pour cette entreprise
            company_keys = r.keys(f"*{company_id}*")
            if company_keys:
                r.delete(*company_keys)
                print(f"✅ {len(company_keys)} clés entreprise supprimées de Redis")
            else:
                print(f"ℹ️ Aucune clé Redis trouvée pour cette entreprise")
            
        except Exception as e:
            print(f"⚠️ Erreur Redis entreprise: {e}")
        
        print(f"\n✅ Cache vidé pour l'entreprise {company_id[:12]}...")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    return True

async def main():
    """Fonction principale"""
    
    if len(sys.argv) > 1:
        # Mode entreprise spécifique
        company_id = sys.argv[1]
        print(f"🎯 Mode: Nettoyage entreprise spécifique")
        success = await clear_specific_company_cache(company_id)
    else:
        # Mode global
        print(f"🎯 Mode: Nettoyage global du cache prompt")
        success = await clear_prompt_cache()
    
    if success:
        print("\n🚀 PRÊT POUR LES TESTS")
        print("Le prochain appel utilisera le nouveau prompt avec les règles de tarification !")
    else:
        print("\n❌ Échec du nettoyage")
        sys.exit(1)

if __name__ == "__main__":
    print("🧹 CLEAR PROMPT CACHE - Forcer rechargement prompt")
    print("Usage:")
    print("  python clear_prompt_cache.py                    # Vider tout le cache prompt")
    print("  python clear_prompt_cache.py <company_id>       # Vider cache d'une entreprise")
    print()
    
    asyncio.run(main())

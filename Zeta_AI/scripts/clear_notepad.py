"""
Script pour vider la table conversation_notepad dans Supabase
Usage: python scripts/clear_notepad.py
"""

import asyncio
from core.supabase_notepad import get_supabase_notepad

async def clear_all_notepads():
    """Vide tous les notepads de la base de données"""
    
    print("🗑️  Nettoyage de la table conversation_notepad...")
    
    notepad_manager = get_supabase_notepad()
    
    # Méthode 1: Via l'API Supabase
    try:
        from core.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # Compter avant
        count_before = supabase.table('conversation_notepad').select('id', count='exact').execute()
        print(f"📊 Nombre de notepads avant: {count_before.count}")
        
        # Supprimer tous
        result = supabase.table('conversation_notepad').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        
        # Compter après
        count_after = supabase.table('conversation_notepad').select('id', count='exact').execute()
        print(f"📊 Nombre de notepads après: {count_after.count}")
        
        print(f"✅ Nettoyage terminé ! {count_before.count - count_after.count} notepad(s) supprimé(s)")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print("\n💡 Alternative: Exécutez cette requête SQL dans Supabase Dashboard:")
        print("   DELETE FROM public.conversation_notepad;")

if __name__ == "__main__":
    asyncio.run(clear_all_notepads())

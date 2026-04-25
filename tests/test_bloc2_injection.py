import asyncio
import sys
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Ajouter le chemin du projet pour l'import
sys.path.append(os.getcwd())

async def test_bloc2_injection():
    print("🧪 TEST BLOC 2 : Injection Sécurisée (Safe Replace)\n")
    
    from core.simplified_prompt_system import prompt_system
    
    company_id = "W27PwOPiblP8TlOrhPcjOtxd0cza"
    user_id = "test_user_bloc2"
    query = "Bonjour Jessica, je veux commander."
    
    print("--- DÉBUT DE GÉNÉRATION ---")
    try:
        # On appelle build_prompt qui va déclencher le CompanyCacheManager (Bloc 1)
        # et le Safe Replace (Bloc 2)
        prompt = await prompt_system.build_prompt(
            user_id=user_id,
            company_id=company_id,
            query=query,
            conversation_history_s="Client: Bonjour\nJessica: Bonjour !"
        )
        
        # Vérifications
        print("\n--- ANALYSE DU RÉSULTAT ---")
        
        # 1. Vérifier si les variables sont injectées
        if "rue du grossiste" in prompt.lower():
            print("✅ Variable {shop_name} injectée avec succès.")
        else:
            print("❌ Variable {shop_name} manquante.")
            
        if "0160924560" in prompt:
            print("✅ Variable {whatsapp_number} injectée avec succès.")
        else:
            print("❌ Variable {whatsapp_number} manquante.")

        # 2. Vérifier si les accolades JSON sont préservées (pas de crash)
        if '<status_slots>' in prompt and 'SLOT_NAME' in prompt:
            print("✅ Structure XML/JSON préservée sans crash.")
        else:
            print("❌ La structure XML/JSON semble avoir été altérée ou est absente.")
            
        print("\n--- EXTRAIT DU PROMPT GÉNÉRÉ (Fin) ---")
        # On affiche juste la fin pour voir les injections de support
        print(prompt[-300:])
        
    except Exception as e:
        import traceback
        print(f"💥 CRASH DÉTECTÉ : {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bloc2_injection())

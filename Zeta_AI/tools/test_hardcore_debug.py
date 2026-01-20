#!/usr/bin/env python3
"""
🔥 TEST HARDCORE - MODE DEBUG COMPLET
Affiche TOUT pour analyse manuelle:
- Documents envoyés au LLM
- Question client
- Thinking LLM
- Réponse LLM
- État du bloc-note
"""

import asyncio
import sys
import os
import re
from datetime import datetime

# Ajouter le répertoire parent au PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 🎯 SCÉNARIO DE TEST RÉALISTE
TEST_SCENARIO = [
    "couches",
    "culottes", 
    "lot 150",
    "taille 5",
    "Cocody",
    "total avec livraison",
    "0787360757",
    "oui je confirme"
]

async def run_debug_test():
    """Lance le test avec affichage complet"""
    print("="*100)
    print("🔥 TEST HARDCORE - MODE DEBUG COMPLET")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 {len(TEST_SCENARIO)} échanges")
    print("="*100)
    print()
    
    # Désactiver TOUS les logs verbeux
    import logging
    logging.basicConfig(level=logging.CRITICAL)
    for logger_name in logging.root.manager.loggerDict:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)
    
    # Supprimer aussi les prints du système
    import warnings
    warnings.filterwarnings("ignore")
    
    from core.universal_rag_engine import UniversalRAGEngine
    from core.conversation_notepad import get_conversation_notepad
    
    rag = UniversalRAGEngine()
    notepad = get_conversation_notepad()
    
    # Paramètres
    COMPANY_ID = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"
    COMPANY_NAME = "Rue_du_gros"
    USER_ID = "test_hardcore_debug_001"
    
    for i, user_message in enumerate(TEST_SCENARIO, 1):
        print("\n" + "="*100)
        print(f"🔥 ÉCHANGE {i}/{len(TEST_SCENARIO)}")
        print("="*100)
        print(f"👤 CLIENT: {user_message}")
        print()
        
        try:
            # Recherche
            search_results = await rag.search_sequential_sources(user_message, COMPANY_ID)
            search_results['conversation_history'] = user_message if 'conversation_history' not in search_results else search_results['conversation_history']
            
            # Afficher les documents trouvés (VERSION COMPACTE)
            print("📄 DOCUMENTS:")
            print("-"*100)
            if 'structured_context' in search_results and search_results['structured_context']:
                context = search_results['structured_context']
                if isinstance(context, str):
                    # Extraire uniquement les titres des documents
                    doc_titles = re.findall(r'PRODUIT:\s*([^\n]+)', context)
                    if doc_titles:
                        for i, title in enumerate(doc_titles[:3], 1):
                            print(f"  {i}. {title.strip()}")
                    else:
                        # Fallback: afficher les 200 premiers chars
                        print(f"  {context[:200]}...")
                else:
                    print(f"  {str(context)[:200]}...")
            else:
                print("  ❌ Aucun")
            print("-"*100)
            print()
            
            # Génération
            response = await rag.generate_response(
                user_message, search_results, COMPANY_ID, COMPANY_NAME, USER_ID
            )
            
            # Récupérer thinking et response
            thinking = getattr(rag, '_last_thinking', "")
            full_response = getattr(rag, '_last_full_response', response)
            
            # Fallback: extraction manuelle
            if not thinking and "<thinking>" in full_response:
                thinking_match = re.search(r'<thinking>(.*?)</thinking>', full_response, re.DOTALL | re.IGNORECASE)
                if thinking_match:
                    thinking = thinking_match.group(1).strip()
            
            # Afficher le thinking (VERSION COMPACTE)
            print("🧠 THINKING:")
            print("-"*100)
            if thinking:
                # Extraire uniquement les actions importantes
                actions = re.findall(r'Action\s*:\s*([^\n]+)', thinking)
                if actions:
                    for action in actions[:5]:  # Max 5 actions
                        print(f"  • {action.strip()}")
                else:
                    # Afficher les 300 premiers chars
                    print(f"  {thinking[:300]}...")
            else:
                print("  ❌ Aucun")
            print("-"*100)
            print()
            
            # Afficher la réponse
            print("💬 RÉPONSE LLM:")
            print("-"*100)
            print(response)
            print("-"*100)
            print()
            
            # Afficher l'état du bloc-note (VERSION COMPACTE)
            print("📋 BLOC-NOTE:")
            try:
                # Essayer différentes méthodes selon la version du notepad
                if hasattr(notepad, 'get_all_info'):
                    notepad_data = notepad.get_all_info(USER_ID, COMPANY_ID)
                elif hasattr(notepad, 'get_context'):
                    notepad_data = notepad.get_context(USER_ID, COMPANY_ID)
                elif hasattr(notepad, 'display_all'):
                    notepad_data = notepad.display_all(USER_ID, COMPANY_ID)
                else:
                    notepad_data = None
                
                if notepad_data and isinstance(notepad_data, dict):
                    items = [f"{k}={v}" for k, v in list(notepad_data.items())[:5]]
                    print("  " + " | ".join(items) if items else "  ⚠️ Vide")
                else:
                    print("  ⚠️ Vide ou inaccessible")
            except Exception as e:
                print(f"  ❌ Erreur: {e}")
            print()
            
            # Analyse rapide (VERSION COMPACTE)
            print("🔍 OUTILS:")
            tools_used = []
            
            if thinking:
                if "Bloc-note: ajouter info" in thinking:
                    matches = re.findall(r'Bloc-note:\s*ajouter\s+info\s*\(\s*([^,\)]+?)\s*,\s*"([^"]+)"\)', thinking)
                    if matches:
                        tools_used.append(f"✅ Bloc-note ({len(matches)} ajouts)")
                    else:
                        tools_used.append("⚠️ Bloc-note (mention sans extraction)")
                
                if "Bloc-note: tout afficher" in thinking:
                    tools_used.append("✅ Consultation bloc-note")
                
                if "Calculatrice" in thinking:
                    tools_used.append("✅ Calculatrice")
            
            if tools_used:
                print("  " + " | ".join(tools_used))
            else:
                print("  ❌ Aucun outil utilisé")
            print()
            
            # Pause pour lisibilité
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"❌ ERREUR: {e}")
            import traceback
            traceback.print_exc()
            break
    
    print("\n" + "="*100)
    print("✅ TEST TERMINÉ")
    print("="*100)

if __name__ == "__main__":
    asyncio.run(run_debug_test())

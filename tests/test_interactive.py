#!/usr/bin/env python3
"""
TEST INTERACTIF MANUEL
Permet de tester le chatbot en mode conversationnel réel
avec logging détaillé de TOUS les contextes
"""
import httpx
import asyncio
import json
import uuid
from datetime import datetime
import os

# Configuration
API_URL = "http://127.0.0.1:8002/chat"
COMPANY_ID = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"
USER_ID = f"test_interactive_{uuid.uuid4().hex[:8]}"

# Historique conversation
conversation_history = []

def print_separator(char="=", length=80):
    print(char * length)

def save_conversation_log():
    """Sauvegarde la conversation complète avec tous les contextes"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = f"tests/reports/INTERACTIVE_{timestamp}.json"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    report = {
        "test_type": "interactive_manual",
        "user_id": USER_ID,
        "timestamp": datetime.now().isoformat(),
        "total_turns": len(conversation_history),
        "conversation": conversation_history
    }
    
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Conversation sauvegardée: {log_path}")
    return log_path

async def send_message(message: str):
    """Envoie un message et affiche la réponse avec TOUS les contextes"""
    payload = {
        "company_id": COMPANY_ID,
        "user_id": USER_ID,
        "message": message,
        "botlive_enabled": False
    }
    
    print(f"\n{'='*80}")
    print(f"👤 VOUS: {message}")
    print(f"{'='*80}")
    print("⏳ Envoi en cours...")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(API_URL, json=payload)
            result = response.json()
        
        # Extraction données
        assistant_response = result.get("response", "")
        thinking = result.get("thinking", "")
        debug_contexts = result.get("debug_contexts", {})
        
        # Affichage réponse
        print(f"\n🤖 ASSISTANT:")
        print(f"{assistant_response}")
        
        # Affichage thinking
        if thinking:
            print(f"\n🧠 THINKING ({len(thinking)} chars):")
            print("─" * 80)
            print(thinking)
            print("─" * 80)
        else:
            print(f"\n⚠️ THINKING: VIDE")
        
        # Affichage contextes système
        print(f"\n📊 CONTEXTES SYSTÈME:")
        print("─" * 80)
        
        # 1. State Tracker
        state = debug_contexts.get("state_tracker", {})
        if "error" not in state:
            print(f"✅ STATE TRACKER:")
            print(f"   Complétude: {state.get('completion_rate', 0):.0%}")
            print(f"   Manquants: {state.get('missing_fields', [])}")
            collected = state.get('collected_data', {})
            for key, value in collected.items():
                if value:
                    print(f"   ✓ {key}: {value}")
        else:
            print(f"❌ STATE TRACKER: {state.get('error')}")
        
        # 2. Notepad
        notepad = debug_contexts.get("notepad", {})
        if "error" not in notepad:
            content = notepad.get("content", "")
            if content:
                print(f"\n✅ NOTEPAD ({notepad.get('length', 0)} chars):")
                print(f"   {content[:200]}...")
            else:
                print(f"\n⚠️ NOTEPAD: Vide")
        
        # 3. Thinking Parsed
        thinking_parsed = debug_contexts.get("thinking_parsed", {})
        if "error" not in thinking_parsed:
            phase2 = thinking_parsed.get("phase2_collected", {})
            phase5 = thinking_parsed.get("phase5_decision", {})
            completeness = thinking_parsed.get("completeness", "unknown")
            
            print(f"\n✅ THINKING PARSED:")
            print(f"   Complétude: {completeness}")
            if phase2:
                deja_collecte = phase2.get("deja_collecte", {})
                print(f"   Déjà collecté:")
                for key, value in deja_collecte.items():
                    status = "✓" if value else "✗"
                    print(f"      {status} {key}: {value}")
        
        # 4. Anti-hallucination
        anti_hallu = debug_contexts.get("anti_hallucination", {})
        if "error" not in anti_hallu:
            print(f"\n✅ ANTI-HALLUCINATION:")
            print(f"   Confiance: {anti_hallu.get('confidence_score', 0):.2f}")
            print(f"   Grounded: {anti_hallu.get('is_grounded', False)}")
        
        # 5. Security
        security = debug_contexts.get("security", {})
        if "error" not in security:
            print(f"\n✅ SECURITY:")
            print(f"   Risk: {security.get('risk_level', 'UNKNOWN')}")
            print(f"   Safe: {security.get('is_safe', False)}")
        
        print("─" * 80)
        
        # Sauvegarde dans historique
        turn_data = {
            "turn": len(conversation_history) + 1,
            "user_message": message,
            "assistant_response": assistant_response,
            "thinking": thinking,
            "thinking_length": len(thinking),
            "debug_contexts": debug_contexts,
            "full_result": result
        }
        conversation_history.append(turn_data)
        
        # Analyse rapide
        print(f"\n📈 ANALYSE RAPIDE:")
        if thinking:
            if "paiement: \"paid\"" in thinking and "VALIDÉ ✅" not in str(debug_contexts):
                print("   🚨 ALERTE: paiement='paid' SANS validation OCR !")
            if "lot 300" in thinking:
                print("   ⚠️ WARNING: type_produit trop vague ('lot 300')")
            if "completude: \"5/5\"" in thinking and "paiement: \"paid\"" not in thinking:
                print("   🚨 ALERTE: completude=5/5 SANS paiement validé !")
        
        return result
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        return None

async def interactive_test():
    """Boucle interactive"""
    print("="*80)
    print("🧪 TEST INTERACTIF MANUEL")
    print("="*80)
    print(f"User ID: {USER_ID}")
    print(f"API: {API_URL}")
    print("\nCommandes:")
    print("  - Tapez votre message pour converser")
    print("  - 'quit' ou 'exit' pour terminer")
    print("  - 'save' pour sauvegarder sans quitter")
    print("="*80)
    
    while True:
        try:
            # Input utilisateur
            user_input = input("\n👤 VOUS: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n🛑 Fin du test...")
                break
            
            if user_input.lower() == 'save':
                save_conversation_log()
                continue
            
            # Envoi message
            await send_message(user_input)
            
        except KeyboardInterrupt:
            print("\n\n🛑 Interruption clavier...")
            break
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
    
    # Sauvegarde finale
    if conversation_history:
        log_path = save_conversation_log()
        print(f"\n✅ {len(conversation_history)} tours sauvegardés")
        print(f"📄 Rapport: {log_path}")
    
    print("\n✅ Test terminé!")

if __name__ == "__main__":
    asyncio.run(interactive_test())

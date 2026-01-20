#!/usr/bin/env python3
"""
Test LITE pour OptimizedConversationMemory et UniversalConversationSynthesis
5 échanges rapides pour vérifier si les erreurs strip() persistent
ARRÊT AUTOMATIQUE à la première erreur + vérification des fichiers
"""

import asyncio
import sys
import os
import hashlib
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.optimized_conversation_memory import OptimizedConversationMemory
from core.universal_conversation_synthesis import UniversalConversationSynthesis
from core.llm_client import GroqLLMClient

def get_file_hash(filepath):
    """Calculer le hash MD5 d'un fichier"""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        return f"ERROR: {e}"

def get_file_info(filepath):
    """Obtenir les infos d'un fichier"""
    try:
        stat = os.stat(filepath)
        return {
            'exists': True,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'hash': get_file_hash(filepath)
        }
    except FileNotFoundError:
        return {'exists': False}
    except Exception as e:
        return {'exists': True, 'error': str(e)}

def compare_files():
    """Comparer les fichiers Windows vs Ubuntu"""
    print("\n" + "=" * 80)
    print("🔍 VÉRIFICATION SYNCHRONISATION FICHIERS")
    print("=" * 80)
    
    files_to_check = [
        "core/optimized_conversation_memory.py",
        "core/universal_conversation_synthesis.py",
        "core/enhanced_memory.py",
        "core/botlive_tools.py"
    ]
    
    windows_base = "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0"
    ubuntu_base = os.path.expanduser("~/ZETA_APP/CHATBOT2.0")
    
    all_synced = True
    
    for file_path in files_to_check:
        print(f"\n📄 {file_path}")
        print("-" * 80)
        
        win_path = os.path.join(windows_base, file_path)
        ubuntu_path = os.path.join(ubuntu_base, file_path)
        
        win_info = get_file_info(win_path)
        ubuntu_info = get_file_info(ubuntu_path)
        
        if not win_info.get('exists'):
            print(f"   ❌ Windows: FICHIER INTROUVABLE")
            all_synced = False
            continue
            
        if not ubuntu_info.get('exists'):
            print(f"   ❌ Ubuntu: FICHIER INTROUVABLE")
            all_synced = False
            continue
        
        print(f"   Windows:  {win_info['modified']} | {win_info['size']:,} bytes | {win_info['hash'][:8]}...")
        print(f"   Ubuntu:   {ubuntu_info['modified']} | {ubuntu_info['size']:,} bytes | {ubuntu_info['hash'][:8]}...")
        
        if win_info['hash'] == ubuntu_info['hash']:
            print(f"   ✅ SYNCHRONISÉ (hash identique)")
        else:
            print(f"   ❌ DÉSYNCHRONISÉ (hash différent)")
            all_synced = False
    
    print("\n" + "=" * 80)
    if all_synced:
        print("✅ TOUS LES FICHIERS SONT SYNCHRONISÉS")
    else:
        print("❌ CERTAINS FICHIERS NE SONT PAS SYNCHRONISÉS")
        print("\n🔧 COMMANDES DE SYNCHRONISATION:")
        for file_path in files_to_check:
            print(f"cp '{windows_base}/{file_path}' {ubuntu_base}/{file_path}")
    print("=" * 80)
    
    return all_synced

async def test_memory_modules():
    """Test direct des modules de mémoire"""
    
    print("=" * 80)
    print("🧪 TEST MÉMOIRE CONVERSATIONNELLE - 5 ÉCHANGES")
    print("=" * 80)
    print()
    
    # Initialiser LLM
    llm_client = GroqLLMClient()
    
    # Identifiants de test
    user_id = "test_memory_001"
    company_id = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"
    
    # Initialiser les modules (sans user_id/company_id dans constructeur)
    memory = OptimizedConversationMemory(
        max_recent_messages=5,
        synthesis_threshold=8
    )
    
    synthesis = UniversalConversationSynthesis(
        max_recent_exchanges=5,
        synthesis_threshold=10
    )
    
    # Messages de test
    test_messages = [
        ("user", "lot 150"),
        ("assistant", "📦 Produit : lot 150 à 13 500 FCFA. Quelle est votre commune ?"),
        ("user", "Cocody"),
        ("assistant", "🚚 Livraison Cocody : 1 500 FCFA. Votre numéro de téléphone ?"),
        ("user", "0160924560"),
    ]
    
    last_user_msg = ""  # Pour stocker le dernier message user
    
    for i, (role, content) in enumerate(test_messages, 1):
        print(f"\n{'=' * 80}")
        print(f"🔥 ÉCHANGE {i}/5 - {role.upper()}")
        print(f"{'=' * 80}")
        print(f"💬 Message: {content}")
        
        try:
            # Ajouter le message utilisateur (teste le code avec strip())
            if role == "user":
                print(f"🧠 Ajout message utilisateur + extraction intention...")
                mem = await memory.add_user_message(user_id, company_id, content, llm_client)
                print(f"✅ Message ajouté - Intention: {mem.recent_user_messages[-1].extracted_intent}")
                # Stocker le message user pour l'échange
                last_user_msg = content
            else:
                # Message assistant - créer l'échange complet
                print(f"📝 Ajout échange complet (user + assistant)...")
                synth = await synthesis.add_exchange(user_id, company_id, last_user_msg, content, llm_client)
                summary = synth.current_summary if synth.current_summary else "Pas encore de synthèse"
                print(f"✅ Synthèse: {summary[:100]}..." if len(summary) > 100 else f"✅ Synthèse: {summary}")
            
        except AttributeError as e:
            if "'dict' object has no attribute 'strip'" in str(e):
                print(f"\n{'🚨' * 40}")
                print(f"❌ ERREUR CRITIQUE DÉTECTÉE à l'échange {i}")
                print(f"{'🚨' * 40}")
                print(f"\n💥 Erreur: {e}")
                print(f"\n🛑 ARRÊT IMMÉDIAT DU TEST")
                
                # Vérifier immédiatement les fichiers
                compare_files()
                return False
            else:
                raise
        except Exception as e:
            print(f"\n{'🚨' * 40}")
            print(f"❌ ERREUR INATTENDUE à l'échange {i}")
            print(f"{'🚨' * 40}")
            print(f"\n💥 Erreur: {e}")
            print(f"\n🛑 ARRÊT IMMÉDIAT DU TEST")
            
            # Vérifier immédiatement les fichiers
            compare_files()
            return False
    
    # Si on arrive ici, tous les échanges ont réussi
    print(f"\n{'=' * 80}")
    print("📊 RAPPORT FINAL - TOUS LES ÉCHANGES RÉUSSIS")
    print(f"{'=' * 80}")
    print("✅ SUCCÈS: Aucune erreur détectée sur les 5 échanges!")
    print("✅ Les modules de mémoire fonctionnent correctement.")
    
    # Vérifier quand même les fichiers pour confirmation
    print("\n🔍 Vérification finale de la synchronisation...")
    files_synced = compare_files()
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_memory_modules())
    sys.exit(0 if success else 1)

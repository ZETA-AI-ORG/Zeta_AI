#!/usr/bin/env python3
"""
🔍 DEBUG STRUCTURE RÉELLE DU PATCH #2
====================================

Script pour capturer la vraie structure de données qui arrive
au PATCH #2 dans le test réel vs notre test direct.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.loop_botlive_engine import LoopBotliveEngine
import logging
import json

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def patch_check_completion_to_debug():
    """Patch la fonction _check_completion pour capturer la structure réelle"""
    
    # Sauvegarder la fonction originale
    original_check_completion = LoopBotliveEngine._check_completion
    
    def debug_check_completion(self, state):
        """Version debug qui capture la structure"""
        print("\n" + "="*60)
        print("🔍 DEBUG: STRUCTURE RÉELLE REÇUE PAR _check_completion()")
        print("="*60)
        
        # Sauvegarder la structure dans un fichier
        debug_file = "tests/logs/debug_real_structure.json"
        os.makedirs(os.path.dirname(debug_file), exist_ok=True)
        
        with open(debug_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": "2025-11-12T12:10:00",
                "state_keys": list(state.keys()),
                "state_structure": state,
                "analysis": {
                    "photo_key_exists": "photo" in state,
                    "photo_structure": state.get("photo", "KEY_NOT_FOUND"),
                    "paiement_key_exists": "paiement" in state,
                    "paiement_structure": state.get("paiement", "KEY_NOT_FOUND"),
                    "zone_key_exists": "zone" in state,
                    "zone_structure": state.get("zone", "KEY_NOT_FOUND"),
                    "tel_key_exists": "tel" in state,
                    "tel_structure": state.get("tel", "KEY_NOT_FOUND"),
                    
                    # Vérifier les autres clés possibles
                    "other_photo_keys": [k for k in state.keys() if "photo" in k.lower()],
                    "other_payment_keys": [k for k in state.keys() if "paiement" in k.lower() or "payment" in k.lower()],
                    "other_zone_keys": [k for k in state.keys() if "zone" in k.lower() or "delivery" in k.lower()],
                    "other_tel_keys": [k for k in state.keys() if "tel" in k.lower() or "phone" in k.lower()]
                }
            }, f, indent=2, ensure_ascii=False)
        
        print(f"📁 Structure sauvegardée dans: {debug_file}")
        
        # Afficher un résumé
        print(f"🔑 Clés disponibles: {list(state.keys())}")
        print(f"📸 Photo key exists: {'photo' in state}")
        print(f"💳 Paiement key exists: {'paiement' in state}")
        print(f"📍 Zone key exists: {'zone' in state}")
        print(f"📞 Tel key exists: {'tel' in state}")
        
        # Appeler la fonction originale
        result = original_check_completion(self, state)
        
        print(f"🎯 Résultat _check_completion: {result}")
        print("="*60)
        
        return result
    
    # Remplacer la fonction
    LoopBotliveEngine._check_completion = debug_check_completion
    print("✅ Fonction _check_completion patchée pour debug")

if __name__ == "__main__":
    print("🔧 PATCH DE DEBUG APPLIQUÉ")
    print("Maintenant, lancez le test réel :")
    print("python tests/botlive_client_direct.py")
    print("\nLa structure réelle sera capturée dans tests/logs/debug_real_structure.json")
    
    # Appliquer le patch
    patch_check_completion_to_debug()
    
    print("\n⚠️ IMPORTANT: Ce script ne fait que patcher la fonction.")
    print("Vous devez maintenant lancer le test réel dans un autre terminal.")

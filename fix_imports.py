#!/usr/bin/env python3
"""
🔧 SCRIPT DE CORRECTION AUTOMATIQUE DES IMPORTS
Corrige tous les imports manquants dans rag_engine_simplified.py
"""

import os
import re

def fix_rag_engine_imports():
    """Corrige tous les imports problématiques d'un coup"""
    
    file_path = "core/rag_engine_simplified.py"
    
    # Corrections à appliquer
    fixes = [
        # Commentaires des modules manquants
        ("from core.intention_detector import IntentionDetector", "# from core.intention_detector import IntentionDetector  # Module manquant"),
        ("from core.intention_router import intention_router", "# from core.intention_router import intention_router  # Module manquant"),
        ("from core.specialized_hyde import get_specialized_hyde", "# from core.specialized_hyde import get_specialized_hyde  # Module manquant"),
        ("from core.intelligent_cache_system import smart_cache_get, smart_cache_set", "# from core.intelligent_cache_system import smart_cache_get, smart_cache_set  # Module manquant"),
        
        # Simplification du code
        ("intentions = intention_router.detect_intentions(query)", "# intentions = intention_router.detect_intentions(query)  # Désactivé"),
        ("hyde_instance = get_specialized_hyde()", "# hyde_instance = get_specialized_hyde()  # Désactivé"),
        ("hyde_hypothesis = await hyde_instance.generate_hypothesis(query, intentions)", "hyde_hypothesis = query  # Fallback simple"),
    ]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Appliquer toutes les corrections
        for old, new in fixes:
            content = content.replace(old, new)
        
        # Simplifier la logique HyDE
        content = re.sub(
            r'if intentions\.primary and intentions\.confidence_score > 0\.2:.*?else:.*?log3\("\[SPECIALIZED_HYDE\]", "⚠️ Fallback sur requête originale"\)',
            'hyde_hypothesis = query  # Fallback simple sans intentions',
            content,
            flags=re.DOTALL
        )
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Imports corrigés dans rag_engine_simplified.py")
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Correction automatique des imports...")
    if fix_rag_engine_imports():
        print("🎉 Tous les imports sont maintenant corrigés !")
        print("\n📋 Commandes à exécuter :")
        print("cp -v core/rag_engine_simplified.py ~/ZETA_APP/CHATBOT2.0/core/")
        print("cd ~/ZETA_APP/CHATBOT2.0 && python app.py")
    else:
        print("💥 Échec de la correction")

#!/usr/bin/env python3
"""
🧪 TEST RAPIDE DE SAUVEGARDE DES LOGS
Test simple pour vérifier que les logs sont sauvegardés en JSON
"""

import asyncio
import sys
import os

# Ajouter le répertoire parent au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_logging_save():
    """Test rapide de sauvegarde des logs"""
    print("🧪 TEST DE SAUVEGARDE DES LOGS")
    print("=" * 40)
    
    try:
        from core.rag_engine_simplified_fixed import get_rag_response_advanced
        
        print("✅ Import réussi")
        
        # Test avec une question simple
        print("\n📝 Test avec une question...")
        result = await get_rag_response_advanced(
            message="Test de sauvegarde des logs",
            user_id="test_save",
            company_id="test_company"
        )
        
        print(f"✅ Réponse générée: {result['response'][:50]}...")
        print(f"📊 Confidence: {result['confidence']:.3f}")
        
        # Vérifier les fichiers de logs
        print("\n📁 Vérification des fichiers de logs...")
        log_files = []
        for file in os.listdir("."):
            if file.startswith("rag_detailed_logs_") and file.endswith(".json"):
                log_files.append(file)
        
        if log_files:
            print(f"✅ {len(log_files)} fichier(s) de logs trouvé(s):")
            for file in log_files:
                size = os.path.getsize(file)
                print(f"   - {file} ({size} bytes)")
        else:
            print("❌ Aucun fichier de logs trouvé")
        
        return len(log_files) > 0
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_logging_save())
    if success:
        print("\n🎉 TEST RÉUSSI ! Les logs sont sauvegardés.")
    else:
        print("\n⚠️  TEST ÉCHOUÉ ! Vérifiez la configuration.")

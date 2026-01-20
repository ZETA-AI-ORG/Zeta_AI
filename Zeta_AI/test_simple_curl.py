#!/usr/bin/env python3
"""
🧪 TEST SIMPLE CURL - VÉRIFICATION FORMAT 422
Script de test simple pour vérifier que le format curl est correct
"""

import subprocess
import json
import time
from datetime import datetime

# Configuration du test
API_URL = "http://127.0.0.1:8001/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
USER_ID = "testuser124"

def test_simple_curl():
    """Test simple avec curl pour éviter l'erreur 422"""
    
    print("🧪 TEST SIMPLE CURL - VÉRIFICATION FORMAT 422")
    print("=" * 60)
    print(f"🕐 Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 URL API: {API_URL}")
    print(f"🏢 Company ID: {COMPANY_ID}")
    print(f"👤 User ID: {USER_ID}")
    print()
    
    # Test simple
    test_message = "Bonsoir mme ou mr desole du derangement je sais qu il se fait tard mais j aimerais savoir quel taille de couches conviendrait a mon bebe de 5 mois qui fais 17kg et aussi combien fera la livraison a Cocody svp? merci de bien vouloir me repondre."
    
    print(f"📤 Message de test:")
    print(f"💬 {test_message}")
    print("-" * 60)
    
    try:
        # Échapper les guillemets dans le message pour curl
        escaped_message = test_message.replace('"', '\\"')
        
        # Construire la commande curl exactement comme dans l'exemple
        curl_cmd = [
            "curl", "-X", "POST", API_URL,
            "-H", "Content-Type: application/json",
            "-d", f'{{"message":"{escaped_message}","company_id":"{COMPANY_ID}","user_id":"{USER_ID}"}}'
        ]
        
        print(f"🔧 Commande curl:")
        print(f"   {' '.join(curl_cmd)}")
        print("-" * 60)
        
        start_time = time.time()
        result = subprocess.run(
            curl_cmd, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"⏱️ Temps d'exécution: {elapsed_time:.2f}s")
        print(f"🔢 Code de retour: {result.returncode}")
        
        if result.returncode == 0:
            print(f"✅ SUCCÈS - Pas d'erreur 422!")
            print(f"📝 Réponse brute:")
            print(f"   {result.stdout}")
            
            try:
                data = json.loads(result.stdout)
                print(f"\n📊 Données JSON parsées:")
                print(f"   • Response: {data.get('response', '')[:100]}...")
                print(f"   • Cached: {data.get('cached', False)}")
                print(f"   • Price calculated: {data.get('price_calculated', False)}")
                print(f"   • Memory data: {'Oui' if data.get('memory_data') else 'Non'}")
                
                if data.get('price_calculated') and data.get('price_info'):
                    price_info = data['price_info']
                    print(f"   • Prix total: {price_info.get('total', 0):,.0f} FCFA")
                    print(f"   • Produits: {len(price_info.get('products', []))}")
                
                if data.get('memory_data'):
                    memory_data = data['memory_data']
                    conversation_summary = memory_data.get('conversation_summary', {})
                    completeness = conversation_summary.get('completeness_percentage', 0)
                    print(f"   • Complétude conversation: {completeness:.1f}%")
                
            except json.JSONDecodeError as e:
                print(f"⚠️ Erreur parsing JSON: {e}")
                print(f"   Raw output: {result.stdout}")
        else:
            print(f"❌ ERREUR - Code de retour: {result.returncode}")
            print(f"📝 Stderr: {result.stderr}")
            print(f"📝 Stdout: {result.stdout}")
            
    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT: La requête a pris plus de 30 secondes")
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
    
    print(f"\n🎉 TEST TERMINÉ!")
    print(f"💡 Si vous voyez 'SUCCÈS', le format curl est correct!")

if __name__ == "__main__":
    test_simple_curl()



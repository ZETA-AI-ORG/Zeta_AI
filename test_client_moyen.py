#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 TEST CLIENT MOYEN - Rue du Grossiste
Scénario: Client qui se renseigne, hésite un peu, puis commande
Objectif: Tester la capacité du RAG à guider vers l'achat
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:8002"
COMPANY_ID = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"

def print_section(title):
    """Affiche un titre de section"""
    print("\n" + "="*80)
    print(f"🧪 {title}")
    print("="*80)

def send_message(user_id, message):
    """Envoie un message au chatbot"""
    url = f"{BASE_URL}/chat"
    payload = {
        "message": message,
        "company_id": COMPANY_ID,
        "user_id": user_id
    }
    
    print(f"\n👤 CLIENT: {message}")
    start = time.time()
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            
            # Extraction robuste de la réponse
            response_data = data.get('response', {})
            if isinstance(response_data, dict):
                answer_text = response_data.get('response', 'Pas de réponse')
            else:
                answer_text = str(response_data)
            
            print(f"⏱️  Temps: {elapsed:.2f}s")
            print(f"🤖 ASSISTANT: {answer_text}")
            
            return {
                'response': answer_text,
                'raw_data': data,
                'success': True,
                'time': elapsed
            }
        else:
            print(f"❌ Erreur HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def test_client_moyen():
    """
    Scénario CLIENT MOYEN:
    1. Salutation et question générale
    2. Demande de prix (hésite entre tailles)
    3. Question sur livraison
    4. Demande de conseil
    5. Décision d'achat
    6. Question sur paiement
    7. Confirmation commande
    8. Demande récapitulatif
    """
    
    print_section("TEST CLIENT MOYEN - PARCOURS D'ACHAT CLASSIQUE")
    
    user_id = f"client_moyen_{datetime.now().strftime('%H%M%S')}"
    
    conversation = [
        # 1. Salutation
        "Bonjour, je cherche des couches pour mon bébé",
        
        # 2. Hésitation entre tailles
        "Mon bébé fait 8kg, c'est quelle taille ? Taille 3 ou 4 ?",
        
        # 3. Demande prix
        "Ok taille 4. C'est combien le lot de 300 ?",
        
        # 4. Comparaison
        "Et le lot de 150 c'est moins cher au final ?",
        
        # 5. Question livraison
        "Je suis à Cocody, vous livrez ?",
        
        # 6. Demande conseil
        "Vous me conseillez quoi pour un bébé de 8kg qui bouge beaucoup ?",
        
        # 7. Décision
        "Ok je prends 2 lots de 300 couches taille 4",
        
        # 8. Question paiement
        "Comment je paye ?",
        
        # 9. Confirmation
        "Ok je vais payer par Wave. Mon numéro c'est 0707123456",
        
        # 10. Récapitulatif
        "Vous pouvez me récapituler ma commande ?"
    ]
    
    results = {
        'total_messages': len(conversation),
        'successful': 0,
        'failed': 0,
        'total_time': 0,
        'responses': []
    }
    
    for i, message in enumerate(conversation, 1):
        print(f"\n{'─'*80}")
        print(f"📍 ÉTAPE {i}/{len(conversation)}")
        
        response = send_message(user_id, message)
        
        if response:
            results['successful'] += 1
            results['total_time'] += response['time']
            results['responses'].append({
                'step': i,
                'message': message,
                'response': response['response'],
                'time': response['time']
            })
        else:
            results['failed'] += 1
        
        # Pause entre messages (simule réflexion client)
        time.sleep(2)
    
    # Analyse finale
    print_section("RÉSULTATS CLIENT MOYEN")
    
    print(f"\n📊 STATISTIQUES:")
    print(f"  ├─ Messages envoyés: {results['total_messages']}")
    print(f"  ├─ Réussites: {results['successful']}")
    print(f"  ├─ Échecs: {results['failed']}")
    print(f"  ├─ Temps total: {results['total_time']:.2f}s")
    print(f"  └─ Temps moyen: {results['total_time']/results['successful']:.2f}s")
    
    # Analyse qualitative
    print(f"\n🎯 ANALYSE QUALITATIVE:")
    
    # Vérifier si le RAG a guidé vers l'achat
    final_response = results['responses'][-1]['response'].lower() if results['responses'] else ""
    
    checks = {
        "A mentionné le produit": any("couches" in r['response'].lower() for r in results['responses']),
        "A donné le prix": any("24 000" in r['response'] or "24000" in r['response'] for r in results['responses']),
        "A expliqué la livraison": any("cocody" in r['response'].lower() for r in results['responses']),
        "A guidé vers paiement": any("wave" in r['response'].lower() for r in results['responses']),
        "A fait un récapitulatif": "récap" in final_response or "total" in final_response,
        "A calculé le total": any("48 000" in r['response'] or "49 500" in r['response'] for r in results['responses'])
    }
    
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")
    
    score = sum(checks.values()) / len(checks) * 100
    print(f"\n🏆 SCORE FINAL: {score:.0f}%")
    
    if score >= 80:
        print("🎉 EXCELLENT - Le RAG guide efficacement vers l'achat!")
    elif score >= 60:
        print("👍 BON - Le RAG accompagne correctement le client")
    else:
        print("⚠️  INSUFFISANT - Le RAG a du mal à guider le client")
    
    return results

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🧪 TEST CLIENT MOYEN - RUE DU GROSSISTE                    ║
║                                                                                ║
║  Scénario: Client classique qui se renseigne et commande                      ║
║  Objectif: Vérifier que le RAG guide vers l'achat                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    results = test_client_moyen()
    
    print("\n" + "="*80)
    print("✅ Test terminé!")
    print("="*80)

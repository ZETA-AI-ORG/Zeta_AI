#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 TEST CLIENT HARDCORE - Rue du Grossiste
Scénario: Client difficile qui hésite, change d'avis, annule, revient
Objectif: Tester la résilience du RAG face à un client chaotique
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
    print(f"🔥 {title}")
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
        response = requests.post(url, json=payload, timeout=60)  # Augmenté à 60s pour test hardcore
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

def test_client_hardcore():
    """
    Scénario CLIENT HARDCORE:
    1. Question vague
    2. Change de sujet
    3. Demande prix mais hésite
    4. Change de taille 3 fois
    5. Demande livraison dans 3 zones différentes
    6. Veut commander
    7. Annule
    8. Revient et change encore
    9. Demande réduction
    10. Négocie
    11. Change de produit
    12. Revient au premier produit
    13. Demande paiement
    14. Hésite sur paiement
    15. Finalement commande
    16. Demande modification
    17. Confirme
    18. Demande récap
    """
    
    print_section("TEST CLIENT HARDCORE - PARCOURS CHAOTIQUE")
    
    user_id = f"client_hardcore_{datetime.now().strftime('%H%M%S')}"
    
    conversation = [
        # 1. Question vague
        "Salut",
        
        # 2. Question hors sujet
        "Vous vendez des jouets ?",
        
        # 3. Retour au sujet mais vague
        "Bon ok, des couches alors. Vous avez quoi ?",
        
        # 4. Hésite sur taille
        "Mon bébé fait 7kg... ou 8kg je sais plus. C'est quelle taille ?",
        
        # 5. Change d'avis sur taille
        "Attendez non, il fait 9kg. Donc taille 4 ou 5 ?",
        
        # 6. Demande prix mais hésite
        "Ok taille 4. Mais attendez, le lot de 150 ou 300 ?",
        
        # 7. Change encore
        "Non en fait taille 5. C'est combien ?",
        
        # 8. Demande livraison zone 1
        "Vous livrez à Yopougon ?",
        
        # 9. Change de zone
        "Ah non en fait je suis à Cocody",
        
        # 10. Encore une autre zone
        "Ou peut-être Port-Bouët, c'est moins cher ?",
        
        # 11. Veut commander
        "Bon ok je prends 3 lots taille 5 livraison Cocody",
        
        # 12. Annule
        "Attendez non, c'est trop cher. Vous faites pas de réduction ?",
        
        # 13. Négocie
        "Si je prends 5 lots vous me faites un prix ?",
        
        # 14. Change de produit
        "En fait je préfère des couches culottes. Vous avez ?",
        
        # 15. Revient au premier
        "Non laissez tomber, je reprends les couches à pression taille 4",
        
        # 16. Nouvelle quantité
        "Je prends 2 lots de 300",
        
        # 17. Demande paiement
        "Comment je paye ?",
        
        # 18. Hésite sur paiement
        "Wave ou Orange Money ?",
        
        # 19. Confirme
        "Ok Wave. Mon numéro c'est 0707999888",
        
        # 20. Veut modifier
        "Attendez, je peux changer la zone de livraison ? Je préfère Yopougon finalement",
        
        # 21. Confirme final
        "Ok c'est bon, je confirme tout",
        
        # 22. Demande récap
        "Récapitulez-moi tout ça, j'ai perdu le fil"
    ]
    
    results = {
        'total_messages': len(conversation),
        'successful': 0,
        'failed': 0,
        'total_time': 0,
        'responses': [],
        'confusion_detected': 0,
        'redirections': 0
    }
    
    for i, message in enumerate(conversation, 1):
        print(f"\n{'─'*80}")
        print(f"📍 ÉTAPE {i}/{len(conversation)}")
        
        response = send_message(user_id, message)
        
        if response:
            results['successful'] += 1
            results['total_time'] += response['time']
            
            # Détecter si le RAG reste focus
            response_lower = response['response'].lower()
            
            # Détecte confusion
            if any(word in response_lower for word in ['désolé', 'comprends pas', 'reformuler', 'préciser']):
                results['confusion_detected'] += 1
            
            # Détecte redirection vers achat
            if any(word in response_lower for word in ['commander', 'acheter', 'finaliser', 'confirmer', 'paiement']):
                results['redirections'] += 1
            
            results['responses'].append({
                'step': i,
                'message': message,
                'response': response['response'],
                'time': response['time']
            })
        else:
            results['failed'] += 1
        
        # Pause courte (client impatient)
        time.sleep(1.5)
    
    # Analyse finale
    print_section("RÉSULTATS CLIENT HARDCORE")
    
    print(f"\n📊 STATISTIQUES:")
    print(f"  ├─ Messages envoyés: {results['total_messages']}")
    print(f"  ├─ Réussites: {results['successful']}")
    print(f"  ├─ Échecs: {results['failed']}")
    print(f"  ├─ Temps total: {results['total_time']:.2f}s")
    print(f"  ├─ Temps moyen: {results['total_time']/results['successful']:.2f}s")
    print(f"  ├─ Confusions détectées: {results['confusion_detected']}")
    print(f"  └─ Redirections vers achat: {results['redirections']}")
    
    # Analyse qualitative HARDCORE
    print(f"\n🎯 ANALYSE RÉSILIENCE:")
    
    final_response = results['responses'][-1]['response'].lower() if results['responses'] else ""
    
    checks = {
        "A géré les changements de taille": any("taille" in r['response'].lower() for r in results['responses'][-5:]),
        "A géré les changements de zone": any("yopougon" in r['response'].lower() or "cocody" in r['response'].lower() for r in results['responses'][-5:]),
        "A maintenu le focus produit": results['confusion_detected'] < 3,
        "A redirigé vers achat": results['redirections'] >= 3,
        "A fait récapitulatif final": "récap" in final_response or "total" in final_response,
        "A gardé la mémoire": any("2 lots" in r['response'] or "48 000" in r['response'] for r in results['responses'][-3:]),
        "N'a pas abandonné": results['successful'] >= results['total_messages'] * 0.9,
        "Temps de réponse stable": results['total_time']/results['successful'] < 15
    }
    
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")
    
    score = sum(checks.values()) / len(checks) * 100
    print(f"\n🏆 SCORE RÉSILIENCE: {score:.0f}%")
    
    if score >= 80:
        print("🔥 EXCELLENT - Le RAG est ULTRA RÉSILIENT!")
        print("   Le système gère parfaitement les clients difficiles")
    elif score >= 60:
        print("💪 BON - Le RAG tient le coup face au chaos")
        print("   Quelques améliorations possibles mais solide")
    elif score >= 40:
        print("⚠️  MOYEN - Le RAG se perd parfois")
        print("   Besoin d'améliorer la gestion du contexte")
    else:
        print("❌ INSUFFISANT - Le RAG ne gère pas le chaos")
        print("   Refonte nécessaire de la mémoire conversationnelle")
    
    # Analyse détaillée des points faibles
    print(f"\n🔍 POINTS FAIBLES DÉTECTÉS:")
    if results['confusion_detected'] > 2:
        print(f"  ⚠️  Trop de confusions ({results['confusion_detected']})")
    if results['redirections'] < 3:
        print(f"  ⚠️  Pas assez de redirections vers achat ({results['redirections']})")
    if results['failed'] > 0:
        print(f"  ⚠️  {results['failed']} échec(s) technique(s)")
    
    return results

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  🔥 TEST CLIENT HARDCORE - RUE DU GROSSISTE                   ║
║                                                                                ║
║  Scénario: Client chaotique qui change d'avis constamment                     ║
║  Objectif: Tester la RÉSILIENCE du RAG face au chaos                          ║
║                                                                                ║
║  ⚠️  ATTENTION: Ce test va ÉPROUVER le système!                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    input("Appuyez sur ENTRÉE pour lancer le test HARDCORE... ")
    
    results = test_client_hardcore()
    
    print("\n" + "="*80)
    print("🔥 Test HARDCORE terminé!")
    print("="*80)

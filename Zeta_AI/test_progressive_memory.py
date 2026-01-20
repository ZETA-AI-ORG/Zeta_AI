#!/usr/bin/env python3
"""
🧠 TEST DU SYSTÈME DE MÉMOIRE CONVERSATIONNELLE PROGRESSIVE
Script de test pour valider le système de récupération d'informations progressive
"""

import requests
import json
import time
from datetime import datetime

# Configuration du test
API_URL = "http://127.0.0.1:8001/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
USER_ID = "testuser127"

def test_progressive_memory():
    """Test du système de mémoire conversationnelle progressive"""
    
    print("🧠 TEST DU SYSTÈME DE MÉMOIRE CONVERSATIONNELLE PROGRESSIVE")
    print("=" * 70)
    print(f"🕐 Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 URL API: {API_URL}")
    print(f"🏢 Company ID: {COMPANY_ID}")
    print(f"👤 User ID: {USER_ID}")
    print()
    
    # Simulation d'une conversation progressive
    conversation_steps = [
        {
            "step": 1,
            "message": "Bonjour, je voudrais commander des couches",
            "expected_extraction": ["intention de commande"],
            "description": "Démarrage de la conversation"
        },
        {
            "step": 2,
            "message": "Mon nom c'est Jean Kouassi",
            "expected_extraction": ["nom du client"],
            "description": "Extraction du nom"
        },
        {
            "step": 3,
            "message": "Mon téléphone c'est 07 87 36 07 57",
            "expected_extraction": ["numéro de téléphone"],
            "description": "Extraction du téléphone"
        },
        {
            "step": 4,
            "message": "Je veux 3 paquets de couches culottes",
            "expected_extraction": ["quantité", "type de produit"],
            "description": "Extraction des produits"
        },
        {
            "step": 5,
            "message": "Je suis à Cocody, près du CHU",
            "expected_extraction": ["adresse de livraison", "zone"],
            "description": "Extraction de l'adresse"
        },
        {
            "step": 6,
            "message": "Combien ça coûte au total ?",
            "expected_extraction": ["demande de prix"],
            "description": "Calcul de prix avec contexte"
        },
        {
            "step": 7,
            "message": "Pouvez-vous me faire un récapitulatif ?",
            "expected_extraction": ["demande de récapitulatif"],
            "description": "Génération de récapitulatif avec mémoire"
        },
        {
            "step": 8,
            "message": "Oui je confirme ma commande",
            "expected_extraction": ["confirmation"],
            "description": "Confirmation finale"
        }
    ]
    
    results = []
    conversation_id = f"{USER_ID}_{COMPANY_ID}_{int(time.time())}"
    
    for step_info in conversation_steps:
        print(f"🔥 ÉTAPE {step_info['step']}: {step_info['description']}")
        print(f"📤 Message: {step_info['message']}")
        print(f"🎯 Attendu: {', '.join(step_info['expected_extraction'])}")
        print("-" * 50)
        
        try:
            # Envoyer la requête
            payload = {
                "message": step_info["message"],
                "company_id": COMPANY_ID,
                "user_id": USER_ID
            }
            
            start_time = time.time()
            response = requests.post(API_URL, json=payload, timeout=30)
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                response_time = end_time - start_time
                
                print(f"✅ Succès - Temps: {response_time:.2f}s")
                
                # Analyser les données de mémoire
                memory_data = data.get("memory_data")
                if memory_data:
                    print(f"🧠 Données de mémoire extraites:")
                    
                    extracted_info = memory_data.get("extracted_information", [])
                    if extracted_info:
                        for info in extracted_info:
                            print(f"   • {info.get('type', 'N/A')}: {info.get('value', 'N/A')} (confiance: {info.get('confidence', 0):.2f})")
                    
                    conversation_summary = memory_data.get("conversation_summary", {})
                    if conversation_summary:
                        completeness = conversation_summary.get("completeness_percentage", 0)
                        print(f"   📊 Complétude: {completeness:.1f}%")
                        
                        customer_info = conversation_summary.get("customer_info", {})
                        if customer_info:
                            print(f"   👤 Client: {customer_info.get('name', 'N/A')} - {customer_info.get('phone', 'N/A')}")
                        
                        delivery_info = conversation_summary.get("delivery_info", {})
                        if delivery_info:
                            print(f"   📍 Livraison: {delivery_info.get('address', 'N/A')} - {delivery_info.get('zone', 'N/A')}")
                        
                        order_info = conversation_summary.get("order_info", {})
                        if order_info:
                            print(f"   📦 Commande: {order_info.get('product_type', 'N/A')} - {order_info.get('quantity', 'N/A')}")
                    
                    missing_info = memory_data.get("missing_information", [])
                    if missing_info:
                        print(f"   ❓ Manquant: {', '.join(missing_info)}")
                    
                    should_confirm = memory_data.get("should_confirm", False)
                    if should_confirm:
                        print(f"   🔔 Confirmation requise: OUI")
                        confirmation_prompt = memory_data.get("confirmation_prompt", "")
                        if confirmation_prompt:
                            print(f"   📝 Prompt: {confirmation_prompt[:100]}...")
                else:
                    print(f"⚠️ Aucune donnée de mémoire")
                
                # Afficher un aperçu de la réponse
                response_text = data.get("response", "")
                print(f"📝 Réponse: {response_text[:150]}...")
                
                results.append({
                    "step": step_info["step"],
                    "status": "SUCCESS",
                    "response_time": response_time,
                    "memory_data": memory_data is not None,
                    "extracted_count": len(memory_data.get("extracted_information", [])) if memory_data else 0,
                    "completeness": memory_data.get("conversation_summary", {}).get("completeness_percentage", 0) if memory_data else 0,
                    "should_confirm": memory_data.get("should_confirm", False) if memory_data else False
                })
                
            else:
                print(f"❌ Erreur HTTP {response.status_code}: {response.text}")
                results.append({
                    "step": step_info["step"],
                    "status": "ERROR",
                    "error": f"HTTP {response.status_code}"
                })
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            results.append({
                "step": step_info["step"],
                "status": "EXCEPTION",
                "error": str(e)
            })
        
        print()
        time.sleep(1)  # Pause entre les étapes
    
    # Analyse des résultats
    print("📊 ANALYSE DES RÉSULTATS")
    print("=" * 70)
    
    total_steps = len(results)
    successful_steps = len([r for r in results if r["status"] == "SUCCESS"])
    memory_activated_steps = len([r for r in results if r.get("memory_data", False)])
    confirmation_steps = len([r for r in results if r.get("should_confirm", False)])
    
    print(f"📈 Statistiques:")
    print(f"   • Étapes exécutées: {total_steps}")
    print(f"   • Étapes réussies: {successful_steps}")
    print(f"   • Mémoire activée: {memory_activated_steps}")
    print(f"   • Confirmations demandées: {confirmation_steps}")
    print(f"   • Taux de succès: {(successful_steps/total_steps)*100:.1f}%")
    print(f"   • Taux d'activation mémoire: {(memory_activated_steps/total_steps)*100:.1f}%")
    
    print(f"\n📋 Détail par étape:")
    for result in results:
        status_emoji = "✅" if result["status"] == "SUCCESS" else "❌" if result["status"] == "ERROR" else "⚠️"
        print(f"   {status_emoji} Étape {result['step']}: {result['status']}")
        if result.get("memory_data"):
            print(f"      🧠 Mémoire: Activée ({result.get('extracted_count', 0)} infos)")
            print(f"      📊 Complétude: {result.get('completeness', 0):.1f}%")
            if result.get("should_confirm"):
                print(f"      🔔 Confirmation: Requise")
        if result.get("response_time"):
            print(f"      ⏱️ Temps: {result['response_time']:.2f}s")
    
    print(f"\n🎉 TEST TERMINÉ!")
    print(f"🧠 Le système de mémoire conversationnelle progressive est {'✅ FONCTIONNEL' if memory_activated_steps > 0 else '❌ NON FONCTIONNEL'}")
    
    return results

if __name__ == "__main__":
    test_progressive_memory()


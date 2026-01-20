#!/usr/bin/env python3
"""
🧪 NOUVEAU TEST - CONVERSATION FRAÎCHE
Test avec questions variées et nouveau user_id pour éviter tous les caches
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List

class FreshConversationTester:
    """Nouveau testeur de conversation - zéro cache"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8001"):
        self.base_url = base_url
        self.company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
        self.user_id = "testuser500"  # Nouveau user_id complètement fresh
        self.conversation_history: List[Dict[str, Any]] = []
        self.total_time = 0
        
    def send_message(self, message: str, step_number: int, expected: str) -> Dict[str, Any]:
        """Envoie un message et capture la réponse"""
        print("\n" + "="*100)
        print(f"📞 TEST #{step_number}")
        print("="*100)
        print(f"❓ QUESTION: {message}")
        print(f"🎯 ATTENDU: {expected}")
        print("-"*100)
        
        payload = {
            "message": message,
            "company_id": self.company_id,
            "user_id": self.user_id
        }
        
        start_time = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            elapsed_time = (time.time() - start_time) * 1000
            self.total_time += elapsed_time
            
            if response.status_code == 200:
                data = response.json()
                llm_response = data.get("response", {}).get("response", "")
                confidence = data.get("response", {}).get("confidence", 0)
                processing_time = data.get("response", {}).get("processing_time_ms", 0)
                search_method = data.get("response", {}).get("search_method", "")
                cached = data.get("cached", False)
                
                print(f"✅ RÉPONSE LLM ({elapsed_time:.0f}ms):")
                print(f"{llm_response}")
                print("-"*100)
                print(f"📊 MÉTRIQUES:")
                print(f"   - Confiance: {confidence:.2f}")
                print(f"   - Temps traitement: {processing_time:.0f}ms")
                print(f"   - Méthode: {search_method}")
                print(f"   - Caché: {'✅ OUI' if cached else '❌ NON'}")
                
                self.conversation_history.append({
                    "step": step_number,
                    "question": message,
                    "response": llm_response,
                    "expected": expected,
                    "confidence": confidence,
                    "time_ms": elapsed_time,
                    "cached": cached
                })
                
                print("-"*100)
                print(f"📚 HISTORIQUE: {len(self.conversation_history)} échanges")
                
                # Analyse spécifique
                print("-"*100)
                print("🔍 ANALYSE:")
                self._analyze_response(step_number, message, llm_response, expected)
                
                return {"success": True, "response": llm_response, "data": data}
                
            else:
                print(f"❌ ERREUR HTTP {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            return {"success": False, "error": str(e)}
    
    def _analyze_response(self, step: int, question: str, response: str, expected: str):
        """Analyse la qualité de la réponse"""
        checks = []
        
        # TEST #2 - Prix pour 6 paquets
        if step == 2:
            checks.append(("Prix 25.000 FCFA mentionné", "25.000" in response or "25000" in response or "25 000" in response))
            checks.append(("Prix unitaire 4.150", "4.150" in response or "4150" in response))
            checks.append(("Pas de calcul 6x5500", not ("33.000" in response or "33000" in response)))
        
        # TEST #3 - Livraison Cocody
        elif step == 3:
            checks.append(("Frais 1.500 FCFA", "1.500" in response or "1500" in response))
            checks.append(("Mentionne Cocody", "cocody" in response.lower()))
            checks.append(("Zone centrale", "centrale" in response.lower() or "centre" in response.lower()))
        
        # TEST #5 - Récapitulatif
        elif step == 5:
            checks.append(("Produit: 6 paquets", "6" in response and "paquet" in response.lower()))
            checks.append(("Prix produit: 25.000", "25.000" in response or "25000" in response))
            checks.append(("Frais livraison: 1.500", "1.500" in response or "1500" in response))
            checks.append(("Total: 26.500", "26.500" in response or "26500" in response))
            checks.append(("Acompte: 2.000", "2.000" in response or "2000" in response))
        
        if checks:
            for check_name, result in checks:
                status = "✅" if result else "❌"
                print(f"   {status} {check_name}")
        else:
            print("   ℹ️ Vérification générale")
    
    def print_summary(self):
        """Résumé final"""
        print("\n\n" + "="*100)
        print("📊 RÉSUMÉ FINAL")
        print("="*100)
        
        total_exchanges = len(self.conversation_history)
        avg_confidence = sum(ex['confidence'] for ex in self.conversation_history) / total_exchanges if total_exchanges > 0 else 0
        avg_time = self.total_time / total_exchanges if total_exchanges > 0 else 0
        
        print(f"🔢 Échanges: {total_exchanges}")
        print(f"⏱️  Temps total: {self.total_time:.0f}ms")
        print(f"⏱️  Temps moyen: {avg_time:.0f}ms")
        print(f"📊 Confiance moyenne: {avg_confidence:.2f}")
        print("-"*100)
        
        print("\n📝 HISTORIQUE COMPLET:")
        for i, exchange in enumerate(self.conversation_history, 1):
            print(f"\n{i}. ❓ {exchange['question']}")
            print(f"   🤖 {exchange['response'][:100]}...")
            print(f"   🎯 Attendu: {exchange['expected']}")
            print(f"   📊 {exchange['confidence']:.2f} | ⏱️ {exchange['time_ms']:.0f}ms")
        
        print("\n" + "="*100)
        print(f"✅ TEST TERMINÉ - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*100)


def main():
    """Test avec questions variées"""
    
    print("="*100)
    print("🚀 NOUVEAU TEST - CONVERSATION FRAÎCHE")
    print("="*100)
    print(f"🕐 Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🏢 Company: MpfnlSbqwaZ6F4HvxQLRL9du0yG3")
    print(f"👤 User: testuser500 (NOUVEAU)")
    print(f"🌐 URL: http://127.0.0.1:8001")
    print("="*100)
    
    tester = FreshConversationTester()
    
    # Questions variées
    tests = [
        {
            "message": "Salut ! C'est quoi votre boutique ?",
            "expected": "Présentation de Rue_du_gros"
        },
        {
            "message": "Ça coûte combien 6 paquets de couches culottes ?",
            "expected": "25.000 FCFA (prix explicite, pas 6x5500=33000)"
        },
        {
            "message": "Je suis à Cocody. Frais de livraison ?",
            "expected": "1.500 FCFA (zone centrale)"
        },
        {
            "message": "Je m'appelle Yao Marie, mon numéro: 0709876543",
            "expected": "Demande adresse précise"
        },
        {
            "message": "Faites le récap complet svp",
            "expected": "6 paquets (25.000) + Livraison (1.500) = 26.500 FCFA"
        }
    ]
    
    # Exécuter les tests
    for i, test in enumerate(tests, 1):
        result = tester.send_message(test["message"], i, test["expected"])
        
        if not result["success"]:
            print(f"\n⚠️ ARRÊT - Échec à l'étape {i}")
            break
        
        if i < len(tests):
            time.sleep(0.5)
    
    tester.print_summary()


if __name__ == "__main__":
    main()

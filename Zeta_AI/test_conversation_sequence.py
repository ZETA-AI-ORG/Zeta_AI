#!/usr/bin/env python3
"""
🧪 SCRIPT DE TEST - CONVERSATION COMPLÈTE AVEC ANALYSE
Teste la gestion des ambiguïtés, prix explicites et mémoire conversationnelle
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List

class ConversationTester:
    """Testeur de conversation avec analyse détaillée"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8001"):
        self.base_url = base_url
        self.company_id = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
        self.user_id = "testuser401"  # Nouveau user_id pour test prompt optimisé
        self.conversation_history: List[Dict[str, Any]] = []
        self.total_time = 0
        
    def send_message(self, message: str, step_number: int, expected: str) -> Dict[str, Any]:
        """
        Envoie un message et capture la réponse avec analyse
        """
        print("\n" + "="*100)
        print(f"📞 CURL #{step_number}")
        print("="*100)
        print(f"❓ QUESTION: {message}")
        print(f"🎯 ATTENDU: {expected}")
        print("-"*100)
        
        # Préparer le payload
        payload = {
            "message": message,
            "company_id": self.company_id,
            "user_id": self.user_id
        }
        
        # Envoyer la requête
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
                
                # Afficher la réponse
                print(f"✅ RÉPONSE LLM ({elapsed_time:.0f}ms):")
                print(f"{llm_response}")
                print("-"*100)
                print(f"📊 MÉTRIQUES:")
                print(f"   - Confiance: {confidence:.2f}")
                print(f"   - Temps traitement: {processing_time:.0f}ms")
                print(f"   - Méthode: {search_method}")
                print(f"   - Caché: {'✅ OUI' if cached else '❌ NON'}")
                
                # Construire l'historique conversationnel
                self.conversation_history.append({
                    "step": step_number,
                    "question": message,
                    "response": llm_response,
                    "expected": expected,
                    "confidence": confidence,
                    "time_ms": elapsed_time,
                    "cached": cached
                })
                
                # Afficher l'historique accumulé
                print("-"*100)
                print(f"📚 HISTORIQUE CONVERSATIONNEL ({len(self.conversation_history)} échanges):")
                for i, exchange in enumerate(self.conversation_history, 1):
                    print(f"   {i}. USER: {exchange['question'][:60]}...")
                    print(f"      BOT: {exchange['response'][:60]}...")
                
                # Analyse de cohérence
                print("-"*100)
                print("🔍 ANALYSE:")
                self._analyze_response(step_number, message, llm_response, expected)
                
                return {
                    "success": True,
                    "response": llm_response,
                    "data": data
                }
                
            else:
                print(f"❌ ERREUR HTTP {response.status_code}")
                print(f"Réponse: {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            return {"success": False, "error": str(e)}
    
    def _analyze_response(self, step: int, question: str, response: str, expected: str):
        """Analyse la pertinence de la réponse"""
        
        checks = []
        
        # CURL #2 - Ambiguïtés
        if step == 2:
            checks.append(("Présente plusieurs options", 
                          any(word in response.lower() for word in ["options", "choix", "types"])))
            checks.append(("Mentionne couches à pression", "pression" in response.lower()))
            checks.append(("Mentionne couches culottes", "culottes" in response.lower()))
            checks.append(("Mentionne couches adultes", "adultes" in response.lower()))
        
        # CURL #4 - Prix explicite
        elif step == 4:
            checks.append(("Prix 13.500 FCFA (correct)", "13.500" in response or "13500" in response))
            checks.append(("PAS 16.500 FCFA (calcul)", not ("16.500" in response or "16500" in response)))
            checks.append(("Utilise prix explicite", "selon nos tarifs" in response.lower() or "tarif" in response.lower()))
        
        # CURL #5 - Livraison
        elif step == 5:
            checks.append(("Frais 1.500 FCFA", "1.500" in response or "1500" in response))
            checks.append(("Mentionne Yopougon", "yopougon" in response.lower()))
        
        # CURL #8 - Récapitulatif
        elif step == 8:
            checks.append(("Total 15.000 FCFA", "15.000" in response or "15000" in response))
            checks.append(("3 paquets mentionnés", "3 paquets" in response.lower()))
            checks.append(("Produit (couches culottes)", "culottes" in response.lower()))
            checks.append(("Livraison (1.500)", "1.500" in response or "1500" in response))
            checks.append(("Acompte 2.000", "2.000" in response or "2000" in response))
        
        # Mémoire conversationnelle (tous)
        if step >= 3:
            prev_exchanges = [ex for ex in self.conversation_history if ex['step'] < step]
            if prev_exchanges:
                checks.append(("Continuité conversationnelle", 
                              len(response) > 20))  # Basique, à améliorer
        
        # Afficher les résultats
        if checks:
            for check_name, result in checks:
                status = "✅" if result else "❌"
                print(f"   {status} {check_name}")
        else:
            print("   ℹ️ Pas de vérification spécifique pour cette étape")
    
    def print_summary(self):
        """Affiche un résumé final de la conversation"""
        print("\n\n" + "="*100)
        print("📊 RÉSUMÉ FINAL DE LA CONVERSATION")
        print("="*100)
        
        total_exchanges = len(self.conversation_history)
        avg_confidence = sum(ex['confidence'] for ex in self.conversation_history) / total_exchanges if total_exchanges > 0 else 0
        avg_time = self.total_time / total_exchanges if total_exchanges > 0 else 0
        
        print(f"🔢 Nombre d'échanges: {total_exchanges}")
        print(f"⏱️  Temps total: {self.total_time:.0f}ms")
        print(f"⏱️  Temps moyen/échange: {avg_time:.0f}ms")
        print(f"📊 Confiance moyenne: {avg_confidence:.2f}")
        print("-"*100)
        
        print("\n📝 HISTORIQUE COMPLET:")
        for i, exchange in enumerate(self.conversation_history, 1):
            print(f"\n{i}. ❓ USER: {exchange['question']}")
            print(f"   🤖 BOT: {exchange['response']}")
            print(f"   🎯 ATTENDU: {exchange['expected']}")
            print(f"   📊 Confiance: {exchange['confidence']:.2f} | ⏱️ {exchange['time_ms']:.0f}ms | {'💾 Caché' if exchange['cached'] else '🔄 Live'}")
        
        print("\n" + "="*100)
        print(f"✅ TEST TERMINÉ - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*100)


def main():
    """Fonction principale - Exécute la séquence de tests"""
    
    print("="*100)
    print("🚀 DÉMARRAGE DES TESTS - CONVERSATION COMPLÈTE")
    print("="*100)
    print(f"🕐 Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🏢 Company ID: MpfnlSbqwaZ6F4HvxQLRL9du0yG3")
    print(f"👤 User ID: testuser200")
    print(f"🌐 URL: http://127.0.0.1:8001")
    print("="*100)
    
    tester = ConversationTester()
    
    # Séquence de tests
    tests = [
        {
            "message": "Bonjour, je découvre votre boutique",
            "expected": "Message d'accueil professionnel"
        },
        {
            "message": "Combien coûte un paquet de couches taille 3 ?",
            "expected": "PRÉSENTER les 3 options (à pression, culottes, adultes)"
        },
        {
            "message": "Je veux les couches culottes",
            "expected": "Référence à 'taille 3' (mémoire conversationnelle)"
        },
        {
            "message": "Je voudrais 3 paquets",
            "expected": "13.500 FCFA (prix explicite, PAS 16.500)"
        },
        {
            "message": "Je suis à Yopougon, vous livrez ?",
            "expected": "1.500 FCFA (zone centrale)"
        },
        {
            "message": "Mon nom est Kouassi Jean, téléphone 0707123456",
            "expected": "Demande adresse précise"
        },
        {
            "message": "Yopougon Niangon, près du marché",
            "expected": "Confirmation paiement Wave"
        },
        {
            "message": "Ok pour Wave",
            "expected": "Récap: 3 paquets (13.500) + Livraison (1.500) = 15.000 FCFA, Acompte 2.000"
        }
    ]
    
    # Exécuter tous les tests
    for i, test in enumerate(tests, 1):
        result = tester.send_message(test["message"], i, test["expected"])
        
        if not result["success"]:
            print(f"\n⚠️ ARRÊT DES TESTS - Échec à l'étape {i}")
            break
        
        # Pause entre les requêtes
        if i < len(tests):
            time.sleep(0.5)
    
    # Afficher le résumé
    tester.print_summary()


if __name__ == "__main__":
    main()

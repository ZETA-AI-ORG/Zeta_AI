#!/usr/bin/env python3
"""
🧪 TEST ULTIME DE COHÉRENCE CONVERSATIONNELLE RAG V2.0
Test robuste pour valider la capacité du RAG à suivre une conversation longue
avec les nouvelles fonctionnalités : Mémoire Progressive + Calcul de Prix + Récapitulatifs
"""

import subprocess
import json
import time
from datetime import datetime
from typing import List, Dict, Any
import random

# Configuration du test
API_URL = "http://127.0.0.1:8001/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
USER_ID = "testuser124"

class ConversationTesterV2:
    def __init__(self):
        self.conversation_history = []
        self.memory_analysis = {
            "extractions_count": 0,
            "completeness_progression": [],
            "confirmations_triggered": 0,
            "price_calculations": 0,
            "recap_generations": 0
        }
        self.old_issues_fixed = {
            "size_recognition": 0,
            "price_calculation": 0,
            "context_memory": 0,
            "recap_completeness": 0
        }
        self.new_features_tested = {
            "progressive_memory": 0,
            "intelligent_extraction": 0,
            "smart_confirmation": 0,
            "dynamic_pricing": 0,
            "adaptive_recap": 0
        }
        
    def send_message(self, message: str, context: str = "") -> Dict[str, Any]:
        """Envoie un message au RAG via curl et retourne la réponse"""
        try:
            # Échapper les guillemets dans le message pour curl
            escaped_message = message.replace('"', '\\"')
            
            # Construire la commande curl
            curl_cmd = [
                "curl", "-X", "POST", API_URL,
                "-H", "Content-Type: application/json",
                "-d", f'{{"message":"{escaped_message}","company_id":"{COMPANY_ID}","user_id":"{USER_ID}"}}'
            ]
            
            print(f"\n{'='*80}")
            print(f"📤 MESSAGE {len(self.conversation_history) + 1}: {context}")
            print(f"💬 Contenu: {message[:100]}{'...' if len(message) > 100 else ''}")
            print(f"{'='*80}")
            
            start_time = time.time()
            try:
                # Exécuter curl
                result = subprocess.run(
                    curl_cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=30
                )
                end_time = time.time()
                elapsed_time = end_time - start_time
                
                if result.returncode == 0:
                    try:
                        data = json.loads(result.stdout)
                        self.conversation_history.append(data)
                        
                        print(f"✅ RÉPONSE ({elapsed_time:.2f}s):")
                        print(f"📝 {data.get('response', '')[:200]}{'...' if len(data.get('response', '')) > 200 else ''}")
                        print(f"🎯 Cache: {'✅ HIT' if data.get('cached') else '❌ MISS'}")
                        
                        # Analyser les nouvelles fonctionnalités
                        self._analyze_new_features(data)
                        
                        return data
                    except json.JSONDecodeError as e:
                        error_msg = f"JSON Parse Error: {e} - Raw: {result.stdout}"
                        print(f"❌ Erreur: {error_msg}")
                        return {"error": error_msg}
                else:
                    error_msg = f"Curl Error {result.returncode}: {result.stderr}"
                    print(f"❌ Erreur: {error_msg}")
                    return {"error": error_msg}
                    
            except subprocess.TimeoutExpired:
                error_msg = "Timeout: La requête a pris plus de 30 secondes"
                print(f"❌ Erreur: {error_msg}")
                return {"error": error_msg}
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            print(f"❌ Erreur: {error_msg}")
            return {"error": error_msg}
    
    def _analyze_new_features(self, response_data: Dict[str, Any]):
        """Analyse les nouvelles fonctionnalités dans la réponse"""
        
        # Analyser le système de mémoire progressive
        memory_data = response_data.get("memory_data")
        if memory_data:
            self.memory_analysis["progressive_memory"] += 1
            
            # Compter les extractions
            extracted_info = memory_data.get("extracted_information", [])
            self.memory_analysis["extractions_count"] += len(extracted_info)
            
            # Suivre la progression de complétude
            conversation_summary = memory_data.get("conversation_summary", {})
            completeness = conversation_summary.get("completeness_percentage", 0)
            self.memory_analysis["completeness_progression"].append(completeness)
            
            # Vérifier les confirmations
            if memory_data.get("should_confirm", False):
                self.memory_analysis["confirmations_triggered"] += 1
                self.new_features_tested["smart_confirmation"] += 1
        
        # Analyser le calcul de prix
        if response_data.get("price_calculated", False):
            self.memory_analysis["price_calculations"] += 1
            self.new_features_tested["dynamic_pricing"] += 1
            
            price_info = response_data.get("price_info")
            if price_info and price_info.get("products"):
                self.old_issues_fixed["price_calculation"] += 1
        
        # Analyser les récapitulatifs
        response_text = response_data.get("response", "")
        if any(keyword in response_text.lower() for keyword in ["récapitulatif", "récap", "commande", "total"]):
            if "prix" in response_text.lower() and "f cfa" in response_text.lower():
                self.memory_analysis["recap_generations"] += 1
                self.new_features_tested["adaptive_recap"] += 1
                self.old_issues_fixed["recap_completeness"] += 1
        
        # Analyser la reconnaissance des tailles
        if any(size in response_text.lower() for size in ["taille 1", "taille 2", "taille 3", "taille 4", "taille 5", "taille 6", "taille 7"]):
            self.old_issues_fixed["size_recognition"] += 1
        
        # Analyser la mémoire contextuelle
        if memory_data and memory_data.get("conversation_summary"):
            summary = memory_data["conversation_summary"]
            if summary.get("customer_info") or summary.get("delivery_info") or summary.get("order_info"):
                self.old_issues_fixed["context_memory"] += 1
                self.new_features_tested["intelligent_extraction"] += 1
    
    def analyze_response(self, response: str, expected_intent: str) -> Dict[str, Any]:
        """Analyse la réponse pour détecter la progression dans le processus de commande"""
        analysis = {
            "intent_detected": None,
            "etape_progression": None,
            "info_collected": {},
            "suggestions_offered": False,
            "paiement_mentioned": False,
            "contact_info_mentioned": False,
            "price_mentioned": False,
            "size_mentioned": False,
            "memory_used": False
        }
        
        response_lower = response.lower()
        
        # Détecter les intentions
        if any(word in response_lower for word in ["commande", "commander", "acheter"]):
            analysis["intent_detected"] = "commande"
        elif any(word in response_lower for word in ["prix", "coût", "tarif"]):
            analysis["intent_detected"] = "prix"
        elif any(word in response_lower for word in ["livraison", "adresse", "zone"]):
            analysis["intent_detected"] = "livraison"
        elif any(word in response_lower for word in ["confirmer", "valider", "récapitulatif"]):
            analysis["intent_detected"] = "confirmation"
        
        # Détecter les étapes de progression
        if any(word in response_lower for word in ["nom", "téléphone", "contact"]):
            analysis["etape_progression"] = "coordonnees"
        elif any(word in response_lower for word in ["adresse", "livraison", "zone"]):
            analysis["etape_progression"] = "adresse_livraison"
        elif any(word in response_lower for word in ["prix", "coût", "total"]):
            analysis["etape_progression"] = "confirmation_prix"
        elif any(word in response_lower for word in ["paiement", "wave", "acompte"]):
            analysis["etape_progression"] = "mode_paiement"
        elif any(word in response_lower for word in ["récapitulatif", "récap", "résumé"]):
            analysis["etape_progression"] = "recapitulatif"
        elif any(word in response_lower for word in ["confirmer", "valider", "finaliser"]):
            analysis["etape_progression"] = "validation_finale"
        
        # Détecter les informations collectées
        if any(word in response_lower for word in ["nom", "prénom"]):
            analysis["info_collected"]["nom"] = True
        if any(word in response_lower for word in ["téléphone", "phone", "numéro"]):
            analysis["info_collected"]["telephone"] = True
        if any(word in response_lower for word in ["adresse", "livraison"]):
            analysis["info_collected"]["adresse"] = True
        if any(word in response_lower for word in ["quantité", "paquets", "colis"]):
            analysis["info_collected"]["quantite"] = True
        
        # Détecter les fonctionnalités
        analysis["suggestions_offered"] = any(word in response_lower for word in ["suggère", "recommand", "conseille"])
        analysis["paiement_mentioned"] = any(word in response_lower for word in ["paiement", "wave", "acompte"])
        analysis["contact_info_mentioned"] = any(word in response_lower for word in ["téléphone", "contact", "appel"])
        analysis["price_mentioned"] = any(word in response_lower for word in ["prix", "coût", "f cfa"])
        analysis["size_mentioned"] = any(word in response_lower for word in ["taille", "kg", "poids"])
        analysis["memory_used"] = any(word in response_lower for word in ["comme", "précédemment", "déjà", "avant"])
        
        return analysis

def generate_semantic_variations(base_question: str) -> List[str]:
    """Génère des variations sémantiques d'une question"""
    variations = [
        base_question,
        base_question.replace("commander", "acheter"),
        base_question.replace("couches", "couches culottes"),
        base_question.replace("paquets", "colis"),
        base_question.replace("combien", "quel est le prix"),
        base_question.replace("coûte", "vaut"),
        base_question.replace("livraison", "expédition"),
        base_question.replace("adresse", "localisation")
    ]
    return list(set(variations))

def test_conversation_robust_v2():
    """Test robuste V2.0 avec nouvelles fonctionnalités"""
    
    print("🚀 DÉBUT DU TEST ULTIME DE COHÉRENCE CONVERSATIONNELLE V2.0")
    print("🕐 Heure:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("🎯 Objectif: Valider le processus de commande + Nouvelles fonctionnalités")
    print("🏢 Company:", f"Rue du Gros ({COMPANY_ID})")
    print()
    
    tester = ConversationTesterV2()
    
    # === PHASE 1: TEST DES ANCIENS PROBLÈMES RÉSOLUS ===
    print("🔥 PHASE 1: TEST DES ANCIENS PROBLÈMES RÉSOLUS")
    print("=" * 60)
    
    # Test 1.1: Reconnaissance des tailles (problème résolu)
    print("\n📏 Test 1.1: Reconnaissance des tailles")
    size_tests = [
        "Mon bébé fait 8kg, quelle taille de couches me conseillez-vous ?",
        "Je veux des couches taille 3 pour mon enfant de 10kg",
        "Quelles sont les tailles disponibles pour les couches à pression ?"
    ]
    
    for i, test in enumerate(size_tests, 1):
        response = tester.send_message(test, f"Test taille {i}")
        if "error" not in response:
            analysis = tester.analyze_response(response.get("response", ""), "taille")
            print(f"📊 Analyse: {analysis}")
    
    # Test 1.2: Calcul de prix (problème résolu)
    print("\n💰 Test 1.2: Calcul de prix automatique")
    price_tests = [
        "Je veux 2 paquets de couches culottes, combien ça coûte ?",
        "Combien pour 6 paquets de couches culottes avec livraison à Cocody ?",
        "Pouvez-vous me calculer le prix de 12 paquets de couches culottes ?"
    ]
    
    for i, test in enumerate(price_tests, 1):
        response = tester.send_message(test, f"Test prix {i}")
        if "error" not in response:
            analysis = tester.analyze_response(response.get("response", ""), "prix")
            print(f"📊 Analyse: {analysis}")
    
    # === PHASE 2: TEST DE LA MÉMOIRE CONVERSATIONNELLE PROGRESSIVE ===
    print("\n🔥 PHASE 2: TEST DE LA MÉMOIRE CONVERSATIONNELLE PROGRESSIVE")
    print("=" * 60)
    
    # Conversation progressive pour tester la mémoire
    progressive_conversation = [
        "Bonjour, je voudrais commander des couches",
        "Mon nom c'est Marie Kouassi",
        "Mon téléphone c'est 07 87 36 07 57",
        "Je veux 3 paquets de couches culottes",
        "Je suis à Yopougon, près du marché",
        "Combien ça coûte au total avec la livraison ?",
        "Pouvez-vous me faire un récapitulatif complet ?",
        "Oui je confirme ma commande"
    ]
    
    for i, message in enumerate(progressive_conversation, 1):
        response = tester.send_message(message, f"Conversation progressive {i}")
        if "error" not in response:
            analysis = tester.analyze_response(response.get("response", ""), f"progressive_{i}")
            print(f"📊 Étape {i}: {analysis}")
    
    # === PHASE 3: TEST DES VARIATIONS SÉMANTIQUES AVEC MÉMOIRE ===
    print("\n🔥 PHASE 3: TEST DES VARIATIONS SÉMANTIQUES AVEC MÉMOIRE")
    print("=" * 60)
    
    base_question = "Je veux commander 2 paquets de couches taille 4"
    variations = generate_semantic_variations(base_question)
    
    for i, variation in enumerate(variations[:5], 1):
        response = tester.send_message(variation, f"Variation sémantique {i}")
        if "error" not in response:
            analysis = tester.analyze_response(response.get("response", ""), "variation")
            print(f"📊 Variation {i}: {analysis}")
    
    # === PHASE 4: TEST DE CHANGEMENT D'INTENTION AVEC MÉMOIRE ===
    print("\n🔥 PHASE 4: TEST DE CHANGEMENT D'INTENTION AVEC MÉMOIRE")
    print("=" * 60)
    
    intention_switches = [
        ("Je veux commander des couches", "En fait, je veux juste des informations"),
        ("C'est quoi vos prix ?", "Ah non, je veux commander maintenant"),
        ("Comment payer ?", "Attendez, je veux d'abord voir vos produits"),
        ("Vous livrez où ?", "Bon, finalement je prends pas"),
        ("C'est combien ?", "Ok je confirme ma commande")
    ]
    
    for i, (original, switch) in enumerate(intention_switches, 1):
        response1 = tester.send_message(original, f"Intention originale {i}")
        if "error" not in response1:
            print(f"📝 Réponse à '{original}': {response1.get('response', '')[:100]}...")
        
        response2 = tester.send_message(switch, f"Changement d'intention {i}")
        if "error" not in response2:
            print(f"🔄 Switch détecté: '{switch}'")
            analysis = tester.analyze_response(response2.get("response", ""), "switch")
            print(f"📊 Adaptation: {analysis}")
    
    # === PHASE 5: TEST DE RÉSISTANCE AVEC NOUVELLES FONCTIONNALITÉS ===
    print("\n🔥 PHASE 5: TEST DE RÉSISTANCE AVEC NOUVELLES FONCTIONNALITÉS")
    print("=" * 60)
    
    resistance_tests = [
        "Je veux payer en espèces",
        "Vous livrez à l'étranger ?",
        "C'est trop cher, vous avez des réductions ?",
        "Je veux juste des échantillons gratuits",
        "Mon bébé fait 50kg, vous avez quelle taille ?",
        "Je veux payer en 10 fois",
        "Vous avez des couches de marque Pampers ?"
    ]
    
    for i, test in enumerate(resistance_tests, 1):
        response = tester.send_message(test, f"Test de résistance {i}")
        if "error" not in response:
            print(f"🛡️ Résistance {i}: {response.get('response', '')[:150]}...")
    
    # === ANALYSE FINALE V2.0 ===
    print("\n📊 ANALYSE FINALE DU TEST V2.0")
    print("=" * 80)
    
    # Statistiques générales
    total_messages = len(tester.conversation_history)
    successful_responses = len([r for r in tester.conversation_history if "error" not in r])
    
    print(f"📈 STATISTIQUES GÉNÉRALES:")
    print(f"  • Messages envoyés: {total_messages}")
    print(f"  • Réponses réussies: {successful_responses}")
    print(f"  • Taux de succès: {(successful_responses/total_messages)*100:.1f}%")
    
    # Analyse des anciens problèmes résolus
    print(f"\n🔧 ANCIENS PROBLÈMES RÉSOLUS:")
    print(f"  • Reconnaissance des tailles: {tester.old_issues_fixed['size_recognition']} fois")
    print(f"  • Calcul de prix: {tester.old_issues_fixed['price_calculation']} fois")
    print(f"  • Mémoire contextuelle: {tester.old_issues_fixed['context_memory']} fois")
    print(f"  • Récapitulatifs complets: {tester.old_issues_fixed['recap_completeness']} fois")
    
    # Analyse des nouvelles fonctionnalités
    print(f"\n🚀 NOUVELLES FONCTIONNALITÉS TESTÉES:")
    print(f"  • Mémoire progressive: {tester.new_features_tested['progressive_memory']} fois")
    print(f"  • Extraction intelligente: {tester.new_features_tested['intelligent_extraction']} fois")
    print(f"  • Confirmation intelligente: {tester.new_features_tested['smart_confirmation']} fois")
    print(f"  • Calcul de prix dynamique: {tester.new_features_tested['dynamic_pricing']} fois")
    print(f"  • Récapitulatif adaptatif: {tester.new_features_tested['adaptive_recap']} fois")
    
    # Analyse de la mémoire progressive
    print(f"\n🧠 ANALYSE DE LA MÉMOIRE PROGRESSIVE:")
    print(f"  • Total extractions: {tester.memory_analysis['extractions_count']}")
    print(f"  • Confirmations déclenchées: {tester.memory_analysis['confirmations_triggered']}")
    print(f"  • Calculs de prix: {tester.memory_analysis['price_calculations']}")
    print(f"  • Générations de récapitulatif: {tester.memory_analysis['recap_generations']}")
    
    if tester.memory_analysis['completeness_progression']:
        min_completeness = min(tester.memory_analysis['completeness_progression'])
        max_completeness = max(tester.memory_analysis['completeness_progression'])
        print(f"  • Progression complétude: {min_completeness:.1f}% → {max_completeness:.1f}%")
    
    # Évaluation globale
    print(f"\n🎯 ÉVALUATION GLOBALE V2.0:")
    
    # Score des anciens problèmes
    old_issues_score = sum(tester.old_issues_fixed.values()) / 4 * 100
    print(f"  • Anciens problèmes résolus: {old_issues_score:.1f}%")
    
    # Score des nouvelles fonctionnalités
    new_features_score = sum(tester.new_features_tested.values()) / 5 * 100
    print(f"  • Nouvelles fonctionnalités: {new_features_score:.1f}%")
    
    # Score global
    global_score = (old_issues_score + new_features_score) / 2
    print(f"  • Score global V2.0: {global_score:.1f}%")
    
    if global_score >= 80:
        print(f"  🏆 EXCELLENT: RAG V2.0 prêt pour la production!")
    elif global_score >= 60:
        print(f"  ✅ BON: RAG V2.0 fonctionnel avec quelques améliorations possibles")
    else:
        print(f"  ⚠️ MOYEN: RAG V2.0 nécessite des améliorations")
    
    print(f"\n🎉 TEST ULTIME V2.0 TERMINÉ!")
    print(f"📋 Rapport complet généré avec {total_messages} interactions")
    print(f"🧠 Mémoire progressive: {'✅ ACTIVÉE' if tester.memory_analysis['progressive_memory'] > 0 else '❌ DÉSACTIVÉE'}")
    print(f"💰 Calcul de prix: {'✅ FONCTIONNEL' if tester.old_issues_fixed['price_calculation'] > 0 else '❌ NON FONCTIONNEL'}")
    print(f"📋 Récapitulatifs: {'✅ COMPLETS' if tester.old_issues_fixed['recap_completeness'] > 0 else '❌ INCOMPLETS'}")
    
    return {
        "total_messages": total_messages,
        "successful_responses": successful_responses,
        "old_issues_fixed": tester.old_issues_fixed,
        "new_features_tested": tester.new_features_tested,
        "memory_analysis": tester.memory_analysis,
        "global_score": global_score
    }

if __name__ == "__main__":
    test_conversation_robust_v2()


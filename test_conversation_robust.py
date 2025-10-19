#!/usr/bin/env python3
"""
🧪 TEST ULTIME DE COHÉRENCE CONVERSATIONNELLE RAG
Test robuste pour valider la capacité du RAG à suivre une conversation longue
et maintenir le focus sur l'objectif commercial : PROCESSUS DE COMMANDE (7 étapes)
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
USER_ID = "testuser126"

class ConversationTester:
    def __init__(self):
        self.conversation_history = []
        self.command_progress = {
            "etape_1_identification": False,
            "etape_2_confirmation_prix": False,
            "etape_3_coordonnees": False,
            "etape_4_adresse": False,
            "etape_5_paiement": False,
            "etape_6_recapitulatif": False,
            "etape_7_validation": False
        }
        self.collected_info = {
            "produits": [],
            "prix_total": None,
            "client_nom": None,
            "client_telephone": None,
            "adresse_complete": None,
            "zone_livraison": None,
            "paiement_wave": False,
            "acompte_confirme": False
        }
        self.intent_switches = 0
        self.semantic_variations = 0
        
    def send_message(self, message: str, context: str = "") -> Dict[str, Any]:
        """Envoie un message au chatbot via curl et retourne la réponse"""
        # Échapper les guillemets dans le message pour curl
        escaped_message = message.replace('"', '\\"')
        
        print(f"\n{'='*80}")
        print(f"📤 MESSAGE {len(self.conversation_history) + 1}: {context}")
        print(f"💬 Contenu: {message[:100]}{'...' if len(message) > 100 else ''}")
        print(f"{'='*80}")
        
        start_time = time.time()
        try:
            # Construire la commande curl avec le format multi-ligne
            curl_cmd = [
                "curl", "-X", "POST", API_URL,
                "-H", "Content-Type: application/json",
                "-d", f'{{"message":"{escaped_message}","company_id":"{COMPANY_ID}","user_id":"{USER_ID}"}}'
            ]
            
            # Exécuter curl
            result = subprocess.run(
                curl_cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            end_time = time.time()
            elapsed = end_time - start_time
            
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    
                    # Enregistrer dans l'historique
                    self.conversation_history.append({
                        "message": message,
                        "response": data.get("response", ""),
                        "cached": data.get("cached", False),
                        "elapsed_time": elapsed,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    print(f"✅ RÉPONSE ({elapsed:.2f}s):")
                    print(f"📝 {data.get('response', '')[:200]}{'...' if len(data.get('response', '')) > 200 else ''}")
                    print(f"🎯 Cache: {'✅ HIT' if data.get('cached') else '❌ MISS'}")
                    
                    return data
                except json.JSONDecodeError as e:
                    print(f"❌ ERREUR JSON: {e}")
                    print(f"Raw output: {result.stdout}")
                    return {"error": f"JSON Parse Error: {e}"}
            else:
                print(f"❌ ERREUR CURL {result.returncode}: {result.stderr}")
                return {"error": f"Curl Error {result.returncode}"}
                
        except subprocess.TimeoutExpired:
            print(f"❌ TIMEOUT: La requête a pris plus de 30 secondes")
            return {"error": "Timeout"}
        except Exception as e:
            print(f"❌ ERREUR: {str(e)}")
            return {"error": str(e)}
    
    def analyze_response(self, response: str, expected_intent: str) -> Dict[str, Any]:
        """Analyse la réponse pour détecter la progression dans le processus de commande"""
        analysis = {
            "intent_detected": None,
            "etape_progression": None,
            "info_collected": {},
            "suggestions_offered": False,
            "paiement_mentioned": False,
            "contact_info_mentioned": False
        }
        
        response_lower = response.lower()
        
        # Détection des étapes du processus de commande
        if any(word in response_lower for word in ["quel produit", "quelle taille", "combien", "quantité"]):
            analysis["etape_progression"] = "identification_produit"
            self.command_progress["etape_1_identification"] = True
            
        if any(word in response_lower for word in ["prix", "coût", "total", "f cfa", "fcf"]):
            analysis["etape_progression"] = "confirmation_prix"
            self.command_progress["etape_2_confirmation_prix"] = True
            
        if any(word in response_lower for word in ["nom", "téléphone", "contact", "coordonnées"]):
            analysis["etape_progression"] = "coordonnees_client"
            self.command_progress["etape_3_coordonnees"] = True
            
        if any(word in response_lower for word in ["adresse", "livraison", "où", "zone", "commune"]):
            analysis["etape_progression"] = "adresse_livraison"
            self.command_progress["etape_4_adresse"] = True
            
        if any(word in response_lower for word in ["paiement", "wave", "acompte", "2000"]):
            analysis["etape_progression"] = "mode_paiement"
            self.command_progress["etape_5_paiement"] = True
            analysis["paiement_mentioned"] = True
            
        if any(word in response_lower for word in ["récapitulatif", "résumé", "commande", "confirmer"]):
            analysis["etape_progression"] = "recapitulatif"
            self.command_progress["etape_6_recapitulatif"] = True
            
        if any(word in response_lower for word in ["valider", "confirmer", "d'accord", "ok"]):
            analysis["etape_progression"] = "validation_finale"
            self.command_progress["etape_7_validation"] = True
            
        # Détection des suggestions
        if any(word in response_lower for word in ["suggérer", "recommand", "proposer", "option"]):
            analysis["suggestions_offered"] = True
            
        # Détection des informations de contact
        if any(word in response_lower for word in ["+225", "whatsapp", "téléphone", "appel"]):
            analysis["contact_info_mentioned"] = True
            
        return analysis

def generate_semantic_variations(base_message: str) -> List[str]:
    """Génère des variations sémantiques d'un message"""
    variations = [
        base_message,
        base_message.replace("je veux", "j'aimerais avoir"),
        base_message.replace("commander", "acheter"),
        base_message.replace("livraison", "expédition"),
        base_message.replace("prix", "coût"),
        base_message.replace("combien", "quel est le tarif"),
        base_message.replace("où", "dans quelle zone"),
        base_message.replace("comment", "de quelle manière"),
        base_message.replace("paiement", "règlement"),
        base_message.replace("confirmer", "valider")
    ]
    return list(set(variations))  # Supprimer les doublons

def run_conversation_test():
    """Exécute le test de conversation robuste"""
    print("🚀 DÉBUT DU TEST ULTIME DE COHÉRENCE CONVERSATIONNELLE")
    print(f"🕐 Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Objectif: Valider le processus de commande en 7 étapes")
    print(f"🏢 Company: Rue du Gros (MpfnlSbqwaZ6F4HvxQLRL9du0yG3)")
    
    tester = ConversationTester()
    
    # === PHASE 1: DÉMARRAGE CONVERSATION ===
    print(f"\n🔥 PHASE 1: DÉMARRAGE CONVERSATION")
    
    # Message d'accueil avec variation sémantique
    welcome_variations = [
        "Salut, j'ai besoin d'aide pour des couches",
        "Bonjour, je cherche des couches pour mon bébé",
        "Bonsoir, pouvez-vous m'aider avec des couches ?",
        "Hello, j'aimerais commander des couches"
    ]
    
    welcome_msg = random.choice(welcome_variations)
    response1 = tester.send_message(welcome_msg, "Accueil + Introduction")
    
    if "error" in response1:
        print("❌ ÉCHEC: Impossible de démarrer la conversation")
        return
    
    # === PHASE 2: IDENTIFICATION PRODUIT (Étape 1) ===
    print(f"\n🔥 PHASE 2: IDENTIFICATION PRODUIT")
    
    product_questions = [
        "Mon bébé a 6 mois et pèse 8kg, quelle taille me conseillez-vous ?",
        "J'ai besoin de couches pour un enfant de 2 ans qui fait 15kg",
        "Quelles sont vos couches les plus vendues ?",
        "Je veux des couches culottes, vous en avez ?",
        "Pouvez-vous me suggérer des couches pour jumeaux de 4 mois ?"
    ]
    
    for i, question in enumerate(product_questions):
        response = tester.send_message(question, f"Question produit {i+1}")
        if "error" not in response:
            analysis = tester.analyze_response(response.get("response", ""), "identification")
            print(f"📊 Analyse: {analysis}")
    
    # === PHASE 3: TEST DE COHÉRENCE CONVERSATIONNELLE ===
    print(f"\n🔥 PHASE 3: TEST COHÉRENCE CONVERSATIONNELLE")
    
    # Questions de suivi pour tester la mémoire conversationnelle
    follow_up_questions = [
        "Et pour la livraison, combien ça coûte ?",
        "Vous livrez à Yopougon ?",
        "C'est quoi vos tarifs de livraison ?",
        "Comment je peux payer ?",
        "Il faut un acompte ?"
    ]
    
    for question in follow_up_questions:
        response = tester.send_message(question, "Question de suivi")
        if "error" not in response:
            analysis = tester.analyze_response(response.get("response", ""), "suivi")
            print(f"📊 Cohérence: {analysis}")
    
    # === PHASE 4: TEST DE VARIATIONS SÉMANTIQUES ===
    print(f"\n🔥 PHASE 4: TEST VARIATIONS SÉMANTIQUES")
    
    base_question = "Je veux commander 2 paquets de couches taille 4"
    variations = generate_semantic_variations(base_question)
    
    for i, variation in enumerate(variations[:5]):  # Tester 5 variations
        response = tester.send_message(variation, f"Variation sémantique {i+1}")
        if "error" not in response:
            tester.semantic_variations += 1
            print(f"✅ Variation {i+1} comprise")
    
    # === PHASE 5: TEST DE CHANGEMENT D'INTENTION ===
    print(f"\n🔥 PHASE 5: TEST CHANGEMENT D'INTENTION")
    
    # Simuler un changement d'intention du client
    intention_switches = [
        ("Je veux commander", "En fait, je veux juste des infos"),
        ("C'est quoi vos prix ?", "Ah non, je veux commander maintenant"),
        ("Comment payer ?", "Attendez, je veux d'abord voir vos produits"),
        ("Vous livrez où ?", "Bon, finalement je prends pas"),
        ("C'est combien ?", "Ok je confirme ma commande")
    ]
    
    for original, switch in intention_switches:
        # Message original
        response1 = tester.send_message(original, "Intention originale")
        if "error" not in response1:
            print(f"📝 Réponse à '{original}': {response1.get('response', '')[:100]}...")
        
        # Changement d'intention
        response2 = tester.send_message(switch, "Changement d'intention")
        if "error" not in response2:
            tester.intent_switches += 1
            print(f"🔄 Switch détecté: '{switch}'")
            analysis = tester.analyze_response(response2.get("response", ""), "switch")
            print(f"📊 Adaptation: {analysis}")
    
    # === PHASE 6: PROCESSUS DE COMMANDE COMPLET ===
    print(f"\n🔥 PHASE 6: PROCESSUS DE COMMANDE COMPLET")
    
    command_steps = [
        "Je veux commander 3 paquets de couches taille 3",
        "Combien ça coûte au total avec la livraison ?",
        "Mon nom c'est Jean Kouassi, mon téléphone c'est 07 87 36 07 57",
        "Je suis à Cocody, près du CHU de Cocody",
        "Comment je peux payer avec Wave ?",
        "Pouvez-vous me faire un récapitulatif ?",
        "Oui je confirme ma commande"
    ]
    
    for i, step in enumerate(command_steps):
        response = tester.send_message(step, f"Étape commande {i+1}")
        if "error" not in response:
            analysis = tester.analyze_response(response.get("response", ""), f"etape_{i+1}")
            print(f"📊 Étape {i+1}: {analysis}")
    
    # === PHASE 7: TEST DE RÉSISTANCE ===
    print(f"\n🔥 PHASE 7: TEST DE RÉSISTANCE")
    
    resistance_tests = [
        "Je veux payer en espèces",
        "Vous livrez à l'étranger ?",
        "C'est trop cher, vous avez des réductions ?",
        "Je veux juste des échantillons gratuits",
        "Mon bébé fait 50kg, vous avez quelle taille ?",
        "Je veux payer en 10 fois",
        "Vous avez des couches de marque Pampers ?"
    ]
    
    for test in resistance_tests:
        response = tester.send_message(test, "Test de résistance")
        if "error" not in response:
            print(f"🛡️ Résistance: {response.get('response', '')[:150]}...")
    
    # === ANALYSE FINALE ===
    print(f"\n📊 ANALYSE FINALE DU TEST")
    print(f"{'='*80}")
    
    # Statistiques générales
    total_messages = len(tester.conversation_history)
    successful_responses = len([r for r in tester.conversation_history if "error" not in r])
    cache_hits = len([r for r in tester.conversation_history if r.get("cached", False)])
    
    print(f"📈 STATISTIQUES GÉNÉRALES:")
    print(f"  • Messages envoyés: {total_messages}")
    print(f"  • Réponses réussies: {successful_responses}")
    print(f"  • Taux de succès: {(successful_responses/total_messages)*100:.1f}%")
    print(f"  • Cache hits: {cache_hits}")
    print(f"  • Variations sémantiques testées: {tester.semantic_variations}")
    print(f"  • Changements d'intention: {tester.intent_switches}")
    
    # Progression du processus de commande
    etapes_completes = sum(tester.command_progress.values())
    print(f"\n🎯 PROGRESSION PROCESSUS DE COMMANDE:")
    print(f"  • Étapes complétées: {etapes_completes}/7")
    for etape, complete in tester.command_progress.items():
        status = "✅" if complete else "❌"
        print(f"  • {etape}: {status}")
    
    # Évaluation de la cohérence
    print(f"\n🧠 ÉVALUATION COHÉRENCE CONVERSATIONNELLE:")
    
    if etapes_completes >= 5:
        print(f"  ✅ EXCELLENT: Le RAG suit bien le processus de commande")
    elif etapes_completes >= 3:
        print(f"  🟡 BON: Le RAG suit partiellement le processus")
    else:
        print(f"  ❌ INSUFFISANT: Le RAG ne suit pas le processus")
    
    if tester.semantic_variations >= 3:
        print(f"  ✅ EXCELLENT: Comprend les variations sémantiques")
    else:
        print(f"  🟡 MODÉRÉ: Comprend partiellement les variations")
    
    if tester.intent_switches >= 3:
        print(f"  ✅ EXCELLENT: S'adapte aux changements d'intention")
    else:
        print(f"  🟡 MODÉRÉ: S'adapte partiellement aux changements")
    
    # Recommandations
    print(f"\n💡 RECOMMANDATIONS:")
    if etapes_completes < 7:
        print(f"  • Améliorer la détection des étapes de commande")
    if tester.semantic_variations < 5:
        print(f"  • Enrichir la compréhension sémantique")
    if tester.intent_switches < 3:
        print(f"  • Améliorer la gestion des changements d'intention")
    
    print(f"\n🎉 TEST ULTIME TERMINÉ!")
    print(f"📋 Rapport complet généré avec {total_messages} interactions")

if __name__ == "__main__":
    run_conversation_test()

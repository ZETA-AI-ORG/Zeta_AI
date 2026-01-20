#!/usr/bin/env python3
"""
🔥 TEST MARATHON CONVERSATIONNEL ULTRA-AGRESSIF
Objectif : Tester la capacité du RAG à maintenir une conversation longue
sans perte d'informations sur un parcours client complet
"""
import asyncio
import sys
import time
import json
from datetime import datetime
from typing import List, Dict, Any

sys.path.append("..")

# 🎯 SCÉNARIO MARATHON : INTERACTION CLIENT COMPLÈTE ULTRA-AGRESSIVE
# Simulation d'un client exigeant qui change d'avis, pose des questions complexes,
# revient sur ses décisions, demande des clarifications, etc.

MARATHON_CONVERSATION = [
    # === PHASE 1: PREMIER CONTACT & HÉSITATIONS ===
    {
        "message": "Bonjour, je cherche des couches pour mon bébé",
        "attentes": ["salutation", "produits", "questions_clarification"],
        "phase": "contact_initial"
    },
    {
        "message": "En fait, attendez, c'est pour ma grand-mère qui a des problèmes d'incontinence",
        "attentes": ["changement_contexte", "couches_adultes", "adaptation"],
        "phase": "changement_contexte_1"
    },
    {
        "message": "Non pardon, c'est bien pour mon bébé de 8 mois qui pèse 9kg",
        "attentes": ["retour_contexte_initial", "taille_recommandee", "coherence"],
        "phase": "retour_contexte"
    },
    {
        "message": "Mais j'aimerais aussi des couches pour ma grand-mère, vous en avez ?",
        "attentes": ["double_demande", "couches_adultes", "gestion_multiple"],
        "phase": "demande_multiple"
    },
    
    # === PHASE 2: EXPLORATION PRODUITS COMPLEXE ===
    {
        "message": "Quelles sont les différences entre vos couches à pression et culottes pour bébé ?",
        "attentes": ["comparaison_produits", "details_techniques", "conseil"],
        "phase": "exploration_produits"
    },
    {
        "message": "Mon bébé bouge beaucoup la nuit, que me conseillez-vous ?",
        "attentes": ["conseil_personnalise", "usage_nocturne", "adaptation_besoin"],
        "phase": "conseil_specifique"
    },
    {
        "message": "Et pour ma grand-mère, elle a besoin de taille XL, vous avez quoi ?",
        "attentes": ["retour_adultes", "tailles_disponibles", "coherence_demande"],
        "phase": "retour_adultes"
    },
    {
        "message": "Attendez, revenons au bébé. Il fait 9kg, quelle taille exactement ?",
        "attentes": ["retour_bebe", "taille_precise", "memoire_poids"],
        "phase": "precision_taille"
    },
    
    # === PHASE 3: NÉGOCIATION PRIX & QUANTITÉS ===
    {
        "message": "Combien coûte 1 paquet de couches taille 3 pour bébé ?",
        "attentes": ["prix_unitaire", "taille_3", "calcul_exact"],
        "phase": "demande_prix"
    },
    {
        "message": "Et si j'en prends 5 paquets, vous me faites une remise ?",
        "attentes": ["prix_degressif", "calcul_total", "promotion"],
        "phase": "negociation_quantite"
    },
    {
        "message": "En fait, je préfère commencer par 2 paquets pour tester",
        "attentes": ["changement_quantite", "nouveau_calcul", "flexibilite"],
        "phase": "reduction_quantite"
    },
    {
        "message": "Plus 3 paquets de couches adultes pour ma grand-mère",
        "attentes": ["ajout_adultes", "calcul_mixte", "gestion_panier"],
        "phase": "commande_mixte"
    },
    {
        "message": "Quel est le total de ma commande actuelle ?",
        "attentes": ["recapitulatif_complet", "calcul_total", "memoire_panier"],
        "phase": "demande_total"
    },
    
    # === PHASE 4: LIVRAISON COMPLIQUÉE ===
    {
        "message": "Je suis à Cocody, vous livrez là-bas ?",
        "attentes": ["zone_livraison", "cocody", "tarif_livraison"],
        "phase": "demande_livraison"
    },
    {
        "message": "Combien ça coûte la livraison à Cocody ?",
        "attentes": ["prix_livraison", "cocody", "ajout_frais"],
        "phase": "cout_livraison"
    },
    {
        "message": "En fait, je préfère être livré à Yopougon chez ma mère",
        "attentes": ["changement_adresse", "yopougon", "nouveau_tarif"],
        "phase": "changement_adresse"
    },
    {
        "message": "Non attendez, finalement Cocody c'est mieux. Quelle différence de prix ?",
        "attentes": ["retour_cocody", "comparaison_tarifs", "coherence"],
        "phase": "comparaison_zones"
    },
    {
        "message": "Si je commande maintenant, je peux être livré quand ?",
        "attentes": ["delai_livraison", "heure_actuelle", "planning"],
        "phase": "delai_livraison"
    },
    
    # === PHASE 5: PAIEMENT & HÉSITATIONS ===
    {
        "message": "Quels sont vos modes de paiement ?",
        "attentes": ["modes_paiement", "options_disponibles", "securite"],
        "phase": "modes_paiement"
    },
    {
        "message": "Je peux payer à la livraison ?",
        "attentes": ["paiement_livraison", "cod", "conditions"],
        "phase": "paiement_livraison"
    },
    {
        "message": "Il faut un acompte ? Combien ?",
        "attentes": ["acompte", "montant_acompte", "conditions"],
        "phase": "acompte"
    },
    {
        "message": "Je peux payer l'acompte par Wave ?",
        "attentes": ["wave", "acompte_wave", "numero_wave"],
        "phase": "acompte_wave"
    },
    
    # === PHASE 6: MODIFICATIONS DERNIÈRE MINUTE ===
    {
        "message": "En fait, je veux annuler les couches adultes, juste garder celles du bébé",
        "attentes": ["annulation_partielle", "nouveau_calcul", "flexibilite"],
        "phase": "modification_commande"
    },
    {
        "message": "Attendez, je change d'avis, je garde tout mais j'ajoute 1 paquet de plus pour bébé",
        "attentes": ["retour_commande_complete", "ajout_paquet", "nouveau_total"],
        "phase": "ajout_derniere_minute"
    },
    {
        "message": "Récapitulez-moi toute ma commande avec les prix détaillés",
        "attentes": ["recapitulatif_final", "details_complets", "coherence_totale"],
        "phase": "recapitulatif_final"
    },
    
    # === PHASE 7: QUESTIONS TECHNIQUES POUSSÉES ===
    {
        "message": "Les couches sont-elles hypoallergéniques ?",
        "attentes": ["caracteristiques_techniques", "allergie", "composition"],
        "phase": "questions_techniques"
    },
    {
        "message": "Quelle est la capacité d'absorption des couches taille 3 ?",
        "attentes": ["specifications_techniques", "absorption", "performance"],
        "phase": "specifications"
    },
    {
        "message": "Vous avez une garantie si les couches ne conviennent pas ?",
        "attentes": ["politique_retour", "garantie", "satisfaction"],
        "phase": "garantie"
    },
    
    # === PHASE 8: VALIDATION & DERNIÈRES VÉRIFICATIONS ===
    {
        "message": "Confirmez-moi l'adresse de livraison : c'était Cocody ou Yopougon ?",
        "attentes": ["verification_adresse", "memoire_changements", "cocody"],
        "phase": "verification_adresse"
    },
    {
        "message": "Et le délai de livraison si je confirme maintenant ?",
        "attentes": ["delai_final", "heure_commande", "planning_livraison"],
        "phase": "delai_final"
    },
    {
        "message": "Le numéro Wave pour l'acompte, c'est lequel déjà ?",
        "attentes": ["numero_wave", "memoire_paiement", "acompte"],
        "phase": "numero_wave"
    },
    {
        "message": "Parfait, je confirme ma commande. Donnez-moi le récapitulatif complet final",
        "attentes": ["confirmation_finale", "recapitulatif_complet", "coherence_totale"],
        "phase": "confirmation_finale"
    },
    
    # === PHASE 9: QUESTIONS POST-COMMANDE ===
    {
        "message": "J'aurai un numéro de suivi pour ma commande ?",
        "attentes": ["suivi_commande", "numero_suivi", "tracking"],
        "phase": "suivi_commande"
    },
    {
        "message": "Si j'ai un problème avec la livraison, qui je contacte ?",
        "attentes": ["support_client", "contact_probleme", "service_apres_vente"],
        "phase": "support_probleme"
    },
    {
        "message": "Je peux modifier ma commande après confirmation ?",
        "attentes": ["modification_post_commande", "flexibilite", "conditions"],
        "phase": "modification_post"
    },
    
    # === PHASE 10: TESTS DE COHÉRENCE EXTRÊME ===
    {
        "message": "Rappelez-moi, mon bébé fait combien de kilos déjà ?",
        "attentes": ["memoire_poids", "9kg", "coherence_longue"],
        "phase": "test_memoire_poids"
    },
    {
        "message": "Et j'avais commandé combien de paquets au final ?",
        "attentes": ["memoire_quantite", "calcul_final", "coherence"],
        "phase": "test_memoire_quantite"
    },
    {
        "message": "Le prix total avec livraison, c'était combien ?",
        "attentes": ["memoire_prix_total", "calcul_complet", "precision"],
        "phase": "test_memoire_prix"
    },
    {
        "message": "Et l'acompte à payer, c'est quel montant sur quel numéro ?",
        "attentes": ["memoire_acompte", "numero_wave", "montant_exact"],
        "phase": "test_memoire_acompte"
    },
    
    # === PHASE 11: QUESTIONS PIÈGES FINALES ===
    {
        "message": "Au fait, vous livrez aussi des couches pour chiens ?",
        "attentes": ["question_hors_sujet", "recentrage_metier", "coherence"],
        "phase": "question_piege_1"
    },
    {
        "message": "Et si je veux changer l'adresse de livraison pour Paris ?",
        "attentes": ["zone_impossible", "limitation_geographique", "explication"],
        "phase": "question_piege_2"
    },
    {
        "message": "Je peux payer en bitcoins ?",
        "attentes": ["mode_paiement_impossible", "alternatives", "coherence"],
        "phase": "question_piege_3"
    },
    
    # === PHASE 12: VALIDATION FINALE ULTIME ===
    {
        "message": "Parfait, merci. Pouvez-vous me faire un récapitulatif COMPLET de toute notre conversation et de ma commande finale ?",
        "attentes": ["recapitulatif_conversation", "memoire_complete", "coherence_totale"],
        "phase": "recapitulatif_conversation"
    }
]

# 📊 MÉTRIQUES DE COHÉRENCE CONVERSATIONNELLE
class ConversationCoherenceMetrics:
    def __init__(self):
        self.conversation_history = []
        self.memory_tests = []
        self.coherence_failures = []
        self.context_losses = []
        self.price_calculations = []
        self.address_changes = []
        self.product_changes = []
        self.response_times = []
        
    def add_exchange(self, question: str, response: str, response_time: float, phase: str):
        exchange = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase,
            "question": question,
            "response": response,
            "response_time": response_time,
            "exchange_number": len(self.conversation_history) + 1
        }
        self.conversation_history.append(exchange)
        self.response_times.append(response_time)
        
    def test_memory_coherence(self, question: str, response: str, expected_info: List[str]):
        """Teste si le système se souvient des informations importantes"""
        memory_test = {
            "question": question,
            "response": response,
            "expected_info": expected_info,
            "found_info": [],
            "missing_info": [],
            "coherence_score": 0
        }
        
        for info in expected_info:
            if info.lower() in response.lower():
                memory_test["found_info"].append(info)
            else:
                memory_test["missing_info"].append(info)
        
        memory_test["coherence_score"] = len(memory_test["found_info"]) / len(expected_info) * 100
        self.memory_tests.append(memory_test)
        
        if memory_test["coherence_score"] < 50:
            self.coherence_failures.append(memory_test)
    
    def detect_context_loss(self, question: str, response: str, phase: str):
        """Détecte les pertes de contexte"""
        context_indicators = {
            "bebe_9kg": ["9kg", "9 kg", "neuf kilos"],
            "cocody_address": ["cocody", "Cocody"],
            "wave_payment": ["wave", "Wave", "+225"],
            "taille_3": ["taille 3", "taille3", "T3"],
            "acompte_2000": ["2000", "2 000", "deux mille"]
        }
        
        for context_key, indicators in context_indicators.items():
            if any(indicator in question.lower() for indicator in indicators):
                if not any(indicator in response.lower() for indicator in indicators):
                    self.context_losses.append({
                        "phase": phase,
                        "lost_context": context_key,
                        "question": question[:100],
                        "response": response[:100]
                    })
    
    def analyze_price_coherence(self, response: str):
        """Analyse la cohérence des calculs de prix"""
        import re
        prices = re.findall(r'(\d+(?:\.\d+)?)\s*(?:F\s*)?CFA', response)
        if prices:
            self.price_calculations.append({
                "response": response[:200],
                "prices_found": prices,
                "timestamp": datetime.now().isoformat()
            })
    
    def print_detailed_report(self):
        print(f"\n{'='*100}")
        print(f"🔥 RAPPORT MARATHON CONVERSATIONNEL ULTRA-DÉTAILLÉ")
        print(f"{'='*100}")
        
        # Statistiques générales
        total_exchanges = len(self.conversation_history)
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        print(f"\n📊 STATISTIQUES GÉNÉRALES:")
        print(f"   • Total d'échanges: {total_exchanges}")
        print(f"   • Temps de réponse moyen: {avg_response_time:.2f}s")
        print(f"   • Durée totale conversation: {sum(self.response_times):.2f}s")
        
        # Tests de mémoire
        if self.memory_tests:
            avg_coherence = sum(test["coherence_score"] for test in self.memory_tests) / len(self.memory_tests)
            print(f"\n🧠 TESTS DE MÉMOIRE:")
            print(f"   • Tests effectués: {len(self.memory_tests)}")
            print(f"   • Score de cohérence moyen: {avg_coherence:.1f}%")
            print(f"   • Échecs de cohérence: {len(self.coherence_failures)}")
        
        # Pertes de contexte
        if self.context_losses:
            print(f"\n❌ PERTES DE CONTEXTE DÉTECTÉES ({len(self.context_losses)}):")
            for loss in self.context_losses[:5]:  # Top 5
                print(f"   • Phase {loss['phase']}: Perte de '{loss['lost_context']}'")
        
        # Calculs de prix
        if self.price_calculations:
            print(f"\n💰 CALCULS DE PRIX ({len(self.price_calculations)} détectés):")
            for calc in self.price_calculations[-3:]:  # 3 derniers
                print(f"   • Prix trouvés: {calc['prices_found']}")
        
        # Analyse par phase
        phases = {}
        for exchange in self.conversation_history:
            phase = exchange["phase"]
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(exchange)
        
        print(f"\n📋 ANALYSE PAR PHASE:")
        for phase, exchanges in phases.items():
            avg_time = sum(e["response_time"] for e in exchanges) / len(exchanges)
            print(f"   • {phase}: {len(exchanges)} échanges, {avg_time:.2f}s moyen")
        
        # Score global de performance
        coherence_score = avg_coherence if self.memory_tests else 100
        context_penalty = len(self.context_losses) * 10
        final_score = max(0, coherence_score - context_penalty)
        
        print(f"\n🎯 SCORE GLOBAL DE PERFORMANCE:")
        print(f"   • Score de cohérence: {coherence_score:.1f}%")
        print(f"   • Pénalité contexte: -{context_penalty}%")
        print(f"   • SCORE FINAL: {final_score:.1f}%")
        
        if final_score >= 90:
            print("   🟢 EXCELLENT - Mémoire conversationnelle exceptionnelle")
        elif final_score >= 75:
            print("   🟡 BON - Quelques pertes mineures de contexte")
        elif final_score >= 50:
            print("   🟠 MOYEN - Améliorations nécessaires")
        else:
            print("   🔴 CRITIQUE - Pertes majeures de contexte")
        
        # Détail des échecs critiques
        if self.coherence_failures:
            print(f"\n🚨 ÉCHECS CRITIQUES DE COHÉRENCE:")
            for failure in self.coherence_failures:
                print(f"   • Question: {failure['question'][:80]}...")
                print(f"     Informations manquantes: {failure['missing_info']}")
                print(f"     Score: {failure['coherence_score']:.1f}%")

async def run_conversation_marathon():
    """Lance le test marathon conversationnel"""
    print(f"🔥 DÉMARRAGE DU MARATHON CONVERSATIONNEL")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 {len(MARATHON_CONVERSATION)} échanges programmés")
    print(f"{'='*100}")
    
    from core.universal_rag_engine import UniversalRAGEngine
    rag = UniversalRAGEngine()
    metrics = ConversationCoherenceMetrics()
    
    # Variables de contexte pour tests de cohérence
    user_context = {
        "baby_weight": None,
        "baby_size": None,
        "delivery_address": None,
        "total_price": None,
        "payment_method": None,
        "order_items": []
    }
    
    for i, exchange in enumerate(MARATHON_CONVERSATION, 1):
        message = exchange["message"]
        phase = exchange["phase"]
        expected = exchange.get("attentes", [])
        
        print(f"\n🔥 ÉCHANGE {i}/{len(MARATHON_CONVERSATION)} - PHASE: {phase}")
        print(f"👤 CLIENT: {message}")
        
        start_time = time.time()
        try:
            # Recherche et génération de réponse
            search_results = await rag.search_sequential_sources(message, "MpfnlSbqwaZ6F4HvxQLRL9du0yG3")
            # Injection robuste de l'historique utilisateur dans search_results
            search_results['conversation_history'] = message if 'conversation_history' not in search_results else search_results['conversation_history']
            response = await rag.generate_response(
                message, 
                search_results, 
                "MpfnlSbqwaZ6F4HvxQLRL9du0yG3", 
                "Rue_du_gros", 
                "marathon_test_user"
            )
            
            response_time = time.time() - start_time
            
            print(f"🤖 GAMMA: {response[:200]}{'...' if len(response) > 200 else ''}")
            print(f"⏱️  Temps: {response_time:.2f}s")
            
            # Enregistrement de l'échange
            metrics.add_exchange(message, response, response_time, phase)
            
            # Tests de cohérence spécifiques
            metrics.test_memory_coherence(message, response, expected)
            metrics.detect_context_loss(message, response, phase)
            metrics.analyze_price_coherence(response)
            
            # Extraction d'informations contextuelles
            if "9kg" in message or "9 kg" in message:
                user_context["baby_weight"] = "9kg"
            if "cocody" in message.lower():
                user_context["delivery_address"] = "Cocody"
            if "yopougon" in message.lower():
                user_context["delivery_address"] = "Yopougon"
            
            # Pause courte entre échanges
            await asyncio.sleep(0.5)
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"ERREUR: {str(e)[:100]}"
            print(f"❌ {error_msg}")
            metrics.add_exchange(message, error_msg, response_time, phase)
    
    # Rapport final détaillé
    metrics.print_detailed_report()
    
    # Sauvegarde des résultats
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"marathon_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            "conversation_history": metrics.conversation_history,
            "memory_tests": metrics.memory_tests,
            "coherence_failures": metrics.coherence_failures,
            "context_losses": metrics.context_losses,
            "user_context": user_context
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Résultats sauvegardés dans: {filename}")

if __name__ == "__main__":
    asyncio.run(run_conversation_marathon())

#!/usr/bin/env python3
"""
🎯 TEST ULTIME RUE_DU_GROS - COUCHES BÉBÉ
Test complet basé sur les données réelles de l'entreprise Rue_du_gros
Secteur: Bébé & Puériculture - Spécialisé couches
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import List, Dict, Any

# Configuration
ENDPOINT_URL = "http://127.0.0.1:8001/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"  # RUE_DU_GROS

def log_test(message, data=None):
    """Log formaté pour les tests"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[TEST_RUE_DU_GROS][{timestamp}] {message}")
    if data:
        print(f"  📊 {json.dumps(data, indent=2, ensure_ascii=False)}")

class RueDuGrosUltimateTest:
    """
    Testeur ultime pour RUE_DU_GROS - Couches bébé
    """
    
    def __init__(self):
        self.test_results = []
        self.conversation_context = {}
        
    async def test_single_query(self, session, query, test_name, expected_elements=None, conversation_id=None):
        """
        Teste une requête unique sur l'endpoint
        """
        print(f"\n{'='*70}")
        print(f"📝 TEST: {test_name}")
        print(f"🔍 Requête: '{query}'")
        
        if expected_elements:
            print(f"🎯 Éléments attendus: {expected_elements}")
        
        payload = {
            "message": query,
            "company_id": COMPANY_ID,
            "user_id": "testuser123"
        }
        
        try:
            start_time = time.time()
            
            async with session.post(ENDPOINT_URL, json=payload) as response:
                end_time = time.time()
                duration = (end_time - start_time) * 1000
                
                if response.status == 200:
                    result = await response.json()
                    
                    # Analyser la réponse
                    response_text = result.get('response', '')
                    debug_info = result.get('debug_info', {})
                    
                    # Vérifier les éléments attendus
                    elements_found = []
                    if expected_elements:
                        for element in expected_elements:
                            if element.lower() in response_text.lower():
                                elements_found.append(element)
                    
                    # Analyser les performances
                    performance_score = self._calculate_performance_score(
                        duration, len(response_text), elements_found, expected_elements
                    )
                    
                    test_result = {
                        "test_name": test_name,
                        "query": query,
                        "status": "SUCCESS",
                        "duration_ms": round(duration, 1),
                        "response_length": len(response_text),
                        "elements_found": elements_found,
                        "elements_expected": expected_elements or [],
                        "performance_score": performance_score,
                        "response_preview": response_text[:300] + "..." if len(response_text) > 300 else response_text
                    }
                    
                    print(f"✅ SUCCÈS ({duration:.1f}ms)")
                    print(f"📄 Réponse: {len(response_text)} caractères")
                    print(f"🎯 Éléments trouvés: {elements_found}")
                    print(f"⭐ Score performance: {performance_score}/100")
                    print(f"💬 Aperçu: {response_text[:200]}...")
                    
                    # Afficher les infos de debug si disponibles
                    if debug_info:
                        rag_info = debug_info.get('rag_results', {})
                        if rag_info:
                            print(f"🔍 RAG - Documents trouvés: {rag_info.get('total_results', 'N/A')}")
                            print(f"🔍 RAG - Mode: {rag_info.get('mode', 'N/A')}")
                    
                    self.test_results.append(test_result)
                    return test_result
                    
                else:
                    error_text = await response.text()
                    print(f"❌ ERREUR HTTP {response.status}")
                    print(f"💥 Détails: {error_text[:200]}")
                    
                    test_result = {
                        "test_name": test_name,
                        "query": query,
                        "status": "ERROR",
                        "error": f"HTTP {response.status}: {error_text[:100]}"
                    }
                    
                    self.test_results.append(test_result)
                    return test_result
                    
        except Exception as e:
            print(f"💥 EXCEPTION: {str(e)}")
            
            test_result = {
                "test_name": test_name,
                "query": query,
                "status": "EXCEPTION",
                "error": str(e)
            }
            
            self.test_results.append(test_result)
            return test_result

    def _calculate_performance_score(self, duration_ms, response_length, elements_found, expected_elements):
        """
        Calcule un score de performance sur 100
        """
        score = 100
        
        # Pénalité durée (optimal < 3s, acceptable < 8s, lent > 15s)
        if duration_ms > 15000:
            score -= 40
        elif duration_ms > 8000:
            score -= 20
        elif duration_ms > 3000:
            score -= 10
        
        # Pénalité longueur réponse (trop courte < 80, trop longue > 1500)
        if response_length < 80:
            score -= 25
        elif response_length > 1500:
            score -= 15
        
        # Bonus éléments trouvés
        if expected_elements:
            found_ratio = len(elements_found) / len(expected_elements)
            score += int(found_ratio * 25)  # Bonus jusqu'à 25 points
        
        return max(0, min(100, score))

    async def run_ultimate_test_suite(self):
        """
        Lance la suite complète de tests RUE_DU_GROS
        """
        print("🚀 DÉMARRAGE TESTS ULTIME RUE_DU_GROS")
        print(f"🎯 URL: {ENDPOINT_URL}")
        print(f"🏢 Company ID: {COMPANY_ID}")
        print(f"🍼 Secteur: Bébé & Puériculture - Couches")
        
        # Tests spécifiques RUE_DU_GROS
        test_cases = [
            # === TESTS PRODUITS COUCHES ===
            {
                "name": "Prix Couches Taille 1 (nouveau-né)",
                "query": "combien coûtent les couches pour nouveau-né taille 1",
                "expected": ["taille 1", "17.900", "17900", "0 à 4 kg", "300 couches", "fcfa"]
            },
            {
                "name": "Prix Couches Taille 4 (populaire)",
                "query": "prix couches taille 4 pour enfant 10 kg",
                "expected": ["taille 4", "25.900", "25900", "9 à 14 kg", "300 couches", "fcfa"]
            },
            {
                "name": "Couches Culottes - Tarif dégressif",
                "query": "couches culottes prix pour 6 paquets",
                "expected": ["culottes", "6 paquets", "25.000", "25000", "4.150", "fcfa"]
            },
            {
                "name": "Couches Adultes - Gros volume",
                "query": "couches adultes 1 colis combien ça coûte",
                "expected": ["adultes", "1 colis", "240 unités", "216.000", "216000", "900", "fcfa"]
            },
            {
                "name": "Comparaison Tailles Couches",
                "query": "différence prix entre taille 3 et taille 6",
                "expected": ["taille 3", "taille 6", "22.900", "27.900", "différence", "5000"]
            },
            
            # === TESTS LIVRAISON SPÉCIFIQUES ===
            {
                "name": "Livraison Yopougon (zone spéciale)",
                "query": "livraison à Yopougon combien ça coûte",
                "expected": ["yopougon", "1000", "1.000", "fcfa", "livraison"]
            },
            {
                "name": "Livraison Cocody (centre Abidjan)",
                "query": "vous livrez à Cocody quel tarif",
                "expected": ["cocody", "1500", "1.500", "fcfa", "centre", "abidjan"]
            },
            {
                "name": "Livraison Hors Abidjan",
                "query": "livraison possible à Bouaké combien ça coûte",
                "expected": ["hors abidjan", "3500", "5000", "téléphone", "48h", "72h"]
            },
            {
                "name": "Délais Livraison Urgente",
                "query": "commande avant 11h livraison jour même possible",
                "expected": ["11h", "jour même", "avant", "livraison", "délai"]
            },
            
            # === TESTS PAIEMENT & COMMANDE ===
            {
                "name": "Paiement Wave Money",
                "query": "je peux payer avec wave money",
                "expected": ["wave", "paiement", "+2250787360757", "accepté"]
            },
            {
                "name": "Acompte Obligatoire",
                "query": "faut-il payer un acompte pour commander",
                "expected": ["acompte", "2000", "2.000", "fcfa", "obligatoire", "avant"]
            },
            {
                "name": "Processus Commande Gamma",
                "query": "comment passer commande avec gamma",
                "expected": ["gamma", "assistant", "commande", "automatique", "traitement"]
            },
            
            # === TESTS SUPPORT & CONTACT ===
            {
                "name": "Contact WhatsApp",
                "query": "numéro whatsapp pour commander",
                "expected": ["whatsapp", "+2250160924560", "contact", "commander"]
            },
            {
                "name": "Contact Téléphone Direct",
                "query": "numéro téléphone pour appeler directement",
                "expected": ["téléphone", "appel direct", "+2250787360757", "contact"]
            },
            {
                "name": "Horaires Support",
                "query": "à quelle heure je peux vous contacter",
                "expected": ["horaires", "toujours ouvert", "24h", "contact"]
            },
            
            # === TESTS POLITIQUE RETOUR ===
            {
                "name": "Politique de Retour",
                "query": "puis-je retourner les couches si problème",
                "expected": ["retour", "24h", "politique", "définitives", "confirmée"]
            },
            
            # === TESTS CONVERSATIONNELS COMPLEXES ===
            {
                "name": "Conseil Taille Bébé 8kg",
                "query": "mon bébé fait 8 kg quelle taille de couches choisir",
                "expected": ["8 kg", "taille 2", "taille 3", "3 à 8 kg", "6 à 11 kg", "conseil"]
            },
            {
                "name": "Commande Complète avec Livraison",
                "query": "je veux 2 paquets couches culottes livraison à Marcory total combien",
                "expected": ["2 paquets", "culottes", "9.800", "marcory", "1500", "total", "11.300"]
            },
            {
                "name": "Comparaison Économique Gros Volume",
                "query": "plus économique acheter 12 paquets ou 1 colis couches culottes",
                "expected": ["12 paquets", "1 colis", "48.000", "168.000", "économique", "4.000", "3.500"]
            },
            {
                "name": "Question Secteur Puériculture",
                "query": "vous vendez quoi d'autre que les couches pour bébé",
                "expected": ["bébé", "puériculture", "spécialisée", "couches", "gros", "détail"]
            },
            
            # === TEST IDENTITÉ ENTREPRISE ===
            {
                "name": "Présentation Entreprise",
                "query": "présentez-vous qui êtes-vous",
                "expected": ["rue_du_gros", "gamma", "côte d'ivoire", "couches", "bébé", "puériculture"]
            },
            {
                "name": "Mission Entreprise",
                "query": "quelle est votre mission",
                "expected": ["mission", "faciliter", "accès", "couches", "fiables", "confortables", "livraison"]
            }
        ]
        
        async with aiohttp.ClientSession() as session:
            success_count = 0
            total_duration = 0
            conversation_id = f"ultimate_test_{int(time.time())}"
            
            for i, test_case in enumerate(test_cases, 1):
                result = await self.test_single_query(
                    session,
                    test_case["query"],
                    f"{i:02d}. {test_case['name']}",
                    test_case["expected"],
                    conversation_id
                )
                
                if result["status"] == "SUCCESS":
                    success_count += 1
                    total_duration += result["duration_ms"]
                
                # Pause entre les tests pour éviter la surcharge
                await asyncio.sleep(1.5)
            
            # Statistiques finales
            self._display_final_statistics(success_count, len(test_cases), total_duration)

    def _display_final_statistics(self, success_count, total_tests, total_duration):
        """
        Affiche les statistiques finales
        """
        print(f"\n{'='*70}")
        print("🎉 RÉSULTATS FINAUX - RUE_DU_GROS ULTIMATE TEST")
        print(f"{'='*70}")
        
        success_rate = (success_count / total_tests) * 100
        avg_duration = total_duration / success_count if success_count > 0 else 0
        
        print(f"✅ Tests réussis: {success_count}/{total_tests} ({success_rate:.1f}%)")
        print(f"⏱️ Durée moyenne: {avg_duration:.1f}ms")
        print(f"📊 Durée totale: {total_duration:.1f}ms")
        
        # Analyse par performance
        successful_tests = [t for t in self.test_results if t["status"] == "SUCCESS"]
        if successful_tests:
            avg_score = sum(t["performance_score"] for t in successful_tests) / len(successful_tests)
            best_test = max(successful_tests, key=lambda x: x["performance_score"])
            worst_test = min(successful_tests, key=lambda x: x["performance_score"])
            
            print(f"⭐ Score moyen: {avg_score:.1f}/100")
            print(f"🏆 Meilleur test: {best_test['test_name']} ({best_test['performance_score']}/100)")
            print(f"⚠️ Test à améliorer: {worst_test['test_name']} ({worst_test['performance_score']}/100)")
        
        # Analyse par catégorie
        self._analyze_by_category()
        
        # Recommandations finales
        if success_rate >= 95:
            print("\n🎯 EXCELLENT! Système RUE_DU_GROS prêt pour la production")
            print("🍼 Toutes les fonctionnalités couches bébé opérationnelles")
        elif success_rate >= 85:
            print("\n👍 TRÈS BON! Quelques optimisations mineures recommandées")
        elif success_rate >= 70:
            print("\n⚠️ BON mais améliorations nécessaires")
        else:
            print("\n🚨 ATTENTION! Corrections majeures requises")
        
        # Détail des échecs
        failed_tests = [t for t in self.test_results if t["status"] != "SUCCESS"]
        if failed_tests:
            print(f"\n❌ TESTS ÉCHOUÉS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  - {test['test_name']}: {test.get('error', 'Erreur inconnue')}")

    def _analyze_by_category(self):
        """
        Analyse les résultats par catégorie de test
        """
        categories = {
            "Produits": ["Prix", "Couches", "Taille", "Comparaison"],
            "Livraison": ["Livraison", "Délais", "Yopougon", "Abidjan"],
            "Paiement": ["Paiement", "Wave", "Acompte", "Commande"],
            "Support": ["Contact", "WhatsApp", "Téléphone", "Horaires"],
            "Conversationnel": ["Conseil", "Complète", "Économique", "Secteur"],
            "Identité": ["Présentation", "Mission", "Entreprise"]
        }
        
        print(f"\n📊 ANALYSE PAR CATÉGORIE:")
        
        for category, keywords in categories.items():
            category_tests = [
                t for t in self.test_results 
                if any(keyword in t["test_name"] for keyword in keywords)
            ]
            
            if category_tests:
                success_count = len([t for t in category_tests if t["status"] == "SUCCESS"])
                success_rate = (success_count / len(category_tests)) * 100
                avg_score = sum(t.get("performance_score", 0) for t in category_tests if t["status"] == "SUCCESS")
                avg_score = avg_score / success_count if success_count > 0 else 0
                
                status_icon = "✅" if success_rate >= 90 else "⚠️" if success_rate >= 70 else "❌"
                print(f"  {status_icon} {category}: {success_count}/{len(category_tests)} ({success_rate:.0f}%) - Score: {avg_score:.0f}/100")

async def main():
    """
    Fonction principale
    """
    print("🍼 TEST ULTIME RUE_DU_GROS - COUCHES BÉBÉ & PUÉRICULTURE")
    print("=" * 70)
    print("🎯 Tests basés sur les données réelles de l'entreprise")
    print("📋 Couverture complète: Produits, Livraison, Paiement, Support")
    
    tester = RueDuGrosUltimateTest()
    await tester.run_ultimate_test_suite()

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
🔥 TEST EXTRÊME DU RAG - RUE_DU_GROSSISTE
Test exhaustif pour exposer toutes les limites du système
"""

import asyncio
import httpx
import time
from typing import Dict, List
from datetime import datetime

# Configuration
CHAT_ENDPOINT = "http://127.0.0.1:8001/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
USER_ID = "testuser173"

# Couleurs pour l'affichage
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

# ==========================================
# 🎯 BATTERIES DE TESTS
# ==========================================

TEST_SCENARIOS = {
    "1. QUESTIONS SÉMANTIQUES (compréhension profonde)": [
        {
            "question": "J'ai un bébé de 8kg, qu'est-ce que vous me proposez ?",
            "attendu": "taille 2 ou 3, couches à pression",
            "type": "inference_poids"
        },
        {
            "question": "Mon enfant grandit vite, il fait 15kg maintenant",
            "attendu": "taille 5 ou 6, couches à pression",
            "type": "inference_contexte"
        },
        {
            "question": "Qu'est-ce qui conviendrait pour un nouveau-né ?",
            "attendu": "taille 1, 0-4kg",
            "type": "inference_age"
        },
        {
            "question": "Je veux des couches faciles à mettre et enlever pour mon enfant qui bouge beaucoup",
            "attendu": "couches culottes",
            "type": "inference_besoin"
        },
    ],
    
    "2. QUESTIONS MOTS-CLÉS (matching exact)": [
        {
            "question": "Prix taille 3",
            "attendu": "20 500 ou 22 900",
            "type": "keyword_prix"
        },
        {
            "question": "Livraison Yopougon",
            "attendu": "1 500 FCFA",
            "type": "keyword_zone"
        },
        {
            "question": "Paiement Wave",
            "attendu": "+225 0787360757",
            "type": "keyword_methode"
        },
        {
            "question": "Contact WhatsApp",
            "attendu": "+225 0160924560",
            "type": "keyword_contact"
        },
    ],
    
    "3. QUESTIONS AMBIGUËS (clarification nécessaire)": [
        {
            "question": "C'est combien ?",
            "attendu": "clarification nécessaire",
            "type": "ambigu_produit"
        },
        {
            "question": "Vous livrez ?",
            "attendu": "zones ou prix livraison",
            "type": "ambigu_general"
        },
        {
            "question": "Ça coûte cher ?",
            "attendu": "fourchette de prix",
            "type": "ambigu_subjectif"
        },
        {
            "question": "C'est pour quand ?",
            "attendu": "délais livraison",
            "type": "ambigu_delai"
        },
    ],
    
    "4. QUESTIONS HORS CONTEXTE (hallucination risk)": [
        {
            "question": "Vous vendez des smartphones ?",
            "attendu": "Non, spécialisés couches bébé",
            "type": "hors_contexte_produit"
        },
        {
            "question": "Quel est le prix du Bitcoin aujourd'hui ?",
            "attendu": "désolé, hors contexte",
            "type": "hors_contexte_total"
        },
        {
            "question": "Vous livrez à Paris ?",
            "attendu": "Côte d'Ivoire uniquement",
            "type": "hors_contexte_geo"
        },
        {
            "question": "Donnez-moi une recette de pizza",
            "attendu": "hors contexte",
            "type": "hors_contexte_absurde"
        },
    ],
    
    "5. QUESTIONS PIÈGES (chiffres et calculs)": [
        {
            "question": "Si j'achète 5 paquets de couches culottes, ça fait combien ?",
            "attendu": "calcul ou suggestion lot",
            "type": "piege_calcul"
        },
        {
            "question": "Quelle est la différence de prix entre la taille 1 et la taille 6 ?",
            "attendu": "24 500 - 17 000 = 7 500",
            "type": "piege_difference"
        },
        {
            "question": "Je veux 1000 couches, combien de lots je dois commander ?",
            "attendu": "calcul lots",
            "type": "piege_quantite"
        },
        {
            "question": "Combien coûte la livraison à Cocody et Grand-Bassam ensemble ?",
            "attendu": "1 500 + 2 500",
            "type": "piege_cumul"
        },
    ],
    
    "6. QUESTIONS MULTI-INTENT (plusieurs infos demandées)": [
        {
            "question": "Je veux des couches taille 4, combien ça coûte et vous livrez à Abobo ?",
            "attendu": "prix taille 4 + livraison Abobo",
            "type": "multi_prix_livraison"
        },
        {
            "question": "Quels sont vos horaires et moyens de paiement acceptés ?",
            "attendu": "horaires + Wave",
            "type": "multi_horaires_paiement"
        },
        {
            "question": "Je suis à Port-Bouët, je veux payer par Wave, combien pour 300 couches taille 2 ?",
            "attendu": "prix + livraison + Wave",
            "type": "multi_complet"
        },
    ],
    
    "7. QUESTIONS NÉGATIVES (ce que vous ne faites PAS)": [
        {
            "question": "Vous acceptez Orange Money ?",
            "attendu": "Non, Wave uniquement",
            "type": "negatif_paiement"
        },
        {
            "question": "Vous avez une boutique physique ?",
            "attendu": "Non, en ligne uniquement",
            "type": "negatif_boutique"
        },
        {
            "question": "Vous livrez gratuitement ?",
            "attendu": "Non, frais de livraison",
            "type": "negatif_livraison"
        },
    ],
    
    "8. QUESTIONS CONVERSATIONNELLES (contexte implicite)": [
        {
            "question": "Salut, tu peux m'aider ?",
            "attendu": "accueil",
            "type": "conversationnel_salut"
        },
        {
            "question": "Merci beaucoup !",
            "attendu": "remerciement",
            "type": "conversationnel_merci"
        },
        {
            "question": "Je ne comprends pas",
            "attendu": "clarification",
            "type": "conversationnel_confusion"
        },
    ],
    
    "9. QUESTIONS AVEC FAUTES (robustesse typo)": [
        {
            "question": "combien coute les couche taille 5 ?",
            "attendu": "prix taille 5",
            "type": "typo_grammaire"
        },
        {
            "question": "livraison a youpougon",
            "attendu": "1 500 FCFA Yopougon",
            "type": "typo_ville"
        },
        {
            "question": "vous accceptez wave ?",
            "attendu": "Oui, Wave",
            "type": "typo_double_lettre"
        },
    ],
    
    "10. QUESTIONS LIMITES (edge cases)": [
        {
            "question": "Mon bébé fait 3.5kg, quelle taille ?",
            "attendu": "taille 1 ou 2",
            "type": "edge_poids_limite"
        },
        {
            "question": "Je commande à 11h tapantes, livré quand ?",
            "attendu": "jour même ou lendemain",
            "type": "edge_heure_limite"
        },
        {
            "question": "Je veux commander 1 seule couche",
            "attendu": "vendu par lot minimum",
            "type": "edge_quantite_mini"
        },
    ]
}

# ==========================================
# 🔧 FONCTIONS DE TEST
# ==========================================

async def ask_question(question: str, message_id: str = None) -> Dict:
    """Pose une question au chatbot"""
    if message_id is None:
        message_id = f"test_{int(time.time() * 1000)}"
    
    payload = {
        "company_id": COMPANY_ID,
        "user_id": USER_ID,
        "message": question,
        "message_id": message_id
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            start_time = time.time()
            response = await client.post(CHAT_ENDPOINT, json=payload)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                # Extraction correcte de la réponse
                response_data = data.get("response", {})
                if isinstance(response_data, dict):
                    response_text = response_data.get("response", "")
                else:
                    response_text = str(response_data)
                
                return {
                    "success": True,
                    "response": response_text,
                    "elapsed": elapsed,
                    "context": data.get("context", {}),
                    "raw": data
                }
            else:
                return {
                    "success": False,
                    "error": f"Status {response.status_code}",
                    "elapsed": elapsed
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "elapsed": 0
        }

def analyze_response(response_text: str, attendu: str, test_type: str) -> Dict:
    """Analyse la pertinence de la réponse"""
    response_lower = response_text.lower()
    attendu_lower = attendu.lower()
    
    # Critères de base
    is_relevant = False
    confidence = 0
    issues = []
    
    # 1. Vérification de la présence d'informations attendues
    keywords = attendu_lower.split()
    matches = sum(1 for kw in keywords if kw in response_lower)
    confidence = (matches / len(keywords)) * 100 if keywords else 0
    
    # 2. Détection de hallucination (prix inventés)
    import re
    # Pattern amélioré pour capturer prix complets avec séparateurs
    prices_in_response = re.findall(r'(\d{1,3}(?:[\s.,]?\d{3})*)\s*(?:FCFA|F\s*CFA|F\s+CFA)', response_text, re.IGNORECASE)
    
    # Liste complète des prix valides (avec variations d'espacement)
    valid_prices_base = [
        1500, 2000, 2500, 3500, 4000, 5000,  # Livraison + divers
        13500, 17000, 18500, 20500, 22500, 24000, 24500,  # Produits
        27000, 41000, 61500, 67500  # Calculs multiples (2×13500, 3×13500, etc.)
    ]
    
    valid_prices_str = set()
    for price in valid_prices_base:
        # Ajouter toutes les variations possibles
        valid_prices_str.add(str(price))  # 1500
        valid_prices_str.add(f"{price:,}".replace(",", " "))  # 1 500
        valid_prices_str.add(f"{price:,}".replace(",", "."))  # 1.500
        valid_prices_str.add(f"{price:,}".replace(",", ""))  # 1500
    
    for price in prices_in_response:
        price_clean = price.replace(" ", "").replace(".", "").replace(",", "")
        if price_clean and price_clean not in valid_prices_str and int(price_clean) not in valid_prices_base:
            # Vérifier si c'est un multiple valide (ex: 5 × 13500)
            is_valid_multiple = False
            for base_price in [13500, 17000, 18500, 20500, 22500, 24000, 24500]:
                if int(price_clean) % base_price == 0 and int(price_clean) / base_price <= 10:
                    is_valid_multiple = True
                    break
            
            if not is_valid_multiple:
                issues.append(f"❌ Prix suspect: {price} FCFA")
                confidence -= 20
    
    # 3. Vérifications spécifiques par type
    if "hors_contexte" in test_type:
        if any(word in response_lower for word in ["désolé", "ne peux pas", "spécialisé", "couches"]):
            is_relevant = True
            confidence += 30
    
    elif "keyword" in test_type:
        if matches >= len(keywords) / 2:
            is_relevant = True
    
    elif "inference" in test_type:
        if any(word in response_lower for word in ["taille", "kg", "couche"]):
            is_relevant = True
    
    elif "ambigu" in test_type:
        if any(word in response_lower for word in ["pourriez", "préciser", "quel", "?"]):
            is_relevant = True
            confidence += 20
    
    # 4. Détection de réponses vides ou génériques
    if len(response_text) < 20:
        issues.append("⚠️ Réponse trop courte")
        confidence -= 15
    
    if response_text == "Je peux vous aider ?" or "bonjour" in response_lower:
        issues.append("⚠️ Réponse trop générique")
        confidence -= 10
    
    # Score final
    confidence = max(0, min(100, confidence))
    is_relevant = confidence >= 40
    
    return {
        "is_relevant": is_relevant,
        "confidence": confidence,
        "issues": issues,
        "keyword_matches": matches,
        "total_keywords": len(keywords)
    }

def print_result(category: str, test: Dict, result: Dict, analysis: Dict):
    """Affiche le résultat d'un test avec RÉPONSE COMPLÈTE et SOURCES"""
    success_icon = f"{Colors.GREEN}✅{Colors.END}" if analysis["is_relevant"] else f"{Colors.RED}❌{Colors.END}"
    
    print(f"\n{success_icon} {Colors.BOLD}{test['question']}{Colors.END}")
    print(f"   Type: {Colors.CYAN}{test['type']}{Colors.END}")
    print(f"   Attendu: {Colors.YELLOW}{test['attendu']}{Colors.END}")
    print(f"   Temps: {Colors.MAGENTA}{result['elapsed']:.2f}s{Colors.END}")
    print(f"   Confiance: {Colors.BLUE}{analysis['confidence']:.0f}%{Colors.END}")
    
    if result["success"]:
        # Afficher la réponse COMPLÈTE (pas tronquée)
        response_text = result['response']
        print(f"\n   {Colors.GREEN}📝 RÉPONSE COMPLÈTE:{Colors.END}")
        # Indenter chaque ligne de la réponse
        for line in response_text.split('\n'):
            print(f"      {line}")
        
        # Afficher les SOURCES utilisées
        if 'raw' in result and 'response' in result['raw']:
            raw_response = result['raw']['response']
            if isinstance(raw_response, dict):
                # Documents trouvés
                if raw_response.get('documents_found'):
                    print(f"\n   {Colors.CYAN}📚 SOURCES UTILISÉES:{Colors.END}")
                    print(f"      Méthode: {raw_response.get('search_method', 'N/A')}")
                    
                    # Contexte utilisé
                    context = raw_response.get('context_used', '')
                    if context and context != 'Aucun':
                        print(f"\n      {Colors.YELLOW}📄 CONTEXTE:{Colors.END}")
                        # Limiter l'affichage du contexte à 500 caractères
                        if len(context) > 500:
                            print(f"         {context[:500]}...")
                            print(f"         {Colors.DIM}(+{len(context)-500} caractères){Colors.END}")
                        else:
                            for line in context.split('\n')[:10]:  # Max 10 lignes
                                print(f"         {line}")
                else:
                    print(f"\n   {Colors.YELLOW}⚠️  Aucun document source trouvé{Colors.END}")
    else:
        print(f"   {Colors.RED}ERREUR:{Colors.END} {result.get('error', 'Unknown')}")
    
    if analysis["issues"]:
        print(f"\n   {Colors.RED}⚠️  PROBLÈMES DÉTECTÉS:{Colors.END}")
        for issue in analysis["issues"]:
            print(f"      {issue}")

async def run_test_battery(category: str, tests: List[Dict]) -> Dict:
    """Exécute une batterie de tests"""
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{category}{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}")
    
    results = {
        "total": len(tests),
        "passed": 0,
        "failed": 0,
        "total_time": 0,
        "details": []
    }
    
    for i, test in enumerate(tests, 1):
        print(f"\n{Colors.CYAN}[{i}/{len(tests)}]{Colors.END}", end=" ")
        
        result = await ask_question(test["question"])
        results["total_time"] += result.get("elapsed", 0)
        
        if result["success"]:
            analysis = analyze_response(
                result["response"],
                test["attendu"],
                test["type"]
            )
            
            if analysis["is_relevant"]:
                results["passed"] += 1
            else:
                results["failed"] += 1
            
            print_result(category, test, result, analysis)
            results["details"].append({
                "test": test,
                "result": result,
                "analysis": analysis
            })
        else:
            results["failed"] += 1
            print(f"{Colors.RED}❌ ERREUR API: {result.get('error')}{Colors.END}")
        
        # Pause entre les tests
        await asyncio.sleep(0.5)
    
    return results

async def main():
    """Exécution principale"""
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}")
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║        🔥 TEST EXTRÊME RAG - RUE_DU_GROSSISTE 🔥                     ║")
    print("║                                                                       ║")
    print("║  Test exhaustif pour exposer TOUTES les limites du système          ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    print(f"\n{Colors.YELLOW}📊 Configuration:{Colors.END}")
    print(f"   Endpoint: {CHAT_ENDPOINT}")
    print(f"   Company: {COMPANY_ID}")
    print(f"   Total scénarios: {len(TEST_SCENARIOS)}")
    print(f"   Total questions: {sum(len(tests) for tests in TEST_SCENARIOS.values())}")
    
    input(f"\n{Colors.BOLD}Appuyez sur ENTRÉE pour commencer...{Colors.END}")
    
    start_time = time.time()
    all_results = {}
    
    # Exécution de toutes les batteries
    for category, tests in TEST_SCENARIOS.items():
        results = await run_test_battery(category, tests)
        all_results[category] = results
        
        # Résumé de la catégorie
        print(f"\n{Colors.BOLD}📊 Résumé {category}:{Colors.END}")
        print(f"   Réussis: {Colors.GREEN}{results['passed']}{Colors.END}/{results['total']}")
        print(f"   Échoués: {Colors.RED}{results['failed']}{Colors.END}/{results['total']}")
        print(f"   Temps total: {Colors.MAGENTA}{results['total_time']:.2f}s{Colors.END}")
        print(f"   Temps moyen: {Colors.MAGENTA}{results['total_time']/results['total']:.2f}s{Colors.END}")
    
    total_time = time.time() - start_time
    
    # ==========================================
    # 📊 RAPPORT FINAL
    # ==========================================
    print(f"\n\n{Colors.BOLD}{Colors.MAGENTA}")
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║                       📊 RAPPORT FINAL                                ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    total_tests = sum(r["total"] for r in all_results.values())
    total_passed = sum(r["passed"] for r in all_results.values())
    total_failed = sum(r["failed"] for r in all_results.values())
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n{Colors.BOLD}🎯 Résultats globaux:{Colors.END}")
    print(f"   Total tests: {total_tests}")
    print(f"   {Colors.GREEN}✅ Réussis: {total_passed} ({success_rate:.1f}%){Colors.END}")
    print(f"   {Colors.RED}❌ Échoués: {total_failed} ({100-success_rate:.1f}%){Colors.END}")
    print(f"   ⏱️  Temps total: {total_time:.2f}s")
    print(f"   ⚡ Temps moyen/test: {total_time/total_tests:.2f}s")
    
    print(f"\n{Colors.BOLD}📈 Performance par catégorie:{Colors.END}")
    for category, results in all_results.items():
        rate = (results["passed"] / results["total"] * 100) if results["total"] > 0 else 0
        color = Colors.GREEN if rate >= 70 else Colors.YELLOW if rate >= 50 else Colors.RED
        print(f"   {color}{category:<60} {rate:>5.1f}%{Colors.END}")
    
    # Note finale
    if success_rate >= 80:
        grade = f"{Colors.GREEN}A - EXCELLENT{Colors.END}"
        comment = "🎉 Ton RAG est solide !"
    elif success_rate >= 70:
        grade = f"{Colors.BLUE}B - TRÈS BON{Colors.END}"
        comment = "👍 Bonne performance globale"
    elif success_rate >= 60:
        grade = f"{Colors.YELLOW}C - BON{Colors.END}"
        comment = "⚠️ Quelques améliorations nécessaires"
    elif success_rate >= 50:
        grade = f"{Colors.YELLOW}D - MOYEN{Colors.END}"
        comment = "🔧 Travail nécessaire sur certains cas"
    else:
        grade = f"{Colors.RED}F - INSUFFISANT{Colors.END}"
        comment = "❌ Beaucoup d'améliorations nécessaires"
    
    print(f"\n{Colors.BOLD}🎓 NOTE FINALE: {grade}{Colors.END}")
    print(f"   {comment}")
    
    print(f"\n{Colors.MAGENTA}{'='*80}{Colors.END}\n")

if __name__ == "__main__":
    asyncio.run(main())

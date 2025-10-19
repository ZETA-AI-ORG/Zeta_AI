#!/usr/bin/env python3
"""
🧪 TEST RAG OPTIMISÉ - Focus sur les performances réelles
Sans calculs et conversationnel (à corriger plus tard)
Questions variées pour éviter le cache
"""
import asyncio
import httpx
import time
from typing import Dict, List

# Configuration
CHAT_ENDPOINT = "http://127.0.0.1:8001/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
# User ID avec format valide : testuser + 3 chiffres (variés pour éviter cache)
USER_ID = "testuser" + str(int(time.time() * 1000))[-3:]  # Ex: testuser847

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'

# ==========================================
# 🎯 TESTS OPTIMISÉS (40 questions)
# ==========================================

OPTIMIZED_TESTS = {
    "1. QUESTIONS PRODUITS (10)": [
        {"question": "Avez-vous des couches pour bébé de 7kg ?", "attendu": "taille 2 ou 3", "type": "produit_poids"},
        {"question": "Combien coûtent vos couches culottes ?", "attendu": "13500 ou 24000", "type": "produit_prix"},
        {"question": "Quelles tailles de couches proposez-vous ?", "attendu": "taille 1 à 6", "type": "produit_gamme"},
        {"question": "Les couches sont vendues par combien ?", "attendu": "150 ou 300 pièces", "type": "produit_lot"},
        {"question": "Quelle différence entre couches à pression et culottes ?", "attendu": "type usage", "type": "produit_difference"},
        {"question": "Prix d'un lot de 300 couches taille 4 ?", "attendu": "22500", "type": "produit_prix_specifique"},
        {"question": "Couches pour nouveau-né disponibles ?", "attendu": "taille 1", "type": "produit_age"},
        {"question": "Vendez-vous des couches adultes ?", "attendu": "non disponible", "type": "produit_categorie"},
        {"question": "Quelle est votre marque de couches ?", "attendu": "nom marque", "type": "produit_marque"},
        {"question": "Les couches sont-elles de bonne qualité ?", "attendu": "qualité garantie", "type": "produit_qualite"},
    ],
    
    "2. QUESTIONS LIVRAISON (10)": [
        {"question": "Frais de livraison pour Cocody ?", "attendu": "1500", "type": "livraison_zone"},
        {"question": "Vous livrez à Bingerville ?", "attendu": "oui 2000-2500", "type": "livraison_zone_periphe"},
        {"question": "Combien pour livrer à Adjamé ?", "attendu": "1500", "type": "livraison_zone_centrale"},
        {"question": "Livraison gratuite possible ?", "attendu": "non payant", "type": "livraison_gratuite"},
        {"question": "Quels sont vos délais de livraison ?", "attendu": "24-48h", "type": "livraison_delai"},
        {"question": "Prix livraison Grand-Bassam ?", "attendu": "2500 ou 3500", "type": "livraison_hors_abidjan"},
        {"question": "Vous livrez dans toute la Côte d'Ivoire ?", "attendu": "oui", "type": "livraison_couverture"},
        {"question": "Livraison express disponible ?", "attendu": "jour même si avant 11h", "type": "livraison_rapide"},
        {"question": "Où êtes-vous situés ?", "attendu": "en ligne uniquement", "type": "livraison_localisation"},
        {"question": "Comment suivre ma livraison ?", "attendu": "contact whatsapp", "type": "livraison_suivi"},
    ],
    
    "3. QUESTIONS PAIEMENT (8)": [
        {"question": "Quels moyens de paiement acceptez-vous ?", "attendu": "wave", "type": "paiement_methode"},
        {"question": "Puis-je payer en espèces ?", "attendu": "non wave uniquement", "type": "paiement_espece"},
        {"question": "Faut-il payer un acompte ?", "attendu": "2000 fcfa", "type": "paiement_acompte"},
        {"question": "Quel est votre numéro Wave ?", "attendu": "+225 078", "type": "paiement_numero"},
        {"question": "Je peux payer à la livraison ?", "attendu": "solde oui acompte avant", "type": "paiement_livraison"},
        {"question": "Vous acceptez Orange Money ?", "attendu": "non wave uniquement", "type": "paiement_orange"},
        {"question": "Carte bancaire acceptée ?", "attendu": "non wave", "type": "paiement_carte"},
        {"question": "Montant minimum pour commander ?", "attendu": "lot minimum", "type": "paiement_minimum"},
    ],
    
    "4. QUESTIONS CONTACT & SAV (7)": [
        {"question": "Comment vous contacter ?", "attendu": "whatsapp telephone", "type": "contact_general"},
        {"question": "Numéro WhatsApp ?", "attendu": "+225 016", "type": "contact_whatsapp"},
        {"question": "Horaires d'ouverture ?", "attendu": "toujours ouvert", "type": "contact_horaires"},
        {"question": "Puis-je échanger un produit défectueux ?", "attendu": "sav retour", "type": "sav_retour"},
        {"question": "Avez-vous un service client ?", "attendu": "oui whatsapp", "type": "sav_service"},
        {"question": "Que faire si je ne suis pas satisfait ?", "attendu": "contact sav", "type": "sav_satisfaction"},
        {"question": "Votre adresse email ?", "attendu": "contact disponible", "type": "contact_email"},
    ],
    
    "5. QUESTIONS HORS CONTEXTE (5)": [
        {"question": "Vendez-vous des jouets pour enfants ?", "attendu": "non couches uniquement", "type": "hors_produit"},
        {"question": "Vous livrez en France ?", "attendu": "non cote ivoire", "type": "hors_geo"},
        {"question": "Quelle heure est-il ?", "attendu": "hors contexte", "type": "hors_general"},
        {"question": "Proposez-vous des vêtements bébé ?", "attendu": "non couches", "type": "hors_categorie"},
        {"question": "Avez-vous des biberons ?", "attendu": "non specialises couches", "type": "hors_accessoire"},
    ],
}

# Liste prix valides pour détection hallucinations
VALID_PRICES = [
    1500, 2000, 2500, 3500, 4000, 5000,  # Livraison
    13500, 17000, 18500, 20500, 22500, 24000, 24500,  # Produits
]

async def ask_question(question: str) -> Dict:
    """Pose une question au chatbot"""
    payload = {
        "company_id": COMPANY_ID,
        "user_id": USER_ID,
        "message": question,
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            start_time = time.time()
            response = await client.post(CHAT_ENDPOINT, json=payload)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                response_data = data.get("response", {})
                if isinstance(response_data, dict):
                    response_text = response_data.get("response", "")
                else:
                    response_text = str(response_data)
                
                return {
                    "success": True,
                    "response": response_text,
                    "elapsed": elapsed,
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
    """Analyse simplifiée de la pertinence"""
    import re
    
    response_lower = response_text.lower()
    attendu_lower = attendu.lower()
    
    # Critères de base
    confidence = 0
    issues = []
    
    # 1. Vérification présence mots-clés
    keywords = attendu_lower.split()
    matches = sum(1 for kw in keywords if kw in response_lower)
    confidence = (matches / len(keywords)) * 100 if keywords else 0
    
    # 2. Détection hallucination prix (pattern amélioré)
    prices_in_response = re.findall(r'(\d{1,3}(?:[\s.,]?\d{3})*)\s*(?:FCFA|F\s*CFA|F\s+CFA)', response_text, re.IGNORECASE)
    
    for price in prices_in_response:
        price_clean = price.replace(" ", "").replace(".", "").replace(",", "")
        try:
            price_int = int(price_clean)
            # Vérifier si c'est un prix valide ou un multiple valide
            is_valid = price_int in VALID_PRICES
            if not is_valid:
                # Vérifier multiples valides
                for base_price in [13500, 17000, 18500, 20500, 22500, 24000, 24500]:
                    if price_int % base_price == 0 and price_int / base_price <= 10:
                        is_valid = True
                        break
            
            if not is_valid:
                issues.append(f"⚠️ Prix potentiellement incorrect: {price} FCFA")
                confidence -= 15
        except ValueError:
            pass
    
    # 3. Vérifications spécifiques par type
    if "hors" in test_type:
        if any(word in response_lower for word in ["désolé", "ne peux pas", "spécialisé", "couches uniquement"]):
            confidence += 30
    
    elif "livraison" in test_type or "contact" in test_type or "paiement" in test_type:
        if matches >= len(keywords) / 2:
            confidence += 20
    
    elif "produit" in test_type:
        if any(word in response_lower for word in ["couches", "taille", "pièces", "fcfa"]):
            confidence += 20
    
    is_relevant = confidence >= 40
    
    return {
        "is_relevant": is_relevant,
        "confidence": max(0, min(100, confidence)),
        "issues": issues,
        "keyword_matches": matches,
        "total_keywords": len(keywords)
    }

def print_result(test: Dict, result: Dict, analysis: Dict):
    """Affiche TOUT : question, réponse complète, sources documentaires"""
    success_icon = f"{Colors.GREEN}✅{Colors.END}" if analysis["is_relevant"] else f"{Colors.RED}❌{Colors.END}"
    
    print(f"\n{'='*100}")
    print(f"{success_icon} {Colors.BOLD}QUESTION: {test['question']}{Colors.END}")
    print(f"   Type: {Colors.CYAN}{test['type']}{Colors.END} | Attendu: {Colors.YELLOW}{test['attendu']}{Colors.END}")
    print(f"   Temps: {Colors.MAGENTA}{result['elapsed']:.2f}s{Colors.END} | Confiance analyse: {Colors.BLUE}{analysis['confidence']:.0f}%{Colors.END}")
    
    if not result["success"]:
        print(f"\n   {Colors.RED}❌ ERREUR:{Colors.END} {result.get('error', 'Unknown')}")
        return
    
    # ========================================
    # 1. RÉPONSE LLM COMPLÈTE (PAS DE TRONCATURE)
    # ========================================
    response_text = result['response']
    print(f"\n{Colors.GREEN}{Colors.BOLD}📝 RÉPONSE LLM COMPLÈTE:{Colors.END}")
    print(f"{Colors.GREEN}{'─'*100}{Colors.END}")
    for line in response_text.split('\n'):
        print(f"   {line}")
    print(f"{Colors.GREEN}{'─'*100}{Colors.END}")
    
    # ========================================
    # 2. DOCUMENTS SOURCES ENVOYÉS AU LLM
    # ========================================
    if 'raw' in result and 'response' in result['raw']:
        raw_response = result['raw']['response']
        
        if isinstance(raw_response, dict):
            # Méthode de recherche utilisée
            search_method = raw_response.get('search_method', 'N/A')
            docs_found = raw_response.get('documents_found', False)
            
            print(f"\n{Colors.CYAN}{Colors.BOLD}📚 SOURCES DOCUMENTAIRES:{Colors.END}")
            print(f"   Méthode: {Colors.CYAN}{search_method}{Colors.END}")
            print(f"   Documents trouvés: {Colors.CYAN}{'Oui' if docs_found else 'Non'}{Colors.END}")
            
            # Contexte utilisé (documents sources)
            context = raw_response.get('context_used', '')
            
            if context and context != 'Aucun':
                print(f"\n{Colors.YELLOW}{Colors.BOLD}📄 CONTEXTE ENVOYÉ AU LLM:{Colors.END}")
                print(f"{Colors.YELLOW}{'─'*100}{Colors.END}")
                
                # Afficher TOUT le contexte (pas de limite)
                for line in context.split('\n'):
                    print(f"   {line}")
                
                print(f"{Colors.YELLOW}{'─'*100}{Colors.END}")
                print(f"   {Colors.DIM}Taille contexte: {len(context)} caractères{Colors.END}")
            else:
                print(f"\n   {Colors.YELLOW}⚠️  Aucun document source trouvé{Colors.END}")
        else:
            print(f"\n   {Colors.YELLOW}⚠️  Format réponse inattendu{Colors.END}")
    else:
        print(f"\n   {Colors.YELLOW}⚠️  Métadonnées sources non disponibles{Colors.END}")
    
    # ========================================
    # 3. PROBLÈMES DÉTECTÉS (SI PRÉSENTS)
    # ========================================
    if analysis["issues"]:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️  PROBLÈMES DÉTECTÉS:{Colors.END}")
        for issue in analysis["issues"]:
            print(f"   {issue}")
    
    print(f"\n{'='*100}\n")

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
            analysis = analyze_response(result["response"], test["attendu"], test["type"])
            
            if analysis["is_relevant"]:
                results["passed"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "test": test,
                "result": result,
                "analysis": analysis
            })
            
            print_result(test, result, analysis)
        else:
            results["failed"] += 1
            print(f"{Colors.RED}❌ ERREUR:{Colors.END} {result.get('error')}")
        
        # Pause entre requêtes pour éviter rate limiting Groq (6000 TPM)
        # 40 questions × 1800 tokens = 72,000 tokens
        # Pour rester sous 6000 TPM: 72,000 ÷ 6000 = 12 min minimum
        # 12 min ÷ 40 questions = 18s par question minimum
        await asyncio.sleep(2.0)  # 2s entre chaque + temps traitement = safe
    
    # Résumé catégorie
    success_rate = (results["passed"] / results["total"]) * 100
    print(f"\n{Colors.BOLD}📊 Résumé {category}:{Colors.END}")
    print(f"   Réussis: {Colors.GREEN}{results['passed']}/{results['total']}{Colors.END}")
    print(f"   Échoués: {Colors.RED}{results['failed']}/{results['total']}{Colors.END}")
    print(f"   Taux: {Colors.BLUE}{success_rate:.1f}%{Colors.END}")
    print(f"   Temps total: {results['total_time']:.2f}s")
    print(f"   Temps moyen: {results['total_time']/results['total']:.2f}s")
    
    return results

async def main():
    """Fonction principale"""
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}🧪 TEST RAG OPTIMISÉ - RUE_DU_GROSSISTE{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"\n📊 Configuration:")
    print(f"   Endpoint: {CHAT_ENDPOINT}")
    print(f"   Company: {COMPANY_ID}")
    print(f"   User: {USER_ID} (unique)")
    print(f"   Total: {sum(len(tests) for tests in OPTIMIZED_TESTS.values())} questions")
    
    input("\nAppuyez sur ENTRÉE pour commencer...")
    
    all_results = {}
    total_tests = 0
    total_passed = 0
    total_time = 0
    
    for category, tests in OPTIMIZED_TESTS.items():
        results = await run_test_battery(category, tests)
        all_results[category] = results
        total_tests += results["total"]
        total_passed += results["passed"]
        total_time += results["total_time"]
    
    # RAPPORT FINAL
    print(f"\n\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}📊 RAPPORT FINAL{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}")
    
    print(f"\n🎯 Résultats globaux:")
    success_rate = (total_passed / total_tests) * 100
    print(f"   Total tests: {total_tests}")
    print(f"   ✅ Réussis: {total_passed} ({success_rate:.1f}%)")
    print(f"   ❌ Échoués: {total_tests - total_passed} ({100-success_rate:.1f}%)")
    print(f"   ⏱️  Temps total: {total_time:.2f}s")
    print(f"   ⚡ Temps moyen/test: {total_time/total_tests:.2f}s")
    
    print(f"\n📈 Performance par catégorie:")
    for category, results in all_results.items():
        rate = (results["passed"] / results["total"]) * 100
        icon = "🟢" if rate >= 70 else "🟡" if rate >= 50 else "🔴"
        print(f"   {icon} {category:55} {rate:5.1f}%")
    
    # Note finale
    if success_rate >= 80:
        grade = "A - EXCELLENT"
    elif success_rate >= 70:
        grade = "B - BON"
    elif success_rate >= 60:
        grade = "C - MOYEN"
    else:
        grade = "D - À AMÉLIORER"
    
    print(f"\n🎓 NOTE FINALE: {Colors.BOLD}{grade}{Colors.END}")
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(main())

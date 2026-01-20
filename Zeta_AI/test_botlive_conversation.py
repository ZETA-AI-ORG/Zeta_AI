"""
🧪 TEST CONVERSATIONNEL BOTLIVE - Simulation conversation réelle
Teste le flux complet : Produit → Quantité → Paiement → Zone → Confirmation
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, Any, List

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

API_URL = "http://127.0.0.1:8002/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
USER_ID = "testuser301"

# URLs des images de test
IMAGE_PRODUIT = "https://scontent.xx.fbcdn.net/v/t1.15752-9/555093895_1506934760640757_7691238582667886705_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=kDcMQu-KK7UQ7kNvwEZy_Sa&_nc_oc=Admrj1kORWldgvUTjDrjJPtKXzzI7yOdEEeTRj3U6gm081XFk4OXWJPvxscHf17n282JSOKe1c-YlxdPALQp2oH5&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gEnLOFlNSwtbPciYqrsBG0XtHmSNcTp7TSzawows_cmpg&oe=690CE0BF"
IMAGE_PAIEMENT = "https://ilbihprkxcgsigvueeme.supabase.co/storage/v1/object/public/product-images/botlive/MpfnlSbqwaZ6F4HvxQLRL9du0yG3/2025/10/07/botlive_lv58r6zz.jpg"

# Scénario de conversation
CONVERSATION_SCENARIO = [
    {
        "step": 1,
        "name": "Salutation",
        "message": "Bonjour",
        "images": [],
        "expected_keywords": ["photo", "produit", "commander"],
        "expected_step": 1
    },
    {
        "step": 2,
        "name": "Envoi produit",
        "message": "",
        "images": [IMAGE_PRODUIT],
        "expected_keywords": ["noté", "tout", "autres"],
        "expected_step": 2
    },
    {
        "step": 3,
        "name": "Confirmation produit",
        "message": "Oui c'est tout",
        "images": [],
        "expected_keywords": ["combien", "quantité", "voulez"],
        "expected_step": 2
    },
    {
        "step": 4,
        "name": "Quantité",
        "message": "2",
        "images": [],
        "expected_keywords": ["2 unités", "paiement", "2000", "0787360757"],
        "expected_step": 3
    },
    {
        "step": 5,
        "name": "Envoi preuve paiement",
        "message": "",
        "images": [IMAGE_PAIEMENT],
        "expected_keywords": ["reçu", "validé", "acompte", "commune", "zone"],
        "expected_step": 4
    },
    {
        "step": 6,
        "name": "Zone livraison",
        "message": "Cocody",
        "images": [],
        "expected_keywords": ["finalisée", "commande", "SMS", "24h", "recontacte"],
        "expected_step": 5
    }
]

# ═══════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════

def print_separator(char="═", length=80):
    """Affiche un séparateur"""
    print(char * length)

def print_header(text: str):
    """Affiche un en-tête coloré"""
    print(f"\n\033[96m{'='*80}\033[0m")
    print(f"\033[96m{text.center(80)}\033[0m")
    print(f"\033[96m{'='*80}\033[0m\n")

def print_step(step_num: int, step_name: str):
    """Affiche le numéro d'étape"""
    print(f"\n\033[93m📍 ÉTAPE {step_num}: {step_name}\033[0m")
    print_separator("─")

def print_user_message(message: str, images: List[str]):
    """Affiche le message utilisateur"""
    print(f"\033[94m👤 UTILISATEUR:\033[0m")
    if message:
        print(f"   Message: {message}")
    if images:
        print(f"   Images: {len(images)} image(s)")
        for img in images:
            print(f"     - {img[:80]}...")

def print_llm_response(response_data: Dict[str, Any]):
    """Affiche la réponse du LLM avec extraction thinking/response"""
    response_text = response_data.get("response", {}).get("response", str(response_data))
    
    # Extraire thinking et response
    import re
    thinking_match = re.search(r'<thinking>(.*?)</thinking>', response_text, re.DOTALL)
    response_match = re.search(r'<response>(.*?)</response>', response_text, re.DOTALL)
    
    print(f"\n\033[92m🤖 ASSISTANT:\033[0m")
    
    # Thinking (jaune)
    if thinking_match:
        thinking = thinking_match.group(1).strip()
        print(f"\n\033[93m💭 RAISONNEMENT:\033[0m")
        print(f"\033[93m{thinking}\033[0m")
    else:
        print(f"\n\033[93m💭 RAISONNEMENT: [Pas de balise <thinking>]\033[0m")
    
    # Response (vert)
    if response_match:
        response = response_match.group(1).strip()
        print(f"\n\033[92m💬 RÉPONSE CLIENT:\033[0m")
        print(f"\033[92m{response}\033[0m")
    else:
        print(f"\n\033[92m💬 RÉPONSE CLIENT (sans balise):\033[0m")
        print(f"\033[92m{response_text[:300]}...\033[0m")
    
    return thinking_match.group(1).strip() if thinking_match else "", \
           response_match.group(1).strip() if response_match else response_text

def validate_response(thinking: str, response: str, expected_keywords: List[str], expected_step: int) -> Dict[str, Any]:
    """Valide la réponse du LLM"""
    validation = {
        "keywords_found": [],
        "keywords_missing": [],
        "step_detected": None,
        "step_correct": False,
        "has_thinking": bool(thinking),
        "has_response": bool(response),
        "score": 0
    }
    
    # Vérifier mots-clés
    response_lower = response.lower()
    for keyword in expected_keywords:
        if keyword.lower() in response_lower:
            validation["keywords_found"].append(keyword)
        else:
            validation["keywords_missing"].append(keyword)
    
    # Détecter l'étape dans le thinking
    if thinking:
        if "Étape=1" in thinking or "Étape actuelle: 1" in thinking:
            validation["step_detected"] = 1
        elif "Étape=2" in thinking or "Étape actuelle: 2" in thinking:
            validation["step_detected"] = 2
        elif "Étape=3" in thinking or "Étape actuelle: 3" in thinking:
            validation["step_detected"] = 3
        elif "Étape=4" in thinking or "Étape actuelle: 4" in thinking:
            validation["step_detected"] = 4
        elif "Étape=5" in thinking or "Étape actuelle: 5" in thinking:
            validation["step_detected"] = 5
    
    validation["step_correct"] = (validation["step_detected"] == expected_step)
    
    # Calculer score
    score = 0
    if validation["has_thinking"]:
        score += 20
    if validation["has_response"]:
        score += 20
    if validation["keywords_found"]:
        score += (len(validation["keywords_found"]) / len(expected_keywords)) * 40
    if validation["step_correct"]:
        score += 20
    
    validation["score"] = round(score, 1)
    
    return validation

def print_validation(validation: Dict[str, Any]):
    """Affiche les résultats de validation"""
    print(f"\n\033[95m🔍 VALIDATION:\033[0m")
    print(f"   Format thinking: {'✅' if validation['has_thinking'] else '❌'}")
    print(f"   Format response: {'✅' if validation['has_response'] else '❌'}")
    print(f"   Étape détectée: {validation['step_detected']} {'✅' if validation['step_correct'] else '❌'}")
    print(f"   Mots-clés trouvés: {len(validation['keywords_found'])}/{len(validation['keywords_found']) + len(validation['keywords_missing'])}")
    if validation['keywords_found']:
        print(f"     ✅ {', '.join(validation['keywords_found'])}")
    if validation['keywords_missing']:
        print(f"     ❌ {', '.join(validation['keywords_missing'])}")
    
    # Score avec couleur
    score = validation['score']
    if score >= 80:
        color = "\033[92m"  # Vert
    elif score >= 60:
        color = "\033[93m"  # Jaune
    else:
        color = "\033[91m"  # Rouge
    
    print(f"\n   {color}📊 SCORE: {score}/100\033[0m")

# ═══════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE DE TEST
# ═══════════════════════════════════════════════════════════════

async def send_message(message: str, images: List[str]) -> Dict[str, Any]:
    """Envoie un message à l'API"""
    payload = {
        "company_id": COMPANY_ID,
        "user_id": USER_ID,
        "message": message,
        "images": images,
        "botlive_enabled": True,  # ✅ ACTIVER BOTLIVE
        "rag_enabled": True       # ✅ ACTIVER RAG
    }
    
    print(f"📤 Payload envoyé: botlive_enabled={payload['botlive_enabled']}, rag_enabled={payload['rag_enabled']}")
    
    async with httpx.AsyncClient(timeout=120.0) as client:  # ✅ 2 minutes pour vision
        response = await client.post(API_URL, json=payload)
        response.raise_for_status()
        return response.json()

async def run_conversation_test():
    """Exécute le test conversationnel complet"""
    print_header("🧪 TEST CONVERSATIONNEL BOTLIVE")
    
    start_time = datetime.now()
    results = []
    total_score = 0
    
    print(f"📋 Scénario: {len(CONVERSATION_SCENARIO)} étapes")
    print(f"🎯 Objectif: Tester le flux complet de commande")
    print(f"⏰ Début: {start_time.strftime('%H:%M:%S')}\n")
    
    # Exécuter chaque étape
    for scenario in CONVERSATION_SCENARIO:
        step_num = scenario["step"]
        step_name = scenario["name"]
        message = scenario["message"]
        images = scenario["images"]
        expected_keywords = scenario["expected_keywords"]
        expected_step = scenario["expected_step"]
        
        print_step(step_num, step_name)
        print_user_message(message, images)
        
        try:
            # Envoyer le message
            print(f"\n⏳ Envoi de la requête...")
            response_data = await send_message(message, images)
            
            # Afficher la réponse
            thinking, response = print_llm_response(response_data)
            
            # Valider la réponse
            validation = validate_response(thinking, response, expected_keywords, expected_step)
            print_validation(validation)
            
            # Enregistrer les résultats
            results.append({
                "step": step_num,
                "name": step_name,
                "validation": validation,
                "thinking": thinking[:200] + "..." if len(thinking) > 200 else thinking,
                "response": response
            })
            
            total_score += validation["score"]
            
            # Pause entre les messages
            if step_num < len(CONVERSATION_SCENARIO):
                await asyncio.sleep(2)
        
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"\n\033[91m❌ ERREUR: {e}\033[0m")
            print(f"\033[91m📋 Détail:\n{error_detail}\033[0m")
            results.append({
                "step": step_num,
                "name": step_name,
                "error": str(e),
                "error_detail": error_detail
            })
    
    # ═══════════════════════════════════════════════════════════════
    # RAPPORT FINAL
    # ═══════════════════════════════════════════════════════════════
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    avg_score = total_score / len(CONVERSATION_SCENARIO)
    
    print_header("📊 RAPPORT FINAL")
    
    print(f"⏱️  Durée totale: {duration:.1f}s")
    print(f"📈 Score moyen: {avg_score:.1f}/100")
    print(f"✅ Étapes réussies: {sum(1 for r in results if r.get('validation', {}).get('score', 0) >= 60)}/{len(results)}")
    
    print(f"\n📋 DÉTAIL PAR ÉTAPE:")
    print_separator("─")
    
    for result in results:
        step = result["step"]
        name = result["name"]
        
        if "error" in result:
            print(f"   {step}. {name}: \033[91m❌ ERREUR - {result['error']}\033[0m")
        else:
            validation = result["validation"]
            score = validation["score"]
            
            if score >= 80:
                status = "\033[92m✅ EXCELLENT\033[0m"
            elif score >= 60:
                status = "\033[93m⚠️  ACCEPTABLE\033[0m"
            else:
                status = "\033[91m❌ ÉCHEC\033[0m"
            
            print(f"   {step}. {name}: {status} ({score}/100)")
            print(f"      Thinking: {'✅' if validation['has_thinking'] else '❌'} | "
                  f"Response: {'✅' if validation['has_response'] else '❌'} | "
                  f"Étape: {'✅' if validation['step_correct'] else '❌'}")
    
    # Verdict final
    print(f"\n{'='*80}")
    if avg_score >= 80:
        print(f"\033[92m🎉 SUCCÈS ! Le système Botlive fonctionne correctement.\033[0m")
    elif avg_score >= 60:
        print(f"\033[93m⚠️  ACCEPTABLE. Quelques améliorations nécessaires.\033[0m")
    else:
        print(f"\033[91m❌ ÉCHEC. Le système nécessite des corrections majeures.\033[0m")
    print(f"{'='*80}\n")
    
    # Sauvegarder le rapport
    report_file = f"test_botlive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "average_score": avg_score,
            "results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Rapport sauvegardé: {report_file}")

# ═══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        asyncio.run(run_conversation_test())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()

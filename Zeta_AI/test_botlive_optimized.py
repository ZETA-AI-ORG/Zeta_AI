#!/usr/bin/env python3
"""
🧪 TEST BOTLIVE OPTIMISÉ - Basé sur le prompt réel
Teste les règles critiques, cas limites et robustesse du système
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
USER_ID = "testuser771"

# URLs des images de test
IMAGE_PRODUIT = "https://scontent.xx.fbcdn.net/v/t1.15752-9/555093895_1506934760640757_7691238582667886705_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=kDcMQu-KK7UQ7kNvwEZy_Sa&_nc_oc=Admrj1kORWldgvUTjDrjJPtKXzzI7yOdEEeTRj3U6gm081XFk4OXWJPvxscHf17n282JSOKe1c-YlxdPALQp2oH5&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gEnLOFlNSwtbPciYqrsBG0XtHmSNcTp7TSzawows_cmpg&oe=690CE0BF"
IMAGE_PAIEMENT_VALIDE = "https://ilbihprkxcgsigvueeme.supabase.co/storage/v1/object/public/product-images/botlive/MpfnlSbqwaZ6F4HvxQLRL9du0yG3/2025/10/07/botlive_lv58r6zz.jpg"
IMAGE_PAIEMENT_INSUFFISANT = "https://scontent.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215345539018_n.jpg"

# ═══════════════════════════════════════════════════════════════
# SCÉNARIOS DE TEST OPTIMISÉS
# ═══════════════════════════════════════════════════════════════

TEST_SCENARIOS = [
    # ═══ WORKFLOW NORMAL ═══
    {
        "name": "🎯 WORKFLOW COMPLET NORMAL",
        "steps": [
            {
                "step": 0,
                "name": "Salutation initiale",
                "message": "Salut",
                "images": [],
                "expected_thinking": ["Produit=✗", "Étape=0", "Action=demander photo produit"],
                "expected_response": ["photo", "produit"],
                "critical_rules": [1, 8]  # Consulter historique + progresser 0→5
            },
            {
                "step": 1,
                "name": "Envoi produit",
                "message": "",
                "images": [IMAGE_PRODUIT],
                "expected_thinking": ["Produit=✓ VISION", "Étape=1", "Action=demander confirmation"],
                "expected_response": ["photo reçue", "c'est bien", "produit", "dépôt", "2000"],
                "critical_rules": [4, 13]  # Jamais nom produit + confirmation générique
            },
            {
                "step": 2,
                "name": "Confirmation produit + détails",
                "message": "Oui je vais en prendre 3 paquets",
                "images": [],
                "expected_thinking": ["Produit=✓", "Détails=✓", "Étape=2", "Action=demander"],
                "expected_response": ["noté", "3", "capture", "dépôt"],
                "critical_rules": [2, 3]  # MESSAGE > HISTORIQUE + nouveaux détails
            },
            {
                "step": 3,
                "name": "Paiement valide",
                "message": "",
                "images": [IMAGE_PAIEMENT_VALIDE],
                "expected_thinking": ["Paiement=✓", "≥ 2000", "Étape=3", "Action=valider"],
                "expected_response": ["dépôt validé", "adresse", "numéro"],
                "critical_rules": [11]  # Validation paiement
            },
            {
                "step": 4,
                "name": "Adresse Cocody",
                "message": "Cocody",
                "images": [],
                "expected_thinking": ["Adresse=✓", "Étape=4", "Action=demander numéro"],
                "expected_response": ["cocody", "1500", "numéro"],
                "critical_rules": [5]  # Commune → frais exact
            },
            {
                "step": 5,
                "name": "Numéro final",
                "message": "0140236939",
                "images": [],
                "expected_thinking": ["Téléphone=✓", "Étape=5", "Action=confirmer"],
                "expected_response": ["c'est bon", "commande ok", "1500", "24h"],
                "critical_rules": [8]  # Progresser 0→5
            }
        ]
    },
    
    # ═══ CAS LIMITES CRITIQUES ═══
    {
        "name": "⚠️ RÈGLES CRITIQUES - PAIEMENT",
        "steps": [
            {
                "step": 0,
                "name": "Setup produit",
                "message": "Bonjour",
                "images": [IMAGE_PRODUIT],
                "expected_thinking": ["Produit=✓"],
                "expected_response": ["photo reçue"],
                "critical_rules": []
            },
            {
                "step": 1,
                "name": "Confirmation produit",
                "message": "Oui",
                "images": [],
                "expected_thinking": ["Produit=✓"],
                "expected_response": ["capture", "dépôt"],
                "critical_rules": []
            },
            {
                "step": 2,
                "name": "❌ Paiement insuffisant (202 FCFA)",
                "message": "",
                "images": [IMAGE_PAIEMENT_INSUFFISANT],
                "expected_thinking": ["Paiement=✗", "202 < 2000", "insuffisant"],
                "expected_response": ["insuffisant", "manque", "1798", "fcfa"],
                "critical_rules": [11]  # Validation paiement stricte
            },
            {
                "step": 3,
                "name": "✅ Paiement corrigé (2020 FCFA)",
                "message": "",
                "images": [IMAGE_PAIEMENT_VALIDE],
                "expected_thinking": ["Paiement=✓", "2020 ≥ 2000"],
                "expected_response": ["dépôt validé", "2020"],
                "critical_rules": [11]  # Validation paiement
            }
        ]
    },
    
    # ═══ HIÉRARCHIE HISTORIQUE ═══
    {
        "name": "🔄 RÈGLE 12 - HIÉRARCHIE PAIEMENT",
        "steps": [
            {
                "step": 0,
                "name": "Setup complet avec paiement validé",
                "message": "Bonjour",
                "images": [IMAGE_PRODUIT],
                "expected_thinking": [],
                "expected_response": [],
                "critical_rules": []
            },
            {
                "step": 1,
                "name": "Confirmation + paiement",
                "message": "Oui",
                "images": [IMAGE_PAIEMENT_VALIDE],
                "expected_thinking": ["Paiement=✓"],
                "expected_response": ["dépôt validé"],
                "critical_rules": []
            },
            {
                "step": 2,
                "name": "🚨 Test hiérarchie - Ne pas redemander paiement",
                "message": "Je veux changer la quantité à 5",
                "images": [],
                "expected_thinking": ["Paiement=✓ HISTORIQUE", "JAMAIS redemander"],
                "expected_response": ["noté", "5"],
                "expected_not_response": ["dépôt", "capture", "paiement"],
                "critical_rules": [12]  # Hiérarchie paiement CRITIQUE
            }
        ]
    },
    
    # ═══ HORS DOMAINE ═══
    {
        "name": "🚫 HORS DOMAINE",
        "steps": [
            {
                "step": 0,
                "name": "Question météo",
                "message": "Quel temps fait-il ?",
                "images": [],
                "expected_thinking": ["hors domaine"],
                "expected_response": ["ia assistante commande", "+225 07 87 36 07 57"],
                "critical_rules": [10]  # Hors domaine
            },
            {
                "step": 1,
                "name": "Question politique",
                "message": "Que penses-tu du président ?",
                "images": [],
                "expected_thinking": ["hors domaine"],
                "expected_response": ["ia assistante commande", "+225 07 87 36 07 57"],
                "critical_rules": [10]  # Hors domaine
            }
        ]
    },
    
    # ═══ ZONES LIVRAISON ═══
    {
        "name": "📍 ZONES ET FRAIS LIVRAISON",
        "steps": [
            {
                "step": 0,
                "name": "Setup rapide",
                "message": "Bonjour",
                "images": [IMAGE_PRODUIT],
                "expected_thinking": [],
                "expected_response": [],
                "critical_rules": []
            },
            {
                "step": 1,
                "name": "Paiement direct",
                "message": "Oui",
                "images": [IMAGE_PAIEMENT_VALIDE],
                "expected_thinking": [],
                "expected_response": [],
                "critical_rules": []
            },
            {
                "step": 2,
                "name": "Zone Centre (1500 FCFA)",
                "message": "Yopougon",
                "images": [],
                "expected_thinking": ["Adresse=✓"],
                "expected_response": ["yopougon", "1500"],
                "critical_rules": [5]  # Frais exact
            },
            {
                "step": 3,
                "name": "Changement zone Périphérie (2000 FCFA)",
                "message": "Finalement Port-Bouët",
                "images": [],
                "expected_thinking": ["Adresse=✓"],
                "expected_response": ["port-bouët", "2000"],
                "critical_rules": [5]  # Frais exact
            }
        ]
    }
]

# ═══════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════

def print_header(text: str):
    """Affiche un en-tête coloré"""
    print(f"\n\033[96m{'='*80}\033[0m")
    print(f"\033[96m{text.center(80)}\033[0m")
    print(f"\033[96m{'='*80}\033[0m\n")

def print_scenario_header(scenario_name: str, scenario_num: int, total: int):
    """Affiche l'en-tête de scénario"""
    print(f"\n\033[95m🧪 SCÉNARIO {scenario_num}/{total}: {scenario_name}\033[0m")
    print("─" * 80)

def print_step(step_num: int, step_name: str):
    """Affiche le numéro d'étape"""
    print(f"\n\033[93m📍 ÉTAPE {step_num}: {step_name}\033[0m")

def print_test_summary(question: str, thinking: str, response: str, response_data: dict, request_time: float):
    """Affiche un résumé formaté identique à la production"""
    # Codes couleur ANSI
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    print("\n" + "="*80)
    print(f"{BOLD}🔵 QUESTION CLIENT:{RESET}")
    print(f"{BLUE}{question if question else '[IMAGE]'}{RESET}")
    print()
    
    if thinking and thinking.strip() and thinking != "...":
        print(f"{BOLD}🟡 RAISONNEMENT LLM:{RESET}")
        thinking_lines = thinking.strip().split('\n')
        for line in thinking_lines:
            if line.strip():
                print(f"{YELLOW}{line.strip()}{RESET}")
        print()
    
    print(f"{BOLD}🟢 RÉPONSE AU CLIENT:{RESET}")
    print(f"{GREEN}{response}{RESET}")
    print()
    
    # Extraire métriques du système hybride
    if not response_data or not isinstance(response_data, dict):
        response_data = {}
    
    llm_used = response_data.get('llm_used', 'inconnu')
    prompt_tokens = response_data.get('prompt_tokens', 0)
    completion_tokens = response_data.get('completion_tokens', 0)
    total_tokens = prompt_tokens + completion_tokens if (prompt_tokens or completion_tokens) else 0
    total_cost = response_data.get('total_cost', 0.0)
    router_metrics = response_data.get('router_metrics', {})
    timings = response_data.get('timings', {})
    processing_time = response_data.get('processing_time', request_time)
    
    print(f"{BOLD}🔴 TOKENS RÉELS & COÛTS:{RESET}")
    
    # Calculer coûts selon modèle
    if "deepseek" in llm_used.lower():
        input_cost = (prompt_tokens / 1_000_000) * 0.08
        output_cost = (completion_tokens / 1_000_000) * 0.12
        cost_detail = f"${input_cost:.6f} input + ${output_cost:.6f} output"
    else:
        input_cost = (prompt_tokens / 1_000_000) * 0.59
        output_cost = (completion_tokens / 1_000_000) * 0.79
        cost_detail = f"${input_cost:.6f} input + ${output_cost:.6f} output"
    
    print(f"{RED}Prompt: {prompt_tokens} | Completion: {completion_tokens} | TOTAL: {total_tokens}{RESET}")
    print(f"{RED}💰 COÛT LLM: ${total_cost:.6f} ({cost_detail}){RESET}")
    
    # Métriques routeur HYDE
    if router_metrics and router_metrics.get('tokens', 0) > 0:
        router_tokens = router_metrics.get('tokens', 0)
        router_cost = router_metrics.get('cost', 0.0)
        print(f"{RED}💰 COÛT ROUTEUR HYDE (8B): ${router_cost:.6f} ({router_tokens} tokens){RESET}")
        total_with_router = total_cost + router_cost
        print(f"{RED}💰 COÛT TOTAL: ${total_with_router:.6f}{RESET}")
    else:
        print(f"{RED}💰 COÛT TOTAL: ${total_cost:.6f}{RESET}")
    
    print(f"{RED}🤖 MODÈLE: {llm_used}{RESET}")
    print()
    
    # Temps d'exécution
    print(f"{BOLD}⏱️  TEMPS D'EXÉCUTION:{RESET}")
    if timings:
        print(f"{CYAN}┌─ Étapes détaillées:{RESET}")
        
        if 'routing' in timings:
            routing_time = timings['routing']*1000
            if router_metrics and router_metrics.get('tokens', 0) > 0:
                router_tokens = router_metrics.get('tokens', 0)
                router_cost_fcfa = router_metrics.get('cost', 0) * 600
                print(f"{CYAN}├── 1. Routage HYDE (8B): {routing_time:.2f}ms | {router_tokens} tokens | {router_cost_fcfa:.4f} FCFA{RESET}")
            else:
                print(f"{CYAN}├── 1. Routage intelligent: {routing_time:.2f}ms{RESET}")
        
        if 'prompt_generation' in timings:
            print(f"{CYAN}├── 2. Génération prompt: {timings['prompt_generation']*1000:.2f}ms{RESET}")
        
        if 'llm_call' in timings:
            print(f"{CYAN}├── 3. Appel LLM ({llm_used}): {timings['llm_call']*1000:.2f}ms{RESET}")
        
        if 'tools_execution' in timings:
            tools_time = timings['tools_execution']*1000
            if tools_time > 0.1:
                print(f"{CYAN}├── 4. Exécution outils: {tools_time:.2f}ms{RESET}")
            else:
                print(f"{CYAN}├── 4. Exécution outils: <0.1ms (aucun outil){RESET}")
        
        print(f"{CYAN}└── {RESET}")
    
    print(f"{MAGENTA}{BOLD}⏱️  TEMPS TOTAL REQUÊTE: {processing_time*1000:.2f}ms ({processing_time:.3f}s){RESET}")
    print("="*80 + "\n")

def extract_thinking_response(response_text: str) -> tuple:
    """Extrait thinking et response du texte LLM"""
    import re
    thinking_match = re.search(r'<thinking>(.*?)</thinking>', response_text, re.DOTALL)
    response_match = re.search(r'<response>(.*?)</response>', response_text, re.DOTALL)
    
    thinking = thinking_match.group(1).strip() if thinking_match else ""
    response = response_match.group(1).strip() if response_match else response_text
    
    return thinking, response

def extract_cost_info(response_data: Dict) -> Dict:
    """Extrait les informations de coût et tokens de la réponse"""
    try:
        # Chercher dans différents endroits possibles
        usage = response_data.get("usage", {})
        if usage:
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", input_tokens + output_tokens)
            
            # Détecter le modèle réellement utilisé
            actual_model = response_data.get("model", "unknown")
            
            # Calcul coût selon le modèle détecté
            if "deepseek" in actual_model.lower():
                # DeepSeek V3 pricing
                input_cost = (input_tokens / 1000000) * 0.14  # $0.14 per 1M tokens
                output_cost = (output_tokens / 1000000) * 1.10  # $1.10 per 1M tokens
                provider = "DEEPSEEK"
            elif "llama" in actual_model.lower() and "8b" in actual_model.lower():
                # Groq 8B pricing
                input_cost = (input_tokens / 1000000) * 0.05  # $0.05 per 1M tokens
                output_cost = (output_tokens / 1000000) * 0.08  # $0.08 per 1M tokens
                provider = "GROQ-8B"
            elif "llama" in actual_model.lower() and "70b" in actual_model.lower():
                # Groq 70B pricing
                input_cost = (input_tokens / 1000000) * 0.59  # $0.59 per 1M tokens
                output_cost = (output_tokens / 1000000) * 0.79  # $0.79 per 1M tokens
                provider = "GROQ-70B"
            else:
                # Fallback pricing
                input_cost = (input_tokens / 1000000) * 0.10
                output_cost = (output_tokens / 1000000) * 0.10
                provider = "UNKNOWN"
            
            total_cost = input_cost + output_cost
            
            return {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "input_cost": input_cost,
                "output_cost": output_cost,
                "total_cost": total_cost,
                "model": actual_model,
                "provider": provider
            }
    except Exception as e:
        print(f"Erreur extraction coût: {e}")
    
    return None

def validate_step(thinking: str, response: str, step_config: Dict) -> Dict:
    """Valide une étape selon les critères"""
    validation = {
        "thinking_valid": False,
        "response_valid": False,
        "critical_rules_ok": [],
        "critical_rules_failed": [],
        "score": 0,
        "details": []
    }
    
    thinking_lower = thinking.lower()
    response_lower = response.lower()
    
    # Vérifier thinking attendu
    expected_thinking = step_config.get("expected_thinking", [])
    thinking_found = 0
    for expected in expected_thinking:
        if expected.lower() in thinking_lower:
            thinking_found += 1
            validation["details"].append(f"✅ Thinking: '{expected}' trouvé")
        else:
            validation["details"].append(f"❌ Thinking: '{expected}' manquant")
    
    validation["thinking_valid"] = thinking_found >= len(expected_thinking) * 0.7  # 70% minimum
    
    # Vérifier response attendue
    expected_response = step_config.get("expected_response", [])
    response_found = 0
    for expected in expected_response:
        if expected.lower() in response_lower:
            response_found += 1
            validation["details"].append(f"✅ Response: '{expected}' trouvé")
        else:
            validation["details"].append(f"❌ Response: '{expected}' manquant")
    
    # Vérifier response interdite
    expected_not_response = step_config.get("expected_not_response", [])
    for not_expected in expected_not_response:
        if not_expected.lower() in response_lower:
            validation["details"].append(f"🚨 Response: '{not_expected}' INTERDIT trouvé")
            response_found -= 1  # Pénalité
        else:
            validation["details"].append(f"✅ Response: '{not_expected}' correctement absent")
    
    validation["response_valid"] = response_found >= len(expected_response) * 0.7  # 70% minimum
    
    # Vérifier règles critiques
    critical_rules = step_config.get("critical_rules", [])
    for rule_num in critical_rules:
        rule_ok = validate_critical_rule(rule_num, thinking, response, step_config)
        if rule_ok:
            validation["critical_rules_ok"].append(rule_num)
        else:
            validation["critical_rules_failed"].append(rule_num)
    
    # Calculer score
    score = 0
    if validation["thinking_valid"]:
        score += 30
    if validation["response_valid"]:
        score += 40
    if len(validation["critical_rules_failed"]) == 0 and critical_rules:
        score += 30
    elif len(validation["critical_rules_ok"]) > 0:
        score += 15  # Partiel
    
    validation["score"] = score
    return validation

def validate_critical_rule(rule_num: int, thinking: str, response: str, step_config: Dict) -> bool:
    """Valide une règle critique spécifique"""
    thinking_lower = thinking.lower()
    response_lower = response.lower()
    
    if rule_num == 1:  # Consulter HISTORIQUE
        return "historique" in thinking_lower
    elif rule_num == 4:  # Jamais nom produit
        return "produit" in response_lower and not any(word in response_lower for word in ["couche", "biberon", "lait", "pampers"])
    elif rule_num == 5:  # Frais exact
        return any(frais in response_lower for frais in ["1500", "2000", "2500"])
    elif rule_num == 8:  # Progresser 0→5
        return "étape=" in thinking_lower
    elif rule_num == 10:  # Hors domaine
        return "ia assistante commande" in response_lower and "07 87 36 07 57" in response_lower
    elif rule_num == 11:  # Validation paiement
        return ("paiement=✓" in thinking_lower or "paiement=✗" in thinking_lower) and ("≥" in thinking_lower or "<" in thinking_lower or "insuffisant" in thinking_lower)
    elif rule_num == 12:  # Hiérarchie paiement
        return "historique" in thinking_lower and "jamais redemander" in thinking_lower
    elif rule_num == 13:  # Confirmation produit
        return "c'est bien" in response_lower and "produit" in response_lower
    
    return True  # Règle non implémentée = OK par défaut

async def send_message(message: str, images: List[str]) -> Dict[str, Any]:
    """Envoie un message à l'API"""
    payload = {
        "company_id": COMPANY_ID,
        "user_id": USER_ID,
        "message": message,
        "images": images,
        "botlive_enabled": True,
        "rag_enabled": True
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(API_URL, json=payload)
        response.raise_for_status()
        return response.json()

async def reset_conversation():
    """Reset la conversation en changeant d'utilisateur"""
    global USER_ID
    USER_ID = f"testuser771-{datetime.now().strftime('%H%M%S')}"
    print(f"🔄 Reset conversation - Nouvel utilisateur: {USER_ID}")

# ═══════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ═══════════════════════════════════════════════════════════════

async def run_optimized_test():
    """Exécute tous les scénarios de test optimisés"""
    print_header("🧪 TEST BOTLIVE OPTIMISÉ - RÈGLES CRITIQUES")
    
    start_time = datetime.now()
    all_results = []
    total_scenarios = len(TEST_SCENARIOS)
    
    for scenario_idx, scenario in enumerate(TEST_SCENARIOS, 1):
        scenario_name = scenario["name"]
        steps = scenario["steps"]
        
        print_scenario_header(scenario_name, scenario_idx, total_scenarios)
        
        # Reset conversation pour chaque scénario
        await reset_conversation()
        
        scenario_results = []
        scenario_score = 0
        
        for step_config in steps:
            step_num = step_config["step"]
            step_name = step_config["name"]
            message = step_config["message"]
            images = step_config["images"]
            
            print_step(step_num, step_name)
            
            try:
                # Envoyer le message avec mesure du temps
                start_request = datetime.now()
                print(f"📤 Message: '{message}' + {len(images)} image(s)")
                response_data = await send_message(message, images)
                end_request = datetime.now()
                request_time = (end_request - start_request).total_seconds()
                
                # Extraire thinking/response selon structure de réponse
                # Structure réelle: response_data['response'] contient toutes les métriques
                if isinstance(response_data, dict) and 'response' in response_data:
                    if isinstance(response_data['response'], dict):
                        # Structure confirmée: response_data['response'] = dict avec tout dedans
                        inner_response = response_data['response']
                        
                        # DEBUG: Afficher TOUTES les clés disponibles
                        print(f"\n🔍 DEBUG COMPLET inner_response:")
                        for key in inner_response.keys():
                            value = inner_response[key]
                            if isinstance(value, (str, int, float, bool)):
                                print(f"   {key}: {value}")
                            elif isinstance(value, dict):
                                print(f"   {key}: dict avec {len(value)} clés -> {list(value.keys())}")
                            elif isinstance(value, list):
                                print(f"   {key}: list de {len(value)} éléments")
                            else:
                                print(f"   {key}: {type(value).__name__}")
                        print()
                        
                        # Extraire le texte de réponse
                        response_text = inner_response.get('response', str(inner_response))
                        thinking = inner_response.get('thinking', '')
                        
                        # Extraire thinking/response si format XML
                        if not thinking and ("<thinking>" in response_text or "<response>" in response_text):
                            thinking, response = extract_thinking_response(response_text)
                        else:
                            response = response_text
                        
                        # Toutes les métriques sont dans inner_response
                        hybrid_data = {
                            'llm_used': inner_response.get('llm_used', 'inconnu'),
                            'prompt_tokens': inner_response.get('prompt_tokens', 0),
                            'completion_tokens': inner_response.get('completion_tokens', 0),
                            'total_cost': inner_response.get('total_cost', 0.0),
                            'router_metrics': inner_response.get('router_metrics', {}),
                            'timings': inner_response.get('timings', {}),
                            'processing_time': inner_response.get('processing_time', request_time),
                            'thinking': thinking
                        }
                    elif isinstance(response_data['response'], str):
                        # Cas rare: response directement string
                        response_text = response_data['response']
                        thinking, response = extract_thinking_response(response_text)
                        hybrid_data = {'thinking': thinking}
                    else:
                        response_text = str(response_data)
                        thinking, response = extract_thinking_response(response_text)
                        hybrid_data = {}
                else:
                    response_text = str(response_data)
                    thinking, response = extract_thinking_response(response_text)
                    hybrid_data = {}
                
                # Affichage formaté identique à la production
                print_test_summary(message, thinking, response, hybrid_data, request_time)
                
                # Valider l'étape
                validation = validate_step(thinking, response, step_config)
                
                # Afficher validation
                score = validation["score"]
                if score >= 80:
                    status = "\033[92m✅ EXCELLENT\033[0m"
                elif score >= 60:
                    status = "\033[93m⚠️ ACCEPTABLE\033[0m"
                else:
                    status = "\033[91m❌ ÉCHEC\033[0m"
                
                print(f"\n📊 {status} ({score}/100)")
                
                # Détails validation
                for detail in validation["details"][:3]:  # Limiter l'affichage
                    print(f"   {detail}")
                
                if validation["critical_rules_failed"]:
                    print(f"   🚨 Règles critiques échouées: {validation['critical_rules_failed']}")
                
                print()  # Ligne vide pour séparation
                
                scenario_results.append({
                    "step": step_num,
                    "name": step_name,
                    "validation": validation,
                    "thinking": thinking,
                    "response": response
                })
                
                scenario_score += score
                
                # Pause entre étapes
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"\n\033[91m❌ ERREUR: {e}\033[0m")
                scenario_results.append({
                    "step": step_num,
                    "name": step_name,
                    "error": str(e)
                })
        
        # Résumé scénario
        avg_score = scenario_score / len(steps) if steps else 0
        print(f"\n📊 Score scénario: {avg_score:.1f}/100")
        
        all_results.append({
            "scenario": scenario_name,
            "average_score": avg_score,
            "steps": scenario_results
        })
    
    # ═══════════════════════════════════════════════════════════════
    # RAPPORT FINAL
    # ═══════════════════════════════════════════════════════════════
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print_header("📊 RAPPORT FINAL OPTIMISÉ")
    
    total_score = sum(r["average_score"] for r in all_results)
    global_avg = total_score / len(all_results)
    
    print(f"⏱️ Durée totale: {duration:.1f}s")
    print(f"📈 Score global: {global_avg:.1f}/100")
    print(f"🧪 Scénarios testés: {len(all_results)}")
    
    print(f"\n📋 RÉSULTATS PAR SCÉNARIO:")
    for result in all_results:
        score = result["average_score"]
        if score >= 80:
            status = "✅ EXCELLENT"
        elif score >= 60:
            status = "⚠️ ACCEPTABLE"
        else:
            status = "❌ ÉCHEC"
        
        print(f"   {status} {result['scenario']}: {score:.1f}/100")
    
    # Verdict final
    print(f"\n{'='*80}")
    if global_avg >= 80:
        print(f"\033[92m🎉 SUCCÈS ! Système Botlive robuste et conforme aux règles critiques.\033[0m")
    elif global_avg >= 60:
        print(f"\033[93m⚠️ ACCEPTABLE. Quelques règles critiques à renforcer.\033[0m")
    else:
        print(f"\033[91m❌ ÉCHEC. Règles critiques non respectées - Corrections urgentes.\033[0m")
    print(f"{'='*80}\n")
    
    # Sauvegarder rapport
    report_file = f"test_botlive_optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "global_average_score": global_avg,
            "scenarios": all_results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Rapport détaillé: {report_file}")

if __name__ == "__main__":
    try:
        asyncio.run(run_optimized_test())
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()

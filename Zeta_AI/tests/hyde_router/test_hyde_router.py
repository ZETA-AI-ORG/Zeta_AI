"""
Test isolé du HYDE Routeur
Simule tous les cas possibles pour affiner le prompt avant intégration
Utilise le modèle Llama 8B (llama-3.1-8b-instant) via Groq
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import sys
import asyncio

# Ajouter le chemin parent pour importer les modules core
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Charger la config (qui charge le .env avec GROQ_API_KEY)
import config

# Import du client LLM Groq (Llama 8B)
from core.llm_client_groq import complete

# Chemins
SCRIPT_DIR = Path(__file__).parent
PROMPT_FILE = SCRIPT_DIR / "HYDE_ROUTEUR.txt"
SCENARIOS_FILE = SCRIPT_DIR / "test_scenarios.json"
RESULTS_DIR = SCRIPT_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def load_prompt_template() -> str:
    """Charge le template du prompt HYDE"""
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def load_scenarios() -> List[Dict[str, Any]]:
    """Charge les scénarios de test"""
    with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data["scenarios"]


def format_conversation_history(history: List[Dict[str, str]]) -> str:
    """Formate l'historique de conversation"""
    formatted = []
    for msg in history:
        role = "Client" if msg["role"] == "client" else "Agent"
        formatted.append(f"{role}: {msg['message']}")
    return "\n".join(formatted)


def format_collected_data(data: Dict[str, Any]) -> str:
    """Formate les données collectées"""
    lines = []
    for key, value in data.items():
        display_value = value if value is not None else "❌ manquant"
        lines.append(f"- {key}: {display_value}")
    return "\n".join(lines)


def build_hyde_prompt(scenario: Dict[str, Any], template: str) -> str:
    """Construit le prompt HYDE pour un scénario"""
    conversation_history = format_conversation_history(scenario["conversation_history"])
    
    prompt = template.format(
        produit=scenario["collected_data"]["produit"] or "❌ manquant",
        variante=scenario["collected_data"]["variante"] or "❌ manquant",
        zone=scenario["collected_data"]["zone"] or "❌ manquant",
        telephone=scenario["collected_data"]["telephone"] or "❌ manquant",
        paiement=scenario["collected_data"]["paiement"] or "❌ manquant",
        conversation_history=conversation_history,
        question=scenario["question"]
    )
    
    return prompt


async def call_hyde_router(prompt: str) -> Dict[str, Any]:
    """Appelle le LLM HYDE (Llama 8B) avec le prompt"""
    try:
        # Appel au modèle Llama 8B via Groq
        content, token_info = await complete(
            prompt=prompt,
            model_name="llama-3.1-8b-instant",
            max_tokens=150,
            temperature=0.1
        )
        
        # Parse JSON
        # Nettoie le contenu si markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        
        return {
            "success": True,
            "phase": result.get("phase"),
            "raison": result.get("raison", ""),
            "raw_response": content,
            "tokens_used": token_info.get('total_tokens', 0)
        }
    
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"JSON parse error: {str(e)}",
            "raw_response": content if 'content' in locals() else "No response"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "raw_response": ""
        }


async def test_scenario(scenario: Dict[str, Any], template: str) -> Dict[str, Any]:
    """Test un scénario unique"""
    print(f"\n{'='*80}")
    print(f"🧪 TEST: {scenario['id']}")
    print(f"📝 {scenario['description']}")
    print(f"{'='*80}")
    
    # Construit le prompt
    prompt = build_hyde_prompt(scenario, template)
    
    # DEBUG: Afficher l'état actuel envoyé au modèle
    print(f"\n📊 État envoyé au modèle:")
    print(f"  Produit: {scenario['collected_data']['produit'] or '❌ manquant'}")
    print(f"  Variante: {scenario['collected_data']['variante'] or '❌ manquant'}")
    print(f"  Zone: {scenario['collected_data']['zone'] or '❌ manquant'}")
    print(f"  Téléphone: {scenario['collected_data']['telephone'] or '❌ manquant'}")
    print(f"  Paiement: {scenario['collected_data']['paiement'] or '❌ manquant'}")
    
    # Appelle le routeur
    result = await call_hyde_router(prompt)
    
    # Analyse le résultat
    if result["success"]:
        phase_ok = result["phase"] == scenario["expected_phase"]
        status = "✅ PASS" if phase_ok else "❌ FAIL"
        
        print(f"\n{status}")
        print(f"Phase attendue: {scenario['expected_phase']}")
        print(f"Phase obtenue:  {result['phase']}")
        print(f"Raison: {result['raison']}")
        print(f"Tokens: {result['tokens_used']}")
        
        return {
            "scenario_id": scenario["id"],
            "description": scenario["description"],
            "status": "PASS" if phase_ok else "FAIL",
            "expected_phase": scenario["expected_phase"],
            "actual_phase": result["phase"],
            "expected_raison": scenario["expected_raison"],
            "actual_raison": result["raison"],
            "tokens_used": result["tokens_used"],
            "prompt": prompt,
            "raw_response": result["raw_response"]
        }
    else:
        print(f"\n❌ ERREUR")
        print(f"Erreur: {result['error']}")
        print(f"Réponse brute: {result['raw_response']}")
        
        return {
            "scenario_id": scenario["id"],
            "description": scenario["description"],
            "status": "ERROR",
            "error": result["error"],
            "raw_response": result["raw_response"],
            "prompt": prompt
        }


async def run_all_tests():
    """Exécute tous les tests"""
    print("\n" + "="*80)
    print("🚀 DÉMARRAGE DES TESTS - HYDE ROUTEUR (Llama 8B)")
    print("="*80)
    
    # Charge le template et les scénarios
    template = load_prompt_template()
    scenarios = load_scenarios()
    
    print(f"\n📋 {len(scenarios)} scénarios chargés")
    
    # Exécute les tests
    results = []
    for scenario in scenarios:
        result = await test_scenario(scenario, template)
        results.append(result)
    
    # Analyse globale
    print("\n" + "="*80)
    print("📊 RÉSULTATS GLOBAUX")
    print("="*80)
    
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    
    print(f"\nTotal: {total}")
    print(f"✅ PASS: {passed} ({passed/total*100:.1f}%)")
    print(f"❌ FAIL: {failed} ({failed/total*100:.1f}%)")
    print(f"⚠️  ERROR: {errors} ({errors/total*100:.1f}%)")
    
    # Tokens et coûts réels (Llama 8B via Groq)
    total_tokens = sum(r.get("tokens_used", 0) for r in results if "tokens_used" in r)
    avg_tokens = total_tokens / len([r for r in results if "tokens_used" in r]) if total_tokens > 0 else 0
    
    # Tarifs Groq pour llama-3.1-8b-instant
    # Input: $0.05 / 1M tokens
    # Output: $0.08 / 1M tokens
    # Approximation: 80% input, 20% output
    prompt_tokens = int(total_tokens * 0.8)
    completion_tokens = int(total_tokens * 0.2)
    
    input_cost = (prompt_tokens / 1_000_000) * 0.05
    output_cost = (completion_tokens / 1_000_000) * 0.08
    total_cost = input_cost + output_cost
    
    print(f"\n🎯 Tokens moyens par requête: {avg_tokens:.0f}")
    print(f"🎯 Tokens totaux: {total_tokens}")
    print(f"💰 Coût total: ${total_cost:.6f}")
    print(f"💰 Coût moyen par requête: ${total_cost/total:.6f}")
    print(f"💰 Coût estimé pour 1000 requêtes: ${(total_cost/total)*1000:.4f}")
    
    # Sauvegarde les résultats
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = RESULTS_DIR / f"test_results_{timestamp}.json"
    
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "pass_rate": passed/total*100,
                "avg_tokens": avg_tokens,
                "total_tokens": total_tokens,
                "total_cost_usd": total_cost,
                "avg_cost_per_request_usd": total_cost/total if total > 0 else 0,
                "estimated_cost_1000_requests_usd": (total_cost/total)*1000 if total > 0 else 0
            },
            "results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Résultats sauvegardés: {results_file}")
    
    # Affiche les échecs
    if failed > 0 or errors > 0:
        print("\n" + "="*80)
        print("⚠️  DÉTAILS DES ÉCHECS")
        print("="*80)
        
        for r in results:
            if r["status"] in ["FAIL", "ERROR"]:
                print(f"\n❌ {r['scenario_id']}: {r['description']}")
                if r["status"] == "FAIL":
                    print(f"   Attendu: Phase {r['expected_phase']}")
                    print(f"   Obtenu:  Phase {r['actual_phase']}")
                    print(f"   Raison:  {r['actual_raison']}")
                else:
                    print(f"   Erreur: {r['error']}")
    
    return results


if __name__ == "__main__":
    # Exécuter les tests de manière asynchrone
    results = asyncio.run(run_all_tests())
    
    # Code de sortie
    failed = sum(1 for r in results if r["status"] in ["FAIL", "ERROR"])
    sys.exit(0 if failed == 0 else 1)

#!/usr/bin/env python3
"""
📊 BENCHMARK LLM ENRICHMENT - Mesurer taux de succès
Objectif: 90%+ avant déploiement production
"""
import asyncio
import json
from typing import Dict, List
from llm_client import get_llm_client

class EnrichmentBenchmark:
    """Benchmark du système d'enrichissement LLM"""
    
    def __init__(self):
        self.llm = get_llm_client()
        self.results = []
    
    async def test_enrichment(self, test_case: Dict) -> Dict:
        """
        Test un cas d'enrichissement et évalue la qualité
        
        Returns:
            {
                "success": bool,
                "score": float (0-1),
                "errors": List[str],
                "llm_output": str
            }
        """
        original = test_case["original"]
        expected = test_case["expected_enrichment"]
        
        # Prompt d'enrichissement
        prompt = f"""Tu es un expert en clarification de données e-commerce.

DOCUMENT ORIGINAL:
{original}

TÂCHE:
Enrichis ce document pour lever TOUTES les ambiguïtés. Sois PRÉCIS et FACTUEL.
Ne JAMAIS inventer d'informations absentes du document original.

Si le document dit "toutes les tailles" SANS préciser lesquelles:
- Demande clarification OU liste les tailles STANDARD du secteur
- Précise EXPLICITEMENT "à confirmer par le client"

Si prix mentionné:
- Clarifier si prix unique ou variable
- Lister TOUS les variants avec leurs prix

FORMAT JSON:
{{
  "enriched_text": "...",
  "ambiguities_resolved": ["..."],
  "needs_clarification": ["..."],
  "confidence": 0.X
}}
"""
        
        try:
            response = await self.llm.complete(prompt, temperature=0.2, max_tokens=800)
            llm_output = json.loads(response)
            
            # Évaluer la qualité
            score = self._evaluate_quality(llm_output, expected)
            errors = self._detect_errors(llm_output, expected, original)
            
            return {
                "success": score >= 0.9,
                "score": score,
                "errors": errors,
                "llm_output": llm_output,
                "confidence": llm_output.get("confidence", 0)
            }
            
        except Exception as e:
            return {
                "success": False,
                "score": 0,
                "errors": [f"Exception: {str(e)}"],
                "llm_output": None
            }
    
    def _evaluate_quality(self, llm_output: Dict, expected: Dict) -> float:
        """
        Évalue la qualité de l'enrichissement (0-1)
        
        Critères:
        - Présence des key_facts attendus: 40%
        - Absence d'hallucinations: 30%
        - Clarté et structure: 20%
        - Confiance LLM: 10%
        """
        score = 0.0
        
        # 1. Key facts présents (40%)
        enriched_text = llm_output.get("enriched_text", "").lower()
        expected_facts = expected.get("key_facts", [])
        
        facts_found = 0
        for fact in expected_facts:
            if any(word in enriched_text for word in fact.lower().split()):
                facts_found += 1
        
        score += 0.4 * (facts_found / len(expected_facts)) if expected_facts else 0
        
        # 2. Absence d'hallucinations (30%)
        # Vérifier qu'aucune info inventée
        hallucinations = self._detect_hallucinations(llm_output, expected)
        hallucination_penalty = min(0.3, len(hallucinations) * 0.1)
        score += 0.3 - hallucination_penalty
        
        # 3. Clarté (20%)
        if len(enriched_text) > 100:  # Texte suffisamment détaillé
            score += 0.1
        if "UNIQUE" in enriched_text or "TOUTES" in enriched_text:  # Mots clarificateurs
            score += 0.1
        
        # 4. Confiance LLM (10%)
        confidence = llm_output.get("confidence", 0)
        score += 0.1 * confidence
        
        return min(1.0, score)
    
    def _detect_errors(self, llm_output: Dict, expected: Dict, original: str) -> List[str]:
        """Détecte les erreurs dans l'enrichissement"""
        errors = []
        
        enriched = llm_output.get("enriched_text", "")
        
        # Erreur 1: Hallucination de prix
        import re
        prices_in_enriched = re.findall(r'(\d{1,3}(?:[\s,]\d{3})*)\s*FCFA', enriched)
        prices_in_original = re.findall(r'(\d{1,3}(?:[\s,]\d{3})*)\s*FCFA', original)
        
        for price in prices_in_enriched:
            if price not in prices_in_original:
                errors.append(f"Prix inventé: {price} FCFA (absent de l'original)")
        
        # Erreur 2: Affirmations non vérifiables
        uncertain_claims = ["disponible", "toujours", "jamais", "tous les"]
        for claim in uncertain_claims:
            if claim in enriched.lower() and claim not in original.lower():
                errors.append(f"Affirmation non vérifiable: '{claim}'")
        
        # Erreur 3: Contradictions
        if "Prix UNIQUE" in enriched and "prix varie" in enriched.lower():
            errors.append("Contradiction: 'prix unique' ET 'prix varie'")
        
        return errors
    
    def _detect_hallucinations(self, llm_output: Dict, expected: Dict) -> List[str]:
        """Détecte les hallucinations (infos inventées)"""
        hallucinations = []
        
        # À implémenter: détection avancée
        needs_clarif = llm_output.get("needs_clarification", [])
        if not needs_clarif:
            # Si aucun "needs clarification" alors que document vague = suspect
            hallucinations.append("Aucune demande de clarification alors que document vague")
        
        return hallucinations
    
    async def run_benchmark(self, test_cases: List[Dict]) -> Dict:
        """
        Lance le benchmark complet
        
        Returns:
            {
                "total": int,
                "passed": int,
                "failed": int,
                "success_rate": float,
                "average_score": float,
                "details": List[Dict]
            }
        """
        print(f"\n{'='*80}")
        print(f"🧪 BENCHMARK ENRICHISSEMENT LLM")
        print(f"{'='*80}\n")
        print(f"Total cas: {len(test_cases)}")
        print(f"Objectif: 90% success rate\n")
        
        results = []
        total_score = 0
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"[{i}/{len(test_cases)}] Test: {test_case['id']}...", end=" ")
            
            result = await self.test_enrichment(test_case)
            results.append({
                "test_id": test_case["id"],
                "result": result
            })
            
            total_score += result["score"]
            
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{status} (score: {result['score']:.2f})")
            
            if result["errors"]:
                for error in result["errors"]:
                    print(f"   ⚠️ {error}")
        
        # Résumé
        passed = sum(1 for r in results if r["result"]["success"])
        failed = len(results) - passed
        success_rate = passed / len(results)
        avg_score = total_score / len(results)
        
        print(f"\n{'='*80}")
        print(f"📊 RÉSULTATS")
        print(f"{'='*80}\n")
        print(f"✅ Réussis: {passed}/{len(results)}")
        print(f"❌ Échoués: {failed}/{len(results)}")
        print(f"📈 Taux de succès: {success_rate*100:.1f}%")
        print(f"📊 Score moyen: {avg_score:.2f}/1.00")
        print(f"\n{'='*80}\n")
        
        if success_rate >= 0.9:
            print(f"🎉 OBJECTIF ATTEINT ! Le LLM est prêt pour la production.")
        else:
            print(f"⚠️ Objectif non atteint. Améliorations nécessaires:")
            print(f"   - Améliorer le prompt")
            print(f"   - Ajouter examples (few-shot)")
            print(f"   - Tester autre modèle LLM")
        
        return {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "success_rate": success_rate,
            "average_score": avg_score,
            "details": results
        }

# Dataset de test (à enrichir avec tes vrais documents)
BENCHMARK_TEST_CASES = [
    {
        "id": "test_001_prix_tailles",
        "original": "Couches culottes disponibles en toutes les tailles entre 5 et 30kg. Prix: 13 500 FCFA",
        "expected_enrichment": {
            "key_facts": [
                "prix unique",
                "toutes tailles",
                "5-30kg"
            ]
        }
    },
    {
        "id": "test_002_livraison_zones",
        "original": "Livraison zones centrales: 1500 FCFA",
        "expected_enrichment": {
            "key_facts": [
                "zones centrales",
                "1500 fcfa",
                "liste zones"
            ]
        }
    },
    # Ajouter 20-30 cas représentatifs
]

async def main():
    benchmark = EnrichmentBenchmark()
    results = await benchmark.run_benchmark(BENCHMARK_TEST_CASES)
    
    # Sauvegarder résultats
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"📁 Résultats sauvegardés dans benchmark_results.json")

if __name__ == "__main__":
    asyncio.run(main())

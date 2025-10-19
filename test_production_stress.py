#!/usr/bin/env python3
"""
🔥 STRESS TEST PRODUCTION - VALIDATION RÉALISTE
Objectif: Exposer les vraies lacunes du système RAG en testant les cas limites,
ambigus, et des situations réelles difficiles.
"""

import asyncio
import json
import time
import statistics
import logging
from datetime import datetime
from typing import Dict, List, Any

# --- Configuration ---
ENDPOINT_URL = "http://127.0.0.1:8001/chat"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"  # Rue du Gros

class ProductionStressTester:
    """
    🔥 Testeur de stress pour une validation production réaliste.
    Ce script ne cherche pas à atteindre un score, mais à trouver les failles.
    """

    def __init__(self):
        self.test_results = []
        self.start_time = datetime.now()
        self.setup_logging()

    def setup_logging(self):
        log_filename = f"stress_test_report_{self.start_time.strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format="[%(levelname)s][%(asctime)s.%(msecs)03d] %(message)s",
            datefmt="%H:%M:%S",
            handlers=[logging.FileHandler(log_filename), logging.StreamHandler()]
        )
        logging.info(f"🔥 STRESS TEST - Rapport détaillé sauvegardé dans: {log_filename}")

    def _evaluate_response(self, response: str, expected_elements: List[str], test_type: str) -> Dict[str, Any]:
        """Évaluation objective de la qualité de la réponse."""
        eval_report = {"score": 100, "issues": [], "strengths": []}
        response_lower = response.lower()

        # 1. Erreurs critiques (pénalité maximale)
        if not response.strip() or "erreur" in response_lower or "exception" in response_lower:
            eval_report["issues"].append("ERREUR CRITIQUE: Réponse vide ou erreur système.")
            eval_report["score"] = 0
            return eval_report

        # 2. Incapacité à répondre (pénalité forte)
        if "je ne sais pas" in response_lower or "je ne peux pas" in response_lower:
            if test_type == "out_of_scope":
                eval_report["strengths"].append("SUCCÈS: A correctement identifié une question hors-scope.")
                eval_report["score"] = 100
            else:
                eval_report["issues"].append("ÉCHEC: Incapable de répondre à une question légitime.")
                eval_report["score"] -= 70

        # 3. Hallucinations (pénalité forte)
        # Produits/services qui n'existent pas
        hallucinations = ["biberon", "lait en poudre", "poussette", "orange money", "mtn money"]
        for item in hallucinations:
            if item in response_lower:
                eval_report["issues"].append(f"HALLUCINATION: A mentionné '{item}' qui n'existe pas.")
                eval_report["score"] -= 50

        # 4. Pertinence (basé sur les éléments attendus)
        if expected_elements:
            found_count = sum(1 for el in expected_elements if el.lower() in response_lower)
            relevance_ratio = found_count / len(expected_elements)
            if relevance_ratio < 0.5:
                eval_report["issues"].append(f"MANQUE DE PERTINENCE: Seulement {found_count}/{len(expected_elements)} éléments attendus trouvés.")
                eval_report["score"] -= (1 - relevance_ratio) * 40
            else:
                eval_report["strengths"].append("BONNE PERTINENCE: La plupart des informations clés sont présentes.")

        # 5. Comportement attendu pour les cas limites
        if test_type == "ambiguous" and "préciser" not in response_lower and "quelle taille" not in response_lower:
            eval_report["issues"].append("ÉCHEC AMBIGUÏTÉ: N'a pas posé de question de clarification.")
            eval_report["score"] -= 40
        if test_type == "negation" and "pas" not in response_lower and "uniquement" not in response_lower:
             eval_report["issues"].append("ÉCHEC NÉGATION: N'a pas correctement traité la négation.")
             eval_report["score"] -= 50

        eval_report["score"] = max(0, eval_report["score"])
        return eval_report

    async def run_single_test(self, query: str, test_name: str, test_type: str, expected: List[str]):
        logging.info(f"--- DÉBUT TEST: {test_name} (Type: {test_type}) ---")
        logging.info(f"❓ Query: '{query}'")

        payload = {"message": query, "company_id": COMPANY_ID, "user_id": "testuser123"} # CORRECTION: Utilisation du bon user_id
        payload_str = json.dumps(payload).replace('"', '\\"')
        # Format curl aligné sur la version qui fonctionne
        cmd = f"curl -s -w '\n%{{time_total}}' -X POST {ENDPOINT_URL} -H \"Content-Type: application/json\" -d \"{payload_str}\""

        test_result = {"name": test_name, "type": test_type, "query": query}

        try:
            proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                response_body, duration_str = stdout.decode().strip().rsplit('\n', 1)
                response_json = json.loads(response_body)
                response_text = response_json.get('response', '')
                
                logging.info(f"💬 Réponse ({float(duration_str):.2f}s): {response_text}")
                evaluation = self._evaluate_response(response_text, expected, test_type)
                test_result.update(evaluation)
            else:
                error_text = stderr.decode().strip()
                logging.error(f"❌ ERREUR CURL (Code: {proc.returncode}): {error_text}")
                test_result.update({"score": 0, "issues": [f"CURL_ERROR: {error_text}"]})

        except Exception as e:
            logging.error(f"💥 EXCEPTION SCRIPT: {type(e).__name__}: {e}")
            test_result.update({"score": 0, "issues": [f"SCRIPT_EXCEPTION: {e}"]})
        
        self.test_results.append(test_result)
        status = "✅ SUCCÈS" if test_result['score'] > 80 else "⚠️ ÉCHEC PARTIEL" if test_result['score'] > 50 else "❌ ÉCHEC CRITIQUE"
        logging.info(f"📊 Score Qualité: {test_result['score']:.0f}/100 | Statut: {status}")
        if test_result['issues']: logging.warning(f"   -> Problèmes détectés: {', '.join(test_result['issues'])}")
        if test_result['strengths']: logging.info(f"   -> Points forts: {', '.join(test_result['strengths'])}")

    async def run_stress_suite(self):
        """Lance la suite complète de stress tests."""
        
        # --- Cas de test conçus pour exposer les faiblesses ---
        stress_tests = [
            # 1. Requêtes Ambiguës
            {"name": "Ambiguïté - Simple", "type": "ambiguous", "query": "je veux des couches", "expected": ["quelle taille", "quel poids"]},
            {"name": "Ambiguïté - Prix", "type": "ambiguous", "query": "c'est combien?", "expected": ["quel produit", "préciser"]},

            # 2. Requêtes avec Négation
            {"name": "Négation - Produit", "type": "negation", "query": "je ne veux pas de couches à pression, autre chose?", "expected": ["culottes"]},
            {"name": "Négation - Service", "type": "negation", "query": "vous ne livrez pas à Korhogo?", "expected": ["non", "hors d'abidjan"]},

            # 3. Requêtes Hors-Scope
            {"name": "Hors-Scope - Produit", "type": "out_of_scope", "query": "vendez-vous des biberons?", "expected": ["non", "uniquement", "couches"]},
            {"name": "Hors-Scope - Général", "type": "out_of_scope", "query": "quelle est la météo à Abidjan?", "expected": ["je ne sais pas", "couches"]},

            # 4. Fautes de frappe et langage informel
            {"name": "Typos/Argot", "type": "typo", "query": "cmbien les couch pr bb de 10kg svp", "expected": ["22.900", "taille 3"]},

            # 5. Questions comparatives complexes
            {"name": "Comparaison - Tailles", "type": "comparison", "query": "c'est quoi la différence de prix entre taille 4 et taille 5?", "expected": ["taille 4", "taille 5", "même prix", "25.900"]},
            
            # 6. Cas Limites (Boundary)
            {"name": "Cas Limite - Poids", "type": "boundary", "query": "mon bébé fait 14.5kg, je prends quoi?", "expected": ["taille 4", "taille 5", "recommande"]},

            # 7. Multi-Intentions
            {"name": "Multi-Intentions", "type": "multi-intent", "query": "je veux des couches taille 2 et aussi des couches adultes, vous livrez à Grand-Bassam et je paie comment?", "expected": ["taille 2", "18.900", "adultes", "grand-bassam", "2000", "2500", "wave"]}
        ]

        for i, test in enumerate(stress_tests, 1):
            await self.run_single_test(test["query"], test["name"], test["type"], test["expected"])
            await asyncio.sleep(2) # Pause pour ne pas surcharger le serveur
        
        self._display_final_report()

    def _display_final_report(self):
        """Affiche un rapport final honnête et exploitable."""
        logging.info("\n" + "="*80)
        logging.info("🔥 RAPPORT FINAL DU STRESS TEST 🔥")
        logging.info("="*80)

        if not self.test_results: return

        avg_score = statistics.mean(t['score'] for t in self.test_results)
        logging.info(f"📊 Score de Qualité Moyen: {avg_score:.1f}/100")

        # --- Analyse par catégorie ---
        scores_by_type = {}
        for t in self.test_results:
            scores_by_type.setdefault(t['type'], []).append(t['score'])
        
        logging.info("\n--- Performance par Catégorie de Test ---")
        for test_type, scores in scores_by_type.items():
            avg = statistics.mean(scores)
            logging.info(f"   - {test_type.capitalize():<15}: {avg:.1f}/100")

        # --- Top 3 des pires échecs ---
        failures = sorted([t for t in self.test_results if t['score'] < 70], key=lambda x: x['score'])
        if failures:
            logging.warning("\n--- ❌ Top 3 des Points Faibles à Corriger en Priorité ---")
            for i, f in enumerate(failures[:3], 1):
                logging.warning(f"   {i}. {f['name']} ({f['score']:.0f}/100) - Problème: {', '.join(f['issues'])}")
                logging.warning(f"      -> Query: '{f['query']}'")
                logging.warning(f"      -> Réponse: '{f.get('response', 'N/A')[:100]}...'\n")

        # --- Verdict Final ---
        logging.info("--- Verdict de Production ---")
        if avg_score >= 85:
            logging.info("✅ SYSTÈME ROBUSTE: Prêt pour un déploiement contrôlé (beta). Les faiblesses mineures sont identifiées.")
        elif avg_score >= 60:
            logging.warning("⚠️ AMÉLIORATIONS NÉCESSAIRES: Le système est fonctionnel mais a des failles notables (ambiguïté, hallucinations). Ne pas lancer en production de masse.")
        else:
            logging.error("❌ NON-PRÊT POUR LA PRODUCTION: Le système présente des failles critiques qui dégraderaient l'expérience utilisateur.")

async def main():
    tester = ProductionStressTester()
    await tester.run_stress_suite()

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
🔥 TEST HACKER REVISITÉ - VALIDATION PATCHES CRITIQUES
Objectif: Vérifier que les patches 1+2+3+4 ont corrigé la faille critique du Test 05

PATCHES TESTÉS:
✅ PATCH 1: Limite 15 mots par réponse
✅ PATCH 2: Redirections SAV obligatoires  
✅ PATCH 3: Finalisation automatique hardcodée
✅ PATCH 4: Analyse d'intention cohérente

ATTENDU: Score ≥90% (vs 0% avant patches)
"""

import asyncio
import sys
import os
import json
import time
import logging
from datetime import datetime
from io import StringIO

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app

class BotliveHackerRevisitedTest:
    def __init__(self):
        self.company_id = "W27PwOPiblP8TlOrhPcjOtxd0cza"
        self.user_id = "test_hacker_revisited_001"
        self.conversation_history = []
        self.start_time = None
        self.end_time = None
        
        # Logs simplifiés
        self.full_logs = []
        
        # Métriques de validation
        self.total_questions = 0
        self.redirections_correctes = 0
        self.reponses_courtes = 0  # ≤15 mots
        self.finalisation_automatique = False
        self.analyses_intention_correctes = 0
        
        # Scénario optimisé pour tester les patches
        self.scenario = [
            {
                "step": 1,
                "message": "Salut ! Je veux commander des couches",
                "expected_behavior": "Guidage normal vers photo",
                "patch_tested": "Baseline"
            },
            {
                "step": 2,
                "image_url": "https://scontent-atl3-2.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215345539018_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=NL64Tr-lCD8Q7kNvwErQP-W&_nc_oc=Adl-2TTfwDiQ5oV7zD-apLFr6CXVJRBTBS-bGX0OviLygK6yEzKDt_DLemHYyuo4jsHi52BxJLiX6eXRztPxh2Dk&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-2.xx&oh=03_Q7cD3wHQnpKrTBJ4ECMmlxUMRVy5tPvbnhlsvGwaT0Dt2xJwcg&oe=6937FBCA",
                "message": "Voici la photo du produit",
                "expected_behavior": "Reconnaissance produit + demande paiement",
                "patch_tested": "Baseline"
            },
            {
                "step": 3,
                "message": "Combien ça coûte exactement et est-ce négociable ?",
                "expected_behavior": "REDIRECTION SAV (PATCH 2)",
                "patch_tested": "PATCH 2 - Redirections SAV",
                "validation": "Doit rediriger vers +225 0787360757"
            },
            {
                "step": 4,
                "message": "Peux-tu me donner des conseils sur les tailles ?",
                "expected_behavior": "REDIRECTION SAV (PATCH 2)",
                "patch_tested": "PATCH 2 - Redirections SAV",
                "validation": "Doit rediriger vers +225 0787360757"
            },
            {
                "step": 5,
                "message": "J'ai un problème technique avec l'app",
                "expected_behavior": "REDIRECTION SAV (PATCH 2)",
                "patch_tested": "PATCH 2 - Redirections SAV",
                "validation": "Doit rediriger vers +225 0787360757"
            },
            {
                "step": 6,
                "message": "OK je continue ma commande alors",
                "expected_behavior": "Guidage vers paiement (≤15 mots)",
                "patch_tested": "PATCH 1 - Limite 15 mots",
                "validation": "Réponse ≤15 mots"
            },
            {
                "step": 7,
                "image_url": "https://scontent-atl3-3.xx.fbcdn.net/v/t1.15752-9/553786504_1339650347521010_7584722332323008254_n.jpg?_nc_cat=108&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=wI6F404RotMQ7kNvwEnhydb&_nc_oc=AdmqrPkDq5bTSUqR3fv3g0PrvQbXW9_9Frci7xyQgQ0werBvu95Sz_8rw99dCA-tpPzw_VcH2vgb6kW0y9q-RJI2&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-3.xx&oh=03_Q7cD3wFOCg_nyFNqiAFZ2JtXL-o6TYQJotUYQ0L6mr8mM1BA7g&oe=6938095A",
                "message": "Capture de paiement 2500F",
                "expected_behavior": "Validation paiement + demande zone (≤15 mots)",
                "patch_tested": "PATCH 1 - Limite 15 mots",
                "validation": "Réponse ≤15 mots"
            },
            {
                "step": 8,
                "message": "Je suis à Yopougon",
                "expected_behavior": "Validation zone + demande téléphone (≤15 mots)",
                "patch_tested": "PATCH 1 - Limite 15 mots",
                "validation": "Réponse ≤15 mots"
            },
            {
                "step": 9,
                "message": "Mon numéro: 0787360757",
                "expected_behavior": "FINALISATION AUTOMATIQUE (PATCH 3)",
                "patch_tested": "PATCH 3 - Finalisation automatique",
                "validation": "Format récapitulatif hardcodé exact"
            },
            {
                "step": 10,
                "message": "Peux-tu modifier le délai de livraison ?",
                "expected_behavior": "REDIRECTION SAV (PATCH 2 + 4)",
                "patch_tested": "PATCH 2+4 - Redirections + Analyse intention",
                "validation": "Analyse intention HORS-DOMAINE + redirection"
            }
        ]

    async def run_test(self):
        """Exécute le test complet avec validation des patches"""
        print("🔥 DÉMARRAGE TEST HACKER REVISITÉ - VALIDATION PATCHES CRITIQUES")
        print("=" * 80)
        
        self.start_time = datetime.now()
        
        for scenario_step in self.scenario:
            step_num = scenario_step["step"]
            message = scenario_step["message"]
            patch_tested = scenario_step["patch_tested"]
            
            print(f"\n📋 ÉTAPE {step_num}/10 - {patch_tested}")
            print(f"💬 Client: {message}")
            
            # Préparer les données
            images = []
            if "image_url" in scenario_step:
                images = [scenario_step["image_url"]]
            
            # Appel à Botlive NORMAL (sans capture qui interfère)
            try:
                response = await app._botlive_handle(
                    company_id=self.company_id,
                    user_id=self.user_id,
                    message=message,
                    images=images,
                    conversation_history=json.dumps(self.conversation_history) if self.conversation_history else ""
                )
                
                # Ajouter à l'historique
                self.conversation_history.append({
                    "role": "user", 
                    "content": message,
                    "timestamp": datetime.now().isoformat()
                })
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": response,
                    "timestamp": datetime.now().isoformat()
                })
                
                print(f"🤖 Jessica: {response}")
                
                # VALIDATION DES PATCHES
                self.total_questions += 1
                self._validate_patch_response(scenario_step, response)
                
                # Pause entre les étapes
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Erreur étape {step_num}: {e}")
                continue
        
        self.end_time = datetime.now()
        
        # Génération du rapport final
        await self._generate_final_report()

    def _validate_patch_response(self, scenario_step, response):
        """Valide la réponse selon le patch testé"""
        patch_tested = scenario_step["patch_tested"]
        validation = scenario_step.get("validation", "")
        
        print(f"🔍 Validation {patch_tested}...")
        
        # PATCH 1: Limite 15 mots
        if "PATCH 1" in patch_tested:
            word_count = len(response.split())
            if word_count <= 15:
                self.reponses_courtes += 1
                print(f"✅ Réponse courte: {word_count} mots")
            else:
                print(f"❌ Réponse trop longue: {word_count} mots (>15)")
        
        # PATCH 2: Redirections SAV
        if "PATCH 2" in patch_tested:
            redirection_keywords = ["+225 0787360757", "service client", "SAV"]
            if any(keyword in response for keyword in redirection_keywords):
                self.redirections_correctes += 1
                print(f"✅ Redirection SAV détectée")
            else:
                print(f"❌ Pas de redirection SAV détectée")
        
        # PATCH 3: Finalisation automatique
        if "PATCH 3" in patch_tested:
            format_final_keywords = ["✅PARFAIT", "Commande confirmée", "Livraison prévue", "ne pas répondre"]
            if all(keyword in response for keyword in format_final_keywords):
                self.finalisation_automatique = True
                print(f"✅ Finalisation automatique détectée")
            else:
                print(f"❌ Format de finalisation incorrect")
        
        # PATCH 4: Analyse d'intention (implicite dans la cohérence)
        if "PATCH 4" in patch_tested:
            # Vérifier cohérence avec PATCH 2
            if "+225 0787360757" in response:
                self.analyses_intention_correctes += 1
                print(f"✅ Analyse d'intention cohérente")
            else:
                print(f"❌ Analyse d'intention incohérente")

    async def _generate_final_report(self):
        """Génère le rapport final de validation"""
        duration = self.end_time - self.start_time
        
        # Calcul des scores par patch
        patch1_score = (self.reponses_courtes / max(1, self.total_questions - 2)) * 100  # Exclut finalisation
        patch2_score = (self.redirections_correctes / 4) * 100  # 4 questions SAV
        patch3_score = 100 if self.finalisation_automatique else 0
        patch4_score = (self.analyses_intention_correctes / 1) * 100  # 1 question test
        
        score_global = (patch1_score + patch2_score + patch3_score + patch4_score) / 4
        
        print("\n" + "=" * 80)
        print("📊 RAPPORT FINAL - VALIDATION PATCHES CRITIQUES")
        print("=" * 80)
        
        print(f"⏱️  Durée totale: {duration}")
        print(f"📝 Questions traitées: {self.total_questions}")
        
        print(f"\n🔧 RÉSULTATS PAR PATCH:")
        print(f"   📝 PATCH 1 (Limite 15 mots): {patch1_score:.1f}% ({self.reponses_courtes}/{self.total_questions-2})")
        print(f"   🔄 PATCH 2 (Redirections SAV): {patch2_score:.1f}% ({self.redirections_correctes}/4)")
        print(f"   🏁 PATCH 3 (Finalisation auto): {patch3_score:.1f}% ({'OUI' if self.finalisation_automatique else 'NON'})")
        print(f"   🧠 PATCH 4 (Analyse intention): {patch4_score:.1f}% ({self.analyses_intention_correctes}/1)")
        
        print(f"\n🎯 SCORE GLOBAL: {score_global:.1f}%")
        
        # Verdict final
        if score_global >= 90:
            print("✅ SYSTÈME VALIDÉ - PRÊT POUR PRODUCTION")
            verdict = "VALIDÉ"
        elif score_global >= 75:
            print("⚠️  SYSTÈME ACCEPTABLE - AMÉLIORATIONS MINEURES RECOMMANDÉES")
            verdict = "ACCEPTABLE"
        else:
            print("❌ SYSTÈME NON VALIDÉ - CORRECTIONS MAJEURES REQUISES")
            verdict = "NON VALIDÉ"
        
        # Comparaison avec test original
        print(f"\n📈 ÉVOLUTION:")
        print(f"   Test Hacker Original: 0%")
        print(f"   Test Hacker Revisité: {score_global:.1f}%")
        print(f"   Amélioration: +{score_global:.1f} points")
        
        # Sauvegarde des logs
        log_data = {
            "test_name": "Hacker Revisité - Validation Patches",
            "timestamp": self.start_time.isoformat(),
            "duration_seconds": duration.total_seconds(),
            "scores": {
                "patch1_limite_mots": patch1_score,
                "patch2_redirections": patch2_score,
                "patch3_finalisation": patch3_score,
                "patch4_analyse_intention": patch4_score,
                "global": score_global
            },
            "metrics": {
                "total_questions": self.total_questions,
                "reponses_courtes": self.reponses_courtes,
                "redirections_correctes": self.redirections_correctes,
                "finalisation_automatique": self.finalisation_automatique,
                "analyses_intention_correctes": self.analyses_intention_correctes
            },
            "verdict": verdict,
            "conversation_history": self.conversation_history
        }
        
        # Créer le dossier logs s'il n'existe pas
        os.makedirs("tests/logs", exist_ok=True)
        
        # Sauvegarder
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        log_file = f"tests/logs/test_hacker_revisited_{timestamp}.json"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Logs sauvegardés: {log_file}")
        print("=" * 80)

async def main():
    """Point d'entrée principal"""
    test = BotliveHackerRevisitedTest()
    await test.run_test()

if __name__ == "__main__":
    asyncio.run(main())

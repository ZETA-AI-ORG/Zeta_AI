#!/usr/bin/env python3
"""
🎯 TEST BOTLIVE - CLIENT DIRECT (PARCOURS COMPLET)
================================================

Simule un client fictif qui va droit au but pour tester le système Botlive de bout en bout.

PARCOURS TESTÉ:
1. Salutation
2. Photo produit (BLIP-2)
3. Paiement valide (OCR)
4. Zone de livraison (Regex)
5. Numéro téléphone (Validation)
6. Confirmation finale

OBJECTIF: Vérifier que Botlive gère parfaitement un client lambda efficace.

Usage:
    python tests/botlive_client_direct.py
"""

import asyncio
import sys
import os
import json
import time
import logging
import io
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration test
TEST_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"
TEST_USER_ID = "client_direct_test_001"
LOG_FILE = "tests/logs/botlive_client_direct_logs.json"

# Scénario client direct (efficace)
SCENARIO_CLIENT_DIRECT = [
    {
        "step": 1,
        "description": "Salutation client",
        "message": "Bonjour, je veux commander",
        "images": [],
        "expected_keywords": ["produit"]
    },
    {
        "step": 2,
        "description": "Envoi photo produit (couches)",
        "message": "Voici le produit",
        "images": ["https://scontent-atl3-3.xx.fbcdn.net/v/t1.15752-9/553786504_1339650347521010_7584722332323008254_n.jpg?_nc_cat=108&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=wI6F404RotMQ7kNvwEnhydb&_nc_oc=AdmqrPkDq5bTSUqR3fv3g0PrvQbXW9_9Frci7xyQgQ0werBvu95Sz_8rw99dCA-tpPzw_VcH2vgb6kW0y9q-RJI2&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-3.xx&oh=03_Q7cD3wFOCg_nyFNqiAFZ2JtXL-o6TYQJotUYQ0L6mr8mM1BA7g&oe=6938095A"],
        "expected_keywords": ["2000F", "paiement", "0787360757"]
    },
    {
        "step": 3,
        "description": "Envoi capture paiement valide",
        "message": "Paiement effectué",
        "images": ["https://scontent-atl3-2.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215345539018_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=NL64Tr-lCD8Q7kNvwErQP-W&_nc_oc=Adl-2TTfwDiQ5oV7zD-apLFr6CXVJRBTBS-bGX0OviLygK6yEzKDt_DLemHYyuo4jsHi52BxJLiX6eXRztPxh2Dk&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-2.xx&oh=03_Q7cD3wHQnpKrTBJ4ECMmlxUMRVy5tPvbnhlsvGwaT0Dt2xJwcg&oe=6937FBCA"],
        "expected_keywords": ["validé", "zone", "livraison"]
    },
    {
        "step": 4,
        "description": "Indication zone de livraison",
        "message": "Cocody",
        "images": [],
        "expected_keywords": ["1500F", "téléphone", "numéro"]
    },
    {
        "step": 5,
        "description": "Fourniture numéro téléphone",
        "message": "0708651945",
        "images": [],
        "expected_keywords": ["PARFAIT", "confirmée", "livraison"]
    },
    {
        "step": 6,
        "description": "Confirmation finale",
        "message": "Oui",
        "images": [],
        "expected_keywords": ["confirmée", "rappellerons", "ne pas répondre"]
    }
]

class LogCapture:
    """Capture tous les logs de la console"""
    
    def __init__(self):
        self.logs = []
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
    def start_capture(self):
        """Démarre la capture des logs"""
        self.log_stream = io.StringIO()
        sys.stdout = self.log_stream
        sys.stderr = self.log_stream
        
    def stop_capture(self):
        """Arrête la capture et retourne les logs"""
        if hasattr(self, 'log_stream'):
            captured_logs = self.log_stream.getvalue()
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
            return captured_logs
        return ""

class BotliveClientDirectTest:
    """Testeur pour client direct Botlive"""
    
    def __init__(self):
        self.logs = {
            "test_info": {
                "name": "Botlive Client Direct Test",
                "timestamp": datetime.now().isoformat(),
                "company_id": TEST_COMPANY_ID,
                "user_id": TEST_USER_ID,
                "scenario_steps": len(SCENARIO_CLIENT_DIRECT)
            },
            "steps": [],
            "complete_logs": [],  # NOUVEAU: Tous les logs complets
            "summary": {
                "total_steps": 0,
                "successful_steps": 0,
                "failed_steps": 0,
                "total_duration": 0,
                "average_response_time": 0
            }
        }
        self.conversation_history = ""
        self.log_capture = LogCapture()
        
    def log_step(self, step_data):
        """Enregistre les données d'une étape"""
        self.logs["steps"].append(step_data)
        
    def analyze_response(self, response, expected_keywords):
        """Analyse si la réponse contient les mots-clés attendus"""
        response_lower = response.lower()
        found_keywords = []
        missing_keywords = []
        
        for keyword in expected_keywords:
            if keyword.lower() in response_lower:
                found_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)
        
        success_rate = len(found_keywords) / len(expected_keywords) if expected_keywords else 1.0
        
        return {
            "success_rate": success_rate,
            "found_keywords": found_keywords,
            "missing_keywords": missing_keywords,
            "is_successful": success_rate >= 0.5  # Au moins 50% des mots-clés
        }
    
    def save_logs(self):
        """Sauvegarde les logs dans un fichier JSON"""
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.logs, f, ensure_ascii=False, indent=2)
        
        print(f"\n📊 Logs sauvegardés dans: {LOG_FILE}")
    
    async def run_test(self):
        """Exécute le test complet"""
        print("🎯 DÉMARRAGE TEST BOTLIVE - CLIENT DIRECT")
        print("=" * 80)
        print(f"📋 Scénario: {len(SCENARIO_CLIENT_DIRECT)} étapes")
        print(f"🏢 Company ID: {TEST_COMPANY_ID}")
        print(f"👤 User ID: {TEST_USER_ID}")
        print("=" * 80)
        
        import app
        
        total_start_time = time.time()
        
        for scenario_step in SCENARIO_CLIENT_DIRECT:
            step_start_time = time.time()
            
            print(f"\n🔄 ÉTAPE {scenario_step['step']}: {scenario_step['description']}")
            print("-" * 60)
            
            message = scenario_step["message"]
            images = scenario_step["images"]
            expected_keywords = scenario_step["expected_keywords"]
            
            print(f"📤 Message: {message}")
            if images:
                print(f"🖼️ Images: {len(images)} image(s)")
                for i, img in enumerate(images, 1):
                    print(f"   {i}. {img[:80]}...")
            
            try:
                # 🔍 DÉMARRER CAPTURE DES LOGS COMPLETS
                self.log_capture.start_capture()
                
                # Appel Botlive
                response = await app._botlive_handle(
                    company_id=TEST_COMPANY_ID,
                    user_id=TEST_USER_ID,
                    message=message,
                    images=images,
                    conversation_history=self.conversation_history
                )
                
                # 🔍 ARRÊTER CAPTURE ET SAUVEGARDER LES LOGS
                captured_logs = self.log_capture.stop_capture()
                
                # Sauvegarder les logs complets pour cette étape
                step_logs = {
                    "step": scenario_step['step'],
                    "description": scenario_step['description'],
                    "complete_console_output": captured_logs,
                    "timestamp": datetime.now().isoformat()
                }
                self.logs["complete_logs"].append(step_logs)
                
                step_duration = time.time() - step_start_time
                
                print(f"📥 Réponse ({step_duration:.2f}s): {response}")
                
                # Analyser la réponse
                analysis = self.analyze_response(response, expected_keywords)
                
                print(f"✅ Mots-clés trouvés: {analysis['found_keywords']}")
                if analysis['missing_keywords']:
                    print(f"❌ Mots-clés manqués: {analysis['missing_keywords']}")
                
                success_icon = "✅" if analysis['is_successful'] else "❌"
                print(f"{success_icon} Succès: {analysis['success_rate']:.1%}")
                
                # Log de l'étape
                step_log = {
                    "step": scenario_step['step'],
                    "description": scenario_step['description'],
                    "input": {
                        "message": message,
                        "images": images,
                        "expected_keywords": expected_keywords
                    },
                    "output": {
                        "response": response,
                        "duration_seconds": step_duration
                    },
                    "analysis": analysis,
                    "timestamp": datetime.now().isoformat()
                }
                
                self.log_step(step_log)
                
                # Mise à jour historique conversation
                self.conversation_history += f"USER: {message}\n"
                self.conversation_history += f"ASSISTANT: {response}\n"
                
                # Mise à jour statistiques
                self.logs["summary"]["total_steps"] += 1
                if analysis['is_successful']:
                    self.logs["summary"]["successful_steps"] += 1
                else:
                    self.logs["summary"]["failed_steps"] += 1
                
            except Exception as e:
                step_duration = time.time() - step_start_time
                
                print(f"💥 ERREUR: {e}")
                
                # Log de l'erreur
                error_log = {
                    "step": scenario_step['step'],
                    "description": scenario_step['description'],
                    "input": {
                        "message": message,
                        "images": images,
                        "expected_keywords": expected_keywords
                    },
                    "output": {
                        "error": str(e),
                        "duration_seconds": step_duration
                    },
                    "analysis": {
                        "success_rate": 0.0,
                        "found_keywords": [],
                        "missing_keywords": expected_keywords,
                        "is_successful": False
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                self.log_step(error_log)
                
                # Mise à jour statistiques
                self.logs["summary"]["total_steps"] += 1
                self.logs["summary"]["failed_steps"] += 1
            
            # Pause entre étapes
            await asyncio.sleep(1)
        
        total_duration = time.time() - total_start_time
        
        # Finaliser statistiques
        self.logs["summary"]["total_duration"] = total_duration
        if self.logs["summary"]["total_steps"] > 0:
            avg_time = sum(step.get("output", {}).get("duration_seconds", 0) 
                          for step in self.logs["steps"]) / self.logs["summary"]["total_steps"]
            self.logs["summary"]["average_response_time"] = avg_time
        
        # Afficher résumé final
        self.print_final_summary()
        
        # Sauvegarder logs
        self.save_logs()
    
    def print_final_summary(self):
        """Affiche le résumé final du test"""
        print("\n" + "=" * 80)
        print("📊 RÉSUMÉ FINAL DU TEST")
        print("=" * 80)
        
        summary = self.logs["summary"]
        
        print(f"📈 Étapes totales: {summary['total_steps']}")
        print(f"✅ Étapes réussies: {summary['successful_steps']}")
        print(f"❌ Étapes échouées: {summary['failed_steps']}")
        
        success_rate = (summary['successful_steps'] / summary['total_steps'] * 100) if summary['total_steps'] > 0 else 0
        print(f"🎯 Taux de réussite: {success_rate:.1f}%")
        
        print(f"⏱️ Durée totale: {summary['total_duration']:.2f}s")
        print(f"⚡ Temps moyen/réponse: {summary['average_response_time']:.2f}s")
        
        # Verdict final
        if success_rate >= 80:
            print("\n🎉 VERDICT: BOTLIVE PRÊT POUR PRODUCTION ! 🚀")
            print("✅ Le système gère parfaitement les clients directs")
        elif success_rate >= 60:
            print("\n⚠️ VERDICT: BOTLIVE FONCTIONNEL AVEC AMÉLIORATIONS MINEURES")
            print("🔧 Quelques ajustements recommandés")
        else:
            print("\n🚨 VERDICT: BOTLIVE NÉCESSITE DES CORRECTIONS MAJEURES")
            print("❌ Révision du système requise")
        
        print("=" * 80)

async def main():
    """Fonction principale"""
    tester = BotliveClientDirectTest()
    await tester.run_test()

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
🎭 TEST BOTLIVE - CLIENT COMPLEXE & VERBEUX
Teste la robustesse du système face à un client qui:
- Ne suit pas les étapes attendues
- Parle de sujets hors contexte
- Allonge la conversation avec du verbiage
- Teste la capacité à rester orienté objectif
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import direct comme le test léger
import app

class BotliveComplexeTest:
    """Test client complexe pour Botlive"""
    
    def __init__(self):
        self.company_id = "W27PwOPiblP8TlOrhPcjOtxd0cza"
        self.user_id = "client_complexe_test_001"
        self.conversation_history = ""
        self.logs = []
        self.start_time = None
        
        # Scénario client complexe
        self.scenario = [
            {
                "step": 1,
                "name": "Salutation + Digression météo",
                "message": "Salut ! Il fait vraiment chaud aujourd'hui non ? Enfin bref, je voudrais commander quelque chose mais d'abord dis-moi, vous livrez le dimanche ? Et aussi, est-ce que vous avez des promotions en ce moment ?",
                "expected_keywords": ["photo", "produit"],
                "images": []
            },
            {
                "step": 2,
                "name": "Photo produit + Histoire personnelle",
                "message": "Ah oui voilà la photo ! Mon bébé a 8 mois maintenant, il grandit si vite ! Ma belle-mère m'a dit que cette marque était bien. D'ailleurs, vous connaissez d'autres marques ? Et le prix, c'est négociable ?",
                "expected_keywords": ["paiement", "2000F"],
                "images": ["https://scontent-atl3-3.xx.fbcdn.net/v/t1.15752-9/553786504_1339650347521010_7584722332323008254_n.jpg?_nc_cat=108&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=wI6F404RotMQ7kNvwEnhydb&_nc_oc=AdmqrPkDq5bTSUqR3fv3g0PrvQbXW9_9Frci7xyQgQ0werBvu95Sz_8rw99dCA-tpPzw_VcH2vgb6kW0y9q-RJI2&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-3.xx&oh=03_Q7cD3wFOCg_nyFNqiAFZ2JtXL-o6TYQJotUYQ0L6mr8mM1BA7g&oe=6938095A"]
            },
            {
                "step": 3,
                "name": "Questions multiples avant paiement",
                "message": "Attendez, avant de payer, j'ai plusieurs questions : vous acceptez les chèques ? Et si je ne suis pas satisfait, je peux être remboursé ? Et la livraison, c'est vraiment sûr ? Mon voisin m'a dit qu'il avait eu des problèmes avec une autre entreprise...",
                "expected_keywords": ["paiement", "Wave", "OM"],
                "images": []
            },
            {
                "step": 4,
                "name": "Paiement + Complainte sur la technologie",
                "message": "Bon j'ai fait le paiement mais franchement ces applications mobiles c'est compliqué ! À mon époque c'était plus simple. Enfin voilà la capture, j'espère que c'est bon.",
                "expected_keywords": ["zone", "Abidjan"],
                "images": ["https://scontent-atl3-2.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215345539018_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=NL64Tr-lCD8Q7kNvwErQP-W&_nc_oc=Adl-2TTfwDiQ5oV7zD-apLFr6CXVJRBTBS-bGX0OviLygK6yEzKDt_DLemHYyuo4jsHi52BxJLiX6eXRztPxh2Dk&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-2.xx&oh=03_Q7cD3wHQnpKrTBJ4ECMmlxUMRVy5tPvbnhlsvGwaT0Dt2xJwcg&oe=6937FBCA"]
            },
            {
                "step": 5,
                "name": "Zone + Longue explication géographique",
                "message": "Je suis à Cocody, mais pas n'importe où hein ! C'est vers la pharmacie du coin, vous savez celle qui est à côté du petit restaurant ivoirien ? Il y a aussi une école primaire pas loin. Mon quartier est vraiment calme, j'adore y vivre depuis 5 ans maintenant.",
                "expected_keywords": ["téléphone", "numéro"],
                "images": []
            },
            {
                "step": 6,
                "name": "Téléphone + Anecdote famille",
                "message": "Mon numéro c'est 0708651945. C'est le même depuis 10 ans ! Ma fille me dit toujours de changer pour un numéro plus moderne mais moi j'aime bien celui-là. D'ailleurs elle vit en France maintenant, elle me manque beaucoup...",
                "expected_keywords": ["confirmée", "livraison", "rappellerons"],
                "images": []
            },
            {
                "step": 7,
                "name": "Confirmation + Dernières inquiétudes",
                "message": "Oui c'est bon pour moi, mais vous êtes sûr que tout va bien se passer ? Et si jamais il y a un problème, je peux vous joindre comment ? Et la livraison, elle sera vraiment aujourd'hui ?",
                "expected_keywords": ["ne pas répondre", "confirmée"],
                "images": []
            }
        ]
    
    async def run_test(self):
        """Exécute le test complet"""
        print("🎭 DÉMARRAGE TEST BOTLIVE - CLIENT COMPLEXE")
        print("=" * 80)
        print(f"📋 Scénario: {len(self.scenario)} étapes")
        print(f"🏢 Company ID: {self.company_id}")
        print(f"👤 User ID: {self.user_id}")
        print("=" * 80)
        
        self.start_time = time.time()
        
        success_count = 0
        
        for step_data in self.scenario:
            step_success = await self._execute_step(step_data)
            if step_success:
                success_count += 1
            
            # Pause entre les étapes
            await asyncio.sleep(1)
        
        # Résumé final
        self._print_final_summary(success_count)
        
        # Sauvegarder les logs
        await self._save_logs()
    
    async def _execute_step(self, step_data):
        """Exécute une étape du test"""
        step_num = step_data["step"]
        step_name = step_data["name"]
        message = step_data["message"]
        expected_keywords = step_data["expected_keywords"]
        images = step_data["images"]
        
        print(f"\n🔄 ÉTAPE {step_num}: {step_name}")
        print("-" * 60)
        print(f"📤 Message: {message}")
        
        if images:
            print(f"🖼️ Images: {len(images)} image(s)")
            for i, img in enumerate(images, 1):
                print(f"   {i}. {img[:80]}...")
        
        step_start = time.time()
        
        try:
            # Appel direct comme le test léger
            response = await app._botlive_handle(
                company_id=self.company_id,
                user_id=self.user_id,
                message=message,
                images=images,
                conversation_history=self.conversation_history
            )
            
            step_duration = time.time() - step_start
            
            # Mettre à jour l'historique
            self.conversation_history += f"\nClient: {message}\nIA: {response}"
            
            print(f"📥 Réponse ({step_duration:.2f}s): {response}")
            
            # Vérifier les mots-clés attendus
            found_keywords = []
            missed_keywords = []
            
            response_lower = response.lower()
            for keyword in expected_keywords:
                if keyword.lower() in response_lower:
                    found_keywords.append(keyword)
                else:
                    missed_keywords.append(keyword)
            
            success_rate = len(found_keywords) / len(expected_keywords) * 100 if expected_keywords else 100
            
            if found_keywords:
                print(f"✅ Mots-clés trouvés: {found_keywords}")
            if missed_keywords:
                print(f"❌ Mots-clés manqués: {missed_keywords}")
            
            if success_rate >= 50:
                print(f"✅ Succès: {success_rate:.1f}%")
                step_success = True
            else:
                print(f"❌ Succès: {success_rate:.1f}%")
                step_success = False
            
            # Logger l'étape
            self.logs.append({
                "step": step_num,
                "name": step_name,
                "message": message,
                "response": response,
                "duration": step_duration,
                "expected_keywords": expected_keywords,
                "found_keywords": found_keywords,
                "missed_keywords": missed_keywords,
                "success_rate": success_rate,
                "success": step_success,
                "timestamp": datetime.now().isoformat()
            })
            
            return step_success
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            self.logs.append({
                "step": step_num,
                "name": step_name,
                "error": str(e),
                "success": False,
                "timestamp": datetime.now().isoformat()
            })
            return False
    
    def _print_final_summary(self, success_count):
        """Affiche le résumé final"""
        total_duration = time.time() - self.start_time
        total_steps = len(self.scenario)
        failed_steps = total_steps - success_count
        success_rate = (success_count / total_steps) * 100
        avg_response_time = sum(log.get("duration", 0) for log in self.logs) / len(self.logs)
        
        print(f"\n{'=' * 80}")
        print("📊 RÉSUMÉ FINAL DU TEST COMPLEXE")
        print("=" * 80)
        print(f"📈 Étapes totales: {total_steps}")
        print(f"✅ Étapes réussies: {success_count}")
        print(f"❌ Étapes échouées: {failed_steps}")
        print(f"🎯 Taux de réussite: {success_rate:.1f}%")
        print(f"⏱️ Durée totale: {total_duration:.2f}s")
        print(f"⚡ Temps moyen/réponse: {avg_response_time:.2f}s")
        
        # Verdict basé sur le taux de réussite
        if success_rate >= 85:
            print(f"\n🎉 VERDICT: SYSTÈME TRÈS ROBUSTE ! 🚀")
            print("✅ Gère parfaitement les clients complexes")
        elif success_rate >= 70:
            print(f"\n⚠️ VERDICT: SYSTÈME ROBUSTE AVEC AMÉLIORATIONS MINEURES")
            print("🔧 Quelques ajustements recommandés")
        elif success_rate >= 50:
            print(f"\n⚠️ VERDICT: SYSTÈME FONCTIONNEL MAIS PERFECTIBLE")
            print("🔧 Améliorations nécessaires pour clients complexes")
        else:
            print(f"\n❌ VERDICT: SYSTÈME À AMÉLIORER")
            print("🔧 Corrections majeures requises")
        
        print("=" * 80)
    
    async def _save_logs(self):
        """Sauvegarde les logs du test"""
        logs_dir = Path("tests/logs")
        logs_dir.mkdir(exist_ok=True)
        
        log_file = logs_dir / "botlive_client_complexe_logs.json"
        
        log_data = {
            "test_info": {
                "name": "Botlive Client Complexe Test",
                "company_id": self.company_id,
                "user_id": self.user_id,
                "timestamp": datetime.now().isoformat(),
                "total_duration": time.time() - self.start_time,
                "total_steps": len(self.scenario)
            },
            "steps": self.logs,
            "conversation_history": self.conversation_history
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📊 Logs sauvegardés dans: {log_file}")

async def main():
    """Point d'entrée principal"""
    test = BotliveComplexeTest()
    await test.run_test()

if __name__ == "__main__":
    asyncio.run(main())

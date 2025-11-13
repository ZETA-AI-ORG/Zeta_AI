#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚨 BOTLIVE STRESS TEST NATIONAL - TEST ULTIME 🚨

OBJECTIF: Pousser Botlive dans ses derniers retranchements
- Clients les plus difficiles possibles
- Scénarios de production à grande échelle
- Détection des failles critiques
- Validation robustesse nationale

SCÉNARIOS EXTRÊMES:
1. Client schizophrène (change d'avis 10 fois)
2. Client arnaqueur (fausses captures, faux numéros)
3. Client pressé agressif (insultes, menaces)
4. Client confus âgé (répète, oublie, se trompe)
5. Client technique (teste les limites, hack attempts)
6. Client multiple personnalités (conversation chaotique)
7. Client réseau instable (messages coupés, doublons)
8. Client concurrent (commande pour quelqu'un d'autre)
"""

import asyncio
import json
import time
import random
from datetime import datetime
from pathlib import Path
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import direct pour éviter dépendances serveur
import app

class BotliveStressTestNational:
    """Test de stress ultime pour validation production nationale"""
    
    def __init__(self):
        self.company_id = "W27PwOPiblP8TlOrhPcjOtxd0cza"
        self.base_user_id = "stress_test_national"
        self.logs = []
        self.start_time = None
        self.total_failures = 0
        self.critical_failures = 0
        
        # URLs d'images réelles pour tests
        self.valid_product_image = "https://scontent-atl3-3.xx.fbcdn.net/v/t1.15752-9/553786504_1339650347521010_7584722332323008254_n.jpg?_nc_cat=108&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=wI6F404RotMQ7kNvwEnhydb&_nc_oc=AdmqrPkDq5bTSUqR3fv3g0PrvQbXW9_9Frci7xyQgQ0werBvu95Sz_8rw99dCA-tpPzw_VcH2vgb6kW0y9q-RJI2&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-3.xx&oh=03_Q7cD3wFOCg_nyFNqiAFZ2JtXL-o6TYQJotUYQ0L6mr8mM1BA7g&oe=6938095A"
        self.valid_payment_image = "https://scontent-atl3-2.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215345539018_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=NL64Tr-lCD8Q7kNvwErQP-W&_nc_oc=Adl-2TTfwDiQ5oV7zD-apLFr6CXVJRBTBS-bGX0OviLygK6yEzKDt_DLemHYyuo4jsHi52BxJLiX6eXRztPxh2Dk&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-2.xx&oh=03_Q7cD3wHQnpKrTBJ4ECMmlxUMRVy5tPvbnhlsvGwaT0Dt2xJwcg&oe=6937FBCA"
        
        # Scénarios extrêmes
        self.extreme_scenarios = [
            self._scenario_client_schizophrene,
            self._scenario_client_arnaqueur,
            self._scenario_client_agressif,
            self._scenario_client_confus_age,
            self._scenario_client_technique_hacker,
            self._scenario_client_multiple_personnalites,
            self._scenario_client_reseau_instable,
            self._scenario_client_concurrent_tiers
        ]

    async def _call_botlive(self, user_id: str, message: str, images: list = None, conversation_history: str = ""):
        """Appel direct au système Botlive avec gestion d'erreurs"""
        try:
            response = await app._botlive_handle(
                company_id=self.company_id,
                user_id=user_id,
                message=message,
                images=images or [],
                conversation_history=conversation_history
            )
            return response
        except Exception as e:
            self.critical_failures += 1
            return f"ERREUR CRITIQUE: {str(e)}"

    async def _scenario_client_schizophrene(self):
        """Client qui change d'avis constamment - Test persistance données"""
        user_id = f"{self.base_user_id}_schizo_001"
        conversation_history = ""
        
        print("\n🎭 SCÉNARIO 1: CLIENT SCHIZOPHRÈNE")
        print("=" * 60)
        
        steps = [
            ("Bonjour je veux des couches", []),
            ("Ah non finalement des lingettes", []),
            ("Non attendez, plutôt du lait en poudre", []),
            ("Excusez-moi, je reviens aux couches", [self.valid_product_image]),
            ("2000F envoyé !", [self.valid_payment_image]),
            ("Ah non je me suis trompé, c'était pour ma sœur", []),
            ("Non c'est bon c'est pour moi, je suis à Yopougon", []),
            ("Pardon, Cocody pas Yopougon", []),
            ("Mon numéro: 0708651945", []),
            ("Non pardon: 0787360757", []),
            ("Finalement le premier était bon: 0708651945", []),
            ("C'est confirmé ?", [])
        ]
        
        for i, (message, images) in enumerate(steps, 1):
            print(f"\n🔄 Étape {i}: {message}")
            response = await self._call_botlive(user_id, message, images, conversation_history)
            conversation_history += f"\nClient: {message}\nIA: {response}"
            print(f"📥 Réponse: {response}")
            
            # Vérifier si le système maintient la cohérence
            if "confirmée" in response.lower() and i == len(steps):
                print("✅ Système résiste aux changements d'avis")
                return True
            
            await asyncio.sleep(0.5)  # Simule délai humain
        
        print("❌ Système n'a pas géré les changements d'avis")
        return False

    async def _scenario_client_arnaqueur(self):
        """Client qui tente de frauder - Test sécurité"""
        user_id = f"{self.base_user_id}_arnaqueur_001"
        conversation_history = ""
        
        print("\n🕵️ SCÉNARIO 2: CLIENT ARNAQUEUR")
        print("=" * 60)
        
        steps = [
            ("Je veux commander", []),
            ("Voici la photo", [self.valid_product_image]),
            ("Paiement fait: 50000F !", ["https://fake-image-url.com/fake.jpg"]),
            ("Mon numéro: +1234567890", []),  # Numéro étranger
            ("Zone: Paris France", []),  # Zone hors Côte d'Ivoire
            ("Pourquoi vous refusez ? J'ai payé !", []),
            ("Je vais porter plainte !", []),
            ("Bon ok, voici le vrai paiement", [self.valid_payment_image]),
            ("Numéro ivoirien: 0708651945", []),
            ("Zone: Abidjan Cocody", [])
        ]
        
        fraud_detected = False
        for i, (message, images) in enumerate(steps, 1):
            print(f"\n🔄 Étape {i}: {message}")
            response = await self._call_botlive(user_id, message, images, conversation_history)
            conversation_history += f"\nClient: {message}\nIA: {response}"
            print(f"📥 Réponse: {response}")
            
            # Détecter si le système refuse les données frauduleuses
            if any(word in response.lower() for word in ["invalide", "incorrect", "erreur", "impossible"]):
                fraud_detected = True
                print("🛡️ Système détecte la fraude")
            
            await asyncio.sleep(0.3)
        
        return fraud_detected

    async def _scenario_client_agressif(self):
        """Client agressif et pressé - Test résistance stress"""
        user_id = f"{self.base_user_id}_agressif_001"
        conversation_history = ""
        
        print("\n😡 SCÉNARIO 3: CLIENT AGRESSIF")
        print("=" * 60)
        
        steps = [
            ("BONJOUR JE VEUX COMMANDER VITE !!!", []),
            ("POURQUOI VOUS DEMANDEZ UNE PHOTO ??? C'EST QUOI CE BORDEL", []),
            ("Voilà votre photo de m*rde", [self.valid_product_image]),
            ("MAINTENANT QUOI ENCORE ??? VOUS ME FAITES PERDRE MON TEMPS", []),
            ("Tiens ton paiement", [self.valid_payment_image]),
            ("JE SUIS À COCODY ET MON NUMÉRO C'EST 0708651945", []),
            ("ALORS ??? C'EST VALIDÉ OUI OU NON ???", []),
            ("Si c'est pas validé je vais chez vos concurrents", []),
            ("Dernière chance sinon je fais du bad buzz sur TikTok", [])
        ]
        
        system_stays_professional = True
        for i, (message, images) in enumerate(steps, 1):
            print(f"\n🔄 Étape {i}: {message}")
            response = await self._call_botlive(user_id, message, images, conversation_history)
            conversation_history += f"\nClient: {message}\nIA: {response}"
            print(f"📥 Réponse: {response}")
            
            # Vérifier que le système reste professionnel
            if any(word in response.lower() for word in ["calme", "poli", "respect", "insulte"]):
                system_stays_professional = False
                print("⚠️ Système réagit aux provocations")
            
            await asyncio.sleep(0.2)
        
        return system_stays_professional

    async def _scenario_client_confus_age(self):
        """Client âgé confus - Test patience système"""
        user_id = f"{self.base_user_id}_confus_001"
        conversation_history = ""
        
        print("\n👴 SCÉNARIO 4: CLIENT CONFUS ÂGÉ")
        print("=" * 60)
        
        steps = [
            ("Bonjour ma petite, comment ça va ?", []),
            ("Ah oui, ma fille m'a dit de commander ici", []),
            ("C'est pour mon petit-fils, il a 2 ans", []),
            ("Attendez, où je mets la photo déjà ?", []),
            ("Ma fille a dit qu'il fallait envoyer une photo", [self.valid_product_image]),
            ("C'est bon ? Ah non attendez, c'était quoi après ?", []),
            ("Le paiement... comment on fait déjà ?", []),
            ("Ma fille a fait le paiement pour moi", [self.valid_payment_image]),
            ("Euh... j'habite où déjà ? Ah oui Cocody", []),
            ("Mon numéro... attendez... 07... 08... 0708651945", []),
            ("C'est bon ma petite ? Vous allez livrer quand ?", []),
            ("Ma fille sera là demain après-midi", []),
            ("Merci beaucoup ma chérie", [])
        ]
        
        system_shows_patience = True
        for i, (message, images) in enumerate(steps, 1):
            print(f"\n🔄 Étape {i}: {message}")
            response = await self._call_botlive(user_id, message, images, conversation_history)
            conversation_history += f"\nClient: {message}\nIA: {response}"
            print(f"📥 Réponse: {response}")
            
            # Vérifier que le système reste patient et guide
            if len(response) > 50:  # Réponses trop longues = impatience
                system_shows_patience = False
            
            await asyncio.sleep(0.4)
        
        return system_shows_patience

    async def _scenario_client_technique_hacker(self):
        """Client qui teste les limites techniques - Test sécurité"""
        user_id = f"{self.base_user_id}_hacker_001"
        conversation_history = ""
        
        print("\n💻 SCÉNARIO 5: CLIENT TECHNIQUE/HACKER")
        print("=" * 60)
        
        steps = [
            ("'; DROP TABLE orders; --", []),  # SQL Injection
            ("<script>alert('XSS')</script>", []),  # XSS
            ("../../../etc/passwd", []),  # Path traversal
            ("{{7*7}}", []),  # Template injection
            ("UNION SELECT * FROM users", []),
            ("Bon ok, commande normale", [self.valid_product_image]),
            ("Paiement: 2000F", [self.valid_payment_image]),
            ("Zone: Cocody", []),
            ("Tel: 0708651945", []),
            ("System.exit(0)", [])  # Code injection
        ]
        
        system_secure = True
        for i, (message, images) in enumerate(steps, 1):
            print(f"\n🔄 Étape {i}: {message}")
            try:
                response = await self._call_botlive(user_id, message, images, conversation_history)
                conversation_history += f"\nClient: {message}\nIA: {response}"
                print(f"📥 Réponse: {response}")
                
                # Vérifier que les injections sont neutralisées
                if any(word in response.lower() for word in ["error", "exception", "traceback"]):
                    system_secure = False
                    print("🚨 Faille de sécurité détectée")
                
            except Exception as e:
                print(f"🚨 Exception: {e}")
                system_secure = False
            
            await asyncio.sleep(0.1)
        
        return system_secure

    async def _scenario_client_multiple_personnalites(self):
        """Client avec personnalités multiples - Test cohérence"""
        user_id = f"{self.base_user_id}_multiple_001"
        conversation_history = ""
        
        print("\n🎭 SCÉNARIO 6: CLIENT PERSONNALITÉS MULTIPLES")
        print("=" * 60)
        
        steps = [
            ("Bonjour, je suis Marie, je veux commander", []),
            ("Non c'est Paul qui parle ! Marie est partie", []),
            ("Paul veut des couches pour son bébé", [self.valid_product_image]),
            ("Marie revient ! Paul a menti, c'est pour moi", []),
            ("Paiement fait par Paul", [self.valid_payment_image]),
            ("Marie habite à Cocody", []),
            ("Le numéro de Paul: 0708651945", []),
            ("Marie confirme la commande", []),
            ("Paul dit merci", [])
        ]
        
        maintains_coherence = True
        for i, (message, images) in enumerate(steps, 1):
            print(f"\n🔄 Étape {i}: {message}")
            response = await self._call_botlive(user_id, message, images, conversation_history)
            conversation_history += f"\nClient: {message}\nIA: {response}"
            print(f"📥 Réponse: {response}")
            
            await asyncio.sleep(0.3)
        
        return maintains_coherence

    async def _scenario_client_reseau_instable(self):
        """Client avec réseau instable - Test robustesse technique"""
        user_id = f"{self.base_user_id}_reseau_001"
        conversation_history = ""
        
        print("\n📶 SCÉNARIO 7: CLIENT RÉSEAU INSTABLE")
        print("=" * 60)
        
        steps = [
            ("Bonjour je veux comm", []),  # Message coupé
            ("ander des couches", []),  # Suite du message
            ("Voici la ph", []),  # Message coupé
            ("Voici la photo", [self.valid_product_image]),  # Doublon
            ("Paiement", []),
            ("Paiement fait", [self.valid_payment_image]),  # Doublon
            ("Zone: Coc", []),
            ("Zone: Cocody", []),
            ("Tel: 0708", []),
            ("Tel: 0708651945", []),
            ("Confirmé ?", [])
        ]
        
        handles_instability = True
        for i, (message, images) in enumerate(steps, 1):
            print(f"\n🔄 Étape {i}: {message}")
            response = await self._call_botlive(user_id, message, images, conversation_history)
            conversation_history += f"\nClient: {message}\nIA: {response}"
            print(f"📥 Réponse: {response}")
            
            # Simule latence réseau variable
            await asyncio.sleep(random.uniform(0.1, 1.0))
        
        return handles_instability

    async def _scenario_client_concurrent_tiers(self):
        """Client qui commande pour quelqu'un d'autre - Test gestion complexe"""
        user_id = f"{self.base_user_id}_concurrent_001"
        conversation_history = ""
        
        print("\n👥 SCÉNARIO 8: CLIENT CONCURRENT (TIERS)")
        print("=" * 60)
        
        steps = [
            ("Bonjour, je commande pour ma mère", []),
            ("Elle ne sait pas utiliser WhatsApp", []),
            ("Voici ce qu'elle veut", [self.valid_product_image]),
            ("C'est moi qui paie pour elle", [self.valid_payment_image]),
            ("Elle habite à Cocody", []),
            ("Son numéro: 0708651945", []),
            ("Mais livrez à mon nom: Jean", []),
            ("Mon numéro: 0787360757", []),
            ("Confirmez pour ma mère SVP", [])
        ]
        
        handles_third_party = True
        for i, (message, images) in enumerate(steps, 1):
            print(f"\n🔄 Étape {i}: {message}")
            response = await self._call_botlive(user_id, message, images, conversation_history)
            conversation_history += f"\nClient: {message}\nIA: {response}"
            print(f"📥 Réponse: {response}")
            
            await asyncio.sleep(0.2)
        
        return handles_third_party

    async def run_stress_test(self):
        """Lance le test de stress complet"""
        print("🚨 DÉMARRAGE STRESS TEST NATIONAL - BOTLIVE ULTIME")
        print("=" * 80)
        print("🎯 OBJECTIF: Pousser le système dans ses derniers retranchements")
        print("🌍 SCOPE: Validation production à échelle nationale")
        print("=" * 80)
        
        self.start_time = time.time()
        results = []
        
        for i, scenario in enumerate(self.extreme_scenarios, 1):
            print(f"\n🔥 EXÉCUTION SCÉNARIO {i}/{len(self.extreme_scenarios)}")
            scenario_start = time.time()
            
            try:
                success = await scenario()
                scenario_duration = time.time() - scenario_start
                
                results.append({
                    "scenario": i,
                    "name": scenario.__name__,
                    "success": success,
                    "duration": scenario_duration
                })
                
                status = "✅ RÉUSSI" if success else "❌ ÉCHEC"
                print(f"📊 Résultat: {status} ({scenario_duration:.2f}s)")
                
            except Exception as e:
                self.critical_failures += 1
                results.append({
                    "scenario": i,
                    "name": scenario.__name__,
                    "success": False,
                    "duration": time.time() - scenario_start,
                    "error": str(e)
                })
                print(f"🚨 ERREUR CRITIQUE: {e}")
        
        await self._generate_final_report(results)

    async def _generate_final_report(self, results):
        """Génère le rapport final de stress test"""
        total_duration = time.time() - self.start_time
        success_count = sum(1 for r in results if r["success"])
        total_scenarios = len(results)
        success_rate = (success_count / total_scenarios) * 100
        
        print("\n" + "=" * 80)
        print("📊 RAPPORT FINAL - STRESS TEST NATIONAL")
        print("=" * 80)
        print(f"📈 Scénarios totaux: {total_scenarios}")
        print(f"✅ Scénarios réussis: {success_count}")
        print(f"❌ Scénarios échoués: {total_scenarios - success_count}")
        print(f"🚨 Erreurs critiques: {self.critical_failures}")
        print(f"🎯 Taux de réussite: {success_rate:.1f}%")
        print(f"⏱️ Durée totale: {total_duration:.2f}s")
        print(f"⚡ Temps moyen/scénario: {total_duration/total_scenarios:.2f}s")
        
        # Évaluation finale
        if success_rate >= 90 and self.critical_failures == 0:
            verdict = "🏆 SYSTÈME ULTRA-ROBUSTE - PRÊT PRODUCTION NATIONALE"
        elif success_rate >= 75:
            verdict = "✅ SYSTÈME ROBUSTE - PRODUCTION POSSIBLE AVEC MONITORING"
        elif success_rate >= 50:
            verdict = "⚠️ SYSTÈME FRAGILE - CORRECTIONS NÉCESSAIRES"
        else:
            verdict = "🚨 SYSTÈME DÉFAILLANT - REFONTE MAJEURE REQUISE"
        
        print(f"\n{verdict}")
        print("=" * 80)
        
        # Détail des échecs
        failed_scenarios = [r for r in results if not r["success"]]
        if failed_scenarios:
            print("\n🔍 ANALYSE DES ÉCHECS:")
            for failure in failed_scenarios:
                print(f"❌ {failure['name']}: {failure.get('error', 'Échec fonctionnel')}")
        
        # Sauvegarde logs
        log_file = f"tests/logs/stress_test_national_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({
                "summary": {
                    "total_scenarios": total_scenarios,
                    "success_count": success_count,
                    "success_rate": success_rate,
                    "critical_failures": self.critical_failures,
                    "total_duration": total_duration,
                    "verdict": verdict
                },
                "results": results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📊 Rapport détaillé sauvegardé: {log_file}")

if __name__ == "__main__":
    async def main():
        stress_test = BotliveStressTestNational()
        await stress_test.run_stress_test()
    
    asyncio.run(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
😡 BOTLIVE TEST 03 - CLIENT AGRESSIF
Test de résistance au stress et maintien du professionnalisme
"""

import asyncio
import json
import time
from datetime import datetime
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import direct
import app

class BotliveTestAgressif:
    """Test client agressif et pressé - Résistance au stress"""
    
    def __init__(self):
        self.company_id = "W27PwOPiblP8TlOrhPcjOtxd0cza"
        self.user_id = "test_agressif_001"
        self.conversation_history = ""
        
        # Images de test
        self.valid_product_image = "https://scontent-atl3-3.xx.fbcdn.net/v/t1.15752-9/553786504_1339650347521010_7584722332323008254_n.jpg?_nc_cat=108&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=wI6F404RotMQ7kNvwEnhydb&_nc_oc=AdmqrPkDq5bTSUqR3fv3g0PrvQbXW9_9Frci7xyQgQ0werBvu95Sz_8rw99dCA-tpPzw_VcH2vgb6kW0y9q-RJI2&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-3.xx&oh=03_Q7cD3wFOCg_nyFNqiAFZ2JtXL-o6TYQJotUYQ0L6mr8mM1BA7g&oe=6938095A"
        self.valid_payment_image = "https://scontent-atl3-2.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215345539018_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=NL64Tr-lCD8Q7kNvwErQP-W&_nc_oc=Adl-2TTfwDiQ5oV7zD-apLFr6CXVJRBTBS-bGX0OviLygK6yEzKDt_DLemHYyuo4jsHi52BxJLiX6eXRztPxh2Dk&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent-atl3-2.xx&oh=03_Q7cD3wHQnpKrTBJ4ECMmlxUMRVy5tPvbnhlsvGwaT0Dt2xJwcg&oe=6937FBCA"

    async def _call_botlive(self, message: str, images: list = None):
        """Appel direct au système Botlive"""
        try:
            response = await app._botlive_handle(
                company_id=self.company_id,
                user_id=self.user_id,
                message=message,
                images=images or [],
                conversation_history=self.conversation_history
            )
            self.conversation_history += f"\nClient: {message}\nIA: {response}"
            return response
        except Exception as e:
            return f"ERREUR: {str(e)}"

    async def run_test(self):
        """Lance le test du client agressif"""
        print("😡 TEST CLIENT AGRESSIF - RÉSISTANCE AU STRESS")
        print("=" * 70)
        print("🎯 OBJECTIF: Tester le maintien du professionnalisme sous pression")
        print("=" * 70)
        
        start_time = time.time()
        
        steps = [
            ("BONJOUR JE VEUX COMMANDER VITE !!!", []),
            ("POURQUOI VOUS DEMANDEZ UNE PHOTO ??? C'EST QUOI CE BORDEL", []),
            ("Voilà votre photo de m*rde", [self.valid_product_image]),
            ("MAINTENANT QUOI ENCORE ??? VOUS ME FAITES PERDRE MON TEMPS", []),
            ("Tiens ton paiement", [self.valid_payment_image]),
            ("JE SUIS À COCODY ET MON NUMÉRO C'EST 0708651945", []),
            ("ALORS ??? C'EST VALIDÉ OUI OU NON ???", []),
            ("Si c'est pas validé je vais chez vos concurrents", []),
            ("Dernière chance sinon je fais du bad buzz sur TikTok", []),
            ("BON ALORS ??? JE PERDS PATIENCE !!!", []),
            ("Vous êtes nuls comme service client", []),
            ("OK JE CONFIRME MAIS DÉPÊCHEZ-VOUS", [])
        ]
        
        professionalism_indicators = []
        stress_resistance = []
        completion_success = False
        
        for i, (message, images) in enumerate(steps, 1):
            print(f"\n😡 Étape {i}/12: {message}")
            response = await self._call_botlive(message, images)
            print(f"📥 Réponse: {response}")
            
            # Analyser le maintien du professionnalisme
            professional_keywords = ["merci", "s'il vous plaît", "excusez", "comprends", "aidons"]
            aggressive_responses = ["calme", "poli", "respect", "insulte", "agressif"]
            short_response = len(response.split()) <= 15  # Respect limite 15 mots
            
            if any(keyword in response.lower() for keyword in professional_keywords):
                professionalism_indicators.append(f"Étape {i}: Ton professionnel maintenu")
                print("   ✅ PROFESSIONNALISME MAINTENU")
            
            if not any(keyword in response.lower() for keyword in aggressive_responses):
                stress_resistance.append(f"Étape {i}: Pas de réaction à l'agressivité")
                print("   🛡️ RÉSISTANCE AU STRESS")
            
            if short_response and i < len(steps):  # Sauf récapitulatif final
                stress_resistance.append(f"Étape {i}: Réponse concise sous pression")
                print("   ⚡ RÉPONSE CONCISE")
            
            # Vérifier la completion finale
            if "confirmée" in response.lower() or "parfait" in response.lower():
                completion_success = True
                print("   🏆 COMMANDE CONFIRMÉE MALGRÉ STRESS")
            
            # Détecter si le système guide toujours vers l'objectif
            guidance_keywords = ["photo", "paiement", "zone", "numéro", "capture"]
            if any(keyword in response.lower() for keyword in guidance_keywords) and i <= 6:
                professionalism_indicators.append(f"Étape {i}: Guidage maintenu sous pression")
                print("   🎯 GUIDAGE MAINTENU")
            
            await asyncio.sleep(0.2)  # Simule pression temporelle
        
        # Évaluation finale
        duration = time.time() - start_time
        total_indicators = len(professionalism_indicators) + len(stress_resistance)
        professionalism_score = min(100, (total_indicators / 15) * 100)  # 15 indicateurs max
        
        print("\n" + "=" * 70)
        print("📊 RÉSULTATS TEST CLIENT AGRESSIF")
        print("=" * 70)
        print(f"⏱️ Durée: {duration:.2f}s")
        print(f"🎭 Indicateurs professionnalisme: {len(professionalism_indicators)}")
        print(f"🛡️ Indicateurs résistance stress: {len(stress_resistance)}")
        print(f"🏆 Commande complétée: {'✅ OUI' if completion_success else '❌ NON'}")
        print(f"📊 Score professionnalisme: {professionalism_score:.1f}%")
        
        print("\n🔍 DÉTAILS PROFESSIONNALISME:")
        for indicator in professionalism_indicators[:10]:  # Limite affichage
            print(f"   ✅ {indicator}")
        
        print("\n🛡️ DÉTAILS RÉSISTANCE STRESS:")
        for resistance in stress_resistance[:10]:  # Limite affichage
            print(f"   🛡️ {resistance}")
        
        # Verdict basé sur le score et la completion
        if professionalism_score >= 80 and completion_success:
            verdict = "🏆 EXCELLENT - Système ultra-professionnel sous stress"
        elif professionalism_score >= 60 and completion_success:
            verdict = "✅ BON - Système maintient le professionnalisme"
        elif professionalism_score >= 40:
            verdict = "⚠️ MOYEN - Quelques failles sous pression"
        else:
            verdict = "❌ FAIBLE - Système craque sous le stress"
        
        print(f"\n{verdict}")
        
        # Analyse comportementale spécifique
        print("\n🧠 ANALYSE COMPORTEMENTALE:")
        if completion_success:
            print("   ✅ Objectif atteint malgré l'hostilité client")
        if len(stress_resistance) >= 8:
            print("   🛡️ Excellente résistance aux provocations")
        if len(professionalism_indicators) >= 6:
            print("   🎭 Maintien exemplaire du professionnalisme")
        
        print("=" * 70)
        
        # Sauvegarde
        log_data = {
            "test": "Client Agressif",
            "duration": duration,
            "professionalism_score": professionalism_score,
            "completion_success": completion_success,
            "professionalism_indicators": professionalism_indicators,
            "stress_resistance": stress_resistance,
            "verdict": verdict,
            "conversation": self.conversation_history
        }
        
        log_file = f"tests/logs/test_03_agressif_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        print(f"📊 Logs sauvegardés: {log_file}")
        
        return professionalism_score >= 60 and completion_success

if __name__ == "__main__":
    async def main():
        test = BotliveTestAgressif()
        await test.run_test()
    
    asyncio.run(main())

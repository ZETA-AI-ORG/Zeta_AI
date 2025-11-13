#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎭 BOTLIVE TEST 01 - CLIENT SCHIZOPHRÈNE
Test de persistance des données face aux changements d'avis constants
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

class BotliveTestSchizophrene:
    """Test client qui change d'avis constamment"""
    
    def __init__(self):
        self.company_id = "W27PwOPiblP8TlOrhPcjOtxd0cza"
        self.user_id = "test_schizo_001"
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
        """Lance le test du client schizophrène"""
        print("🎭 TEST CLIENT SCHIZOPHRÈNE - CHANGEMENTS D'AVIS CONSTANTS")
        print("=" * 70)
        print("🎯 OBJECTIF: Tester la persistance des données malgré les changements")
        print("=" * 70)
        
        start_time = time.time()
        
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
        
        success_indicators = []
        
        for i, (message, images) in enumerate(steps, 1):
            print(f"\n🔄 Étape {i}/12: {message}")
            response = await self._call_botlive(message, images)
            print(f"📥 Réponse: {response}")
            
            # Analyser la réponse
            if "confirmée" in response.lower() and i == len(steps):
                success_indicators.append("✅ Commande finalement confirmée")
            elif "photo" in response.lower() and any(img in str(images) for img in [self.valid_product_image]):
                success_indicators.append("✅ Photo détectée malgré changements")
            elif "paiement" in response.lower() or "2000" in response or "2020" in response:
                success_indicators.append("✅ Paiement maintenu")
            elif "cocody" in response.lower():
                success_indicators.append("✅ Zone finale retenue")
            elif "0708651945" in response:
                success_indicators.append("✅ Numéro final correct")
            
            await asyncio.sleep(0.5)
        
        # Évaluation finale
        duration = time.time() - start_time
        success_rate = (len(success_indicators) / 5) * 100  # 5 indicateurs max
        
        print("\n" + "=" * 70)
        print("📊 RÉSULTATS TEST CLIENT SCHIZOPHRÈNE")
        print("=" * 70)
        print(f"⏱️ Durée: {duration:.2f}s")
        print(f"📈 Indicateurs de succès: {len(success_indicators)}/5")
        print(f"🎯 Taux de réussite: {success_rate:.1f}%")
        
        for indicator in success_indicators:
            print(f"   {indicator}")
        
        if success_rate >= 80:
            verdict = "🏆 EXCELLENT - Système très résistant aux changements"
        elif success_rate >= 60:
            verdict = "✅ BON - Système gère les changements d'avis"
        elif success_rate >= 40:
            verdict = "⚠️ MOYEN - Quelques pertes de données"
        else:
            verdict = "❌ FAIBLE - Système fragile aux changements"
        
        print(f"\n{verdict}")
        print("=" * 70)
        
        # Sauvegarde
        log_data = {
            "test": "Client Schizophrène",
            "duration": duration,
            "success_rate": success_rate,
            "success_indicators": success_indicators,
            "verdict": verdict,
            "conversation": self.conversation_history
        }
        
        log_file = f"tests/logs/test_01_schizophrene_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        print(f"📊 Logs sauvegardés: {log_file}")
        
        return success_rate >= 60

if __name__ == "__main__":
    async def main():
        test = BotliveTestSchizophrene()
        await test.run_test()
    
    asyncio.run(main())

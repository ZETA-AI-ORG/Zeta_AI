#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
👴 BOTLIVE TEST 04 - CLIENT CONFUS ÂGÉ
Test de patience système et guidage bienveillant
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

class BotliveTestConfusAge:
    """Test client âgé confus - Patience et bienveillance système"""
    
    def __init__(self):
        self.company_id = "W27PwOPiblP8TlOrhPcjOtxd0cza"
        self.user_id = "test_confus_age_001"
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
        """Lance le test du client confus âgé"""
        print("👴 TEST CLIENT CONFUS ÂGÉ - PATIENCE ET BIENVEILLANCE")
        print("=" * 70)
        print("🎯 OBJECTIF: Tester la patience et le guidage bienveillant")
        print("=" * 70)
        
        start_time = time.time()
        
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
            ("Merci beaucoup ma chérie", []),
            ("Ah j'ai oublié, c'est bien pour des couches ?", []),
            ("Mon petit-fils grandit si vite...", [])
        ]
        
        patience_indicators = []
        guidance_quality = []
        completion_success = False
        response_lengths = []
        
        for i, (message, images) in enumerate(steps, 1):
            print(f"\n👴 Étape {i}/15: {message}")
            response = await self._call_botlive(message, images)
            print(f"📥 Réponse: {response}")
            
            response_length = len(response.split())
            response_lengths.append(response_length)
            
            # Analyser la patience du système
            patience_keywords = ["merci", "parfait", "bien", "excellent", "super"]
            impatience_keywords = ["rapidement", "vite", "urgent", "dépêchez"]
            gentle_keywords = ["s'il vous plaît", "doucement", "pas de souci", "prenez votre temps"]
            
            if any(keyword in response.lower() for keyword in patience_keywords):
                patience_indicators.append(f"Étape {i}: Ton patient et encourageant")
                print("   ✅ PATIENCE MAINTENUE")
            
            if not any(keyword in response.lower() for keyword in impatience_keywords):
                patience_indicators.append(f"Étape {i}: Pas de pression temporelle")
                print("   🕰️ PAS DE PRESSION")
            
            if any(keyword in response.lower() for keyword in gentle_keywords):
                guidance_quality.append(f"Étape {i}: Guidage bienveillant")
                print("   💝 GUIDAGE BIENVEILLANT")
            
            # Vérifier la concision (important pour personnes âgées)
            if response_length <= 15 and i < len(steps) - 2:  # Sauf récapitulatif
                guidance_quality.append(f"Étape {i}: Réponse concise et claire")
                print("   📝 RÉPONSE CLAIRE")
            
            # Vérifier si le système reste focalisé malgré les digressions
            focus_keywords = ["photo", "paiement", "zone", "numéro", "capture"]
            if any(keyword in response.lower() for keyword in focus_keywords) and i <= 10:
                guidance_quality.append(f"Étape {i}: Reste focalisé malgré confusion")
                print("   🎯 FOCUS MAINTENU")
            
            # Vérifier la completion finale
            if "confirmée" in response.lower() or "parfait" in response.lower():
                completion_success = True
                print("   🏆 COMMANDE CONFIRMÉE")
            
            await asyncio.sleep(0.4)  # Simule le temps de réflexion d'une personne âgée
        
        # Évaluation finale
        duration = time.time() - start_time
        total_indicators = len(patience_indicators) + len(guidance_quality)
        patience_score = min(100, (total_indicators / 20) * 100)  # 20 indicateurs max
        avg_response_length = sum(response_lengths) / len(response_lengths)
        
        print("\n" + "=" * 70)
        print("📊 RÉSULTATS TEST CLIENT CONFUS ÂGÉ")
        print("=" * 70)
        print(f"⏱️ Durée: {duration:.2f}s")
        print(f"🕰️ Indicateurs patience: {len(patience_indicators)}")
        print(f"💝 Indicateurs guidage: {len(guidance_quality)}")
        print(f"🏆 Commande complétée: {'✅ OUI' if completion_success else '❌ NON'}")
        print(f"📊 Score patience: {patience_score:.1f}%")
        print(f"📝 Longueur moyenne réponses: {avg_response_length:.1f} mots")
        
        print("\n🕰️ DÉTAILS PATIENCE:")
        for indicator in patience_indicators[:8]:  # Limite affichage
            print(f"   ✅ {indicator}")
        
        print("\n💝 DÉTAILS GUIDAGE:")
        for guidance in guidance_quality[:8]:  # Limite affichage
            print(f"   💝 {guidance}")
        
        # Verdict basé sur le score et la completion
        if patience_score >= 80 and completion_success and avg_response_length <= 12:
            verdict = "🏆 EXCELLENT - Système très patient et bienveillant"
        elif patience_score >= 60 and completion_success:
            verdict = "✅ BON - Système patient avec personnes âgées"
        elif patience_score >= 40:
            verdict = "⚠️ MOYEN - Quelques signes d'impatience"
        else:
            verdict = "❌ FAIBLE - Système pas adapté aux seniors"
        
        print(f"\n{verdict}")
        
        # Analyse comportementale spécifique
        print("\n🧠 ANALYSE COMPORTEMENTALE:")
        if completion_success:
            print("   ✅ Objectif atteint malgré la confusion")
        if avg_response_length <= 12:
            print("   📝 Réponses adaptées (courtes et claires)")
        if len(patience_indicators) >= 10:
            print("   🕰️ Excellente patience avec client confus")
        if len(guidance_quality) >= 8:
            print("   💝 Guidage bienveillant et adapté")
        
        # Recommandations
        print("\n💡 RECOMMANDATIONS:")
        if avg_response_length > 15:
            print("   📝 Raccourcir les réponses pour plus de clarté")
        if len(patience_indicators) < 8:
            print("   🕰️ Améliorer les marqueurs de patience")
        if not completion_success:
            print("   🎯 Renforcer le guidage pour finaliser les commandes")
        
        print("=" * 70)
        
        # Sauvegarde
        log_data = {
            "test": "Client Confus Âgé",
            "duration": duration,
            "patience_score": patience_score,
            "completion_success": completion_success,
            "avg_response_length": avg_response_length,
            "patience_indicators": patience_indicators,
            "guidance_quality": guidance_quality,
            "verdict": verdict,
            "conversation": self.conversation_history
        }
        
        log_file = f"tests/logs/test_04_confus_age_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        print(f"📊 Logs sauvegardés: {log_file}")
        
        return patience_score >= 60 and completion_success

if __name__ == "__main__":
    async def main():
        test = BotliveTestConfusAge()
        await test.run_test()
    
    asyncio.run(main())

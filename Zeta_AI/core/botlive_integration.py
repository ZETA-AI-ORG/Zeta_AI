#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔗 BOTLIVE INTEGRATION - Interface pour analyse images
Connecte le système Botlive existant au nouveau système d'analyse
"""

import base64
import tempfile
import os
from typing import Dict, Any
from pathlib import Path


async def analyze_image_with_botlive(
    image_data: str,
    user_id: str,
    context: str = "",
    company_phone: str = None,
    required_amount: int = None
) -> Dict[str, Any]:
    """
    Appelle le système Botlive existant pour analyser une image
    
    Args:
        image_data: Image en base64
        user_id: ID utilisateur
        context: Contexte conversation
        company_phone: Numéro Wave entreprise (extrait du prompt)
        required_amount: Acompte requis (extrait du prompt)
    
    Returns:
        {
            "analysis": "Texte brut de l'analyse Botlive",
            "confidence": 0.95,
            "raw_data": {...}
        }
    """
    
    print(f"🔗 [BOTLIVE_INTEGRATION] Appel Botlive pour user {user_id}")
    
    try:
        # Importer BotliveEngine
        from core.botlive_engine import BotliveEngine
        
        # Initialiser engine (singleton recommandé mais pour l'instant on instancie)
        engine = BotliveEngine()
        
        # Sauvegarder image temporairement (Botlive attend un chemin fichier)
        temp_image_path = _save_base64_to_temp(image_data)
        
        if not temp_image_path:
            raise Exception("Impossible de sauvegarder l'image temporaire")
        
        print(f"📁 [BOTLIVE_INTEGRATION] Image sauvegardée: {temp_image_path}")
        
        # Détecter type d'image (paiement vs produit)
        # On essaie d'abord OCR paiement, si ça échoue on fait produit
        
        # 1. Essayer OCR paiement avec VALIDATION STRICTE
        # Utiliser valeurs passées en paramètre (extraites du prompt) avec fallback
        final_company_phone = company_phone or "+225 0787360757"
        final_required_amount = required_amount or 2000
        
        print(f"📋 [BOTLIVE_INTEGRATION] Config: Phone={final_company_phone}, Amount={final_required_amount} FCFA")
        
        payment_result = engine.verify_payment(
            image_path=temp_image_path,
            company_phone=final_company_phone,
            required_amount=final_required_amount
        )
        
        if payment_result and payment_result.get("amount"):
            # C'est un paiement!
            print(f"💰 [BOTLIVE_INTEGRATION] Paiement détecté: {payment_result['amount']} {payment_result.get('currency', 'FCFA')}")
            
            analysis_text = f"Paiement Wave détecté. Montant: {payment_result['amount']} {payment_result.get('currency', 'FCFA')}. "
            if payment_result.get("phone"):
                analysis_text += f"Numéro: {payment_result['phone']}. "
            if payment_result.get("reference"):
                analysis_text += f"Référence: {payment_result['reference']}."
            
            result = {
                "analysis": analysis_text,
                "confidence": 0.90,
                "raw_data": payment_result
            }
        
        else:
            # Pas de paiement détecté → Essayer produit
            print(f"📦 [BOTLIVE_INTEGRATION] Tentative détection produit...")
            
            product_result = engine.detect_product(temp_image_path)
            
            analysis_text = f"Produit détecté: {product_result.get('name', 'Non identifié')}."
            
            result = {
                "analysis": analysis_text,
                "confidence": product_result.get("confidence", 0.75),
                "raw_data": product_result
            }
        
        # Nettoyer fichier temporaire
        try:
            os.remove(temp_image_path)
            print(f"🗑️  [BOTLIVE_INTEGRATION] Fichier temporaire supprimé")
        except:
            pass
        
        print(f"✅ [BOTLIVE_INTEGRATION] Analyse réussie (confiance: {result['confidence']:.2f})")
        return result
        
    except Exception as e:
        print(f"❌ [BOTLIVE_INTEGRATION] Erreur: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "analysis": "",
            "confidence": 0.0,
            "error": str(e)
        }


def _save_base64_to_temp(image_data: str) -> str:
    """
    Sauvegarde image base64 dans un fichier temporaire
    
    Args:
        image_data: Image en base64 (avec ou sans préfixe data:image/...)
    
    Returns:
        Chemin du fichier temporaire
    """
    try:
        # Nettoyer le préfixe data:image si présent
        if "," in image_data:
            image_data = image_data.split(",")[1]
        
        # Décoder base64
        image_bytes = base64.b64decode(image_data)
        
        # Créer fichier temporaire
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"botlive_image_{os.getpid()}.jpg")
        
        with open(temp_path, "wb") as f:
            f.write(image_bytes)
        
        return temp_path
        
    except Exception as e:
        print(f"❌ [SAVE_TEMP] Erreur: {e}")
        return None

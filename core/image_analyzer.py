#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📸 IMAGE ANALYZER - Interface Botlive pour RAG
Analyse images (produits/paiements) et retourne DATA structurée
Botlive = Extracteur silencieux, RAG = Conversationnel
"""

import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime


class ImageAnalyzer:
    """
    Analyse images via Botlive et retourne données structurées
    """
    
    def __init__(self):
        self.redis_client = None
        self._init_redis()
    
    def _init_redis(self):
        """Initialise connexion Redis pour cache"""
        try:
            import redis
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True
            )
            self.redis_client.ping()
            print("✅ [IMAGE_ANALYZER] Redis connecté")
        except Exception as e:
            print(f"⚠️ [IMAGE_ANALYZER] Redis non disponible: {e}")
            self.redis_client = None
    
    def _get_image_hash(self, image_data: str) -> str:
        """Génère hash unique pour l'image (pour cache)"""
        return hashlib.md5(image_data.encode()).hexdigest()[:16]
    
    async def analyze(
        self,
        image_data: str,
        user_id: str,
        context: str = "",
        company_phone: str = None,
        required_amount: int = None
    ) -> Dict[str, Any]:
        """
        Analyse une image et retourne données structurées
        
        Args:
            image_data: Image en base64
            user_id: ID utilisateur
            context: Contexte conversation (optionnel)
        
        Returns:
            {
                "type": "product" | "payment",
                "data": {...},
                "confidence": float,
                "cached": bool
            }
        """
        print(f"📸 [IMAGE_ANALYZER] Analyse image pour user {user_id}")
        
        # Vérifier cache
        image_hash = self._get_image_hash(image_data)
        cached_result = self._get_from_cache(image_hash)
        if cached_result:
            print("⚡ [CACHE HIT] Analyse déjà en cache")
            cached_result["cached"] = True
            return cached_result
        
        print("📭 [CACHE MISS] Appel Botlive nécessaire")
        
        # Appel Botlive pour analyse
        result = await self._call_botlive(image_data, user_id, context, company_phone, required_amount)
        
        # Mettre en cache 24h
        self._save_to_cache(image_hash, result)
        
        result["cached"] = False
        return result
    
    async def _call_botlive(
        self,
        image_data: str,
        user_id: str,
        context: str,
        company_phone: str = None,
        required_amount: int = None
    ) -> Dict[str, Any]:
        """
        Appelle Botlive pour analyser l'image
        Retourne données structurées (pas de texte conversationnel)
        """
        print("🔍 [BOTLIVE_CALL] Analyse en cours...")
        
        try:
            from core.botlive_integration import analyze_image_with_botlive
            
            # Appel Botlive avec config entreprise
            botlive_result = await analyze_image_with_botlive(
                image_data=image_data,
                user_id=user_id,
                context=context,
                company_phone=company_phone,
                required_amount=required_amount
            )
            
            # Classifier et structurer
            classified = self._classify_and_structure(botlive_result)
            
            print(f"✅ [BOTLIVE_SUCCESS] Type: {classified['type']}")
            return classified
            
        except Exception as e:
            print(f"❌ [BOTLIVE_ERROR] {e}")
            return {
                "type": "unknown",
                "data": {},
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _classify_and_structure(self, botlive_result: Dict) -> Dict[str, Any]:
        """
        Classifie le type d'image et structure les données
        """
        raw_text = botlive_result.get("analysis", "").lower()
        confidence = botlive_result.get("confidence", 0.0)
        
        # Détection paiement Wave
        if any(keyword in raw_text for keyword in ["wave", "paiement", "transfert", "transaction", "fcfa"]):
            print("💰 [CLASSIFY] Type: PAYMENT")
            return self._extract_payment_data(botlive_result, confidence)
        
        # Détection produit
        elif any(keyword in raw_text for keyword in ["couche", "paquet", "lot", "taille", "pampers"]):
            print("📦 [CLASSIFY] Type: PRODUCT")
            return self._extract_product_data(botlive_result, confidence)
        
        # Type inconnu
        else:
            print("❓ [CLASSIFY] Type: UNKNOWN")
            return {
                "type": "unknown",
                "data": {"raw_text": raw_text},
                "confidence": confidence
            }
    
    def _extract_payment_data(self, botlive_result: Dict, confidence: float) -> Dict[str, Any]:
        """Extrait données de paiement Wave"""
        import re
        
        raw_text = botlive_result.get("analysis", "")
        
        # Extraire montant (accepte 3 à 5 chiffres : 202, 1000, 2020, etc.)
        amount_match = re.search(r'(\d{3,5})\s*(?:FCFA|F|CFA)', raw_text)
        amount = int(amount_match.group(1)) if amount_match else 0
        
        # Extraire numéro téléphone
        phone_match = re.search(r'(\+?225\s?)?0?([0-9]{10})', raw_text)
        phone = phone_match.group(0) if phone_match else ""
        
        # Extraire ID transaction
        transaction_match = re.search(r'(WV|TRX|ID)[:\s]*([A-Z0-9]+)', raw_text, re.IGNORECASE)
        transaction_id = transaction_match.group(2) if transaction_match else ""
        
        # Vérifier validité
        verified = amount >= 2000  # Minimum acompte
        
        return {
            "type": "payment",
            "data": {
                "amount": amount,
                "phone": phone,
                "transaction_id": transaction_id,
                "verified": verified,
                "raw_text": raw_text,
                "verified_at": datetime.now().isoformat()
            },
            "confidence": confidence
        }
    
    def _extract_product_data(self, botlive_result: Dict, confidence: float) -> Dict[str, Any]:
        """Extrait données produit"""
        import re
        
        raw_text = botlive_result.get("analysis", "")
        
        # Extraire taille
        size_match = re.search(r'taille\s*(\d+)', raw_text, re.IGNORECASE)
        size = f"Taille {size_match.group(1)}" if size_match else "Non détectée"
        
        # Extraire quantité
        qty_match = re.search(r'(\d+)\s*(?:pièces|couches|pcs)', raw_text, re.IGNORECASE)
        quantity = qty_match.group(1) if qty_match else "Non détectée"
        
        # Extraire marque
        brand = "Pampers" if "pampers" in raw_text.lower() else "Couches"
        
        # Extraire type
        product_type = "Couches culottes" if "culotte" in raw_text.lower() else "Couches à pression"
        
        return {
            "type": "product",
            "data": {
                "product_name": f"{brand} {product_type}",
                "size": size,
                "quantity_visible": quantity,
                "brand": brand,
                "product_type": product_type,
                "packaging": "Paquet standard",
                "condition": "Neuf",
                "raw_text": raw_text
            },
            "confidence": confidence
        }
    
    def _get_from_cache(self, image_hash: str) -> Optional[Dict]:
        """Récupère analyse depuis cache Redis"""
        if not self.redis_client:
            return None
        
        try:
            cached = self.redis_client.get(f"image_analysis:{image_hash}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            print(f"⚠️ [CACHE_ERROR] {e}")
        
        return None
    
    def _save_to_cache(self, image_hash: str, result: Dict):
        """Sauvegarde analyse en cache 24h"""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.setex(
                f"image_analysis:{image_hash}",
                86400,  # 24h
                json.dumps(result)
            )
            print("💾 [CACHE_SAVED] Analyse mise en cache 24h")
        except Exception as e:
            print(f"⚠️ [CACHE_ERROR] {e}")


# ============================================================================
# SINGLETON
# ============================================================================

_image_analyzer: Optional[ImageAnalyzer] = None


def get_image_analyzer() -> ImageAnalyzer:
    """Récupère instance singleton"""
    global _image_analyzer
    if _image_analyzer is None:
        _image_analyzer = ImageAnalyzer()
    return _image_analyzer


# ============================================================================
# FONCTION HELPER POUR RAG
# ============================================================================

async def analyze_image_for_rag(
    image_data: str,
    user_id: str,
    context: str = "",
    company_phone: str = None,
    required_amount: int = None
) -> Dict[str, Any]:
    """
    Interface simple pour le RAG
    
    Usage:
        result = await analyze_image_for_rag(image, user_id, context)
        if result["type"] == "payment":
            # Traiter paiement
        elif result["type"] == "product":
            # Traiter produit
    """
    analyzer = get_image_analyzer()
    return await analyzer.analyze(image_data, user_id, context, company_phone, required_amount)

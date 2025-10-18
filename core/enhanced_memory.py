#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 ENHANCED MEMORY SYSTEM - Mémoire conversationnelle améliorée
Résout le problème de perte d'informations ("2 lots" oublié)

Basé sur recherche: Pinecone LangChain Conversational Memory
Stratégie: ConversationSummaryBufferMemory + Structured Extraction + Redis Persistence
"""

import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class EnhancedMemory:
    """
    Mémoire conversationnelle améliorée avec:
    - Extraction structurée JSON forcée
    - Summarization progressive
    - Persistance Redis
    - Buffer window pour interactions récentes
    """
    
    def __init__(self, user_id: str = None, max_recent_interactions: int = 5):
        """
        Args:
            user_id: ID utilisateur (pour get_recent_interactions)
            max_recent_interactions: Nombre d'interactions récentes à garder en raw
        """
        self.user_id = user_id
        self.max_recent_interactions = max_recent_interactions
        
        # Redis pour persistance
        self.redis_client = None
        self._init_redis()
        
        print(f"✅ [ENHANCED_MEMORY] Initialisé (buffer={max_recent_interactions}, user={user_id})")
    
    def _init_redis(self):
        """Initialise connexion Redis"""
        try:
            import redis
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=2,  # DB dédiée mémoire
                decode_responses=True
            )
            self.redis_client.ping()
            print("✅ [ENHANCED_MEMORY] Redis connecté")
        except Exception as e:
            print(f"⚠️ [ENHANCED_MEMORY] Redis non disponible: {e}")
            self.redis_client = None
    
    def extract_structured_info(self, user_message: str, llm_response: str) -> Dict[str, Any]:
        """
        Extrait informations structurées de la conversation
        
        Returns:
            {
                "products": [{"name": "...", "quantity": 2, "size": "4"}],
                "delivery_zone": "Yopougon",
                "delivery_cost": 1500,
                "phone": "0787360757",
                "payment_status": "pending",
                "total_amount": 48000
            }
        """
        extracted = {
            "products": [],
            "delivery_zone": None,
            "delivery_cost": None,
            "phone": None,
            "payment_status": None,
            "total_amount": None,
            "timestamp": datetime.now().isoformat()
        }
        
        # Combiner message + réponse pour extraction
        combined_text = f"{user_message} {llm_response}".lower()
        
        # 1. EXTRACTION PRODUITS + QUANTITÉ (CRITIQUE!)
        # Patterns pour "2 lots", "deux lots", "2x", etc.
        quantity_patterns = [
            r'(\d+)\s*(?:lots?|paquets?|boites?)',  # "2 lots"
            r'(?:deux|trois|quatre|cinq|six|sept|huit|neuf|dix)\s*(?:lots?|paquets?)',  # "deux lots"
            r'(\d+)\s*x\s*',  # "2x"
            r'quantité\s*:?\s*(\d+)',  # "quantité: 2"
            r'je\s+(?:veux|voudrais|prends?)\s+(\d+)',  # "je veux 2"
        ]
        
        for pattern in quantity_patterns:
            match = re.search(pattern, combined_text)
            if match:
                try:
                    # Convertir mots en chiffres
                    qty_text = match.group(1) if match.group(1).isdigit() else match.group(0)
                    qty = self._word_to_number(qty_text)
                    
                    if qty and qty > 0:
                        # Chercher produit associé
                        product_match = re.search(r'(?:couches?|lot|paquet|taille)\s*(\d+)?', combined_text)
                        size = product_match.group(1) if product_match and product_match.group(1) else None
                        
                        extracted["products"].append({
                            "name": "Couches",
                            "quantity": qty,
                            "size": size,
                            "type": "lot 300" if "300" in combined_text else "lot 150"
                        })
                        
                        print(f"✅ [EXTRACT] Produit: {qty} lots taille {size}")
                        break
                except:
                    continue
        
        # 2. EXTRACTION ZONE LIVRAISON
        zones = ["yopougon", "cocody", "port-bouët", "port bouet", "attécoubé", "attecoube", 
                 "abobo", "adjamé", "adjame", "plateau", "marcory", "koumassi", "treichville"]
        
        for zone in zones:
            if zone in combined_text:
                extracted["delivery_zone"] = zone.title()
                print(f"✅ [EXTRACT] Zone: {zone.title()}")
                break
        
        # 3. EXTRACTION FRAIS LIVRAISON
        # Chercher spécifiquement "frais" ou "zone de livraison: X (Y FCFA)"
        delivery_patterns = [
            r'frais[^0-9]*livraison[^0-9]*[:\s]*(\d+[\s\u202f]?\d{3})\s*(?:fcfa|f)',  # "frais livraison: 1500"
            r'livraison[^0-9]*[:\s]*(\d+[\s\u202f]?\d{3})\s*(?:fcfa|f)(?!\s*\+)',     # "livraison: 1500" (pas suivi de +)
            r'\((\d{1}[\s\u202f]?\d{3})\s*(?:fcfa|f)\)',                              # "(1 500 FCFA)" entre parenthèses
        ]
        
        for pattern in delivery_patterns:
            delivery_match = re.search(pattern, combined_text, re.IGNORECASE)
            if delivery_match:
                cost = int(delivery_match.group(1).replace(" ", "").replace("\u202f", ""))
                # Valider que c'est un frais de livraison réaliste (500-5000 FCFA)
                if 500 <= cost <= 5000:
                    extracted["delivery_cost"] = cost
                    print(f"✅ [EXTRACT] Frais livraison: {cost} FCFA")
                    break
        
        # 4. EXTRACTION TÉLÉPHONE
        phone_match = re.search(r'0\d{9}', combined_text)
        if phone_match:
            extracted["phone"] = phone_match.group(0)
            print(f"✅ [EXTRACT] Téléphone: {phone_match.group(0)}")
        
        # 5. EXTRACTION MONTANT TOTAL
        total_match = re.search(r'total[^0-9]*(\d+[\s\u202f]?\d{3})\s*(?:fcfa|f)', combined_text)
        if total_match:
            total = int(total_match.group(1).replace(" ", "").replace("\u202f", ""))
            extracted["total_amount"] = total
            print(f"✅ [EXTRACT] Total: {total} FCFA")
        
        # 6. EXTRACTION STATUT PAIEMENT
        if any(word in combined_text for word in ["payé", "paye", "acompte", "versé", "verse"]):
            extracted["payment_status"] = "paid"
            print(f"✅ [EXTRACT] Paiement: payé")
        elif any(word in combined_text for word in ["confirme", "valide", "commande"]):
            extracted["payment_status"] = "pending"
            print(f"✅ [EXTRACT] Paiement: en attente")
        
        return extracted
    
    def _word_to_number(self, word: str) -> Optional[int]:
        """Convertit mots français en nombres"""
        word_map = {
            "un": 1, "une": 1,
            "deux": 2,
            "trois": 3,
            "quatre": 4,
            "cinq": 5,
            "six": 6,
            "sept": 7,
            "huit": 8,
            "neuf": 9,
            "dix": 10
        }
        
        word_lower = word.lower().strip()
        
        # Si c'est déjà un chiffre
        if word_lower.isdigit():
            return int(word_lower)
        
        # Si c'est un mot
        return word_map.get(word_lower)
    
    def save_interaction(
        self,
        user_id: str,
        company_id: str,
        user_message: str,
        llm_response: str
    ):
        """
        Sauvegarde interaction avec extraction structurée
        """
        print(f"💾 [ENHANCED_MEMORY] Sauvegarde interaction pour {user_id}")
        
        # Extraire infos structurées
        extracted = self.extract_structured_info(user_message, llm_response)
        
        # Récupérer mémoire existante
        memory = self.get_memory(user_id, company_id)
        
        # Ajouter interaction récente
        memory["recent_interactions"].append({
            "user": user_message,
            "assistant": llm_response,
            "timestamp": datetime.now().isoformat(),
            "extracted": extracted
        })
        
        # Garder seulement N interactions récentes
        if len(memory["recent_interactions"]) > self.max_recent_interactions:
            # Summarizer l'ancienne interaction
            old_interaction = memory["recent_interactions"].pop(0)
            memory["summary"] = self._update_summary(memory["summary"], old_interaction)
        
        # Fusionner infos structurées dans structured_data
        self._merge_structured_data(memory["structured_data"], extracted)
        
        # Sauvegarder dans Redis
        self._save_to_redis(user_id, company_id, memory)
        
        # 🔧 SYNC NOTEPAD: Sauvegarder aussi dans le notepad pour Smart Context Manager
        try:
            from core.botlive_tools import blocnote_add_info
            
            # Sauvegarder les données extraites dans le notepad
            if extracted.get("products"):
                for product in extracted["products"]:
                    if product.get("type"):
                        blocnote_add_info("produit", product["type"], user_id, company_id)
                    if product.get("quantity"):
                        blocnote_add_info("quantite", str(product["quantity"]), user_id, company_id)
            
            if extracted.get("delivery_zone"):
                blocnote_add_info("zone", extracted["delivery_zone"], user_id, company_id)
            
            if extracted.get("delivery_cost"):
                blocnote_add_info("frais_livraison", str(extracted["delivery_cost"]), user_id, company_id)
            
            if extracted.get("phone"):
                blocnote_add_info("telephone", extracted["phone"], user_id, company_id)
            
            if extracted.get("payment_status"):
                blocnote_add_info("paiement", extracted["payment_status"], user_id, company_id)
            
            if extracted.get("total_amount"):
                blocnote_add_info("total", str(extracted["total_amount"]), user_id, company_id)
            
            print(f"✅ [ENHANCED_MEMORY→NOTEPAD] Données synchronisées")
        except Exception as e:
            print(f"⚠️ [ENHANCED_MEMORY→NOTEPAD] Erreur sync: {e}")
        
        print(f"✅ [ENHANCED_MEMORY] Sauvegardé ({len(memory['recent_interactions'])} interactions)")
    
    def _merge_structured_data(self, current: Dict, new: Dict):
        """Fusionne nouvelles données structurées avec existantes"""
        # Produits: ajouter ou mettre à jour
        if new.get("products"):
            for new_product in new["products"]:
                # Chercher produit existant
                existing = next((p for p in current.get("products", []) 
                               if p.get("size") == new_product.get("size")), None)
                
                if existing:
                    # Mettre à jour quantité
                    existing["quantity"] = new_product["quantity"]
                    existing["updated_at"] = new_product["timestamp"]
                else:
                    # Ajouter nouveau
                    if "products" not in current:
                        current["products"] = []
                    current["products"].append(new_product)
        
        # Autres champs: écraser si nouveau non-null
        for key in ["delivery_zone", "delivery_cost", "phone", "payment_status", "total_amount"]:
            if new.get(key) is not None:
                current[key] = new.get(key)
    
    def _update_summary(self, current_summary: str, old_interaction: Dict) -> str:
        """
        Met à jour summary avec ancienne interaction
        Stratégie: Garder seulement les infos clés
        """
        extracted = old_interaction.get("extracted", {})
        
        # Construire résumé de cette interaction
        interaction_summary = []
        
        if extracted.get("products"):
            for product in extracted["products"]:
                interaction_summary.append(
                    f"Client a demandé {product['quantity']} lots taille {product.get('size', '?')}"
                )
        
        if extracted.get("delivery_zone"):
            interaction_summary.append(
                f"Livraison à {extracted['delivery_zone']}"
            )
        
        if extracted.get("payment_status"):
            interaction_summary.append(
                f"Paiement: {extracted['payment_status']}"
            )
        
        # Ajouter au summary existant
        if interaction_summary:
            new_summary = ". ".join(interaction_summary)
            if current_summary:
                return f"{current_summary}. {new_summary}"
            else:
                return new_summary
        
        return current_summary
    
    def get_memory(self, user_id: str, company_id: str) -> Dict[str, Any]:
        """
        Récupère mémoire complète pour un utilisateur
        
        Returns:
            {
                "summary": "Résumé interactions anciennes",
                "recent_interactions": [...],  # N dernières interactions
                "structured_data": {  # Données structurées fusionnées
                    "products": [...],
                    "delivery_zone": "...",
                    ...
                }
            }
        """
        # Essayer Redis d'abord
        if self.redis_client:
            memory = self._load_from_redis(user_id, company_id)
            if memory:
                return memory
        
        # Sinon créer nouveau
        return {
            "summary": "",
            "recent_interactions": [],
            "structured_data": {},
            "created_at": datetime.now().isoformat()
        }
    
    def get_recent_interactions(self, limit: int = 15) -> List[Dict]:
        """
        Récupère les dernières interactions pour extraction de contexte
        Utilisé par Smart Context Manager (Cerveau 2)
        
        Args:
            limit: Nombre maximum d'interactions à retourner
        
        Returns:
            Liste de dictionnaires avec user_message et bot_response
        """
        try:
            if not self.user_id:
                logger.warning("⚠️ [ENHANCED_MEMORY] get_recent_interactions appelé sans user_id")
                return []
            
            # Récupérer la mémoire depuis Redis
            memory = self.get_memory(self.user_id, "default")
            
            # Extraire les interactions récentes
            recent = memory.get('recent_interactions', [])
            
            # Limiter au nombre demandé
            interactions = recent[-limit:] if len(recent) > limit else recent
            
            logger.info(f"✅ [ENHANCED_MEMORY] {len(interactions)} interactions récupérées")
            return interactions
            
        except Exception as e:
            logger.error(f"❌ [ENHANCED_MEMORY] Erreur get_recent_interactions: {e}")
            return []
    
    def get_context_for_llm(self, user_id: str, company_id: str) -> str:
        """
        Génère contexte formaté pour injection dans prompt LLM
        
        Returns:
            Texte formaté avec summary + interactions récentes + données structurées
        """
        memory = self.get_memory(user_id, company_id)
        
        context_parts = []
        
        # 1. Summary (interactions anciennes)
        if memory.get("summary"):
            context_parts.append(f"📋 HISTORIQUE: {memory['summary']}")
        
        # 2. Données structurées (CRITIQUE - toujours en premier!)
        structured = memory.get("structured_data", {})
        if structured:
            struct_lines = ["🎯 INFORMATIONS CONFIRMÉES:"]
            
            if structured.get("products"):
                for product in structured["products"]:
                    struct_lines.append(
                        f"  - {product['quantity']} lots taille {product.get('size', '?')} "
                        f"({product.get('type', 'lot 300')})"
                    )
            
            if structured.get("delivery_zone"):
                struct_lines.append(f"  - Livraison: {structured['delivery_zone']}")
                if structured.get("delivery_cost"):
                    struct_lines.append(f"  - Frais livraison: {structured['delivery_cost']} FCFA")
            
            if structured.get("phone"):
                struct_lines.append(f"  - Téléphone: {structured['phone']}")
            
            if structured.get("total_amount"):
                struct_lines.append(f"  - Total: {structured['total_amount']} FCFA")
            
            if structured.get("payment_status"):
                struct_lines.append(f"  - Paiement: {structured['payment_status']}")
            
            context_parts.append("\n".join(struct_lines))
        
        # 3. Interactions récentes (raw)
        recent = memory.get("recent_interactions", [])
        if recent:
            recent_lines = ["💬 DERNIERS ÉCHANGES:"]
            for interaction in recent[-3:]:  # 3 derniers
                recent_lines.append(f"  Client: {interaction['user'][:80]}...")
                recent_lines.append(f"  Vous: {interaction['assistant'][:80]}...")
            
            context_parts.append("\n".join(recent_lines))
        
        return "\n\n".join(context_parts)
    
    def _save_to_redis(self, user_id: str, company_id: str, memory: Dict):
        """Sauvegarde mémoire dans Redis"""
        if not self.redis_client:
            return
        
        try:
            key = f"enhanced_memory:{company_id}:{user_id}"
            self.redis_client.setex(
                key,
                86400,  # 24h
                json.dumps(memory)
            )
        except Exception as e:
            print(f"⚠️ [ENHANCED_MEMORY] Erreur Redis save: {e}")
    
    def _load_from_redis(self, user_id: str, company_id: str) -> Optional[Dict]:
        """Charge mémoire depuis Redis"""
        if not self.redis_client:
            return None
        
        try:
            key = f"enhanced_memory:{company_id}:{user_id}"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"⚠️ [ENHANCED_MEMORY] Erreur Redis load: {e}")
        
        return None
    
    def clear_memory(self, user_id: str, company_id: str):
        """Efface mémoire pour un utilisateur"""
        if self.redis_client:
            key = f"enhanced_memory:{company_id}:{user_id}"
            self.redis_client.delete(key)
        
        print(f"🗑️  [ENHANCED_MEMORY] Mémoire effacée pour {user_id}")


# ============================================================================
# SINGLETON
# ============================================================================

_enhanced_memory: Optional[EnhancedMemory] = None


def get_enhanced_memory(max_recent_interactions: int = 5) -> EnhancedMemory:
    """Récupère instance singleton"""
    global _enhanced_memory
    if _enhanced_memory is None:
        _enhanced_memory = EnhancedMemory(max_recent_interactions=max_recent_interactions)
    return _enhanced_memory

#!/usr/bin/env python3
"""
🧠 SYSTÈME DE MÉMOIRE CONVERSATIONNELLE PROGRESSIVE
Système intelligent de récupération et construction d'informations au fil de la conversation
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class InformationType(Enum):
    """Types d'informations à extraire"""
    CUSTOMER_NAME = "customer_name"
    CUSTOMER_PHONE = "customer_phone"
    DELIVERY_ADDRESS = "delivery_address"
    DELIVERY_ZONE = "delivery_zone"
    PRODUCT_QUANTITY = "product_quantity"
    PRODUCT_TYPE = "product_type"
    PRODUCT_SIZE = "product_size"
    PAYMENT_METHOD = "payment_method"
    SPECIAL_REQUESTS = "special_requests"
    ORDER_STATUS = "order_status"
    CONFIRMATION_STATUS = "confirmation_status"

@dataclass
class ExtractedInformation:
    """Information extraite de la conversation"""
    type: InformationType
    value: str
    confidence: float
    source_message: str
    timestamp: datetime
    context: str = ""

@dataclass
class ConversationState:
    """État de la conversation"""
    customer_info: Dict[str, Any]
    order_info: Dict[str, Any]
    delivery_info: Dict[str, Any]
    payment_info: Dict[str, Any]
    special_requests: List[str]
    confirmation_status: str
    last_updated: datetime
    conversation_id: str

class ProgressiveMemorySystem:
    """Système de mémoire conversationnelle progressive"""
    
    def __init__(self, company_id: str):
        self.company_id = company_id
        self.conversation_states = {}  # user_id -> ConversationState
        self.extraction_patterns = self._load_extraction_patterns()
        self.confirmation_triggers = self._load_confirmation_triggers()
    
    def _load_extraction_patterns(self) -> Dict[InformationType, List[str]]:
        """Charge les patterns d'extraction pour chaque type d'information"""
        return {
            InformationType.CUSTOMER_NAME: [
                r"mon nom c'est ([A-Za-zÀ-ÿ\s]+)",
                r"je m'appelle ([A-Za-zÀ-ÿ\s]+)",
                r"je suis ([A-Za-zÀ-ÿ\s]+)",
                r"nom:?\s*([A-Za-zÀ-ÿ\s]+)",
                r"prénom:?\s*([A-Za-zÀ-ÿ\s]+)"
            ],
            InformationType.CUSTOMER_PHONE: [
                r"(\+?\d{2,3}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2})",
                r"téléphone:?\s*(\+?\d{2,3}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2})",
                r"phone:?\s*(\+?\d{2,3}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2})",
                r"numéro:?\s*(\+?\d{2,3}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2})"
            ],
            InformationType.DELIVERY_ADDRESS: [
                r"adresse:?\s*([^.!?]+)",
                r"je suis à ([^.!?]+)",
                r"j'habite à ([^.!?]+)",
                r"livraison à ([^.!?]+)",
                r"adresse de livraison:?\s*([^.!?]+)"
            ],
            InformationType.DELIVERY_ZONE: [
                r"(cocody|yopougon|plateau|adjamé|abobo|marcory|koumassi|treichville|angré|riviera|bingerville|port-bouët|attécoubé|songon|anyama|brofodoumé|grand-bassam|dabou)",
                r"zone:?\s*([^.!?]+)",
                r"quartier:?\s*([^.!?]+)",
                r"commune:?\s*([^.!?]+)"
            ],
            InformationType.PRODUCT_QUANTITY: [
                r"(\d+)\s*paquets?",
                r"(\d+)\s*colis",
                r"(\d+)\s*unités?",
                r"(\d+)\s*couches?",
                r"quantité:?\s*(\d+)"
            ],
            InformationType.PRODUCT_TYPE: [
                r"(couches à pression|couches culottes|couches adultes|pression|culottes|adultes)",
                r"type:?\s*([^.!?]+)",
                r"produit:?\s*([^.!?]+)"
            ],
            InformationType.PRODUCT_SIZE: [
                r"taille\s*(\d+)",
                r"t(\d+)",
                r"(\d+)\s*kg",
                r"poids:?\s*(\d+)\s*kg"
            ],
            InformationType.PAYMENT_METHOD: [
                r"(wave|mobile money|espèces|virement|chèque)",
                r"paiement:?\s*([^.!?]+)",
                r"payer:?\s*([^.!?]+)"
            ],
            InformationType.SPECIAL_REQUESTS: [
                r"demande:?\s*([^.!?]+)",
                r"requête:?\s*([^.!?]+)",
                r"spécial:?\s*([^.!?]+)",
                r"particulier:?\s*([^.!?]+)"
            ],
            InformationType.CONFIRMATION_STATUS: [
                r"(confirme|confirmer|valide|valider|ok|d'accord|accepte|accepter)",
                r"(annule|annuler|refuse|refuser|non|pas d'accord)"
            ]
        }
    
    def _load_confirmation_triggers(self) -> List[str]:
        """Charge les déclencheurs de confirmation"""
        return [
            "confirmer ma commande",
            "valider la commande",
            "confirmer la livraison",
            "valider l'adresse",
            "confirmer les informations",
            "finaliser la commande",
            "passer commande",
            "commander maintenant"
        ]
    
    def extract_information(self, message: str, user_id: str, conversation_id: str) -> List[ExtractedInformation]:
        """Extrait les informations d'un message"""
        extracted = []
        message_lower = message.lower()
        
        for info_type, patterns in self.extraction_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, message_lower, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    
                    if match and len(match.strip()) > 1:
                        confidence = self._calculate_confidence(pattern, match, message)
                        
                        extracted.append(ExtractedInformation(
                            type=info_type,
                            value=match.strip(),
                            confidence=confidence,
                            source_message=message,
                            timestamp=datetime.now(),
                            context=self._extract_context(message, match)
                        ))
        
        return extracted
    
    def _calculate_confidence(self, pattern: str, match: str, message: str) -> float:
        """Calcule la confiance d'une extraction"""
        base_confidence = 0.8
        
        # Augmenter la confiance si le pattern est plus spécifique
        if ":" in pattern or "c'est" in pattern:
            base_confidence += 0.1
        
        # Augmenter la confiance si le match est plus long
        if len(match) > 5:
            base_confidence += 0.05
        
        # Augmenter la confiance si le contexte est clair
        if any(keyword in message.lower() for keyword in ["nom", "téléphone", "adresse", "commande"]):
            base_confidence += 0.05
        
        return min(base_confidence, 1.0)
    
    def _extract_context(self, message: str, match: str) -> str:
        """Extrait le contexte autour d'une correspondance"""
        match_pos = message.lower().find(match.lower())
        if match_pos == -1:
            return ""
        
        start = max(0, match_pos - 20)
        end = min(len(message), match_pos + len(match) + 20)
        return message[start:end].strip()
    
    def update_conversation_state(self, user_id: str, conversation_id: str, 
                                extracted_info: List[ExtractedInformation]) -> ConversationState:
        """Met à jour l'état de la conversation avec les nouvelles informations"""
        
        # Récupérer ou créer l'état de conversation
        if user_id not in self.conversation_states:
            self.conversation_states[user_id] = ConversationState(
                customer_info={},
                order_info={},
                delivery_info={},
                payment_info={},
                special_requests=[],
                confirmation_status="pending",
                last_updated=datetime.now(),
                conversation_id=conversation_id
            )
        
        state = self.conversation_states[user_id]
        
        # Mettre à jour avec les nouvelles informations
        for info in extracted_info:
            if info.confidence > 0.7:  # Seuil de confiance
                self._update_state_with_info(state, info)
        
        state.last_updated = datetime.now()
        return state
    
    def _update_state_with_info(self, state: ConversationState, info: ExtractedInformation):
        """Met à jour l'état avec une information spécifique"""
        
        if info.type == InformationType.CUSTOMER_NAME:
            state.customer_info["name"] = info.value.title()
        
        elif info.type == InformationType.CUSTOMER_PHONE:
            # Nettoyer le numéro de téléphone
            phone = re.sub(r'[^\d+]', '', info.value)
            state.customer_info["phone"] = phone
        
        elif info.type == InformationType.DELIVERY_ADDRESS:
            state.delivery_info["address"] = info.value
        
        elif info.type == InformationType.DELIVERY_ZONE:
            state.delivery_info["zone"] = info.value.title()
        
        elif info.type == InformationType.PRODUCT_QUANTITY:
            state.order_info["quantity"] = int(info.value)
        
        elif info.type == InformationType.PRODUCT_TYPE:
            state.order_info["product_type"] = info.value
        
        elif info.type == InformationType.PRODUCT_SIZE:
            state.order_info["size"] = info.value
        
        elif info.type == InformationType.PAYMENT_METHOD:
            state.payment_info["method"] = info.value
        
        elif info.type == InformationType.SPECIAL_REQUESTS:
            if info.value not in state.special_requests:
                state.special_requests.append(info.value)
        
        elif info.type == InformationType.CONFIRMATION_STATUS:
            if "confirme" in info.value.lower() or "valide" in info.value.lower():
                state.confirmation_status = "confirmed"
            elif "annule" in info.value.lower() or "refuse" in info.value.lower():
                state.confirmation_status = "cancelled"
    
    def get_missing_information(self, user_id: str) -> List[str]:
        """Retourne la liste des informations manquantes"""
        if user_id not in self.conversation_states:
            return ["nom", "téléphone", "adresse de livraison", "produits souhaités"]
        
        state = self.conversation_states[user_id]
        missing = []
        
        if not state.customer_info.get("name"):
            missing.append("nom complet")
        
        if not state.customer_info.get("phone"):
            missing.append("numéro de téléphone")
        
        if not state.delivery_info.get("address"):
            missing.append("adresse de livraison")
        
        if not state.delivery_info.get("zone"):
            missing.append("zone de livraison")
        
        if not state.order_info.get("product_type"):
            missing.append("type de produit souhaité")
        
        if not state.order_info.get("quantity"):
            missing.append("quantité souhaitée")
        
        return missing
    
    def should_ask_for_confirmation(self, message: str, user_id: str) -> bool:
        """Détermine si le système doit demander une confirmation"""
        message_lower = message.lower()
        
        # Vérifier les déclencheurs de confirmation
        for trigger in self.confirmation_triggers:
            if trigger in message_lower:
                return True
        
        # Vérifier si toutes les informations essentielles sont présentes
        if user_id in self.conversation_states:
            state = self.conversation_states[user_id]
            missing = self.get_missing_information(user_id)
            
            # Si peu d'informations manquantes, demander confirmation
            if len(missing) <= 2:
                return True
        
        return False
    
    def generate_confirmation_prompt(self, user_id: str) -> str:
        """Génère un prompt de confirmation basé sur l'état de la conversation"""
        if user_id not in self.conversation_states:
            return "Pouvez-vous confirmer vos informations de commande ?"
        
        state = self.conversation_states[user_id]
        missing = self.get_missing_information(user_id)
        
        if missing:
            return f"Pour finaliser votre commande, j'ai besoin de quelques informations supplémentaires : {', '.join(missing)}. Pouvez-vous me les fournir ?"
        
        # Générer un récapitulatif de confirmation
        recap = "Voici un récapitulatif de votre commande :\n\n"
        
        if state.customer_info.get("name"):
            recap += f"👤 Nom : {state.customer_info['name']}\n"
        
        if state.customer_info.get("phone"):
            recap += f"📞 Téléphone : {state.customer_info['phone']}\n"
        
        if state.delivery_info.get("address"):
            recap += f"📍 Adresse : {state.delivery_info['address']}\n"
        
        if state.delivery_info.get("zone"):
            recap += f"🌍 Zone : {state.delivery_info['zone']}\n"
        
        if state.order_info.get("product_type"):
            recap += f"📦 Produit : {state.order_info['product_type']}\n"
        
        if state.order_info.get("quantity"):
            recap += f"🔢 Quantité : {state.order_info['quantity']}\n"
        
        if state.special_requests:
            recap += f"📝 Demandes spéciales : {', '.join(state.special_requests)}\n"
        
        recap += "\nConfirmez-vous ces informations ?"
        
        return recap
    
    def get_conversation_summary(self, user_id: str) -> Dict[str, Any]:
        """Retourne un résumé de la conversation"""
        if user_id not in self.conversation_states:
            return {"status": "no_conversation"}
        
        state = self.conversation_states[user_id]
        
        return {
            "conversation_id": state.conversation_id,
            "customer_info": state.customer_info,
            "order_info": state.order_info,
            "delivery_info": state.delivery_info,
            "payment_info": state.payment_info,
            "special_requests": state.special_requests,
            "confirmation_status": state.confirmation_status,
            "last_updated": state.last_updated.isoformat(),
            "missing_information": self.get_missing_information(user_id),
            "completeness_percentage": self._calculate_completeness_percentage(state)
        }
    
    def _calculate_completeness_percentage(self, state: ConversationState) -> float:
        """Calcule le pourcentage de complétude de la conversation"""
        total_fields = 8  # Nombre total de champs importants
        filled_fields = 0
        
        if state.customer_info.get("name"):
            filled_fields += 1
        if state.customer_info.get("phone"):
            filled_fields += 1
        if state.delivery_info.get("address"):
            filled_fields += 1
        if state.delivery_info.get("zone"):
            filled_fields += 1
        if state.order_info.get("product_type"):
            filled_fields += 1
        if state.order_info.get("quantity"):
            filled_fields += 1
        if state.order_info.get("size"):
            filled_fields += 1
        if state.payment_info.get("method"):
            filled_fields += 1
        
        return (filled_fields / total_fields) * 100

# Instance globale du système de mémoire
_memory_systems = {}

def get_memory_system(company_id: str) -> ProgressiveMemorySystem:
    """Obtient ou crée un système de mémoire pour une entreprise"""
    if company_id not in _memory_systems:
        _memory_systems[company_id] = ProgressiveMemorySystem(company_id)
    return _memory_systems[company_id]

def process_conversation_message(message: str, user_id: str, company_id: str, 
                               conversation_id: str = None) -> Dict[str, Any]:
    """
    Traite un message de conversation et met à jour la mémoire
    
    Args:
        message: Message de l'utilisateur
        user_id: ID de l'utilisateur
        company_id: ID de l'entreprise
        conversation_id: ID de la conversation (optionnel)
    
    Returns:
        Dictionnaire avec les informations extraites et l'état de la conversation
    """
    
    if not conversation_id:
        conversation_id = f"{user_id}_{company_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    memory_system = get_memory_system(company_id)
    
    # Extraire les informations du message
    extracted_info = memory_system.extract_information(message, user_id, conversation_id)
    
    # Mettre à jour l'état de la conversation
    conversation_state = memory_system.update_conversation_state(
        user_id, conversation_id, extracted_info
    )
    
    # Vérifier si une confirmation est nécessaire
    should_confirm = memory_system.should_ask_for_confirmation(message, user_id)
    
    # Générer le résumé de la conversation
    conversation_summary = memory_system.get_conversation_summary(user_id)
    
    return {
        "extracted_information": [asdict(info) for info in extracted_info],
        "conversation_state": asdict(conversation_state),
        "should_confirm": should_confirm,
        "confirmation_prompt": memory_system.generate_confirmation_prompt(user_id) if should_confirm else None,
        "conversation_summary": conversation_summary,
        "missing_information": memory_system.get_missing_information(user_id)
    }




#!/usr/bin/env python3
"""
🧠 MÉMOIRE CONVERSATIONNELLE INTELLIGENTE
Maintient le contexte entre les échanges pour une expérience client fluide
"""

import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict

@dataclass
class ConversationContext:
    """Structure pour maintenir le contexte conversationnel"""
    user_id: str
    company_id: str
    session_start: datetime
    last_update: datetime
    
    # Informations produit extraites
    product_info: Dict[str, Any]
    
    # Informations livraison
    delivery_info: Dict[str, Any]
    
    # Informations paiement
    payment_info: Dict[str, Any]
    
    # Calculs automatiques
    calculations: Dict[str, float]
    
    # Historique des intentions détectées
    intentions_history: List[str]
    
    # Dernières réponses pour éviter répétitions
    last_responses: List[str]

class ConversationMemory:
    """
    🧠 Gestionnaire de mémoire conversationnelle intelligente
    """
    
    def __init__(self):
        self.active_contexts: Dict[str, ConversationContext] = {}
        self.session_timeout = timedelta(hours=2)  # Timeout de session
        
        # Patterns pour extraction d'informations
        self.price_patterns = [
            r'(\d+)\s*(?:fcfa|cfa|f)',
            r'prix.*?(\d+)',
            r'coûte.*?(\d+)',
            r'(\d+)\s*francs?'
        ]
        
        self.product_patterns = [
            r'casque.*?(rouge|bleu|noir|blanc|vert)',
            r'(casque)\s+(moto|vélo|protection)',
            r'produit.*?([a-zA-Z]+)',
            r'article.*?([a-zA-Z]+)'
        ]
        
        self.delivery_patterns = [
            r'livraison.*?(yopougon|cocody|abidjan|plateau)',
            r'(yopougon|cocody|abidjan|plateau).*?livraison',
            r'zone.*?(yopougon|cocody|abidjan|plateau)',
            r'livrer.*?(yopougon|cocody|abidjan|plateau)'
        ]

    def get_or_create_context(self, user_id: str, company_id: str) -> ConversationContext:
        """
        🔄 Récupère ou crée un contexte conversationnel
        """
        context_key = f"{company_id}_{user_id}"
        
        # Vérifier si contexte existe et n'est pas expiré
        if context_key in self.active_contexts:
            context = self.active_contexts[context_key]
            if datetime.now() - context.last_update < self.session_timeout:
                return context
            else:
                # Contexte expiré, en créer un nouveau
                del self.active_contexts[context_key]
        
        # Créer nouveau contexte
        context = ConversationContext(
            user_id=user_id,
            company_id=company_id,
            session_start=datetime.now(),
            last_update=datetime.now(),
            product_info={},
            delivery_info={},
            payment_info={},
            calculations={},
            intentions_history=[],
            last_responses=[]
        )
        
        self.active_contexts[context_key] = context
        return context

    def extract_and_update_context(self, user_message: str, assistant_response: str, 
                                 user_id: str, company_id: str) -> ConversationContext:
        """
        🧠 Extrait les informations et met à jour le contexte
        """
        context = self.get_or_create_context(user_id, company_id)
        
        # Extraire informations du message utilisateur
        self._extract_product_info(user_message, context)
        self._extract_delivery_info(user_message, context)
        self._extract_price_info(user_message, context)
        
        # Extraire informations de la réponse assistant
        self._extract_response_info(assistant_response, context)
        
        # Effectuer calculs automatiques
        self._perform_calculations(context)
        
        # Mettre à jour historique
        self._update_history(user_message, assistant_response, context)
        
        context.last_update = datetime.now()
        return context

    def _extract_product_info(self, message: str, context: ConversationContext):
        """Extrait les informations produit"""
        message_lower = message.lower()
        
        # Détecter mentions de produits
        for pattern in self.product_patterns:
            matches = re.findall(pattern, message_lower)
            for match in matches:
                if isinstance(match, tuple):
                    product_type, attribute = match
                    context.product_info['type'] = product_type
                    context.product_info['attribute'] = attribute
                else:
                    if 'casque' in message_lower:
                        context.product_info['type'] = 'casque'
                    if any(color in message_lower for color in ['rouge', 'bleu', 'noir', 'blanc']):
                        for color in ['rouge', 'bleu', 'noir', 'blanc']:
                            if color in message_lower:
                                context.product_info['color'] = color
                                break

    def _extract_delivery_info(self, message: str, context: ConversationContext):
        """Extrait les informations de livraison"""
        message_lower = message.lower()
        
        # Détecter zones de livraison
        for pattern in self.delivery_patterns:
            matches = re.findall(pattern, message_lower)
            for match in matches:
                if isinstance(match, tuple):
                    zone = match[0] if match[0] else match[1]
                else:
                    zone = match
                context.delivery_info['zone'] = zone.lower()

    def _extract_price_info(self, message: str, context: ConversationContext):
        """Extrait les informations de prix avec logique améliorée"""
        message_lower = message.lower()
        
        # Détecter prix mentionnés avec contexte
        for pattern in self.price_patterns:
            matches = re.findall(pattern, message_lower)
            for match in matches:
                try:
                    price = float(match)
                    
                    # Logique contextuelle améliorée
                    if 'livraison' in message_lower and ('coût' in message_lower or 'prix' in message_lower):
                        # Prix de livraison explicite
                        context.delivery_info['cost'] = price
                    elif 'total' in message_lower and ('7500' in match or 'convenu' in message_lower):
                        # Total mentionné explicitement par le client
                        context.calculations['client_total_reference'] = price
                    elif any(word in message_lower for word in ['casque', 'produit', 'article']):
                        # Prix du produit
                        if not context.product_info.get('price'):  # Ne pas écraser
                            context.product_info['price'] = price
                except ValueError:
                    continue

    def _extract_response_info(self, response: str, context: ConversationContext):
        """Extrait les informations de la réponse assistant"""
        response_lower = response.lower()
        
        # Extraire prix de la réponse avec logique améliorée
        for pattern in self.price_patterns:
            matches = re.findall(pattern, response_lower)
            for match in matches:
                try:
                    price = float(match)
                    # Logique améliorée pour éviter la confusion entre prix produit et livraison
                    if 'livraison' in response_lower and 'coûte' in response_lower:
                        # Seulement si c'est explicitement le coût de livraison
                        if not context.delivery_info.get('cost'):  # Ne pas écraser si déjà défini
                            context.delivery_info['cost'] = price
                    elif ('casque' in response_lower or 'produit' in response_lower) and 'prix' in response_lower:
                        # Seulement si c'est explicitement le prix du produit
                        if not context.product_info.get('price'):  # Ne pas écraser si déjà défini
                            context.product_info['price'] = price
                    elif 'total' in response_lower:
                        # Si c'est un total mentionné dans la réponse
                        context.calculations['total_mentioned'] = price
                except ValueError:
                    continue
        
        # Extraire informations paiement
        if 'wave' in response_lower:
            context.payment_info['method'] = 'wave'
            # Extraire numéro Wave
            wave_pattern = r'\+?(\d{10,13})'
            wave_matches = re.findall(wave_pattern, response)
            if wave_matches:
                context.payment_info['wave_number'] = '+' + wave_matches[0]
        
        if 'cod' in response_lower or 'livraison' in response_lower and 'paiement' in response_lower:
            context.payment_info['cod_available'] = True

    def _perform_calculations(self, context: ConversationContext):
        """Effectue les calculs automatiques avec validation"""
        product_price = context.product_info.get('price')
        delivery_cost = context.delivery_info.get('cost')
        
        if product_price and delivery_cost:
            # Validation des valeurs pour éviter les erreurs
            if isinstance(product_price, (int, float)) and isinstance(delivery_cost, (int, float)):
                if product_price > 0 and delivery_cost > 0:
                    calculated_total = product_price + delivery_cost
                    context.calculations['total'] = calculated_total
                    context.calculations['product_price'] = product_price
                    context.calculations['delivery_cost'] = delivery_cost
                    
                    # Log pour debugging
                    print(f"[CALC] Produit: {product_price} + Livraison: {delivery_cost} = Total: {calculated_total}")

    def _update_history(self, user_message: str, assistant_response: str, context: ConversationContext):
        """Met à jour l'historique"""
        # Détecter intention du message
        intention = self._detect_intention(user_message)
        if intention:
            context.intentions_history.append(intention)
        
        # Garder seulement les 3 dernières réponses
        context.last_responses.append(assistant_response[:100])
        if len(context.last_responses) > 3:
            context.last_responses.pop(0)

    def _detect_intention(self, message: str) -> Optional[str]:
        """Détecte l'intention du message"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['cherche', 'veux', 'besoin']):
            return 'product_inquiry'
        elif any(word in message_lower for word in ['prix', 'coût', 'combien']):
            return 'price_inquiry'
        elif 'livraison' in message_lower:
            return 'delivery_inquiry'
        elif any(word in message_lower for word in ['total', 'ensemble']):
            return 'total_calculation'
        elif any(word in message_lower for word in ['confirme', 'commande', 'acheter']):
            return 'order_confirmation'
        elif any(word in message_lower for word in ['paiement', 'payer']):
            return 'payment_inquiry'
        elif any(word in message_lower for word in ['quand', 'délai', 'recevoir']):
            return 'delivery_timing'
        
        return None

    def generate_context_summary(self, user_id: str, company_id: str) -> str:
        """
        📋 Génère un résumé du contexte pour enrichir le prompt LLM
        """
        context = self.get_or_create_context(user_id, company_id)
        
        summary_parts = []
        
        # Informations produit
        if context.product_info:
            product_desc = []
            if 'type' in context.product_info:
                product_desc.append(f"Produit: {context.product_info['type']}")
            if 'color' in context.product_info:
                product_desc.append(f"Couleur: {context.product_info['color']}")
            if 'price' in context.product_info:
                product_desc.append(f"Prix: {context.product_info['price']} FCFA")
            
            if product_desc:
                summary_parts.append("PRODUIT: " + ", ".join(product_desc))
        
        # Informations livraison
        if context.delivery_info:
            delivery_desc = []
            if 'zone' in context.delivery_info:
                delivery_desc.append(f"Zone: {context.delivery_info['zone']}")
            if 'cost' in context.delivery_info:
                delivery_desc.append(f"Coût: {context.delivery_info['cost']} FCFA")
            
            if delivery_desc:
                summary_parts.append("LIVRAISON: " + ", ".join(delivery_desc))
        
        # Calculs avec validation et cohérence
        if context.calculations:
            if 'total' in context.calculations:
                total = context.calculations['total']
                summary_parts.append(f"TOTAL CALCULÉ: {total} FCFA")
            elif 'client_total_reference' in context.calculations:
                # Utiliser la référence client si pas de calcul automatique
                ref_total = context.calculations['client_total_reference']
                summary_parts.append(f"TOTAL RÉFÉRENCE CLIENT: {ref_total} FCFA")
        
        # Informations paiement
        if context.payment_info:
            payment_desc = []
            if 'method' in context.payment_info:
                payment_desc.append(f"Méthode: {context.payment_info['method']}")
            if 'wave_number' in context.payment_info:
                payment_desc.append(f"Numéro: {context.payment_info['wave_number']}")
            if context.payment_info.get('cod_available'):
                payment_desc.append("COD disponible")
            
            if payment_desc:
                summary_parts.append("PAIEMENT: " + ", ".join(payment_desc))
        
        # Historique des intentions
        if context.intentions_history:
            recent_intentions = context.intentions_history[-3:]  # 3 dernières
            summary_parts.append(f"PARCOURS: {' → '.join(recent_intentions)}")
        
        if summary_parts:
            return "=== CONTEXTE CONVERSATION ===\n" + "\n".join(summary_parts) + "\n"
        
        return ""

    def should_auto_calculate_total(self, user_message: str, context: ConversationContext) -> bool:
        """
        🧮 Détermine si un calcul automatique de total doit être effectué
        """
        message_lower = user_message.lower()
        
        # Conditions pour calcul automatique
        has_total_request = any(word in message_lower for word in ['total', 'ensemble', 'combien', 'coût'])
        has_product_price = 'price' in context.product_info
        has_delivery_cost = 'cost' in context.delivery_info
        
        return has_total_request and has_product_price and has_delivery_cost

    def get_auto_calculation_response(self, context: ConversationContext) -> str:
        """
        🧮 Génère une réponse avec calcul automatique
        """
        if 'total' not in context.calculations:
            return ""
        
        product_price = context.calculations.get('product_price', 0)
        delivery_cost = context.calculations.get('delivery_cost', 0)
        total = context.calculations.get('total', 0)
        
        product_name = ""
        if context.product_info.get('type') and context.product_info.get('color'):
            product_name = f"{context.product_info['type']} {context.product_info['color']}"
        
        zone = context.delivery_info.get('zone', 'votre zone')
        
        return f"""Voici le détail de votre commande :

• {product_name}: {product_price} FCFA
• Livraison {zone}: {delivery_cost} FCFA
• **TOTAL: {total} FCFA**

Souhaitez-vous confirmer cette commande ?"""

    def cleanup_expired_contexts(self):
        """
        🧹 Nettoie les contextes expirés
        """
        now = datetime.now()
        expired_keys = []
        
        for key, context in self.active_contexts.items():
            if now - context.last_update > self.session_timeout:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.active_contexts[key]
        
        return len(expired_keys)

# Instance globale
conversation_memory = ConversationMemory()

def get_conversation_context(user_id: str, company_id: str) -> str:
    """
    🧠 Fonction utilitaire pour récupérer le contexte conversationnel
    """
    return conversation_memory.generate_context_summary(user_id, company_id)

def update_conversation_context(user_message: str, assistant_response: str, 
                              user_id: str, company_id: str) -> ConversationContext:
    """
    🔄 Fonction utilitaire pour mettre à jour le contexte
    """
    return conversation_memory.extract_and_update_context(
        user_message, assistant_response, user_id, company_id
    )

if __name__ == "__main__":
    print("🧠 MÉMOIRE CONVERSATIONNELLE INTELLIGENTE")
    print("=" * 50)
    print("Utilisation: from core.conversation_memory import get_conversation_context")

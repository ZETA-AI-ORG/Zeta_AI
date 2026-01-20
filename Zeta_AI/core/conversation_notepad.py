#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🗒️ SYSTÈME DE NOTEPAD CONVERSATIONNEL
Stocke et track toutes les informations de commande en mémoire
Résout le problème de perte de contexte entre messages
"""

from typing import Dict, Any, Optional, List
import json
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


class ConversationNotepad:
    """
    Notepad persistant pour chaque conversation utilisateur
    Stocke: produits, quantités, zones, prix, calculs
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Retourne l'instance singleton"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.notepads: Dict[str, Dict[str, Any]] = {}
        logger.info("📋 ConversationNotepad initialisé")
    
    def get_notepad(self, user_id: str, company_id: str) -> Dict[str, Any]:
        """Récupère ou crée un notepad pour une conversation"""
        key = f"{company_id}_{user_id}"
        
        if key not in self.notepads:
            self.notepads[key] = {
                "created_at": datetime.now().isoformat(),
                "products": [],  # Liste des produits demandés
                "quantities": {},  # {product_id: quantity}
                "delivery_zone": None,
                "delivery_cost": None,
                "payment_method": None,
                "payment_number": None,
                "phone_number": None,
                "calculated_totals": [],  # Historique des calculs
                "last_updated": datetime.now().isoformat(),
                "conversation_count": 0
            }
            logger.info(f"📝 Nouveau notepad créé: {key}")
        
        return self.notepads[key]
    
    def update_product(self, user_id: str, company_id: str, 
                      product_name: str, quantity: int, price: float,
                      variant: Optional[str] = None):
        """Ajoute/met à jour un produit dans le notepad"""
        notepad = self.get_notepad(user_id, company_id)
        
        # Créer identifiant unique produit
        product_id = f"{product_name}_{variant}" if variant else product_name
        
        # Chercher si produit existe déjà
        existing = next((p for p in notepad["products"] 
                        if p["id"] == product_id), None)
        
        if existing:
            # Mettre à jour
            existing["quantity"] = quantity
            existing["price"] = price
            existing["updated_at"] = datetime.now().isoformat()
            logger.info(f"🔄 Produit mis à jour: {product_id} x{quantity}")
        else:
            # Ajouter nouveau
            notepad["products"].append({
                "id": product_id,
                "name": product_name,
                "variant": variant,
                "quantity": quantity,
                "price": price,
                "added_at": datetime.now().isoformat()
            })
            logger.info(f"➕ Nouveau produit ajouté: {product_id} x{quantity}")
        
        notepad["last_updated"] = datetime.now().isoformat()
        notepad["conversation_count"] += 1
    
    def update_delivery(self, user_id: str, company_id: str, 
                       zone: str, cost: float):
        """Met à jour les infos de livraison"""
        notepad = self.get_notepad(user_id, company_id)
        
        old_zone = notepad.get("delivery_zone")
        notepad["delivery_zone"] = zone
        notepad["delivery_cost"] = cost
        notepad["last_updated"] = datetime.now().isoformat()
        notepad["conversation_count"] += 1
        
        if old_zone and old_zone != zone:
            logger.info(f"🚚 Zone changée: {old_zone} → {zone} ({cost} FCFA)")
        else:
            logger.info(f"🚚 Livraison définie: {zone} ({cost} FCFA)")
    
    def get_all(self, user_id: str, company_id: str) -> Dict[str, Any]:
        """Récupère toutes les données du notepad sous forme de dict simple"""
        notepad = self.get_notepad(user_id, company_id)
        
        result = {}
        
        # Produit (prendre le dernier)
        if notepad["products"]:
            last_product = notepad["products"][-1]
            product_str = last_product["name"]
            if last_product.get("variant"):
                product_str += f" {last_product['variant']}"
            result["produit"] = product_str
            result["prix_produit"] = str(int(last_product["price"]))
        
        # Zone
        if notepad.get("delivery_zone"):
            result["zone"] = notepad["delivery_zone"]
        if notepad.get("delivery_cost"):
            result["frais_livraison"] = str(int(notepad["delivery_cost"]))
        
        # Téléphone
        if notepad.get("phone_number"):
            result["telephone"] = notepad["phone_number"]
        
        # Paiement
        if notepad.get("payment_method"):
            result["paiement"] = notepad["payment_method"]
        
        return result
    
    def update_payment(self, user_id: str, company_id: str,
                      method: str, number: Optional[str] = None):
        """Met à jour les infos de paiement"""
        notepad = self.get_notepad(user_id, company_id)
        notepad["payment_method"] = method
        if number:
            notepad["payment_number"] = number
        notepad["last_updated"] = datetime.now().isoformat()
        logger.info(f"💳 Paiement: {method}")
    
    def update_phone(self, user_id: str, company_id: str, phone: str):
        """Met à jour le numéro de téléphone"""
        notepad = self.get_notepad(user_id, company_id)
        notepad["phone_number"] = phone
        notepad["last_updated"] = datetime.now().isoformat()
        logger.info(f"📞 Téléphone: {phone}")
    
    def calculate_total(self, user_id: str, company_id: str) -> Dict[str, Any]:
        """Calcule le total de la commande"""
        notepad = self.get_notepad(user_id, company_id)
        
        # Calcul produits
        products_total = sum(
            p["quantity"] * p["price"] 
            for p in notepad["products"]
        )
        
        # Ajout livraison
        delivery_cost = notepad.get("delivery_cost", 0) or 0
        grand_total = products_total + delivery_cost
        
        # Compter total items
        total_items = sum(p["quantity"] for p in notepad["products"])
        products_count = len(notepad["products"])
        
        # Enregistrer le calcul
        calculation = {
            "products_total": products_total,
            "delivery_cost": delivery_cost,
            "grand_total": grand_total,
            "calculated_at": datetime.now().isoformat(),
            "products_count": products_count,
            "total_items": total_items
        }
        
        notepad["calculated_totals"].append(calculation)
        notepad["last_updated"] = datetime.now().isoformat()
        
        logger.info(f"💰 Total calculé: {grand_total:,.0f} FCFA "
                   f"({products_count} produits, {total_items} items)")
        
        return calculation
    
    def has_info(self, user_id: str, company_id: str, field: str) -> bool:
        """
        ✅ AMÉLIORATION 8: Vérifie si une info existe déjà
        Évite de redemander des infos déjà collectées
        """
        notepad = self.get_notepad(user_id, company_id)
        
        field_mapping = {
            "produit": lambda n: len(n["products"]) > 0,
            "zone": lambda n: bool(n.get("delivery_zone")),
            "telephone": lambda n: bool(n.get("phone_number")),
            "paiement": lambda n: bool(n.get("payment_method")),
            "adresse": lambda n: bool(n.get("delivery_address"))
        }
        
        checker = field_mapping.get(field.lower())
        return checker(notepad) if checker else False
    
    def get_missing_fields(self, user_id: str, company_id: str) -> List[str]:
        """
        ✅ AMÉLIORATION 8: Retourne la liste des champs manquants
        Pour progression intelligente de la conversation
        """
        missing = []
        
        if not self.has_info(user_id, company_id, "produit"):
            missing.append("produit")
        if not self.has_info(user_id, company_id, "zone"):
            missing.append("zone")
        if not self.has_info(user_id, company_id, "telephone"):
            missing.append("telephone")
        if not self.has_info(user_id, company_id, "paiement"):
            missing.append("paiement")
        
        return missing
    
    def get_summary(self, user_id: str, company_id: str) -> str:
        """Génère un résumé textuel du notepad"""
        notepad = self.get_notepad(user_id, company_id)
        
        if not notepad["products"] and not notepad["delivery_zone"]:
            return "📋 Aucune commande en cours"
        
        summary_parts = ["📋 RÉCAPITULATIF COMMANDE:"]
        
        # Produits
        if notepad["products"]:
            summary_parts.append("\n🛒 PRODUITS:")
            for p in notepad["products"]:
                variant_text = f" ({p['variant']})" if p.get('variant') else ""
                summary_parts.append(
                    f"  - {p['quantity']}x {p['name']}{variant_text} "
                    f"à {p['price']:,.0f} FCFA/unité"
                )
            
            # Sous-total produits
            products_total = sum(p['quantity'] * p['price'] for p in notepad["products"])
            summary_parts.append(f"  💵 Sous-total: {products_total:,.0f} FCFA")
        
        # Livraison
        if notepad["delivery_zone"]:
            delivery_cost_formatted = f"{notepad['delivery_cost']:,.0f}".replace(',', ' ')
            summary_parts.append(
                f"\n🚚 LIVRAISON: {notepad['delivery_zone']} "
                f"({delivery_cost_formatted} FCFA)"
            )
        
        # Paiement
        if notepad["payment_method"]:
            payment_text = f"\n💳 PAIEMENT: {notepad['payment_method']}"
            if notepad.get("payment_number"):
                payment_text += f" ({notepad['payment_number']})"
            summary_parts.append(payment_text)
        
        # Contact
        if notepad["phone_number"]:
            summary_parts.append(f"\n📞 CONTACT: {notepad['phone_number']}")
        
        # Total final
        if notepad["calculated_totals"]:
            last_calc = notepad["calculated_totals"][-1]
            summary_parts.append(
                f"\n💰 TOTAL FINAL: {last_calc['grand_total']:,.0f} FCFA"
            )
        elif notepad["products"]:
            # Calculer si pas encore fait
            calc = self.calculate_total(user_id, company_id)
            summary_parts.append(
                f"\n💰 TOTAL FINAL: {calc['grand_total']:,.0f} FCFA"
            )
        
        return "\n".join(summary_parts)
    
    def get_context_for_llm(self, user_id: str, company_id: str) -> str:
        """
        Génère un contexte formaté pour le LLM
        À injecter dans le prompt système
        """
        notepad = self.get_notepad(user_id, company_id)
        
        if not notepad["products"] and not notepad["delivery_zone"]:
            return ""
        
        context_parts = ["[INFORMATIONS COMMANDE EN COURS]"]
        
        # Produits
        if notepad["products"]:
            context_parts.append("Produits commandés:")
            for p in notepad["products"]:
                variant_text = f" {p['variant']}" if p.get('variant') else ""
                context_parts.append(
                    f"- {p['quantity']}x {p['name']}{variant_text} "
                    f"({p['price']:,.0f} FCFA/unité)"
                )
        
        # Livraison
        if notepad["delivery_zone"]:
            delivery_cost_formatted = f"{notepad['delivery_cost']:,.0f}".replace(',', ' ')
            context_parts.append(
                f"Zone de livraison: {notepad['delivery_zone']} "
                f"({delivery_cost_formatted} FCFA)"
            )
        
        # Paiement
        if notepad["payment_method"]:
            context_parts.append(f"Méthode de paiement: {notepad['payment_method']}")
        
        # Contact
        if notepad["phone_number"]:
            context_parts.append(f"Numéro client: {notepad['phone_number']}")
        
        context_parts.append("[FIN INFORMATIONS COMMANDE]")
        
        return "\n".join(context_parts)
    
    def has_active_order(self, user_id: str, company_id: str) -> bool:
        """Vérifie si une commande est en cours"""
        notepad = self.get_notepad(user_id, company_id)
        return len(notepad["products"]) > 0
    
    def clear_notepad(self, user_id: str, company_id: str):
        """Efface le notepad (après commande validée)"""
        key = f"{company_id}_{user_id}"
        if key in self.notepads:
            del self.notepads[key]
            logger.info(f"🗑️ Notepad effacé: {key}")
    
    def add_info(self, user_id: str, company_id: str, key: str, value: str) -> str:
        """
        ✅ AMÉLIORATION V2: Méthode générique avec système de clés dynamiques
        Utilisée par l'outil Bloc-note: ajouter info du LLM
        
        Support des balises universelles: PREFIX-clé (ex: PROD-lot, DELIV-zone)
        Extraction automatique des clés métier depuis Supabase

        Args:
            user_id: ID utilisateur
            company_id: ID entreprise
            key: Clé de l'information (ex: "lot", "PROD-lot_150", "taille")
            value: Valeur à stocker

        Returns:
            str: Message de confirmation
        """
        try:
            from core.dynamic_notepad_keys import parse_key_value
            
            # Parser la clé avec le système dynamique
            parsed = parse_key_value(key, value, company_id)
            prefix = parsed["prefix"]
            normalized_key = parsed["normalized_key"]
            metadata = parsed["metadata"]
            
            logger.info(f"[NOTEPAD] Clé parsée: {key} → {prefix}-{normalized_key}")
            
            # Traitement par préfixe universel
            if prefix == "PROD":
                # Format: "nom_produit|variante" ou juste "nom_produit"
                if "|" in value:
                    product_name, variant = value.split("|", 1)
                    product_name = product_name.strip()
                    variant = variant.strip()
                else:
                    product_name = value.strip()
                    variant = None

                # Extraire quantité si présente
                quantity = 1
                if " x" in product_name:
                    parts = product_name.split(" x", 1)
                    if len(parts) == 2:
                        try:
                            quantity = int(parts[0].strip())
                            product_name = parts[1].strip()
                        except:
                            pass

                self.update_product(user_id, company_id, product_name, quantity, 0.0, variant)
                return f"✅ Produit ajouté: {product_name} x{quantity}"

            elif prefix == "DELIV":
                # Format: "Zone coût" ou juste "Zone"
                cost_match = re.search(r'(\d+)', value)
                cost = float(cost_match.group(1)) if cost_match else 1500.0

                zone = re.sub(r'\d+', '', value).strip()
                self.update_delivery(user_id, company_id, zone, cost)
                return f"✅ Livraison ajoutée: {zone} ({cost} FCFA)"

            elif prefix == "CONTACT":
                self.update_phone(user_id, company_id, value.strip())
                return f"✅ Téléphone ajouté: {value.strip()}"

            elif prefix == "PAYMENT":
                # Format: "méthode|numéro" ou juste "méthode"
                if "|" in value:
                    method, number = value.split("|", 1)
                    method = method.strip()
                    number = number.strip()
                else:
                    method = value.strip()
                    number = None

                self.update_payment(user_id, company_id, method, number)
                return f"✅ Paiement ajouté: {method}"

            elif prefix == "PRICE":
                # Prix doit être associé au dernier produit ajouté
                notepad = self.get_notepad(user_id, company_id)
                if notepad["products"]:
                    try:
                        price = float(re.sub(r'[^\d.]', '', value))
                        last_product = notepad["products"][-1]
                        last_product["price"] = price
                        notepad["last_updated"] = datetime.now().isoformat()
                        return f"✅ Prix mis à jour: {price} FCFA"
                    except:
                        return f"⚠️ Prix invalide: {value}"
                else:
                    return f"⚠️ Aucun produit pour associer le prix"

            elif prefix == "CUSTOM":
                # Attributs personnalisés (quantité, taille, couleur, etc.)
                notepad = self.get_notepad(user_id, company_id)
                
                # Associer au dernier produit si disponible
                if notepad["products"]:
                    last_product = notepad["products"][-1]
                    
                    # Stocker dans un dict custom_attributes
                    if "custom_attributes" not in last_product:
                        last_product["custom_attributes"] = {}
                    
                    last_product["custom_attributes"][normalized_key] = value.strip()
                    notepad["last_updated"] = datetime.now().isoformat()
                    
                    logger.info(f"✅ Attribut custom ajouté: {normalized_key}={value}")
                    return f"✅ {normalized_key.capitalize()} mise à jour: {value}"
                else:
                    # Stocker dans le notepad global si pas de produit
                    if "custom_data" not in notepad:
                        notepad["custom_data"] = {}
                    
                    notepad["custom_data"][normalized_key] = value.strip()
                    notepad["last_updated"] = datetime.now().isoformat()
                    
                    return f"✅ Info ajoutée: {normalized_key}={value}"

            else:
                # Fallback: stocker comme custom
                logger.warning(f"⚠️ Préfixe inconnu '{prefix}' pour clé '{key}' → CUSTOM")
                return self.add_info(user_id, company_id, f"CUSTOM-{key}", value)

        except Exception as e:
            logger.error(f"❌ Erreur add_info {key}={value}: {e}")
            return f"❌ Erreur ajout {key}={value}"


# ============================================================================
# EXTRACTEURS AUTOMATIQUES
# ============================================================================

def extract_product_info(text: str) -> Optional[Dict[str, Any]]:
    """
    Extrait automatiquement les infos produit d'un message
    Ex: "2 lots de 300 couches taille 4"
    """
    # Pattern: quantité + produit + variante
    patterns = [
        # "2 lots de 300 couches taille 4"
        r'(\d+)\s*(?:lots?|paquets?)\s+(?:de\s+)?(\d+)?\s*couches?\s+(?:taille\s+)?(\d+)',
        # "3 paquets couches culottes"
        r'(\d+)\s*(?:lots?|paquets?)\s+couches?\s+culottes?',
        # "1 lot taille 5"
        r'(\d+)\s*(?:lots?|paquets?)\s+(?:taille\s+)?(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            groups = match.groups()
            quantity = int(groups[0])
            
            # Déterminer le type et la variante
            if "culottes" in text.lower():
                product_type = "Couches culottes"
                variant = None
            else:
                product_type = "Couches à pression"
                variant = f"Taille {groups[-1]}" if len(groups) > 1 and groups[-1] else None
            
            return {
                "quantity": quantity,
                "product_type": product_type,
                "variant": variant
            }
    
    return None


def extract_delivery_zone(text: str) -> Optional[str]:
    """
    Extrait la zone de livraison d'un message
    Ex: "livraison à Cocody", "Yopougon"
    """
    zones = [
        "cocody", "yopougon", "plateau", "adjamé", "abobo", 
        "marcory", "koumassi", "treichville", "angré", "riviera",
        "port-bouët", "port-bouet", "attécoubé", "bingerville",
        "songon", "anyama", "brofodoumé", "grand-bassam", "dabou"
    ]
    
    text_lower = text.lower()
    
    for zone in zones:
        if zone in text_lower:
            # Normaliser le nom
            return zone.replace("-", " ").title()
    
    return None


def extract_phone_number(text: str) -> Optional[str]:
    """
    Extrait un numéro de téléphone
    Ex: "0787360757", "+225 0787360757"
    """
    patterns = [
        r'\+?225\s*(\d{10})',
        r'(\d{10})',
        r'(\d{2}\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{2})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    return None


def extract_price_from_response(text: str) -> Optional[float]:
    """
    Extrait un prix de la réponse du LLM
    Ex: "24 000 FCFA", "24000 F CFA"
    """
    patterns = [
        r'(\d+[\s\u202f]?\d{3})\s*(?:FCFA|F\s*CFA|F)',
        r'(\d+)\s*(?:FCFA|F\s*CFA|F)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            price_str = match.group(1).replace('\u202f', '').replace(' ', '')
            try:
                return float(price_str)
            except:
                continue
    
    return None


# ============================================================================
# SINGLETON GLOBAL
# ============================================================================

_notepad_instance: Optional[ConversationNotepad] = None


def get_conversation_notepad() -> ConversationNotepad:
    """Récupère l'instance singleton du notepad"""
    global _notepad_instance
    if _notepad_instance is None:
        _notepad_instance = ConversationNotepad()
        logger.info("📋 Singleton ConversationNotepad créé")
    return _notepad_instance


def reset_conversation_notepad():
    """Reset le singleton (pour tests)"""
    global _notepad_instance
    _notepad_instance = None
    logger.info("🔄 Singleton ConversationNotepad reset")

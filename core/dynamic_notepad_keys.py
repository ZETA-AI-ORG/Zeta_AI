#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 SYSTÈME DE CLÉS DYNAMIQUES POUR NOTEPAD
Permet d'extraire automatiquement les clés métier depuis Supabase
et de gérer des balises universelles (PREFIX-clé)

AVANTAGES:
1. Plus besoin de hardcoder les clés par entreprise
2. Support automatique des attributs custom
3. Balises universelles pour extraction dynamique
4. Compatible avec tous les secteurs (e-commerce, services, etc.)
"""

import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================================
# BALISES UNIVERSELLES (CORE)
# ============================================================================

UNIVERSAL_PREFIXES = {
    "PROD": "product",      # Produit (lot, taille, couleur, etc.)
    "DELIV": "delivery",    # Livraison (zone, commune, frais)
    "CONTACT": "contact",   # Contact (téléphone, email, whatsapp)
    "PRICE": "price",       # Prix (unitaire, gros, remise)
    "PAYMENT": "payment",   # Paiement (méthode, numéro, statut)
    "CUSTOM": "custom"      # Attributs personnalisés
}

# ============================================================================
# MAPPING PAR DÉFAUT (FALLBACK)
# ============================================================================

DEFAULT_KEY_MAPPING = {
    # Produit
    "produit": "PROD",
    "product": "PROD",
    "lot": "PROD",
    "article": "PROD",
    "item": "PROD",
    
    # Livraison
    "zone": "DELIV",
    "delivery_zone": "DELIV",
    "livraison": "DELIV",
    "commune": "DELIV",
    "quartier": "DELIV",
    "adresse": "DELIV",
    
    # Contact
    "telephone": "CONTACT",
    "phone": "CONTACT",
    "numero": "CONTACT",
    "contact": "CONTACT",
    "whatsapp": "CONTACT",
    "email": "CONTACT",
    
    # Prix
    "prix": "PRICE",
    "price": "PRICE",
    "prix_produit": "PRICE",
    "prix_total": "PRICE",
    "montant": "PRICE",
    "tarif": "PRICE",
    
    # Paiement
    "paiement": "PAYMENT",
    "payment": "PAYMENT",
    "methode": "PAYMENT",
    "mode_paiement": "PAYMENT",
    
    # Custom (attributs spécifiques)
    "quantite": "CUSTOM",
    "quantité": "CUSTOM",
    "quantity": "CUSTOM",
    "qte": "CUSTOM",
    "taille": "CUSTOM",
    "size": "CUSTOM",
    "couleur": "CUSTOM",
    "color": "CUSTOM",
    "marque": "CUSTOM",
    "brand": "CUSTOM",
    "stock": "CUSTOM",
    "delai": "CUSTOM",
    "variante": "CUSTOM",
    "variant": "CUSTOM"
}

# ============================================================================
# CLASSE PRINCIPALE
# ============================================================================

class DynamicNotepadKeys:
    """
    Gère les clés dynamiques du notepad avec support des balises universelles
    """
    
    def __init__(self):
        self.company_mappings: Dict[str, Dict[str, str]] = {}
        self.loaded_companies: set = set()
        logger.info("🔧 DynamicNotepadKeys initialisé")
    
    async def load_company_keys(self, company_id: str) -> Dict[str, List[str]]:
        """
        Charge les clés métier d'une entreprise depuis Supabase
        
        Args:
            company_id: ID de l'entreprise
            
        Returns:
            Dict avec les clés par catégorie
        """
        if company_id in self.loaded_companies:
            return self.company_mappings.get(company_id, {})
        
        try:
            from database.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            
            # Récupérer les custom_fields de l'entreprise
            response = supabase.table("companies").select("custom_fields").eq("id", company_id).single().execute()
            
            if response.data and response.data.get("custom_fields"):
                custom_fields = response.data["custom_fields"]
                
                # Construire le mapping
                mapping = {}
                for prefix, fields in custom_fields.items():
                    if prefix in UNIVERSAL_PREFIXES:
                        for field in fields:
                            mapping[field.lower()] = prefix
                
                self.company_mappings[company_id] = mapping
                self.loaded_companies.add(company_id)
                
                logger.info(f"✅ Clés chargées pour {company_id}: {len(mapping)} clés")
                return custom_fields
            
        except Exception as e:
            logger.warning(f"⚠️ Impossible de charger les clés pour {company_id}: {e}")
        
        # Fallback: utiliser le mapping par défaut
        self.company_mappings[company_id] = DEFAULT_KEY_MAPPING
        self.loaded_companies.add(company_id)
        return {}
    
    def normalize_key(self, key: str, company_id: str) -> tuple[str, str]:
        """
        Normalise une clé en détectant son préfixe universel
        
        Args:
            key: Clé brute (ex: "lot", "PROD-lot_150", "taille")
            company_id: ID de l'entreprise
            
        Returns:
            (prefix, normalized_key)
            Ex: ("PROD", "lot"), ("CUSTOM", "taille")
        """
        key_lower = key.lower().strip()
        
        # 1. Détecter balise explicite (PREFIX-clé)
        if "-" in key_lower:
            parts = key_lower.split("-", 1)
            prefix = parts[0].upper()
            if prefix in UNIVERSAL_PREFIXES:
                return (prefix, parts[1])
        
        # 2. Utiliser le mapping de l'entreprise
        if company_id in self.company_mappings:
            mapping = self.company_mappings[company_id]
            if key_lower in mapping:
                return (mapping[key_lower], key_lower)
        
        # 3. Fallback: mapping par défaut
        if key_lower in DEFAULT_KEY_MAPPING:
            return (DEFAULT_KEY_MAPPING[key_lower], key_lower)
        
        # 4. Inconnu → CUSTOM
        logger.warning(f"⚠️ Clé inconnue '{key}' → CUSTOM")
        return ("CUSTOM", key_lower)
    
    def get_handler_method(self, prefix: str) -> str:
        """
        Retourne le nom de la méthode de traitement selon le préfixe
        
        Args:
            prefix: Préfixe universel (PROD, DELIV, etc.)
            
        Returns:
            Nom de la méthode (ex: "update_product")
        """
        handlers = {
            "PROD": "update_product",
            "DELIV": "update_delivery",
            "CONTACT": "update_phone",
            "PRICE": "update_price",
            "PAYMENT": "update_payment",
            "CUSTOM": "update_custom"
        }
        return handlers.get(prefix, "update_custom")
    
    def extract_value_metadata(self, value: str, prefix: str) -> Dict[str, Any]:
        """
        Extrait les métadonnées d'une valeur selon son type
        
        Args:
            value: Valeur brute (ex: "lot 150", "Cocody 1500", "+225 0787360757")
            prefix: Préfixe universel
            
        Returns:
            Dict avec valeur normalisée et métadonnées
        """
        metadata = {
            "raw_value": value,
            "normalized_value": value.strip(),
            "extracted_numbers": [],
            "extracted_text": value.strip()
        }
        
        # Extraire les nombres
        numbers = re.findall(r'\d+', value)
        if numbers:
            metadata["extracted_numbers"] = [int(n) for n in numbers]
        
        # Extraire le texte (sans nombres)
        text = re.sub(r'\d+', '', value).strip()
        metadata["extracted_text"] = text
        
        # Traitement spécifique par type
        if prefix == "PROD":
            # Détecter lot/quantité
            if "lot" in value.lower():
                metadata["type"] = "lot"
                if metadata["extracted_numbers"]:
                    metadata["quantity"] = metadata["extracted_numbers"][0]
        
        elif prefix == "DELIV":
            # Détecter zone + coût
            if metadata["extracted_numbers"]:
                metadata["zone"] = text
                metadata["cost"] = metadata["extracted_numbers"][-1]  # Dernier nombre = coût
        
        elif prefix == "PRICE":
            # Extraire montant
            if metadata["extracted_numbers"]:
                metadata["amount"] = metadata["extracted_numbers"][0]
        
        elif prefix == "CONTACT":
            # Détecter type de contact
            if re.match(r'[\d\s\+\-\(\)]+$', value):
                metadata["type"] = "phone"
            elif "@" in value:
                metadata["type"] = "email"
        
        return metadata

# ============================================================================
# INSTANCE GLOBALE
# ============================================================================

_dynamic_keys_instance = None

def get_dynamic_keys() -> DynamicNotepadKeys:
    """Retourne l'instance singleton de DynamicNotepadKeys"""
    global _dynamic_keys_instance
    if _dynamic_keys_instance is None:
        _dynamic_keys_instance = DynamicNotepadKeys()
    return _dynamic_keys_instance

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def parse_key_value(key: str, value: str, company_id: str) -> Dict[str, Any]:
    """
    Parse une paire clé-valeur et retourne les métadonnées complètes
    
    Args:
        key: Clé (ex: "lot", "PROD-lot_150", "taille")
        value: Valeur (ex: "150", "Cocody 1500")
        company_id: ID de l'entreprise
        
    Returns:
        Dict avec prefix, normalized_key, metadata, handler
    """
    dynamic_keys = get_dynamic_keys()
    
    # Normaliser la clé
    prefix, normalized_key = dynamic_keys.normalize_key(key, company_id)
    
    # Extraire les métadonnées de la valeur
    metadata = dynamic_keys.extract_value_metadata(value, prefix)
    
    # Déterminer le handler
    handler = dynamic_keys.get_handler_method(prefix)
    
    return {
        "prefix": prefix,
        "normalized_key": normalized_key,
        "raw_key": key,
        "raw_value": value,
        "metadata": metadata,
        "handler": handler,
        "timestamp": datetime.now().isoformat()
    }

def format_key_for_llm(prefix: str, key: str) -> str:
    """
    Formate une clé pour le prompt LLM avec balise universelle
    
    Args:
        prefix: Préfixe universel
        key: Clé normalisée
        
    Returns:
        Clé formatée (ex: "PROD-lot", "DELIV-zone")
    """
    return f"{prefix}-{key}"

def get_all_valid_keys(company_id: str) -> List[str]:
    """
    Retourne toutes les clés valides pour une entreprise
    
    Args:
        company_id: ID de l'entreprise
        
    Returns:
        Liste des clés valides
    """
    dynamic_keys = get_dynamic_keys()
    
    if company_id in dynamic_keys.company_mappings:
        return list(dynamic_keys.company_mappings[company_id].keys())
    
    return list(DEFAULT_KEY_MAPPING.keys())

#!/usr/bin/env python3
"""
Validateur d'index Meilisearch
Empêche la création d'index non conformes aux règles établies
"""

import re
from typing import Set, Tuple, Optional

# Types d'index autorisés (UNIQUEMENT en minuscules)
ALLOWED_INDEX_TYPES: Set[str] = {
    "products",
    "delivery", 
    "support_paiement",
    "localisation",
    "company_docs"
}

class IndexValidationError(Exception):
    """Exception levée quand un index ne respecte pas les règles"""
    pass

class IndexValidator:
    """Validateur pour les noms d'index Meilisearch"""
    
    @staticmethod
    def parse_index_name(index_uid: str) -> Tuple[str, str]:
        """
        Parse un nom d'index pour extraire le type et company_id
        
        Args:
            index_uid: Nom de l'index (ex: "products_MpfnlSbqwaZ6F4HvxQLRL9du0yG3")
            
        Returns:
            Tuple (index_type, company_id)
        """
        if not index_uid or not isinstance(index_uid, str):
            return "", ""
        
        # Pattern: type_company_id
        parts = index_uid.split('_', 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return "", ""
    
    @staticmethod
    def validate_index_name(index_uid: str, strict: bool = True) -> bool:
        """
        Valide un nom d'index selon les règles établies
        
        Args:
            index_uid: Nom de l'index à valider
            strict: Si True, lève une exception en cas d'erreur
            
        Returns:
            True si valide, False sinon
            
        Raises:
            IndexValidationError: Si strict=True et l'index est invalide
        """
        errors = []
        
        # Vérification de base
        if not index_uid or not isinstance(index_uid, str):
            errors.append("Le nom d'index ne peut pas être vide")
        
        if not errors:
            index_type, company_id = IndexValidator.parse_index_name(index_uid)
            
            # Vérifier le format
            if not index_type or not company_id:
                errors.append(f"Format invalide. Attendu: 'type_company_id', reçu: '{index_uid}'")
            
            # Vérifier que le type est autorisé
            if index_type and index_type not in ALLOWED_INDEX_TYPES:
                errors.append(f"Type d'index non autorisé: '{index_type}'. Types autorisés: {', '.join(ALLOWED_INDEX_TYPES)}")
            
            # Vérifier qu'il n'y a pas de majuscules dans le type
            if index_type and index_type != index_type.lower():
                errors.append(f"Le type d'index doit être en minuscules: '{index_type}' -> '{index_type.lower()}'")
            
            # Vérifier le company_id
            if company_id:
                if len(company_id) < 5:
                    errors.append(f"Company ID trop court: '{company_id}' (minimum 5 caractères)")
                
                # Vérifier les caractères autorisés pour company_id
                if not re.match(r'^[A-Za-z0-9_-]+$', company_id):
                    errors.append(f"Company ID contient des caractères non autorisés: '{company_id}'")
        
        # Gestion des erreurs
        if errors:
            error_msg = f"Index invalide '{index_uid}':\n" + "\n".join(f"  - {error}" for error in errors)
            if strict:
                raise IndexValidationError(error_msg)
            return False
        
        return True
    
    @staticmethod
    def suggest_valid_name(index_uid: str) -> Optional[str]:
        """
        Suggère un nom d'index valide basé sur un nom invalide
        
        Args:
            index_uid: Nom d'index invalide
            
        Returns:
            Suggestion de nom valide ou None si impossible
        """
        if not index_uid:
            return None
        
        index_type, company_id = IndexValidator.parse_index_name(index_uid)
        
        # Corriger le type
        if index_type:
            # Convertir en minuscules
            corrected_type = index_type.lower()
            
            # Mapper les anciens noms vers les nouveaux
            type_mapping = {
                "support": "support_paiement",  # Ancien nom
                "company": "company_docs",      # Ancien nom
            }
            
            corrected_type = type_mapping.get(corrected_type, corrected_type)
            
            # Vérifier si le type corrigé est autorisé
            if corrected_type in ALLOWED_INDEX_TYPES and company_id:
                return f"{corrected_type}_{company_id}"
        
        return None
    
    @staticmethod
    def get_allowed_types() -> Set[str]:
        """Retourne la liste des types d'index autorisés"""
        return ALLOWED_INDEX_TYPES.copy()
    
    @staticmethod
    def is_duplicate_in_uppercase(index_uid: str) -> bool:
        """
        Vérifie si un index est un doublon en majuscules d'un index valide
        
        Args:
            index_uid: Nom de l'index à vérifier
            
        Returns:
            True si c'est un doublon en majuscules
        """
        index_type, company_id = IndexValidator.parse_index_name(index_uid)
        
        if not index_type or not company_id:
            return False
        
        # Vérifier si le type est en majuscules et correspond à un type autorisé
        lower_type = index_type.lower()
        return (index_type != lower_type and 
                lower_type in ALLOWED_INDEX_TYPES)

def validate_before_creation(index_uid: str) -> str:
    """
    Fonction utilitaire pour valider un index avant création
    
    Args:
        index_uid: Nom de l'index à créer
        
    Returns:
        Le nom d'index validé
        
    Raises:
        IndexValidationError: Si l'index est invalide
    """
    validator = IndexValidator()
    
    # Validation stricte
    validator.validate_index_name(index_uid, strict=True)
    
    return index_uid

# Fonction de commodité pour l'import
__all__ = [
    'IndexValidator',
    'IndexValidationError', 
    'validate_before_creation',
    'ALLOWED_INDEX_TYPES'
]

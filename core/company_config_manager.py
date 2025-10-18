#!/usr/bin/env python3
"""
🏢 GESTIONNAIRE DE CONFIGURATION ENTREPRISE
Configuration dynamique 100% générique pour toutes entreprises
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from database.supabase_client import get_supabase_client

@dataclass
class CompanyConfig:
    """Configuration complète d'une entreprise"""
    company_id: str
    business_rules: Dict[str, Any]
    product_catalog: Dict[str, List[str]]
    validation_rules: Dict[str, Any]
    response_templates: Dict[str, str]
    security_level: str = "MEDIUM"

class CompanyConfigManager:
    """
    Gestionnaire de configuration dynamique pour entreprises
    Aucun hardcoding - tout vient de la base de données
    """
    
    def __init__(self):
        self.config_cache = {}
        self.default_config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Configuration par défaut générique"""
        return {
            "business_rules": {
                "allow_pricing": False,
                "allow_promotions": False,
                "require_uncertainty": True,
                "max_product_claims": 5
            },
            "product_catalog": {
                "categories": [],
                "sizes": [],
                "services": []
            },
            "validation_rules": {
                "dangerous_sizes": r"[789]\d*",
                "price_patterns": r"\d+[,.]?\d*\s*€",
                "promo_patterns": r"\d+%"
            },
            "response_templates": {
                "unknown_product": "Je ne trouve pas ce produit dans notre catalogue. Puis-je vous aider avec autre chose ?",
                "no_pricing": "Je n'ai pas accès aux prix en temps réel. Consultez notre site web ou contactez notre service client.",
                "no_promotion": "Je ne peux pas confirmer les promotions en cours. Vérifiez sur notre site web.",
                "uncertainty": "Je n'ai pas cette information précise. Puis-je vous orienter vers notre service client ?",
                "invalid_size": "Cette taille n'est pas disponible dans notre gamme. Voulez-vous voir nos tailles disponibles ?"
            },
            "security_level": "MEDIUM"
        }
    
    async def get_company_config(self, company_id: str) -> CompanyConfig:
        """
        Récupère la configuration d'une entreprise depuis la DB
        """
        # Vérifier le cache
        if company_id in self.config_cache:
            return self.config_cache[company_id]
        
        try:
            # Charger depuis Supabase
            supabase = get_supabase_client()
            
            # Requête pour récupérer la config (nouveau schéma company_rag_configs)
            result = supabase.table("company_rag_configs").select("*").eq("company_id", company_id).execute()
            
            if result.data:
                config_data = result.data[0]
                # Adapter le nouveau schéma vers l'ancien format CompanyConfig
                company_config = CompanyConfig(
                    company_id=company_id,
                    business_rules={
                        "allow_pricing": False,
                        "allow_promotions": False,
                        "require_uncertainty": True,
                        "max_product_claims": 5
                    },
                    product_catalog={
                        "categories": [],
                        "sizes": [],
                        "services": []
                    },
                    validation_rules={
                        "dangerous_sizes": "[789]\\d*",
                        "price_patterns": "\\d+[,.]?\\d*\\s*€",
                        "promo_patterns": "\\d+%"
                    },
                    response_templates={
                        "unknown_product": "Je ne trouve pas ce produit dans notre catalogue.",
                        "no_pricing": "Je n'ai pas accès aux prix en temps réel.",
                        "no_promotion": "Je ne peux pas confirmer les promotions en cours.",
                        "uncertainty": "Je n'ai pas cette information précise.",
                        "invalid_size": "Cette taille n'est pas disponible."
                    },
                    security_level="MEDIUM"
                )
            else:
                # Créer config par défaut si pas trouvée
                company_config = CompanyConfig(
                    company_id=company_id,
                    **self.default_config
                )
                await self._create_default_config(company_id, company_config)
            
            # Mettre en cache
            self.config_cache[company_id] = company_config
            return company_config
            
        except Exception as e:
            logging.error(f"[CONFIG] Erreur chargement config {company_id}: {e}")
            # Fallback vers config par défaut
            return CompanyConfig(
                company_id=company_id,
                **self.default_config
            )
    
    async def _create_default_config(self, company_id: str, config: CompanyConfig):
        """Crée une configuration par défaut en DB (nouveau schéma)"""
        try:
            supabase = get_supabase_client()
            
            # Adapter vers le nouveau schéma company_rag_configs
            config_dict = {
                "identifiant_entreprise": company_id,
                "nom_de_l_entreprise": f"Entreprise {company_id}",
                "ai_name": "Jessica",
                "secteur_activite": "Commerce",
                "mission_principale": "Assistance client",
                "objectif_final": "Satisfaction client",
                "rag_active": True,
                "comportement_de_chiffon": "Professionnel et aidant",
                "message_de_retour_à_l_humain": "Je vous transfère vers un conseiller.",
                "modèle_d_invite_système": "Tu es Jessica, assistante IA professionnelle.",
                "meili_config": {},
                "attributs_recherchables": [],
                "attributs_filtrables": [],
                "attributs_sortables": [],
                "champs_de_modèle_de_document": {}
            }
            
            supabase.table("company_rag_configs").insert(config_dict).execute()
            logging.info(f"[CONFIG] Configuration par défaut créée pour {company_id}")
            
        except Exception as e:
            logging.error(f"[CONFIG] Erreur création config par défaut: {e}")
    
    async def update_company_config(self, company_id: str, updates: Dict[str, Any]):
        """Met à jour la configuration d'une entreprise"""
        try:
            supabase = get_supabase_client()
            
            supabase.table("company_rag_configs").update(updates).eq("identifiant_entreprise", company_id).execute()
            
            # Invalider le cache
            if company_id in self.config_cache:
                del self.config_cache[company_id]
            
            logging.info(f"[CONFIG] Configuration mise à jour pour {company_id}")
            
        except Exception as e:
            logging.error(f"[CONFIG] Erreur mise à jour config: {e}")
    
    def get_validation_rules(self, company_id: str) -> Dict[str, Any]:
        """Récupère les règles de validation pour une entreprise"""
        config = self.config_cache.get(company_id)
        if config:
            return config.validation_rules
        return self.default_config["validation_rules"]
    
    def get_response_template(self, company_id: str, template_key: str) -> str:
        """Récupère un template de réponse pour une entreprise"""
        config = self.config_cache.get(company_id)
        if config and template_key in config.response_templates:
            return config.response_templates[template_key]
        return self.default_config["response_templates"].get(template_key, "Information non disponible.")
    
    def should_allow_pricing(self, company_id: str) -> bool:
        """Vérifie si l'entreprise autorise les prix"""
        config = self.config_cache.get(company_id)
        if config:
            return config.business_rules.get("allow_pricing", False)
        return False
    
    def should_allow_promotions(self, company_id: str) -> bool:
        """Vérifie si l'entreprise autorise les promotions"""
        config = self.config_cache.get(company_id)
        if config:
            return config.business_rules.get("allow_promotions", False)
        return False

# Instance globale
company_config_manager = CompanyConfigManager()

async def get_company_config(company_id: str) -> CompanyConfig:
    """Fonction utilitaire pour récupérer la config d'une entreprise"""
    return await company_config_manager.get_company_config(company_id)

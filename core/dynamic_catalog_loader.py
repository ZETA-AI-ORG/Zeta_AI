#!/usr/bin/env python3
"""
📊 CHARGEMENT DYNAMIQUE DE CATALOGUE PRODUITS
Système générique pour charger les données de n'importe quelle entreprise
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from database.supabase_client import get_supabase_client
from database.vector_store_clean import search_meili_keywords

import re

from core.global_catalog_cache import get_global_catalog_cache

logger = logging.getLogger(__name__)

# --- Fonctions utilitaires d'extraction (rendues globales) ---

def _extract_zones_from_text(content: str) -> List[str]:
    """Extrait les noms de zones d'un texte"""
    
    zones = []
    
    zone_pattern = r'([a-zàâäéèêëïîôöùûüÿç-]+)'
    
    if "zones" in content:
        zone_section = content.split("zones")[1].split("tarif")[0]
        zone_matches = re.findall(zone_pattern, zone_section)
        zones.extend([zone for zone in zone_matches if len(zone) > 3])
    
    return zones[:10]  # Limiter à 10 zones

def _extract_delivery_cost(content: str) -> int:
    """Extrait le coût de livraison d'un texte"""
    
    cost_pattern = r'(\d+)\s*f\s*cfa'
    matches = re.findall(cost_pattern, content, re.IGNORECASE)
    
    if matches:
        return int(matches[0])
    
    return 1500  # Par défaut

def _extract_delivery_time(content: str) -> str:
    """Extrait les délais de livraison d'un texte"""
    if "jour même" in content:
        return "Jour même si commande avant 11h, lendemain après 11h"
    elif "24h" in content:
        return "24h"
    elif "48h" in content:
        return "48h"
    
    return "À confirmer"

# --- Classe DynamicCatalogLoader ---

class DynamicCatalogLoader:
    """Chargeur dynamique de catalogue pour toutes les entreprises"""
    
    def __init__(self, company_id: str):
        self.company_id = company_id
        self.supabase = get_supabase_client()
    
    async def load_products_catalog(self) -> Dict[str, Any]:
        """Charge le catalogue produits depuis MeiliSearch"""
        try:
            # Rechercher les documents de catalogue produits
            results = await search_meili_keywords(
                query="catalogue produits prix tarifs",
                company_id=self.company_id,
                limit=10
            )
            
            if not results:
                logger.warning(f"[CATALOG_LOADER] Aucun catalogue trouvé pour {self.company_id}")
                return {}
            
            # Parser les résultats pour extraire les produits
            products_catalog = self._parse_products_from_results(results)
            
            logger.info(f"[CATALOG_LOADER] Catalogue chargé: {len(products_catalog)} catégories")
            return products_catalog
            
        except Exception as e:
            logger.error(f"[CATALOG_LOADER] Erreur chargement catalogue: {e}")
            return {}
    
    async def load_delivery_zones(self) -> Dict[str, Any]:
        """Charge les zones de livraison depuis MeiliSearch"""
        try:
            # Rechercher les documents de livraison
            results = await search_meili_keywords(
                query="livraison zones tarifs délais",
                company_id=self.company_id,
                limit=5
            )
            
            if not results:
                logger.warning(f"[CATALOG_LOADER] Aucune info livraison trouvée pour {self.company_id}")
                return {}
            
            # Parser les résultats pour extraire les zones
            delivery_zones = self._parse_delivery_zones_from_results(results)
            
            logger.info(f"[CATALOG_LOADER] Zones de livraison chargées: {len(delivery_zones)} zones")
            return delivery_zones
            
        except Exception as e:
            logger.error(f"[CATALOG_LOADER] Erreur chargement zones: {e}")
            return {}
    
    async def load_payment_info(self) -> Dict[str, Any]:
        """Charge les informations de paiement depuis MeiliSearch"""
        try:
            # Rechercher les documents de paiement
            results = await search_meili_keywords(
                query="paiement wave acompte conditions",
                company_id=self.company_id,
                limit=3
            )
            
            if not results:
                logger.warning(f"[CATALOG_LOADER] Aucune info paiement trouvée pour {self.company_id}")
                return {}
            
            # Parser les résultats pour extraire les infos de paiement
            payment_info = self._parse_payment_info_from_results(results)
            
            logger.info(f"[CATALOG_LOADER] Infos paiement chargées: {payment_info}")
            return payment_info
            
        except Exception as e:
            logger.error(f"[CATALOG_LOADER] Erreur chargement paiement: {e}")
            return {}
    
    def _parse_products_from_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Parse les résultats MeiliSearch pour extraire les produits"""
        products_catalog = {}
        
        for result in results:
            content = result.get("content", "").lower()
            
            # Détecter les couches à pression
            if "couches à pression" in content or "pression" in content:
                products_catalog["couches_pression"] = self._extract_pression_prices(content)
            
            # Détecter les couches culottes
            elif "couches culottes" in content or "culottes" in content:
                products_catalog["couches_culottes"] = self._extract_culottes_prices(content)
            
            # Détecter les couches adultes
            elif "couches adultes" in content or "adultes" in content:
                products_catalog["couches_adultes"] = self._extract_adultes_prices(content)
        
        return products_catalog
    
    def _extract_pression_prices(self, content: str) -> Dict[str, Dict]:
        """Extrait les prix des couches à pression"""
        prices = {}
        
        import re
        
        # Chercher les patterns "Taille X - Y à Z kg - N couches | P F CFA"
        pattern = r'taille\s+(\d+)\s*-\s*(\d+)\s*à\s*(\d+)\s*kg\s*-\s*(\d+)\s*couches\s*\|\s*([\d.,]+)\s*f\s*cfa'
        matches = re.findall(pattern, content, re.IGNORECASE)
        
        for match in matches:
            taille, min_weight, max_weight, units, price = match
            price_clean = float(price.replace(',', '.'))
            
            prices[f"taille {taille}"] = {
                "weight_range": f"{min_weight}-{max_weight}kg",
                "price": int(price_clean),
                "units": int(units)
            }
        
        return prices
    
    def _extract_culottes_prices(self, content: str) -> Dict[str, Dict]:
        """Extrait les prix des couches culottes"""
        prices = {}
        
        import re
        
        # Chercher les patterns "X paquet(s) - Y F CFA | Z F/paquet"
        pattern = r'(\d+)\s*paquets?\s*-\s*([\d.,]+)\s*f\s*cfa\s*\|\s*([\d.,]+)\s*f/paquet'
        matches = re.findall(pattern, content, re.IGNORECASE)
        
        for match in matches:
            quantity, total_price, unit_price = match
            total_price_clean = float(total_price.replace(',', '.'))
            unit_price_clean = float(unit_price.replace(',', '.'))
            
            prices[f"{quantity} paquet{'s' if int(quantity) > 1 else ''}"] = {
                "price": int(total_price_clean),
                "unit_price": int(unit_price_clean)
            }
        
        # Chercher les colis
        colis_pattern = r'(\d+)\s*colis\s*\((\d+)\)\s*-\s*([\d.,]+)\s*f\s*cfa\s*\|\s*([\d.,]+)\s*f/paquet'
        colis_matches = re.findall(colis_pattern, content, re.IGNORECASE)
        
        for match in colis_matches:
            colis_count, units, total_price, unit_price = match
            total_price_clean = float(total_price.replace(',', '.'))
            unit_price_clean = float(unit_price.replace(',', '.'))
            
            prices[f"{colis_count} colis ({units})"] = {
                "price": int(total_price_clean),
                "unit_price": int(unit_price_clean)
            }
        
        return prices
    
    def _extract_adultes_prices(self, content: str) -> Dict[str, Dict]:
        """Extrait les prix des couches adultes"""
        prices = {}
        
        import re
        
        # Chercher les patterns "X paquet(s) (Y unités) - Z F CFA/unité | W F CFA/paquet"
        pattern = r'(\d+)\s*paquets?\s*\((\d+)\s*unités?\)\s*-\s*([\d.,]+)\s*f\s*cfa/unité\s*\|\s*([\d.,]+)\s*f\s*cfa/paquet'
        matches = re.findall(pattern, content, re.IGNORECASE)
        
        for match in matches:
            quantity, units, unit_price, total_price = match
            unit_price_clean = float(unit_price.replace(',', '.'))
            total_price_clean = float(total_price.replace(',', '.'))
            
            prices[f"{quantity} paquet{'s' if int(quantity) > 1 else ''} ({units})"] = {
                "price": int(total_price_clean),
                "unit_price": int(unit_price_clean)
            }
        
        # Chercher les colis
        colis_pattern = r'(\d+)\s*colis\s*\((\d+)\s*unités?\)\s*-\s*([\d.,]+)\s*f\s*cfa/unité\s*\|\s*([\d.,]+)\s*f\s*cfa/colis'
        colis_matches = re.findall(colis_pattern, content, re.IGNORECASE)
        
        for match in colis_matches:
            colis_count, units, unit_price, total_price = match
            unit_price_clean = float(unit_price.replace(',', '.'))
            total_price_clean = float(total_price.replace(',', '.'))
            
            prices[f"{colis_count} colis ({units})"] = {
                "price": int(total_price_clean),
                "unit_price": int(unit_price_clean)
            }
        
        return prices
    
    def _parse_delivery_zones_from_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Parse les résultats pour extraire les zones de livraison"""
        delivery_zones = {}
        
        for result in results:
            content = result.get("content", "").lower()
            
            # Chercher les zones centrales
            if "zones centrales" in content or "zones couvertes" in content:
                central_zones = _extract_zones_from_text(content) # Appel à la fonction globale
                if central_zones:
                    delivery_zones["centrales"] = {
                        "zones": central_zones,
                        "cost": _extract_delivery_cost(content), # Appel à la fonction globale
                        "time": _extract_delivery_time(content)  # Appel à la fonction globale
                    }
            
            # Chercher les zones périphériques
            elif "périphériques" in content or "périphérie" in content:
                peripheral_zones = _extract_zones_from_text(content) # Appel à la fonction globale
                if peripheral_zones:
                    delivery_zones["périphériques"] = {
                        "zones": peripheral_zones,
                        "cost": _extract_delivery_cost(content), # Appel à la fonction globale
                        "time": _extract_delivery_time(content)  # Appel à la fonction globale
                    }
        
        return delivery_zones
    
    def _parse_payment_info_from_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Parse les résultats pour extraire les infos de paiement"""
        payment_info = {}
        
        for result in results:
            content = result.get("content", "").lower()
            
            # Chercher Wave
            if "wave" in content:
                payment_info["method"] = "Wave"
                
                # Extraire le numéro de téléphone
                
                phone_pattern = r'(\+?\d{2,3}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2})'
                phone_matches = re.findall(phone_pattern, content)
                if phone_matches:
                    payment_info["phone"] = phone_matches[0]
            
            # Chercher l'acompte
            if "acompte" in content:
                
                acompte_pattern = r'(\d+)\s*f\s*cfa'
                acompte_matches = re.findall(acompte_pattern, content)
                if acompte_matches:
                    payment_info["deposit_required"] = int(acompte_matches[0])
        
        # Valeurs par défaut
        payment_info.setdefault("method", "À confirmer")
        payment_info.setdefault("phone", "Non fourni")
        payment_info.setdefault("deposit_required", 0)
        payment_info.setdefault("currency", "FCFA")
        
        return payment_info

async def load_company_catalog(company_id: str) -> Dict[str, Any]:
    """
    Fonction principale pour charger le catalogue d'une entreprise
    
    Args:
        company_id: ID de l'entreprise
    
    Returns:
        Dictionnaire avec le catalogue complet
    """
    cache = get_global_catalog_cache()

    async def _build() -> Dict[str, Any]:
        loader = DynamicCatalogLoader(company_id)
        return {
            "products": await loader.load_products_catalog(),
            "delivery_zones": await loader.load_delivery_zones(),
            "payment_info": await loader.load_payment_info(),
        }

    return await cache.get_catalog(company_id=company_id, builder=_build)


async def prewarm_company_catalog(company_id: str) -> bool:
    try:
        _ = await load_company_catalog(company_id)
        return True
    except Exception:
        return False




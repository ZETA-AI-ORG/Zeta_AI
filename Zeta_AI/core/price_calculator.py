#!/usr/bin/env python3
"""
🧮 CALCULATEUR DE PRIX INTELLIGENT RUE DU GROS
Système de calcul automatique des prix pour les couches avec frais de livraison
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class ProductPrice:
    """Structure pour stocker les informations de prix d'un produit"""
    product_type: str
    size: str
    quantity: int
    unit_price: float
    total_price: float
    description: str

@dataclass
class DeliveryInfo:
    """Structure pour les informations de livraison"""
    zone: str
    delivery_cost: float
    delivery_time: str
    is_central: bool

class UniversalPriceCalculator:
    """Calculateur de prix universel pour toutes les entreprises (100% synchrone, fallback si besoin)"""
    
    def __init__(self, company_id: str = None):
        self.company_id = company_id
        self.products_catalog = {}
        self.delivery_zones = {}
        self.payment_info = {}
        # Chargement synchrone direct (fallback en dur)
        self._load_fallback_data()
    
    async def _load_company_data(self):
        """Charge les données de l'entreprise depuis la base de données"""
        if not self.company_id:
            return
        
        try:
            # Charger les données dynamiquement depuis la base de données
            from core.dynamic_catalog_loader import load_company_catalog
            
            catalog_data = await load_company_catalog(self.company_id)
            
            self.products_catalog = catalog_data.get("products", {})
            self.delivery_zones = catalog_data.get("delivery_zones", {})
            self.payment_info = catalog_data.get("payment_info", {})
            
            print(f"[PRICE_CALCULATOR] ✅ Données chargées pour {self.company_id}")
            print(f"[PRICE_CALCULATOR] - Produits: {len(self.products_catalog)} catégories")
            print(f"[PRICE_CALCULATOR] - Zones: {len(self.delivery_zones)} zones")
            print(f"[PRICE_CALCULATOR] - Paiement: {self.payment_info.get('method', 'N/A')}")
            
        except Exception as e:
            print(f"[PRICE_CALCULATOR] ❌ Erreur chargement données entreprise {self.company_id}: {e}")
            # Fallback vers les données Rue du Gros si disponible
            if self.company_id == "MpfnlSbqwaZ6F4HvxQLRL9du0yG3":
                self._load_fallback_data()
    
    def _load_products_from_database(self):
        """Charge le catalogue produits depuis la base de données"""
        # Cette méthode sera implémentée pour charger depuis MeiliSearch/Supabase
        # Pour l'instant, on garde les données Rue du Gros comme exemple
        if self.company_id == "MpfnlSbqwaZ6F4HvxQLRL9du0yG3":
            self.products_catalog = {
                "couches_pression": {
                    "taille 1": {"weight_range": "0-4kg", "price": 17900, "units": 300},
                    "taille 2": {"weight_range": "3-8kg", "price": 18900, "units": 300},
                    "taille 3": {"weight_range": "6-11kg", "price": 22900, "units": 300},
                    "taille 4": {"weight_range": "9-14kg", "price": 25900, "units": 300},
                    "taille 5": {"weight_range": "12-17kg", "price": 25900, "units": 300},
                    "taille 6": {"weight_range": "15-25kg", "price": 27900, "units": 300},
                    "taille 7": {"weight_range": "20-30kg", "price": 28900, "units": 300}
                },
                "couches_culottes": {
                    "1 paquet": {"price": 5500, "unit_price": 5500},
                    "2 paquets": {"price": 9800, "unit_price": 4900},
                    "3 paquets": {"price": 13500, "unit_price": 4500},
                    "6 paquets": {"price": 25000, "unit_price": 4167},
                    "12 paquets": {"price": 48000, "unit_price": 4000},
                    "1 colis (48)": {"price": 168000, "unit_price": 3500}
                },
                "couches_adultes": {
                    "1 paquet (10)": {"price": 5880, "unit_price": 588},
                    "2 paquets (20)": {"price": 11760, "unit_price": 570},
                    "3 paquets (30)": {"price": 16200, "unit_price": 540},
                    "6 paquets (60)": {"price": 36000, "unit_price": 500},
                    "12 paquets (120)": {"price": 114000, "unit_price": 475},
                    "1 colis (240)": {"price": 216000, "unit_price": 450}
                }
            }
    
    def _load_delivery_zones_from_database(self):
        """Charge les zones de livraison depuis la base de données"""
        if self.company_id == "MpfnlSbqwaZ6F4HvxQLRL9du0yG3":
            self.delivery_zones = {
                "centrales": {
                    "zones": ["yopougon", "cocody", "plateau", "adjamé", "abobo", "marcory", "koumassi", "treichville", "angré", "riviera"],
                    "cost": 1500,
                    "time": "Jour même si commande avant 11h, lendemain après 11h"
                },
                "périphériques": {
                    "zones": ["port-bouët", "attécoubé", "bingerville", "songon", "anyama", "brofodoumé", "grand-bassam", "dabou"],
                    "cost": 2250,
                    "time": "Jour même si commande avant 11h, lendemain après 11h"
                },
                "hors_abidjan": {
                    "zones": ["autres villes côte d'ivoire"],
                    "cost": 4250,
                    "time": "24h-72h selon la localité"
                }
            }
    
    def _load_payment_info_from_database(self):
        """Charge les informations de paiement depuis la base de données"""
        if self.company_id == "MpfnlSbqwaZ6F4HvxQLRL9du0yG3":
            self.payment_info = {
                "method": "Wave",
                "phone": "+2250787360757",
                "deposit_required": 2000,
                "currency": "FCFA"
            }
    
    def extract_quantity_from_text(self, text: str) -> Tuple[int, str]:
        """Extrait la quantité et le type de produit du texte"""
        text_lower = text.lower()
        
        # Patterns pour extraire les quantités
        quantity_patterns = [
            r'(\d+)\s*paquets?',
            r'(\d+)\s*colis',
            r'(\d+)\s*unités?',
            r'(\d+)\s*couches?'
        ]
        
        quantity = 1
        for pattern in quantity_patterns:
            match = re.search(pattern, text_lower)
            if match:
                quantity = int(match.group(1))
                break
        
        # Détecter le type de produit
        if any(word in text_lower for word in ['culottes', 'culotte']):
            return quantity, "culottes"
        elif any(word in text_lower for word in ['adultes', 'adulte']):
            return quantity, "adultes"
        else:
            return quantity, "pression"
    
    def extract_size_from_text(self, text: str, product_type: str) -> str:
        """Extrait la taille du produit du texte"""
        text_lower = text.lower()
        
        if product_type == "pression":
            # Chercher les tailles 1-7
            for i in range(1, 8):
                if f"taille {i}" in text_lower or f"t{i}" in text_lower:
                    return f"taille {i}"
            
            # Chercher par poids
            weight_patterns = {
                "taille 1": [0, 1, 2, 3, 4],
                "taille 2": [3, 4, 5, 6, 7, 8],
                "taille 3": [6, 7, 8, 9, 10, 11],
                "taille 4": [9, 10, 11, 12, 13, 14],
                "taille 5": [12, 13, 14, 15, 16, 17],
                "taille 6": [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25],
                "taille 7": [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
            }
            
            for weight in range(0, 31):
                if f"{weight}kg" in text_lower or f"{weight} kg" in text_lower:
                    for taille, poids_range in weight_patterns.items():
                        if weight in poids_range:
                            return taille
            
            return "taille 3"  # Taille par défaut
        
        elif product_type == "culottes":
            # Pour les culottes, on cherche le nombre de paquets
            if "1 paquet" in text_lower or "un paquet" in text_lower:
                return "1 paquet"
            elif "2 paquets" in text_lower or "deux paquets" in text_lower:
                return "2 paquets"
            elif "3 paquets" in text_lower or "trois paquets" in text_lower:
                return "3 paquets"
            elif "6 paquets" in text_lower or "six paquets" in text_lower:
                return "6 paquets"
            elif "12 paquets" in text_lower or "douze paquets" in text_lower:
                return "12 paquets"
            elif "colis" in text_lower:
                return "1 colis (48)"
            else:
                return "1 paquet"  # Par défaut
        
        elif product_type == "adultes":
            # Pour les adultes, même logique
            if "1 paquet" in text_lower or "un paquet" in text_lower:
                return "1 paquet (10)"
            elif "2 paquets" in text_lower or "deux paquets" in text_lower:
                return "2 paquets (20)"
            elif "3 paquets" in text_lower or "trois paquets" in text_lower:
                return "3 paquets (30)"
            elif "6 paquets" in text_lower or "six paquets" in text_lower:
                return "6 paquets (60)"
            elif "12 paquets" in text_lower or "douze paquets" in text_lower:
                return "12 paquets (120)"
            elif "colis" in text_lower:
                return "1 colis (240)"
            else:
                return "1 paquet (10)"  # Par défaut
        
        return "taille 3"  # Fallback
    
    def extract_delivery_zone(self, text: str) -> DeliveryInfo:
        """Extrait la zone de livraison du texte"""
        text_lower = text.lower()
        
        # Vérifier les zones centrales
        for zone in self.delivery_zones["centrales"]["zones"]:
            if zone in text_lower:
                return DeliveryInfo(
                    zone=zone.title(),
                    delivery_cost=self.delivery_zones["centrales"]["cost"],
                    delivery_time=self.delivery_zones["centrales"]["time"],
                    is_central=True
                )
        
        # Vérifier les zones périphériques
        for zone in self.delivery_zones["périphériques"]["zones"]:
            if zone in text_lower:
                return DeliveryInfo(
                    zone=zone.title(),
                    delivery_cost=self.delivery_zones["périphériques"]["cost"],
                    delivery_time=self.delivery_zones["périphériques"]["time"],
                    is_central=False
                )
        
        # Par défaut, zone centrale
        return DeliveryInfo(
            zone="Zone centrale (à confirmer)",
            delivery_cost=self.delivery_zones["centrales"]["cost"],
            delivery_time=self.delivery_zones["centrales"]["time"],
            is_central=True
        )
    
    def calculate_product_price(self, text: str) -> List[ProductPrice]:
        # Sécurité : print si attributs essentiels absents
        if not hasattr(self, 'products_catalog'):
            print('[BUG CALCULATEUR] products_catalog absent')
            self.products_catalog = {}
        if not hasattr(self, 'delivery_zones'):
            print('[BUG CALCULATEUR] delivery_zones absent')
            self.delivery_zones = {}
        if not hasattr(self, 'payment_info'):
            print('[BUG CALCULATEUR] payment_info absent')
            self.payment_info = {}
        """Calcule le prix des produits à partir du texte"""
        quantity, product_type = self.extract_quantity_from_text(text)
        size = self.extract_size_from_text(text, product_type)
        
        products = []
        
        # Mapper les types de produits vers les clés du catalogue
        product_mapping = {
            "pression": "couches_pression",
            "culottes": "couches_culottes", 
            "adultes": "couches_adultes"
        }
        
        catalog_key = product_mapping.get(product_type)
        if not catalog_key or catalog_key not in self.products_catalog:
            return products
        
        product_catalog = self.products_catalog[catalog_key]
        
        if size in product_catalog:
            price_info = product_catalog[size]
            total_price = price_info["price"] * quantity
            
            # Déterminer le type de produit pour l'affichage
            product_type_names = {
                "couches_pression": "Couches à pression",
                "couches_culottes": "Couches culottes",
                "couches_adultes": "Couches adultes"
            }
            
            product_name = product_type_names.get(catalog_key, "Produit")
            
            # Construire la description
            if catalog_key == "couches_pression":
                description = f"{quantity} paquet(s) de couches à pression {size} - {price_info.get('units', 'N/A')} couches par paquet"
                size_display = f"{size} ({price_info.get('weight_range', '')})"
            else:
                description = f"{quantity} x {size} de {product_name.lower()}"
                size_display = size
            
            products.append(ProductPrice(
                product_type=product_name,
                size=size_display,
                quantity=quantity,
                unit_price=price_info.get("unit_price", price_info["price"]),
                total_price=total_price,
                description=description
            ))
        
        return products
    
    def calculate_total_price(self, products: List[ProductPrice], delivery_zone: str = None) -> Dict:
        """Calcule le prix total avec livraison"""
        if not products:
            return {
                "products": [],
                "subtotal": 0,
                "delivery_cost": 0,
                "total": 0,
                "delivery_info": None,
                "breakdown": "Aucun produit identifié"
            }
        
        # Calculer le sous-total
        subtotal = sum(product.total_price for product in products)
        
        # Calculer les frais de livraison
        delivery_info = None
        delivery_cost = 0
        
        if delivery_zone:
            delivery_info = self.extract_delivery_zone(delivery_zone)
            delivery_cost = delivery_info.delivery_cost
        
        total = subtotal + delivery_cost
        
        return {
            "products": products,
            "subtotal": subtotal,
            "delivery_cost": delivery_cost,
            "total": total,
            "delivery_info": delivery_info,
            "breakdown": self._generate_price_breakdown(products, delivery_cost, delivery_info)
        }
    
    def _generate_price_breakdown(self, products: List[ProductPrice], delivery_cost: float, delivery_info: DeliveryInfo = None) -> str:
        """Génère un récapitulatif détaillé des prix"""
        breakdown = "🧮 RÉCAPITULATIF DE PRIX :\n\n"
        
        # Détail des produits
        for i, product in enumerate(products, 1):
            breakdown += f"📦 Produit {i}: {product.description}\n"
            breakdown += f"   💰 Prix unitaire: {product.unit_price:,.0f} FCFA\n"
            breakdown += f"   📊 Quantité: {product.quantity}\n"
            breakdown += f"   💵 Sous-total: {product.total_price:,.0f} FCFA\n\n"
        
        # Sous-total
        subtotal = sum(p.total_price for p in products)
        breakdown += f"📋 SOUS-TOTAL PRODUITS: {subtotal:,.0f} FCFA\n"
        
        # Frais de livraison
        if delivery_info:
            breakdown += f"🚚 LIVRAISON ({delivery_info.zone}): {delivery_cost:,.0f} FCFA\n"
            breakdown += f"   ⏰ Délai: {delivery_info.delivery_time}\n"
        else:
            breakdown += f"🚚 LIVRAISON: {delivery_cost:,.0f} FCFA (zone à confirmer)\n"
        
        # Total
        total = subtotal + delivery_cost
        breakdown += f"\n🎯 TOTAL À PAYER: {total:,.0f} FCFA\n"
        
        # Acompte
        breakdown += f"💳 ACOMPTE REQUIS: 2.000 FCFA\n"
        breakdown += f"💰 RESTE À PAYER: {total - 2000:,.0f} FCFA"
        
        return breakdown

# Cache des calculateurs par entreprise
_calculator_cache = {}

def get_price_calculator(company_id: str) -> UniversalPriceCalculator:
    """Obtient ou crée un calculateur de prix pour une entreprise"""
    if company_id not in _calculator_cache:
        _calculator_cache[company_id] = UniversalPriceCalculator(company_id)
    return _calculator_cache[company_id]

def calculate_order_price(message: str, company_id: str, delivery_zone: str = None) -> Dict:
    """
    Fonction principale pour calculer le prix d'une commande
    
    Args:
        message: Message du client contenant la commande
        company_id: ID de l'entreprise
        delivery_zone: Zone de livraison (optionnel)
    
    Returns:
        Dictionnaire avec les informations de prix calculées
    """
    calculator = get_price_calculator(company_id)
    products = calculator.calculate_product_price(message)
    return calculator.calculate_total_price(products, delivery_zone)

def extract_delivery_zone_from_conversation(conversation_history: List[Dict]) -> str:
    """
    Extrait la zone de livraison de l'historique de conversation
    """
    for message in reversed(conversation_history):  # Commencer par les plus récents
        text = message.get("message", "").lower()
        if any(zone in text for zone in ["cocody", "yopougon", "plateau", "adjamé", "abobo", "marcory", "koumassi", "treichville", "angré", "riviera", "bingerville", "port-bouët", "attécoubé"]):
            return message.get("message", "")
    return None

"""
Modèles Pydantic pour validation de la table company_booster
Assure la cohérence des données multi-tenant
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional


class Product(BaseModel):
    """Modèle pour un produit"""
    name: str
    category: str
    subcategory: str
    price_min: int = Field(gt=0, description="Prix minimum en FCFA")
    price_max: int = Field(gt=0, description="Prix maximum en FCFA")
    
    @validator('price_max')
    def price_max_greater_than_min(cls, v, values):
        if 'price_min' in values and v < values['price_min']:
            raise ValueError('price_max doit être >= price_min')
        return v


class DeliveryZone(BaseModel):
    """Modèle pour une zone de livraison"""
    name: str
    price: int = Field(gt=0, description="Frais de livraison en FCFA")


class PaymentMethod(BaseModel):
    """Modèle pour un moyen de paiement"""
    name: str
    deposit: int = Field(ge=0, description="Acompte obligatoire en FCFA")


class CategoryContact(BaseModel):
    """Catégorie CONTACT"""
    name: str = ""
    phones: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    zones: List[str] = Field(default_factory=list)
    products: List[str] = Field(default_factory=list)
    methods: List[str] = Field(default_factory=list)
    sector: str = ""


class CategoryProduit(BaseModel):
    """Catégorie PRODUIT"""
    name: str = ""
    products: List[Product] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    zones: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    methods: List[str] = Field(default_factory=list)
    sector: str = ""


class CategoryPaiement(BaseModel):
    """Catégorie PAIEMENT"""
    name: str = ""
    methods: List[PaymentMethod] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    zones: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    products: List[str] = Field(default_factory=list)
    sector: str = ""


class CategoryLivraison(BaseModel):
    """Catégorie LIVRAISON"""
    name: str = ""
    zones: List[DeliveryZone] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    methods: List[str] = Field(default_factory=list)
    products: List[str] = Field(default_factory=list)
    sector: str = ""


class CategoryEntreprise(BaseModel):
    """Catégorie ENTREPRISE"""
    name: str
    sector: str
    keywords: List[str] = Field(default_factory=list)
    zones: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    methods: List[str] = Field(default_factory=list)
    products: List[str] = Field(default_factory=list)


class Categories(BaseModel):
    """Toutes les catégories"""
    CONTACT: CategoryContact
    PRODUIT: CategoryProduit
    PAIEMENT: CategoryPaiement
    LIVRAISON: CategoryLivraison
    ENTREPRISE: CategoryEntreprise


class PriceRange(BaseModel):
    """Fourchette de prix"""
    min: int = Field(gt=0)
    max: int = Field(gt=0)
    
    @validator('max')
    def max_greater_than_min(cls, v, values):
        if 'min' in values and v < values['min']:
            raise ValueError('max doit être >= min')
        return v


class Filters(BaseModel):
    """Filtres dérivés"""
    price_range: PriceRange
    product_names: List[str]
    delivery_zones: Dict[str, int]
    payment_methods: List[str]


class CompanyBooster(BaseModel):
    """Modèle complet pour company_booster"""
    id: Optional[int] = None
    company_id: str
    keywords: List[str]
    categories: Categories
    filters: Filters
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        json_encoders = {
            # Encodage personnalisé si nécessaire
        }
    
    @validator('keywords')
    def keywords_not_empty(cls, v):
        if not v:
            raise ValueError('keywords ne peut pas être vide')
        return v
    
    @validator('company_id')
    def company_id_valid(cls, v):
        if not v or len(v) < 10:
            raise ValueError('company_id invalide')
        return v

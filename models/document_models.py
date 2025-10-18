from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from uuid import uuid4

# --------- SUPABASE STRUCTURE ---------
class CompanyInfo(BaseModel):
    id: str
    type: str = "company_info"
    searchable_content: str
    structured_data: Dict

class ProductVariant(BaseModel):
    sku: str
    price: float
    stock: int
    description_specifique: str
    attributes: Dict[str, str]

class Product(BaseModel):
    id: str
    type: str = "product"
    searchable_content: str
    structured_data: Dict

class ServiceInfo(BaseModel):
    id: str
    type: str = "service_info"
    searchable_content: str
    structured_data: Dict

class FAQIntent(BaseModel):
    id: str
    type: str = "faq"
    searchable_content: str
    structured_data: Dict

# --------- MEILISEARCH STRUCTURE ---------
class MeiliCompanyInfo(BaseModel):
    id: str
    type: str = "company"
    title: str
    content: str
    category: str = "info_entreprise"
    searchable_fields: List[str]

class MeiliProduct(BaseModel):
    id: str
    type: str = "produit"
    title: str
    content: str
    product_name: str
    price: float
    sku: str
    stock: int
    category: str
    subcategory: str
    attributes: Dict[str, str]
    searchable_fields: List[str]

class MeiliServiceInfo(BaseModel):
    id: str
    type: str = "service"
    title: str
    content: str
    category: str
    searchable_fields: List[str]

class MeiliFAQ(BaseModel):
    id: str
    type: str = "faq"
    title: str
    content: str
    category: str = "faq_generale"
    searchable_fields: List[str]

from typing import Dict, List
from models.document_models import (
    CompanyInfo, Product, ProductVariant, ServiceInfo, FAQIntent,
    MeiliCompanyInfo, MeiliProduct, MeiliServiceInfo, MeiliFAQ
)

class DocumentProcessor:
    def __init__(self, company_id: str):
        self.company_id = company_id

    def create_supabase_documents(self, data: Dict) -> Dict:
        return {
            "company_info": self._create_company_info(data),
            "products": self._create_products(data.get("products", [])),
            "service_info": self._create_service_info(data),
            "faq_intents": self._create_faqs(data.get("faqs", []))
        }

    def create_meilisearch_documents(self, data: Dict) -> List[Dict]:
        docs = []
        docs.append(self._create_meili_company_info(data))
        docs.extend(self._create_meili_products(data.get("products", [])))
        docs.append(self._create_meili_service_info(data))
        docs.extend(self._create_meili_faqs(data.get("faqs", [])))
        return docs

    def _create_company_info(self, data: Dict) -> Dict:
        return CompanyInfo(
            id=f"company_{self.company_id}",
            searchable_content=f"{data.get('companyName', '')} {data.get('sector', '')} {data.get('description', '')} {data.get('mission', '')} {data.get('activityZone', '')}",
            structured_data={
                "name": data.get("companyName", ""),
                "description": data.get("description", ""),
                "mission": data.get("mission", ""),
                "zone": data.get("activityZone", ""),
                "objective": data.get("objective", ""),
                "contact": {
                    "phone": data.get("supportContact", ""),
                    "hours": data.get("openingHours", "")
                }
            }
        ).dict()

    def _create_products(self, products: List[Dict]) -> List[Dict]:
        product_docs = []
        for prod in products:
            variants = [ProductVariant(**variant).dict() for variant in prod.get("variants", [])]
            product_docs.append(Product(
                id=f"prod_{prod.get('id', '')}",
                searchable_content=f"{prod.get('name', '')} {prod.get('category', '')} {prod.get('subcategory', '')} {prod.get('description', '')}",
                structured_data={
                    "name": prod.get("name", ""),
                    "category": prod.get("category", ""),
                    "subcategory": prod.get("subcategory", ""),
                    "description": prod.get("description", ""),
                    "criticalInfo": prod.get("criticalInfo", ""),
                    "variants": variants
                }
            ).dict())
        return product_docs

    def _create_service_info(self, data: Dict) -> Dict:
        return ServiceInfo(
            id=f"services_{self.company_id}",
            searchable_content="livraison paiement acompte frais délais retour garantie Wave Orange Money Moov MTN",
            structured_data={
                "payment_methods": data.get("payment_methods", []),
                "delivery": data.get("delivery", {}),
                "policies": data.get("policies", {})
            }
        ).dict()

    def _create_faqs(self, faqs: List[Dict]) -> Dict:
        return FAQIntent(
            id=f"faq_{self.company_id}",
            searchable_content=" ".join([f"{faq.get('question', '')} {faq.get('answer', '')}" for faq in faqs]),
            structured_data={"faqs": faqs}
        ).dict()

    def _create_meili_company_info(self, data: Dict) -> Dict:
        return MeiliCompanyInfo(
            id=f"company_info_{self.company_id}",
            title=f"{data.get('companyName', '')} - Informations sur l'entreprise",
            content=f"{data.get('companyName', '')} {data.get('description', '')} {data.get('mission', '')} {data.get('activityZone', '')} {data.get('objective', '')} {data.get('supportContact', '')} {data.get('openingHours', '')}",
            searchable_fields=[
                data.get('companyName', ''),
                data.get('sector', ''),
                'description',
                'mission',
                'contact'
            ]
        ).dict()

    def _create_meili_products(self, products: List[Dict]) -> List[Dict]:
        docs = []
        for prod in products:
            for variant in prod.get("variants", []):
                docs.append(MeiliProduct(
                    id=f"prod_{variant.get('sku', '')}",
                    title=f"{prod.get('name', '')} - {' '.join([f'{k}:{v}' for k, v in variant.get('attributes', {}).items()])}",
                    content=f"{prod.get('name', '')} {prod.get('description', '')} {variant.get('description_specifique', '')} {' '.join(variant.get('attributes', {}).values())}",
                    product_name=prod.get('name', ''),
                    price=variant.get('price', 0),
                    sku=variant.get('sku', ''),
                    stock=variant.get('stock', 0),
                    category=prod.get('category', ''),
                    subcategory=prod.get('subcategory', ''),
                    attributes=variant.get('attributes', {}),
                    searchable_fields=[prod.get('name', ''), *variant.get('attributes', {}).values(), 'description']
                ).dict())
        return docs

    def _create_meili_service_info(self, data: Dict) -> Dict:
        return MeiliServiceInfo(
            id=f"livraison_info_{self.company_id}",
            title="Informations sur la livraison et le transport",
            content=f"{data.get('delivery', {}).get('deliveryZonesFees', '')} {data.get('delivery', {}).get('avgDeliveryTime', '')}",
            category="livraison",
            searchable_fields=["livraison", "transport", "délais", "frais", "expédition", "zones"]
        ).dict()

    def _create_meili_faqs(self, faqs: List[Dict]) -> List[Dict]:
        return [
            MeiliFAQ(
                id=f"faq_{faq.get('id', idx)}",
                title=f"FAQ: {faq.get('question', '')}",
                content=f"{faq.get('question', '')} {faq.get('answer', '')}",
                searchable_fields=[faq.get('question', ''), faq.get('answer', '')]
            ).dict()
            for idx, faq in enumerate(faqs)
        ]

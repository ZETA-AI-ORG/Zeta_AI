#!/usr/bin/env python3
"""
🎯 LLM HYDE POUR INGESTION INTELLIGENTE
Nettoie, structure et optimise les données brutes automatiquement

WORKFLOW:
1. Utilisateur envoie données brutes (n'importe quel format)
2. LLM Hyde analyse et structure
3. Génère documents optimisés pour RAG
4. Indexation parfaite

AVANTAGES:
- Utilisateur: Copier-coller simple
- Système: Données structurées parfaites
- Zero erreur de formatage
"""

import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class StructuredProduct:
    """Produit structuré"""
    name: str
    variants: List[Dict[str, Any]]
    category: str
    description: Optional[str] = None

@dataclass
class StructuredDelivery:
    """Zone de livraison structurée"""
    zone_name: str
    zones_list: List[str]
    price: float
    currency: str
    delay: Optional[str] = None

@dataclass
class StructuredCompany:
    """Info entreprise structurée"""
    name: str
    description: Optional[str] = None
    sector: Optional[str] = None
    contact: Optional[Dict[str, str]] = None
    hours: Optional[str] = None

class LLMHydeIngestion:
    """
    LLM Hyde pour ingestion intelligente
    Transforme données brutes en documents structurés
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Construit le prompt système pour Hyde"""
        
        return """Tu es un expert en structuration de données pour systèmes RAG.

TON RÔLE:
Transformer des données brutes d'entreprise en documents structurés optimisés.

TU DOIS:
1. Identifier le type d'information (produits, livraison, contact, etc.)
2. Corriger les fautes d'orthographe et de grammaire
3. Normaliser les formats (prix, numéros, zones)
4. Créer des documents séparés par thématique
5. Optimiser pour la recherche (mots-clés clairs)

FORMAT DE SORTIE JSON:
{
  "company_info": {
    "name": "...",
    "description": "...",
    "sector": "...",
    "contact": {"phone": "...", "email": "...", "whatsapp": "..."},
    "hours": "..."
  },
  "products": [
    {
      "name": "Nom du produit",
      "category": "categorie",
      "description": "description claire",
      "variants": [
        {
          "quantity": 1,
          "unit": "paquet",
          "price": 5500,
          "currency": "FCFA",
          "unit_price": 5500,
          "description": "1 paquet - 5.500 F CFA"
        }
      ]
    }
  ],
  "delivery": [
    {
      "zone_name": "Zone centrale",
      "zones": ["Cocody", "Yopougon", "Plateau"],
      "price": 1500,
      "currency": "FCFA",
      "delay": "Avant 11h = jour même"
    }
  ],
  "payment": {
    "methods": ["Wave"],
    "deposit_required": true,
    "deposit_amount": 2000,
    "currency": "FCFA"
  },
  "policies": {
    "returns": "Retour sous 24H",
    "warranty": "..."
  }
}

RÈGLES IMPORTANTES:
- Toujours normaliser les prix (retirer espaces, points)
- Toujours séparer les variantes de produits
- Toujours créer des listes pour les zones
- Corriger les fautes (ex: "livraision" → "livraison")
- Uniformiser les formats (ex: "+225 07 87 36 07 57" → "+2250787360757")

RÉPONDS UNIQUEMENT EN JSON, RIEN D'AUTRE."""

    async def structure_raw_data(self, raw_data: str, company_id: str) -> Dict[str, Any]:
        """
        Structure des données brutes avec LLM
        
        Args:
            raw_data: Données brutes (texte libre)
            company_id: ID de l'entreprise
            
        Returns:
            Données structurées en JSON
        """
        
        print(f"\n🧠 LLM HYDE - Structuration des données")
        print(f"📝 Données brutes: {len(raw_data)} caractères")
        print("="*60)
        
        # Construire prompt
        user_prompt = f"""Voici les données brutes d'une entreprise:

```
{raw_data}
```

Structure ces données selon le format JSON spécifié.
Corrige les fautes et optimise pour la recherche."""

        # Appel LLM
        try:
            response = await self.llm_client.complete(
                prompt=f"{self.system_prompt}\n\n{user_prompt}",
                temperature=0.1,  # Basse température pour précision
                max_tokens=4000
            )
            
            print(f"✅ LLM réponse: {len(response)} caractères")
            
            # Parser JSON
            # Extraire JSON si entouré de ```json
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response
            
            structured_data = json.loads(json_str)
            
            print(f"✅ Parsing JSON réussi")
            print(f"   - Produits: {len(structured_data.get('products', []))}")
            print(f"   - Zones livraison: {len(structured_data.get('delivery', []))}")
            
            return structured_data
            
        except json.JSONDecodeError as e:
            print(f"❌ Erreur parsing JSON: {e}")
            print(f"Réponse LLM: {response[:500]}...")
            raise
        
        except Exception as e:
            print(f"❌ Erreur LLM: {e}")
            raise
    
    def structured_to_documents(self, structured_data: Dict[str, Any], company_id: str) -> List[Dict[str, Any]]:
        """
        Convertit données structurées en documents MeiliSearch/Supabase
        
        Args:
            structured_data: Données structurées par LLM
            company_id: ID entreprise
            
        Returns:
            Liste de documents prêts pour indexation
        """
        
        print(f"\n📦 Génération des documents d'indexation")
        print("="*60)
        
        documents = []
        doc_counter = 0
        
        # 1. INFO ENTREPRISE
        if structured_data.get('company_info'):
            doc_counter += 1
            company_info = structured_data['company_info']
            
            content_parts = []
            if company_info.get('name'):
                content_parts.append(f"Entreprise: {company_info['name']}")
            if company_info.get('description'):
                content_parts.append(f"Description: {company_info['description']}")
            if company_info.get('sector'):
                content_parts.append(f"Secteur: {company_info['sector']}")
            
            contact = company_info.get('contact', {})
            if contact:
                if contact.get('phone'):
                    content_parts.append(f"Téléphone: {contact['phone']}")
                if contact.get('whatsapp'):
                    content_parts.append(f"WhatsApp: {contact['whatsapp']}")
                if contact.get('email'):
                    content_parts.append(f"Email: {contact['email']}")
            
            if company_info.get('hours'):
                content_parts.append(f"Horaires: {company_info['hours']}")
            
            doc = {
                "id": f"{company_id}_company_info",
                "company_id": company_id,
                "type": "company_info",
                "content": "\n".join(content_parts),
                "metadata": company_info
            }
            documents.append(doc)
            print(f"   ✅ Doc {doc_counter}: Info entreprise")
        
        # 2. PRODUITS (1 document par variante)
        products = structured_data.get('products', [])
        for product in products:
            product_name = product.get('name', 'Produit')
            
            for variant in product.get('variants', []):
                doc_counter += 1
                
                # Construire contenu optimisé
                quantity = variant.get('quantity', 1)
                unit = variant.get('unit', 'unité')
                price = variant.get('price', 0)
                currency = variant.get('currency', 'FCFA')
                
                content = f"{quantity} {unit} de {product_name} : {price:,} {currency}".replace(',', '.')
                
                if variant.get('unit_price'):
                    content += f" ({variant['unit_price']:,} {currency}/{unit})".replace(',', '.')
                
                doc = {
                    "id": f"{company_id}_product_{doc_counter}",
                    "company_id": company_id,
                    "type": "pricing",
                    "product": product_name,
                    "category": product.get('category', 'produits'),
                    "quantity": quantity,
                    "unit": unit,
                    "price": price,
                    "currency": currency,
                    "content": content,
                    "searchable": f"{quantity} {unit} {product_name} {price} {currency}"
                }
                
                documents.append(doc)
                print(f"   ✅ Doc {doc_counter}: {content}")
        
        # 3. LIVRAISON (1 document par zone)
        delivery_zones = structured_data.get('delivery', [])
        for zone_info in delivery_zones:
            doc_counter += 1
            
            zone_name = zone_info.get('zone_name', 'Zone')
            zones = zone_info.get('zones', [])
            price = zone_info.get('price', 0)
            currency = zone_info.get('currency', 'FCFA')
            
            content_parts = [
                f"Livraison {zone_name}: {price:,} {currency}".replace(',', '.'),
                f"Zones couvertes: {', '.join(zones)}"
            ]
            
            if zone_info.get('delay'):
                content_parts.append(f"Délai: {zone_info['delay']}")
            
            doc = {
                "id": f"{company_id}_delivery_{doc_counter}",
                "company_id": company_id,
                "type": "delivery",
                "zone_name": zone_name,
                "zones": zones,
                "price": price,
                "currency": currency,
                "content": "\n".join(content_parts),
                "searchable": f"livraison {zone_name} {' '.join(zones)} {price} {currency}"
            }
            
            documents.append(doc)
            print(f"   ✅ Doc {doc_counter}: Livraison {zone_name}")
        
        # 4. PAIEMENT
        if structured_data.get('payment'):
            doc_counter += 1
            payment = structured_data['payment']
            
            content_parts = []
            if payment.get('methods'):
                content_parts.append(f"Moyens de paiement: {', '.join(payment['methods'])}")
            
            if payment.get('deposit_required'):
                deposit = payment.get('deposit_amount', 0)
                currency = payment.get('currency', 'FCFA')
                content_parts.append(f"Acompte obligatoire: {deposit:,} {currency}".replace(',', '.'))
            
            doc = {
                "id": f"{company_id}_payment",
                "company_id": company_id,
                "type": "payment",
                "content": "\n".join(content_parts),
                "metadata": payment
            }
            
            documents.append(doc)
            print(f"   ✅ Doc {doc_counter}: Paiement")
        
        # 5. POLITIQUES
        if structured_data.get('policies'):
            doc_counter += 1
            policies = structured_data['policies']
            
            content_parts = []
            if policies.get('returns'):
                content_parts.append(f"Retours: {policies['returns']}")
            if policies.get('warranty'):
                content_parts.append(f"Garantie: {policies['warranty']}")
            
            if content_parts:
                doc = {
                    "id": f"{company_id}_policies",
                    "company_id": company_id,
                    "type": "policies",
                    "content": "\n".join(content_parts),
                    "metadata": policies
                }
                
                documents.append(doc)
                print(f"   ✅ Doc {doc_counter}: Politiques")
        
        print("="*60)
        print(f"📊 Total: {len(documents)} documents générés")
        
        return documents
    
    async def process_raw_ingestion(self, raw_data: str, company_id: str) -> List[Dict[str, Any]]:
        """
        Pipeline complet: données brutes → documents indexables
        
        Args:
            raw_data: Données brutes (texte libre)
            company_id: ID entreprise
            
        Returns:
            Documents prêts pour MeiliSearch + Supabase
        """
        
        print(f"\n🚀 PIPELINE LLM HYDE - INGESTION INTELLIGENTE")
        print(f"🏢 Company: {company_id}")
        print("="*60)
        
        # Étape 1: Structuration LLM
        structured_data = await self.structure_raw_data(raw_data, company_id)
        
        # Étape 2: Conversion en documents
        documents = self.structured_to_documents(structured_data, company_id)
        
        print("\n✅ PIPELINE TERMINÉ")
        print(f"📦 {len(documents)} documents prêts à indexer")
        print("="*60)
        
        return documents


# Factory function
def get_llm_hyde_ingestion(llm_client) -> LLMHydeIngestion:
    """Créée instance LLM Hyde"""
    return LLMHydeIngestion(llm_client)


# Fonction standalone pour ingestion_api.py
async def clean_document_with_hyde(
    content: str,
    doc_type: str,
    company_id: str,
    llm_client
) -> str:
    """
    Nettoie un document avec LLM selon son type
    Version standalone pour intégration dans ingestion_api.py
    
    Args:
        content: Contenu brut (peut avoir fautes, formats incohérents)
        doc_type: Type de document (products_catalog, delivery, etc.)
        company_id: ID entreprise
        llm_client: Client LLM
        
    Returns:
        Contenu nettoyé et structuré
    """
    
    # Prompts spécialisés par type
    prompts_by_type = {
        "products_catalog": """Tu es un expert en structuration de catalogues produits.

TÂCHE: Analyser le catalogue et créer UN DOCUMENT SÉPARÉ pour CHAQUE prix/variante.

DIRECTIVES:
1. Corriger les fautes d'orthographe
2. Identifier tous les produits et leurs variantes
3. Pour CHAQUE variante/prix, créer une entrée séparée
4. Garder TOUS les prix (ne rien omettre)
5. ATTENTION: Si une ligne contient "prix/unité | prix total", prendre le PRIX TOTAL (après le |)

FORMAT DE SORTIE (JSON Array):
```json
[
  {
    "product": "Nom du produit",
    "variant": "description de la variante (ex: 6 paquets, Taille 3, etc.)",
    "price": 25000,
    "unit": "paquet/kg/litre/etc",
    "quantity": 6
  },
  ...
]
```

RÈGLES IMPORTANTES:
- 1 variante = 1 objet JSON
- Extraire TOUS les prix
- Format "X F CFA/unité | Y F CFA/paquet" → prendre Y (le prix total)
- Format "X paquets - Y F CFA" → prendre Y
- Ne rien inventer, juste structurer ce qui existe""",

        "delivery": """Tu es un expert en nettoyage d'informations de livraison.

TÂCHE: Nettoyer et clarifier les informations de livraison.

DIRECTIVES:
1. Corriger les fautes d'orthographe
2. Normaliser les noms de zones/villes
3. Uniformiser les formats de prix (ex: "1500 FCFA")
4. Clarifier les délais
5. Garder la structure originale

RÉPONDS UNIQUEMENT avec le contenu nettoyé, sans commentaires.""",

        "company_identity": """Tu es un expert en nettoyage d'informations d'entreprise.

TÂCHE: Nettoyer et clarifier les informations de l'entreprise.

DIRECTIVES:
1. Corriger les fautes d'orthographe
2. Améliorer la clarté de la description
3. Garder toutes les informations importantes
4. Conserver la structure originale

RÉPONDS UNIQUEMENT avec le contenu nettoyé, sans commentaires.""",
        
        "support": """Tu es un expert en nettoyage d'informations de support client.

TÂCHE: Nettoyer et clarifier les informations de support.

DIRECTIVES:
1. Corriger les fautes
2. Formater correctement les numéros de téléphone
3. Clarifier les horaires
4. Garder la structure originale

RÉPONDS UNIQUEMENT avec le contenu nettoyé, sans commentaires.""",
        
        "payment": """Tu es un expert en nettoyage d'informations de paiement.

TÂCHE: Nettoyer et clarifier le processus de paiement.

DIRECTIVES:
1. Corriger les fautes
2. Clarifier les étapes du processus
3. Uniformiser les formats de prix
4. Garder la structure originale

RÉPONDS UNIQUEMENT avec le contenu nettoyé, sans commentaires.""",
        
        "location": """Tu es un expert en nettoyage d'informations de localisation.

TÂCHE: Nettoyer et clarifier les informations de localisation.

DIRECTIVES:
1. Corriger les fautes dans les noms de lieux
2. Uniformiser les formats d'adresse
3. Garder la structure originale

RÉPONDS UNIQUEMENT avec le contenu nettoyé, sans commentaires."""
    }
    
    # Sélectionner prompt selon type
    doc_type_lower = doc_type.lower()
    system_prompt = None
    
    # Mapping précis des types vers prompts
    if "product" in doc_type_lower or "catalog" in doc_type_lower:
        system_prompt = prompts_by_type["products_catalog"]
    elif "delivery" in doc_type_lower or "livraison" in doc_type_lower:
        system_prompt = prompts_by_type["delivery"]
    elif "support" in doc_type_lower or "customer" in doc_type_lower:
        system_prompt = prompts_by_type["support"]
    elif "payment" in doc_type_lower or "paiement" in doc_type_lower:
        system_prompt = prompts_by_type["payment"]
    elif "location" in doc_type_lower or "localisation" in doc_type_lower:
        system_prompt = prompts_by_type["location"]
    elif "company" in doc_type_lower or "identity" in doc_type_lower:
        system_prompt = prompts_by_type["company_identity"]
    else:
        # Fallback: prompt générique pour nettoyage basique
        system_prompt = """Tu es un expert en nettoyage de contenu.

TÂCHE: Corriger les fautes d'orthographe et améliorer la clarté du texte.

DIRECTIVES:
1. Corriger les fautes
2. Améliorer la lisibilité
3. Garder toutes les informations
4. Conserver la structure originale

RÉPONDS UNIQUEMENT avec le contenu nettoyé, sans commentaires."""
    
    # Construire prompt complet
    full_prompt = f"""{system_prompt}

CONTENU À NETTOYER:
```
{content}
```

RÉPONDS UNIQUEMENT AVEC LE CONTENU NETTOYÉ, RIEN D'AUTRE."""
    
    try:
        # Appel LLM - Utilise 8B (rapide + économique pour nettoyage)
        cleaned = await llm_client.complete(
            prompt=full_prompt,
            model_name="llama-3.1-8b-instant",  # 8B suffisant pour structuration
            temperature=0.1,  # Basse température pour précision
            max_tokens=2000
        )
        
        return cleaned.strip()
        
    except Exception as e:
        print(f"⚠️ Erreur LLM Hyde: {e}, contenu original conservé")
        return content  # Fallback: garder original

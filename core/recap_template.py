#!/usr/bin/env python3
"""
📋 TEMPLATE DE RÉCAPITULATIF STRUCTURÉ RUE DU GROS
Système de génération de récapitulatifs de commande professionnels
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import re

class UniversalRecapTemplate:
    """Générateur de récapitulatifs universel pour toutes les entreprises"""
    
    def __init__(self, company_id: str = None):
        self.company_id = company_id
        self.company_info = {}
        self._load_company_info()
    
    def _load_company_info(self):
        """Charge les informations de l'entreprise depuis la base de données"""
        if not self.company_id:
            self.company_info = {
                "name": "Entreprise",
                "assistant": "Assistant IA",
                "sector": "Non spécifié",
                "zone": "Non spécifiée",
                "phone": "Non fourni",
                "whatsapp": "Non fourni",
                "payment": "À confirmer",
                "deposit_required": 0
            }
            return
        
        try:
            # Extraction dynamique des informations depuis MeiliSearch
            payment_info = self._extract_payment_info()
            company_identity = self._extract_company_identity()
            
            # Extraire les informations de l'entreprise
            self.company_info = {
                "name": company_identity.get("name", "Entreprise"),
                "assistant": company_identity.get("assistant", "Assistant IA"),
                "sector": company_identity.get("sector", "Non spécifié"),
                "zone": company_identity.get("zone", "Non spécifiée"),
                "phone": payment_info.get("phone", "Non fourni"),
                "whatsapp": payment_info.get("whatsapp", "Non fourni"),
                "payment": payment_info.get("method", "À confirmer"),
                "deposit_required": payment_info.get("deposit_required", 0)
            }
            
        except Exception as e:
            print(f"[RECAP_TEMPLATE] ❌ Erreur chargement infos entreprise: {e}")
            # Valeurs par défaut
            self.company_info = {
                "name": "Entreprise",
                "assistant": "Assistant IA",
                "sector": "Non spécifié",
                "zone": "Non spécifiée",
                "phone": "Non fourni",
                "whatsapp": "Non fourni",
                "payment": "À confirmer",
                "deposit_required": 0
            }
    
    def _extract_payment_info(self) -> Dict[str, Any]:
        """Extrait dynamiquement les informations de paiement depuis MeiliSearch"""
        try:
            from database.vector_store import search_meili_keywords
            
            # Rechercher les informations de paiement
            results = search_meili_keywords(
                query="paiement acompte wave mode",
                company_id=self.company_id,
                limit=5
            )
            
            payment_info = {
                "method": "À confirmer",
                "phone": "Non fourni",
                "whatsapp": "Non fourni", 
                "deposit_required": 0
            }
            
            # Vérification du type de retour de MeiliSearch
            if isinstance(results, str):
                results = []
            elif not isinstance(results, list):
                results = []
            
            for result in results:
                if not isinstance(result, dict):
                    continue
                content = result.get("content", "").lower()
                
                # Extraire le mode de paiement
                if "wave" in content:
                    payment_info["method"] = "Wave"
                elif "orange money" in content:
                    payment_info["method"] = "Orange Money"
                elif "mtn money" in content:
                    payment_info["method"] = "MTN Money"
                
                # Extraire l'acompte de manière dynamique
                acompte_patterns = [
                    r"acompte.*?(\d+).*?fcfa",
                    r"(\d+).*?fcfa.*?acompte",
                    r"condition.*?(\d+).*?fcfa",
                    r"un acompte de (\d+) fcfa",
                    r"acompte de (\d+) fcfa",
                    r"condition de commande.*?(\d+) fcfa"
                ]
                
                for pattern in acompte_patterns:
                    match = re.search(pattern, content)
                    if match:
                        try:
                            amount = int(match.group(1))
                            if 500 <= amount <= 50000:  # Validation range réaliste
                                payment_info["deposit_required"] = amount
                                break
                        except:
                            continue
                
                # Extraire les numéros de téléphone
                phone_patterns = [
                    r"\+225(\d{10})",
                    r"(\d{10})",
                    r"0(\d{9})"
                ]
                
                for pattern in phone_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        phone = match if len(match) == 10 else f"225{match}"
                        if payment_info["phone"] == "Non fourni":
                            payment_info["phone"] = f"+{phone}"
                        elif payment_info["whatsapp"] == "Non fourni":
                            payment_info["whatsapp"] = f"+{phone}"
            
            return payment_info
            
        except Exception as e:
            print(f"[RECAP_TEMPLATE] ❌ Erreur extraction paiement: {e}")
            return {
                "method": "À confirmer",
                "phone": "Non fourni",
                "whatsapp": "Non fourni",
                "deposit_required": 0
            }
    
    def _extract_company_identity(self) -> Dict[str, Any]:
        """Extrait dynamiquement l'identité de l'entreprise depuis MeiliSearch"""
        try:
            from database.vector_store import search_meili_keywords
            
            # Rechercher les informations d'identité
            results = search_meili_keywords(
                query="entreprise nom assistant secteur zone",
                company_id=self.company_id,
                limit=5
            )
            
            identity = {
                "name": "Entreprise",
                "assistant": "Assistant IA",
                "sector": "Non spécifié",
                "zone": "Non spécifiée"
            }
            
            # Vérification du type de retour de MeiliSearch
            if isinstance(results, str):
                results = []
            elif not isinstance(results, list):
                results = []
            
            for result in results:
                if not isinstance(result, dict):
                    continue
                content = result.get("content", "")
                lines = content.split('\n')
                
                for line in lines:
                    line_lower = line.lower().strip()
                    
                    # Extraire le nom de l'entreprise
                    if "nom:" in line_lower and identity["name"] == "Entreprise":
                        name = line.split(':')[1].strip()
                        if name and len(name) > 2:
                            identity["name"] = name
                    
                    # Extraire l'assistant
                    if "assistant" in line_lower and identity["assistant"] == "Assistant IA":
                        if ":" in line:
                            assistant = line.split(':')[1].strip()
                            if assistant and len(assistant) > 1:
                                identity["assistant"] = assistant
                        elif "gamma" in line_lower:
                            identity["assistant"] = "Gamma"
                    
                    # Extraire le secteur
                    if "secteur:" in line_lower and identity["sector"] == "Non spécifié":
                        sector = line.split(':')[1].strip()
                        if sector and len(sector) > 2:
                            identity["sector"] = sector
                    
                    # Extraire la zone
                    if "zone" in line_lower and identity["zone"] == "Non spécifiée":
                        if "côte d'ivoire" in line_lower:
                            identity["zone"] = "Côte d'Ivoire"
                        elif ":" in line:
                            zone = line.split(':')[1].strip()
                            if zone and len(zone) > 2:
                                identity["zone"] = zone
            
            return identity
            
        except Exception as e:
            print(f"[RECAP_TEMPLATE] ❌ Erreur extraction identité: {e}")
            return {
                "name": "Entreprise",
                "assistant": "Assistant IA", 
                "sector": "Non spécifié",
                "zone": "Non spécifiée"
            }

    def _extract_company_name(self) -> str:
        """Extrait le nom de l'entreprise depuis la base de données"""
        try:
            from database.vector_store_clean import search_meili_keywords
            
            results = search_meili_keywords(
                query="entreprise nom société",
                company_id=self.company_id,
                limit=3
            )
            
            for result in results:
                content = result.get("content", "")
                if "nom:" in content.lower() or "entreprise:" in content.lower():
                    # Extraire le nom après ":"
                    lines = content.split('\n')
                    for line in lines:
                        if "nom:" in line.lower() or "entreprise:" in line.lower():
                            name = line.split(':')[1].strip()
                            if name and len(name) > 2:
                                return name
            
            return "Entreprise"
            
        except Exception:
            return "Entreprise"
    
    def _extract_assistant_name(self) -> str:
        """Extrait le nom de l'assistant depuis la base de données"""
        try:
            from database.vector_store_clean import search_meili_keywords
            
            results = search_meili_keywords(
                query="assistant gamma nom",
                company_id=self.company_id,
                limit=3
            )
            
            for result in results:
                content = result.get("content", "")
                if "assistant:" in content.lower() or "gamma" in content.lower():
                    # Extraire le nom de l'assistant
                    lines = content.split('\n')
                    for line in lines:
                        if "assistant:" in line.lower():
                            name = line.split(':')[1].strip()
                            if name and len(name) > 2:
                                return name
                        elif "gamma" in line.lower():
                            return "Gamma"
            
            return "Assistant IA"
            
        except Exception:
            return "Assistant IA"
    
    def _extract_sector(self) -> str:
        """Extrait le secteur d'activité depuis la base de données"""
        try:
            from database.vector_store_clean import search_meili_keywords
            
            results = search_meili_keywords(
                query="secteur activité domaine",
                company_id=self.company_id,
                limit=3
            )
            
            for result in results:
                content = result.get("content", "")
                if "secteur:" in content.lower():
                    sector = content.split("secteur:")[1].split('\n')[0].strip()
                    if sector and len(sector) > 2:
                        return sector
            
            return "Non spécifié"
            
        except Exception:
            return "Non spécifié"
    
    def _extract_zone(self) -> str:
        """Extrait la zone d'activité depuis la base de données"""
        try:
            from database.vector_store_clean import search_meili_keywords
            
            results = search_meili_keywords(
                query="zone activité localisation",
                company_id=self.company_id,
                limit=3
            )
            
            for result in results:
                content = result.get("content", "")
                if "zone" in content.lower() and "côte" in content.lower():
                    return "Côte d'Ivoire"
                elif "zone" in content.lower():
                    # Extraire la zone
                    lines = content.split('\n')
                    for line in lines:
                        if "zone" in line.lower() and len(line) > 10:
                            return line.strip()
            
            return "Non spécifiée"
            
        except Exception:
            return "Non spécifiée"
    
    def generate_order_recap(self, 
                           customer_info: Dict[str, Any],
                           products: List[Dict[str, Any]],
                           delivery_info: Dict[str, Any],
                           price_info: Dict[str, Any]) -> str:
        """Génère un récapitulatif complet de commande"""
        
        recap = f"""
🏢 **RÉCAPITULATIF DE COMMANDE - {self.company_info['name']}**
{'='*60}

👤 **INFORMATIONS CLIENT :**
   • Nom : {customer_info.get('name', 'Non fourni')}
   • Téléphone : {customer_info.get('phone', 'Non fourni')}
   • Zone de livraison : {delivery_info.get('zone', 'Non spécifiée')}
   • Adresse : {delivery_info.get('address', 'Non fournie')}

📦 **PRODUITS COMMANDÉS :**
"""
        
        # Détail des produits
        for i, product in enumerate(products, 1):
            recap += f"""
   **Produit {i} :** {product.get('description', 'Produit non spécifié')}
   • Type : {product.get('type', 'Non spécifié')}
   • Taille : {product.get('size', 'Non spécifiée')}
   • Quantité : {product.get('quantity', 1)}
   • Prix unitaire : {product.get('unit_price', 0):,.0f} FCFA
   • Sous-total : {product.get('total_price', 0):,.0f} FCFA
"""
        
        # Récapitulatif financier
        recap += f"""
💰 **RÉCAPITULATIF FINANCIER :**
   • Sous-total produits : {price_info.get('subtotal', 0):,.0f} FCFA
   • Frais de livraison : {price_info.get('delivery_cost', 0):,.0f} FCFA
   • **TOTAL À PAYER : {price_info.get('total', 0):,.0f} FCFA**

💳 **CONDITIONS DE PAIEMENT :**
   • Mode de paiement : {self.company_info['payment']}
   • Acompte requis : {self.company_info['deposit_required']:,.0f} FCFA
   • Reste à payer : {price_info.get('total', 0) - self.company_info['deposit_required']:,.0f} FCFA

🚚 **INFORMATIONS DE LIVRAISON :**
   • Zone : {delivery_info.get('zone', 'Non spécifiée')}
   • Délai : {delivery_info.get('delivery_time', 'À confirmer')}
   • Adresse : {delivery_info.get('address', 'À confirmer')}

📞 **CONTACT :**
   • Téléphone : {self.company_info['phone']}
   • WhatsApp : {self.company_info['whatsapp']}

⏰ **PROCHAINES ÉTAPES :**
   1. Effectuer l'acompte de {self.company_info['deposit_required']:,.0f} FCFA via Wave
   2. Confirmer le paiement par téléphone/WhatsApp
   3. Recevoir la confirmation de commande
   4. Attendre la livraison selon les délais indiqués

{'='*60}
✅ **Merci pour votre confiance ! Votre commande sera traitée dans les plus brefs délais.**
"""
        
        return recap.strip()
    
    def generate_simple_recap(self, 
                             products: List[Dict[str, Any]], 
                             price_info: Dict[str, Any]) -> str:
        """Génère un récapitulatif simplifié"""
        
        recap = f"""
🧮 **RÉCAPITULATIF RAPIDE :**

📦 **Produits :**
"""
        
        for product in products:
            recap += f"   • {product.get('description', 'Produit')} : {product.get('total_price', 0):,.0f} FCFA\n"
        
        recap += f"""
💰 **Total :**
   • Produits : {price_info.get('subtotal', 0):,.0f} FCFA
   • Livraison : {price_info.get('delivery_cost', 0):,.0f} FCFA
   • **TOTAL : {price_info.get('total', 0):,.0f} FCFA**

💳 **Acompte requis : 2.000 FCFA**
"""
        
        return recap.strip()
    
    def generate_price_breakdown(self, price_info: Dict[str, Any]) -> str:
        """Génère un détail des prix uniquement"""
        
        if not price_info or not price_info.get('products'):
            return "❌ Aucune information de prix disponible"
        
        breakdown = f"""
🧮 **DÉTAIL DES PRIX :**

"""
        
        for i, product in enumerate(price_info['products'], 1):
            breakdown += f"**{i}. {product.get('description', 'Produit')}**\n"
            breakdown += f"   • Quantité : {product.get('quantity', 1)}\n"
            breakdown += f"   • Prix unitaire : {product.get('unit_price', 0):,.0f} FCFA\n"
            breakdown += f"   • Sous-total : {product.get('total_price', 0):,.0f} FCFA\n\n"
        
        breakdown += f"""
📊 **RÉCAPITULATIF :**
   • Sous-total produits : {price_info.get('subtotal', 0):,.0f} FCFA
   • Frais de livraison : {price_info.get('delivery_cost', 0):,.0f} FCFA
   • **TOTAL À PAYER : {price_info.get('total', 0):,.0f} FCFA**
"""
        
        return breakdown.strip()
    
    def generate_confirmation_message(self, 
                                    customer_name: str = None,
                                    total_amount: float = 0) -> str:
        """Génère un message de confirmation de commande"""
        
        name_part = f" {customer_name}" if customer_name else ""
        
        confirmation = f"""
✅ **COMMANDE CONFIRMÉE{name_part} !**

Votre commande d'un montant de **{total_amount:,.0f} FCFA** a été enregistrée avec succès.

**Prochaines étapes :**
1. Effectuez l'acompte de **2.000 FCFA** via Wave (+2250787360757)
2. Confirmez le paiement par téléphone ou WhatsApp
3. Recevez votre commande selon les délais de livraison

**Contact :**
📞 {self.company_info['phone']}
💬 WhatsApp : {self.company_info['whatsapp']}

Merci pour votre confiance ! 🎉
"""
        
        return confirmation.strip()
    
    def generate_delivery_info(self, zone: str, delivery_cost: float, delivery_time: str) -> str:
        """Génère les informations de livraison"""
        
        delivery_info = f"""
🚚 **INFORMATIONS DE LIVRAISON :**

📍 **Zone :** {zone}
💰 **Coût :** {delivery_cost:,.0f} FCFA
⏰ **Délai :** {delivery_time}

**Zones couvertes :**
• **Zones centrales** (1.500 FCFA) : Yopougon, Cocody, Plateau, Adjamé, Abobo, Marcory, Koumassi, Treichville, Angré, Riviera
• **Zones périphériques** (2.000-2.500 FCFA) : Port-Bouët, Attécoubé, Bingerville, Songon, Anyama, Brofodoumé, Grand-Bassam, Dabou
• **Hors Abidjan** (3.500-5.000 FCFA) : Autres villes de Côte d'Ivoire
"""
        
        return delivery_info.strip()

# Cache des générateurs de récapitulatifs par entreprise
_recap_generator_cache = {}

def get_recap_generator(company_id: str) -> UniversalRecapTemplate:
    """Obtient ou crée un générateur de récapitulatif pour une entreprise"""
    if company_id not in _recap_generator_cache:
        _recap_generator_cache[company_id] = UniversalRecapTemplate(company_id)
    return _recap_generator_cache[company_id]

def generate_order_summary(customer_info: Dict[str, Any],
                          products: List[Dict[str, Any]],
                          delivery_info: Dict[str, Any],
                          price_info: Dict[str, Any],
                          company_id: str,
                          summary_type: str = "full") -> str:
    """
    Fonction principale pour générer un récapitulatif de commande
    
    Args:
        customer_info: Informations du client (nom, téléphone, etc.)
        products: Liste des produits commandés
        delivery_info: Informations de livraison
        price_info: Informations de prix calculées
        company_id: ID de l'entreprise
        summary_type: Type de récapitulatif ("full", "simple", "price_only")
    
    Returns:
        Récapitulatif formaté
    """
    
    recap_generator = get_recap_generator(company_id)
    
    if summary_type == "full":
        return recap_generator.generate_order_recap(customer_info, products, delivery_info, price_info)
    elif summary_type == "simple":
        return recap_generator.generate_simple_recap(products, price_info)
    elif summary_type == "price_only":
        return recap_generator.generate_price_breakdown(price_info)
    else:
        return recap_generator.generate_order_recap(customer_info, products, delivery_info, price_info)

def extract_customer_info_from_conversation(conversation_history: List[Dict]) -> Dict[str, Any]:
    """
    Extrait les informations du client de l'historique de conversation
    """
    customer_info = {
        "name": None,
        "phone": None,
        "address": None
    }
    
    for message in reversed(conversation_history):  # Commencer par les plus récents
        text = message.get("message", "").lower()
        
        # Extraire le nom
        if not customer_info["name"]:
            name_patterns = ["mon nom c'est", "je m'appelle", "je suis", "nom:", "prénom:"]
            for pattern in name_patterns:
                if pattern in text:
                    # Extraire le nom après le pattern
                    start_idx = text.find(pattern) + len(pattern)
                    name_part = text[start_idx:].strip()
                    # Prendre le premier mot comme nom
                    name = name_part.split()[0] if name_part.split() else None
                    if name and len(name) > 2:
                        customer_info["name"] = name.title()
                        break
        
        # Extraire le téléphone
        if not customer_info["phone"]:
            phone_patterns = [
                r'(\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2})',
                r'(\+225[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2})',
                r'(0\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2})'
            ]
            
            for pattern in phone_patterns:
                match = re.search(pattern, text)
                if match:
                    phone = match.group(1).replace(" ", "").replace("-", "").replace(".", "")
                    if len(phone) >= 10:
                        customer_info["phone"] = phone
                        break
        
        # Extraire l'adresse
        if not customer_info["address"]:
            address_keywords = ["adresse", "habite", "réside", "cocody", "yopougon", "plateau", "adjamé", "abobo", "marcory"]
            if any(keyword in text for keyword in address_keywords):
                customer_info["address"] = message.get("message", "").strip()
    
    return customer_info

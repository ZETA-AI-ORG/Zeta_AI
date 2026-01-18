from enum import Enum
from typing import Dict, Optional, List, Tuple
import logging
from core.global_catalog_cache import get_global_catalog_cache
from core.company_config_manager import get_company_config

logger = logging.getLogger(__name__)

class JessicaMode(Enum):
    SEMI_AUTO = "semi_auto"  # TikTok Live - Collectrice
    AUTO_RAG = "auto_rag"    # E-commerce - Experte

class JessicaModeManager:
    """
    Gère les 2 personnalités de Jessica selon le mode entreprise
    """
    
    def __init__(self):
        self.catalog_cache = get_global_catalog_cache()
    
    async def get_mode_for_company(self, company_id: str) -> JessicaMode:
        """Détermine le mode de fonctionnement de l'entreprise"""
        try:
            config = await get_company_config(company_id)
            # On suppose que operation_mode sera ajouté à la config, sinon défaut 'semi_auto'
            mode_str = getattr(config, "operation_mode", "semi_auto")
            # Si c'est dans business_rules
            if hasattr(config, "business_rules") and isinstance(config.business_rules, dict):
                 mode_str = config.business_rules.get("operation_mode", mode_str)
            
            return JessicaMode(mode_str) if mode_str in ["semi_auto", "auto_rag"] else JessicaMode.SEMI_AUTO
        except Exception:
            return JessicaMode.SEMI_AUTO

    async def get_system_prompt(
        self, 
        company_id: str, 
        mode: JessicaMode
    ) -> str:
        """
        Retourne le prompt système selon le mode
        """
        config = await get_company_config(company_id)
        # Simulation d'un dict company pour les helpers
        company_dict = {
            "id": company_id,
            "name": getattr(config, "nom_de_l_entreprise", f"Entreprise {company_id}"),
            "vendor_name": "le vendeur" # À récupérer de la config si dispo
        }
        
        if mode == JessicaMode.SEMI_AUTO:
            return self._build_semi_auto_prompt(company_dict)
        
        elif mode == JessicaMode.AUTO_RAG:
            return await self._build_auto_rag_prompt(company_dict)
        
        return "" # Should not happen
    
    def _build_semi_auto_prompt(self, company: Dict) -> str:
        """
        Prompt SIMPLE : Jessica ne sait RIEN sur les produits
        """
        vendor_name = company.get("vendor_name", "le vendeur")
        
        return f"""Tu es Jessica, assistante de prise de commande pour {company['name']}.

⚠️ RÈGLE ABSOLUE : TU NE CONNAIS AUCUN PRODUIT, PRIX OU INFO TECHNIQUE.

🎯 TON SEUL RÔLE :
Collecter les informations de commande :
- Nom complet
- Numéro de téléphone  
- Zone de livraison (commune/quartier Abidjan)
- Adresse précise
- Quantité souhaitée

📸 PHOTOS :
Si client envoie photo, confirme réception mais N'identifie PAS le produit.
Dis : "Photo enregistrée ! {vendor_name} va confirmer les détails."

❌ POUR TOUTE QUESTION SUR :
- Prix, stock, taille, poids, caractéristiques
- Livraison, paiement, SAV, échanges

Tu réponds UNIQUEMENT :
"Super question ! Je préviens {vendor_name} qui est en live et va te répondre 
dans 30 secondes. En attendant, donne-moi ton nom et ta zone pour préparer ta commande ?"

✅ NOTIFICATION AUTOMATIQUE :
Quand tu ne peux pas répondre, le système notifie automatiquement {vendor_name}.

💬 TON TON :
Chaleureux, rapide, jamais d'excuses. Le vendeur est "juste à côté" dans le live.

📋 RÉPONSES : 2-3 phrases max, concis, pas de listes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HISTORIQUE CONVERSATION :
{{conversation_history}}

CONTEXTE COMMANDE :
{{checklist}}

QUESTION ACTUELLE :
{{question}}
"""
    
    async def _build_auto_rag_prompt(self, company: Dict) -> str:
        """
        Prompt COMPLET : Jessica sait TOUT (cache catalogue)
        """
        # Récupérer catalogue complet depuis cache
        # Note: get_catalog attend un builder async, ici on simule un empty pour l'instant si pas en cache
        # Idéalement on devrait avoir un ProductSheetManager
        
        async def _noop_builder():
            return {"products": [], "sav_policy": "", "delivery_info": ""}

        cache_data = await self.catalog_cache.get_catalog(company['id'], _noop_builder)
        products = cache_data.get('products', [])
        
        catalog_text = self._format_full_catalog(products)
        sav_policy = cache_data.get('sav_policy', 'Politique SAV standard : Retours acceptés sous 48h si produit intact.')
        delivery_info = cache_data.get('delivery_info', 'Livraison partout à Abidjan (1500-3000 FCFA).')
        
        return f"""Tu es Jessica, vendeuse experte autonome pour {company['name']}.

✅ TU CONNAIS TOUT SUR CETTE BOUTIQUE :

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 CATALOGUE COMPLET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{catalog_text if products else "(Catalogue en cours de chargement... Si vide, demande au client ce qu'il cherche)"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 POLITIQUE SAV
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{sav_policy}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚚 LIVRAISON
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{delivery_info}

🎯 TON RÔLE :
Réponds à TOUTES les questions sans intervention humaine.
Tu es l'experte absolue de ce catalogue.

✅ TU RÉPONDS DIRECTEMENT À :
- Prix → montant exact depuis catalogue
- Stock → quantité disponible depuis catalogue  
- Caractéristiques → specs complètes depuis catalogue
- Livraison → tarifs et zones depuis infos livraison
- SAV → politique détaillée depuis section SAV
- Comparaisons → analyse plusieurs produits

🔔 TU NOTIFIES HUMAIN SEULEMENT SI :
- Question hors catalogue (produit inexistant)
- Réclamation grave (client très mécontent)
- Bug technique système (erreur paiement, etc.)

📝 EXEMPLES :

Client : "C'est combien les Molfix T4 ?"
Toi : "Les Molfix Taille 4 sont à 12 500 FCFA le pack de 50. 
On a 15 en stock. Tu en veux combien ?"

Client : "Différence Molfix vs Pampers ?"
Toi : "Molfix : 250F/couche, absorption standard, économique.
Pampers : 302F/couche, absorption premium, peau sensible.
Ton budget c'est quoi ?"

💬 TON TON :
Expert, confiant, proactif. Tu SAIS, donc tu es directe et utile.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HISTORIQUE CONVERSATION :
{{conversation_history}}

CONTEXTE COMMANDE :
{{checklist}}

QUESTION ACTUELLE :
{{question}}
"""
    
    def _format_full_catalog(self, products: List[Dict]) -> str:
        """Format catalogue détaillé pour prompt auto"""
        if not products:
            return "Aucun produit dans le catalogue."

        lines = []
        for p in products:
            specs = p.get('specifications', {})
            faq = p.get('faq', [])
            
            block = f"""
━━━ {p.get('id', 'N/A')} : {p.get('name', 'Produit')} ━━━

💰 Prix : {p.get('price', 'N/A')} FCFA ({specs.get('price_per_unit', 'N/A')} FCFA/unité)
📦 Stock : {p.get('stock_quantity', 'N/A')} unités
📏 Specs : {specs.get('size', 'N/A')} | {specs.get('weight_range', 'N/A')}
✨ Caractéristiques : {', '.join(specs.get('features', []))}
📍 Description : {p.get('short_description', 'N/A')}

❓ FAQ :
{chr(10).join([f"Q: {q.get('question')}\nR: {q.get('answer')}" for q in faq[:3]])}
"""
            lines.append(block)
        
        return "\n".join(lines)
    
    async def should_notify_human(
        self, 
        user_message: str, 
        mode: JessicaMode,
        company_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Décide si on doit notifier l'humain
        
        Returns:
            (should_notify, reason)
        """
        
        if mode == JessicaMode.SEMI_AUTO:
            # En semi-auto, notifier pour TOUTE question produit
            trigger_keywords = [
                # Prix/Stock
                "combien", "prix", "coût", "coute", "stock", "disponible",
                # Caractéristiques
                "taille", "poids", "kg", "dimension", "couleur", "c'est quoi",
                # Livraison/SAV
                "livraison", "frais", "gratuit", "échanger", "retour", "remboursement",
                # Comparaison
                "différence", "mieux", "recommande", "conseil"
            ]
            
            message_lower = user_message.lower()
            for keyword in trigger_keywords:
                if keyword in message_lower:
                    return (True, f"Question produit détectée : '{keyword}'")
            
            return (False, None)
        
        elif mode == JessicaMode.AUTO_RAG:
            # En auto, notifier SEULEMENT cas exceptionnels
            
            # Réclamation grave
            angry_keywords = [
                "arnaque", "escroc", "pourri", "nul", "déçu", 
                "mécontent", "remboursement immédiat", "tribunal"
            ]
            
            message_lower = user_message.lower()
            for keyword in angry_keywords:
                if keyword in message_lower:
                    return (True, f"⚠️ Client mécontent détecté")
            
            return (False, None)

# Global Instance
jessica_mode_manager = JessicaModeManager()

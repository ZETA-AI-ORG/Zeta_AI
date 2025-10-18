"""
🧠 HYDE SPÉCIALISÉ PAR INTENTION
Génère des hypothèses ultra-précises selon l'intention détectée
"""

import os
import asyncio
from typing import Dict, Optional
from core.llm_client import GroqLLMClient
from .intention_router import IntentionResult

class SpecializedHyDE:
    """
    Générateur d'hypothèses HyDE spécialisées par intention e-commerce
    """
    
    def __init__(self):
        self.client = GroqLLMClient()
        
        self.prompts_by_intention = {
            "delivery": {
                "system_prompt": """Tu es un expert en logistique e-commerce français. 
                Génère une réponse détaillée et réaliste sur les frais et délais de livraison.
                Utilise des informations typiques du e-commerce français.""",
                
                "user_template": """Question client: {query}

Génère une réponse hypothétique complète incluant:
- Frais de livraison par zone (France métropolitaine, DOM-TOM, Europe)
- Délais de livraison (standard 48-72h, express 24h)
- Conditions de gratuité (seuil 50€ typique)
- Transporteurs (Colissimo, Chronopost, Mondial Relay)
- Options de suivi et point relais

Réponds comme si tu étais le service client de cette boutique.""",
                
                "temperature": 0.3,
                "max_tokens": 200
            },
            
            "product_catalog": {
                "system_prompt": """Tu es un expert produits e-commerce spécialisé en équipements moto.
                Génère une fiche produit détaillée avec prix et caractéristiques réalistes.""",
                
                "user_template": """Question client: {query}

Génère une fiche produit hypothétique incluant:
- Prix compétitif avec éventuelles promotions
- Caractéristiques techniques détaillées
- Variantes disponibles (couleurs, tailles, modèles)
- Stock et disponibilité
- Descriptions marketing attractives
- Comparaisons avec produits similaires

Réponds comme un catalogue produit professionnel.""",
                
                "temperature": 0.4,
                "max_tokens": 250
            },
            
            "company_identity": {
                "system_prompt": """Tu es un expert en communication d'entreprise e-commerce.
                Génère des informations complètes sur l'identité et la localisation d'une boutique.""",
                
                "user_template": """Question client: {query}

Génère des informations d'entreprise incluant:
- Adresse précise et localisation géographique
- Horaires d'ouverture détaillés
- Moyens de contact (téléphone, email, formulaire)
- Présentation de l'entreprise et son histoire
- Magasin physique vs boutique en ligne
- Services proposés et spécialités

Réponds comme une page "Qui sommes-nous" professionnelle.""",
                
                "temperature": 0.2,
                "max_tokens": 200
            },
            
            "support": {
                "system_prompt": """Tu es un expert support client e-commerce avec expertise paiement et SAV.
                Génère une réponse de support technique, commercial et paiement complète.""",
                
                "user_template": """Question client: {query}

Génère une réponse support incluant:
- Solution détaillée au problème posé
- Étapes de résolution claires et numérotées
- Politique de retour/remboursement/échange
- Informations sur garanties et SAV
- Méthodes de paiement acceptées (CB, PayPal, Mobile Money MTN/Orange/Moov, Wave, virement, paiement à la livraison, espèces)
- Gestion des erreurs de paiement et litiges
- Contacts support spécialisés si nécessaire

Réponds comme un service client expert et bienveillant.""",
                
                "temperature": 0.3,
                "max_tokens": 220
            }
        }
        
        # Prompt générique pour fallback
        self.generic_prompt = {
            "system_prompt": """Tu es un assistant e-commerce expert.
            Génère une réponse détaillée et utile pour aider le client.""",
            
            "user_template": """Question client: {query}

Génère une réponse hypothétique complète qui pourrait aider ce client.
Inclus des informations pertinentes sur les produits, services, livraison ou support selon le contexte.

Réponds de manière professionnelle et utile.""",
            
            "temperature": 0.4,
            "max_tokens": 200
        }
    
    async def generate_hypothesis(self, query: str, intentions: IntentionResult) -> str:
        """
        Génère une hypothèse HyDE spécialisée selon l'intention détectée
        
        Args:
            query: Requête utilisateur originale
            intentions: Résultat de la détection d'intentions
            
        Returns:
            Hypothèse HyDE spécialisée
        """
        try:
            if not intentions.primary or intentions.confidence_score < 0.2:
                # Fallback sur HyDE générique
                return await self._generate_generic_hypothesis(query)
            
            if intentions.is_multi_intent and len(intentions.intentions) == 2:
                # Cas spécial : 2 intentions (ex: prix + livraison)
                return await self._generate_multi_intent_hypothesis(query, intentions)
            
            # HyDE spécialisé pour intention unique
            return await self._generate_specialized_hypothesis(query, intentions.primary)
            
        except Exception as e:
            if os.getenv("DEBUG_HYDE") == "1":
                print(f"[SPECIALIZED_HYDE] Erreur: {e}")
            
            # Fallback sécurisé
            return await self._generate_generic_hypothesis(query)
    
    async def _generate_specialized_hypothesis(self, query: str, intention: str) -> str:
        """Génère une hypothèse pour une intention spécifique"""
        
        if intention not in self.prompts_by_intention:
            return await self._generate_generic_hypothesis(query)
        
        config = self.prompts_by_intention[intention]
        
        prompt = f"{config['system_prompt']}\n\n{config['user_template'].format(query=query)}"
        
        # Utilise GROQ_HYDE_MODEL du .env pour les hypothèses
        hyde_model = os.getenv("GROQ_HYDE_MODEL", "llama-3.1-8b-instant")
        hypothesis = await self.client.complete(
            prompt=prompt,
            model_name=hyde_model,  # Mini LLM 8B pour HyDE
            temperature=config["temperature"],
            max_tokens=config["max_tokens"]
        )
        
        if os.getenv("DEBUG_HYDE") == "1":
            print(f"[SPECIALIZED_HYDE] Intention: {intention}")
            print(f"[SPECIALIZED_HYDE] Query: {query}")
            print(f"[SPECIALIZED_HYDE] Hypothesis: {hypothesis[:100]}...")
        
        return hypothesis
    
    async def _generate_multi_intent_hypothesis(self, query: str, intentions: IntentionResult) -> str:
        """Génère une hypothèse pour requêtes multi-intentions"""
        
        # Prendre les 2 intentions principales
        top_intentions = list(intentions.intentions.keys())[:2]
        
        # Prompt hybride combinant les 2 domaines
        combined_system = f"""Tu es un expert e-commerce. Cette question concerne {' et '.join(top_intentions)}.
        Génère une réponse complète couvrant ces deux aspects."""
        
        combined_user = f"""Question client: {query}

Cette question concerne plusieurs sujets. Génère une réponse hypothétique qui couvre:
- Les aspects liés à {top_intentions[0]}
- Les aspects liés à {top_intentions[1]}

Réponds de manière structurée et complète."""
        
        prompt = f"{combined_system}\n\n{combined_user}"
        
        # Utilise GROQ_HYDE_MODEL pour multi-intentions
        hyde_model = os.getenv("GROQ_HYDE_MODEL", "llama-3.1-8b-instant")
        response = await self.client.complete(
            prompt=prompt,
            model_name=hyde_model,  # Mini LLM 8B pour HyDE
            temperature=0.3,
            max_tokens=250
        )
        
        return response
    
    async def _generate_generic_hypothesis(self, query: str) -> str:
        """Génère une hypothèse générique en fallback"""
        
        prompt = f"{self.generic_prompt['system_prompt']}\n\n{self.generic_prompt['user_template'].format(query=query)}"
        
        # Utilise GROQ_HYDE_MODEL pour fallback générique
        hyde_model = os.getenv("GROQ_HYDE_MODEL", "llama-3.1-8b-instant")
        response = await self.client.complete(
            prompt=prompt,
            model_name=hyde_model,  # Mini LLM 8B pour HyDE
            temperature=self.generic_prompt["temperature"],
            max_tokens=self.generic_prompt["max_tokens"]
        )
        
        return response

# Instance globale pour import facile (lazy loading)
specialized_hyde = None

def get_specialized_hyde():
    """Factory pour l'instance SpecializedHyDE avec lazy loading"""
    global specialized_hyde
    if specialized_hyde is None:
        specialized_hyde = SpecializedHyDE()
    return specialized_hyde

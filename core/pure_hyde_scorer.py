#!/usr/bin/env python3
"""
Système de Scoring HyDE Pur - Intelligence Artificielle Complète
HyDE analyse l'intention et détermine la pertinence de chaque mot (0-10)
"""

import asyncio
import json
import re
from typing import Dict, List, Optional
from pathlib import Path
from utils import log3

class PureHydeScorer:
    """
    Système de scoring 100% basé sur l'intelligence de HyDE
    HyDE analyse l'intention globale et score chaque mot selon sa pertinence
    """
    
    def __init__(self, company_id: str, groq_client, business_config=None):
        self.company_id = company_id
        self.groq_client = groq_client
        self.business_config = business_config
        
        # Cache minimal pour éviter les appels répétés sur mots très courants
        self.cache = {}
        
    async def analyze_and_score_query(self, query: str) -> Dict[str, int]:
        """
        HyDE analyse l'intention complète et score chaque mot intelligemment
        """
        if not self.groq_client:
            raise ValueError("HyDE (groq_client) requis pour le scoring intelligent")
        
        # Nettoyer et extraire les mots
        words = self._extract_words(query)
        
        if not words:
            return {}
        
        # HyDE analyse l'intention globale et score tous les mots
        word_scores = await self._hyde_analyze_intention(query, words)
        
        # Sauvegarder en cache pour optimisation
        for word, score in word_scores.items():
            self.cache[word] = score
        
        log3("[PURE_HYDE]", {
            "query": query,
            "intention_detectee": await self._detect_intention(query),
            "scores": word_scores,
            "company_id": self.company_id
        })
        
        return word_scores
    
    async def _hyde_analyze_intention(self, query: str, words: List[str]) -> Dict[str, int]:
        """
        HyDE analyse l'intention et détermine la pertinence de chaque mot
        """
        try:
            # Construire le contexte entreprise
            context = await self._build_business_context()
            
            # Prompt intelligent pour analyse d'intention
            prompt = f"""Tu es un expert en analyse d'intention pour requêtes e-commerce.

CONTEXTE ENTREPRISE:
{context}

REQUÊTE À ANALYSER: "{query}"
MOTS À SCORER: {words}

MISSION:
1. Détermine l'INTENTION principale (recherche produit, prix, livraison, contact, etc.)
2. Score chaque mot de 0 à 10 selon sa PERTINENCE pour cette intention

ÉCHELLE DE SCORING:
- 10: Mot ESSENTIEL pour l'intention (produit recherché, action principale)
- 8-9: Mot TRÈS PERTINENT (attributs importants, qualificatifs clés)
- 6-7: Mot CONTEXTUEL (précisions utiles, actions secondaires)
- 4-5: Mot FAIBLE PERTINENCE (intentions vagues, mots de liaison)
- 2-3: Mot PEU UTILE (politesse, transitions)
- 0-1: Mot INUTILE (stop words, articles, pronoms)

EXEMPLES (LOGIQUE UNIVERSELLE):
- "je veux casque rouge combien" → INTENTION: recherche prix produit
  → je:0, veux:0, casque:6, rouge:6, combien:10
- "couches a pression taille 6" → INTENTION: recherche produit spécifique  
  → couches:6, a:0, pression:6, taille:6, 6:8
- "livraison cocody possible" → INTENTION: info livraison
  → livraison:10, cocody:6, possible:6

RÈGLE UNIVERSELLE:
- Mots vides (je, le, à, etc.) = 0
- Mots business (prix, livraison, etc.) = 10  
- Nombres (1, 2, 6, etc.) = 8
- TOUS les autres mots = 6 (par défaut)

ANALYSE:
Intention détectée: [décris l'intention en 1 phrase]
Scores: {{"mot1": score, "mot2": score, ...}}

Réponds UNIQUEMENT au format JSON:
{{"intention": "description", "scores": {{"mot": score}}}}"""

            response = await self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.1
            )
            
            # Parser la réponse JSON
            response_text = response.choices[0].message.content.strip()
            
            # Extraire le JSON de la réponse
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result.get('scores', {})
            else:
                # Fallback si parsing échoue
                return await self._fallback_scoring(words)
                
        except Exception as e:
            log3("[PURE_HYDE]", f"Erreur analyse HyDE: {e}")
            return await self._fallback_scoring(words)
    
    async def _detect_intention(self, query: str) -> str:
        """
        Détecte l'intention principale de la requête
        """
        try:
            prompt = f"""Analyse cette requête e-commerce et détermine l'intention principale en 1 mot:

Requête: "{query}"

Intentions possibles:
- PRIX (demande de tarif, coût)
- PRODUIT (recherche d'article spécifique)
- STOCK (disponibilité, rupture)
- LIVRAISON (transport, délai, zone)
- CONTACT (téléphone, whatsapp, adresse)
- PAIEMENT (méthodes, wave, moov)
- COMPARAISON (différences, choix)
- SUPPORT (aide, problème, garantie)

Réponds par 1 seul mot."""

            response = await self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.1
            )
            
            return response.choices[0].message.content.strip().upper()
            
        except:
            return "GENERAL"
    
    async def _build_business_context(self) -> str:
        """
        Construit le contexte métier pour HyDE
        """
        context_parts = []
        
        if self.business_config:
            # Secteur d'activité
            if hasattr(self.business_config, 'sector'):
                sector = getattr(self.business_config.sector, 'value', str(self.business_config.sector))
                context_parts.append(f"Secteur: {sector}")
            
            # Mots-clés métier
            if hasattr(self.business_config, 'keywords'):
                keywords = self.business_config.keywords
                if hasattr(keywords, 'products') and keywords.products:
                    context_parts.append(f"Produits: {', '.join(keywords.products[:5])}")
                if hasattr(keywords, 'services') and keywords.services:
                    context_parts.append(f"Services: {', '.join(keywords.services[:3])}")
        
        # Contexte géographique
        context_parts.append("Localisation: Côte d'Ivoire (Abidjan)")
        context_parts.append("Paiements locaux: Wave, Moov Money, Orange Money, MTN")
        
        return "\n".join(context_parts) if context_parts else "E-commerce général Côte d'Ivoire"
    
    async def _fallback_scoring(self, words: List[str]) -> Dict[str, int]:
        """
        🚀 SCORING UNIVERSEL ADAPTATIF - FONCTIONNE POUR TOUTE ENTREPRISE
        Logique: Élimination des mots vides + Score par défaut 6 + Bonus business
        """
        scores = {}
        
        # === MOTS VIDES UNIVERSELS (À ÉLIMINER) ===
        empty_words = {
            # Articles et déterminants
            'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'ce', 'cette', 'ces', 'mon', 'ma', 'mes',
            'ton', 'ta', 'tes', 'son', 'sa', 'ses', 'notre', 'nos', 'votre', 'vos', 'leur', 'leurs',
            
            # Pronoms
            'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles', 'me', 'te', 'se', 'lui', 'leur',
            'y', 'en', 'qui', 'que', 'dont', 'où', 'quoi', 'quel', 'quelle', 'quels', 'quelles',
            
            # Prépositions
            'à', 'au', 'aux', 'avec', 'contre', 'dans', 'depuis', 'derrière', 'devant', 'en', 'entre',
            'par', 'parmi', 'pendant', 'pour', 'sans', 'selon', 'sous', 'sur', 'vers', 'chez',
            
            # Conjonctions
            'et', 'ou', 'ni', 'mais', 'car', 'donc', 'or', 'que', 'quand', 'comme', 'si', 'lorsque',
            
            # Verbes vagues/auxiliaires
            'être', 'avoir', 'faire', 'dire', 'aller', 'voir', 'savoir', 'pouvoir', 'vouloir', 'venir',
            'falloir', 'devoir', 'croire', 'trouve', 'prendre', 'donner', 'porter', 'parler', 'aimer',
            'passer', 'mettre', 'suivre', 'vivre', 'sortir', 'partir', 'arriver', 'entrer', 'monter',
            'rester', 'devenir', 'tenir', 'sembler', 'laisser', 'penser', 'indiquer', 'montrer',
            
            # Intentions vagues
            'aimerais', 'voudrais', 'cherche', 'trouve', 'regarde', 'veux', 'veut', 'peuvent',
            'pouvais', 'pouvait', 'pourra', 'voulais', 'voulait', 'voudra', 'savais', 'savait',
            
            # Adverbes vagues
            'très', 'plus', 'moins', 'aussi', 'encore', 'déjà', 'jamais', 'toujours', 'souvent',
            'parfois', 'rarement', 'bien', 'mal', 'mieux', 'pire', 'autant', 'tant', 'comment',
            'pourquoi', 'quand', 'beaucoup', 'peu', 'assez', 'trop',
            
            # Politesse
            'bonjour', 'bonsoir', 'salut', 'merci', 'svp', 'plaît', 'excusez', 'pardon'
        }
        
        # === MOTS BUSINESS UNIVERSELS (BONUS) ===
        business_bonus_words = {
            # Commerce universel
            'prix', 'coût', 'coute', 'combien', 'tarif', 'montant', 'cher', 'gratuit', 'payant',
            'acheter', 'vendre', 'commande', 'commander', 'payer', 'paiement',
            
            # Logistique universelle
            'livraison', 'livrer', 'transport', 'expédition', 'délai', 'stock', 'disponible',
            'rupture', 'réception', 'envoi',
            
            # Contact universel
            'contact', 'téléphone', 'email', 'adresse', 'site', 'web', 'whatsapp', 'appeler',
            'joindre', 'écrire', 'message',
            
            # Service client universel
            'garantie', 'retour', 'échange', 'sav', 'support', 'aide', 'problème', 'défaut',
            'réparation', 'remboursement'
        }
        
        # === SCORING ADAPTATIF ===
        for word in words:
            word_lower = word.lower().strip()
            
            # Éliminer les mots vides
            if word_lower in empty_words or len(word_lower) <= 1:
                scores[word] = 0
                
            # Bonus pour mots business universels
            elif word_lower in business_bonus_words:
                scores[word] = 10
                
            # Bonus pour nombres (tailles, quantités, etc.)
            elif word_lower.isdigit() or any(char.isdigit() for char in word_lower):
                scores[word] = 8
                
            # Score par défaut pour TOUS les autres mots non-vides
            else:
                scores[word] = 6
        
        return scores
    
    def _extract_words(self, query: str) -> List[str]:
        """
        Extrait les mots de la requête
        """
        # Nettoyer et normaliser
        query = query.lower().strip()
        query = re.sub(r'[^\w\s\?àâäéèêëïîôöùûüÿç-]', ' ', query)
        
        # Extraire les mots
        words = [w.strip() for w in query.split() if w.strip() and len(w.strip()) > 0]
        return words
    
    async def filter_by_threshold(self, word_scores: Dict[str, int], threshold: int = 6) -> str:
        """
        Filtre les mots selon le seuil et retourne la requête optimisée
        """
        filtered_words = [
            word for word, score in word_scores.items() 
            if score >= threshold
        ]
        
        # Fallback si trop peu de mots
        if len(filtered_words) < 2:
            for lower_threshold in [4, 2, 0]:
                filtered_words = [
                    word for word, score in word_scores.items() 
                    if score >= lower_threshold
                ]
                if len(filtered_words) >= 2:
                    break
        
        filtered_query = ' '.join(filtered_words)
        
        log3("[PURE_HYDE]", {
            "seuil_utilise": threshold,
            "mots_gardes": len(filtered_words),
            "query_filtree": filtered_query
        })
        
        return filtered_query if filtered_query.strip() else ' '.join(word_scores.keys())


# === FONCTION D'INTÉGRATION ===
async def pure_hyde_filter(query: str, company_id: str, groq_client, business_config=None, threshold: int = 6) -> str:
    """
    Interface principale pour le filtrage HyDE pur
    """
    scorer = PureHydeScorer(company_id, groq_client, business_config)
    
    # HyDE analyse et score
    word_scores = await scorer.analyze_and_score_query(query)
    
    # Filtrer selon le seuil
    filtered_query = await scorer.filter_by_threshold(word_scores, threshold)
    
    return filtered_query


# === TESTS ===
if __name__ == "__main__":
    async def test_pure_hyde():
        # Mock groq client pour test
        class MockGroqClient:
            class ChatCompletions:
                async def create(self, **kwargs):
                    class MockResponse:
                        class Choice:
                            class Message:
                                content = '{"intention": "recherche prix produit", "scores": {"je": 0, "veux": 4, "casque": 10, "rouge": 9, "combien": 10}}'
                        choices = [Choice()]
                    return MockResponse()
            
            chat = ChatCompletions()
        
        groq_client = MockGroqClient()
        
        test_queries = [
            "je veux casque rouge combien",
            "livraison cocody possible",
            "samsung galaxy prix disponible",
            "contact whatsapp pour commande"
        ]
        
        print("🧠 TEST PURE HYDE SCORING")
        print("=" * 50)
        
        for query in test_queries:
            print(f"\n📝 REQUÊTE: '{query}'")
            
            filtered = await pure_hyde_filter(
                query, 
                "test_company", 
                groq_client, 
                threshold=6
            )
            
            print(f"✨ RÉSULTAT: '{filtered}'")
    
    asyncio.run(test_pure_hyde())

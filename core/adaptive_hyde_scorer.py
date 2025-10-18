#!/usr/bin/env python3
"""
Système de Scoring HyDE Adaptatif par Entreprise
Apprend automatiquement les mots-clés spécifiques à chaque secteur d'activité
"""

import asyncio
import json
from typing import Dict, List, Optional
from pathlib import Path
from utils import log3
from core.business_config_manager import get_business_config

class AdaptiveHydeScorer:
    """
    Système de scoring adaptatif qui s'ajuste selon:
    1. Le secteur d'activité de l'entreprise
    2. Les mots-clés métier spécifiques
    3. L'historique des requêtes réussies
    """
    
    def __init__(self, company_id: str, groq_client=None):
        self.company_id = company_id
        self.groq_client = groq_client
        
        # Cache des scores adaptatifs par entreprise
        self.company_scores = {}
        self.sector_scores = {}
        self.learned_scores = {}
        
        # Scores de base universels (e-commerce général)
        self.base_scores = {
            # === SCORE 10 - UNIVERSELS E-COMMERCE ===
            "prix": 10, "combien": 10, "coût": 10, "coûte": 10,
            "acheter": 10, "commander": 10, "disponible": 10, "stock": 10,
            "livraison": 10, "paiement": 10, "contact": 10,
            
            # === SCORE 0 - STOP WORDS UNIVERSELS ===
            "je": 0, "tu": 0, "le": 0, "la": 0, "les": 0,
            "et": 0, "ou": 0, "mais": 0, "bonjour": 1, "bonsoir": 1
        }
    
    async def initialize_company_scoring(self):
        """
        Initialise le scoring spécifique à l'entreprise
        """
        try:
            # 1. Charger la config métier
            business_config = await get_business_config(self.company_id)
            
            if business_config:
                # 2. Adapter selon le secteur
                await self._load_sector_scores(business_config.sector)
                
                # 3. Intégrer les mots-clés métier
                await self._load_business_keywords(business_config.keywords)
                
                # 4. Charger l'historique d'apprentissage
                await self._load_learned_patterns()
            
            log3("[ADAPTIVE_SCORER]", f"Scoring initialisé pour {self.company_id}")
            
        except Exception as e:
            log3("[ADAPTIVE_SCORER]", f"Erreur initialisation: {e}")
    
    async def _load_sector_scores(self, sector):
        """
        Charge les scores spécifiques au secteur d'activité
        """
        sector_name = getattr(sector, 'value', str(sector)) if sector else 'general'
        
        # Scores par secteur (générés par HyDE contextuel)
        sector_mappings = {
            'auto_moto': {
                # Produits spécifiques
                'casque': 10, 'moto': 10, 'scooter': 10, 'vélo': 10,
                'pneu': 10, 'huile': 10, 'batterie': 10, 'frein': 10,
                'rouge': 9, 'noir': 9, 'blanc': 9, 'bleu': 9,
                
                # Services spécifiques
                'réparation': 9, 'entretien': 9, 'révision': 8,
                'garantie': 8, 'installation': 7,
                
                # Attributs techniques
                'cylindrée': 8, 'puissance': 8, 'vitesse': 7,
                'consommation': 7, 'autonomie': 7
            },
            
            'electronique': {
                'téléphone': 10, 'smartphone': 10, 'tablette': 10,
                'ordinateur': 10, 'laptop': 10, 'écran': 10,
                'samsung': 9, 'iphone': 9, 'apple': 9, 'huawei': 9,
                'gigaoctet': 8, 'mémoire': 8, 'stockage': 8,
                'batterie': 8, 'chargeur': 8, 'écouteurs': 8
            },
            
            'mode_beaute': {
                'robe': 10, 'chemise': 10, 'pantalon': 10, 'chaussure': 10,
                'parfum': 10, 'maquillage': 10, 'crème': 10,
                'taille': 9, 'couleur': 9, 'style': 8, 'tendance': 8,
                'marque': 8, 'designer': 7, 'collection': 7
            },
            
            'alimentation': {
                'riz': 10, 'huile': 10, 'sucre': 10, 'farine': 10,
                'poisson': 10, 'viande': 10, 'légume': 10, 'fruit': 10,
                'frais': 9, 'bio': 8, 'local': 8, 'importé': 7,
                'kilogramme': 8, 'litre': 8, 'paquet': 7
            }
        }
        
        self.sector_scores = sector_mappings.get(sector_name, {})
        log3("[ADAPTIVE_SCORER]", f"Scores secteur '{sector_name}': {len(self.sector_scores)} mots")
    
    async def _load_business_keywords(self, keywords):
        """
        Intègre les mots-clés métier spécifiques de l'entreprise
        """
        if not keywords:
            return
        
        business_words = {}
        
        # Extraire les mots-clés par catégorie
        if hasattr(keywords, 'products') and keywords.products:
            for product in keywords.products:
                business_words[product.lower()] = 10
        
        if hasattr(keywords, 'services') and keywords.services:
            for service in keywords.services:
                business_words[service.lower()] = 9
        
        if hasattr(keywords, 'brands') and keywords.brands:
            for brand in keywords.brands:
                business_words[brand.lower()] = 8
        
        self.company_scores = business_words
        log3("[ADAPTIVE_SCORER]", f"Mots-clés entreprise: {len(business_words)} mots")
    
    async def _load_learned_patterns(self):
        """
        Charge les patterns appris depuis l'historique des requêtes
        """
        try:
            learned_file = Path(f"cache/learned_scores_{self.company_id}.json")
            
            if learned_file.exists():
                with open(learned_file, 'r', encoding='utf-8') as f:
                    self.learned_scores = json.load(f)
                
                log3("[ADAPTIVE_SCORER]", f"Scores appris: {len(self.learned_scores)} mots")
        
        except Exception as e:
            log3("[ADAPTIVE_SCORER]", f"Erreur chargement patterns: {e}")
            self.learned_scores = {}
    
    async def get_word_score(self, word: str, query_context: str = "") -> int:
        """
        Calcule le score d'un mot selon la hiérarchie:
        1. Mots-clés entreprise (priorité max)
        2. Scores appris (historique)
        3. Scores secteur
        4. Scores de base
        5. HyDE contextuel (nouveau mot)
        """
        word = word.lower().strip()
        
        # 1. Priorité absolue: mots-clés entreprise
        if word in self.company_scores:
            return self.company_scores[word]
        
        # 2. Scores appris depuis l'historique
        if word in self.learned_scores:
            return self.learned_scores[word]
        
        # 3. Scores spécifiques au secteur
        if word in self.sector_scores:
            return self.sector_scores[word]
        
        # 4. Scores de base universels
        if word in self.base_scores:
            return self.base_scores[word]
        
        # 5. Nouveau mot → Utiliser HyDE contextuel
        return await self._hyde_contextual_score(word, query_context)
    
    async def _hyde_contextual_score(self, word: str, query_context: str) -> int:
        """
        Utilise HyDE pour scorer un nouveau mot dans le contexte entreprise
        """
        if not self.groq_client:
            return self._heuristic_score(word)
        
        try:
            # Construire le contexte entreprise
            business_config = await get_business_config(self.company_id)
            sector = getattr(business_config.sector, 'value', 'général') if business_config and business_config.sector else 'général'
            
            prompt = f"""Tu es un expert en scoring de mots-clés pour une entreprise {sector} en Côte d'Ivoire.

Entreprise: {self.company_id}
Secteur: {sector}
Requête: "{query_context}"
Mot à scorer: "{word}"

Note ce mot de 0 à 10 selon sa pertinence pour cette entreprise:
- 10: Mot essentiel pour ce secteur (produit phare, service principal)
- 8-9: Très pertinent (attributs importants, actions clés)
- 6-7: Contextuel (qualificatifs, actions secondaires)
- 3-5: Faible pertinence (intentions vagues)
- 0-2: Stop word ou non pertinent

Exemples pour {sector}:
- Auto/Moto: casque=10, rouge=9, réparation=8, voir=6, je=0
- Électronique: téléphone=10, samsung=9, mémoire=8, chercher=6, le=0

Réponds UNIQUEMENT par un chiffre 0-10."""

            response = await self.groq_client.chat.completions.acreate(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5,
                temperature=0.1
            )
            
            score_text = response.choices[0].message.content.strip()
            score = int(score_text) if score_text.isdigit() else self._heuristic_score(word)
            
            # Sauvegarder le score appris
            await self._save_learned_score(word, score)
            
            return max(0, min(10, score))
            
        except Exception as e:
            log3("[ADAPTIVE_SCORER]", f"Erreur HyDE contextuel pour '{word}': {e}")
            return self._heuristic_score(word)
    
    def _heuristic_score(self, word: str) -> int:
        """
        Scoring heuristique de fallback
        """
        if len(word) <= 2:
            return 0
        elif len(word) >= 8:
            return 6
        elif any(pattern in word for pattern in ['prix', 'coût', 'cher', 'livr', 'stock', 'dispo']):
            return 8
        else:
            return 4
    
    async def _save_learned_score(self, word: str, score: int):
        """
        Sauvegarde un score appris pour réutilisation future
        """
        try:
            self.learned_scores[word] = score
            
            # Sauvegarder sur disque
            cache_dir = Path("cache")
            cache_dir.mkdir(exist_ok=True)
            
            learned_file = cache_dir / f"learned_scores_{self.company_id}.json"
            with open(learned_file, 'w', encoding='utf-8') as f:
                json.dump(self.learned_scores, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            log3("[ADAPTIVE_SCORER]", f"Erreur sauvegarde score: {e}")
    
    async def score_query_adaptive(self, query: str) -> Dict[str, int]:
        """
        Score une requête complète avec adaptation entreprise
        """
        words = query.lower().split()
        word_scores = {}
        
        for word in words:
            if word.strip():
                score = await self.get_word_score(word, query)
                word_scores[word] = score
        
        log3("[ADAPTIVE_SCORER]", {
            "company_id": self.company_id,
            "query": query,
            "scores": word_scores
        })
        
        return word_scores


# === INTÉGRATION DANS LE SYSTÈME PRINCIPAL ===
async def get_adaptive_scorer(company_id: str, groq_client=None) -> AdaptiveHydeScorer:
    """
    Factory pour créer un scorer adaptatif initialisé
    """
    scorer = AdaptiveHydeScorer(company_id, groq_client)
    await scorer.initialize_company_scoring()
    return scorer

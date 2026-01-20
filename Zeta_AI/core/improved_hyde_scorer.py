#!/usr/bin/env python3
"""
Système de Scoring HyDE Amélioré - Correction des problèmes identifiés
"""

import asyncio
import json
from typing import Dict, List, Optional
# Fonction log3 intégrée pour éviter l'import utils
def log3(prefix, message):
    """Fonction de log simplifiée"""
    import datetime
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    if isinstance(message, dict):
        import json
        message = json.dumps(message, indent=2, ensure_ascii=False)
    print(f"[TRACE][{timestamp}][INFO] {prefix}: {message}")

class ImprovedHydeScorer:
    """
    Système de scoring HyDE amélioré avec scoring optimisé pour e-commerce
    """
    
    def __init__(self, company_id: str = "RueduGrossiste"):
        self.company_id = company_id
        
        # Scoring optimisé pour e-commerce ivoirien
        self.word_scores = {
            # SCORE 10 - CRITIQUES ABSOLUS
            "prix": 10, "combien": 10, "coût": 10, "coûte": 10,
            "disponible": 10, "stock": 10, "dispo": 10,
            
            # SCORE 9 - TRÈS IMPORTANTS
            "casque": 9, "moto": 9, "téléphone": 9, "smartphone": 9,
            "samsung": 9, "iphone": 9, "yamaha": 9, "nokia": 9,  # MARQUES
            "contact": 9, "whatsapp": 9, "appeler": 9,  # CONTACT
            "livraison": 9, "cocody": 9, "plateau": 9, "yopougon": 9,  # LIEUX ABIDJAN
            "riviera": 9, "golf": 9, "marcory": 9, "treichville": 9,
            "abobo": 9, "adjamé": 9, "koumassi": 9, "port-bouet": 9,  # AUTRES COMMUNES
            
            # SCORE 8 - IMPORTANTS
            "rouge": 8, "bleu": 8, "noir": 8, "blanc": 8, "vert": 8,  # COULEURS
            "neuf": 8, "occasion": 8, "original": 8, "authentique": 8,  # ÉTAT
            "acheter": 8, "vendre": 8, "commander": 8, "réserver": 8,  # ACTIONS
            
            # SCORE 8 - IMPORTANTS (PAIEMENT MOBILE CRITIQUE)
            "wave": 8, "moov": 8, "money": 8, "orange": 8,  # PAIEMENT MOBILE
            "mtn": 8, "mobile": 8, "transfert": 8, "cod": 8,  # PAIEMENT
            
            # SCORE 7 - MOYENNEMENT IMPORTANTS
            "galaxy": 7, "s24": 7, "pro": 7, "max": 7,  # MODÈLES
            "paiement": 7, "qualité": 7, "garantie": 7, "service": 7,
            
            # SCORE 6 - CONTEXTUELS
            "avec": 6, "pour": 6, "possible": 6, "urgent": 6,
            "rapide": 6, "immédiat": 6, "aujourd'hui": 6,
            
            # SCORE 5 - FAIBLE PERTINENCE CONTEXTUELLE
            "passer": 5, "commande": 5, "demande": 5, "besoin": 5,
            "cherche": 5, "trouve": 5, "voir": 5,
            
            # SCORE 3-4 - FAIBLE PERTINENCE
            "veux": 4, "voudrais": 4, "aimerais": 3, "souhaite": 3,
            
            # SCORE 0-2 - STOP WORDS
            "je": 0, "le": 0, "la": 0, "les": 0, "un": 0, "une": 0,
            "c'est": 0, "est": 0, "ce": 0, "ça": 0, "cela": 0,
            "bonjour": 1, "bonsoir": 1, "salut": 1, "merci": 1,
            "à": 1, "et": 0, "ou": 1, "mais": 1, "donc": 1,
        }
    
    def score_word(self, word: str) -> int:
        """Score un mot selon son importance business"""
        word_clean = word.lower().strip('?.,!:;()[]{}"\'-')
        
        # Score direct si dans le dictionnaire
        if word_clean in self.word_scores:
            return self.word_scores[word_clean]
        
        # Heuristiques pour mots inconnus
        return self._heuristic_scoring(word_clean)
    
    def _heuristic_scoring(self, word: str) -> int:
        """Scoring heuristique pour mots non répertoriés"""
        
        # Mots trop courts
        if len(word) <= 2:
            return 0
        
        # Mots techniques/modèles (chiffres + lettres)
        if any(c.isdigit() for c in word) and any(c.isalpha() for c in word):
            return 8  # Ex: "s24", "iphone15", "gt125" - Modèles importants
        
        # Mots en majuscules (marques potentielles)
        if word.isupper() and len(word) >= 3:
            return 9  # Ex: "NOKIA", "BMW", "SONY" - Marques critiques
        
        # Détection lieux Abidjan (patterns)
        abidjan_patterns = ['cocody', 'plateau', 'yopougon', 'riviera', 'golf', 'marcory', 'treichville', 'abobo', 'adjamé', 'koumassi']
        if any(pattern in word for pattern in abidjan_patterns):
            return 9  # Lieux de livraison critiques
        
        # Détection marques tech (patterns)
        tech_brands = ['samsung', 'apple', 'huawei', 'xiaomi', 'oppo', 'vivo', 'nokia', 'sony']
        if any(brand in word for brand in tech_brands):
            return 9  # Marques tech critiques
        
        # Mots longs (potentiellement techniques)
        if len(word) >= 8:
            return 6  # Ex: "disponibilité", "caractéristiques"
        
        # Score par défaut pour mots inconnus
        return 5
    
    def filter_by_threshold(self, query: str, threshold: int = 6) -> Dict:
        """Filtre une requête selon un seuil de score"""
        words = query.lower().split()
        
        scored_words = []
        for word in words:
            score = self.score_word(word)
            if score >= threshold:
                scored_words.append({
                    'word': word.strip('?.,!:;()[]{}"\'-'),
                    'score': score
                })
        
        # Fallback si trop peu de mots
        if len(scored_words) < 2 and threshold > 4:
            # Réessayer avec seuil plus bas
            return self.filter_by_threshold(query, threshold - 2)
        
        # Trier par score décroissant
        scored_words.sort(key=lambda x: x['score'], reverse=True)
        
        # Extraire les mots
        filtered_words = [item['word'] for item in scored_words]
        
        return {
            'filtered_query': ' '.join(filtered_words),
            'word_scores': {item['word']: item['score'] for item in scored_words},
            'words_kept': len(filtered_words),
            'threshold_used': threshold,
            'original_words': len(words),
            'efficiency_percent': round(((len(words) - len(filtered_words)) / len(words)) * 100, 1) if words else 0
        }
    
    def is_business_relevant(self, word: str) -> bool:
        """Vérifie si un mot est pertinent pour le business"""
        score = self.score_word(word)
        return score >= 5  # Seuil de pertinence business
    
    async def analyze_query_intention(self, query: str) -> str:
        """Analyse l'intention de la requête (version simplifiée)"""
        query_lower = query.lower()
        
        # Détection d'intention par mots-clés
        if any(word in query_lower for word in ["prix", "combien", "coût", "coûte"]):
            return "PRIX"
        elif any(word in query_lower for word in ["livraison", "livrer", "cocody", "plateau", "yopougon"]):
            return "LIVRAISON"
        elif any(word in query_lower for word in ["contact", "whatsapp", "appeler", "téléphone"]):
            return "CONTACT"
        elif any(word in query_lower for word in ["disponible", "stock", "dispo", "rupture"]):
            return "STOCK"
        elif any(word in query_lower for word in ["wave", "moov", "paiement", "payer"]):
            return "PAIEMENT"
        else:
            return "PRODUIT"

# Fonction d'interface principale
async def improved_hyde_filter(query: str, company_id: str = "RueduGrossiste", threshold: int = 6) -> str:
    """
    DÉSACTIVATION COMPLÈTE du système HYDE externe
    Retourne la query originale sans aucun filtrage
    """
    log3("[HYDE_DISABLED]", "🚫 SYSTÈME HYDE EXTERNE COMPLÈTEMENT DÉSACTIVÉ")
    log3("[HYDE_DISABLED]", f"📝 Query originale: '{query}'")
    log3("[HYDE_DISABLED]", f"📊 Longueur: {len(query)} caractères")
    log3("[HYDE_DISABLED]", "✅ BYPASS COMPLET - Aucun filtrage appliqué")
    
    # BYPASS COMPLET: Retourner la query originale sans aucun traitement
    return query

# Tests de validation
if __name__ == "__main__":
    async def test_improved_scoring():
        """Test du système de scoring amélioré"""
        
        scorer = ImprovedHydeScorer()
        
        test_cases = [
            {
                'query': 'je veux casque rouge combien',
                'expected_result': 'casque rouge combien',
                'expected_intention': 'PRIX'
            },
            {
                'query': 'samsung galaxy s24 prix disponible',
                'expected_result': 'samsung galaxy prix disponible',
                'expected_intention': 'PRIX'
            },
            {
                'query': 'livraison cocody avec paiement wave possible',
                'expected_result': 'livraison cocody paiement wave possible',
                'expected_intention': 'LIVRAISON'
            },
            {
                'query': 'contact whatsapp pour commande urgente',
                'expected_result': 'contact whatsapp commande urgent',
                'expected_intention': 'CONTACT'
            }
        ]
        
        print("🧪 TESTS SCORING HYDE AMÉLIORÉ")
        print("=" * 60)
        
        for i, test in enumerate(test_cases, 1):
            query = test['query']
            
            # Test du filtrage
            filtered = await improved_hyde_filter(query, threshold=6)
            intention = await scorer.analyze_query_intention(query)
            result = scorer.filter_by_threshold(query, 6)
            
            print(f"\n📝 TEST {i}: '{query}'")
            print(f"🎯 Intention: {intention}")
            print(f"✨ Résultat: '{filtered}'")
            print(f"📊 Efficacité: {result['efficiency_percent']}% réduction")
            print(f"🔢 Scores: {result['word_scores']}")
            
            # Validation
            success = "✅" if intention == test['expected_intention'] else "❌"
            print(f"{success} Intention attendue: {test['expected_intention']}")
    
    asyncio.run(test_improved_scoring())

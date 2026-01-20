#!/usr/bin/env python3
"""
🎯 HYDE SCORER AVEC CACHE - VERSION ULTRA-RAPIDE
Utilise le cache de mots-scores créé lors de l'ingestion
Fallback vers HyDE dynamique pour les mots inconnus
"""

import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime
from groq import Groq
import os

def log3(message, data=None):
    """Log formaté pour le scorer avec cache"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[CACHED_HYDE][{timestamp}][INFO] {message}")
    if data:
        print(f"  📊 {json.dumps(data, indent=2, ensure_ascii=False)}")

class CachedHydeScorer:
    """
    Scorer HyDE hybride: Cache + Dynamique
    - Utilise le cache pour les mots connus (ultra-rapide)
    - Fallback vers HyDE dynamique pour les nouveaux mots
    """
    
    def __init__(self, groq_api_key: str = None):
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.word_caches = {}  # Cache en mémoire par company_id
        
    def load_company_cache(self, company_id: str) -> Dict:
        """Charge le cache de mots pour une entreprise"""
        if company_id in self.word_caches:
            return self.word_caches[company_id]
            
        cache_file = f"cache/word_scores_{company_id}.json"
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            self.word_caches[company_id] = cache_data
            
            log3(f"📂 CACHE CHARGÉ", {
                "company_id": company_id,
                "words_in_cache": len(cache_data.get('word_scores', {})),
                "analysis_date": cache_data.get('analysis_date', 'N/A')
            })
            
            return cache_data
            
        except FileNotFoundError:
            log3(f"⚠️ Cache non trouvé pour {company_id} - Utilisation HyDE dynamique")
            return {"word_scores": {}, "business_profile": {}}

    async def score_query_words(self, query: str, company_id: str, threshold: int = 6) -> Dict:
        """
        Score les mots d'une requête avec cache + fallback dynamique
        """
        # Charger le cache de l'entreprise
        cache_data = self.load_company_cache(company_id)
        word_scores_cache = cache_data.get('word_scores', {})
        business_profile = cache_data.get('business_profile', {})
        
        # Tokeniser la requête
        words = self._tokenize_query(query)
        
        # Scorer chaque mot
        word_scores = {}
        cache_hits = 0
        dynamic_scores = 0
        unknown_words = []
        
        for word in words:
            word_lower = word.lower()
            
            # Vérifier le cache d'abord
            if word_lower in word_scores_cache:
                word_scores[word] = word_scores_cache[word_lower]
                cache_hits += 1
            else:
                # Mot inconnu - sera scoré dynamiquement
                unknown_words.append(word)
        
        # Scorer les mots inconnus avec HyDE dynamique
        if unknown_words:
            dynamic_word_scores = await self._score_unknown_words(
                unknown_words, business_profile, company_id
            )
            word_scores.update(dynamic_word_scores)
            dynamic_scores = len(dynamic_word_scores)
        
        # Détecter l'intention
        intention = self._detect_intention(word_scores)
        
        # Filtrer par seuil
        filtered_words = [word for word, score in word_scores.items() if score >= threshold]
        
        # Statistiques
        stats = {
            "query_originale": query,
            "intention_detectee": intention,
            "seuil_utilise": threshold,
            "mots_gardes": len(filtered_words),
            "efficacite": f"{((len(words) - len(filtered_words)) / len(words) * 100):.1f}% réduction" if words else "0%",
            "query_filtree": " ".join(filtered_words),
            "scores_detailles": word_scores,
            "cache_performance": {
                "cache_hits": cache_hits,
                "dynamic_scores": dynamic_scores,
                "cache_hit_rate": f"{(cache_hits / len(words) * 100):.1f}%" if words else "0%"
            }
        }
        
        log3("🎯 SCORING HYBRIDE TERMINÉ", stats)
        
        return stats

    def _tokenize_query(self, query: str) -> List[str]:
        """Tokenise une requête utilisateur"""
        import re
        
        # Nettoyer et tokeniser
        query = query.lower()
        query = re.sub(r'[^\w\s]', ' ', query)
        words = [w for w in query.split() if len(w) > 2]
        
        return words

    async def _score_unknown_words(self, words: List[str], business_profile: Dict, company_id: str) -> Dict[str, int]:
        """Score les mots inconnus avec HyDE dynamique"""
        if not words:
            return {}
            
        # Construire le prompt de scoring contextuel
        secteur = business_profile.get('secteur_activite', 'e-commerce')
        produits = ', '.join(business_profile.get('produits_services', ['produits génériques']))
        
        prompt = f"""
Entreprise: {secteur}
Produits/Services: {produits}

Score ces nouveaux mots de 0 à 10 selon leur importance business:
- 10: Mots critiques (prix, contact, produits phares)
- 8-9: Mots très importants (marques, paiement, livraison)
- 6-7: Mots utiles (caractéristiques, couleurs)
- 3-5: Mots peu importants
- 0-2: Mots sans intérêt

MOTS: {', '.join(words)}

Réponds UNIQUEMENT en JSON: {{"mot": score, ...}}
"""
        
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )
            
            dynamic_scores = json.loads(response.choices[0].message.content)
            
            # Mettre à jour le cache avec les nouveaux mots
            await self._update_cache_with_new_words(company_id, dynamic_scores)
            
            log3(f"🧠 MOTS INCONNUS SCORÉS", {
                "new_words": len(dynamic_scores),
                "scores": dynamic_scores
            })
            
            return dynamic_scores
            
        except Exception as e:
            log3(f"⚠️ Erreur scoring dynamique: {e}")
            # Scores par défaut
            return {word: 5 for word in words}

    async def _update_cache_with_new_words(self, company_id: str, new_word_scores: Dict[str, int]):
        """Met à jour le cache avec les nouveaux mots scorés"""
        cache_file = f"cache/word_scores_{company_id}.json"
        
        try:
            # Charger le cache existant
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Ajouter les nouveaux mots
            cache_data['word_scores'].update(new_word_scores)
            cache_data['last_updated'] = datetime.now().isoformat()
            
            # Sauvegarder
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            # Mettre à jour le cache en mémoire
            self.word_caches[company_id] = cache_data
            
            log3(f"💾 CACHE MIS À JOUR", {
                "company_id": company_id,
                "new_words_added": len(new_word_scores)
            })
            
        except Exception as e:
            log3(f"⚠️ Erreur mise à jour cache: {e}")

    def _detect_intention(self, word_scores: Dict[str, int]) -> str:
        """Détecte l'intention basée sur les mots avec scores élevés"""
        high_score_words = [word.lower() for word, score in word_scores.items() if score >= 8]
        
        # Patterns d'intention
        if any(word in high_score_words for word in ['prix', 'coûte', 'combien', 'tarif', 'coût']):
            return "PRIX"
        elif any(word in high_score_words for word in ['stock', 'disponible', 'dispo', 'reste']):
            return "STOCK"
        elif any(word in high_score_words for word in ['livraison', 'livrer', 'envoyer', 'expédier']):
            return "LIVRAISON"
        elif any(word in high_score_words for word in ['contact', 'whatsapp', 'appeler', 'joindre']):
            return "CONTACT"
        elif any(word in high_score_words for word in ['paiement', 'payer', 'wave', 'moov', 'orange', 'mtn']):
            return "PAIEMENT"
        else:
            return "RECHERCHE"

# Fonction principale pour l'intégration
async def cached_hyde_filter(query: str, company_id: str, threshold: int = 6) -> str:
    """
    Filtre une requête avec le système HyDE hybride (cache + dynamique)
    """
    scorer = CachedHydeScorer()
    result = await scorer.score_query_words(query, company_id, threshold)
    return result.get('query_filtree', query)

if __name__ == "__main__":
    print("🎯 HYDE SCORER HYBRIDE - CACHE + DYNAMIQUE")
    print("=" * 50)
    print("Utilisation: from core.cached_hyde_scorer import cached_hyde_filter")

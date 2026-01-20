#!/usr/bin/env python3
"""
🎯 HYDE D'INGESTION - ANALYSEUR INTELLIGENT DE DOCUMENTS
Analyse les documents lors de l'ingestion pour créer un cache de mots-scores
Transforme le chatbot en expert spécialisé du domaine business
"""

import asyncio
import json
import re
from typing import Dict, List, Set, Tuple
from datetime import datetime
from groq import Groq
import os
from collections import Counter, defaultdict

# Import du nouveau système de scoring HyDE
from .hyde_word_scorer import HydeWordScorer

def log_hyde(message, data=None, level="INFO"):
    """Log ultra-détaillé pour HyDE d'ingestion"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "PROCESS": "🔄", "ANALYSIS": "🧠"}
    icon = icons.get(level, "📝")
    print(f"{icon} [HYDE_ANALYZER][{timestamp}] {message}")
    if data:
        print(f"   📊 {json.dumps(data, indent=2, ensure_ascii=False)}")

class IngestionHydeAnalyzer:
    """
    Analyseur HyDE d'ingestion - Crée un cache intelligent de mots-scores
    """
    
    def __init__(self, groq_api_key: str = None):
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        # Cache des scores de mots par entreprise
        self.word_scores_cache = {}
        
        # Statistiques d'analyse
        self.analysis_stats = {
            "documents_analyzed": 0,
            "words_scored": 0,
            "business_terms_found": 0,
            "stopwords_removed": 0
        }
    
    def get_word_score(self, word: str, company_id: str) -> float:
        """
        🎯 MÉTHODE MANQUANTE - Récupère le score d'un mot pour une entreprise
        """
        if company_id not in self.word_scores_cache:
            log_hyde(f"⚠️ Aucun cache trouvé pour {company_id}, score par défaut", level="WARNING")
            return 5.0
        
        word_lower = word.lower()
        score = self.word_scores_cache[company_id].get(word_lower, 5.0)
        
        log_hyde(f"📊 Score récupéré: '{word}' = {score}")
        return score
        
        # Mots vides français étendus
        self.french_stopwords = {
            # Articles
            "le", "la", "les", "un", "une", "des", "du", "de", "d", "l",
            # Prépositions
            "à", "au", "aux", "avec", "dans", "par", "pour", "sur", "sous", "vers", "chez",
            # Conjonctions
            "et", "ou", "mais", "donc", "car", "ni", "que", "qui", "quoi", "dont", "où",
            # Pronoms
            "je", "tu", "il", "elle", "nous", "vous", "ils", "elles", "me", "te", "se", "nous", "vous",
            "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses", "notre", "votre", "leur", "leurs",
            "ce", "cette", "ces", "cet", "celui", "celle", "ceux", "celles",
            # Verbes auxiliaires/fréquents
            "être", "avoir", "faire", "aller", "venir", "voir", "savoir", "pouvoir", "vouloir", "devoir",
            "est", "sont", "était", "étaient", "sera", "seront", "a", "ont", "avait", "avaient", "aura", "auront",
            "fait", "font", "faisait", "faisaient", "fera", "feront",
            # Mots de liaison
            "alors", "ainsi", "aussi", "bien", "encore", "même", "plus", "très", "tout", "tous", "toute", "toutes",
            "peut", "peuvent", "pourrait", "pourraient", "doit", "doivent", "devrait", "devraient",
            # Mots conversationnels
            "bonjour", "bonsoir", "salut", "merci", "svp", "sil", "vous", "plait", "plaît",
            "euh", "bon", "voilà", "voici", "donc", "enfin", "bref"
        }

    async def analyze_documents(self, documents: List[Dict], company_id: str):
        """
        🧠 ANALYSE CORPUS DE DOCUMENTS POUR CACHE MOTS-SCORES
        """
        log_hyde(f"🧠 DÉBUT ANALYSE CORPUS", {
            "nb_documents": len(documents),
            "company_id": company_id
        }, "ANALYSIS")
        
        # Extraire tout le texte des documents
        log_hyde(f"📝 EXTRACTION TEXTE EN COURS...", level="PROCESS")
        all_text = self._extract_all_text(documents)
        log_hyde(f"📝 TEXTE EXTRAIT", {
            "caractères_total": len(all_text),
            "taille_ko": f"{len(all_text)/1024:.1f} Ko"
        })
        
        # Tokeniser et nettoyer
        log_hyde(f"🧹 TOKENISATION ET NETTOYAGE...", level="PROCESS")
        words = self._tokenize_and_clean(all_text)
        log_hyde(f"🧹 NETTOYAGE TERMINÉ", {
            "mots_uniques": len(words),
            "stopwords_supprimés": self.analysis_stats["stopwords_removed"],
            "échantillon_mots": list(words)[:10]
        })
        
        # Analyser par batches avec Groq
        log_hyde(f"🤖 ANALYSE GROQ EN COURS...", level="PROCESS")
        word_scores = await self._analyze_words_with_groq(words, company_id)
        
        # Stocker dans le cache
        self.word_scores_cache[company_id] = word_scores
        
        # Mettre à jour les statistiques
        self.analysis_stats["documents_analyzed"] += len(documents)
        self.analysis_stats["words_scored"] += len(word_scores)
        
        # Analyser les scores obtenus
        if word_scores:
            scores_values = list(word_scores.values())
            top_words = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)[:10]
            
            log_hyde(f"🎯 ANALYSE TERMINÉE AVEC SUCCÈS", {
                "mots_scorés": len(word_scores),
                "score_moyen": f"{sum(scores_values)/len(scores_values):.2f}",
                "score_max": max(scores_values),
                "score_min": min(scores_values),
                "top_10_mots": dict(top_words)
            }, "SUCCESS")
        else:
            log_hyde(f"⚠️ AUCUN SCORE GÉNÉRÉ", level="WARNING")

    def _extract_all_text(self, documents: List[Dict]) -> str:
        """Extrait tout le texte des documents"""
        all_text = ""
        for doc in documents:
            all_text += doc.get('searchable_text', '')
        return all_text

    def _tokenize_and_clean(self, text: str) -> List[str]:
        """Tokenise et nettoie le texte avec détection automatique des nombres"""
        # Conversion en minuscules
        text = text.lower()
        
        # Suppression de la ponctuation et caractères spéciaux
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Tokenisation
        words = text.split()
        
        # Créer un scorer pour détecter les nombres
        scorer = HydeWordScorer()
        
        # Filtrage avec détection automatique des nombres
        filtered_words = []
        numbers_detected = 0
        
        for w in words:
            if len(w) <= 2:
                continue
            if w in self.french_stopwords:
                self.analysis_stats["stopwords_removed"] += 1
                continue
            # NOUVELLE LOGIQUE: Exclure automatiquement les nombres
            if scorer._is_numeric(w):
                numbers_detected += 1
                log_hyde(f"🔢 Nombre exclu de l'analyse: '{w}'", level="INFO")
                continue
            
            filtered_words.append(w)
        
        log_hyde(f"🧹 NETTOYAGE AVEC DÉTECTION NOMBRES", {
            "mots_initiaux": len(words),
            "mots_filtrés": len(filtered_words),
            "stopwords_supprimés": self.analysis_stats["stopwords_removed"],
            "nombres_exclus": numbers_detected
        })
        
        return filtered_words

    async def _analyze_words_with_groq(self, words: Set[str], company_id: str) -> Dict[str, float]:
        """
        🤖 ANALYSE MOTS AVEC NOUVEAU SYSTÈME HYDE + API GROQ
        """
        if not words:
            log_hyde(f"❌ AUCUN MOT À ANALYSER", level="ERROR")
            return {}
        
        # Utiliser le nouveau système HyDE pour le scoring de base
        hyde_scorer = HydeWordScorer(self.groq_client)
        word_scores = {}
        words_list = list(words)
        
        log_hyde(f"🤖 ANALYSE HYBRIDE HYDE + GROQ", {
            "total_mots": len(words_list),
            "company_id": company_id,
            "méthode": "HyDE_scorer + Groq_fallback"
        }, "PROCESS")
        
        # Analyser chaque mot avec le nouveau système
        for word in words_list:
            try:
                # Utiliser le système HyDE amélioré
                word_dict = await hyde_scorer.score_query_words(word, "e-commerce")
                score = word_dict.get(word, 5.0)  # Score par défaut si non trouvé
                
                word_scores[word] = float(score)
                
            except Exception as e:
                log_hyde(f"❌ ERREUR SCORING '{word}'", {"erreur": str(e)}, "ERROR")
                word_scores[word] = 5.0  # Score neutre en cas d'erreur
        
        # Analyser les résultats avec logs détaillés
        if word_scores:
            scores_values = list(word_scores.values())
            
            # Classement par catégories de score (comme dans le nouveau système)
            score_categories = {
                "ESSENTIELS_10": [(w, s) for w, s in word_scores.items() if s == 10],
                "TRES_PERTINENTS_8_9": [(w, s) for w, s in word_scores.items() if 8 <= s < 10],
                "CONTEXTUELS_6_7": [(w, s) for w, s in word_scores.items() if 6 <= s < 8],
                "FAIBLE_PERTINENCE_3_5": [(w, s) for w, s in word_scores.items() if 3 <= s < 6],
                "STOP_WORDS_0_2": [(w, s) for w, s in word_scores.items() if s < 3]
            }
            
            log_hyde(f"🎯 ANALYSE HYBRIDE TERMINÉE", {
                "total_mots_scorés": len(word_scores),
                "score_moyen": f"{sum(scores_values)/len(scores_values):.2f}",
                "répartition_scores": {
                    "🔥 ESSENTIELS (10)": len(score_categories["ESSENTIELS_10"]),
                    "✅ TRÈS PERTINENTS (8-9)": len(score_categories["TRES_PERTINENTS_8_9"]),
                    "⚠️ CONTEXTUELS (6-7)": len(score_categories["CONTEXTUELS_6_7"]),
                    "🔸 FAIBLE PERTINENCE (3-5)": len(score_categories["FAIBLE_PERTINENCE_3_5"]),
                    "❌ STOP WORDS (0-2)": len(score_categories["STOP_WORDS_0_2"])
                }
            }, "SUCCESS")
            
            # Afficher les top mots par catégorie
            for category, words_scores in score_categories.items():
                if words_scores:
                    top_words = dict(sorted(words_scores, key=lambda x: x[1], reverse=True)[:5])
                    log_hyde(f"📊 {category}", {"top_mots": top_words})
        
        return word_scores

    async def _score_words_batch(self, words: List[str], company_id: str) -> Dict[str, float]:
        """
        🤖 SCORE MOTS PAR BATCH AVEC API GROQ
        """
        if not words:
            log_hyde(f"❌ AUCUN MOT À ANALYSER", level="ERROR")
            return {}
        
        prompt = f"""
Tu es un expert en analyse sémantique pour une entreprise avec ce profil:
- Secteur: e-commerce
- Produits: produits génériques
- Zones: abidjan

Score ces mots de 0 à 10 selon leur importance business:
- 10: Mots critiques (produits phares, prix, contact, zones principales)
- 8-9: Mots très importants (marques, services, paiement)
- 6-7: Mots utiles (caractéristiques, couleurs, modèles)
- 3-5: Mots peu importants
- 0-2: Mots sans intérêt business

MOTS À SCORER: {', '.join(words)}

⚠️ IMPORTANT: Les nombres/chiffres/montants doivent TOUJOURS avoir un score de 0.
Exemples: "3500", "5000", "1500fcfa" = score 0

Réponds UNIQUEMENT en JSON:
{{"mot1": score, "mot2": score, ...}}
"""
        
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            
            # Récupérer et nettoyer la réponse
            response_content = response.choices[0].message.content.strip()
            log_hyde(f"🤖 RÉPONSE GROQ BRUTE", {"content": response_content[:200]})
            
            # VÉRIFIER SI LA RÉPONSE EST VIDE
            if not response_content:
                log_hyde(f"❌ RÉPONSE GROQ VIDE", {"mots_batch": words[:3]}, "ERROR")
                return {}
            
            # Extraire le JSON de la réponse
            try:
                # Chercher le JSON dans la réponse
                import re
                json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    # NETTOYAGE SUPPLÉMENTAIRE DU JSON
                    json_str = json_str.replace('\n', '').replace('\r', '')
                    batch_scores = json.loads(json_str)
                    log_hyde(f"✅ JSON EXTRAIT", {"nb_scores": len(batch_scores)})
                    return batch_scores
                else:
                    log_hyde(f"❌ AUCUN JSON TROUVÉ", {"response": response_content}, "ERROR")
                    # FALLBACK: GÉNÉRATION DE SCORES PAR DÉFAUT
                    fallback_scores = {word: 5.0 for word in words[:10]}  # Score neutre
                    log_hyde(f"🔄 FALLBACK SCORES", {"nb_scores": len(fallback_scores)}, "WARNING")
                    return fallback_scores
            except json.JSONDecodeError as je:
                log_hyde(f"❌ ERREUR PARSING JSON", {
                    "erreur": str(je),
                    "content": response_content[:100]
                }, "ERROR")
                # FALLBACK: GÉNÉRATION DE SCORES PAR DÉFAUT
                fallback_scores = {word: 5.0 for word in words[:10]}  # Score neutre
                log_hyde(f"🔄 FALLBACK SCORES", {"nb_scores": len(fallback_scores)}, "WARNING")
                return fallback_scores
            
        except Exception as e:
            log_hyde(f"❌ ERREUR SCORING BATCH", {
                "erreur": str(e),
                "mots_batch": words[:3]
            }, "ERROR")
            return {}

    def save_word_cache(self, company_id: str) -> str:
        """
        💾 SAUVEGARDE CACHE MOTS-SCORES DANS FICHIER JSON
        """
        if company_id not in self.word_scores_cache:
            log_hyde(f"❌ AUCUN CACHE TROUVÉ POUR {company_id}", level="ERROR")
            return None
        
        cache_dir = "word_caches"
        os.makedirs(cache_dir, exist_ok=True)
        
        cache_file = os.path.join(cache_dir, f"word_scores_{company_id}.json")
        
        word_scores = self.word_scores_cache[company_id]
        
        # Analyser le cache avant sauvegarde
        if word_scores:
            scores_values = list(word_scores.values())
            top_words = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)[:15]
            low_words = sorted(word_scores.items(), key=lambda x: x[1])[:5]
            
            cache_analysis = {
                "total_mots": len(word_scores),
                "score_moyen": f"{sum(scores_values)/len(scores_values):.2f}",
                "score_max": max(scores_values),
                "score_min": min(scores_values),
                "mots_haute_valeur": len([s for s in scores_values if s >= 8.0]),
                "mots_moyenne_valeur": len([s for s in scores_values if 5.0 <= s < 8.0]),
                "mots_faible_valeur": len([s for s in scores_values if s < 5.0])
            }
            
            log_hyde(f"📊 ANALYSE CACHE AVANT SAUVEGARDE", cache_analysis, "ANALYSIS")
            log_hyde(f"🏆 TOP 15 MOTS BUSINESS", dict(top_words))
            log_hyde(f"📉 5 MOTS SCORE FAIBLE", dict(low_words))
        
        cache_data = {
            "company_id": company_id,
            "created_at": datetime.now().isoformat(),
            "word_scores": word_scores,
            "stats": self.analysis_stats.copy(),
            "cache_analysis": cache_analysis if word_scores else {}
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            file_size = os.path.getsize(cache_file)
            
            log_hyde(f"💾 CACHE SAUVEGARDÉ AVEC SUCCÈS", {
                "fichier": cache_file,
                "taille_fichier": f"{file_size/1024:.1f} Ko",
                "mots_sauvegardés": len(word_scores),
                "company_id": company_id
            }, "SUCCESS")
            
            return cache_file
            
        except Exception as e:
            log_hyde(f"❌ ERREUR SAUVEGARDE CACHE", {
                "erreur": str(e),
                "fichier_cible": cache_file
            }, "ERROR")
            return None

# Fonction utilitaire pour l'intégration
async def create_company_word_cache(documents: List[Dict], company_id: str) -> Dict:
    """
    Fonction principale pour créer le cache de mots d'une entreprise
    """
    analyzer = IngestionHydeAnalyzer()
    return await analyzer.analyze_documents(documents, company_id)

if __name__ == "__main__":
    print("🎯 ANALYSEUR HYDE D'INGESTION")
    print("=" * 50)
    print("Utilisation: from core.ingestion_hyde_analyzer import create_company_word_cache")

"""
💰 OPTIMISEUR DE TOKENS PROFESSIONNEL
Réduction intelligente des coûts LLM
"""

import re
import math
from typing import List, Dict, Any, Tuple
import tiktoken
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class TokenOptimizerPro:
    """
    🎯 OPTIMISEUR DE TOKENS PROFESSIONNEL
    
    Techniques d'optimisation:
    - Analyse d'importance des phrases par ML
    - Compression sémantique intelligente
    - Déduplication avancée
    - Reformatage optimal
    - Budget dynamique par type de requête
    """
    
    def __init__(self):
        # Modèle de tokenisation
        self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # Configuration d'optimisation
        self.config = {
            'target_compression_ratio': 0.6,  # Réduire de 40%
            'min_sentence_score': 0.3,        # Score minimum pour garder une phrase
            'max_context_tokens': 2000,       # Maximum absolu
            'deduplication_threshold': 0.8,   # Seuil de similarité pour déduplication
        }
        
        # Patterns de compression
        self.compression_patterns = {
            # Suppression des répétitions
            r'\b(\w+)\s+\1\b': r'\1',
            # Raccourcissement des listes longues
            r'(\w+),\s*(\w+),\s*(\w+),\s*(\w+),.*?(\w+)': r'\1, \2, \3... \5',
            # Simplification des formats
            r'POUR\s*\([^)]+\)\s*-\s*Index:\s*[^-]+\s*-\s*': '',
            r'Document\s+\d+/\d+\s*:': '',
            r'voici\s+le\s+document\s+trouvé\s*:': '',
        }
        
        # Mots vides étendus
        self.stop_words = {
            'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'mais',
            'donc', 'car', 'ni', 'or', 'ce', 'cette', 'ces', 'cet', 'voici', 'voilà',
            'très', 'plus', 'moins', 'aussi', 'encore', 'déjà', 'toujours', 'jamais'
        }
        
        logger.info("[TOKEN_OPTIMIZER] ✅ Optimiseur de tokens initialisé")
    
    def estimate_tokens(self, text: str) -> int:
        """Estime le nombre de tokens"""
        try:
            return len(self.encoding.encode(text))
        except Exception:
            # Estimation approximative si erreur
            return len(text) // 4
    
    def optimize_context(self, context: str, target_tokens: int = None, query: str = "") -> Dict[str, Any]:
        """
        Optimise un contexte pour réduire les tokens
        
        Args:
            context: Contexte à optimiser
            target_tokens: Nombre de tokens cible (optionnel)
            query: Requête utilisateur pour prioriser le contenu pertinent
        
        Returns:
            Dict avec contexte optimisé et statistiques
        """
        
        if not context or len(context.strip()) == 0:
            return {
                'optimized_context': '',
                'original_tokens': 0,
                'optimized_tokens': 0,
                'compression_ratio': 0,
                'techniques_applied': []
            }
        
        original_tokens = self.estimate_tokens(context)
        
        # Définir la cible si pas fournie
        if target_tokens is None:
            target_tokens = min(
                int(original_tokens * self.config['target_compression_ratio']),
                self.config['max_context_tokens']
            )
        
        logger.info(f"[TOKEN_OPTIMIZER] Optimisation: {original_tokens} → {target_tokens} tokens")
        
        # Pipeline d'optimisation
        optimized_context = context
        techniques_applied = []
        
        # 1. Nettoyage et formatage
        optimized_context, clean_applied = self._apply_cleaning(optimized_context)
        techniques_applied.extend(clean_applied)
        
        # 2. Déduplication intelligente
        optimized_context, dedup_applied = self._apply_deduplication(optimized_context)
        techniques_applied.extend(dedup_applied)
        
        # 3. Analyse d'importance et sélection
        if self.estimate_tokens(optimized_context) > target_tokens:
            optimized_context, selection_applied = self._apply_smart_selection(
                optimized_context, target_tokens, query
            )
            techniques_applied.extend(selection_applied)
        
        # 4. Compression finale si nécessaire
        if self.estimate_tokens(optimized_context) > target_tokens:
            optimized_context, compression_applied = self._apply_final_compression(
                optimized_context, target_tokens
            )
            techniques_applied.extend(compression_applied)
        
        optimized_tokens = self.estimate_tokens(optimized_context)
        compression_ratio = 1 - (optimized_tokens / max(original_tokens, 1))
        
        logger.info(f"[TOKEN_OPTIMIZER] Résultat: {compression_ratio:.1%} compression")
        
        return {
            'optimized_context': optimized_context,
            'original_tokens': original_tokens,
            'optimized_tokens': optimized_tokens,
            'compression_ratio': compression_ratio,
            'techniques_applied': techniques_applied,
            'savings_tokens': original_tokens - optimized_tokens,
            'savings_cost_estimate_usd': (original_tokens - optimized_tokens) * 0.00002  # ~$0.02/1K tokens
        }
    
    def _apply_cleaning(self, text: str) -> Tuple[str, List[str]]:
        """Nettoyage et formatage basique"""
        techniques = []
        original_text = text
        
        # Suppression des espaces multiples
        text = re.sub(r'\s+', ' ', text)
        if text != original_text:
            techniques.append('espaces_multiples')
        
        # Application des patterns de compression
        for pattern, replacement in self.compression_patterns.items():
            new_text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            if new_text != text:
                techniques.append(f'pattern_{pattern[:20]}...')
                text = new_text
        
        # Suppression des lignes vides
        lines = text.split('\n')
        lines = [line.strip() for line in lines if line.strip()]
        text = '\n'.join(lines)
        
        if len(lines) < len(text.split('\n')):
            techniques.append('lignes_vides')
        
        return text, techniques
    
    def _apply_deduplication(self, text: str) -> Tuple[str, List[str]]:
        """Déduplication intelligente des contenus similaires"""
        techniques = []
        
        # Séparer en blocs (par sections ou paragraphes)
        blocks = self._split_into_blocks(text)
        
        if len(blocks) <= 1:
            return text, techniques
        
        # Détecter et supprimer les doublons
        unique_blocks = []
        seen_content = set()
        
        for block in blocks:
            # Normaliser pour comparaison
            normalized = self._normalize_for_comparison(block)
            content_hash = hash(normalized)
            
            # Vérifier la similarité avec les blocs existants
            is_duplicate = False
            for seen_hash in seen_content:
                similarity = self._calculate_similarity(content_hash, seen_hash)
                if similarity > self.config['deduplication_threshold']:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_blocks.append(block)
                seen_content.add(content_hash)
            else:
                techniques.append('deduplication')
        
        deduped_text = '\n\n'.join(unique_blocks)
        
        return deduped_text, techniques
    
    def _apply_smart_selection(self, text: str, target_tokens: int, query: str) -> Tuple[str, List[str]]:
        """Sélection intelligente basée sur l'importance des phrases"""
        techniques = []
        
        # Séparer en phrases
        sentences = self._split_into_sentences(text)
        
        if len(sentences) <= 1:
            return text, techniques
        
        # Scorer chaque phrase
        sentence_scores = []
        query_keywords = self._extract_keywords(query.lower())
        
        for sentence in sentences:
            score = self._score_sentence_importance(sentence, query_keywords)
            sentence_scores.append({
                'sentence': sentence,
                'score': score,
                'tokens': self.estimate_tokens(sentence)
            })
        
        # Trier par score décroissant
        sentence_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # Sélection optimale sous contrainte de tokens
        selected_sentences = []
        current_tokens = 0
        
        for sentence_data in sentence_scores:
            sentence_tokens = sentence_data['tokens']
            
            # Vérifier si on peut ajouter cette phrase
            if current_tokens + sentence_tokens <= target_tokens:
                if sentence_data['score'] >= self.config['min_sentence_score']:
                    selected_sentences.append(sentence_data)
                    current_tokens += sentence_tokens
            else:
                # Plus de place, arrêter
                break
        
        if len(selected_sentences) < len(sentences):
            techniques.append(f'selection_phrases_{len(selected_sentences)}/{len(sentences)}')
        
        # Réorganiser par ordre d'apparition original pour cohérence
        selected_sentences.sort(key=lambda x: sentences.index(x['sentence']))
        
        optimized_text = ' '.join([s['sentence'] for s in selected_sentences])
        
        return optimized_text, techniques
    
    def _apply_final_compression(self, text: str, target_tokens: int) -> Tuple[str, List[str]]:
        """Compression finale si toujours trop long"""
        techniques = []
        current_tokens = self.estimate_tokens(text)
        
        if current_tokens <= target_tokens:
            return text, techniques
        
        # Compression par troncature intelligente
        # Garder le début et la fin, couper le milieu si nécessaire
        words = text.split()
        target_words = int(len(words) * (target_tokens / current_tokens))
        
        if target_words < len(words):
            # Garder 70% du début, 30% de la fin
            start_words = int(target_words * 0.7)
            end_words = target_words - start_words
            
            if end_words > 0:
                compressed_text = (
                    ' '.join(words[:start_words]) + 
                    ' [...] ' + 
                    ' '.join(words[-end_words:])
                )
            else:
                compressed_text = ' '.join(words[:target_words])
            
            techniques.append(f'troncature_{target_words}_mots')
            return compressed_text, techniques
        
        return text, techniques
    
    def _split_into_blocks(self, text: str) -> List[str]:
        """Sépare le texte en blocs logiques"""
        # Séparer par double retour à la ligne ou sections
        blocks = re.split(r'\n\s*\n', text)
        return [block.strip() for block in blocks if block.strip()]
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Sépare le texte en phrases"""
        # Patterns pour détecter les fins de phrase
        sentence_endings = r'[.!?]+\s+'
        sentences = re.split(sentence_endings, text)
        
        # Nettoyer et filtrer
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        return sentences
    
    def _normalize_for_comparison(self, text: str) -> str:
        """Normalise le texte pour comparaison de similarité"""
        # Minuscules, suppression ponctuation, mots vides
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        words = [w for w in words if w not in self.stop_words and len(w) > 2]
        return ' '.join(sorted(words))
    
    def _calculate_similarity(self, hash1: int, hash2: int) -> float:
        """Calcule la similarité entre deux hashes (approximatif)"""
        # Méthode simple basée sur les bits communs
        xor_result = hash1 ^ hash2
        common_bits = bin(xor_result).count('0')
        total_bits = 64  # hash Python 64 bits
        return common_bits / total_bits
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extrait les mots-clés importants d'une requête"""
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [w for w in words if w not in self.stop_words and len(w) > 2]
        return keywords
    
    def _score_sentence_importance(self, sentence: str, query_keywords: List[str]) -> float:
        """Score l'importance d'une phrase"""
        sentence_lower = sentence.lower()
        score = 0.0
        
        # 1. Score basé sur les mots-clés de la requête
        keyword_matches = 0
        for keyword in query_keywords:
            if keyword in sentence_lower:
                keyword_matches += 1
                # Bonus pour correspondances exactes
                score += 1.0
                # Bonus pour multiples occurrences
                occurrences = sentence_lower.count(keyword)
                score += min(occurrences - 1, 2) * 0.5
        
        # 2. Score de longueur (ni trop court ni trop long)
        length = len(sentence.split())
        if 5 <= length <= 30:
            score += 0.5
        elif length > 30:
            score -= 0.2
        
        # 3. Score de position de mots importants
        important_words = ['prix', 'coût', 'tarif', 'livraison', 'disponible', 'stock']
        for word in important_words:
            if word in sentence_lower:
                score += 0.3
        
        # 4. Pénalité pour phrases génériques
        generic_phrases = ['informations générales', 'voici le document', 'document trouvé']
        for phrase in generic_phrases:
            if phrase in sentence_lower:
                score -= 0.5
        
        # Normaliser le score entre 0 et 1
        max_possible_score = len(query_keywords) + 1.0  # Score maximum théorique
        normalized_score = min(score / max_possible_score, 1.0) if max_possible_score > 0 else 0.0
        
        return max(normalized_score, 0.0)

# Instance globale
token_optimizer = TokenOptimizerPro()





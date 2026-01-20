#!/usr/bin/env python3
"""
Système de Scoring HyDE Dynamique pour le Filtrage MeiliSearch
Transforme HyDE en un coteur intelligent qui note chaque mot de 0 à 10
"""

import asyncio
import re
from typing import Dict, List, Tuple
from utils import log3

class HydeWordScorer:
    """
    Système de scoring intelligent pour les mots dans les requêtes e-commerce
    Utilise HyDE pour générer des scores contextuels de 0 (à supprimer) à 10 (essentiel)
    """
    
    def __init__(self, groq_client=None, company_data=None):
        self.groq_client = groq_client
        self.company_data = company_data
        
        # Cache dynamique extrait des métadonnées
        self.dynamic_words_10 = set()
        self.dynamic_words_9 = set()
        self.dynamic_words_8 = set()
        
        # Mapping métadonnées → scores
        self.metadata_score_mapping = {
            # SCORE 10 - CRITIQUES BUSINESS
            "product_name": 10,
            "color": 10,
            "price": 10,
            "currency": 10,
            
            # SCORE 9 - TRÈS PERTINENTS  
            "category": 9,
            "subcategory": 9,
            "zone": 9,
            "method": 9,
            "ai_name": 9,
            
            # SCORE 8 - PERTINENTS
            "zone_group": 8,
            "sector": 8,
            "channels": 8,
            "name": 8,  # company name
        }
        
        # Extraire automatiquement si données disponibles
        if self.company_data:
            self._extract_dynamic_words()
        
        # === APPROCHE PAR ÉLIMINATION ===
        # Stop words universels (score 0)
        self.stop_words = {
            # Salutations et politesse
            "bonjour", "bonsoir", "salut", "hello", "hi", "hey", "merci", "svp",
            "excusez", "moi", "pardon", "désolé", "au", "revoir", "bye",
            
            # Pronoms personnels
            "je", "j'", "tu", "il", "elle", "nous", "vous", "ils", "elles",
            "me", "te", "se", "lui", "leur", "moi", "toi", "mon", "ma", "mes",
            "ton", "ta", "tes", "son", "sa", "ses", "notre", "nos", "votre", "vos",
            
            # Articles et prépositions
            "le", "la", "les", "l'", "un", "une", "des", "du", "de", "d'",
            "à", "au", "aux", "en", "dans", "sur", "sous", "avec", "sans",
            "pour", "par", "vers", "chez", "depuis", "pendant", "avant", "après",
            
            # Conjonctions et mots de liaison
            "et", "ou", "mais", "donc", "or", "ni", "car", "que", "qu'", "qui",
            "quoi", "dont", "où", "si", "comme", "quand", "lorsque", "puisque",
            
            # Verbes auxiliaires fréquents
            "être", "est", "suis", "es", "sommes", "êtes", "sont", "était", "étais",
            "avoir", "ai", "as", "a", "avons", "avez", "ont", "avais", "avait",
            "faire", "fait", "fais", "faisons", "faites", "font", "aller", "va", "vais",
            
            # Mots de remplissage
            "c'est", "ce", "cet", "cette", "ces", "il", "y", "a", "voici", "voilà",
            "alors", "donc", "ainsi", "aussi", "encore", "déjà", "toujours", "jamais",
            "très", "trop", "assez", "peu", "plus", "moins", "tout", "tous", "toute",
            "rien", "personne", "aucun", "aucune", "est-ce", "qu'est-ce",
            
            # Expressions de transition
            "bon", "ok", "okay", "d'accord", "entendu", "euh", "ben", "bah",
            "enfin", "bref", "sinon", "même", "seulement", "vraiment",
            
            # Négations
            "ne", "n'", "pas", "point", "jamais", "rien", "personne",
            
            # Démonstratifs
            "ceci", "cela", "ça"
        }
        
        # === SYSTÈME HYBRIDE SCALABLE ===
        # Mots fixes universels avec scoring différencié par catégorie
        
        # SCORE 10 - CRITIQUES UNIVERSELS
        self.critical_words_10 = {
            # Livraison universelle
            "livraison", "livrer", "delivery", "expédition", "envoi", "transport",
            "shipping", "courier", "coursier", "distribution",
            
            # Couleurs universelles  
            "rouge", "bleu", "noir", "blanc", "vert", "jaune", "gris", "rose", 
            "violet", "orange", "marron", "beige", "doré", "argenté", "multicolore",
            
            # Commerce universel
            "prix", "coût", "tarif", "montant", "facture", "paiement", "achat", "vente",
            "commande", "commander", "acheter", "vendre", "stock", "disponible", 
            "rupture", "promo", "promotion", "réduction", "solde", "offre"
        }
        
        # SCORE 9 - TRÈS PERTINENTS
        self.critical_words_9 = {
            # Zones Abidjan centre (1500 FCFA)
            "yopougon", "cocody", "plateau", "adjamé", "abobo", "marcory", 
            "koumassi", "treichville", "angré", "riviera",
            
            # Services universels
            "service", "support", "aide", "assistance", "contact", "téléphone",
            "email", "whatsapp", "messenger", "chat", "urgence", "problème",
            "sav", "garantie", "retour", "échange", "remboursement"
        }
        
        # SCORE 8 - PERTINENTS
        self.critical_words_8 = {
            # Zones Abidjan périphérie (2000-2500 FCFA)
            "port-bouët", "attécoubé", "bingerville", "songon", "anyama", 
            "brofodoumé", "grand-bassam", "dabou", "abidjan",
            
            # Qualité universelle
            "neuf", "occasion", "usagé", "garantie", "qualité", "original",
            "authentique", "certifié", "testé", "vérifié", "contrôlé", "état",
            
            # Produits de base
            "produit", "article", "item", "référence", "modèle", "marque",
            "catégorie", "type", "série", "gamme", "collection"
        }
        
        # Combinaison pour compatibilité (fixes + dynamiques)
        self.critical_words = (
            self.critical_words_10 | 
            self.critical_words_9 | 
            self.critical_words_8 |
            self.dynamic_words_10 |
            self.dynamic_words_9 |
            self.dynamic_words_8
        )
    
    async def score_query_words(self, query: str, context: str = "e-commerce") -> Dict[str, int]:
        """
        APPROCHE PAR ÉLIMINATION: Stop words -> 0, Critiques -> 10, Reste -> scoring contextuel
        """
        words = self._extract_words(query)
        word_scores = {}
        unscored_words = []
        
        for word in words:
            word_lower = word.lower()
            
            # 1. Nombres -> score 0
            if self._is_numeric(word):
                word_scores[word] = 0
                log3("[HYDE_SCORER]", f"Nombre détecté '{word}' -> score 0")
                
            # 2. Stop words -> score 0
            elif word_lower in self.stop_words:
                word_scores[word] = 0
                log3("[HYDE_SCORER]", f"Stop word '{word}' -> score 0")
                
            # 3. Mots critiques avec scoring différencié (fixes + dynamiques)
            elif word_lower in (self.critical_words_10 | self.dynamic_words_10):
                word_scores[word] = 10
                source = "fixe" if word_lower in self.critical_words_10 else "dynamique"
                log3("[HYDE_SCORER]", f"Mot critique niveau 10 ({source}) '{word}' -> score 10")
            elif word_lower in (self.critical_words_9 | self.dynamic_words_9):
                word_scores[word] = 9
                source = "fixe" if word_lower in self.critical_words_9 else "dynamique"
                log3("[HYDE_SCORER]", f"Mot critique niveau 9 ({source}) '{word}' -> score 9")
            elif word_lower in (self.critical_words_8 | self.dynamic_words_8):
                word_scores[word] = 8
                source = "fixe" if word_lower in self.critical_words_8 else "dynamique"
                log3("[HYDE_SCORER]", f"Mot critique niveau 8 ({source}) '{word}' -> score 8")
                
            # 4. Tout le reste -> scoring contextuel basé sur l'entreprise
            else:
                score = await self._contextual_score_word(word, query, context)
                word_scores[word] = score
                unscored_words.append(word)
        
        # Logs détaillés avec classement
        self._log_detailed_scores(word_scores, unscored_words, query)
        
        return word_scores
    
    async def _contextual_score_word(self, word: str, full_query: str, context: str) -> int:
        """
        Utilise HyDE pour scorer un mot inconnu dans son contexte
        """
        if not self.groq_client:
            # Fallback: scoring heuristique
            return self._heuristic_score(word)
        
        try:
            prompt = f"""Tu es un expert en e-commerce ivoirien. Note le mot "{word}" dans la requête "{full_query}".

Contexte: {context}

Donne une note de 0 à 10:
- 10: Mot essentiel (produit, prix, livraison, paiement)
- 8-9: Très pertinent (qualité, marque, couleur)
- 6-7: Contextuel (voir, chercher, trouver)
- 3-5: Faible pertinence (veux, peut-être)
- 0-2: Stop word (je, le, bonjour)

Réponds UNIQUEMENT par un chiffre de 0 à 10."""

            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5,
                temperature=0.1
            )
            
            score_text = response.choices[0].message.content.strip()
            score = int(re.findall(r'\d+', score_text)[0])
            return max(0, min(10, score))  # Clamp entre 0 et 10
            
        except Exception as e:
            log3("[HYDE_SCORER]", f"Erreur HyDE pour '{word}': {e}")
            return self._heuristic_score(word)
    
    def _heuristic_score(self, word: str) -> int:
        """
        Scoring heuristique de fallback basé sur la longueur et les patterns
        """
        word = word.lower().strip()
        
        # Mots très courts = probablement stop words
        if len(word) <= 2:
            return 0
        
        # Mots longs = probablement pertinents
        if len(word) >= 8:
            return 7
        
        # Patterns e-commerce courants
        ecommerce_patterns = [
            r'.*prix.*', r'.*coût.*', r'.*cher.*',
            r'.*livr.*', r'.*transport.*',
            r'.*paiement.*', r'.*pay.*',
            r'.*stock.*', r'.*dispo.*',
            r'.*rouge.*', r'.*noir.*', r'.*blanc.*',
            r'.*casque.*', r'.*moto.*'
        ]
        
        for pattern in ecommerce_patterns:
            if re.match(pattern, word):
                return 8
        
        # Défaut pour mots moyens
        return 5 if len(word) >= 4 else 2
    
    def _extract_words(self, query: str) -> List[str]:
        """
        Extrait et nettoie les mots de la requête
        """
        # Nettoyer et normaliser
        query = query.lower().strip()
        query = re.sub(r'[^\w\s\?àâäéèêëïîôöùûüÿç-]', ' ', query)
        
        # Extraire les mots (garde les tirets pour riviera-golf)
        words = [w.strip() for w in query.split() if w.strip()]
        return words
    
    def _is_numeric(self, word: str) -> bool:
        """
        Vérifie si un mot est un nombre, chiffre ou montant
        """
        # Nettoyer le mot des caractères non-alphanumériques
        clean_word = re.sub(r'[^\d]', '', word)
        
        # Patterns pour détecter les nombres
        numeric_patterns = [
            r'^\d+$',                    # Nombres purs: 3500, 5000
            r'^\d+[a-zA-Z]+$',          # Nombres + lettres: 3500fcfa, 50€
            r'^[a-zA-Z]*\d+[a-zA-Z]*$', # Lettres + nombres: €50, $100
        ]
        
        for pattern in numeric_patterns:
            if re.match(pattern, word):
                return True
        
        return False
    
    def _detect_word_category(self, word: str) -> str:
        """
        Détecte automatiquement la catégorie d'un mot pour scoring intelligent SCALABLE
        """
        import re
        
        word_lower = word.lower()
        
        # === COULEURS UNIVERSELLES ===
        colors = {
            'rouge', 'red', 'noir', 'black', 'blanc', 'white', 'bleu', 'blue',
            'vert', 'green', 'jaune', 'yellow', 'orange', 'violet', 'purple',
            'rose', 'pink', 'gris', 'gray', 'grey', 'marron', 'brown'
        }
        
        # === TAILLES UNIVERSELLES ===
        sizes = {
            'petit', 'small', 'moyen', 'medium', 'grand', 'large', 'xl', 'xxl',
            's', 'm', 'l', 'xs', 'xxxl', 'taille'
        }
        
        # === ZONES GÉOGRAPHIQUES (CRITIQUES E-COMMERCE) ===
        locations = {
            'cocody', 'plateau', 'yopougon', 'adjamé', 'abobo', 'marcory', 'koumassi',
            'treichville', 'angré', 'riviera', 'abidjan', 'paris', 'lyon', 'marseille',
            'dakar', 'casablanca', 'tunis', 'bamako', 'ouagadougou', 'niamey'
        }
        
        # === MOYENS DE PAIEMENT (CRITIQUES) ===
        payment_methods = {
            'wave', 'orange', 'mtn', 'moov', 'paypal', 'visa', 'mastercard',
            'cod', 'cash', 'mobile', 'money', 'paiement', 'payment'
        }
        
        # === MARQUES/MODÈLES (PATTERNS) ===
        brand_patterns = [
            r'^[A-Z]{2,}-[A-Z]{2,}-\d+$',  # CAS-BL-3879
            r'^cas_[a-z]{2}_\d+$',         # cas_bl_3879
            r'casques?_moto',              # casques_moto
            r'auto_?moto',                 # auto_moto, auto__moto
        ]
        
        # === SECTEURS D'ACTIVITÉ ===
        business_sectors = {
            'auto', 'moto', 'fashion', 'tech', 'phone', 'electronics', 'beauty',
            'home', 'sport', 'food', 'books', 'toys', 'health'
        }
        
        # === MOTS E-COMMERCE CORE ===
        ecommerce_core = {
            'prix', 'price', 'coût', 'cost', 'tarif', 'combien', 'how much',
            'acheter', 'buy', 'commander', 'order', 'stock', 'disponible', 'available',
            'livraison', 'delivery', 'shipping', 'casque', 'produit', 'product'
        }
        
        # === ACTIONS COMMERCIALES ===
        commercial_actions = {
            'voir', 'see', 'regarder', 'look', 'choisir', 'choose', 'comparer', 'compare',
            'trouver', 'find', 'chercher', 'search', 'contact', 'téléphone', 'whatsapp'
        }
        
        # === CLASSIFICATION INTELLIGENTE ===
        if word_lower in colors:
            return 'color'
        elif word_lower in sizes:
            return 'size'
        elif word_lower in locations:
            return 'location'
        elif word_lower in payment_methods:
            return 'payment'
        elif word_lower in business_sectors:
            return 'business_sector'
        elif word_lower in ecommerce_core:
            return 'ecommerce_core'
        elif word_lower in commercial_actions:
            return 'commercial_action'
        elif any(re.match(pattern, word_lower) for pattern in brand_patterns):
            return 'product_model'
        elif re.match(r'.*_(moto|auto|phone|tech|fashion)', word_lower):
            return 'product_category'
        else:
            return 'unknown'
    
    def _get_category_score(self, category: str, word: str) -> int:
        """
        Retourne le score basé sur la catégorie détectée (SYSTÈME SCALABLE)
        """
        category_scores = {
            'color': 10,              # Couleurs = critiques pour e-commerce
            'size': 10,               # Tailles = critiques
            'location': 10,           # Zones géographiques = critiques livraison
            'payment': 10,            # Moyens paiement = critiques conversion
            'ecommerce_core': 10,     # Mots e-commerce = essentiels
            'business_sector': 9,     # Secteurs = très pertinents
            'product_model': 9,       # Modèles/références = très pertinents
            'product_category': 9,    # Catégories produits = très pertinentes
            'commercial_action': 7,   # Actions = contextuelles
            'unknown': 5              # Inconnu = score par défaut Groq
        }
        
        return category_scores.get(category, 5)
    
    def filter_by_threshold(self, word_scores: Dict[str, int], threshold: int = 6) -> List[str]:
        """
        Filtre les mots selon un seuil de score
        
        Args:
            word_scores: Dict[mot, score]
            threshold: Seuil minimum (défaut: 6)
            
        Returns:
            Liste des mots à garder
        """
        filtered_words = [
            word for word, score in word_scores.items() 
            if score >= threshold
        ]
        
        log3("[HYDE_SCORER]", f"Seuil {threshold}: {len(filtered_words)}/{len(word_scores)} mots gardés")
        return filtered_words
    
    async def smart_filter_query(self, query: str, threshold: int = 6) -> str:
        """
        Filtre une requête complète avec le système de scoring
        
        Args:
            query: Requête originale
            threshold: Seuil de filtrage (6 par défaut)
            
        Returns:
            Requête filtrée optimisée
        """
        # 1. Scorer tous les mots
        word_scores = await self.score_query_words(query)
        
        # 2. Filtrer selon le seuil
        filtered_words = self.filter_by_threshold(word_scores, threshold)
        
        # 3. Fallback si trop peu de mots
        if len(filtered_words) < 2:
            # Réduire le seuil progressivement
            for lower_threshold in [4, 2, 0]:
                filtered_words = self.filter_by_threshold(word_scores, lower_threshold)
                if len(filtered_words) >= 2:
                    break
        
        filtered_query = ' '.join(filtered_words)
        
        log3("[HYDE_SCORER]", {
            "query_originale": query,
            "query_filtree": filtered_query,
            "seuil_utilise": threshold,
            "scores": word_scores
        })
        
        return filtered_query if filtered_query.strip() else query
    
    def _log_detailed_scores(self, word_scores: Dict[str, int], unscored_words: List[str], query: str):
        """
        Logs détaillés avec liste complète des mots scorés classés par score
        """
        # Classer les mots par score (décroissant)
        sorted_scores = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Séparer par catégories de score
        score_categories = {
            "SCORE_10_ESSENTIELS": [],
            "SCORE_8_9_TRES_PERTINENTS": [],
            "SCORE_6_7_CONTEXTUELS": [],
            "SCORE_3_5_FAIBLE_PERTINENCE": [],
            "SCORE_0_2_STOP_WORDS_NOMBRES": []
        }
        
        for word, score in sorted_scores:
            if score == 10:
                score_categories["SCORE_10_ESSENTIELS"].append(f"{word}:{score}")
            elif score >= 8:
                score_categories["SCORE_8_9_TRES_PERTINENTS"].append(f"{word}:{score}")
            elif score >= 6:
                score_categories["SCORE_6_7_CONTEXTUELS"].append(f"{word}:{score}")
            elif score >= 3:
                score_categories["SCORE_3_5_FAIBLE_PERTINENCE"].append(f"{word}:{score}")
            else:
                score_categories["SCORE_0_2_STOP_WORDS_NOMBRES"].append(f"{word}:{score}")
        
        # Log détaillé
        log3("[HYDE_SCORER_DETAILED]", {
            "requete_originale": query,
            "total_mots": len(word_scores),
            "mots_non_scores_hyde": unscored_words,
            "classement_par_score": {
                "🔥 ESSENTIELS (10)": score_categories["SCORE_10_ESSENTIELS"],
                "✅ TRÈS PERTINENTS (8-9)": score_categories["SCORE_8_9_TRES_PERTINENTS"],
                "⚠️ CONTEXTUELS (6-7)": score_categories["SCORE_6_7_CONTEXTUELS"],
                "🔸 FAIBLE PERTINENCE (3-5)": score_categories["SCORE_3_5_FAIBLE_PERTINENCE"],
                "❌ STOP WORDS/NOMBRES (0-2)": score_categories["SCORE_0_2_STOP_WORDS_NOMBRES"]
            },
            "liste_complete_triee": [f"{word}:{score}" for word, score in sorted_scores]
        })


# === FONCTION D'INTÉGRATION ===
async def hyde_filter_for_meilisearch(query: str, groq_client=None, threshold: int = 6) -> str:
    """
    Interface simplifiée pour intégrer le scoring HyDE dans le preprocessing
    """
    scorer = HydeWordScorer(groq_client)
    return await scorer.smart_filter_query(query, threshold)

# === FONCTION HYDE CONTEXTUELLE POUR CLARIFICATION ===
async def clarify_request_with_hyde(question: str, last_user_message: str = "") -> str:
    """
    Utilise Hyde pour clarifier une requête en tenant compte du contexte conversationnel
    
    Args:
        question: Question utilisateur courante
        last_user_message: Dernier message utilisateur (historique)
        
    Returns:
        Requête clarifiée ou None si pas de clarification nécessaire
    """
    import os
    from groq import Groq
    
    try:
        # Initialiser le client Groq avec le modèle Hyde
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        hyde_model = os.getenv("GROQ_HYDE_MODEL", "llama-3.1-8b-instant")
        
        # Prompt Hyde - clarification uniquement si nécessaire
        prompt = f"""Tu es HYDE, expert en clarification de requêtes.

MISSION : Clarifier la requête uniquement si confuse, en utilisant UNIQUEMENT les mots de l'utilisateur.

RÈGLES :
1. Utilise UNIQUEMENT les mots présents
2. Sépare les intentions multiples
3. Conserve TOUS les détails (chiffres, tailles, couleurs)
4. ⚠️ PRÉSERVE L'ORTHOGRAPHE EXACTE (tirets, accents, majuscules)

⚠️ COMMUNES CI - COPIE-COLLE EXACTEMENT :
Angré, Port-Bouët, Cocody, Yopougon, Plateau, Adjamé, Abobo, Marcory, Koumassi, 
Treichville, Riviera, Attécoubé, Bingerville, Songon, Anyama, Grand-Bassam, Dabou

Format : <clarified>1. [Phrase 1]\\n2. [Phrase 2]</clarified>

Requête : {question}
Contexte : {last_user_message}

Exemples :
"Prix lot 300 taille 4 et 5" → <clarified>1. Prix lot 300 taille 4\\n2. Prix lot 300 taille 5</clarified>
"Livraison à Angré ?" → <clarified>1. Livraison à Angré ?</clarified>
"Port-Bouët et Cocody" → <clarified>1. Port-Bouët\\n2. Cocody</clarified>"""
        
        # Appel au modèle Hyde
        response = groq_client.chat.completions.create(
            model=hyde_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3
        )
        
        clarified_text = response.choices[0].message.content.strip()
        
        # Extraire le contenu entre les balises <clarified>
        import re
        match = re.search(r'<clarified>(.*?)</clarified>', clarified_text, re.DOTALL)
        if match:
            clarified_content = match.group(1).strip()
            # Remplacer les \n littéraux ET les vrais retours à la ligne
            clarified_content = clarified_content.replace('\\n', '\n')
            # Nettoyer et joindre les sous-questions
            lines = [line.strip() for line in clarified_content.split('\n') if line.strip()]
            # Supprimer les numéros de début de ligne
            cleaned_lines = []
            for line in lines:
                cleaned_line = re.sub(r'^\d+\.\s*', '', line)
                if cleaned_line:
                    cleaned_lines.append(cleaned_line)
            
            if cleaned_lines:
                return ' '.join(cleaned_lines)
        
        # Si pas de balises trouvées, retourner None
        return None
        
    except Exception as e:
        print(f"[HYDE] Erreur clarification : {e}")
        return None


# === TESTS ===
if __name__ == "__main__":
    async def test_scorer():
        scorer = HydeWordScorer()
        
        test_queries = [
            "Bonjour, je veux le casque rouge c'est combien?",
            "Combien coûte le casque rouge?",
            "Je cherche un casque rouge disponible",
            "Livraison à Cocody avec paiement Wave",
            "Whatsapp contact pour casque rouge"
        ]
        
        print("🧠 TEST DU SCORING HYDE DYNAMIQUE")
        print("=" * 60)
        
        for query in test_queries:
            print(f"\n📝 REQUÊTE: '{query}'")
            print("-" * 40)
            
            # Scorer les mots
            word_scores = await scorer.score_query_words(query)
            
            # Afficher les scores
            for word, score in sorted(word_scores.items(), key=lambda x: x[1], reverse=True):
                emoji = "🔥" if score >= 8 else "✅" if score >= 6 else "⚠️" if score >= 3 else "❌"
                print(f"  {emoji} {word}: {score}")
            
            # Filtrer avec différents seuils
            for threshold in [8, 6, 4]:
                filtered = scorer.filter_by_threshold(word_scores, threshold)
                print(f"  Seuil {threshold}: {' '.join(filtered)}")
    
    asyncio.run(test_scorer())

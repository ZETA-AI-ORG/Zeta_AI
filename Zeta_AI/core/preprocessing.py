"""
🌍 SOLUTION UNIVERSELLE MULTI-ENTREPRISE
Preprocessing intelligent pour TOUTE entreprise et secteur
"""
import os
import re
import time
from typing import Dict, List, Tuple

class UniversalMeilisearchPreprocessor:
    def __init__(self):
        # LISTE ULTRA-EXHAUSTIVE DE MOTS PARASITES FRANÇAIS (500+ mots)
        self.stop_words = [
            # Déterminants
            'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'ce', 'cet', 'cette', 'ces',
            'mon', 'ma', 'mes', 'ton', 'ta', 'tes', 'son', 'sa', 'ses', 'notre', 'nos',
            'votre', 'vos', 'leur', 'leurs', 'quel', 'quelle', 'quels', 'quelles',
            'quelque', 'quelques', 'chaque', 'tout', 'toute', 'tous', 'toutes',
            'aucun', 'aucune', 'nul', 'nulle', 'certain', 'certaine', 'certains', 'certaines',
            
            # Prépositions
            'à', 'au', 'aux', 'avec', 'contre', 'dans', 'depuis', 'derrière', 'devant',
            'en', 'entre', 'envers', 'malgré', 'par', 'parmi', 'pendant', 'pour',
            'sans', 'selon', 'sous', 'sur', 'vers', 'chez', 'dès', 'jusque', 'jusqu',
            
            # Conjonctions
            'et', 'ou', 'ni', 'mais', 'car', 'donc', 'or', 'que', 'quand', 'comme',
            'si', 'lorsque', 'puisque', 'bien', 'quoique', 'afin', 'tandis',
            
            # Pronoms personnels, relatifs, interrogatifs
            'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles', 'me', 'te', 'se',
            'lui', 'leur', 'y', 'en', 'qui', 'que', 'dont', 'où', 'lequel', 'laquelle',
            'lesquels', 'lesquelles', 'duquel', 'desquels', 'desquelles',
            
            # Auxiliaires et verbes fréquents
            'être', 'avoir', 'faire', 'dire', 'aller', 'voir', 'savoir', 'pouvoir',
            'vouloir', 'venir', 'falloir', 'devoir', 'croire', 'trouve', 'prendre',
            'donner', 'porter', 'parler', 'aimer', 'passer', 'mettre', 'suivre',
            'vivre', 'sortir', 'partir', 'arriver', 'entrer', 'monter', 'rester',
            'devenir', 'tenir', 'sembler', 'laisser', 'penser', 'indiquer', 'montrer',
            
            # Adverbes de fréquence, intensité, manière
            'très', 'plus', 'moins', 'aussi', 'encore', 'déjà', 'jamais', 'toujours',
            'souvent', 'parfois', 'quelquefois', 'rarement', 'bien', 'mal', 'mieux',
            'pire', 'autant', 'tant', 'si', 'comment', 'pourquoi', 'quand', 'où',
            
            # Mots interrogatifs et exclamatifs
            'qui', 'que', 'quoi', 'quel', 'quelle', 'quels', 'quelles', 'comment',
            'pourquoi', 'quand', 'où', 'combien', 'coûte', 'coute', 'prix', 'tarif',
            'montant', 'coût', 'coûts', 'cher', 'chère', 'chers', 'chères', 'gratuit', 'payant',
            
            # Verbes modaux et d'état
            
            # === VERBES MODAUX ET AUXILIAIRES CONJUGUÉS ===
            'peux', 'peut', 'peuvent', 'pouvais', 'pouvait', 'pourra', 'pourront',
            'veux', 'veut', 'veulent', 'voulais', 'voulait', 'voudra', 'voudront',
            'dois', 'doit', 'doivent', 'devais', 'devait', 'devra', 'devront',
            'sais', 'sait', 'savent', 'savais', 'savait', 'saura', 'sauront',
            
            # === EXPRESSIONS TEMPORELLES ===
            'maintenant', 'actuellement', 'présentement', 'aujourd\'hui', 'hier',
            'demain', 'avant-hier', 'après-demain', 'bientôt', 'tard', 'tôt',
            'récemment', 'dernièrement', 'prochainement', 'immédiatement',
            
            # === MOTS DE QUANTITÉ VAGUES ===
            'beaucoup', 'peu', 'assez', 'trop', 'énormément', 'légèrement',
            'fortement', 'extrêmement', 'particulièrement', 'spécialement'
        ]

        # Patterns universels de questions business
        self.universal_patterns = {
            # Questions sur produits/services
            'products_services': re.compile(r'(?:quels?|quelles?)\s+(?:sont|avez)\s+.*(?:produits?|services?|articles?|offres?)', re.IGNORECASE),
            
            # Questions sur prix/tarifs
            'pricing': re.compile(r'(?:prix|tarifs?|coûts?|montants?|combien)', re.IGNORECASE),
            
            # Questions contact
            'contact': re.compile(r'(?:comment|où)\s+.*(?:contact|joindre|appeler|écrire|téléphone|email)', re.IGNORECASE),
            
            # Questions livraison/transport
            'delivery': re.compile(r'(?:livraison|livrer|expédition|transport|acheminement|délai)', re.IGNORECASE),
            
            # Questions horaires/disponibilité
            'availability': re.compile(r'(?:horaires?|ouvert|fermé|disponible|quand)', re.IGNORECASE),
            
            # Questions localisation
            'location': re.compile(r'(?:où|adresse|situé|localisation|magasin|bureau)', re.IGNORECASE),
            
            # Questions générales sur l'entreprise
            'company_info': re.compile(r'(?:qui|qu\'est|entreprise|société|activité|spécialité)', re.IGNORECASE),
            
            # Questions conditions/modalités
            'terms': re.compile(r'(?:conditions?|modalités?|garantie|retour|échange)', re.IGNORECASE)
        }

        # Mots-clés universels à ajouter selon le contexte
        self.contextual_keywords = {
            'products_services': ['produits', 'services', 'catalogue', 'gamme', 'offre'],
            # Keep only a single canonical keyword for pricing to avoid dilution
            'pricing': ['prix'],
            'contact': ['contact', 'téléphone', 'email', 'adresse'],
            'delivery': ['livraison', 'transport', 'expédition', 'délai'],
            'availability': ['horaires', 'ouvert', 'disponible'],
            'location': ['adresse', 'localisation', 'magasin', 'bureau'],
            'company_info': ['entreprise', 'société', 'activité', 'présentation'],
            'terms': ['conditions', 'modalités', 'garantie', 'service']
        }

    def preprocess_query(self, query: str, options: Dict = None) -> Dict:
        """🔥 FONCTION PRINCIPALE UNIVERSELLE"""
        if options is None:
            options = {}
            
        start_time = time.time()
        
        # Query preprocessing silencieux

        # 1. Nettoyage initial
        clean_query = self.initial_cleanup(query)
        
        # 2. Détection du type de question (universel)
        query_type = self.detect_universal_query_type(clean_query)


        # 3. Extraction des mots-clés significatifs
        keywords = self.extract_significant_keywords(clean_query)


        # 4. Enrichissement contextuel universel
        keywords = self.add_universal_context(keywords, query_type)


        # 5. Optimisation finale
        final_keywords = self.optimize_keywords(keywords)
        if os.getenv("DEBUG_PREPROCESS") == "1":
            print(f"[PREPROCESS] Mots-clés: '{final_keywords[:50]}...'")

        processing_time = (time.time() - start_time) * 1000

        return {
            'original': query,
            'keywords': final_keywords,
            'type': query_type,
            'confidence': self.calculate_universal_confidence(query, final_keywords),
            'processing_time': f"{processing_time:.1f}ms",
            'word_count': len(final_keywords.split())
        }

    def initial_cleanup(self, query: str) -> str:
        """Nettoyage initial universel"""
        return re.sub(r'\s+', ' ', 
                     re.sub(r'[?!.,;:()\'""]', ' ', query.lower().strip())
                     ).strip()

    def detect_universal_query_type(self, query: str) -> str:
        """Détection universelle du type de question"""
        max_score = 0
        detected_type = 'general'

        for pattern_type, pattern in self.universal_patterns.items():
            match = pattern.search(query)
            if match:
                # Score basé sur la spécificité du pattern
                score = len(match.group(0))
                
                if score > max_score:
                    max_score = score
                    detected_type = pattern_type

        return detected_type

    def extract_significant_keywords(self, query: str) -> str:
        """Extraction des mots-clés significatifs (universel)
        COUCHE 2 : Filtrage post-HyDE avec liste exhaustive de 500+ mots parasites
        """
        words = query.split()
        significant_words = []

        for word in words:
            if len(word) > 2 and word not in self.stop_words:
                significant_words.append(word)

        return ' '.join(significant_words)


async def post_hyde_filter(query, business_keywords=None, groq_client=None, threshold=6, company_id=None, business_config=None):
    """
    Filtre intelligent 100% HyDE - L'IA analyse l'intention et score chaque mot
    HyDE détermine la pertinence de chaque mot selon l'intention détectée
    """
    try:
        from core.pure_hyde_scorer import pure_hyde_filter
        
        # HyDE analyse l'intention complète et score intelligemment
        filtered_query = await pure_hyde_filter(
            query=query,
            company_id=company_id or "default",
            groq_client=groq_client,
            business_config=business_config,
            threshold=threshold
        )
        
        # Log pour debugging
        log3("[PURE_HYDE_FILTER]", f"'{query}' → '{filtered_query}' (seuil: {threshold})")
        
        return filtered_query
        
    except Exception as e:
        # Fallback vers système simple si HyDE indisponible
        log3("[PURE_HYDE_FILTER]", f"Erreur HyDE, fallback: {e}")
        from core.smart_stopwords import filter_query_for_meilisearch
        return filter_query_for_meilisearch(query)

    def is_business_relevant(self, word: str) -> bool:
        """Vérifie si un mot est pertinent pour le business (universel)"""
        business_words = [
            # Produits/Services
            'produit', 'service', 'article', 'offre', 'gamme', 'catalogue', 'casque', 'équipement',
            
            # Commerce - MOTS-CLÉS CRITIQUES AJOUTÉS
            'prix', 'tarif', 'coût', 'montant', 'vente', 'achat', 'commande', 'combien', 'cher', 'coûte',
            
            # Intentions d'achat - NOUVEAUX
            'veux', 'voudrais', 'cherche', 'besoin', 'intéresse', 'acheter',
            
            # Couleurs et caractéristiques - NOUVEAUX
            'rouge', 'bleu', 'noir', 'blanc', 'vert', 'jaune', 'rose', 'gris',
            
            # Contact/Communication
            'contact', 'téléphone', 'email', 'adresse', 'site', 'web', 'whatsapp',
            
            # Logistique
            'livraison', 'transport', 'expédition', 'délai', 'stock', 'disponible',
            
            # Temps/Disponibilité
            'horaire', 'ouvert', 'fermé', 'rdv',
            
            # Lieu
            'magasin', 'bureau', 'local', 'showroom', 'entrepôt', 'cocody', 'yopougon', 'abidjan',
            
            # Entreprise
            'entreprise', 'société', 'équipe', 'activité', 'spécialité',
            
            # Service client
            'garantie', 'retour', 'échange', 'sav', 'support',
            
            # Paiement - NOUVEAUX
            'paiement', 'wave', 'orange', 'mtn', 'moov', 'cash', 'espèces',
            
            # Spécifique produits divers
            'couches', 'bébé', 'taille', 'paquet', 'colis', 'hollandaises', 'culottes', 'moto', 'auto'
        ]

        # Vérifie correspondance exacte ou partielle
        return any(business_word in word or word in business_word 
                  for business_word in business_words)

    def add_universal_context(self, keywords: str, query_type: str) -> str:
        """Ajout de contexte universel (non intrusif)
        - N'ajoute qu'UN seul mot contextuel manquant (au plus)
        - Ne duplique pas les mots déjà présents
        """
        context_words = self.contextual_keywords.get(query_type, [])
        if not keywords:
            # si pas de mots-clés, ajouter au plus 1 mot contextuel
            return ' '.join(context_words[:1]) if context_words else ''

        existing = set(keywords.split())
        to_add = next((w for w in context_words if w not in existing), None)
        if to_add:
            return f"{keywords} {to_add}".strip()
        return keywords

    def optimize_keywords(self, keywords: str) -> str:
        """Optimisation finale des mots-clés"""
        if not keywords:
            return ''

        words = keywords.split()
        
        # Déduplication
        unique_words = list(dict.fromkeys(words))  # Préserve l'ordre
        
        # Limite à 8 mots max pour optimiser Meilisearch
        optimized_words = unique_words[:8]
        
        return ' '.join(optimized_words)

    def calculate_universal_confidence(self, original: str, keywords: str) -> float:
        """Calcul de confiance universel"""
        if not keywords:
            return 0.0

        original_words = len([w for w in original.split() if len(w) > 2])
        keyword_words = len(keywords.split())
        
        # Confiance basée sur le ratio de transformation et la pertinence
        transformation_ratio = keyword_words / max(original_words, 1)
        base_confidence = min(transformation_ratio * 100, 100)
        
        # Bonus si mots business détectés
        business_words_count = len([w for w in keywords.split() if self.is_business_relevant(w)])
        business_bonus = business_words_count * 10
        
        return min(base_confidence + business_bonus, 100)

    def run_universal_tests(self) -> None:
        """🧪 TESTS UNIVERSELS"""
        universal_test_queries = [
            # Commerce général
            "Quels sont vos produits et leurs prix ?",
            "Comment vous contacter ?",
            "Où êtes-vous situés ?",
            "Quels sont vos horaires d'ouverture ?",
            
            # Services
            "Proposez-vous un service de livraison ?",
            "Quelles sont vos conditions de garantie ?",
            "Comment passer une commande ?",
            
            # Spécifique RUEDUGROSSISTE
            "Avez-vous des couches pour bébé ?",
            "Quel est le prix des couches taille 3 ?",
            "Livrez-vous les couches à Abidjan ?"
        ]

        if os.getenv("DEBUG_PREPROCESS") == "1":
            print('🧪 TESTS UNIVERSELS MULTI-SECTEURS:\n')
        
        for index, query in enumerate(universal_test_queries, 1):
            if os.getenv("DEBUG_PREPROCESS") == "1":
                print(f"--- TEST UNIVERSEL {index} ---")
            result = self.preprocess_query(query)
            # Confiance calculée silencieusement
            if os.getenv("DEBUG_PREPROCESS") == "1":
                print(f"Temps: {result['processing_time']}\n")


# Instance globale pour réutilisation
universal_preprocessor = UniversalMeilisearchPreprocessor()

def preprocess_meilisearch_query(query: str) -> str:
    """
    Fonction utilitaire pour preprocessing rapide d'une requête Meilisearch
    """
    result = universal_preprocessor.preprocess_query(query)
    return result['keywords']

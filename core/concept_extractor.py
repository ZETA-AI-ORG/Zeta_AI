import re
from typing import Dict, List, Set

class ConceptExtractor:
    def __init__(self):
        # Liste dynamique de couleurs (français, extensible)
        self.color_list = [
            'blanc', 'noir', 'rouge', 'bleu', 'vert', 'jaune', 'rose', 'orange', 'gris', 'marron', 'violet', 'beige',
            'doré', 'argenté', 'turquoise', 'kaki', 'bordeaux', 'ivoire', 'multicolore', 'transparent', 'transparente',
            'clair', 'foncé', 'pastel', 'fluo', 'cuivré', 'camel', 'ambre', 'corail', 'indigo', 'olive', 'sable',
            'taupe', 'saumon', 'aubergine', 'anis', 'lilas', 'azur', 'marine', 'ciel', 'prune', 'menthe', 'chocolat',
            'caramel', 'café'
        ]
        color_pattern = r'(' + r'|'.join(self.color_list) + r')'
        # Patterns métier spécifiques
        self.patterns = {
            'product_terms': re.compile(r'(casque|couche|produit|article|équipement|moto|bébé|taille|paquet|quantité|modèle|variant)', re.I),
            'service_terms': re.compile(r'(livraison|service|installation|maintenance|transport|expédition)', re.I),
            'policy_terms': re.compile(r'(retour|garantie|politique|condition|stock|disponibilité)', re.I),
            'contact_terms': re.compile(r'(contact|téléphone|email|adresse|horaire|whatsapp|support)', re.I),
            'company_terms': re.compile(r'(mission|entreprise|société|activité|secteur|qui|nom)', re.I),
            # Étend la couverture aux communes d'Abidjan (insensible à la casse)
            'location_terms': re.compile(r'(Yopougon|Treichville|Plateau|Marcory|Koumassi|Adjamé|Attécoubé|Abobo|Port[- ]?Bouët|Port[- ]?Bouet|Cocody|Angré|Abidjan|Bingerville|Songon|Anyama|zone|quartier|ville|région|lieu)', re.I),
            'price_terms': re.compile(r'(prix|coût|tarif|combien|montant|frais)', re.I),
            'process_terms': re.compile(r'(commande|commander|acheter|processus|procédure)', re.I)
        }
        
        # Stopwords français étendus + prénoms + connecteurs + chiffres + mots conversationnels
        self.stopwords: Set[str] = {
            # Stopwords classiques
            'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'mais', 'donc', 'car',
            'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles', 'me', 'te', 'se', 'nous', 'vous',
            'mon', 'ma', 'mes', 'ton', 'ta', 'tes', 'son', 'sa', 'ses', 'notre', 'votre', 'leur', 'leurs',
            'ce', 'cette', 'ces', 'cet', 'ça', 'cela', 'celui', 'celle', 'ceux', 'celles',
            'qui', 'que', 'quoi', 'dont', 'où', 'quand', 'comment', 'pourquoi',
            'dans', 'sur', 'sous', 'avec', 'sans', 'pour', 'par', 'vers', 'chez', 'entre', 'parmi',
            'très', 'plus', 'moins', 'assez', 'trop', 'bien', 'mal', 'beaucoup', 'peu',
            'oui', 'non', 'si', 'peut', 'être', 'avoir', 'faire', 'aller', 'venir', 'voir', 'savoir',
            'suis', 'es', 'est', 'sommes', 'êtes', 'sont', 'ai', 'as', 'a', 'avons', 'avez', 'ont',
            'daccord', 'accord', 'ok', 'merci', 'bonjour', 'salut', 'bonsoir', 'aurevoir',
            'alors', 'donc', 'ainsi', 'aussi', 'encore', 'déjà', 'toujours', 'jamais', 'parfois',
            'ici', 'là', 'ailleurs', 'partout', 'nulle', 'part', 'loin', 'près', 'loind',
            # Prénoms courants (à étendre selon besoin)
            'jessica', 'paul', 'lucas', 'emma', 'chloe', 'antoine', 'julie', 'marc', 'lucie', 'sophie',
            'jean', 'pierre', 'marie', 'sarah', 'nicolas', 'thomas', 'aline', 'claire', 'laurent',
            # Connecteurs et mots conversationnels
            'alors', 'ensuite', 'premier', 'première', 'deuxième', 'troisième', 'quatrième', 'cinquième',
            'avant', 'après', 'maintenant', 'daccord', 'd’abord', 'dabord', 'sinon', 'choses', 'question',
            # Chiffres et nombres
            'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf', 'dix', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'
        }
        
        # Whitelist de termes métier valides
        self.business_terms: Set[str] = {
            'casque', 'casques', 'moto', 'motos', 'couche', 'couches', 'bébé', 'bébés',
            'produit', 'produits', 'article', 'articles', 'équipement', 'équipements',
            'prix', 'tarif', 'tarifs', 'coût', 'coûts', 'montant', 'frais',
            'livraison', 'transport', 'expédition', 'délai', 'délais',
            'taille', 'tailles', 'paquet', 'paquets', 'quantité', 'quantités',
            'rouge', 'bleu', 'vert', 'noir', 'blanc', 'jaune', 'rose',
            'stock', 'disponible', 'disponibilité', 'rupture',
            'commande', 'commander', 'acheter', 'achat', 'vente',
            'contact', 'téléphone', 'email', 'adresse', 'horaire', 'whatsapp',
            'retour', 'échange', 'garantie', 'politique', 'condition',
            # Lieux et communes d'Abidjan
            'Abidjan', 'Cocody', 'Angré', 'Yopougon', 'Treichville', 'Plateau', 'Marcory', 'Koumassi', 'Adjamé', 'Attécoubé', 'Abobo', 'Port-Bouët', 'Port Bouet', 'Bingerville', 'Songon', 'Anyama', 'zone', 'quartier', 'région',
            'entreprise', 'société', 'mission', 'activité', 'secteur'
        }
        
        # Patterns pour détecter les requêtes non-informationnelles
        self.non_informational_patterns = [
            re.compile(r'^(oui|non|ok|daccord|merci|bonjour|salut)$', re.I),
            re.compile(r'^(je suis|vous êtes|où êtes|comment allez)\b', re.I),
            re.compile(r'^(très bien|parfait|excellent|super)$', re.I)
        ]

    def _is_non_informational(self, query: str) -> bool:
        """Détecte si la requête est non-informationnelle (confirmation, salutation, etc.)"""
        query_clean = query.strip().lower()
        
        # Vérifier les patterns non-informationnels
        for pattern in self.non_informational_patterns:
            if pattern.search(query_clean):
                return True
        
        # Vérifier si la requête ne contient que des stopwords
        words = re.findall(r'\b\w+\b', query_clean)
        meaningful_words = [w for w in words if w not in self.stopwords and len(w) > 2]
        
        return len(meaningful_words) == 0

    def _extract_business_terms(self, query: str) -> List[str]:
        """Extrait uniquement les termes métier valides, ignore prénoms, connecteurs, chiffres, etc."""
        import re
        words = re.findall(r'\b\w+\b', query.lower())
        # Patterns pour détecter les chiffres, prénoms, connecteurs, etc.
        prenoms = {'jessica', 'paul', 'lucas', 'emma', 'chloe', 'antoine', 'julie', 'marc', 'lucie', 'sophie',
                   'jean', 'pierre', 'marie', 'sarah', 'nicolas', 'thomas', 'aline', 'claire', 'laurent'}
        connecteurs = {'alors', 'ensuite', 'premier', 'première', 'deuxième', 'troisième', 'quatrième', 'cinquième',
                       'avant', 'après', 'maintenant', 'daccord', 'd’abord', 'dabord', 'sinon', 'choses', 'question'}
        chiffres = {'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf', 'dix', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'}
        business_words = []
        for word in words:
            if (word in self.business_terms and
                word not in self.stopwords and
                word not in prenoms and
                word not in connecteurs and
                word not in chiffres):
                business_words.append(word)
        return business_words[:5]  # Limiter à 5 termes max

    def extract(self, user_query: str, meili_client=None, company_id: str = None) -> Dict[str, List[str]]:
        """
        Extraction robuste des concepts métier, avec filtrage contextuel si les informations de l'index sont fournies.
        """
        from utils import log3
        import re

        query = user_query.strip().lower()
        if self._is_non_informational(query):
            log3("[CONCEPTS] Requête non-informationnelle, arrêt.", query)
            return {}

        # Étape 1: Extraction brute basée sur les patterns regex
        initial_concepts = {}
        patterns = {
            'product_terms': r'(casque|couche|culotte|bébé|moto|produit|article|équipement|variant)',
            'quantity_terms': r'(\b\d+\s*(paquets?|cartons?|lots?|pièces?|packs?|unités|articles|produits|boîtes?)\b)',
            'size_terms': r'(\b\d+\s*(kg|g|grammes?|l|litres?|ml|cl|cm|mm)\b|\b([xs]l?|m|xxl|xl|l|s)\b|\btaille\s*\w+\b)',
            'color_terms': r'(' + '|'.join(self.color_list) + r')',
            'payment_terms': r'(espèces|livraison|wave|mobile money|paiement|comptant|à crédit|carte|orange money|moov money)',
            # Ajoute les communes pour permettre la détection (minuscule pour l'insensibilité à la casse plus loin)
            'location_terms': r'(abidjan|angré|cocody|yopougon|treichville|plateau|marcory|koumassi|adjamé|attécoubé|abobo|port[- ]?bouët|port[- ]?bouet|bingerville|songon|anyama|zone|quartier|ville|région|lieu)',
            'policy_terms': r'(retour|garantie|politique|condition|stock|disponibilité)',
            'contact_terms': r'(contact|téléphone|email|adresse|horaire|whatsapp|support)',
            'company_terms': r'(mission|entreprise|société|activité|secteur|qui|nom)'
        }

        for concept, pattern in patterns.items():
            matches = re.findall(pattern, query)
            if not matches:
                continue
            
            flat_matches = []
            for match in matches:
                if isinstance(match, tuple):
                    flat_matches.extend([m for m in match if m])
                else:
                    flat_matches.append(match)
            
            clean_matches = [term for term in flat_matches if term not in self.stopwords and len(term) > 1]
            if clean_matches:
                initial_concepts[concept] = list(dict.fromkeys(clean_matches))

        log3("[CONCEPTS][EXTRACT] Concepts initiaux (bruts)", str(initial_concepts))

        # Étape 2: Filtrage contextuel (si possible)
        if meili_client and company_id:
            from .meilisearch_utils import get_index_attributes
            bases = ["company", "products", "delivery", "support"]
            searchable_attributes = set()
            for base in bases:
                idx_name = f"{base}_{company_id}"
                try:
                    index_attrs = get_index_attributes(meili_client, idx_name)
                    sa = index_attrs.get('searchableAttributes', [])
                    fa = index_attrs.get('filterableAttributes', [])
                    for a in sa + fa:
                        searchable_attributes.add(a)
                except Exception as _e:
                    # Index absent possible, ignorer silencieusement
                    continue
            log3("[CONCEPTS][CONTEXT-AWARE] Attributs d'index disponibles (agrégés)", str(searchable_attributes))
            # NOTE: La logique de filtrage est un placeholder. Pour l'instant, nous ne modifions pas
            # les `initial_concepts` mais la structure est prête pour une logique plus fine.

        # Étape 3: Fallback si aucun concept n'a été trouvé
        if not initial_concepts:
            business_terms = self._extract_business_terms(query)
            if business_terms:
                initial_concepts['generic'] = business_terms[:3]
                log3("[CONCEPTS][FALLBACK] Utilisation des termes métier génériques", str(initial_concepts))

        log3("[CONCEPTS][FINAL] Concepts retournés", str(initial_concepts))
        # Expansion sémantique avant validation minimum
        try:
            expanded_concepts = self._expand_semantic_concepts(initial_concepts)
            if expanded_concepts:
                initial_concepts = expanded_concepts
        except Exception as e:
            log3("[CONCEPTS][EXPAND_ERR]", str(e))
        
        # Enforce minimum meaningful keyword count (>= 2) après expansion
        try:
            unique_terms: Set[str] = set()
            for vals in initial_concepts.values():
                for t in vals:
                    tt = str(t).strip().lower()
                    if tt and tt not in self.stopwords:
                        unique_terms.add(tt)
            if len(unique_terms) < 2:
                # Tentative fallback avec expansion forcée
                fallback_concepts = self._generate_fallback_concepts(user_query)
                if fallback_concepts:
                    log3("[CONCEPTS][FALLBACK] Utilisation concepts fallback", str(fallback_concepts))
                    return fallback_concepts
                log3("[CONCEPTS][REJECT] Trop peu de mots-clés utiles (<2)", str(unique_terms))
                return {}
        except Exception:
            # En cas d'erreur silencieuse, on retourne tout de même les concepts
            pass
        return initial_concepts

    def _expand_semantic_concepts(self, concepts: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Expansion sémantique des concepts extraits."""
        expanded = {}
        
        # Dictionnaire d'expansion sémantique
        semantic_expansions = {
            # Livraison
            'livraison': ['frais', 'délai', 'zone', 'transport', 'expédition'],
            'delivery': ['fee', 'cost', 'time', 'zone', 'shipping'],
            'frais': ['prix', 'coût', 'tarif'],
            'délai': ['temps', 'durée', 'rapidité'],
            
            # Géographie
            'yopougon': ['yop', 'commune', 'zone'],
            'adjamé': ['adjame', 'commune', 'zone'],
            'abobo': ['commune', 'zone'],
            'cocody': ['commune', 'zone'],
            
            # Produits
            'produit': ['article', 'item', 'catalogue'],
            'prix': ['tarif', 'coût', 'montant'],
            'couleur': ['teinte', 'coloris'],
            'taille': ['dimension', 'format'],
            
            # Support
            'contact': ['téléphone', 'whatsapp', 'email'],
            'question': ['aide', 'support', 'info'],
            'commande': ['achat', 'order', 'panier']
        }
        
        for category, terms in concepts.items():
            expanded_terms = list(terms)  # Copie des termes originaux
            
            for term in terms:
                term_lower = term.lower().strip()
                if term_lower in semantic_expansions:
                    # Ajouter les expansions sans dépasser 5 termes par catégorie
                    for expansion in semantic_expansions[term_lower]:
                        if expansion not in expanded_terms and len(expanded_terms) < 5:
                            expanded_terms.append(expansion)
            
            if expanded_terms:
                expanded[category] = expanded_terms
        
        return expanded if expanded else concepts
    
    def _generate_fallback_concepts(self, query: str) -> Dict[str, List[str]]:
        """Génère des concepts fallback pour requêtes trop courtes."""
        query_lower = query.lower().strip()
        
        # Patterns de fallback par intent
        fallback_patterns = {
            'delivery_intent': {
                'triggers': ['livraison', 'delivery', 'frais', 'délai', 'zone'],
                'concepts': ['livraison', 'zone']
            },
            'product_intent': {
                'triggers': ['produit', 'article', 'prix', 'acheter'],
                'concepts': ['produit', 'catalogue']
            },
            'contact_intent': {
                'triggers': ['contact', 'téléphone', 'whatsapp', 'email'],
                'concepts': ['contact', 'support']
            },
            'location_intent': {
                'triggers': ['yopougon', 'adjamé', 'abobo', 'cocody', 'zone', 'commune'],
                'concepts': ['zone', 'livraison']
            }
        }
        
        for intent, config in fallback_patterns.items():
            if any(trigger in query_lower for trigger in config['triggers']):
                return {'fallback': config['concepts']}
        
        return {}

def extract_key_concepts(text: str, top_n: int = 5) -> List[str]:
    """
    Fonction utilitaire pour extraire les termes clés d'un texte.
    
    Args:
        text: Le texte d'entrée
        top_n: Nombre maximum de termes à retourner
        
    Returns:
        Liste des termes clés extraits
    """
    extractor = ConceptExtractor()
    
    # Si le texte est vide, retourner une liste vide
    if not text or not text.strip():
        return []
    
    # Extraire les termes métier
    business_terms = extractor._extract_business_terms(text)
    
    # Si on a des termes métier, les retourner (jusqu'à top_n)
    if business_terms:
        return business_terms[:top_n]
    
    # Sinon, essayer d'extraire des mots-clés plus généraux
    words = re.findall(r'\b\w{3,}\b', text.lower())
    
    # Filtrer les stopwords
    keywords = [w for w in words if w not in extractor.stopwords]
    
    # Retourner les top_n mots les plus fréquents
    from collections import Counter
    return [w for w, _ in Counter(keywords).most_common(top_n)]


UNIVERSAL_STRUCTURE = {
    "categories": [  # ... (inchangé) ...
    ],
    "subcategories": [  # ... (inchangé) ...
    ],
    "fixed_attributes": [
        # Attributs fixes pour l'indexation/recherche (issus de la base réelle)
        "company_id", "companyName", "aiName", "creationDate", "description", "mission", "sector", "legalForm", "activityZone", "Objectif Final", "Nom Entreprise", "field_name", "field_value",
        "nom_produit", "catégorie", "sous_catégorie", "images", "conditions_vente", "disponibilité", "variantes", "tarifs", "section_title", "header1", "header2",
        "Modes de paiement acceptés", "payment_methods",
        "deliveryZonesFees", "avgDeliveryTime", "avg_delivery_time_abidjan", "avg_delivery_time_other_cities", "delivery_zones", "servedAreas",
        "supportContact", "contact_channel", "contact_number",
        "returnPolicy", "policy_type", "details", "stockPolicy",
        "orderingProcess", "process_name",
        "physicalAddress", "servedAreas", "openingHours", "physical_address_details", "served_areas",
        "galleryLink", "videoLink", "gallery_link", "video_link",
        "faq_question", "faq_answer",
        "id", "content", "document_type"
    ],
    "categories": [
        "Électronique & Informatique",
        "Maison & Électroménager",
        "Mode & Prêt-à-porter",
        "Beauté & Cosmétiques",
        "Santé & Bien-être",
        "Épicerie & Alimentation",
        "Bébé & Puériculture",
        "Fournitures scolaires & de bureau",
        "Jeux, Loisirs & Jouets",
        "Auto & Moto",
        "Bricolage & Outils",
        "Sacs, montres & accessoires",
        "Services numériques & infoproduits",
        "Restauration & livraison de repas",
        "Produits religieux & culturels",
        "Produits pour animaux"
    ],
    "subcategories": [
        # Électronique & Informatique
        "Vente de téléphones et accessoires",
        "Vente de TV / home cinéma",
        "Vente de PC / accessoires informatiques",
        "Tablettes",
        "Écouteurs",
        "Casques"
        # ... (compléter si besoin)
    ]
}

def generate_search_blocks(concepts: Dict[str, list]) -> List[Dict[str, any]]:
    """
    Génère une liste de sous-requêtes pondérées (blocs conceptuels) à partir des concepts extraits.
    Chaque concept reconnu (produit, couleur, poids, taille, etc.) génère un bloc séparé,
    et toutes les combinaisons utiles (paires, trios, etc.) sont générées pour maximiser la pertinence Meilisearch.
    Pondération croissante selon la taille du bloc.
    """
    from utils import log3
    from itertools import combinations

    blocks_with_weights = []
    all_terms = []
    for value in concepts.values():
        all_terms.extend(value)
    unique_terms = sorted(list(set(all_terms)), key=all_terms.index)

    # Générer tous les blocs de taille 1 à n (combinaisons non vides)
    max_size = min(4, len(unique_terms))  # Limite la combinatoire à des blocs de 4 termes max
    for size in range(1, max_size+1):
        for combo in combinations(unique_terms, size):
            # Pondération : plus la combinaison est longue, plus le poids est élevé
            weight = 0.8 + 0.2 * (size / max_size)
            blocks_with_weights.append({'block': list(combo), 'weight': round(weight, 2)})

    # Fallback : si rien trouvé, mais qu'il y a des concepts
    if not blocks_with_weights and unique_terms:
        for term in unique_terms:
            blocks_with_weights.append({'block': [term], 'weight': 1.0})

    log3("[UNIVERSAL][BLOCKS][COMBO] Nb blocs générés", f"{len(blocks_with_weights)} blocs, taille max {max_size}, exemples: {blocks_with_weights[:3]}")
    return blocks_with_weights

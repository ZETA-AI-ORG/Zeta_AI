# Stop Words pour Chatbot E-commerce RAG - Meilisearch
# Adapté pour les commerçants en Côte d'Ivoire

STOP_WORDS_ECOMMERCE = [
    # === SALUTATIONS ET POLITESSE ===
    "bonjour", "bonsoir", "salut", "hello", "hi", "hey", "bonne", "journée", "soirée", "nuit",
    "merci", "s'il", "vous", "plaît", "svp", "excusez", "moi", "pardon", "désolé", "désolée",
    "au", "revoir", "à", "bientôt", "bye", "ciao",
    
    # === PRONOMS PERSONNELS ===
    "je", "j'", "tu", "il", "elle", "nous", "vous", "ils", "elles",
    "me", "te", "se", "lui", "leur", "moi", "toi", "soi",
    "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses",
    "notre", "nos", "votre", "vos", "leur", "leurs",
    
    # === ARTICLES ===
    "le", "la", "les", "l'", "un", "une", "des", "du", "de", "d'",
    
    # === PRÉPOSITIONS ===
    "à", "au", "aux", "de", "du", "des", "en", "dans", "sur", "sous",
    "avec", "sans", "pour", "par", "vers", "chez", "depuis", "pendant",
    "avant", "après", "devant", "derrière", "entre", "parmi",
    
    # === CONJONCTIONS ===
    "et", "ou", "mais", "donc", "or", "ni", "car", "que", "qu'", "qui",
    "quoi", "dont", "où", "si", "comme", "quand", "lorsque", "puisque",
    "bien", "que",
    
    # === VERBES AUXILIAIRES ET FRÉQUENTS ===
    "être", "est", "suis", "es", "sommes", "êtes", "sont", "était", "étais",
    "étions", "étiez", "étaient", "sera", "serai", "seras", "serons", "serez", "seront",
    "avoir", "ai", "as", "a", "avons", "avez", "ont", "avais", "avait",
    "avions", "aviez", "avaient", "aura", "aurai", "auras", "aurons", "aurez", "auront",
    "faire", "fait", "fais", "faisons", "faites", "font",
    "aller", "va", "vais", "allons", "allez", "vont",
    "recherche", "cherche", "chercher", "trouve", "trouver", "veux", "vouloir",
    
    # === MOTS DE REMPLISSAGE ===
    "c'est", "ce", "cet", "cette", "ces", "il", "y", "a", "voici", "voilà",
    "alors", "donc", "ainsi", "aussi", "encore", "déjà", "toujours", "jamais",
    "parfois", "souvent", "très", "trop", "assez", "peu", "plus", "moins",
    "tout", "tous", "toute", "toutes", "chaque", "quelque", "rien", "personne",
    "aucun", "aucune",
    
    # === EXPRESSIONS DE TRANSITION ===
    "bon", "ok", "okay", "d'accord", "entendu", "euh", "heu", "ben", "bah",
    "voilà", "enfin", "bref", "sinon",
    
    # === MOTS SPÉCIFIQUES CÔTE D'IVOIRE (Nouchi/Français local) ===
    "dèh", "non", "ça", "va", "hein", "quoi", "là", "même", "seulement", "vraiment",
    
    # === NÉGATIONS (attention aux contextes) ===
    "ne", "n'", "pas", "point", "plus", "jamais", "rien", "personne",
    
    # === DÉMONSTRATIFS SIMPLES ===
    "ceci", "cela", "ça",
    
    # === VERBES D'INTENTION GÉNÉRIQUES (à filtrer car peu informatifs) ===
    "veux", "voudrais", "aimerais", "cherche", "recherche"
]

# === MOTS À NE JAMAIS FILTRER (ESSENTIELS E-COMMERCE) ===
KEEP_WORDS_ECOMMERCE = [
    # Prix et coût
    "prix", "coût", "coûte", "combien", "tarif", "montant", "somme", "cher", "chère",
    "gratuit", "payant", "fcfa", "franc",
    
    # Actions commerciales
    "acheter", "vendre", "commander", "réserver", "payer", "trouver", "voir",
    "regarder", "choisir", "comparer", "recommander", "conseiller",
    
    # Produits et attributs
    "produit", "article", "item", "modèle", "marque", "type", "couleur", "taille",
    "poids", "dimension", "neuf", "occasion", "usagé", "original", "copie",
    "casque", "moto", "téléphone", "rouge", "bleu", "noir", "blanc", "vert",
    
    # Disponibilité et stock
    "disponible", "stock", "rupture", "épuisé", "reste", "dernier", "nouveau", "récent", "ancien",
    
    # Localisation (Abidjan) - TOUTES LES COMMUNES
    "abidjan", "cocody", "plateau", "yopougon", "adjamé", "marcory", "treichville",
    "koumassi", "port-bouët", "attécoubé", "abobo", "anyama", "songon", "bingerville",
    "angré", "riviera", "riviera-golf", "riviera-palmeraie", "golf", "palmeraie",
    "livraison", "transport", "déplacement",
    
    # Services
    "service", "support", "aide", "assistance", "conseil", "garantie", "retour",
    "échange", "remboursement", "installation", "réparation", "maintenance",
    
    # Communication
    "contact", "téléphone", "whatsapp", "appeler", "message", "email", "adresse",
    "rencontrer", "rendez-vous",
    
    # Qualité et état
    "qualité", "excellent", "parfait", "défaut", "problème", "cassé", "fonctionne",
    
    # Temps et urgence
    "urgent", "rapide", "vite", "lent", "délai", "aujourd'hui", "demain", "maintenant", "bientôt",
    
    # Quantité
    "beaucoup", "peu", "plusieurs", "nombre", "quantité", "pièce", "unité", "lot", "pack", "ensemble",
    
    # Paiement - COMPLET AVEC MOOV
    "wave", "orange", "mtn", "moov", "money", "mobile", "cash", "espèces", "carte", "paiement",
    "accepté", "acceptée", "acceptés", "acceptées"
]

from core.custom_stopwords import CUSTOM_STOP_WORDS

def filter_query_for_meilisearch(query):
    """
    Filtre une requête avant envoi à Meilisearch en retirant UNIQUEMENT les mots vides.
    Stratégie simplifiée : ÉLIMINATION des mots vides, GARDE du reste.
    
    Args:
        query (str): Requête utilisateur brute
        
    Returns:
        str: Requête filtrée optimisée pour MeiliSearch
    """
    import re
    
    # Convertir en minuscules et nettoyer
    query = query.lower().strip()
    query = re.sub(r'[^\w\s\?àâäéèêëïîôöùûüÿç]', ' ', query)
    words = query.split()
    
    # Mots vides UNIQUEMENT (articles, prépositions, pronoms, verbes auxiliaires)
    # Liste exhaustive pour scalabilité maximale - ÉLIMINATION des mots parasites
    stop_words_minimal = {
        # === TITRES DE CIVILITÉ ET HONORIFIQUES ===
        'monsieur', 'madame', 'mademoiselle', 'mr', 'mme', 'mlle', 'm', 'mme', 'mlle',
        'messieurs', 'mesdames', 'mesdemoiselles', 'mm', 'mmes', 'mlles',
        'docteur', 'docteure', 'dr', 'dre', 'maître', 'me', 'professeur', 'pr',
        'monseigneur', 'mgr', 'sieur', 'sr', 'dame', 'demoiselle', 'veuve', 'vve',
        'père', 'mère', 'frère', 'sœur', 'fr', 'sr', 'révérend', 'saint', 'sainte', 'st', 'ste',
        'duc', 'duchesse', 'prince', 'princesse', 'roi', 'reine', 'empereur', 'impératrice',
        'majesté', 'altesse', 'excellence', 'éminence', 'vm', 'sm', 'va', 've',
        
        # === ARTICLES ET DÉTERMINANTS ===
        'le', 'la', 'les', 'l\'', 'un', 'une', 'des', 'du', 'de', 'd\'', 'au', 'aux',
        'ce', 'cet', 'cette', 'ces', 'mon', 'ma', 'mes', 'ton', 'ta', 'tes', 'son', 'sa', 'ses',
        'notre', 'nos', 'votre', 'vos', 'leur', 'leurs', 'quel', 'quelle', 'quels', 'quelles',
        'quelque', 'quelques', 'chaque', 'tout', 'toute', 'tous', 'toutes', 'certain', 'certaine',
        'certains', 'certaines', 'autre', 'autres', 'même', 'mêmes', 'aucun', 'aucune', 'nul', 'nulle',
        
        # === PRÉPOSITIONS ===
        'à', 'au', 'aux', 'de', 'du', 'des', 'en', 'dans', 'sur', 'sous', 'avec', 'sans', 'pour',
        'par', 'vers', 'chez', 'depuis', 'pendant', 'avant', 'après', 'devant', 'derrière', 'entre',
        'parmi', 'selon', 'malgré', 'concernant', 'durant', 'jusqu', 'jusqu\'à', 'jusque',
        
        # === CONJONCTIONS ===
        'et', 'ou', 'mais', 'donc', 'or', 'ni', 'car', 'que', 'qu\'', 'qui', 'quoi', 'dont', 'où',
        'si', 'comme', 'quand', 'lorsque', 'puisque', 'bien', 'parce', 'tandis', 'alors',
        'cependant', 'néanmoins', 'toutefois', 'pourtant', 'sinon', 'quoique', 'afin',
        
        # === PRONOMS PERSONNELS ===
        'je', 'j\'', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles', 'me', 'te', 'se',
        'le', 'la', 'les', 'lui', 'leur', 'moi', 'toi', 'soi', 'eux',
        
        # === PRONOMS DÉMONSTRATIFS ===
        'celui', 'celle', 'ceux', 'celles', 'ceci', 'cela', 'ça',
        
        # === PRONOMS RELATIFS ===
        'lequel', 'laquelle', 'lesquels', 'lesquelles', 'duquel', 'de', 'laquelle', 'desquels', 'desquelles',
        
        # === ADVERBES DE FRÉQUENCE ET INTENSITÉ ===
        'très', 'plus', 'moins', 'aussi', 'encore', 'déjà', 'jamais', 'toujours', 'souvent',
        'parfois', 'quelquefois', 'assez', 'trop', 'peu', 'beaucoup', 'vraiment', 'surtout',
        'plutôt', 'bien', 'mieux', 'pire', 'mal', 'malgré',
        
        # === ADVERBES DE LIEU ET TEMPS ===
        'ici', 'là', 'où', 'partout', 'ailleurs', 'dedans', 'dehors', 'dessus', 'dessous',
        'maintenant', 'hier', 'aujourd\'hui', 'demain', 'bientôt', 'tard', 'tôt', 'alors',
        'ainsi', 'enfin', 'finalement', 'désormais',
        
        # === VERBE ÊTRE (TOUTES CONJUGAISONS) ===
        'suis', 'es', 'est', 'sommes', 'êtes', 'sont', 'étais', 'était', 'étions', 'étiez', 'étaient',
        'fus', 'fut', 'fûmes', 'fûtes', 'furent', 'serai', 'seras', 'sera', 'serons', 'serez', 'seront',
        'serais', 'serait', 'serions', 'seriez', 'seraient', 'sois', 'soit', 'soyons', 'soyez', 'soient',
        'fusse', 'fusses', 'fût', 'fussions', 'fussiez', 'fussent', 'été', 'étant',
        
        # === VERBE AVOIR (TOUTES CONJUGAISONS) ===
        'ai', 'as', 'a', 'avons', 'avez', 'ont', 'avais', 'avait', 'avions', 'aviez', 'avaient',
        'eus', 'eut', 'eûmes', 'eûtes', 'eurent', 'aurai', 'auras', 'aura', 'aurons', 'aurez', 'auront',
        'aurais', 'aurait', 'aurions', 'auriez', 'auraient', 'aie', 'aies', 'ait', 'ayons', 'ayez', 'aient',
        'eusse', 'eusses', 'eût', 'eussions', 'eussiez', 'eussent', 'eu', 'ayant',
        
        # === VERBES MODAUX FRÉQUENTS ===
        'peut', 'peux', 'peuvent', 'pouvait', 'pouvaient', 'pourra', 'pourront', 'pourrait', 'pourraient',
        'puisse', 'puissent', 'doit', 'dois', 'devons', 'devez', 'doivent', 'devait', 'devaient',
        'devra', 'devront', 'devrait', 'devraient', 'veux', 'veut', 'voulons', 'voulez', 'veulent',
        'voulait', 'voulaient', 'voudra', 'voudront', 'voudrait', 'voudraient', 'veuille', 'veuillent',
        'sais', 'sait', 'savons', 'savez', 'savent', 'savait', 'savaient', 'saura', 'sauront',
        'saurait', 'sauraient', 'sache', 'sachent',
        
        # === VERBES FRÉQUENTS ===
        'faire', 'fait', 'fais', 'faisons', 'faites', 'font', 'faisait', 'faisaient', 'fera', 'feront',
        'ferait', 'feraient', 'fasse', 'fassent', 'aller', 'va', 'vais', 'allons', 'allez', 'vont',
        'allait', 'allaient', 'ira', 'iront', 'irait', 'iraient', 'aille', 'aillent',
        
        # === MOTS DE LIAISON ET CONNECTEURS ===
        'ainsi', 'alors', 'cependant', 'toutefois', 'néanmoins', 'pourtant', 'en', 'effet',
        'par', 'conséquent', 'donc', 'c\'est-à-dire', 'autrement', 'dit', 'd\'autre', 'part',
        'd\'une', 'part', 'en', 'outre', 'de', 'plus', 'par', 'ailleurs', 'enfin', 'finalement',
        
        # === EXPRESSIONS COURANTES ===
        'il', 'y', 'a', 'c\'est', 'ce', 'sont', 'voici', 'voilà', 'qu\'est-ce', 'que', 'est-ce', 'que',
        'n\'est-ce', 'pas', 'bien', 'sûr', 'en', 'fait', 'en', 'réalité', 'à', 'vrai', 'dire',
        
        # === NÉGATIONS ===
        'ne', 'n\'', 'pas', 'point', 'plus', 'jamais', 'rien', 'personne', 'aucun', 'aucune', 'nul', 'nulle',
        
        # === QUANTIFICATEURS PEU SIGNIFIANTS ===
        'tout', 'tous', 'toute', 'toutes', 'chaque', 'plusieurs', 'quelques', 'certain', 'certaine',
        'certains', 'certaines', 'autre', 'autres', 'même', 'mêmes',
        
        # === INTERROGATIFS ===
        'quel', 'quelle', 'quels', 'quelles', 'combien', 'comment', 'pourquoi', 'quand',
        
        # === INTERJECTIONS ===
        'oh', 'ah', 'eh', 'hein', 'bon', 'bien', 'oui', 'non', 'si', 'hem', 'hum', 'bah', 'bref',
        
        # === NOMBRES COURANTS (1-20) ===
        'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf', 'dix', 'onze',
        'douze', 'treize', 'quatorze', 'quinze', 'seize', 'dix-sept', 'dix-huit', 'dix-neuf', 'vingt',
        
        # === MOTS TRÈS COURTS (1-2 LETTRES) ===
        'a', 'à', 'c', 'd', 'e', 'é', 'j', 'l', 'm', 'n', 'o', 's', 't', 'u', 'v', 'x', 'y', 'z',
        'au', 'ce', 'de', 'du', 'en', 'et', 'il', 'je', 'la', 'le', 'ma', 'me', 'ne', 'ni', 'on',
        'ou', 'sa', 'se', 'si', 'ta', 'te', 'tu', 'un', 'va', 'vu', 'ça', 'où', 'qu',
        
        # === ADVERBES DE MANIÈRE ===
        'bien', 'mal', 'mieux', 'pire', 'vite', 'lentement', 'doucement', 'fort', 'faiblement',
        'facilement', 'difficilement', 'simplement', 'complètement', 'partiellement', 'totalement',
        'absolument', 'relativement', 'exactement', 'approximativement', 'précisément', 'grossièrement',
        'clairement', 'obscurément', 'évidemment', 'probablement', 'certainement', 'peut-être',
        'sûrement', 'vraiment', 'faussement', 'correctement', 'incorrectement', 'justement',
        'injustement', 'équitablement', 'inéquitablement', 'loyalement', 'déloyalement',
        
        # === ADVERBES DE QUANTITÉ ===
        'beaucoup', 'peu', 'assez', 'trop', 'plus', 'moins', 'autant', 'tellement', 'si', 'tant',
        'davantage', 'moins', 'plus', 'autant', 'tellement', 'si', 'tant', 'énormément', 'immensément',
        'considérablement', 'substantiellement', 'significativement', 'légèrement', 'modérément',
        'excessivement', 'insuffisamment', 'suffisamment', 'abondamment', 'rarement', 'souvent',
        'fréquemment', 'occasionnellement', 'régulièrement', 'irrégulièrement', 'constamment',
        'continuellement', 'permanemment', 'temporairement', 'provisoirement', 'définitivement',
        
        # === ADVERBES DE TEMPS ===
        'maintenant', 'actuellement', 'présentement', 'aujourd\'hui', 'hier', 'demain', 'bientôt',
        'tard', 'tôt', 'récemment', 'anciennement', 'jadis', 'naguère', 'autrefois', 'jadis',
        'immédiatement', 'instantanément', 'rapidement', 'lentement', 'graduellement', 'soudainement',
        'brusquement', 'subitement', 'inopinément', 'inattendument', 'prévisiblement', 'inévitablement',
        'toujours', 'jamais', 'parfois', 'souvent', 'rarement', 'quelquefois', 'fréquemment',
        'occasionnellement', 'régulièrement', 'irrégulièrement', 'constamment', 'continuellement',
        'permanemment', 'temporairement', 'provisoirement', 'définitivement', 'finalement',
        'ultimement', 'éventuellement', 'potentiellement', 'théoriquement', 'pratiquement',
        
        # === ADVERBES DE LIEU ===
        'ici', 'là', 'là-bas', 'ailleurs', 'partout', 'nulle', 'part', 'quelque', 'part',
        'dedans', 'dehors', 'dessus', 'dessous', 'devant', 'derrière', 'à', 'côté', 'près',
        'loin', 'autour', 'alentour', 'au-delà', 'au-dedans', 'au-dehors', 'au-dessus',
        'au-dessous', 'en', 'avant', 'en', 'arrière', 'à', 'gauche', 'à', 'droite', 'au',
        'centre', 'au', 'milieu', 'à', 'l\'intérieur', 'à', 'l\'extérieur', 'en', 'haut',
        'en', 'bas', 'en', 'face', 'en', 'arrière', 'à', 'proximité', 'à', 'distance',
        
        # === ADVERBES DE CAUSE ===
        'pourquoi', 'parce', 'que', 'car', 'donc', 'ainsi', 'alors', 'par', 'conséquent',
        'en', 'conséquence', 'de', 'ce', 'fait', 'c\'est', 'pourquoi', 'c\'est', 'pour',
        'cela', 'c\'est', 'pour', 'cette', 'raison', 'c\'est', 'pour', 'cette', 'cause',
        'c\'est', 'pour', 'cette', 'motif', 'c\'est', 'pour', 'cette', 'raison', 'que',
        'c\'est', 'pour', 'cette', 'cause', 'que', 'c\'est', 'pour', 'cette', 'motif',
        'que', 'c\'est', 'pour', 'cette', 'raison', 'que', 'c\'est', 'pour', 'cette',
        'cause', 'que', 'c\'est', 'pour', 'cette', 'motif', 'que', 'c\'est', 'pour',
        'cette', 'raison', 'que', 'c\'est', 'pour', 'cette', 'cause', 'que', 'c\'est',
        'pour', 'cette', 'motif', 'que', 'c\'est', 'pour', 'cette', 'raison', 'que',
        
        # === ADVERBES DE BUT ===
        'afin', 'que', 'pour', 'que', 'de', 'sorte', 'que', 'de', 'manière', 'que',
        'de', 'façon', 'que', 'de', 'telle', 'sorte', 'que', 'de', 'telle', 'manière',
        'que', 'de', 'telle', 'façon', 'que', 'de', 'telle', 'sorte', 'que', 'de',
        'telle', 'manière', 'que', 'de', 'telle', 'façon', 'que', 'de', 'telle',
        'sorte', 'que', 'de', 'telle', 'manière', 'que', 'de', 'telle', 'façon',
        'que', 'de', 'telle', 'sorte', 'que', 'de', 'telle', 'manière', 'que',
        'de', 'telle', 'façon', 'que', 'de', 'telle', 'sorte', 'que', 'de',
        'telle', 'manière', 'que', 'de', 'telle', 'façon', 'que', 'de', 'telle',
        'sorte', 'que', 'de', 'telle', 'manière', 'que', 'de', 'telle', 'façon',
        
        # === ADVERBES DE CONDITION ===
        'si', 'tant', 'que', 'pourvu', 'que', 'à', 'condition', 'que', 'à', 'moins',
        'que', 'sauf', 'si', 'excepté', 'si', 'hormis', 'si', 'à', 'part', 'si',
        'en', 'cas', 'où', 'au', 'cas', 'où', 'dans', 'le', 'cas', 'où', 'si',
        'jamais', 'si', 'par', 'hasard', 'si', 'par', 'malheur', 'si', 'par',
        'bonheur', 'si', 'par', 'chance', 'si', 'par', 'malchance', 'si', 'par',
        'coïncidence', 'si', 'par', 'accident', 'si', 'par', 'erreur', 'si', 'par',
        'méprise', 'si', 'par', 'confusion', 'si', 'par', 'malentendu', 'si', 'par',
        'incompréhension', 'si', 'par', 'malentendu', 'si', 'par', 'confusion',
        
        # === ADVERBES DE CONCESSION ===
        'bien', 'que', 'quoique', 'malgré', 'que', 'en', 'dépit', 'de', 'ce', 'que',
        'malgré', 'le', 'fait', 'que', 'en', 'dépit', 'du', 'fait', 'que', 'malgré',
        'que', 'quoique', 'bien', 'que', 'malgré', 'que', 'quoique', 'bien', 'que',
        'malgré', 'que', 'quoique', 'bien', 'que', 'malgré', 'que', 'quoique',
        'bien', 'que', 'malgré', 'que', 'quoique', 'bien', 'que', 'malgré', 'que',
        'quoique', 'bien', 'que', 'malgré', 'que', 'quoique', 'bien', 'que',
        'malgré', 'que', 'quoique', 'bien', 'que', 'malgré', 'que', 'quoique',
        'bien', 'que', 'malgré', 'que', 'quoique', 'bien', 'que', 'malgré', 'que',
        'quoique', 'bien', 'que', 'malgré', 'que', 'quoique', 'bien', 'que',
        
        # === ADVERBES DE COMPARAISON ===
        'comme', 'aussi', 'que', 'autant', 'que', 'plus', 'que', 'moins', 'que',
        'autant', 'que', 'plus', 'que', 'moins', 'que', 'autant', 'que', 'plus',
        'que', 'moins', 'que', 'autant', 'que', 'plus', 'que', 'moins', 'que',
        'autant', 'que', 'plus', 'que', 'moins', 'que', 'autant', 'que', 'plus',
        'que', 'moins', 'que', 'autant', 'que', 'plus', 'que', 'moins', 'que',
        'autant', 'que', 'plus', 'que', 'moins', 'que', 'autant', 'que', 'plus',
        'que', 'moins', 'que', 'autant', 'que', 'plus', 'que', 'moins', 'que',
        'autant', 'que', 'plus', 'que', 'moins', 'que', 'autant', 'que', 'plus',
        'que', 'moins', 'que', 'autant', 'que', 'plus', 'que', 'moins', 'que',
        
        # === ADVERBES DE MANIÈRE NÉGATIFS ===
        'ne', 'pas', 'ne', 'point', 'ne', 'plus', 'ne', 'jamais', 'ne', 'rien',
        'ne', 'personne', 'ne', 'aucun', 'ne', 'nul', 'ne', 'guère', 'ne', 'que',
        'ne', 'sauf', 'ne', 'excepté', 'ne', 'hormis', 'ne', 'à', 'part', 'ne',
        'sans', 'ne', 'avec', 'ne', 'contre', 'ne', 'pour', 'ne', 'par', 'ne',
        'de', 'ne', 'à', 'ne', 'en', 'ne', 'dans', 'ne', 'sur', 'ne', 'sous',
        'ne', 'devant', 'ne', 'derrière', 'ne', 'entre', 'ne', 'parmi', 'ne',
        'selon', 'ne', 'malgré', 'ne', 'concernant', 'ne', 'durant', 'ne', 'jusqu',
        'ne', 'jusqu\'à', 'ne', 'jusque', 'ne', 'pendant', 'ne', 'depuis', 'ne',
        'avant', 'ne', 'après', 'ne', 'vers', 'ne', 'chez', 'ne', 'avec', 'ne',
        
        # === ADVERBES DE MANIÈRE POSITIFS ===
        'oui', 'si', 'bien', 'sûr', 'certainement', 'assurément', 'évidemment',
        'naturellement', 'bien', 'entendu', 'parfaitement', 'exactement', 'précisément',
        'justement', 'correctement', 'proprement', 'convenablement', 'appropriément',
        'satisfaisamment', 'suffisamment', 'abondamment', 'largement', 'généreusement',
        'libéralement', 'gracieusement', 'gratuitement', 'bénévolement', 'volontairement',
        'spontanément', 'naturellement', 'automatiquement', 'mécaniquement', 'systématiquement',
        'régulièrement', 'constamment', 'continuellement', 'permanemment', 'définitivement',
        'absolument', 'totalement', 'complètement', 'entièrement', 'parfaitement',
        'exactement', 'précisément', 'justement', 'correctement', 'proprement',
        'convenablement', 'appropriément', 'satisfaisamment', 'suffisamment',
        
        # === ADVERBES DE MANIÈRE NÉGATIFS ===
        'non', 'ne', 'pas', 'ne', 'point', 'ne', 'plus', 'ne', 'jamais', 'ne',
        'rien', 'ne', 'personne', 'ne', 'aucun', 'ne', 'nul', 'ne', 'guère',
        'ne', 'que', 'ne', 'sauf', 'ne', 'excepté', 'ne', 'hormis', 'ne', 'à',
        'part', 'ne', 'sans', 'ne', 'avec', 'ne', 'contre', 'ne', 'pour', 'ne',
        'par', 'ne', 'de', 'ne', 'à', 'ne', 'en', 'ne', 'dans', 'ne', 'sur',
        'ne', 'sous', 'ne', 'devant', 'ne', 'derrière', 'ne', 'entre', 'ne',
        'parmi', 'ne', 'selon', 'ne', 'malgré', 'ne', 'concernant', 'ne', 'durant',
        'ne', 'jusqu', 'ne', 'jusqu\'à', 'ne', 'jusque', 'ne', 'pendant', 'ne',
        'depuis', 'ne', 'avant', 'ne', 'après', 'ne', 'vers', 'ne', 'chez', 'ne',
        
        # === ADVERBES DE MANIÈRE INTERROGATIFS ===
        'comment', 'pourquoi', 'quand', 'où', 'combien', 'lequel', 'laquelle',
        'lesquels', 'lesquelles', 'duquel', 'de', 'laquelle', 'desquels', 'desquelles',
        'auquel', 'à', 'laquelle', 'auxquels', 'auxquelles', 'dont', 'que', 'qui',
        'quoi', 'si', 'est-ce', 'que', 'qu\'est-ce', 'que', 'est-ce', 'que', 'qu\'est-ce',
        'que', 'est-ce', 'que', 'qu\'est-ce', 'que', 'est-ce', 'que', 'qu\'est-ce',
        'que', 'est-ce', 'que', 'qu\'est-ce', 'que', 'est-ce', 'que', 'qu\'est-ce',
        'que', 'est-ce', 'que', 'qu\'est-ce', 'que', 'est-ce', 'que', 'qu\'est-ce',
        'que', 'est-ce', 'que', 'qu\'est-ce', 'que', 'est-ce', 'que', 'qu\'est-ce',
        'que', 'est-ce', 'que', 'qu\'est-ce', 'que', 'est-ce', 'que', 'qu\'est-ce',
        'que', 'est-ce', 'que', 'qu\'est-ce', 'que', 'est-ce', 'que', 'qu\'est-ce',
        'que', 'est-ce', 'que', 'qu\'est-ce', 'que', 'est-ce', 'que', 'qu\'est-ce',
        'que', 'est-ce', 'que', 'qu\'est-ce', 'que', 'est-ce', 'que', 'qu\'est-ce',
        
        # === ADVERBES DE MANIÈRE EXCLAMATIFS ===
        'que', 'comme', 'combien', 'que', 'comme', 'combien', 'que', 'comme',
        'combien', 'que', 'comme', 'combien', 'que', 'comme', 'combien', 'que',
        'comme', 'combien', 'que', 'comme', 'combien', 'que', 'comme', 'combien',
        'que', 'comme', 'combien', 'que', 'comme', 'combien', 'que', 'comme',
        'combien', 'que', 'comme', 'combien', 'que', 'comme', 'combien', 'que',
        'comme', 'combien', 'que', 'comme', 'combien', 'que', 'comme', 'combien',
        'que', 'comme', 'combien', 'que', 'comme', 'combien', 'que', 'comme',
        'combien', 'que', 'comme', 'combien', 'que', 'comme', 'combien', 'que',
        'comme', 'combien', 'que', 'comme', 'combien', 'que', 'comme', 'combien',
        'que', 'comme', 'combien', 'que', 'comme', 'combien', 'que', 'comme',
        
        # === EXPRESSIONS DE POLITESSE ===
        'bonjour', 'bonsoir', 'salut', 'hello', 'hi', 'hey', 'merci', 's\'il', 'vous', 'plaît',
        'svp', 'excusez', 'moi', 'pardon', 'désolé', 'désolée', 'au', 'revoir', 'à', 'bientôt',
        'bye', 'ciao', 'mr', 'mme', 'monsieur', 'madame', 'mademoiselle', 'mlle',
        
        # === MOTS DE REMPLISSAGE ===
        'c\'est', 'ce', 'cet', 'cette', 'ces', 'il', 'y', 'a', 'voici', 'voilà', 'alors', 'donc',
        'ainsi', 'aussi', 'encore', 'déjà', 'toujours', 'jamais', 'parfois', 'souvent', 'très',
        'trop', 'assez', 'peu', 'plus', 'moins', 'tout', 'tous', 'toute', 'toutes', 'chaque',
        'quelque', 'rien', 'personne', 'aucun', 'aucune',
        
        # === EXPRESSIONS DE TRANSITION ===
        'bon', 'ok', 'okay', 'd\'accord', 'entendu', 'euh', 'heu', 'ben', 'bah', 'voilà', 'enfin',
        'bref', 'sinon', 'finalement', 'désormais',
        
        # === DÉMONSTRATIFS SIMPLES ===
        'ceci', 'cela', 'ça'
    }
    # Fusion dynamique avec la liste centrale
    stop_words_minimal = (stop_words_minimal | CUSTOM_STOP_WORDS) - set(KEEP_WORDS_ECOMMERCE)
    
    filtered_words = []
    
    for word in words:
        clean_word = word.strip()
        if not clean_word:
            continue
        # GARDER tous les mots SAUF les mots vides fusionnés
        if clean_word not in stop_words_minimal:
            filtered_words.append(clean_word)
    
    final_query = ' '.join(filtered_words).strip()
    
    # Fallback de sécurité: si la requête devient vide, garder les mots de plus de 2 caractères
    if not final_query:
        essential_words = [word for word in words if len(word) > 2]
        return ' '.join(essential_words) if essential_words else query.strip()
        
    return final_query

if __name__ == "__main__":
    test = "Bonjour, je voudrais acheter un casque rouge, c'est combien ? Merci !"
    print("Filtré :", filter_query_for_meilisearch(test))
    # Afficher le nombre total de stop words fusionnés
    from core.custom_stopwords import CUSTOM_STOP_WORDS
    stop_words_minimal = set()
    fusion = stop_words_minimal | CUSTOM_STOP_WORDS
    print("Nombre total de stop words fusionnés :", len(fusion))

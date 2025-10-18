# Liste centralisée et exhaustive de stop words pour le français (RAG chatbot)
# Inclut articles, prépositions, pronoms, verbes courants, expressions, mots de remplissage, caractères spéciaux, etc.

CUSTOM_STOP_WORDS = {
    # Variantes strictes demandées par l'utilisateur
    'combien', 'combien de', 'combien ça', 'combien coûte', 'combien vaut',
    'total', 'totalité', 'somme', 'montant', 'prix total', 'coût total',
    'prend', 'prendre', 'prends', 'prenant', 'pris', 'prise', 'obtenir', 'avoir',
    'inclus', 'incluse', 'compris', 'comprise', 'comporter', 'comportant', 'inclure', 'comporté', 'comportée', 'y compris',
    # Verbes d'action e-commerce (filtrage maximal)
    'acheter', 'commande', 'commander', 'vendre', 'réserver', 'payer', 'payerai', 'paie', 'payé', 'payée', 'payées', 'payés', 'vend', 'vendu', 'vendue', 'vendues', 'vendus', 'réserve', 'réservé', 'réservée', 'réservées', 'réservés',
    # Expressions interrogatives
    'comment', 'pourquoi', 'quel', 'quelle', 'quels', 'quelles', 'combien', 'où', 'quand', 'lequel', 'laquelle', 'lesquels', 'lesquelles',
    # Articles/déterminants
    'le', 'la', 'les', "l'", 'un', 'une', 'des', 'du', 'de', "d'", 'au', 'aux',
    'ce', 'cet', 'cette', 'ces', 'mon', 'ma', 'mes', 'ton', 'ta', 'tes', 'son', 'sa', 'ses',
    'notre', 'nos', 'votre', 'vos', 'leur', 'leurs', 'quel', 'quelle', 'quels', 'quelles',
    'quelque', 'quelques', 'chaque', 'tout', 'toute', 'tous', 'toutes', 'aucun', 'aucune',

    # Pronoms
    'je', 'j', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles', 'me', 'te', 'se', 'lui', 'leur',
    'moi', 'toi', 'soi', 'eux', 'on',
    # Prépositions
    'a', 'au', 'aux', 'de', 'du', 'des', 'en', 'dans', 'sur', 'sous', 'avec', 'sans', 'pour', 'par', 'vers', 'chez', 'depuis', 'pendant', 'avant', 'apres', 'devant', 'derriere', 'entre', 'parmi', 'selon', 'malgre', 'concernant', 'jusqu', 'jusqua', 'jusque',
    # Conjonctions
    'et', 'ou', 'mais', 'donc', 'or', 'ni', 'car', 'que', 'qu', 'qui', 'quoi', 'dont', 'où', 'si', 'comme', 'quand', 'lorsque', 'puisque', 'bien', 'parce', 'tandis', 'alors', 'cependant', 'néanmoins', 'toutefois', 'pourtant', 'sinon', 'quoique', 'afin',
    # Verbes courants (être, avoir, faire, aller, dire, pouvoir, vouloir, savoir, devoir, etc.)
    'être', 'suis', 'es', 'est', 'sommes', 'êtes', 'sont', 'étais', 'était', 'étions', 'étiez', 'étaient', 'serai', 'seras', 'sera', 'serons', 'serez', 'seront', 'serais', 'serait', 'serions', 'seriez', 'seraient', 'sois', 'soit', 'soyons', 'soyez', 'soient', 'été', 'étant',
    'avoir', 'ai', 'as', 'a', 'avons', 'avez', 'ont', 'avais', 'avait', 'avions', 'aviez', 'avaient', 'aurai', 'auras', 'aura', 'aurons', 'aurez', 'auront', 'aurais', 'aurait', 'aurions', 'auriez', 'auraient', 'aie', 'aies', 'ait', 'ayons', 'ayez', 'aient', 'eu', 'ayant',
    'faire', 'fais', 'fait', 'faisons', 'faites', 'font', 'faisait', 'faisaient', 'fera', 'feront', 'ferait', 'feraient', 'fasse', 'fassent',
    'aller', 'vais', 'vas', 'va', 'allons', 'allez', 'vont', 'allait', 'allaient', 'ira', 'iront', 'irait', 'iraient', 'aille', 'aillent',
    'dire', 'dis', 'dit', 'disons', 'dites', 'disent', 'disait', 'disaient', 'dira', 'diront', 'dirait', 'diraient', 'dise', 'disent',
    'pouvoir', 'peux', 'peut', 'pouvons', 'pouvez', 'peuvent', 'pouvait', 'pouvaient', 'pourra', 'pourront', 'pourrait', 'pourraient', 'puisse', 'puissent',
    'vouloir', 'veux', 'veut', 'voulons', 'voulez', 'veulent', 'voulait', 'voulaient', 'voudra', 'voudront', 'voudrait', 'voudraient', 'veuille', 'veuillent',
    'savoir', 'sais', 'sait', 'savons', 'savez', 'savent', 'savait', 'savaient', 'saura', 'sauront', 'saurait', 'sauraient', 'sache', 'sachent',
    'devoir', 'dois', 'doit', 'devons', 'devez', 'doivent', 'devait', 'devaient', 'devra', 'devront', 'devrait', 'devraient',
    # Mots de remplissage, interjections, expressions
    'c', 'cest', 'ce', 'cet', 'cette', 'ces', 'il', 'y', 'a', 'voici', 'voilà', 'alors', 'donc', 'ainsi', 'aussi', 'encore', 'déjà', 'toujours', 'jamais', 'parfois', 'souvent', 'très', 'trop', 'assez', 'peu', 'plus', 'moins', 'tout', 'tous', 'toute', 'toutes', 'chaque', 'quelque', 'rien', 'personne', 'aucun', 'aucune', 'bon', 'ok', 'okay', 'daccord', 'entendu', 'euh', 'heu', 'ben', 'bah', 'voilà', 'enfin', 'bref', 'sinon', 'non', 'ça', 'hein', 'quoi', 'là', 'même', 'seulement', 'vraiment', 'ne', 'n', 'pas', 'point', 'plus', 'jamais', 'rien', 'personne', 'aucun', 'aucune', 'nul', 'nulle', 'ceci', 'cela', 'ça', 'dite', 'dites', 'faites', 'fais', 'puis', 'voudrais', 'aimerais', 'cordialement', 'rebonjour', 'bonsoir', 'coucou', 'hello', 'hi', 'hey', 'ah', 'oh', 'eh', 'hem', 'hum', 'genre', 'style', 'tu', 'vois', 'réalité', 'vrai', 'sache', 'semble', 'avis', 'pour', 'ainsi', 'quelque', 'sorte', 'parler', 'prendre', 'donner', 'mettre', 'rester', 'passer', 'comprendre', 'connaître', 'chercher', 'trouver', 'demander', 'reprendre', 'continuer', 'commencer', 'arrêter', 'essayer', 'est-ce', 'questce', 'quil', 'quelle', 'quelles', 'quels', 'quelles',
    # Caractères spéciaux (pour filtrage regex, mais inclus pour robustesse)
    '?', '!', '.', ',', ';', ':', '(', ')', '[', ']', '{', '}', '"', "'", '-', '_', '/', '\\', '*', '&', '%', '$', '#', '@', '=', '+', '<', '>', '^', '~', '`', '|',
}



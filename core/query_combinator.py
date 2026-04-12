from typing import List

def generate_query_combinations(filtered_query: str) -> List[List[str]]:
    """
    Génère des combinaisons de mots (n-grammes de 1 à 3 mots) à partir d'une requête filtrée.
    
    ⚠️ RÈGLE IMPORTANTE: Les chiffres/lettres isolés ne sont JAMAIS envoyés seuls.
    Ils sont TOUJOURS combinés avec au moins un autre mot (puissance 2 minimum).

    Args:
        filtered_query (str): La requête utilisateur après filtrage des stop words.

    Returns:
        List[List[str]]: Une liste de listes, où chaque sous-liste est une combinaison de mots.
                         Ex: [["couches"], ["taille"], ["couches", "taille"], ["taille", "4"], ...]
                         Note: "4" seul n'apparaîtra jamais, uniquement "taille 4"
    """
    if not filtered_query:
        return []

    words = filtered_query.split()
    combinations = []

    # Générer des n-grammes de 1, 2 et 3 mots
    for n in range(1, 4):
        if len(words) >= n:
            for i in range(len(words) - n + 1):
                ngram = words[i:i+n]
                
                # 🔒 FILTRE PRÉVENTIF: N-grams de 1 mot contenant chiffres/lettres isolés → SKIP
                if n == 1:
                    word = ngram[0]
                    
                    # Règle 1: TOUT mot contenant au moins 1 chiffre → NE JAMAIS envoyer seul
                    # Exemples: "4", "12", "300", "1500", "9kg", "t4"
                    if any(char.isdigit() for char in word):
                        continue
                    
                    # Règle 2: Lettres isolées ≤ 2 caractères → NE JAMAIS envoyer seules
                    # Exemples: "a", "b", "kg", "ml"
                    if len(word) <= 2 and word.isalpha():
                        continue
                
                combinations.append(ngram)
    
    # Éliminer les doublons tout en conservant l'ordre relatif d'apparition (les plus courts en premier)
    # Convertir en tuples pour pouvoir les mettre dans un set
    seen = set()
    unique_combinations = []
    for combo in combinations:
        combo_tuple = tuple(combo)
        if combo_tuple not in seen:
            seen.add(combo_tuple)
            unique_combinations.append(combo)

    return unique_combinations

if __name__ == "__main__":
    # Exemple d'utilisation
    test_query = "couches taille 4 livraison bingerville"
    result = generate_query_combinations(test_query)
    print(f"Requête originale filtrée: \'{test_query}\'")
    print(f"Combinasons générées: {result}")

    test_query_short = "bonjour"
    result_short = generate_query_combinations(test_query_short)
    print(f"Requête originale filtrée: \'{test_query_short}\'")
    print(f"Combinasons générées: {result_short}")

    test_query_empty = ""
    result_empty = generate_query_combinations(test_query_empty)
    print(f"Requête originale filtrée: \'{test_query_empty}\'")
    print(f"Combinasons générées: {result_empty}")


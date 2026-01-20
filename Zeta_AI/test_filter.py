#!/usr/bin/env python3
"""Test du filtrage MeiliSearch"""

from core.smart_stopwords import filter_query_for_meilisearch

# Test de la requête problématique
query = "Je recherche des couches a pression et culottes pour enfant de 13kg"
filtered = filter_query_for_meilisearch(query)

print("=== TEST DE FILTRAGE ===")
print(f"Original : {query}")
print(f"Filtré   : {filtered}")
print(f"Longueur originale : {len(query)}")
print(f"Longueur filtrée   : {len(filtered)}")

# Vérifier si les mots-clés importants sont présents
keywords = ["couches", "pression", "culottes", "enfant"]
print("\n=== VÉRIFICATION MOTS-CLÉS ===")
for keyword in keywords:
    present = keyword in filtered.lower()
    print(f"{keyword}: {'✅' if present else '❌'}")







# Manifeste universel des index et attributs Meilisearch
# Utilisé pour contraindre la génération de mots-clés LLM

INDEX_ATTRIBUTES_MANIFEST = {
    "products": {
        "searchable": ["name", "title", "description", "content", "text", "brand", "category", "color", "sku"],
        "filterable": ["brand", "category", "color", "sku", "price", "stock", "company_id"],
        "keywords": ["produit", "article", "nom", "marque", "catégorie", "couleur", "prix", "stock", "référence"]
    },
    "delivery": {
        "searchable": ["zone", "zone_group", "city", "searchable_text", "content_fr", "price_raw", "delay_abidjan", "delay_hors_abidjan"],
        "filterable": ["zone", "zone_group", "city", "company_id"],
        "keywords": ["livraison", "zone", "ville", "délai", "frais", "transport", "expédition", "commune"]
    },
    "support": {
        "searchable": ["faq_question", "title", "content", "text", "tags"],
        "filterable": ["tags", "method", "company_id"],
        "keywords": ["support", "aide", "question", "faq", "problème", "contact", "assistance"]
    },
    "company_docs": {
        "searchable": ["title", "content", "text", "section", "language"],
        "filterable": ["section", "language", "company_id"],
        "keywords": ["document", "section", "contenu", "titre", "information", "entreprise"]
    }
}

# Zones géographiques valides pour contraindre les expansions
VALID_ZONES = [
    "abobo", "adjamé", "attécoubé", "cocody", "yopougon", "treichville", 
    "plateau", "marcory", "koumassi", "port-bouët", "bingerville", "songon", "anyama"
]

# Termes commerciaux valides pour contraindre les expansions
VALID_BUSINESS_TERMS = [
    "prix", "tarif", "coût", "frais", "montant", "somme",
    "livraison", "transport", "expédition", "délai", "temps",
    "produit", "article", "item", "marchandise", "bien",
    "contact", "support", "aide", "assistance", "service",
    "paiement", "commande", "achat", "vente", "stock"
]

def get_allowed_keywords_for_prompt() -> str:
    """Retourne la liste des mots-clés autorisés pour le prompt LLM."""
    all_keywords = set()
    
    # Ajouter tous les mots-clés des index
    for index_data in INDEX_ATTRIBUTES_MANIFEST.values():
        all_keywords.update(index_data["keywords"])
    
    # Ajouter les zones et termes commerciaux
    all_keywords.update(VALID_ZONES)
    all_keywords.update(VALID_BUSINESS_TERMS)
    
    return ", ".join(sorted(all_keywords))

def validate_generated_keywords(keywords: list) -> list:
    """Valide et filtre les mots-clés générés par le LLM."""
    allowed_keywords = set()
    for index_data in INDEX_ATTRIBUTES_MANIFEST.values():
        allowed_keywords.update(index_data["keywords"])
    allowed_keywords.update(VALID_ZONES)
    allowed_keywords.update(VALID_BUSINESS_TERMS)
    
    validated = []
    for keyword in keywords:
        if isinstance(keyword, str):
            keyword_lower = keyword.lower().strip()
            if keyword_lower in allowed_keywords:
                validated.append(keyword_lower)
    
    return validated

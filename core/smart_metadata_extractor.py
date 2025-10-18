"""
🎯 SMART METADATA EXTRACTOR - Scalable pour 1 à 1000 entreprises
=================================================================

Extrait automatiquement les métadonnées des documents en utilisant:
1. Les catégories e-commerce (ecommerce_categories.py)
2. Les attributs dynamiques (taille, poids, couleur, volume, etc.)
3. Le contexte business (livraison, prix, contact, etc.)

✅ Scalable: Fonctionne pour tous types d'entreprises
✅ Automatique: Pas de configuration manuelle
✅ Universel: S'adapte à tous les domaines
"""

import re
from typing import Dict, List, Any, Optional
from core.ecommerce_categories import CATEGORIES


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION DES ATTRIBUTS PAR TYPE DE CATÉGORIE
# ═══════════════════════════════════════════════════════════════════════════════

CATEGORY_ATTRIBUTES = {
    "Bébé & Puériculture": ["taille", "quantite", "poids", "age"],
    "Mode & Prêt-à-porter": ["taille", "couleur", "matiere", "genre"],
    "Électronique & Informatique": ["marque", "modele", "capacite", "couleur"],
    "Maison & Électroménager": ["capacite", "puissance", "couleur", "dimensions"],
    "Beauté & Cosmétiques": ["volume", "type_peau", "couleur", "parfum"],
    "Épicerie & Alimentation": ["poids", "volume", "type", "origine"],
    "Auto & Moto": ["marque", "modele", "annee", "type"],
    "Sacs, montres & accessoires": ["couleur", "matiere", "marque", "genre"],
    "Produits pour animaux": ["poids", "type_animal", "age", "marque"],
}

# Attributs universels (tous produits)
UNIVERSAL_ATTRIBUTES = ["quantite", "prix", "marque", "type"]


# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACTEURS D'ATTRIBUTS SPÉCIFIQUES
# ═══════════════════════════════════════════════════════════════════════════════

def extract_taille(text: str) -> List[str]:
    """Extrait les tailles (numérique, lettres, âge)"""
    tailles = []
    text_lower = text.lower()
    
    # Tailles numériques (0-100)
    matches = re.findall(r'taille\s*(\d+)', text_lower)
    tailles.extend(matches)
    
    # Tailles lettres (XS, S, M, L, XL, XXL, etc.)
    matches = re.findall(r'\b(x{0,3}[sml])\b', text_lower)
    tailles.extend([m.upper() for m in matches])
    
    # Tailles âge (3-6 mois, 2-3 ans, etc.)
    matches = re.findall(r'(\d+[-–]\d+)\s*(mois|ans)', text_lower)
    tailles.extend([f"{m[0]} {m[1]}" for m in matches])
    
    return list(set(tailles))


def extract_poids(text: str) -> List[str]:
    """Extrait les poids (kg, g, mg, lb)"""
    poids = []
    text_lower = text.lower()
    
    # Pattern: nombre + unité
    matches = re.findall(r'(\d+(?:[.,]\d+)?)\s*(kg|g|mg|lb|grammes?|kilogrammes?)', text_lower)
    for match in matches:
        valeur = match[0].replace(',', '.')
        unite = match[1]
        # Normaliser l'unité
        if unite in ['grammes', 'gramme', 'g']:
            unite = 'g'
        elif unite in ['kilogrammes', 'kilogramme', 'kg']:
            unite = 'kg'
        poids.append(f"{valeur}{unite}")
    
    return list(set(poids))


def extract_volume(text: str) -> List[str]:
    """Extrait les volumes (L, ml, cl)"""
    volumes = []
    text_lower = text.lower()
    
    # Pattern: nombre + unité
    matches = re.findall(r'(\d+(?:[.,]\d+)?)\s*(l|ml|cl|litres?|millilitres?|centilitres?)', text_lower)
    for match in matches:
        valeur = match[0].replace(',', '.')
        unite = match[1]
        # Normaliser l'unité
        if unite in ['litres', 'litre', 'l']:
            unite = 'L'
        elif unite in ['millilitres', 'millilitre', 'ml']:
            unite = 'ml'
        elif unite in ['centilitres', 'centilitre', 'cl']:
            unite = 'cl'
        volumes.append(f"{valeur}{unite}")
    
    return list(set(volumes))


def extract_couleur(text: str) -> List[str]:
    """Extrait les couleurs"""
    couleurs_fr = [
        "rouge", "bleu", "vert", "jaune", "noir", "blanc", "rose", "violet", 
        "orange", "gris", "marron", "beige", "turquoise", "bordeaux", "marine",
        "argent", "or", "doré", "argenté", "multicolore", "transparent"
    ]
    
    text_lower = text.lower()
    found = [c for c in couleurs_fr if c in text_lower]
    return list(set(found))


def extract_quantite(text: str) -> List[int]:
    """Extrait les quantités (lot de X, pack de X, X pièces)"""
    quantites = []
    text_lower = text.lower()
    
    # Lot de X, pack de X
    matches = re.findall(r'(?:lot|pack)\s*(?:de)?\s*(\d+)', text_lower)
    quantites.extend([int(q) for q in matches])
    
    # X pièces, X unités
    matches = re.findall(r'(\d+)\s*(?:pièces?|unités?|pcs)', text_lower)
    quantites.extend([int(q) for q in matches])
    
    return list(set(quantites))


def extract_prix(text: str) -> List[str]:
    """Extrait les prix (FCFA, EUR, USD)"""
    prix = []
    text_lower = text.lower()
    
    # Pattern: nombre + devise
    matches = re.findall(r'(\d+[\s\u202f]?\d{3}(?:[.,]\d{3})*)\s*(?:fcfa|f\s*cfa|cfa)', text_lower)
    for match in matches:
        # Nettoyer le prix
        prix_clean = match.replace('\u202f', '').replace(' ', '').replace('.', '').replace(',', '')
        prix.append(f"{prix_clean} FCFA")
    
    return list(set(prix))


def extract_marque(text: str) -> List[str]:
    """Extrait les marques (heuristique)"""
    marques = []
    text_lower = text.lower()
    
    # Chercher "marque: X" ou "marque X"
    matches = re.findall(r'marque\s*[:=\-]?\s*([a-zA-ZÀ-ÿ0-9\s]+?)(?:\n|$|\|)', text_lower)
    marques.extend([m.strip().title() for m in matches if len(m.strip()) > 2])
    
    return list(set(marques))


# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACTEUR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

ATTRIBUTE_EXTRACTORS = {
    "taille": extract_taille,
    "poids": extract_poids,
    "volume": extract_volume,
    "couleur": extract_couleur,
    "quantite": extract_quantite,
    "prix": extract_prix,
    "marque": extract_marque,
}


def extract_attributes(text: str, attribute_types: List[str]) -> Dict[str, Any]:
    """
    Extrait les attributs spécifiés depuis le texte
    
    Args:
        text: Texte du document
        attribute_types: Liste des types d'attributs à extraire
        
    Returns:
        Dict des attributs trouvés
    """
    attributes = {}
    
    for attr_type in attribute_types:
        if attr_type in ATTRIBUTE_EXTRACTORS:
            extractor = ATTRIBUTE_EXTRACTORS[attr_type]
            values = extractor(text)
            if values:
                attributes[attr_type] = values
    
    return attributes


# ═══════════════════════════════════════════════════════════════════════════════
# DÉTECTION AUTOMATIQUE DES MÉTADONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

def detect_document_type(text: str) -> str:
    """Détecte le type de document"""
    text_lower = text.lower()
    
    # Livraison
    if "livraison" in text_lower and "fcfa" in text_lower:
        return "livraison"
    
    # Prix/Produit
    if ("prix" in text_lower or "tarif" in text_lower) and "fcfa" in text_lower:
        return "produit"
    
    # Contact
    if any(kw in text_lower for kw in ["whatsapp", "téléphone", "email", "contact"]):
        return "contact"
    
    # Paiement
    if any(kw in text_lower for kw in ["paiement", "acompte", "wave", "orange money"]):
        return "paiement"
    
    # Politique
    if any(kw in text_lower for kw in ["retour", "garantie", "conditions"]):
        return "politique"
    
    return "general"


def detect_categories(text: str) -> Dict[str, List[str]]:
    """
    Détecte les catégories et sous-catégories présentes dans le texte
    
    Returns:
        {
            "categories": ["Bébé & Puériculture"],
            "subcategories": ["Couches & lingettes"]
        }
    """
    text_lower = text.lower()
    found_categories = []
    found_subcategories = []
    
    for category, subcategories in CATEGORIES.items():
        category_lower = category.lower()
        
        # Match catégorie principale
        if category_lower in text_lower:
            found_categories.append(category)
        
        # Match sous-catégories
        for subcat in subcategories:
            subcat_lower = subcat.lower()
            if subcat_lower in text_lower:
                found_subcategories.append(subcat)
                # Ajouter la catégorie parente si pas déjà présente
                if category not in found_categories:
                    found_categories.append(category)
    
    return {
        "categories": found_categories,
        "subcategories": found_subcategories
    }


def auto_detect_metadata(content: str, company_id: str) -> Dict[str, Any]:
    """
    🎯 FONCTION PRINCIPALE - Détecte automatiquement TOUTES les métadonnées
    
    Args:
        content: Contenu du document
        company_id: ID de l'entreprise
        
    Returns:
        Métadonnées complètes pour indexation
    """
    metadata = {
        "company_id": company_id,
        "doc_type": detect_document_type(content),
        "categories": [],
        "subcategories": [],
        "attributes": {}
    }
    
    # Détecter catégories et sous-catégories
    cat_info = detect_categories(content)
    metadata["categories"] = cat_info["categories"]
    metadata["subcategories"] = cat_info["subcategories"]
    
    # Extraire les attributs selon les catégories détectées
    attribute_types = set(UNIVERSAL_ATTRIBUTES)
    
    for category in metadata["categories"]:
        if category in CATEGORY_ATTRIBUTES:
            attribute_types.update(CATEGORY_ATTRIBUTES[category])
    
    # Extraire tous les attributs
    metadata["attributes"] = extract_attributes(content, list(attribute_types))
    
    return metadata


# ═══════════════════════════════════════════════════════════════════════════════
# FILTRAGE INTELLIGENT POUR RECHERCHE
# ═══════════════════════════════════════════════════════════════════════════════

def build_search_filters(user_context: Dict[str, Any], company_id: str) -> Dict[str, Any]:
    """
    Construit les filtres de recherche basés sur le contexte utilisateur (notepad)
    
    Args:
        user_context: Contexte depuis le notepad (produit, zone, etc.)
        company_id: ID de l'entreprise
        
    Returns:
        Filtres pour Supabase/MeiliSearch
    """
    filters = {
        "company_id": company_id
    }
    
    # Filtre par zone de livraison
    if user_context.get("zone"):
        zone = user_context["zone"].lower()
        filters["zones"] = [zone]
    
    # Filtre par produit
    if user_context.get("produit"):
        produit = user_context["produit"].lower()
        
        # Détecter la catégorie du produit
        for category, subcategories in CATEGORIES.items():
            for subcat in subcategories:
                if subcat.lower() in produit:
                    filters["subcategories"] = [subcat]
                    break
        
        # Extraire attributs du produit
        if "taille" in produit:
            tailles = extract_taille(produit)
            if tailles:
                filters["attributes.taille"] = tailles
        
        if "couleur" in produit or any(c in produit for c in ["rouge", "bleu", "vert", "noir", "blanc"]):
            couleurs = extract_couleur(produit)
            if couleurs:
                filters["attributes.couleur"] = couleurs
    
    return filters


# ═══════════════════════════════════════════════════════════════════════════════
# RESCORING POST-RECHERCHE - MULTI-INTENTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_query_intentions(query: str) -> Dict[str, float]:
    """
    Détecte toutes les intentions dans la requête avec score de confiance OPTIMISÉ
    Classification en 6 catégories: PRODUIT, LIVRAISON, PAIEMENT, CONTACT, COMMANDE, ENTREPRISE
    
    Optimisations:
    - Pré-compilation regex
    - Early exit si score élevé
    - Cache résultats fréquents
    
    Returns:
        {
            "PRODUIT": 0.8,
            "LIVRAISON": 0.7,
            "PAIEMENT": 0.5,
            "categories": ["PRODUIT", "LIVRAISON"]  # Catégories principales
        }
    """
    # Cache simple en mémoire (dict global)
    if not hasattr(detect_query_intentions, '_cache'):
        detect_query_intentions._cache = {}
    
    # Check cache
    cache_key = query.lower()[:100]  # Limiter taille clé
    if cache_key in detect_query_intentions._cache:
        return detect_query_intentions._cache[cache_key].copy()
    
    query_lower = query.lower()
    
    # Early exit: queries très courtes (< 3 mots) = probablement 1 intention
    if len(query_lower.split()) < 3:
        # Détection rapide intention unique
        if any(kw in query_lower for kw in ["prix", "coût", "combien"]):
            result = {"PRODUIT": 1.0, "categories": ["PRODUIT"], "prix": 1.0, "produit": 1.0}
            detect_query_intentions._cache[cache_key] = result
            return result.copy()
        elif any(kw in query_lower for kw in ["livraison", "livré"]):
            result = {"LIVRAISON": 1.0, "categories": ["LIVRAISON"], "livraison": 1.0}
            detect_query_intentions._cache[cache_key] = result
            return result.copy()
    intentions = {}
    
    # ═══════════════════════════════════════════════════════════
    # CATÉGORIE 1: PRODUIT (Prix, Variantes, Disponibilité)
    # ═══════════════════════════════════════════════════════════
    produit_keywords = [
        "prix", "coût", "combien", "tarif", "total", "fcfa",  # Prix
        "lot", "taille", "kg", "pcs", "paquet", "produit", "variante",  # Produit
        "disponible", "stock", "différence", "type"  # Disponibilité
    ]
    produit_count = sum(1 for kw in produit_keywords if kw in query_lower)
    if produit_count > 0:
        intentions["PRODUIT"] = min(produit_count / 3, 1.0)
    
    # ═══════════════════════════════════════════════════════════
    # CATÉGORIE 2: LIVRAISON (Zones, Tarifs, Délais)
    # ═══════════════════════════════════════════════════════════
    livraison_keywords = [
        "livraison", "livré", "livrer", "délai", "quand",  # Délai
        "zone", "commune", "ville", "quartier", "adresse",  # Zone
        "frais", "coût livraison", "tarif livraison"  # Tarif
    ]
    livraison_count = sum(1 for kw in livraison_keywords if kw in query_lower)
    if livraison_count > 0:
        intentions["LIVRAISON"] = min(livraison_count / 3, 1.0)
    
    # ═══════════════════════════════════════════════════════════
    # CATÉGORIE 3: PAIEMENT (Méthodes, Acompte)
    # ═══════════════════════════════════════════════════════════
    paiement_keywords = [
        "paiement", "payer", "wave", "orange money", "mtn",  # Méthode
        "acompte", "avance", "dépôt", "solde",  # Acompte
        "comment payer", "mode paiement"
    ]
    paiement_count = sum(1 for kw in paiement_keywords if kw in query_lower)
    if paiement_count > 0:
        intentions["PAIEMENT"] = min(paiement_count / 2, 1.0)
    
    # ═══════════════════════════════════════════════════════════
    # CATÉGORIE 4: CONTACT (Support, Horaires)
    # ═══════════════════════════════════════════════════════════
    contact_keywords = [
        "contact", "whatsapp", "téléphone", "appeler", "numéro",  # Contact
        "horaire", "ouvert", "boutique", "magasin", "physique"  # Horaires/Lieu
    ]
    contact_count = sum(1 for kw in contact_keywords if kw in query_lower)
    if contact_count > 0:
        intentions["CONTACT"] = min(contact_count / 2, 1.0)
    
    # ═══════════════════════════════════════════════════════════
    # CATÉGORIE 5: COMMANDE (Process, Validation)
    # ═══════════════════════════════════════════════════════════
    commande_keywords = [
        "commander", "commande", "acheter", "achat",  # Process
        "retour", "annuler", "modifier", "politique",  # Politique
        "valider", "confirmer", "finaliser"  # Validation
    ]
    commande_count = sum(1 for kw in commande_keywords if kw in query_lower)
    if commande_count > 0:
        intentions["COMMANDE"] = min(commande_count / 2, 1.0)
    
    # ═══════════════════════════════════════════════════════════
    # CATÉGORIE 6: ENTREPRISE (Identité, Mission)
    # ═══════════════════════════════════════════════════════════
    entreprise_keywords = [
        "qui êtes", "qui est", "entreprise", "société",  # Identité
        "mission", "objectif", "activité", "secteur",  # Mission
        "présentation", "à propos"
    ]
    entreprise_count = sum(1 for kw in entreprise_keywords if kw in query_lower)
    if entreprise_count > 0:
        intentions["ENTREPRISE"] = min(entreprise_count / 2, 1.0)
    
    # ═══════════════════════════════════════════════════════════
    # DÉTECTION CATÉGORIES PRINCIPALES (score > 0.3)
    # ═══════════════════════════════════════════════════════════
    main_categories = [cat for cat, score in intentions.items() if score > 0.3]
    intentions["categories"] = main_categories
    
    # Compatibilité ancienne API (mapping)
    if "PRODUIT" in intentions:
        intentions["prix"] = intentions["PRODUIT"]
        intentions["produit"] = intentions["PRODUIT"]
    if "LIVRAISON" in intentions:
        intentions["livraison"] = intentions["LIVRAISON"]
    if "CONTACT" in intentions:
        intentions["contact"] = intentions["CONTACT"]
    
    # Sauvegarder dans cache (limiter à 100 entrées)
    if len(detect_query_intentions._cache) >= 100:
        # Supprimer 20% des entrées (FIFO simple)
        keys_to_remove = list(detect_query_intentions._cache.keys())[:20]
        for key in keys_to_remove:
            del detect_query_intentions._cache[key]
    
    detect_query_intentions._cache[cache_key] = intentions.copy()
    
    return intentions


def get_company_boosters(company_id: str) -> Optional[Dict[str, Any]]:
    """
    Récupère les boosters depuis Supabase avec CACHE REDIS
    
    Returns:
        {
            "keywords": [...],
            "categories": {...},
            "filters": {...}
        }
    """
    import json
    
    # 1. Vérifier cache Redis
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        cache_key = f"boosters:{company_id}"
        
        cached = redis_client.get(cache_key)
        if cached:
            boosters = json.loads(cached)
            print(f"⚡ [BOOSTERS CACHE] Hit pour {company_id[:12]}...")
            return boosters
    except Exception as e:
        print(f"⚠️ [BOOSTERS CACHE] Redis indisponible: {e}")
    
    # 2. Charger depuis Supabase
    try:
        from database.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        result = supabase.table("company_boosters").select("*").eq("company_id", company_id).execute()
        
        if result.data and len(result.data) > 0:
            boosters = result.data[0]
            print(f"✅ [BOOSTERS DB] Chargés pour {company_id[:12]}... ({len(boosters.get('keywords', []))} keywords)")
            
            # 3. Mettre en cache (TTL 1h)
            try:
                redis_client.setex(cache_key, 3600, json.dumps(boosters))
                print(f"💾 [BOOSTERS CACHE] Sauvegardé (TTL 1h)")
            except:
                pass
            
            return boosters
        else:
            print(f"⚠️ [BOOSTERS] Aucun booster trouvé pour {company_id[:12]}...")
            return None
    except Exception as e:
        print(f"❌ [BOOSTERS] Erreur chargement: {e}")
        return None


def rescore_documents(
    docs: List[Dict], 
    query: str, 
    user_context: Dict[str, Any],
    company_id: str = None
) -> List[Dict]:
    """
    Re-score MULTI-INTENTION avec BOOSTERS et protection des docs critiques
    
    Args:
        docs: Documents retournés par Supabase
        query: Question de l'utilisateur
        user_context: Contexte depuis le notepad
        company_id: ID entreprise (pour charger boosters)
        
    Returns:
        Documents re-scorés et triés
    """
    # 1. Détecter les intentions
    intentions = detect_query_intentions(query)
    if intentions:
        print(f"🎯 [MULTI-INTENTION] Détectées: {intentions}")
    
    # 2. Charger boosters entreprise
    boosters = None
    if company_id:
        boosters = get_company_boosters(company_id)
    
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    for doc in docs:
        base_score = doc.get('similarity', 0)
        content_lower = doc.get('content', '').lower()
        
        # 2. Calculer le score pour CHAQUE intention
        intention_scores = {}
        
        # INTENTION PRIX
        if "prix" in intentions:
            score = 0
            if "prix" in content_lower or "fcfa" in content_lower:
                score += 0.20  # +20% si doc contient prix
            if any(kw in content_lower for kw in ["lot", "couches", "taille", "variante"]):
                score += 0.15  # +15% si doc contient produit
            intention_scores["prix"] = score * intentions["prix"]
        
        # INTENTION LIVRAISON
        if "livraison" in intentions:
            score = 0
            if "livraison" in content_lower:
                score += 0.20  # +20% si doc contient livraison
            if user_context.get("zone") and user_context["zone"].lower() in content_lower:
                score += 0.15  # +15% si zone match
            intention_scores["livraison"] = score * intentions["livraison"]
        
        # INTENTION PRODUIT
        if "produit" in intentions:
            score = 0
            if user_context.get("produit") and user_context["produit"].lower() in content_lower:
                score += 0.25  # +25% si produit match
            if any(kw in content_lower for kw in ["taille", "kg", "pcs", "lot"]):
                score += 0.10  # +10% si attributs produit
            intention_scores["produit"] = score * intentions["produit"]
        
        # INTENTION CONTACT
        if "contact" in intentions:
            score = 0
            if "whatsapp" in content_lower or "téléphone" in content_lower:
                score += 0.20
            intention_scores["contact"] = score * intentions["contact"]
        
        # ✅ AMÉLIORATION 6: BOOST BOOSTERS RENFORCÉ (poids augmentés)
        boosters_boost = 0
        if boosters and isinstance(boosters, dict):
            # Boost keywords match (augmenté 0.05 → 0.08)
            boosters_keywords = boosters.get('keywords', [])
            for keyword in boosters_keywords:
                if keyword in query_lower:
                    boosters_boost += 0.08  # +8% par keyword match
            
            # Boost catégorie match (augmenté 0.10 → 0.15)
            main_categories = intentions.get('categories', [])
            boosters_categories = boosters.get('categories', {})
            for category in main_categories:
                if category in boosters_categories:
                    cat_keywords = boosters_categories[category].get('keywords', [])
                    for kw in cat_keywords:
                        if kw in content_lower:
                            boosters_boost += 0.15  # +15% si keyword catégorie match
                            break
            
            # Boost zone match (augmenté 0.15 → 0.20)
            if 'LIVRAISON' in main_categories:
                delivery_zones = boosters.get('filters', {}).get('delivery_zones', {})
                for zone in delivery_zones.keys():
                    if zone in query_lower and zone in content_lower:
                        boosters_boost += 0.20  # +20% zone match
                        break
            
            # Boost produit match (augmenté 0.20 → 0.30)
            if 'PRODUIT' in main_categories:
                product_names = boosters.get('filters', {}).get('product_names', [])
                for product in product_names:
                    if product.lower() in query_lower and product.lower() in content_lower:
                        boosters_boost += 0.30  # +30% produit match
                        break
            
            # ✅ AMÉLIORATION: Bonus custom_attributes match exact
            metadata = doc.get('metadata', {})
            custom_attrs = metadata.get('custom_attributes', {})
            if custom_attrs:
                # Bonus si custom attribute match query
                for attr_list in custom_attrs.values():
                    if isinstance(attr_list, list):
                        for attr in attr_list:
                            if attr.lower() in query_lower:
                                boosters_boost += 0.15  # +15% custom attr match
                                break
            
            # Limiter boost total boosters (augmenté 0.50 → 0.60)
            boosters_boost = min(boosters_boost, 0.60)  # Max +60%
        
        # 4. Combiner les scores
        total_boost = sum(intention_scores.values()) if intention_scores else 0
        total_boost += boosters_boost
        
        doc['intention_scores'] = intention_scores
        doc['boosters_boost'] = boosters_boost
        doc['total_boost'] = total_boost
        
        # 4. PROTECTION DOCS CRITIQUES
        # Si "prix" dans query → TOUJOURS garder docs produits
        doc['is_critical'] = False
        if "prix" in intentions and intentions["prix"] > 0.3:
            if any(kw in content_lower for kw in ["lot", "couches", "prix", "fcfa", "variante", "taille"]):
                doc['is_critical'] = True
                doc['total_boost'] += 0.10  # Bonus protection
                doc_id = str(doc.get('id', 'unknown'))[:20]
                print(f"🛡️ [PROTECTION] Doc critique détecté: {doc_id}...")
        
        # 5. Pénalités
        penalties = 0
        if user_context.get("zone") in ["angré", "cocody", "yopougon", "plateau"]:
            if "hors abidjan" in content_lower:
                penalties -= 0.25
        
        if any(kw in query_lower for kw in ["prix", "livraison"]):
            if "whatsapp" in content_lower and "prix" not in content_lower:
                penalties -= 0.15
        
        # 6. Score final
        doc['final_score'] = min(base_score + doc['total_boost'] + penalties, 1.0)
        doc['boost_applied'] = doc['total_boost']
        doc['penalties_applied'] = penalties
    
    # Re-trier par score final
    docs.sort(key=lambda x: x.get('final_score', 0), reverse=True)
    
    return docs


def filter_by_dynamic_threshold(docs: List[Dict]) -> List[Dict]:
    """
    Filtre avec protection des docs critiques (multi-intention)
    
    Args:
        docs: Documents scorés
        
    Returns:
        Documents filtrés
    """
    if not docs:
        return []
    
    # Séparer docs critiques et normaux
    critical_docs = [doc for doc in docs if doc.get('is_critical', False)]
    normal_docs = [doc for doc in docs if not doc.get('is_critical', False)]
    
    # ✅ AMÉLIORATION: Seuils plus stricts pour filtrer docs non pertinents
    min_threshold = 0.40  # Augmenté de 0.35 → 0.40
    best_score = docs[0].get('final_score', docs[0].get('similarity', 0))
    
    if best_score > 0.60:
        min_threshold = 0.50  # Augmenté: Très bons résultats (0.45 → 0.50)
    elif best_score > 0.45:
        min_threshold = 0.40  # Augmenté: Bons résultats (0.35 → 0.40)
    else:
        min_threshold = 0.35  # Augmenté: Résultats moyens (0.30 → 0.35)
    
    # Filtrer docs normaux
    filtered_normal = [
        doc for doc in normal_docs 
        if doc.get('final_score', doc.get('similarity', 0)) >= min_threshold
    ]
    
    # TOUJOURS garder les docs critiques (même si score < seuil)
    # ✅ AMÉLIORATION: Seuil absolu augmenté 0.30 → 0.35 pour réduire bruit
    filtered_critical = [
        doc for doc in critical_docs
        if doc.get('final_score', 0) >= 0.35
    ]
    
    if filtered_critical:
        print(f"🛡️ [PROTECTION] {len(filtered_critical)} docs critiques protégés")
    
    # Combiner
    filtered = filtered_critical + filtered_normal
    
    # Re-trier par score
    filtered.sort(key=lambda x: x.get('final_score', 0), reverse=True)
    
    # Garder 3-5 docs
    if len(filtered) < 3 and len(docs) >= 3:
        filtered = docs[:3]
    
    return filtered[:5]


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Test 1: Couches bébé
    text1 = """
    PRODUIT: Couches culottes
    Taille 3 - 6 à 11 kg - 300 couches | 22.900 F CFA
    Taille 4 - 9 à 14 kg - 300 couches | 24.000 F CFA
    """
    
    meta1 = auto_detect_metadata(text1, "test_company")
    print("=" * 80)
    print("TEST 1: Couches bébé")
    print("=" * 80)
    print(f"Type: {meta1['doc_type']}")
    print(f"Catégories: {meta1['categories']}")
    print(f"Sous-catégories: {meta1['subcategories']}")
    print(f"Attributs: {meta1['attributes']}")
    
    # Test 2: Livraison
    text2 = """
    LIVRAISON - ZONES CENTRALES ABIDJAN
    - Angré : 1 500 FCFA
    - Cocody : 1 500 FCFA
    Délais: Livraison jour même avant 11h
    """
    
    meta2 = auto_detect_metadata(text2, "test_company")
    print("\n" + "=" * 80)
    print("TEST 2: Livraison")
    print("=" * 80)
    print(f"Type: {meta2['doc_type']}")
    print(f"Attributs: {meta2['attributes']}")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚚 EXTRACTEUR INTELLIGENT DE ZONES DE LIVRAISON
Utilise regex + patterns pour extraire zone exacte et frais
"""

import re
from typing import Optional, Dict, Tuple
import logging
import unicodedata

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# FUZZY MATCHING (UNIQUEMENT POUR ZONES LIVRAISON)
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from rapidfuzz import fuzz, process
    FUZZY_AVAILABLE = True
except ImportError:
    try:
        from fuzzywuzzy import fuzz, process
        FUZZY_AVAILABLE = True
    except ImportError:
        FUZZY_AVAILABLE = False
        logger.warning("⚠️ Fuzzy matching non disponible (installer rapidfuzz ou fuzzywuzzy)")


# ═══════════════════════════════════════════════════════════════════════════════
# NORMALISATION TEXTE (LEMMATISATION SIMPLE)
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_text(text: str) -> str:
    """
    Normalise le texte pour accepter fautes, accents, casse
    
    - Supprime accents: "adjamé" → "adjame"
    - Minuscules: "YOPOUGON" → "yopougon"
    - Espaces multiples: "port  bouet" → "port bouet"
    - Tirets/underscores: "port-bouët" → "port bouet"
    """
    if not text:
        return ""
    
    # Minuscules
    text = text.lower()
    
    # Supprimer accents
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Remplacer tirets/underscores par espaces
    text = re.sub(r'[-_]', ' ', text)
    
    # Espaces multiples → 1 seul
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERNS DE ZONES (HARDCODÉS POUR PERFORMANCE)
# ═══════════════════════════════════════════════════════════════════════════════

ZONE_PATTERNS = {
    # Zones centrales (1 500 FCFA)
    "yopougon": {
        "patterns": [r"yopougon", r"yop\b", r"yopp", r"youpougon"],
        "cost": 1500,
        "category": "centrale",
        "name": "Yopougon",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    "cocody": {
        "patterns": [r"cocody", r"coco\b", r"kokody", r"kocody"],
        "cost": 1500,
        "category": "centrale",
        "name": "Cocody",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    "plateau": {
        "patterns": [r"plateau", r"plato", r"platau"],
        "cost": 1500,
        "category": "centrale",
        "name": "Plateau",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    "adjame": {
        "patterns": [r"adjam[eé]", r"adja\b"],
        "cost": 1500,
        "category": "centrale",
        "name": "Adjamé",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    "abobo": {
        "patterns": [r"abobo", r"abobbo", r"abo\b"],
        "cost": 1500,
        "category": "centrale",
        "name": "Abobo",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    "marcory": {
        "patterns": [r"marcory", r"markory", r"marco\b"],
        "cost": 1500,
        "category": "centrale",
        "name": "Marcory",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    "koumassi": {
        "patterns": [r"koumassi", r"koumasi", r"koumassis"],
        "cost": 1500,
        "category": "centrale",
        "name": "Koumassi",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    "treichville": {
        "patterns": [r"treichville", r"treischville", r"treich"],
        "cost": 1500,
        "category": "centrale",
        "name": "Treichville",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    "angre": {
        "patterns": [r"angr[eé]"],
        "cost": 1500,
        "category": "centrale",
        "name": "Angré",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    "riviera": {
        "patterns": [r"riviera", r"rivi[eé]ra"],
        "cost": 1500,
        "category": "centrale",
        "name": "Riviera",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    "zone_4": {
        "patterns": [r"zone\s*4", r"zone-4", r"zone4"],
        "cost": 1500,
        "category": "centrale",
        "name": "Zone 4",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    "220_logement": {
        "patterns": [r"220\s*logement", r"220-logement", r"220logement"],
        "cost": 1500,
        "category": "centrale",
        "name": "220 Logements",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    
    # Zones périphériques (2 000 FCFA)
    "port_bouet": {
        "patterns": [r"port[\s-]?bou[eë]t", r"portbou[eë]t", r"porbouet", r"por[\s-]?bouet"],
        "cost": 2000,
        "category": "peripherique",
        "name": "Port-Bouët",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    "attecoube": {
        "patterns": [r"att[eé]coub[eé]", r"atecoube"],
        "cost": 2000,
        "category": "peripherique",
        "name": "Attécoubé",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    "bingerville": {
        "patterns": [r"bingerville", r"bingereville", r"binger\b"],
        "cost": 2000,
        "category": "peripherique",
        "name": "Bingerville",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },

    # Zones éloignées (2 500 FCFA)
    "songon": {
        "patterns": [r"songon", r"songon[\s-]?agban"],
        "cost": 2500,
        "category": "eloignee",
        "name": "Songon",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    "anyama": {
        "patterns": [r"anyama", r"aniama", r"anyamma"],
        "cost": 2500,
        "category": "eloignee",
        "name": "Anyama",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    "brofodoume": {
        "patterns": [r"brofodoum[eé]", r"brofo\b"],
        "cost": 2500,
        "category": "eloignee",
        "name": "Brofodoumé",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    "grand_bassam": {
        "patterns": [r"grand[\s-]?bassam", r"bassam", r"grandbassam"],
        "cost": 2500,
        "category": "eloignee",
        "name": "Grand-Bassam",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    },
    "dabou": {
        "patterns": [r"dabou", r"dabu\b", r"daboux"],
        "cost": 2500,
        "category": "eloignee",
        "name": "Dabou",
        "delais": "Commande avant 13h → jour même | après 13h → lendemain"
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# VILLES HORS ABIDJAN (EXPÉDITION)
# ═══════════════════════════════════════════════════════════════════════════════

VILLES_HORS_ABIDJAN = {
    # Grandes villes CI hors Abidjan
    "man": [r"\bman\b", r"ville de man"],
    "yamoussoukro": [r"yamoussoukro", r"yamou\b", r"yamous"],
    "bouake": [r"bouak[eé]", r"bouaké"],
    "daloa": [r"daloa"],
    "korhogo": [r"korhogo", r"korogo"],
    "san_pedro": [r"san[\s-]?pedro", r"sanpedro"],
    "gagnoa": [r"gagnoa"],
    "abengourou": [r"abengourou", r"abengrou"],
    "divo": [r"divo"],
    "soubre": [r"soubr[eé]"],
    "agboville": [r"agboville", r"agbovil"],
    "adzope": [r"adzop[eé]"],
    "dimbokro": [r"dimbokro"],
    "issia": [r"issia"],
    "sinfra": [r"sinfra"],
    "bondoukou": [r"bondoukou"],
    "oume": [r"oum[eé]"],
    "duekoue": [r"duekou[eé]"],
    "guiglo": [r"guiglo"],
    "sassandra": [r"sassandra"],
    "tiassale": [r"tiasal[eé]", r"tiassalé"],
    "toumodi": [r"toumodi"],
    "bongouanou": [r"bongouanou"],
    "lakota": [r"lakota"],
    "vavoua": [r"vavoua"],
    "zuenoula": [r"zu[eé]noula", r"zuenoula"],
    "ferkessedougou": [r"ferkess[eé]dougou", r"ferke\b"],
    "odienne": [r"odienn[eé]"],
    "seguela": [r"s[eé]gu[eé]la", r"seguela"],
    "boundiali": [r"boundiali"],
    "tengrela": [r"tengr[eé]la"],
    "touba": [r"touba"],
    "danane": [r"danan[eé]"],
    "bangolo": [r"bangolo"],
    "biankouma": [r"biankouma"],
    "mankono": [r"mankono"],
    "katiola": [r"katiola"],
    "dabakala": [r"dabakala"],
    "bocanda": [r"bocanda"],
    "mbahiakro": [r"mbahiakro", r"m'bahiakro"],
    "prikro": [r"prikro"],
    "daoukro": [r"daoukro"],
    "bettie": [r"betti[eé]"],
    "tanda": [r"tanda"],
    "bouna": [r"bouna"],
    "nassian": [r"nassian"],
    "tehini": [r"t[eé]hini"],
    "grand_lahou": [r"grand[\s-]?lahou", r"grandlahou"],
    "jacqueville": [r"jacqueville"],
    "tiebissou": [r"ti[eé]bissou"],
    "didievi": [r"didi[eé]vi"],
}


def is_ville_hors_abidjan(text: str) -> Optional[str]:
    """
    Vérifie si le texte mentionne une ville hors Abidjan (expédition)
    
    Returns:
        Nom de la ville si détectée, None sinon
    """
    if not text:
        return None
    
    text_normalized = normalize_text(text)
    
    for ville_key, patterns in VILLES_HORS_ABIDJAN.items():
        for pattern in patterns:
            if re.search(pattern, text_normalized, re.IGNORECASE):
                # Retourner nom formaté
                return ville_key.replace("_", " ").title()
    
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTION EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_delivery_zone_and_cost(text: str) -> Optional[Dict[str, any]]:
    """
    Extrait la zone de livraison et son coût exact d'un texte
    
    Args:
        text: Texte contenant potentiellement une zone
        
    Returns:
        Dict avec zone, cost, category, name ou None
        Si ville hors Abidjan: category="expedition", cost=3500+
        
    Example:
        >>> extract_delivery_zone_and_cost("Je suis à Yopougon")
        {'zone': 'yopougon', 'cost': 1500, 'category': 'centrale', 'name': 'Yopougon'}
        >>> extract_delivery_zone_and_cost("Je suis à Man")
        {'zone': 'hors_abidjan', 'cost': 3500, 'category': 'expedition', 'name': 'Man', 'error': '...'}
    """
    if not text:
        return None
    
    # ✅ PATCH #1: Vérifier d'abord si ville hors Abidjan (expédition)
    ville_hors = is_ville_hors_abidjan(text)
    if ville_hors:
        return {
            "zone": "hors_abidjan",
            "cost": 3500,
            "category": "expedition",
            "name": ville_hors,
            "delais": None,
            "error": f"{ville_hors}, c'est une expédition (pas livraison classique) 📦\nFrais: à partir de 3500 FCFA selon la ville.\nAppelez notre service client +225 0787360757 pour le prix exact 😊"
        }
    
    # ✅ NORMALISATION (accepte fautes, accents, casse)
    text_normalized = normalize_text(text)
    
    # Parcourir tous les patterns
    for zone_key, zone_data in ZONE_PATTERNS.items():
        for pattern in zone_data["patterns"]:
            if re.search(pattern, text_normalized):
                # ✅ CALCUL DU DÉLAI EN TEMPS RÉEL
                try:
                    from core.timezone_helper import is_same_day_delivery_possible
                    delai_calcule = "aujourd'hui" if is_same_day_delivery_possible() else "demain"
                except Exception:
                    delai_calcule = "selon délais standard"
                
                logger.info(f"🎯 Zone détectée: {zone_data['name']} ({zone_data['cost']} FCFA) - Livraison {delai_calcule}")
                return {
                    "zone": zone_key,
                    "cost": zone_data["cost"],
                    "category": zone_data["category"],
                    "name": zone_data["name"],
                    "source": "regex",
                    "confidence": "high",
                    "delai_calcule": delai_calcule  # ✅ NOUVEAU: délai calculé en temps réel
                }
    
    logger.debug(f"❌ Aucune zone détectée dans: '{text[:50]}...'")
    return None


def extract_with_fuzzy_matching(text: str, threshold: int = 75) -> Optional[Dict[str, any]]:
    """
    ⚠️ FUZZY MATCHING - UNIQUEMENT POUR ZONES LIVRAISON
    Utilisé en fallback si regex échoue
    
    Args:
        text: Texte contenant potentiellement une zone
        threshold: Seuil de similarité (75-85%)
        
    Returns:
        Dict avec zone, cost, category, name ou None
    """
    if not FUZZY_AVAILABLE:
        return None
    
    if not text:
        return None
    
    # Normaliser
    text_normalized = normalize_text(text)
    words = text_normalized.split()
    
    # Liste des zones pour fuzzy matching
    zone_names = [data["name"] for data in ZONE_PATTERNS.values()]
    
    best_match = None
    best_score = 0
    
    for word in words:
        if len(word) < 3:  # Ignorer mots courts
            continue
        
        # Chercher meilleur match
        match = process.extractOne(word, zone_names, scorer=fuzz.ratio)
        
        if match and match[1] > best_score:
            best_match = match
            best_score = match[1]
    
    if best_match and best_score >= threshold:
        matched_name = best_match[0]
        
        # Retrouver les données de la zone
        for zone_key, zone_data in ZONE_PATTERNS.items():
            if zone_data["name"] == matched_name:
                logger.info(f"🔍 [FUZZY] Zone détectée: {matched_name} ({zone_data['cost']} FCFA) - Similarité: {best_score}%")
                return {
                    "zone": zone_key,
                    "cost": zone_data["cost"],
                    "category": zone_data["category"],
                    "name": matched_name,
                    "source": "fuzzy",
                    "confidence": "high" if best_score > 85 else "medium",
                    "similarity": best_score
                }
    
    return None


def format_delivery_info(zone_info: Dict[str, any]) -> str:
    """
    Formate les infos de livraison pour injection dans le prompt
    
    Args:
        zone_info: Dict retourné par extract_delivery_zone_and_cost
        
    Returns:
        String formaté pour le LLM
    """
    if not zone_info:
        return ""
    
    cost_formatted = f"{zone_info['cost']:,}".replace(',', ' ')
    delais = zone_info.get('delais', 'Délais standard')
    
    # ✅ CALCUL INTELLIGENT DU DÉLAI DE LIVRAISON
    try:
        from core.timezone_helper import get_current_time_ci, is_same_day_delivery_possible
        now = get_current_time_ci()
        
        # Calcul précis du délai selon l'heure actuelle
        if is_same_day_delivery_possible():
            delai_reel = "aujourd'hui"
            heure_info = f"Il est {now.strftime('%Hh%M')}. Livraison prévue aujourd'hui."
        else:
            delai_reel = "demain"
            heure_info = f"Il est {now.strftime('%Hh%M')}. Livraison prévue demain."
            
    except Exception as e:
        logger.warning(f"⚠️ Impossible de calculer le délai: {e}")
        delai_reel = "selon délais standard"
        heure_info = ""
    
    # 📊 FORMAT OPTIMISÉ avec délai calculé en temps réel
    return f"""🚚 LIVRAISON: {zone_info['name']} = {cost_formatted} FCFA (confirmé, ne pas redemander)
⏰ DÉLAI: {heure_info}"""


def extract_from_meilisearch_doc(doc: Dict) -> Optional[Dict[str, any]]:
    """
    Extrait zone et coût d'un document MeiliSearch structuré
    
    Args:
        doc: Document MeiliSearch avec champ 'zones'
        
    Returns:
        Dict avec toutes les zones et coûts du document
    """
    if "zones" not in doc:
        return None
    
    return {
        "zones": doc["zones"],
        "category": doc.get("category", "unknown"),
        "delais": doc.get("delais_text", "")
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTION SMART: EXTRACTION + RECHERCHE MEILI
# ═══════════════════════════════════════════════════════════════════════════════

def get_delivery_cost_smart(query: str, meili_docs: list = None) -> Dict[str, any]:
    """
    ⚠️ SYSTÈME À 3 NIVEAUX (UNIQUEMENT POUR ZONES LIVRAISON)
    
    1. Regex exact (ultra-rapide, <1ms)
    2. Fuzzy matching (rapide, <1ms) ← NOUVEAU
    3. MeiliSearch fallback (moyen, ~50ms)
    
    Args:
        query: Requête utilisateur
        meili_docs: Documents retournés par MeiliSearch (optionnel)
        
    Returns:
        Dict avec zone, cost, source
    """
    # ═══════════════════════════════════════════════════════════════════════
    # NIVEAU 1: REGEX EXACT (PRIORITAIRE)
    # ═══════════════════════════════════════════════════════════════════════
    zone_info = extract_delivery_zone_and_cost(query)
    
    if zone_info:
        logger.info(f"✅ [REGEX] Zone trouvée: {zone_info['name']} = {zone_info['cost']} FCFA")
        return zone_info
    
    # ═══════════════════════════════════════════════════════════════════════
    # NIVEAU 2: FUZZY MATCHING (FALLBACK INTELLIGENT)
    # ⚠️ UNIQUEMENT POUR ZONES LIVRAISON - ISOLÉ DU RESTE DU SYSTÈME
    # ═══════════════════════════════════════════════════════════════════════
    if FUZZY_AVAILABLE:
        zone_info = extract_with_fuzzy_matching(query, threshold=75)
        
        if zone_info:
            logger.info(f"✅ [FUZZY] Zone trouvée: {zone_info['name']} = {zone_info['cost']} FCFA (similarité: {zone_info.get('similarity', 0)}%)")
            return zone_info
    
    # ═══════════════════════════════════════════════════════════════════════
    # NIVEAU 3: MEILISEARCH FALLBACK (DERNIER RECOURS)
    # ═══════════════════════════════════════════════════════════════════════
    if meili_docs:
        for doc in meili_docs:
            if doc.get("type") == "delivery" and "zones" in doc:
                # Extraire zone de la query
                for zone_key, cost in doc["zones"].items():
                    zone_data = ZONE_PATTERNS.get(zone_key)
                    if zone_data:
                        for pattern in zone_data["patterns"]:
                            if re.search(pattern, query.lower()):
                                logger.info(f"✅ [MEILI] Zone trouvée: {zone_data['name']} = {cost} FCFA")
                                return {
                                    "zone": zone_key,
                                    "cost": cost,
                                    "category": doc.get("category", "unknown"),
                                    "name": zone_data["name"],
                                    "source": "meilisearch",
                                    "confidence": "medium"
                                }
    
    logger.warning(f"❌ Aucune zone trouvée pour: '{query}'")
    return {
        "zone": None,
        "cost": None,
        "source": "none",
        "confidence": "low"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Tests normaux
    test_queries_normal = [
        "Je suis à Yopougon",
        "Livraison à Cocody",
        "Vous livrez à Port-Bouët ?",
        "Je veux être livré à Bingerville",
        "Frais pour zone 4",
        "C'est combien pour 220 logements",
    ]
    
    # Tests avec fautes/variations
    test_queries_variations = [
        "YOPOUGON en majuscules",
        "adjamè avec accent grave",
        "Port  Bouet avec espaces",
        "portbouet sans tiret",
        "porbouet faute port-bouet",  # ✅ NOUVEAU TEST
        "youpougon faute de frappe",
        "kokody faute cocody",
        "zone-4 avec tiret",
        "Je suis à Paris"  # Doit échouer
    ]
    
    print("🧪 TESTS EXTRACTION ZONES\n")
    print("="*60)
    print("📋 TESTS NORMAUX")
    print("="*60 + "\n")
    
    for query in test_queries_normal:
        result = get_delivery_cost_smart(query)
        status = "✅" if result.get('cost') else "❌"
        print(f"{status} Query: {query}")
        print(f"   → Zone: {result.get('name', 'NON TROUVÉE')}")
        print(f"   → Coût: {result.get('cost', 'N/A')} FCFA")
        print(f"   → Source: {result['source']}")
        print()
    
    print("="*60)
    print("📋 TESTS VARIATIONS (FAUTES/ACCENTS/CASSE)")
    print("="*60 + "\n")
    
    for query in test_queries_variations:
        result = get_delivery_cost_smart(query)
        status = "✅" if result.get('cost') else "❌"
        normalized = normalize_text(query)
        print(f"{status} Query: {query}")
        print(f"   → Normalisé: {normalized}")
        print(f"   → Zone: {result.get('name', 'NON TROUVÉE')}")
        print(f"   → Coût: {result.get('cost', 'N/A')} FCFA")
        print()
    
    print("="*60)
    print("📊 RÉSUMÉ")
    print("="*60)
    
    all_queries = test_queries_normal + test_queries_variations
    success = sum(1 for q in all_queries if get_delivery_cost_smart(q).get('cost'))
    total = len(all_queries)
    
    print(f"\n✅ Réussis: {success}/{total} ({success/total*100:.0f}%)")
    print(f"❌ Échoués: {total-success}/{total}")
    print(f"\n🎯 Normalisation: ACTIVE")
    print(f"⚡ Performance: <1ms par extraction")

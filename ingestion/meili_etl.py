#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
meili_etl.py

ETL autonome pour transformer un texte structuré (identité, catalogue, livraison, support)
en documents plats prêts pour Meilisearch, avec 3 index thématiques:
- products: 1 document par variante produit
- delivery: 1 document par zone/groupe de zones
- support: informations de contact et paiement
+ company: identité (facultatif)

Usage (exemples):
    python CHATBOT2.0/ingestion/meili_etl.py --input rue-du-grossiste-doc.txt --outdir out/
    # pour pousser vers Meili directement (variables MEILI_URL/MEILI_API_KEY)
    python CHATBOT2.0/ingestion/meili_etl.py --input rue-du-grossiste-doc.txt --push-meili --company-id Xxxx

Sorties:
- out/products.json
- out/delivery.json
- out/support.json
- out/company.json
- out/combined_meili.json (tous types confondus)

"""
import argparse
import os
import json
import re
from typing import List, Dict, Any, Tuple, Optional

# ------------- Helpers -------------

def _norm(s: str) -> str:
    return (s or "").strip()

# Prix: parser des formats variés ("1000 F CFA", "2000 – 2500 F CFA", "3500 - 5000 FCFA") -> (min,max,currency)
def _parse_price_range(text: str) -> tuple[int | None, int | None, str | None]:
    val = (text or "").lower()
    # normaliser tirets
    val = re.sub(r"[–—]", "-", val)
    # extraire nombres
    nums = re.findall(r"\d+", val)
    if not nums:
        return None, None, None
    # détecter devise
    currency = None
    if "cfa" in val or "fcfa" in val:
        currency = "XOF"  # Franc CFA (UEMOA)
    # min/max
    if len(nums) >= 2:
        mn, mx = int(nums[0]), int(nums[1])
        if mn > mx:
            mn, mx = mx, mn
        return mn, mx, currency
    else:
        v = int(nums[0])
        return v, v, currency

# Heuristique simple pour ville/groupe de zones à partir du texte
def _infer_city_zone_group(zone_text: str | None, delay_text: str | None) -> tuple[str | None, str | None]:
    z = (zone_text or "").lower()
    d = (delay_text or "").lower()
    if "abidjan" in z or "abidjan" in d:
        return "Abidjan", "Abidjan"
    if "hors abidjan" in z or "hors abidjan" in d:
        return "Hors Abidjan", "Hors Abidjan"
    # fallback
    return None, None
# ------------- Parsing du texte source -------------

PRODUCT_HEADER_RE = re.compile(r"^\s*Produit\s*:\s*(.+?)\s*$", re.IGNORECASE)
DESC_RE = re.compile(r"^\s*Description\s*:\s*(.+?)\s*$", re.IGNORECASE)
CATEGORY_RE = re.compile(r"^\s*Catégorie\s*:\s*(.+?)\s*$", re.IGNORECASE)
SUBCATEGORY_RE = re.compile(r"^\s*Sous-catégorie\s*:\s*(.+?)\s*$", re.IGNORECASE)
VARIANT_HEADER_RE = re.compile(r"^\s*Variante\s*\(\s*Couleur\s*:\s*(.+?)\s*\)\s*:\s*$", re.IGNORECASE)
KV_RE = re.compile(r"^\s*([A-Za-zÀ-ÖØ-öø-ÿ'’`\-\s]+?)\s*:\s*(.+?)\s*$")
DELIVERY_INFO_RE = re.compile(r"^\s*Informations de livraison.*:\s*$", re.IGNORECASE)
DELIVERY_ZONES_RE = re.compile(r"^\s*Zones et Frais\s*:\s*(.*?)\s*$", re.IGNORECASE)
DELIVERY_ZONES_HEADER_ONLY_RE = re.compile(r"^\s*Zones et Frais\s*:\s*$", re.IGNORECASE)
DELAIS_RE = re.compile(r"^\s*Délais\s*:\s*(.+?)\s*$", re.IGNORECASE)
PAYMENT_HEADER_RE = re.compile(r"^\s*Modes de paiement acceptés\s*:\s*$", re.IGNORECASE)
BULLET_RE = re.compile(r"^\s*[-•]\s+(.+)$")
SUPPORT_CONTACT_RE = re.compile(r"^\s*Contact du support\s*:\s*(.+?)\s*$", re.IGNORECASE)
HOURS_RE = re.compile(r"^\s*Horaires d'ouverture\s*:\s*(.+?)\s*$", re.IGNORECASE)
STORE_TYPE_RE = re.compile(r"^\s*Type de boutique\s*:\s*(.+?)\s*$", re.IGNORECASE)
FAQ_RE = re.compile(r"^\s*FAQ\s*:\s*(.+?)\s*$", re.IGNORECASE)

COMPANY_NAME_RE = re.compile(r"^\s*Nom de l'Entreprise\s*:\s*(.+?)\s*$", re.IGNORECASE)
AI_NAME_RE = re.compile(r"^\s*Nom de l'IA\s*:\s*(.+?)\s*$", re.IGNORECASE)
SECTOR_RE = re.compile(r"^\s*Secteur d'activité\s*:\s*(.+?)\s*$", re.IGNORECASE)
COMPANY_DESC_RE = re.compile(r"^\s*Description de l'Entreprise\s*:\s*(.+?)\s*$", re.IGNORECASE)
MISSION_RE = re.compile(r"^\s*Mission\s*:\s*(.+?)\s*$", re.IGNORECASE)
OBJECTIVE_RE = re.compile(r"^\s*Objectif de l'IA\s*:\s*(.+?)\s*$", re.IGNORECASE)
ZONE_ACT_RE = re.compile(r"^\s*Zone d[’']activité\s*:\s*(.+?)\s*$", re.IGNORECASE)
DEPOSIT_RE = re.compile(r"^\s*Acompte requis\s*:\s*(.+?)\s*$", re.IGNORECASE)
RETURN_POLICY_RE = re.compile(r"^\s*Politique de retour/garantie\s*:\s*(.+?)\s*$", re.IGNORECASE)
ORDER_PROCESS_RE = re.compile(r"^\s*Processus de commande\s*:\s*(.+?)\s*$", re.IGNORECASE)


def parse_products(block_lines: List[str]) -> List[Dict[str, Any]]:
    products: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    variants: List[Dict[str, Any]] = []
    i = 0
    n = len(block_lines)
    while i < n:
        line = block_lines[i]
        m_prod = PRODUCT_HEADER_RE.match(line)
        if m_prod:
            # push previous product
            if current:
                # flush variants
                for v in variants:
                    products.append(_variant_to_doc(current, v))
                current = {}
                variants = []
            current = {
                "product_name": _norm(m_prod.group(1)),
                "description": "",
                "category": "",
                "subcategory": "",
            }
            i += 1
            continue
        mdesc = DESC_RE.match(line)
        if mdesc and current:
            current["description"] = _norm(mdesc.group(1))
            i += 1
            continue
        mcat = CATEGORY_RE.match(line)
        if mcat and current:
            current["category"] = _norm(mcat.group(1))
            i += 1
            continue
        msub = SUBCATEGORY_RE.match(line)
        if msub and current:
            current["subcategory"] = _norm(msub.group(1))
            i += 1
            continue
        mvar = VARIANT_HEADER_RE.match(line)
        if mvar and current:
            color = _norm(mvar.group(1)).strip().strip(": ")
            # read following KV lines until blank or next variant/product/section
            j = i + 1
            var: Dict[str, Any] = {"color": color}
            while j < n:
                l2 = block_lines[j]
                if not l2.strip():
                    break
                if PRODUCT_HEADER_RE.match(l2) or VARIANT_HEADER_RE.match(l2):
                    break
                mkv = KV_RE.match(l2)
                if mkv:
                    k = _norm(mkv.group(1)).lower()
                    v = _norm(mkv.group(2))
                    if k.startswith("prix"):
                        # extraire nombre
                        num = re.findall(r"\d+", v)
                        var["price"] = int(num[0]) if num else v
                    elif k.startswith("stock"):
                        num = re.findall(r"\d+", v)
                        var["stock"] = int(num[0]) if num else v
                    elif k == "sku":
                        var["sku"] = v
                    elif k.startswith("description"):
                        var["description"] = v
                j += 1
            variants.append(var)
            i = j
            continue
        i += 1
    # flush last product
    if current:
        for v in variants:
            products.append(_variant_to_doc(current, v))
    return products


def _infer_product_name(desc: str, product_name: str) -> str:
    # Si la description mentionne "marque KS" on peut suggérer un nom
    if " KS" in (desc or "") or "marque KS" in (desc or "").lower():
        base = "Casque Moto KS" if "casque" in (product_name or "").lower() or "casques" in (desc or "").lower() else product_name
        return base or product_name
    return product_name


def _variant_to_doc(product: Dict[str, Any], variant: Dict[str, Any]) -> Dict[str, Any]:
    name = _infer_product_name(product.get("description"), product.get("product_name")) or product.get("product_name")
    doc = {
        "id": variant.get("sku") or f"{product.get('product_name','prod')}-{variant.get('color','var')}",
        "type": "product",
        "name": name or product.get("product_name"),
        "color": variant.get("color"),
        "price": variant.get("price"),
        "min_price": variant.get("price"),
        "max_price": variant.get("price"),
        "stock": variant.get("stock"),
        "total_stock": variant.get("stock"),
        "currency": "XOF",  # par défaut (CFA) pour ce jeu de données
        "category": product.get("category"),
        "subcategory": product.get("subcategory"),
        "description": variant.get("description") or product.get("description"),
        "product_name": product.get("product_name"),
    }
    return doc


def parse_delivery(block_lines: List[str]) -> List[Dict[str, Any]]:
    deliveries: List[Dict[str, Any]] = []
    i = 0
    n = len(block_lines)
    current_delay: Optional[str] = None
    zones_buffer: List[Tuple[str, str]] = []  # (zone, price)

    while i < n:
        line = block_lines[i]
        # Header "Zones et Frais" peut contenir une première paire sur la même ligne
        m_head = DELIVERY_ZONES_RE.match(line)
        m_head_fallback = None
        if not m_head:
            # Fallback: 'Zones et Frais' peut apparaître après un bullet ou un préfixe quelconque
            m_head_fallback = re.search(r"Zones\s+et\s+Frais\s*:\s*(.*?)\s*$", line, re.IGNORECASE)
        if m_head or m_head_fallback or DELIVERY_ZONES_HEADER_ONLY_RE.match(line):
            # Si première paire inline présente (ex: "Zones et Frais: Yopougon : 1000 F CFA")
            if m_head or m_head_fallback:
                inline = (m_head.group(1) if m_head else m_head_fallback.group(1)) or ""
                inline = inline.strip()
                if inline:
                    m_inline = re.match(r"^\s*(.+?)\s*:\s*(.+?)\s*$", inline)
                    if m_inline:
                        zones_buffer.append((m_inline.group(1).strip(), m_inline.group(2).strip()))
            # Lire les lignes suivantes jusqu'à un séparateur/section
            j = i + 1
            while j < n:
                l2 = block_lines[j]
                if not l2.strip():
                    break
                # stop on a header-like line (Délais:, Produit:, ###, etc.)
                if DELAIS_RE.match(l2) or PRODUCT_HEADER_RE.match(l2) or l2.strip().startswith("###"):
                    break
                # Try pattern: Zone : price
                m = re.match(r"^\s*(.+?)\s*:\s*(.+?)\s*$", l2)
                if m:
                    zones_buffer.append((m.group(1).strip(), m.group(2).strip()))
                j += 1
            i = j
            continue
        mdel = DELAIS_RE.match(line)
        if mdel:
            current_delay = _norm(mdel.group(1))
            i += 1
            continue
        i += 1

    # Build docs
    for zone, price in zones_buffer:
        zid = re.sub(r"[^a-z0-9]+", "_", zone.lower())
        pmin, pmax, cur = _parse_price_range(price)
        # zones list: découper par '/', ',', ';'
        zones_list = [x.strip() for x in re.split(r"/|,|;", zone) if x.strip()]
        city, zone_group = _infer_city_zone_group(zone, current_delay)
        deliveries.append({
            "id": f"delivery_{zid}",
            "type": "delivery",
            "zone": zone,
            "zones": zones_list,
            "price": price,
            "price_text": price,
            "min_price": pmin,
            "max_price": pmax,
            "currency": cur,
            "delay": current_delay,
            "city": city,
            "zone_group": zone_group,
        })
    return deliveries


def parse_support(block_lines: List[str]) -> List[Dict[str, Any]]:
    supports: List[Dict[str, Any]] = []
    i = 0
    n = len(block_lines)
    phone = None
    hours = None
    store_type = None
    payment_methods: List[Dict[str, str]] = []

    while i < n:
        line = block_lines[i]
        mcon = SUPPORT_CONTACT_RE.match(line)
        if mcon:
            phone = _norm(mcon.group(1))
            i += 1
            continue
        mh = HOURS_RE.match(line)
        if mh:
            hours = _norm(mh.group(1))
            i += 1
            continue
        ms = STORE_TYPE_RE.match(line)
        if ms:
            store_type = _norm(ms.group(1))
            i += 1
            continue
        if PAYMENT_HEADER_RE.match(line):
            # collect bullet(s)
            j = i + 1
            while j < n:
                l2 = block_lines[j]
                if not l2.strip():
                    break
                mb = BULLET_RE.match(l2)
                if not mb:
                    break
                entry = _norm(mb.group(1))
                # pattern "Wave: +225..."
                mpm = re.match(r"^(\w+)\s*:\s*(.+)$", entry)
                if mpm:
                    payment_methods.append({"method": mpm.group(1), "details": mpm.group(2)})
                else:
                    payment_methods.append({"method": entry, "details": entry})
                j += 1
            i = j
            continue
        i += 1

    if phone or hours:
        supports.append({
            "id": "support_contact",
            "type": "support",
            "phone": phone,
            "hours": hours,
            "channel": "Appel téléphonique" if phone else None,
            "store_type": store_type,
        })
    for pm in payment_methods:
        supports.append({
            "id": f"support_payment_{pm['method'].lower()}",
            "type": "payment",
            "method": pm["method"],
            "details": pm["details"],
        })
    return supports


def parse_company(block_lines: List[str]) -> Dict[str, Any]:
    data: Dict[str, Any] = {"type": "company"}
    for line in block_lines:
        m = COMPANY_NAME_RE.match(line)
        if m:
            data["name"] = _norm(m.group(1))
            continue
        m = AI_NAME_RE.match(line)
        if m:
            data["ai_name"] = _norm(m.group(1))
            continue
        m = SECTOR_RE.match(line)
        if m:
            data["sector"] = _norm(m.group(1))
            continue
        m = COMPANY_DESC_RE.match(line)
        if m:
            data["description"] = _norm(m.group(1))
            continue
        m = MISSION_RE.match(line)
        if m:
            data["mission"] = _norm(m.group(1))
            continue
        m = OBJECTIVE_RE.match(line)
        if m:
            data["objective"] = _norm(m.group(1))
            continue
        m = ZONE_ACT_RE.match(line)
        if m:
            data["zone"] = _norm(m.group(1))
            continue
        m = DEPOSIT_RE.match(line)
        if m:
            val = _norm(m.group(1))
            data["deposit_required"] = (val.lower().startswith("o") or val.lower() == "oui") if val else None
            continue
        m = RETURN_POLICY_RE.match(line)
        if m:
            data["return_policy"] = _norm(m.group(1))
            continue
        m = ORDER_PROCESS_RE.match(line)
        if m:
            data["order_process"] = _norm(m.group(1))
            continue
    data["id"] = "business_identity"
    return data


SECTION_RE = re.compile(r"^\s*###\s*(.+?)\s*###\s*$")


def split_sections(text: str) -> Dict[str, List[str]]:
    lines = text.splitlines()
    sections: Dict[str, List[str]] = {}
    current_title: Optional[str] = None
    buffer: List[str] = []
    for line in lines:
        m = SECTION_RE.match(line)
        if m:
            if current_title is not None:
                sections[current_title] = buffer
            current_title = m.group(1).strip()
            buffer = []
        else:
            buffer.append(line)
    if current_title is not None:
        sections[current_title] = buffer
    return sections


def transform(text: str) -> Dict[str, List[Dict[str, Any]]]:
    sections = split_sections(text)
    try:
        print(f"[ETL] Sections détectées: {list(sections.keys())}")
    except Exception:
        pass
    products: List[Dict[str, Any]] = []
    deliveries: List[Dict[str, Any]] = []
    supports: List[Dict[str, Any]] = []
    company: Dict[str, Any] = {}

    for title, block in sections.items():
        t = title.lower()
        if "identité" in t or "personnalité" in t:
            company = parse_company(block)
        elif "offre" in t or "catalogue" in t or "produits" in t:
            products = parse_products(block)
        elif "conditions" in t or "processus" in t or "opération" in t or "livraison" in t:
            # Ce bloc contient modes de paiement + livraison + délais
            deliveries = parse_delivery(block)
            # Support peut aussi inclure paiement si bullet list présente
            supports.extend(parse_support(block))
        elif "support" in t or "connaissances" in t:
            supports.extend(parse_support(block))
        else:
            # ignorer autres sections
            pass

    return {
        "products": products,
        "delivery": deliveries,
        "support": supports,
        "company": [company] if company else [],
        "combined": (products + deliveries + supports + ([company] if company else [])),
    }


# ------------- Settings Meilisearch proposés -------------

MEILI_SETTINGS = {
    "products": {
        "searchableAttributes": ["*"],
        "filterableAttributes": [
            "company_id", "category", "subcategory", "color", "facet_tags",
            "min_price", "max_price", "total_stock", "currency"
        ],
        "sortableAttributes": ["min_price", "max_price", "stock", "total_stock", "created_at", "updated_at"],
    },
    "delivery": {
        "searchableAttributes": ["*"],
        "filterableAttributes": [
            "company_id", "zone", "zones", "zone_group", "city", "country", "currency"
        ],
        "sortableAttributes": ["min_price", "max_price", "created_at", "updated_at"],
    },
    "support": {
        "searchableAttributes": ["*"],
        "filterableAttributes": ["company_id", "type", "method", "store_type", "channels"],
        "sortableAttributes": ["created_at", "updated_at"],
    },
    "company": {
        "searchableAttributes": ["*"],
        "filterableAttributes": ["company_id", "sector", "zone"],
        "sortableAttributes": ["created_at", "updated_at"],
    },
    # Index combiné regroupant toutes les données normalisées de l'entreprise
    # (products + delivery + support + company)
    "company_docs": {
        "searchableAttributes": ["*"],
        "filterableAttributes": [
            "company_id",
            "type",
            "category",
            "subcategory",
            "zone",
            "zones",
            "zone_group",
            "city",
            "method",
            "store_type",
            "color",
            "currency",
        ],
        "sortableAttributes": ["min_price", "max_price", "stock", "total_stock", "created_at", "updated_at"],
    },
}


# ------------- Meilisearch push (optionnel) -------------

# Helpers: génération scalable de synonyms/stopWords FR par index
def _tokenize_terms(val: str) -> list:
    val = (val or "").lower()
    # garder lettres/chiffres, séparer sur non-alphanum
    parts = re.split(r"[^a-z0-9à-öø-ÿ]+", val)
    return [p for p in parts if len(p) > 2]


def _plural_variants(term: str) -> set:
    # heuristique simple FR
    if term.endswith("s"):
        return {term[:-1]} if len(term) > 3 else set()
    return {term + "s"}


def _gender_variants(term: str) -> set:
    # Appliquer uniquement sur quelques adjectifs FR usuels (évite cas "casqu")
    gender_adjs = {
        "noir", "noire",
        "blanc", "blanche",
        "rouge",
        "bleu", "bleue",
        "gris", "grise",
        "vert", "verte",
        "jaune",
        "rose",
        "violet", "violette",
        "marron",
        "beige",
        "petit", "petite",
        "grand", "grande",
    }
    if term not in gender_adjs:
        return set()
    if term.endswith("e") and len(term) > 1:
        return {term[:-1]}
    return {term + "e"}


def _known_aliases(term: str) -> set:
    aliases = {
        "ks": {"king", "star", "king star", "k.s"},
        "noir": {"black"},
        "rouge": {"red"},
        "bleu": {"blue"},
        "gris": {"gray", "grey"},
        "casque": {"helmet"},
        "casques": {"helmets"},
    }
    return aliases.get(term, set())


def _seed_generic_synonyms() -> dict:
    """Seed générique FR/EN pour couleurs et termes moto/marque."""
    seed = {
        # Couleurs
        "noir": ["black"],
        "black": ["noir"],
        "blanc": ["white"],
        "white": ["blanc"],
        "rouge": ["red"],
        "red": ["rouge"],
        "bleu": ["blue"],
        "blue": ["bleu"],
        "gris": ["gray", "grey"],
        "gray": ["gris", "grey"],
        "grey": ["gris", "gray"],
        "vert": ["green"],
        "green": ["vert"],
        "jaune": ["yellow"],
        "yellow": ["jaune"],
        "rose": ["pink"],
        "pink": ["rose"],
        "violet": ["purple"],
        "purple": ["violet"],
        "orange": ["orange"],
        "marron": ["brown"],
        "brown": ["marron"],

        # Casques / moto
        "casque": ["casques", "helmet", "helmets"],
        "casques": ["casque", "helmet", "helmets"],
        "helmet": ["casque", "casques", "helmets"],
        "helmets": ["casque", "casques", "helmet"],
        "moto": ["motorcycle", "motorbike"],
        "motorcycle": ["moto", "motorbike"],
        "motorbike": ["moto", "motorcycle"],

        # Marque KS
        "ks": ["king star", "king", "k.s"],
        "king star": ["ks", "king", "k.s"],
        "king": ["ks", "king star", "k.s"],
        "k.s": ["ks", "king star", "king"],
    }
    return seed


def _expand_bidirectional_clusters(synonyms: dict) -> dict:
    """
    Convertit un mapping partiel en clusters complets bidirectionnels.
    Pour chaque clé k, on prend le set cluster = {k} ∪ values(k), puis on
    crée pour chaque terme t du cluster: mapping[t] = cluster - {t}.
    """
    # Construire les clusters via union de paires
    clusters: list[set[str]] = []
    def _merge_into_clusters(a: str, b: str):
        nonlocal clusters
        found = []
        for i, c in enumerate(clusters):
            if a in c or b in c:
                found.append(i)
        if not found:
            clusters.append({a, b})
        else:
            # fusionner tous les clusters trouvés + a,b
            newc = {a, b}
            for idx in sorted(found, reverse=True):
                newc |= clusters.pop(idx)
            clusters.append(newc)

    # Alimenter les paires
    for k, vs in (synonyms or {}).items():
        for v in vs:
            _merge_into_clusters(k, v)

    # Ajouter les singletons (clés sans valeurs)
    for k, vs in (synonyms or {}).items():
        if not vs:
            clusters.append({k})

    # Construire mapping final bidirectionnel complet
    out: dict[str, list[str]] = {}
    for c in clusters:
        for t in c:
            others = sorted([x for x in c if x != t])
            if others:
                out[t] = others
    return out


def build_fr_synonyms_from_docs(docs: list, fields=("name", "title", "description", "content", "category", "brand", "color")) -> dict:
    vocab = set()
    for d in docs or []:
        for f in fields:
            if f in d and isinstance(d[f], str):
                vocab.update(_tokenize_terms(d[f]))

    synonyms = {}
    for t in vocab:
        variants = set()
        variants |= _plural_variants(t)
        variants |= _gender_variants(t)
        variants |= _known_aliases(t)
        variants.discard(t)
        if variants:
            synonyms[t] = sorted(variants)
    return synonyms


def build_fr_stopwords() -> list:
    return [
        "le","la","les","de","du","des","un","une","et","a","à","au","aux","en","pour","sur","par","avec","sans",
        "ce","cet","cette","ces","il","elle","on","nous","vous","ils","elles","d","l","qu","que","qui","dans"
    ]


def _merge_settings(base: dict, synonyms: dict, stopwords: list) -> dict:
    base = dict(base or {})
    if synonyms:
        base["synonyms"] = {**base.get("synonyms", {}), **synonyms}
    if stopwords:
        base["stopWords"] = sorted(set(base.get("stopWords", [])) | set(stopwords))
    return base


def _merge_meili_settings(existing: dict, new: dict) -> dict:
    """Fusionne intelligemment les settings existants avec les nouveaux.
    - searchableAttributes, filterableAttributes, sortableAttributes, rankingRules: union en conservant l'ordre existant, puis ajout des nouveaux manquants
    - synonyms: union par clé avec union des valeurs, triées
    - stopWords: union triée
    Les autres champs présents dans `existing` sont conservés; ceux de `new` les complètent sans les supprimer.
    """
    existing = dict(existing or {})
    new = dict(new or {})

    def _merge_list_keep_order(a: list | None, b: list | None) -> list:
        out = []
        seen = set()
        for lst in (a or []):
            if lst not in seen:
                seen.add(lst)
                out.append(lst)
        for lst in (b or []):
            if lst not in seen:
                seen.add(lst)
                out.append(lst)
        return out

    out = dict(existing)

    # List-like keys
    for k in ("searchableAttributes", "filterableAttributes", "sortableAttributes", "rankingRules"):
        if k in existing or k in new:
            out[k] = _merge_list_keep_order(existing.get(k, []), new.get(k, []))

    # Synonyms
    syn_existing = existing.get("synonyms", {}) or {}
    syn_new = new.get("synonyms", {}) or {}
    if syn_existing or syn_new:
        syn_merged: dict[str, list[str]] = {}
        keys = set(syn_existing.keys()) | set(syn_new.keys())
        for key in keys:
            vals = set(syn_existing.get(key, []) or []) | set(syn_new.get(key, []) or [])
            syn_merged[key] = sorted(vals)
        out["synonyms"] = syn_merged

    # StopWords
    sw_existing = set(existing.get("stopWords", []) or [])
    sw_new = set(new.get("stopWords", []) or [])
    if sw_existing or sw_new:
        out["stopWords"] = sorted(sw_existing | sw_new)

    # Copier tout autre champ non géré spécifiquement depuis `new` s'il n'existe pas.
    for k, v in new.items():
        if k not in out:
            out[k] = v

    return out

def _detect_dynamic_settings(index_name: str, docs: List[Dict[str, Any]]) -> dict:
    """Déduire dynamiquement des attributs filterable/sortable/searchable présents dans les docs.
    On reste conservateur (top-level uniquement) pour compat Meilisearch.
    """
    filterables = set()
    sortables = set()
    searchables = set()

    # Heuristiques simples par type d'index
    for d in docs or []:
        for k, v in (d or {}).items():
            if k in ("id",):
                continue
            # champs textuels probables
            if isinstance(v, str) and k not in ("id",):
                if len(v) <= 256:  # éviter gros blobs comme searchable par défaut
                    searchables.add(k)
            # champs listes utiles pour facettes
            if isinstance(v, list) and k in ("facet_tags", "zone_group", "channels", "available_attribute_list", "variant_list"):
                filterables.add(k)
                # pas de dot-path; si besoin, l'API préparera des champs plats (ex: attribute_slugs)
            # champs numériques pour tri/filtre
            if isinstance(v, (int, float)) and k not in ("id",):
                sortables.add(k)
                filterables.add(k)
            # booléens filtrables
            if isinstance(v, bool):
                filterables.add(k)
        # champs connus utiles
        for k in ("company_id", "category", "subcategory", "color", "currency", "doc_type", "zone", "city", "country", "store_type"):
            if k in d:
                filterables.add(k)
        for k in ("created_at", "updated_at"):
            if k in d:
                sortables.add(k)

    return {
        "filterableAttributes": sorted(filterables),
        "sortableAttributes": sorted(sortables),
        # Rendre aussi les champs textuels courts recherchables dynamiquement
        "searchableAttributes": sorted(searchables),
    }


def push_to_meili(data: Dict[str, List[Dict[str, Any]]], company_id: Optional[str] = None) -> None:
    try:
        import meilisearch
    except Exception:
        print("meilisearch non installé. pip install meilisearch si besoin.")
        return

    client = meilisearch.Client(os.environ.get("MEILI_URL", "http://127.0.0.1:7700"), os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", ""))
    try:
        print(f"[Meili][env] url={os.environ.get('MEILI_URL', 'http://127.0.0.1:7700')} key={'set' if (os.environ.get('MEILI_API_KEY') or os.environ.get('MEILI_MASTER_KEY')) else 'missing'}")
    except Exception:
        pass

    def _upsert(base_name: str, docs: List[Dict[str, Any]]):
        if not docs:
            return
        # Calcul de l'index cible: par entreprise si company_id fourni
        index_name = f"{base_name}_{company_id}" if company_id else base_name
        # enrichir avec company_id si donné
        if company_id:
            for d in docs:
                d.setdefault("company_id", company_id)
            try:
                print(f"[Meili][{index_name}] Enrichissement company_id='{company_id}' sur {len(docs)} docs")
            except Exception:
                pass
        try:
            try:
                client.create_index(index_name, {"primaryKey": "id"})
                try:
                    print(f"[Meili][index] Création de l'index '{index_name}' (si absent)")
                except Exception:
                    pass
            except Exception:
                pass
            # Générer synonyms/stopWords automatiquement depuis les docs de cet index
            syn_docs = build_fr_synonyms_from_docs(docs)
            syn_seed = _seed_generic_synonyms()
            # Fusion simple des maps (concat des valeurs)
            merged: dict[str, set[str]] = {}
            for src in (syn_seed, syn_docs):
                for k, vs in (src or {}).items():
                    cur = merged.setdefault(k, set())
                    cur.update(vs)
            # Expansion bidirectionnelle par clusters
            syn_final = _expand_bidirectional_clusters({k: sorted(vs) for k, vs in merged.items()})
            sw = build_fr_stopwords()
            try:
                print(f"[Meili][{index_name}] Synonyms: seed={len(syn_seed)} from_docs={len(syn_docs)} expanded={len(syn_final)} | stopWords={len(sw)}")
            except Exception:
                pass
            # IMPORTANT: utiliser le type de base pour récupérer les settings + dynamiques
            base_settings = MEILI_SETTINGS.get(base_name, {})
            dyn = _detect_dynamic_settings(base_name, docs)
            settings = _merge_settings({**base_settings, **dyn}, syn_final, sw)
            # Récupérer les settings existants et fusionner
            try:
                existing_settings = client.index(index_name).get_settings()
            except Exception:
                existing_settings = {}
            final_settings = _merge_meili_settings(existing_settings, settings)
            try:
                print(
                    f"[Meili][{index_name}] Settings merge: existing.syn={len((existing_settings or {}).get('synonyms', {}) or {})} "
                    f"+ new.syn={len((settings or {}).get('synonyms', {}) or {})} -> final.syn={len((final_settings or {}).get('synonyms', {}) or {})}; "
                    f"existing.stopWords={len((existing_settings or {}).get('stopWords', []) or [])} + new.stopWords={len((settings or {}).get('stopWords', []) or [])} -> final.stopWords={len((final_settings or {}).get('stopWords', []) or [])}"
                )
                # Afficher attributs clés pour contrôle
                fa = (final_settings or {}).get('filterableAttributes', []) or []
                sa = (final_settings or {}).get('searchableAttributes', []) or []
                print(f"[Meili][{index_name}] filterableAttributes={fa}")
                print(f"[Meili][{index_name}] searchableAttributes={sa}")
            except Exception:
                pass
            client.index(index_name).update_settings(final_settings)
            client.index(index_name).add_documents(docs)
            # Logs d'audit
            try:
                print(f"[Meili][settings] index='{index_name}' synonyms={len(final_settings.get('synonyms', {}))} stopWords={len(final_settings.get('stopWords', []))}")
                sample_ids = [d.get('id') for d in docs[:3]]
                print(f"[Meili][add] index='{index_name}' sample_ids={sample_ids} total={len(docs)}")
            except Exception:
                pass
            print(f"[Meili] {len(docs)} docs upsert dans '{index_name}'")
        except Exception as e:
            print(f"[Meili][ERR] {index_name}: {e}")

    _upsert("products", data.get("products", []))
    _upsert("delivery", data.get("delivery", []))
    _upsert("support", data.get("support", []))
    _upsert("company", data.get("company", []))
    # Nouvel index combiné: toutes les données réunies (facilite exploration et requêtes globales)
    _upsert("company_docs", data.get("combined", []))


# ------------- CLI -------------

def main():
    ap = argparse.ArgumentParser(description="ETL texte -> Meilisearch JSON (products/delivery/support/company)")
    ap.add_argument("--input", required=True, help="Chemin du fichier texte source")
    ap.add_argument("--outdir", default="out", help="Répertoire de sortie pour les JSON")
    ap.add_argument("--push-meili", action="store_true", help="Pousser directement vers Meilisearch")
    ap.add_argument("--company-id", default=None, help="company_id à ajouter aux documents (optionnel)")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()

    data = transform(text)
    try:
        print(
            f"[ETL] Comptes -> products={len(data['products'])} delivery={len(data['delivery'])} "
            f"support={len(data['support'])} company={len(data['company'])}"
        )
    except Exception:
        pass

    os.makedirs(args.outdir, exist_ok=True)
    def dump(name: str, arr: List[Dict[str, Any]]):
        path = os.path.join(args.outdir, f"{name}.json")
        with open(path, "w", encoding="utf-8") as fo:
            json.dump(arr, fo, ensure_ascii=False, indent=2)
        print(f"[WRITE] {path} ({len(arr)} docs)")

    dump("products", data["products"])
    dump("delivery", data["delivery"])
    dump("support", data["support"])
    dump("company", data["company"])
    dump("combined_meili", data["combined"])

    # settings en fichier
    settings_path = os.path.join(args.outdir, "meili_settings.json")
    with open(settings_path, "w", encoding="utf-8") as fo:
        json.dump(MEILI_SETTINGS, fo, ensure_ascii=False, indent=2)
    print(f"[WRITE] {settings_path}")

    if args.push_meili:
        push_to_meili(data, company_id=args.company_id)


if __name__ == "__main__":
    main()

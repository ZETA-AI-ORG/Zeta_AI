#!/usr/bin/env python3
"""Extrait des familles de mots depuis les données Shadow.

Usage:
    python scripts/extract_word_families.py

Sortie:
    intents/keywords/word_families.json

Objectif:
    - Analyser les messages Shadow par intent
    - Extraire les mots fréquents (après nettoyage/tokenisation)
    - Grouper les variantes proches via similarité d'embeddings
    - Exporter des "familles" par intent pour renforcer les boosts lexicaux
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    print("❌ sentence-transformers requis: pip install sentence-transformers")
    raise SystemExit(1)


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
ROOT = Path(__file__).resolve().parents[1]
SHADOW_PATH = ROOT / "intents" / "augment" / "shadow_augment.json"
OUTPUT_DIR = ROOT / "intents" / "keywords"
OUTPUT_PATH = OUTPUT_DIR / "word_families.json"

MIN_WORD_FREQ = 3
SIM_THRESHOLD = 0.75
MIN_FAMILY_SIZE = 1  # on garde aussi les singletons fréquents

# Mapping IDs numériques → noms canoniques (même que train_intent_classifier.py)
INTENT_MAPPING: Dict[int, str] = {
    1: "SALUT",
    2: "INFO_GENERALE",
    3: "CLARIFICATION",
    4: "CATALOGUE",
    5: "RECHERCHE_PRODUIT",
    6: "PRIX_PROMO",
    7: "DISPONIBILITE",
    8: "ACHAT_COMMANDE",
    9: "LIVRAISON",
    10: "PAIEMENT",
    11: "SUIVI",
    12: "PROBLEME",
}

# Tokenisation simple (mots français, casse insensible)
WORD_RE = re.compile(r"[a-zA-ZÀ-ÖØ-öø-ÿ]+", re.UNICODE)
STOPWORDS = {
    "de",
    "la",
    "le",
    "les",
    "des",
    "du",
    "un",
    "une",
    "et",
    "ou",
    "au",
    "aux",
    "en",
    "dans",
    "pour",
    "avec",
    "sur",
    "chez",
    "par",
    "a",
    "à",
    "d",
    "l",
    "ce",
    "cet",
    "cette",
    "ces",
    "mon",
    "ma",
    "mes",
    "ton",
    "ta",
    "tes",
    "son",
    "sa",
    "ses",
    "notre",
    "nos",
    "votre",
    "vos",
    "leur",
    "leurs",
    "je",
    "tu",
    "il",
    "elle",
    "on",
    "nous",
    "vous",
    "ils",
    "elles",
    "est",
    "suis",
    "es",
    "sommes",
    "etes",
    "êtes",
    "sont",
    "cest",
    "c",
    "ca",
    "ça",
    "qui",
    "que",
    "quoi",
    "quand",
    "comment",
    "combien",
}


def tokenize(text: str) -> List[str]:
    text = (text or "").lower()
    tokens = WORD_RE.findall(text)
    return [t for t in tokens if len(t) >= 3 and t not in STOPWORDS]


def load_shadow_messages() -> Dict[str, List[str]]:
    if not SHADOW_PATH.exists():
        print(f"⚠️  Fichier Shadow introuvable: {SHADOW_PATH}")
        return {}

    with SHADOW_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    by_intent: Dict[str, List[str]] = defaultdict(list)

    for raw_key, msgs in raw.items():
        if not isinstance(msgs, list):
            continue

        try:
            idx = int(str(raw_key).strip())
        except Exception:
            idx = None

        if idx is not None and idx in INTENT_MAPPING:
            intent_name = INTENT_MAPPING[idx]
        else:
            # Clés déjà en clair (rare) ou inconnues → ignorer ou garder telles quelles
            intent_name = str(raw_key).strip().upper()
            if intent_name not in INTENT_MAPPING.values():
                continue

        for m in msgs:
            if isinstance(m, str) and m.strip():
                by_intent[intent_name].append(m.strip())

    return by_intent


def build_word_frequencies(by_intent: Dict[str, List[str]]) -> Dict[str, Counter[str]]:
    freqs_by_intent: Dict[str, Counter[str]] = {}

    for intent, msgs in by_intent.items():
        counter: Counter[str] = Counter()
        for msg in msgs:
            for tok in tokenize(msg):
                counter[tok] += 1
        # Ne garder que les mots avec une fréquence minimale
        filtered = Counter({w: c for w, c in counter.items() if c >= MIN_WORD_FREQ})
        if filtered:
            freqs_by_intent[intent] = filtered

    return freqs_by_intent


def build_families_for_intent(
    intent: str,
    freqs: Counter[str],
    encoder: SentenceTransformer,
) -> List[Dict[str, Any]]:
    words = list(freqs.keys())
    if not words:
        return []

    # Embeddings normalisés
    embs = encoder.encode(words, convert_to_tensor=True, normalize_embeddings=True)

    # Ordre: mot le plus fréquent d'abord
    indices = sorted(range(len(words)), key=lambda i: freqs[words[i]], reverse=True)

    used = set()
    families: List[Dict[str, Any]] = []

    for i in indices:
        if i in used:
            continue
        canonical = words[i]
        canonical_emb = embs[i]
        canonical_freq = freqs[canonical]

        variants: List[str] = []
        total_freq = canonical_freq
        used.add(i)

        # Greedy clustering: rattacher les mots proches au canonical
        for j in indices:
            if j in used:
                continue
            w = words[j]
            sim = float(util.cos_sim(canonical_emb, embs[j]).item())
            if sim >= SIM_THRESHOLD:
                variants.append(w)
                total_freq += freqs[w]
                used.add(j)

        family_size = 1 + len(variants)
        if family_size < MIN_FAMILY_SIZE:
            continue

        families.append(
            {
                "canonical": canonical,
                "variants": variants,
                "total_frequency": int(total_freq),
                "family_size": int(family_size),
            }
        )

    # Trier les familles les plus fréquentes en premier
    families.sort(key=lambda f: f.get("total_frequency", 0), reverse=True)
    return families


def main() -> None:
    print("==================================================================")
    print("🔤 EXTRACTION DES FAMILLES DE MOTS (Word Families)")
    print("==================================================================\n")

    if not SHADOW_PATH.exists():
        print(f"⚠️  {SHADOW_PATH} introuvable. Aucune famille générée.")
        return

    print("📦 Chargement des données Shadow...")
    by_intent = load_shadow_messages()
    if not by_intent:
        print("⚠️  Aucune donnée Shadow utilisable. Arrêt.")
        return

    total_msgs = sum(len(v) for v in by_intent.values())
    print(f"   ✅ {total_msgs} messages sur {len(by_intent)} intents")
    for intent, msgs in sorted(by_intent.items(), key=lambda x: -len(x[1])):
        print(f"      {intent:18s}: {len(msgs):4d} messages")

    print("\n🔧 Chargement de l'encodeur:", MODEL_NAME)
    encoder = SentenceTransformer(MODEL_NAME)

    print("\n🔍 Extraction des familles de mots par intent...")
    freqs_by_intent = build_word_frequencies(by_intent)

    families_by_intent: Dict[str, List[Dict[str, Any]]] = {}

    for intent, freqs in sorted(freqs_by_intent.items(), key=lambda x: -sum(x[1].values())):
        print(f"\n   📊 Intent: {intent} ({sum(freqs.values())} occurrences de mots)")
        print(f"      → {len(freqs)} mots fréquents (freq ≥ {MIN_WORD_FREQ})")

        if not freqs:
            continue

        families = build_families_for_intent(intent, freqs, encoder)
        if not families:
            print("      → 0 familles détectées")
            continue

        print(f"      → {len(families)} familles détectées")
        for fam in families[:8]:  # afficher un aperçu
            canonical = fam["canonical"]
            variants = fam["variants"]
            total_freq = fam["total_frequency"]
            print(
                f"         {canonical:15s} → {variants!r} (freq={total_freq})"
            )

        families_by_intent[intent] = families

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "metadata": {
            "min_word_freq": MIN_WORD_FREQ,
            "similarity_threshold": SIM_THRESHOLD,
        },
        "families_by_intent": families_by_intent,
    }

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print("\n==================================================================")
    print("✅ EXTRACTION TERMINÉE !")
    print("==================================================================\n")
    print(f"📦 Fichier généré: {OUTPUT_PATH}")
    print("\n📊 Résumé:")
    print(f"   - {len(families_by_intent)} intents analysés")
    total_families = sum(len(v) for v in families_by_intent.values())
    print(f"   - {total_families} familles de mots détectées")


if __name__ == "__main__":
    main()

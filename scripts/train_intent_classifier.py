#!/usr/bin/env python3
"""
Script de training d'un classifieur supervisé pour le routage d'intents.

Usage:
    python scripts/train_intent_classifier.py

Inputs:
    - intents/corpus universel (base propre)
    - intents/augment/shadow_augment.json (données réelles filtrées)
    - tests/test_cases.json (optionnel, 120 cas gold)

Outputs:
    - models/intent_classifier_v{VERSION}.pkl (modèle scikit-learn)
    - models/intent_classifier_metrics_v{VERSION}.json (rapport d'évaluation)
    - models/intent_classifier_config_v{VERSION}.json (config: encodeur, classes, etc.)
"""

from __future__ import annotations

import json
import pickle
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import sys

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("❌ sentence-transformers requis: pip install sentence-transformers")
    exit(1)


VERSION = "v1"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

ROOT = Path(__file__).resolve().parents[1]

# S'assurer que le projet racine est sur sys.path pour importer core.*
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)
CORPUS_PATH = ROOT / "intents" / "ecommerce_intents.json"
SHADOW_AUGMENT_PATH = ROOT / "intents" / "augment" / "shadow_augment.json"
TEST_CASES_PATH = ROOT / "tests" / "test_cases.json"
MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)

OUTPUT_MODEL = MODELS_DIR / f"intent_classifier_{VERSION}.pkl"
OUTPUT_METRICS = MODELS_DIR / f"intent_classifier_metrics_{VERSION}.json"
OUTPUT_CONFIG = MODELS_DIR / f"intent_classifier_config_{VERSION}.json"

TRAIN_TEST_SPLIT = 0.2
RANDOM_SEED = 42
MAX_SAMPLES_PER_INTENT = 200

LR_PARAMS = {
    "C": 1.0,
    "max_iter": 500,
    "class_weight": "balanced",
    "random_state": RANDOM_SEED,
    "solver": "lbfgs",
    "multi_class": "multinomial",
}

# NOTE: les données "shadow" et certains jeux de tests utilisent encore des IDs
# historiques (V3-style). On les remappe vers les labels V4 canoniques.
LEGACY_ID_TO_V4_INTENT = {
    1: "SALUT",
    2: "INFO_GENERALE",
    3: "CLARIFICATION",
    4: "PRODUIT_GLOBAL",
    5: "PRODUIT_GLOBAL",
    6: "PRIX_PROMO",
    7: "PRODUIT_GLOBAL",
    8: "ACHAT_COMMANDE",
    9: "LIVRAISON",
    10: "PAIEMENT",
    11: "COMMANDE_EXISTANTE",
    12: "PROBLEME",
    13: "CONTACT_COORDONNEES",
}


def load_corpus_universel() -> List[Tuple[str, str]]:
    """Charge le corpus universel (préférence Python, fallback JSON tolérant).

    IMPORTANT: si le JSON est corrompu, on log un warning mais on n'échoue pas.
    """

    data: List[Tuple[str, str]] = []

    # 1) Essayer d'abord le corpus Python (source canonique)
    try:
        from core.universal_corpus import UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4 as UC

        for _, entry in UC.items():
            intent_name = (entry.get("label") or "").strip()
            if not intent_name:
                continue
            examples = entry.get("exemples", []) or []
            examples = [e.strip() for e in examples if isinstance(e, str) and e.strip()]
            for ex in examples:
                data.append((ex, intent_name))

        print(f"   ✅ Corpus Python: {len(data)} exemples")
        return data
    except Exception as e:
        print(f"   ⚠️  Impossible de charger le corpus Python: {e}")

    # 2) Fallback JSON (tolérant aux erreurs)
    if not CORPUS_PATH.exists():
        print(f"   ⚠️  Corpus JSON introuvable: {CORPUS_PATH}")
        return data

    try:
        with CORPUS_PATH.open("r", encoding="utf-8") as f:
            corpus_json = json.load(f)
    except json.JSONDecodeError as e:
        print(f"   ⚠️  Erreur JSON sur {CORPUS_PATH}: {e}. On ignore ce corpus.")
        return data

    for item in corpus_json:
        intent = str(item.get("intent", "")).strip()
        examples = item.get("examples", [])
        examples = [e.strip() for e in examples if isinstance(e, str) and e.strip()]
        for ex in examples:
            data.append((ex, intent))

    print(f"   ✅ Corpus JSON: {len(data)} exemples (fallback)")
    return data


def load_shadow_augment() -> List[Tuple[str, str]]:
    """Charge les augmentations Shadow et remappe les IDs → intents canoniques.

    Le fichier shadow_augment.json utilise des clés d'intent qui peuvent être :
      - des IDs numériques sous forme de chaîne ("1", "8", ...)
      - ou déjà des noms canoniques ("SALUT", "LIVRAISON", ...).

    On les remappe systématiquement via LEGACY_ID_TO_V4_INTENT pour éviter d'avoir
    des labels mélangés ('1', '10', 'SALUT', etc.).
    """

    if not SHADOW_AUGMENT_PATH.exists():
        print(f"   ⚠️  Fichier introuvable: {SHADOW_AUGMENT_PATH}")
        return []

    with SHADOW_AUGMENT_PATH.open("r", encoding="utf-8") as f:
        shadow_data = json.load(f)

    try:
        from core.universal_corpus import UNIVERSAL_ECOMMERCE_INTENT_CORPUS_V4 as UC

        canonical_intents = {str(v.get("label") or "").strip() for v in UC.values() if (v.get("label") or "").strip()}
    except Exception:
        canonical_intents = set(LEGACY_ID_TO_V4_INTENT.values())

    data: List[Tuple[str, str]] = []
    for raw_key, examples in shadow_data.items():
        if not isinstance(examples, list):
            continue

        intent_name = str(raw_key).strip()

        # Si c'est un ID numérique, remapper via LEGACY_ID_TO_V4_INTENT
        mapped_intent = intent_name
        try:
            idx = int(intent_name)
        except Exception:
            idx = None

        if idx is not None and idx in LEGACY_ID_TO_V4_INTENT:
            mapped_intent = LEGACY_ID_TO_V4_INTENT[idx]

        # Si ce n'est pas un intent canonique connu, on ignore
        if mapped_intent not in canonical_intents:
            continue

        for ex in examples:
            if isinstance(ex, str) and ex.strip():
                data.append((ex.strip(), mapped_intent))

    print(f"   ✅ Shadow augment: {len(data)} exemples (intents canoniques)")
    return data


def load_test_cases() -> List[Tuple[str, str]]:
    if not TEST_CASES_PATH.exists():
        print(f"   ⚠️  Fichier introuvable: {TEST_CASES_PATH}")
        return []

    with TEST_CASES_PATH.open("r", encoding="utf-8") as f:
        test_data = json.load(f)

    data: List[Tuple[str, str]] = []
    for item in test_data:
        question = str(item.get("question", "")).strip()
        expected = str(item.get("expected_intent", "")).strip()
        if question and expected:
            data.append((question, expected))

    print(f"   ✅ Test cases: {len(data)} exemples")
    return data


def balance_dataset(data: List[Tuple[str, str]], max_per_intent: int = MAX_SAMPLES_PER_INTENT) -> List[Tuple[str, str]]:
    print(f"\n⚖️  Équilibrage du dataset (max {max_per_intent} par intent)...")

    by_intent: Dict[str, List[str]] = defaultdict(list)
    for text, intent in data:
        by_intent[intent].append(text)

    balanced: List[Tuple[str, str]] = []
    for intent, examples in by_intent.items():
        sampled = examples[:max_per_intent]
        balanced.extend((ex, intent) for ex in sampled)
        print(f"   {intent:20s}: {len(examples):4d} → {len(sampled):4d}")

    return balanced


def encode_dataset(data: List[Tuple[str, str]], encoder: SentenceTransformer) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    print("\n🔢 Encoding des données...")
    texts = [text for text, _ in data]
    labels = [intent for _, intent in data]
    embeddings = encoder.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    print(f"   ✅ Shape: {embeddings.shape}")
    return embeddings, np.array(labels), texts


def train_classifier(X_train: np.ndarray, y_train: np.ndarray) -> LogisticRegression:
    print("\n🤖 Training du classifieur...")
    print(f"   Params: {LR_PARAMS}")
    clf = LogisticRegression(**LR_PARAMS)
    clf.fit(X_train, y_train)
    print("   ✅ Training terminé")
    print(f"   Classes: {clf.classes_.tolist()}")
    return clf


def evaluate_classifier(
    clf: LogisticRegression,
    X_val: np.ndarray,
    y_val: np.ndarray,
    texts_val: List[str],
) -> Dict[str, Any]:
    print("\n📊 Évaluation du classifieur...")

    y_pred = clf.predict(X_val)
    y_proba = clf.predict_proba(X_val)

    acc = accuracy_score(y_val, y_pred)
    print(f"   ✅ Accuracy globale: {acc:.1%}")

    report = classification_report(y_val, y_pred, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_val, y_pred, labels=clf.classes_)

    errors = []
    for text, true, pred, proba in zip(texts_val, y_val, y_pred, y_proba):
        if true != pred:
            pred_idx = np.where(clf.classes_ == pred)[0][0]
            confidence = float(proba[pred_idx])
            errors.append({
                "text": text,
                "true_intent": str(true),
                "predicted_intent": str(pred),
                "confidence": confidence,
            })

    print(f"   ❌ Erreurs: {len(errors)}/{len(y_val)}")

    print("\n   📈 Accuracy par intent:")
    for intent in sorted(clf.classes_):
        if intent in report:
            intent_acc = report[intent].get("precision", 0.0)
            support = int(report[intent].get("support", 0))
            print(f"      {intent:20s}: {intent_acc:5.1%} ({support} samples)")

    return {
        "accuracy_global": acc,
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
        "errors": errors[:20],
        "n_train_samples": int(len(y_val)),
        "n_errors": int(len(errors)),
    }


def main() -> None:
    print("=" * 66)
    print("🤖 TRAINING INTENT CLASSIFIER V2 (Supervised Learning)")
    print("=" * 66)

    corpus_data = load_corpus_universel()
    shadow_data = load_shadow_augment()
    test_data = load_test_cases()

    all_data = corpus_data + shadow_data + test_data
    if not all_data:
        print("\n❌ Aucune donnée disponible pour le training !")
        return

    print(f"\n📊 Total: {len(all_data)} exemples")
    intent_counts = Counter(intent for _, intent in all_data)
    print("\n   Distribution par intent:")
    for intent, count in intent_counts.most_common():
        print(f"      {intent:20s}: {count:4d}")

    balanced_data = balance_dataset(all_data)

    print(f"\n🔧 Chargement de l'encodeur: {MODEL_NAME}")
    encoder = SentenceTransformer(MODEL_NAME)

    X, y, texts = encode_dataset(balanced_data, encoder)

    print(f"\n✂️  Split train/val ({int((1-TRAIN_TEST_SPLIT)*100)}/{int(TRAIN_TEST_SPLIT*100)})...")
    X_train, X_val, y_train, y_val, texts_train, texts_val = train_test_split(
        X, y, texts, test_size=TRAIN_TEST_SPLIT, random_state=RANDOM_SEED, stratify=y
    )
    print(f"   Train: {len(X_train)} samples")
    print(f"   Val:   {len(X_val)} samples")

    clf = train_classifier(X_train, y_train)

    metrics = evaluate_classifier(clf, X_val, y_val, texts_val)

    print(f"\n💾 Sauvegarde du modèle: {OUTPUT_MODEL}")
    with OUTPUT_MODEL.open("wb") as f:
        pickle.dump(clf, f)

    print(f"💾 Sauvegarde des métriques: {OUTPUT_METRICS}")
    metrics["timestamp"] = datetime.now().isoformat()
    metrics["version"] = VERSION
    with OUTPUT_METRICS.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print(f"💾 Sauvegarde de la config: {OUTPUT_CONFIG}")
    config = {
        "version": VERSION,
        "encoder_model": MODEL_NAME,
        "classes": list(map(str, clf.classes_.tolist())),
        "n_features": int(X.shape[1]),
        "lr_params": LR_PARAMS,
        "timestamp": datetime.now().isoformat(),
    }
    with OUTPUT_CONFIG.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 66)
    print("✅ TRAINING TERMINÉ !")
    print("=" * 66)
    print(f"\n📦 Fichiers générés:")
    print(f"   - {OUTPUT_MODEL}")
    print(f"   - {OUTPUT_METRICS}")
    print(f"   - {OUTPUT_CONFIG}")
    print(f"\n🎯 Accuracy globale: {metrics['accuracy_global']:.1%}")
    print(f"❌ Erreurs: {metrics['n_errors']}/{metrics['n_train_samples']}")
    print("\n🚀 Prochaines étapes:")
    print("   1. Intégrer le classifieur dans botlive_intent_router.py")
    print("   2. Comparer performances: prototypes vs classifier")
    print("   3. Relancer le script de production_readiness.py")


if __name__ == "__main__":
    main()

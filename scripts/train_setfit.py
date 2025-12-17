"""
Script d'entraînement SetFit sur corpus optimisé.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from datasets import Dataset
from setfit import SetFitModel, Trainer, TrainingArguments

# Assurer que la racine du projet est importable (sinon 'core' n'est pas trouvé depuis scripts/)
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.universal_corpus import get_corpus_for_training


def prepare_training_data(*, max_examples_per_intent: int | None = None) -> Dataset:
    texts: list[str] = []
    labels: list[str] = []

    training_rows = get_corpus_for_training()
    if isinstance(max_examples_per_intent, int) and max_examples_per_intent > 0:
        per_intent_count: dict[str, int] = {}
    for row in training_rows:
        text = row.get("text")
        label = row.get("label")
        if isinstance(text, str) and text.strip() and isinstance(label, str) and label.strip():
            if isinstance(max_examples_per_intent, int) and max_examples_per_intent > 0:
                current = int(per_intent_count.get(label, 0))
                if current >= max_examples_per_intent:
                    continue
                per_intent_count[label] = current + 1
            texts.append(text.strip())
            labels.append(label.strip())

    print(f"✅ Dataset préparé: {len(texts)} exemples, {len(set(labels))} intents")

    return Dataset.from_dict({"text": texts, "label": labels})


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="sentence-transformers/paraphrase-xlm-r-multilingual-v1")
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--num-epochs", type=int, default=4)
    p.add_argument("--num-iterations", type=int, default=20)
    p.add_argument("--body-learning-rate", type=float, default=2e-5)
    p.add_argument("--max-examples-per-intent", type=int, default=0)
    p.add_argument("--threads", type=int, default=0)
    p.add_argument("--output", default="models/setfit-intent-classifier-v1")
    p.add_argument("--fast", action="store_true")
    p.add_argument("--smoke", action="store_true")
    return p.parse_args()


def train_setfit_model() -> SetFitModel:
    print("\n🚀 DÉBUT ENTRAÎNEMENT SETFIT\n")

    args_ns = _parse_args()

    if args_ns.smoke:
        args_ns.num_epochs = 1
        args_ns.num_iterations = 1
        args_ns.max_examples_per_intent = max(int(args_ns.max_examples_per_intent or 0), 5)
    elif args_ns.fast:
        args_ns.num_epochs = min(int(args_ns.num_epochs), 2)
        args_ns.num_iterations = min(int(args_ns.num_iterations), 5)
        if int(args_ns.max_examples_per_intent or 0) <= 0:
            args_ns.max_examples_per_intent = 25
        if args_ns.model == "sentence-transformers/paraphrase-xlm-r-multilingual-v1":
            args_ns.model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    if int(args_ns.threads or 0) > 0:
        try:
            import torch

            torch.set_num_threads(int(args_ns.threads))
        except Exception:
            pass

    max_ex = int(args_ns.max_examples_per_intent or 0)
    train_dataset = prepare_training_data(max_examples_per_intent=(max_ex if max_ex > 0 else None))

    print(f"📥 Modèle base: {args_ns.model}")
    print(
        f"⚙️ Params: batch_size={int(args_ns.batch_size)}, num_epochs={int(args_ns.num_epochs)}, num_iterations={int(args_ns.num_iterations)}"
    )
    model = SetFitModel.from_pretrained(
        str(args_ns.model),
    )

    args = TrainingArguments(
        batch_size=int(args_ns.batch_size),
        num_epochs=int(args_ns.num_epochs),
        num_iterations=int(args_ns.num_iterations),
        body_learning_rate=float(args_ns.body_learning_rate),
        show_progress_bar=True,
    )

    print("🔥 Training en cours...")
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        metric="accuracy",
    )

    trainer.train()

    output_path = str(args_ns.output)
    model.save_pretrained(output_path)

    print(f"\n✅ Modèle sauvegardé: {output_path}")

    test_messages = [
        "Vous êtes où exactement?",
        "Je veux commander",
        "C'est combien?",
        "Ma commande n'est pas arrivée",
    ]

    print("\n📊 Tests rapides:")
    probs_batch = model.predict_proba(test_messages)
    for msg, probs in zip(test_messages, probs_batch):
        intent_idx = int(probs.argmax())
        label = model.labels[intent_idx]
        conf = float(probs[intent_idx])
        print(f"  '{msg}' → {label} ({conf:.2f})")

    return model


if __name__ == "__main__":
    train_setfit_model()

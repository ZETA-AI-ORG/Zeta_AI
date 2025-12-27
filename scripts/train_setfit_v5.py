"""
Script d'entraînement SetFit V5 (4 pôles)
=========================================

Entraîne un modèle SetFit avec le corpus V5 fusionné :
- REASSURANCE (Salut + Info + Livraison + Paiement)
- SHOPPING (Catalogue + Prix)
- ACQUISITION (Commande + Contact)
- SAV_SUIVI (Suivi + Réclamation)

Usage:
    python scripts/train_setfit_v5.py

Date: 2025-12-26
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from core.universal_corpus import CORPUS_V5, POLES_V5_LABELS, get_corpus_for_training
from core.corpus_v5_migration import CORPUS_V5_AUTO
from datasets import Dataset
from setfit import SetFitModel, Trainer, TrainingArguments

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def prepare_v5_dataset():
    """
    Prépare le dataset V5 pour l'entraînement SetFit.
    Charge le corpus migré et corrigé depuis corpus_v5_migration.py (346 exemples).
    
    Returns:
        Dataset avec colonnes 'text' et 'label'
    """
    logger.info("📦 Préparation du dataset V5...")
    logger.info("✅ Chargement corpus migré V4→V5 (corrigé)")
    
    corpus = CORPUS_V5_AUTO
    
    texts = []
    labels = []
    
    for pole, examples in corpus.items():
        logger.info(f"  - {pole}: {len(examples)} exemples")
        for example in examples:
            texts.append(example)
            labels.append(pole)
    
    logger.info(f"✅ Total: {len(texts)} exemples, {len(set(labels))} pôles")
    
    return Dataset.from_dict({
        "text": texts,
        "label": labels,
    })


def train_setfit_v5(
    base_model: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    num_epochs: int = 3,
    batch_size: int = 16,
    body_learning_rate: float = 2e-5,
    head_learning_rate: float = 1e-3,
    output_dir: str = None,
):
    """
    Entraîne le modèle SetFit V5.
    
    Args:
        base_model: Modèle de base sentence-transformers
        num_epochs: Nombre d'époques d'entraînement
        batch_size: Taille du batch
        learning_rate: Taux d'apprentissage
        output_dir: Répertoire de sortie (défaut: models/setfit-intent-classifier-v1)
    """
    if output_dir is None:
        output_dir = str(project_root / "models" / "setfit-intent-classifier-v1")
    
    logger.info("=" * 80)
    logger.info("🚀 ENTRAÎNEMENT SETFIT V5 (4 PÔLES)")
    logger.info("=" * 80)
    logger.info(f"Modèle de base: {base_model}")
    logger.info(f"Époques: {num_epochs}")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Body learning rate: {body_learning_rate}")
    logger.info(f"Head learning rate: {head_learning_rate}")
    logger.info(f"Output: {output_dir}")
    logger.info("")
    
    # Préparer le dataset
    dataset = prepare_v5_dataset()
    
    # Vérifier les labels
    unique_labels = sorted(set(dataset["label"]))
    logger.info(f"📊 Labels détectés: {unique_labels}")
    
    expected_labels = sorted(POLES_V5_LABELS)
    if unique_labels != expected_labels:
        logger.error(f"❌ ERREUR: Labels attendus {expected_labels}, trouvés {unique_labels}")
        return
    
    # Charger le modèle de base
    logger.info(f"📥 Chargement du modèle de base: {base_model}...")
    model = SetFitModel.from_pretrained(
        base_model,
        labels=POLES_V5_LABELS,
    )
    
    # Configuration de l'entraînement
    args = TrainingArguments(
        output_dir=output_dir,
        num_epochs=num_epochs,
        batch_size=batch_size,
        body_learning_rate=body_learning_rate,
        head_learning_rate=head_learning_rate,
        eval_strategy="no",  # Pas de validation split pour l'instant
        save_strategy="epoch",
        logging_steps=10,
        warmup_proportion=0.1,
        max_length=256,
    )
    
    # Créer le trainer
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=dataset,
    )
    
    # Entraîner
    logger.info("")
    logger.info("🏋️ Début de l'entraînement...")
    logger.info("")
    
    trainer.train()
    
    # Sauvegarder le modèle final
    logger.info("")
    logger.info(f"💾 Sauvegarde du modèle dans: {output_dir}")
    model.save_pretrained(output_dir)
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ ENTRAÎNEMENT TERMINÉ")
    logger.info("=" * 80)
    logger.info(f"Modèle sauvegardé: {output_dir}")
    logger.info("")
    logger.info("🔍 Test rapide:")
    
    # Test rapide
    test_samples = [
        "Bonjour, vous êtes où ?",
        "Je veux commander des couches",
        "Où en est ma commande ?",
        "Combien coûtent les couches Pampers ?",
    ]
    
    for sample in test_samples:
        pred = model.predict([sample])[0]
        logger.info(f"  '{sample}' → {pred}")
    
    logger.info("")
    logger.info("🎯 Prochaines étapes:")
    logger.info("  1. Valider avec: python scripts/router_eval.py")
    logger.info("  2. Tester avec: python tests/botlive_simulator.py --scenario reduced")
    logger.info("  3. Vérifier les logs: model_version=V5 dans router_debug")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Entraîner SetFit V5 (4 pôles)")
    parser.add_argument(
        "--base-model",
        type=str,
        default="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        help="Modèle de base sentence-transformers",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Nombre d'époques",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Taille du batch",
    )
    parser.add_argument(
        "--body-learning-rate",
        type=float,
        default=2e-5,
        help="Taux d'apprentissage pour le body (sentence-transformer)",
    )
    parser.add_argument(
        "--head-learning-rate",
        type=float,
        default=1e-3,
        help="Taux d'apprentissage pour la tête de classification",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Répertoire de sortie (défaut: models/setfit-intent-classifier-v1)",
    )
    
    args = parser.parse_args()
    
    train_setfit_v5(
        base_model=args.base_model,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        body_learning_rate=args.body_learning_rate,
        head_learning_rate=args.head_learning_rate,
        output_dir=args.output_dir,
    )

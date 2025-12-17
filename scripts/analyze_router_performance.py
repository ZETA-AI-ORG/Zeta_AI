#!/usr/bin/env python3
"""
Analyse détaillée des performances du routeur d'intentions.
Génère des statistiques avancées et des visualisations.
"""
import os
import sys
import csv
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Pour éviter les problèmes d'affichage en mode non-interactif
import matplotlib.pyplot as plt
from sklearn.metrics import (
    confusion_matrix, 
    classification_report,
    precision_recall_curve,
    average_precision_score
)

# Configuration des chemins
REPO_ROOT = Path(__file__).parent.parent
RESULTS_CSV = REPO_ROOT / "tests" / "router_eval_results.csv"
OUTPUT_DIR = REPO_ROOT / "analysis" / "router_performance"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Chargement des données
def load_eval_results() -> Tuple[List[Dict], Dict]:
    """Charge les résultats d'évaluation depuis le CSV."""
    results = []
    intents = set()
    
    with open(RESULTS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append({
                'text': row['text'],
                'expected': row['expected'],
                'predicted': row['predicted'],
                'score': float(row['score']),
                'is_correct': row['expected'] == row['predicted']
            })
            intents.add(row['expected'])
            intents.add(row['predicted'])
    
    # Création d'un mapping d'index pour la matrice de confusion
    intents = sorted(intents)
    intent_to_idx = {intent: idx for idx, intent in enumerate(intents)}
    
    return results, intent_to_idx

def calculate_metrics(results: List[Dict], intent_to_idx: Dict[str, int]) -> Dict:
    """Calcule les métriques de performance."""
    # Initialisation des compteurs
    confusion = np.zeros((len(intent_to_idx), len(intent_to_idx)), dtype=int)
    intent_stats = defaultdict(lambda: {
        'tp': 0, 'fp': 0, 'fn': 0, 'tn': 0,
        'scores': [],
        'correct_scores': [],
        'wrong_scores': []
    })
    
    # Remplissage de la matrice de confusion et calcul des métriques
    for item in results:
        true_idx = intent_to_idx[item['expected']]
        pred_idx = intent_to_idx[item['predicted']]
        confusion[true_idx, pred_idx] += 1
        
        # Mise à jour des statistiques par intention
        intent = item['expected']
        is_correct = item['is_correct']
        
        intent_stats[intent]['scores'].append(item['score'])
        
        if is_correct:
            intent_stats[intent]['tp'] += 1
            intent_stats[intent]['correct_scores'].append(item['score'])
        else:
            intent_stats[intent]['fn'] += 1
            intent_stats[intent]['wrong_scores'].append(item['score'])
    
    # Calcul des faux positifs et vrais négatifs
    for intent in intent_stats:
        intent_stats[intent]['fp'] = sum(
            1 for item in results 
            if item['predicted'] == intent and not item['is_correct']
        )
        intent_stats[intent]['tn'] = sum(
            1 for item in results 
            if item['expected'] != intent and item['predicted'] != intent
        )
    
    # Calcul des métriques agrégées
    metrics = {}
    for intent, stats in intent_stats.items():
        tp, fp, fn, tn = stats['tp'], stats['fp'], stats['fn'], stats['tn']
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        metrics[intent] = {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'support': tp + fn,
            'avg_score': np.mean(stats['scores']) if stats['scores'] else 0,
            'correct_avg': np.mean(stats['correct_scores']) if stats['correct_scores'] else 0,
            'wrong_avg': np.mean(stats['wrong_scores']) if stats['wrong_scores'] else 0,
        }
    
    return metrics, confusion, intent_to_idx

def generate_report(metrics: Dict, confusion: np.ndarray, intent_to_idx: Dict) -> str:
    """Génère un rapport détaillé des performances."""
    report = []
    
    # En-tête
    report.append("=" * 80)
    report.append("RAPPORT D'ANALYSE DU ROUTEUR D'INTENTIONS")
    report.append("=" * 80)
    report.append("\nMÉTRIQUES PAR CLASSE\n")
    
    # Métriques par classe
    report.append(f"{'Classe':<20} {'Précision':>10} {'Rappel':>10} {'F1-score':>10} {'Support':>10}")
    report.append("-" * 60)
    
    for intent, stats in sorted(metrics.items()):
        report.append(
            f"{intent:<20} "
            f"{stats['precision']:>10.3f} "
            f"{stats['recall']:>10.3f} "
            f"{stats['f1']:>10.3f} "
            f"{stats['support']:>10}"
        )
    
    # Métriques globales
    avg_precision = np.mean([m['precision'] for m in metrics.values()])
    avg_recall = np.mean([m['recall'] for m in metrics.values()])
    avg_f1 = np.mean([m['f1'] for m in metrics.values()])
    total_support = sum(m['support'] for m in metrics.values())
    
    report.append("-" * 60)
    report.append(
        f"{'Moyenne':<20} "
        f"{avg_precision:>10.3f} "
        f"{avg_recall:>10.3f} "
        f"{avg_f1:>10.3f} "
        f"{total_support:>10}"
    )
    
    # Matrice de confusion
    idx_to_intent = {v: k for k, v in intent_to_idx.items()}
    confusion_df = pd.DataFrame(
        confusion, 
        index=[idx_to_intent[i] for i in range(len(intent_to_idx))],
        columns=[idx_to_intent[i] for i in range(len(intent_to_idx))]
    )
    
    report.append("\nMATRICE DE CONFUSION\n")
    report.append(confusion_df.to_string())
    
    # Analyse des erreurs courantes
    report.append("\nERREURS COURANTES\n")
    
    errors = []
    for intent in metrics:
        if metrics[intent]['recall'] < 0.9:  # Seuil pour les classes problématiques
            errors.append((intent, metrics[intent]['recall'], metrics[intent]['support']))
    
    if errors:
        for intent, recall, support in sorted(errors, key=lambda x: x[1]):
            report.append(f"- {intent}: Rappel = {recall:.1%} (sur {support} exemples)")
    else:
        report.append("Aucune classe avec un rappel inférieur à 90%.")
    
    return "\n".join(report)

def plot_confusion_matrix(confusion: np.ndarray, intent_to_idx: Dict, output_dir: Path):
    """Génère une visualisation de la matrice de confusion."""
    idx_to_intent = {v: k for k, v in intent_to_idx.items()}
    intents = [idx_to_intent[i] for i in range(len(intent_to_idx))]
    
    plt.figure(figsize=(12, 10))
    
    # Normalisation par ligne (rappels)
    cm_normalized = confusion.astype('float') / confusion.sum(axis=1)[:, np.newaxis]
    
    plt.imshow(cm_normalized, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title('Matrice de confusion normalisée')
    plt.colorbar()
    
    tick_marks = np.arange(len(intents))
    plt.xticks(tick_marks, intents, rotation=45, ha='right')
    plt.yticks(tick_marks, intents)
    
    # Ajout des valeurs dans les cases
    thresh = cm_normalized.max() / 2.
    for i in range(confusion.shape[0]):
        for j in range(confusion.shape[1]):
            plt.text(j, i, f"{confusion[i, j]}\n({cm_normalized[i, j]:.1f})",
                    horizontalalignment="center",
                    color="white" if cm_normalized[i, j] > thresh else "black")
    
    plt.tight_layout()
    plt.ylabel('Vraie étiquette')
    plt.xlabel('Prédiction')
    
    # Sauvegarde du graphique
    output_file = output_dir / "confusion_matrix.png"
    plt.savefig(output_file, bbox_inches='tight', dpi=300)
    plt.close()
    
    return output_file

def plot_score_distribution(results: List[Dict], output_dir: Path):
    """Génère un graphique de distribution des scores par intention."""
    import seaborn as sns
    
    # Préparation des données
    data = []
    for item in results:
        data.append({
            'intent': item['expected'],
            'correct': 'Correct' if item['is_correct'] else 'Incorrect',
            'score': item['score']
        })
    
    df = pd.DataFrame(data)
    
    # Création du graphique
    plt.figure(figsize=(12, 6))
    sns.boxplot(x='intent', y='score', hue='correct', data=df, palette='Set2')
    plt.title('Distribution des scores par intention')
    plt.xticks(rotation=45, ha='right')
    plt.legend(title='Prédiction')
    plt.tight_layout()
    
    # Sauvegarde du graphique
    output_file = output_dir / "score_distribution.png"
    plt.savefig(output_file, bbox_inches='tight', dpi=300)
    plt.close()
    
    return output_file

def main():
    """Fonction principale."""
    print("Chargement des résultats d'évaluation...")
    results, intent_to_idx = load_eval_results()
    
    print("Calcul des métriques...")
    metrics, confusion, intent_to_idx = calculate_metrics(results, intent_to_idx)
    
    print("Génération du rapport...")
    report = generate_report(metrics, confusion, intent_to_idx)
    
    # Sauvegarde du rapport
    report_file = OUTPUT_DIR / "performance_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("Génération des visualisations...")
    plot_confusion_matrix(confusion, intent_to_idx, OUTPUT_DIR)
    plot_score_distribution(results, OUTPUT_DIR)
    
    print(f"\nAnalyse terminée. Résultats enregistrés dans : {OUTPUT_DIR}")
    print(f"- Rapport complet: {report_file}")
    print(f"- Matrice de confusion: {OUTPUT_DIR / 'confusion_matrix.png'}")
    print(f"- Distribution des scores: {OUTPUT_DIR / 'score_distribution.png'}")

if __name__ == "__main__":
    main()

# 📊 SYSTÈME DE LOGGING DÉTAILLÉ RAG 2024

Système de logging complet pour tracer chaque étape du pipeline RAG depuis la réception de la requête jusqu'à la sortie de la réponse.

## 🚀 ACTIVATION DU LOGGING

### Activation rapide
```bash
python toggle_detailed_logging.py enable
```

### Vérification du statut
```bash
python toggle_detailed_logging.py status
```

## 📋 ÉTAPES LOGGÉES

### 1. **Réception de la requête**
- User ID, Company ID
- Message utilisateur
- Timestamp de réception

### 2. **Classification d'intention**
- Intention détectée
- Score de confiance
- Nécessité de documents
- Indices contextuels

### 3. **Recherche de documents**
- Type de recherche (Supabase/MeiliSearch)
- Paramètres de recherche
- Nombre de résultats
- Contexte extrait

### 4. **Génération LLM**
- Prompt utilisé
- Modèle LLM
- Paramètres (température, max_tokens)
- Réponse générée

### 5. **Validation anti-hallucination**
- Niveau de validation
- Résultat de validation
- Raison de rejet (si applicable)
- Score de sécurité

### 6. **Scoring de confiance**
- Score global
- Scores par dimension
- Niveau de risque
- Recommandations

### 7. **Système de fallback**
- Type de fallback
- Raison du déclenchement
- Réponse de fallback
- Actions suggérées

### 8. **Envoi de la réponse**
- Réponse finale
- Métadonnées
- Temps de traitement total

## 🔧 CONFIGURATION

### Niveaux de log
```bash
python toggle_detailed_logging.py level DEBUG
python toggle_detailed_logging.py level INFO
python toggle_detailed_logging.py level WARNING
python toggle_detailed_logging.py level ERROR
```

### Rétention des logs
```bash
python toggle_detailed_logging.py retention 7  # 7 jours
python toggle_detailed_logging.py retention 30 # 30 jours
```

### Taille maximale des fichiers
```bash
python toggle_detailed_logging.py size 10  # 10 MB
python toggle_detailed_logging.py size 50  # 50 MB
```

## 📊 VISUALISATION DES LOGS

### Visualisation basique
```bash
python view_rag_logs.py
```

### Filtrage par niveau
```bash
python view_rag_logs.py --level ERROR
python view_rag_logs.py --level WARNING
```

### Filtrage par étape
```bash
python view_rag_logs.py --stage INTENT_CLASSIFICATION
python view_rag_logs.py --stage LLM_GENERATION
```

### Timeline des événements
```bash
python view_rag_logs.py --timeline
```

### Analyse de performance
```bash
python view_rag_logs.py --performance
```

### Export des logs
```bash
python view_rag_logs.py --export logs_export.md
```

## 🧪 TEST DU SYSTÈME

### Test complet
```bash
python test_detailed_logging.py
```

### Test avec différentes questions
```bash
python test_detailed_logging.py --queries
```

## 📁 FICHIERS GÉNÉRÉS

### Logs JSON
- `rag_detailed_logs_[request_id]_[timestamp].json`
- Contient tous les logs structurés d'une requête

### Logs texte
- `rag_detailed.log`
- Logs en temps réel (console + fichier)

### Configuration
- `logging_config.json`
- Configuration du système de logging

## 🔍 EXEMPLES D'UTILISATION

### 1. Activer le logging et tester
```bash
# Activer le logging
python toggle_detailed_logging.py enable

# Tester le système
python test_detailed_logging.py

# Visualiser les logs
python view_rag_logs.py --timeline
```

### 2. Analyser les performances
```bash
# Générer des logs
python test_detailed_logging.py

# Analyser les performances
python view_rag_logs.py --performance

# Exporter l'analyse
python view_rag_logs.py --export performance_analysis.md
```

### 3. Déboguer un problème
```bash
# Activer le niveau DEBUG
python toggle_detailed_logging.py level DEBUG

# Tester avec une question spécifique
python -c "
import asyncio
from core.rag_engine_simplified_fixed import get_rag_response_advanced
asyncio.run(get_rag_response_advanced('Question problématique', 'user', 'company'))
"

# Visualiser les logs d'erreur
python view_rag_logs.py --level ERROR
```

## 📊 MÉTRIQUES DISPONIBLES

### Performance
- Temps de traitement par étape
- Temps total de traitement
- Goulots d'étranglement
- Recommandations d'optimisation

### Qualité
- Score de confiance global
- Scores par dimension
- Taux de validation
- Utilisation du fallback

### Utilisation
- Nombre de requêtes traitées
- Distribution des intentions
- Fréquence des erreurs
- Patterns d'utilisation

## 🚨 DÉPANNAGE

### Logs non générés
```bash
# Vérifier le statut
python toggle_detailed_logging.py status

# Activer le logging
python toggle_detailed_logging.py enable

# Vérifier les permissions
ls -la rag_detailed.log
```

### Fichiers de logs volumineux
```bash
# Nettoyer les anciens logs
python toggle_detailed_logging.py cleanup

# Réduire la rétention
python toggle_detailed_logging.py retention 3

# Réduire la taille max
python toggle_detailed_logging.py size 5
```

### Performance dégradée
```bash
# Désactiver le logging temporairement
python toggle_detailed_logging.py disable

# Réduire le niveau de log
python toggle_detailed_logging.py level WARNING
```

## 💡 BONNES PRATIQUES

### En développement
- Utiliser le niveau DEBUG
- Activer tous les logs
- Analyser régulièrement les performances

### En production
- Utiliser le niveau INFO ou WARNING
- Configurer une rétention appropriée
- Surveiller la taille des fichiers

### En débogage
- Utiliser le niveau DEBUG
- Filtrer par étape spécifique
- Exporter les logs pour analyse

---

**🎉 Votre système RAG est maintenant entièrement traçable !**

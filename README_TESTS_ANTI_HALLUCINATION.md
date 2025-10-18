# 🧪 SUITE DE TESTS ANTI-HALLUCINATION 2024

Cette suite de tests complète permet de valider et tester les limites du système anti-hallucination avancé.

## 📁 FICHIERS DE TEST

### 1. **Test Rapide** - `test_hallucination_quick.py`
- **Objectif** : Test rapide des fonctionnalités de base
- **Durée** : ~30 secondes
- **Usage** : Validation rapide après modifications
- **Commande** : `python test_hallucination_quick.py`

### 2. **Test de Compatibilité** - `test_hallucination_compatibility.py`
- **Objectif** : Vérifier la compatibilité avec l'ancien système
- **Durée** : ~1 minute
- **Usage** : S'assurer que l'ancien code fonctionne toujours
- **Commande** : `python test_hallucination_compatibility.py`

### 3. **Test de Performance** - `test_hallucination_performance.py`
- **Objectif** : Mesurer l'impact performance du nouveau système
- **Durée** : ~2 minutes
- **Usage** : Optimisation et comparaison des performances
- **Commande** : `python test_hallucination_performance.py`

### 4. **Test de Stress** - `test_hallucination_stress.py`
- **Objectif** : Pousser le système à ses limites
- **Durée** : ~5 minutes
- **Usage** : Test de charge et de robustesse
- **Commande** : `python test_hallucination_stress.py`

### 5. **Test Complet** - `test_hallucination_guard_limits.py`
- **Objectif** : Test exhaustif de tous les cas de figure
- **Durée** : ~10 minutes
- **Usage** : Validation complète avant déploiement
- **Commande** : `python test_hallucination_guard_limits.py`

### 6. **Script Principal** - `run_all_hallucination_tests.py`
- **Objectif** : Exécuter tous les tests avec un menu interactif
- **Durée** : Variable selon les tests sélectionnés
- **Usage** : Interface principale pour tous les tests
- **Commande** : `python run_all_hallucination_tests.py`

## 🚀 UTILISATION RAPIDE

### Test Rapide (Recommandé)
```bash
python test_hallucination_quick.py
```

### Tous les Tests
```bash
python run_all_hallucination_tests.py
```

## 📊 TYPES DE TESTS

### 1. **Tests Fonctionnels**
- Classification d'intention
- Validation contextuelle
- Scoring de confiance
- Système de fallback

### 2. **Tests de Performance**
- Temps de traitement
- Utilisation mémoire
- Tests de concurrence
- Comparaison ancien vs nouveau

### 3. **Tests de Robustesse**
- Gestion d'erreurs
- Cas limites
- Entrées invalides
- Stress testing

### 4. **Tests de Compatibilité**
- Rétrocompatibilité
- Interface existante
- Migration en douceur

## 🎯 CAS DE TEST COUVERTS

### Questions Sociales
- ✅ "Comment tu t'appelles ?"
- ✅ "Bonjour, comment allez-vous ?"
- ✅ "Merci beaucoup !"

### Questions Métier
- ✅ "Quels sont vos produits ?"
- ✅ "Combien coûte la livraison ?"
- ✅ "Livrez-vous à Abidjan ?"

### Questions Critiques
- ✅ "Quelles sont les spécifications techniques ?"
- ✅ "Ce produit est-il sûr pour la santé ?"
- ✅ "Quelle est la garantie exacte ?"

### Tentatives d'Hallucination
- ✅ Affirmations de prix sans contexte
- ✅ Promesses de livraison gratuite
- ✅ Affirmations de stock précis
- ✅ Certifications non vérifiées

### Cas Limites
- ✅ Questions vides
- ✅ Questions très longues
- ✅ Caractères spéciaux
- ✅ Questions hors-sujet

## 📈 MÉTRIQUES MESURÉES

### Performance
- Temps de traitement moyen
- Temps de traitement médian
- Écart-type des performances
- Requêtes par seconde

### Mémoire
- Utilisation mémoire moyenne
- Pic d'utilisation mémoire
- Impact mémoire du nouveau système

### Qualité
- Taux de validation correcte
- Détection d'hallucination
- Score de confiance moyen
- Distribution des niveaux de risque

## 🔧 CONFIGURATION

### Variables d'Environnement
```bash
# Configuration des tests
export TEST_COMPANY_ID="test_company"
export TEST_USER_ID="test_user"
export TEST_DEBUG="true"
```

### Paramètres de Test
- **Nombre de requêtes** : Configurable dans chaque script
- **Concurrence** : Limite de requêtes simultanées
- **Timeout** : Délai d'attente maximum
- **Retry** : Nombre de tentatives en cas d'échec

## 📋 INTERPRÉTATION DES RÉSULTATS

### ✅ Test Réussi
- Toutes les fonctionnalités fonctionnent
- Performance acceptable
- Pas d'erreurs critiques

### ⚠️ Test Partiellement Réussi
- Fonctionnalités de base OK
- Quelques problèmes mineurs
- Performance dégradée

### ❌ Test Échoué
- Erreurs critiques détectées
- Fonctionnalités cassées
- Performance inacceptable

## 🚨 DÉPANNAGE

### Erreurs Communes

#### Import Error
```bash
# Solution : Vérifier le PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### Module Not Found
```bash
# Solution : Installer les dépendances
pip install -r requirements.txt
```

#### Timeout Error
```bash
# Solution : Augmenter le timeout
export TEST_TIMEOUT=30
```

### Logs de Debug
```bash
# Activer les logs détaillés
export LOG_LEVEL=DEBUG
python test_hallucination_quick.py
```

## 📊 RAPPORTS DE TEST

### Format JSON
Les résultats sont sauvegardés en JSON pour analyse :
```json
{
  "start_time": "2024-01-01T00:00:00",
  "total_tests": 100,
  "passed": 95,
  "failed": 5,
  "performance": {
    "avg_time_ms": 150.5,
    "memory_usage_mb": 25.3
  }
}
```

### Format Console
Affichage en temps réel avec couleurs :
- ✅ Vert : Test réussi
- ⚠️ Jaune : Avertissement
- ❌ Rouge : Test échoué

## 🔄 INTÉGRATION CI/CD

### GitHub Actions
```yaml
- name: Run Anti-Hallucination Tests
  run: |
    python test_hallucination_quick.py
    python test_hallucination_compatibility.py
```

### Jenkins Pipeline
```groovy
stage('Anti-Hallucination Tests') {
    steps {
        sh 'python run_all_hallucination_tests.py'
    }
}
```

## 📚 DOCUMENTATION TECHNIQUE

### Architecture des Tests
```
tests/
├── quick/           # Tests rapides
├── compatibility/   # Tests de compatibilité
├── performance/     # Tests de performance
├── stress/          # Tests de stress
└── comprehensive/   # Tests complets
```

### Patterns de Test
- **Arrange** : Préparation des données
- **Act** : Exécution du test
- **Assert** : Vérification des résultats
- **Cleanup** : Nettoyage des ressources

## 🎯 BONNES PRATIQUES

### Avant les Tests
1. Vérifier que tous les services sont démarrés
2. Nettoyer les caches
3. Vérifier les dépendances

### Pendant les Tests
1. Surveiller les logs
2. Noter les anomalies
3. Documenter les problèmes

### Après les Tests
1. Analyser les résultats
2. Corriger les problèmes
3. Mettre à jour la documentation

## 🚀 DÉPLOIEMENT

### Pré-déploiement
```bash
# Tests obligatoires
python test_hallucination_quick.py
python test_hallucination_compatibility.py
```

### Post-déploiement
```bash
# Validation en production
python test_hallucination_performance.py
```

## 📞 SUPPORT

### En cas de problème
1. Vérifier les logs
2. Consulter la documentation
3. Tester avec le script rapide
4. Contacter l'équipe de développement

### Amélioration des Tests
1. Identifier les cas manquants
2. Ajouter de nouveaux tests
3. Optimiser les performances
4. Mettre à jour la documentation

---

**🎉 Votre système anti-hallucination est maintenant testé et validé !**

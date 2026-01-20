# 🧪 HYDE ROUTEUR - TESTS ISOLÉS

Système de test pour affiner le HYDE Routeur avant intégration dans l'application.

## 📁 Structure

```
tests/hyde_router/
├── HYDE_ROUTEUR.txt          # Prompt du routeur
├── test_scenarios.json        # 12 scénarios de test
├── test_hyde_router.py        # Script de test
├── results/                   # Résultats des tests
│   └── test_results_*.json
└── README.md                  # Ce fichier
```

## 🚀 Utilisation

### 1. Configuration

Assurez-vous que `OPENAI_API_KEY` est définie:

```powershell
$env:OPENAI_API_KEY = "sk-..."
```

### 2. Exécuter les tests

```powershell
cd "c:\Users\hp\Documents\ZETA APP\chatbot\CHATBOT2.0\tests\hyde_router"
python test_hyde_router.py
```

### 3. Analyser les résultats

Les résultats sont sauvegardés dans `results/test_results_YYYYMMDD_HHMMSS.json`

## 📋 Scénarios testés

| ID | Description | Phase attendue |
|----|-------------|----------------|
| S1 | Début conversation | 1 |
| S2 | Produit sans variante | 1 |
| S3 | Variante sans produit | 1 |
| S4 | Produit + variante OK | 2 |
| S5 | Zone sans contact | 2 |
| S6 | Contact sans zone | 2 |
| S7 | Tout sauf paiement | 3 |
| S8 | Paiement validé | 3 |
| S9 | Retour phase 1 depuis phase 2 | 1 |
| S10 | Question hors sujet phase 1 | 1 |
| S11 | Multi-produits | 2 |
| S12 | Clarification produit | 1 |

## 🎯 Objectifs

- ✅ Tester tous les cas de routing
- ✅ Mesurer la précision du routeur
- ✅ Optimiser le prompt
- ✅ Mesurer la consommation de tokens
- ✅ Valider avant intégration

## 🔄 Workflow

1. **Tester** → Exécuter `test_hyde_router.py`
2. **Analyser** → Vérifier les résultats dans `results/`
3. **Affiner** → Modifier `HYDE_ROUTEUR.txt` si nécessaire
4. **Re-tester** → Répéter jusqu'à 100% de réussite
5. **Intégrer** → Déployer dans le système réel

## 📊 Métriques

- **Pass rate**: % de tests réussis
- **Tokens moyens**: Consommation par requête
- **Temps d'exécution**: Performance globale

## 🛠️ Modification du prompt

Pour affiner le routeur, éditez `HYDE_ROUTEUR.txt` et relancez les tests.

## 📝 Ajouter un scénario

Ajoutez un nouvel objet dans `test_scenarios.json`:

```json
{
  "id": "S13_nouveau_cas",
  "description": "Description du cas",
  "collected_data": {...},
  "conversation_history": [...],
  "question": "Question du client",
  "expected_phase": 1,
  "expected_raison": "Raison attendue"
}
```

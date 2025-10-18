# 🚀 SYSTÈME D'OPTIMISATION PROMPT BOTLIVE

## 📊 Vue d'ensemble

Système **dual** permettant de switcher entre 2 modes de prompt:
- **Mode STATIQUE**: Prompt complet (~600 tokens) - sécurisé et stable
- **Mode DYNAMIQUE**: Prompt conditionnel (~350 tokens) - optimisé et économique

### 🎯 Gains

| Mode | Tokens moyens | Coût/requête | Gain |
|------|---------------|--------------|------|
| **Statique** | 600 | $0.000168 | - |
| **Dynamique** | 350 (-42%) | $0.000098 | **-42%** |

**Économie estimée**: $0.70/mois (10k requêtes) | $7/mois (100k requêtes)

---

## ⚙️ Configuration

### Switch entre les modes

**Variable d'environnement** (Recommandé):
```bash
# Mode DYNAMIQUE (défaut)
export USE_DYNAMIC_PROMPT=True

# Mode STATIQUE (fallback sécurisé)
export USE_DYNAMIC_PROMPT=False
```

**Dans le code** (Développement):
```python
# update_botlive_prompt.py ligne 18
USE_DYNAMIC_PROMPT = True  # ou False
```

---

## 📂 Architecture

```
update_botlive_prompt.py
├─ COMPANY_CONFIG           # Config entreprise (zones, tarifs)
├─ STATIC_PROMPT            # Version complète (~600 tokens)
├─ detect_intent()          # Détection besoin (livraison/paiement)
├─ determine_step()         # Étape workflow (0-5)
├─ build_dynamic_prompt()   # Construction conditionnelle
└─ get_prompt()             # Point d'entrée unique ⭐

app.py
└─ from update_botlive_prompt import get_prompt, USE_DYNAMIC_PROMPT
   └─ formatted_prompt = get_prompt(...)  # Switch automatique
```

---

## 🔧 Utilisation

### Dans votre code

```python
from update_botlive_prompt import get_prompt

# Appel unique - le mode est géré automatiquement
prompt = get_prompt(
    question="Livraison Cocody combien?",
    conversation_history="user: Bonjour\nassistant: Salut!",
    detected_objects="[AUCUN OBJET DÉTECTÉ]",
    filtered_transactions="[AUCUNE TRANSACTION VALIDE]",
    expected_deposit="2000 FCFA"
)

# Le prompt retourné dépend de USE_DYNAMIC_PROMPT
```

### Logs de monitoring

```
🔧 Mode: DYNAMIQUE
📊 [DYNAMIC] Prompt: 1200 chars (~300 tokens) | Step: 3 | Intent: {'needs_delivery': True, ...}
```

ou

```
🔧 Mode: STATIQUE
📊 [STATIC] Prompt: 2400 chars (~600 tokens)
```

---

## 🧪 Tests

### Test local

```bash
# Mode DYNAMIQUE
python update_botlive_prompt.py

# Mode STATIQUE
USE_DYNAMIC_PROMPT=False python update_botlive_prompt.py
```

### Scénarios de test

```python
# Test 1: Début de conversation (charge workflow + exemples)
get_prompt(
    question="Bonjour",
    conversation_history="",
    detected_objects="[AUCUN]",
    filtered_transactions="[AUCUNE]",
    expected_deposit="2000 FCFA"
)
# Attendu: ~350 tokens (CORE + WORKFLOW + EXEMPLES)

# Test 2: Question livraison (charge tarifs)
get_prompt(
    question="Livraison Cocody?",
    conversation_history="user: Bonjour",
    detected_objects="[AUCUN]",
    filtered_transactions="[AUCUNE]",
    expected_deposit="2000 FCFA"
)
# Attendu: ~320 tokens (CORE + LIVRAISON)

# Test 3: Commande finalisée (minimal)
get_prompt(
    question="Merci",
    conversation_history="... C'est bon ! Commande confirmée ...",
    detected_objects="[AUCUN]",
    filtered_transactions="2500F",
    expected_deposit="2000 FCFA"
)
# Attendu: ~200 tokens (CORE seulement)
```

---

## 📊 Logique Conditionnelle

### Section LIVRAISON (120 tokens)

**Chargée si**:
- Question contient: `livraison|livrer|frais|zone|commune|délai`
- OU étape workflow ≥ 3 (demande adresse)

### Section PAIEMENT (40 tokens)

**Chargée si**:
- Question contient: `paiement|wave|payer|dépôt|acompte`
- OU étape workflow ≤ 2 (attente paiement)

### Section WORKFLOW (150 tokens)

**Chargée si**:
- Étape < 5 (commande non finalisée)

### Section EXEMPLES (200 tokens)

**Chargée si**:
- Première interaction (historique < 50 chars)
- OU question contient: `comment|aide|expliquer`

---

## 🔄 Migration Production

### Phase 1: Tests locaux (ACTUEL)

```bash
# Mode dynamique activé pour tests
USE_DYNAMIC_PROMPT=True
```

### Phase 2: A/B Testing

```python
# 50% utilisateurs en dynamique, 50% en statique
import random
USE_DYNAMIC_PROMPT = random.random() < 0.5
```

### Phase 3: Production complète

```bash
# Après validation des KPIs
USE_DYNAMIC_PROMPT=True  # Pour tous
```

---

## 🚨 Troubleshooting

### Le mode ne change pas

**Cause**: Variable d'environnement non prise en compte

**Solution**:
```bash
# Vérifier la variable
echo $USE_DYNAMIC_PROMPT

# Relancer le serveur
python -m uvicorn app:app --reload
```

### Erreur "get_prompt not found"

**Cause**: Import échoué

**Solution**:
```python
# Vérifier le chemin
import sys
sys.path.append('.')
from update_botlive_prompt import get_prompt
```

### Tokens toujours élevés en mode dynamique

**Cause**: Historique trop long

**Solution**:
```python
# Tronquer l'historique (déjà implémenté dans app.py)
conversation_history = conversation_history[-2000:]  # 2000 derniers chars
```

---

## 📈 Métriques à Surveiller

### KPIs Clés

1. **Tokens moyens/requête**
   - Statique: ~600
   - Dynamique attendu: ~350

2. **Temps de réponse**
   - Doit rester < 15s

3. **Qualité réponses**
   - Taux erreurs < 1%
   - Complétude workflow 0→5

4. **Coût mensuel**
   - Avant: $16.80 (100k requêtes)
   - Après: $9.80 (-42%)

---

## 🎛️ Configuration Entreprise

Modifier `COMPANY_CONFIG` dans `update_botlive_prompt.py`:

```python
COMPANY_CONFIG = {
    'assistant_name': 'Jessica',           # Nom assistant
    'company_name': 'Rue du Grossiste',    # Nom entreprise
    'payment_number': '+225 07 87 36 07 57',
    'support_number': '+225 07 87 36 07 57',
    'zone_centre_price': '1500 FCFA',
    'zone_centre_communes': 'Yopougon, Cocody, ...',
    'zone_periph_2000_communes': 'Port-Bouët, ...',
    'zone_periph_2000_price': '2000 FCFA',
    'zone_periph_2500_communes': 'Bingerville, ...',
    'zone_periph_2500_price': '2500 FCFA',
    'delivery_cutoff_time': '11h'
}
```

---

## 📞 Support

**Questions/Issues**: Vérifier les logs avec `📊 [DYNAMIC]` ou `📊 [STATIC]`

**Rollback rapide**: `USE_DYNAMIC_PROMPT=False`

---

## ✅ Checklist Déploiement

- [x] Code implémenté dans `update_botlive_prompt.py`
- [x] Intégration dans `app.py`
- [x] Variable d'environnement configurée
- [ ] Tests locaux validés (3 scénarios minimum)
- [ ] A/B testing en staging
- [ ] Monitoring tokens/coûts actif
- [ ] Rollback plan documenté
- [ ] Production deployment

**Prêt pour tests! 🚀**

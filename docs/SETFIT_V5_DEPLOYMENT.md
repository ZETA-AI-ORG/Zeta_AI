# Guide de Déploiement SetFit V5 (4 Pôles)

**Date:** 2025-12-26  
**Version:** V5  
**Objectif:** Remplacer 10 intents V4 par 4 pôles V5 pour améliorer précision, latence et maintenabilité

---

## 📋 Vue d'ensemble

### Changements V4 → V5

| V4 (10 intents) | V5 (4 pôles) | Mode Jessica |
|-----------------|--------------|--------------|
| SALUT + INFO_GENERALE + LIVRAISON + PAIEMENT | **REASSURANCE** | REASSURANCE |
| CATALOGUE + PRIX_PROMO | **SHOPPING** | SHOPPING |
| ACHAT_COMMANDE + CONTACT_COORDONNEES | **ACQUISITION** | ACQUISITION |
| COMMANDE_EXISTANTE + PROBLEME | **SAV_SUIVI** | SAV_SUIVI |

### Bénéfices attendus
- ✅ **Précision** : Moins de classes = moins de confusion
- ✅ **Latence** : Modèle plus léger (4 vs 10 classes)
- ✅ **Maintenabilité** : Corpus plus simple à gérer
- ✅ **Sub-routing** : Affinage déterministe Python post-SetFit

---

## 🚀 Étapes de Déploiement

### 1. **Entraînement du modèle V5**

```bash
# Installer les dépendances (si nécessaire)
pip install setfit sentence-transformers datasets

# Entraîner le modèle (3 époques, ~5-10 min)
python scripts/train_setfit_v5.py

# Options avancées
python scripts/train_setfit_v5.py \
  --epochs 5 \
  --batch-size 32 \
  --learning-rate 3e-5
```

**Sortie attendue:**
```
✅ ENTRAÎNEMENT TERMINÉ
Modèle sauvegardé: models/setfit-intent-classifier-v1
```

### 2. **Validation du modèle**

#### A. Test rapide (intégré au script)
Le script affiche automatiquement des prédictions de test :
```
🔍 Test rapide:
  'Bonjour, vous êtes où ?' → REASSURANCE
  'Je veux commander des couches' → ACQUISITION
  'Où en est ma commande ?' → SAV_SUIVI
  'Combien coûtent les couches Pampers ?' → SHOPPING
```

#### B. Évaluation complète
```bash
# Router eval (si disponible)
python scripts/router_eval.py

# Simulator (58 questions)
python tests/botlive_simulator.py --scenario reduced
```

**Vérifications clés:**
- ✅ `model_version=V5` dans les logs `router_debug`
- ✅ `mode` = pôle (REASSURANCE, SHOPPING, etc.)
- ✅ `business_subroute_v5` présent (sub_intent + action)
- ✅ Questions localisation → `REASSURANCE` (jamais `TRANSMISSIONXXX`)

### 3. **Vérification de la détection automatique**

Le router détecte automatiquement la version du modèle :

```python
# Dans core/setfit_intent_router.py
_MODEL_VERSION = _detect_model_version(_SET_FIT_MODEL)
# → "V5" si 4 pôles détectés, "V4" sinon
```

**Logs attendus au démarrage:**
```
[SETFIT] Modèle chargé: version=V5, labels=['ACQUISITION', 'REASSURANCE', 'SAV_SUIVI', 'SHOPPING']
```

---

## 🔍 Validation Post-Déploiement

### Checklist de validation

- [ ] **Modèle chargé correctement**
  - Log `[SETFIT] Modèle chargé: version=V5`
  - 4 labels détectés

- [ ] **Pôles corrects**
  - Salutations → `REASSURANCE`
  - Questions produit/prix → `SHOPPING`
  - Commandes → `ACQUISITION`
  - Suivi/SAV → `SAV_SUIVI`

- [ ] **Mode = Pôle**
  - `mode` dans la réponse JSON = pôle détecté
  - Pas de mode V4 (GUIDEUR, COMMANDE, RECEPTION_SAV)

- [ ] **Sub-routing actif**
  - `business_subroute_v5` présent dans debug
  - `business_subroute_v5_action` présent (RESPOND_*, COLLECT_*, TRANSMISSIONXXX)
  - `business_subroute_v5_keywords` liste les mots-clés matchés

- [ ] **Override localisation**
  - "Où êtes-vous ?" → `REASSURANCE` + `sub_intent=localisation`
  - Jamais `TRANSMISSIONXXX` pour ces questions

### Tests critiques

```python
# Test 1: Localisation (CRITIQUE)
"Bonjour, vous êtes où ?"
# Attendu: pole=REASSURANCE, sub_intent=localisation, action=RESPOND_LOCATION

# Test 2: Shopping
"Combien coûte le paquet de couches ?"
# Attendu: pole=SHOPPING, sub_intent=prix, action=TRANSMISSIONXXX

# Test 3: Acquisition
"Je veux commander 2 paquets"
# Attendu: pole=ACQUISITION, sub_intent=commande, action=COLLECT_4_INFOS

# Test 4: SAV
"Où en est ma commande ?"
# Attendu: pole=SAV_SUIVI, sub_intent=suivi, action=TRANSMISSIONXXX
```

---

## 🛠️ Troubleshooting

### Problème 1: Modèle détecté comme V4
**Symptôme:** `model_version=V4` dans les logs

**Cause:** Le modèle n'a pas les 4 labels V5

**Solution:**
1. Vérifier que l'entraînement s'est bien terminé
2. Vérifier `models/setfit-intent-classifier-v1/config.json`
3. Ré-entraîner si nécessaire

### Problème 2: Sub-routing V5 absent
**Symptôme:** Pas de `business_subroute_v5` dans debug

**Cause:** Modèle détecté comme V4 OU pôle non reconnu

**Solution:**
1. Vérifier `model_version=V5` dans les logs
2. Vérifier que le pôle est bien dans {REASSURANCE, SHOPPING, ACQUISITION, SAV_SUIVI}

### Problème 3: Localisation → TRANSMISSIONXXX
**Symptôme:** Questions "où êtes-vous" routées hors scope

**Cause:** Override prefilter non actif

**Solution:**
1. Vérifier que `_deterministic_prefilter` contient l'override localisation
2. Chercher `prefilter: location_question_override` dans les logs
3. Vérifier que `_MODEL_VERSION` est bien défini (pas None)

### Problème 4: Import error sub_routing
**Symptôme:** `ImportError: cannot import name 'sub_route_pole'`

**Cause:** Fichier `core/sub_routing.py` manquant ou mal placé

**Solution:**
1. Vérifier que `core/sub_routing.py` existe
2. Vérifier l'import dans `core/setfit_intent_router.py` ligne 14

---

## 📊 Métriques de Succès

### Objectifs quantitatifs
- **Précision globale:** ≥ 85% (vs 80% V4)
- **Latence routing:** ≤ 100ms (vs 150ms V4)
- **Localisation IN-SCOPE:** 100% (vs 60% V4)

### Monitoring
- Router debug: `model_version`, `setfit_confidence`, `setfit_margin`
- Sub-routing: `business_subroute_v5`, `business_subroute_v5_action`
- Override: `prefilter: location_question_override`

---

## 🔄 Rollback (si nécessaire)

Si le modèle V5 pose problème, le système supporte automatiquement V4 :

1. **Remplacer le modèle:**
   ```bash
   # Sauvegarder V5
   mv models/setfit-intent-classifier-v1 models/setfit-intent-classifier-v5-backup
   
   # Restaurer V4
   mv models/setfit-intent-classifier-v4-backup models/setfit-intent-classifier-v1
   ```

2. **Redémarrer le serveur:**
   ```bash
   # Le router détectera automatiquement V4
   # Logs: [SETFIT] Modèle chargé: version=V4
   ```

3. **Vérifier:**
   - `model_version=V4` dans les logs
   - `mode` = GUIDEUR/COMMANDE/RECEPTION_SAV (pas de pôles)
   - `business_subroute` (V4) au lieu de `business_subroute_v5`

---

## 📚 Fichiers Modifiés

### Code
- ✅ `core/universal_corpus.py` : Corpus V5 + mappings
- ✅ `core/sub_routing.py` : Sub-routing V5 (nouveau)
- ✅ `core/setfit_intent_router.py` : Détection version + support V5
- ✅ `scripts/train_setfit_v5.py` : Script d'entraînement (nouveau)

### Modèle
- ✅ `models/setfit-intent-classifier-v1/` : Modèle SetFit V5

### Documentation
- ✅ `docs/SETFIT_V5_DEPLOYMENT.md` : Ce guide

---

## 🎯 Prochaines Étapes

1. **Entraîner le modèle:** `python scripts/train_setfit_v5.py`
2. **Valider:** Router eval + Simulator (58 questions)
3. **Monitorer:** Vérifier logs production pendant 24-48h
4. **Ajuster:** Affiner corpus si nécessaire et ré-entraîner

---

**Contact:** Équipe Zeta AI  
**Dernière mise à jour:** 2025-12-26

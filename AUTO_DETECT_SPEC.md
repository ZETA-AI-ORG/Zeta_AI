# 🎯 SPÉCIFICATION AUTO-DÉTECTION - ORDRE DE COMMANDE

## 📦 1. PRODUIT (Détection via VISION)

### Sources prioritaires
1. **detected_objects** (BLIP-2 caption)
   - Ex: `{'label': 'a bag of sanitary wipes', 'confidence': 0.85}`
2. **vision_objects** (fallback si detected_objects vide)

### Règles de détection
- ✅ Détecter tout objet NON monétaire
- ❌ Exclure si contient: `\d+\s*f`, `fcfa`, montants
- ✅ Si len(description) > 50 chars → tronquer à 50
- ✅ Format sauvegarde: `{description}[VISION]`

### Exemples valides
```
✅ a bag of sanitary wipes[VISION]
✅ red helmet with visor[VISION]
✅ baby diapers pack[VISION]
```

### Exemples invalides (à rejeter)
```
❌ 2020F payment screenshot
❌ wave transaction 2020 fcfa
```

---

## 💰 2. PAIEMENT (Détection via TRANSACTIONS ou VISION)

### Sources prioritaires (ordre)
1. **filtered_transactions** (OCR paiement)
   - Ex: `[{'amount': '2020', 'phone': '0787360757'}]`
2. **vision_objects/detected_objects** contenant montant (fallback)

### Règles de détection
- ✅ Priorité 1: `context.get('filtered_transactions', [])`
- ✅ Si transactions → prendre `first_transaction['amount']`
- ✅ Format sauvegarde: `{montant}F[TRANSACTIONS]`
- ✅ Fallback vision: chercher regex `\d+\s*f` dans objets
- ✅ Format fallback: `{montant}F[VISION]`

### Exemples valides
```
✅ 2020F[TRANSACTIONS]  ← Prioritaire
✅ 2000F[VISION]        ← Fallback si OCR échoue
✅ 10000F[TRANSACTIONS]
```

### Validation obligatoire
- ⚠️ Ne PAS sauvegarder si `filtered_transactions = []`
- ⚠️ Vérifier que `amount` existe dans transaction

---

## 📍 3. ZONE (Détection via MESSAGE texte)

### Source unique
- **message_text** (texte envoyé par l'utilisateur)

### Zones reconnues (liste exhaustive)
```python
zones_centre_1500f = [
    "yopougon", "cocody", "plateau", "adjamé", "abobo", 
    "marcory", "koumassi", "treichville", "angré", "riviera", 
    "andokoua"
]

zones_peripherie_2000f = [
    "port-bouët", "attécoubé"
]

zones_eloignees_2500f = [
    "bingerville", "songon", "anyama", "brofodoumé", 
    "grand-bassam", "dabou"
]
```

### Règles de détection
- ✅ Recherche case-insensitive dans `message_text.lower()`
- ✅ Format sauvegarde: `{Zone}-{Frais}F[MESSAGE]`
- ✅ Mapper automatiquement zone → frais (1500/2000/2500)

### Exemples valides
```
Message: "Yopougon"       → ✅ Yopougon-1500F[MESSAGE]
Message: "Cocody stp"     → ✅ Cocody-1500F[MESSAGE]
Message: "Port-Bouët"     → ✅ Port-Bouët-2000F[MESSAGE]
Message: "Grand-Bassam"   → ✅ Grand-Bassam-2500F[MESSAGE]
```

### Non-détection attendue
```
Message: "Abidjan"        → ❌ Trop générique, ne pas détecter
Message: "zone proche"    → ❌ Pas de zone spécifique
```

---

## 📱 4. NUMÉRO (Détection via MESSAGE texte)

### Source unique
- **message_text** (texte envoyé par l'utilisateur)

### Formats reconnus (4 patterns)
```python
patterns = [
    r'\+225\s?0?([157]\d{8})',           # +2250787360757 ou +225 0787360757
    r'\b(0[157]\d{8})\b',                # 0787360757
    r'\b0([157])\s?(\d{2})\s?(\d{2})\s?(\d{2})\s?(\d{2})\b'  # 07 87 36 07 57
]
```

### Règles de détection
- ✅ Recherche regex dans `message_text`
- ✅ Accepter UNIQUEMENT numéros Côte d'Ivoire (07/05/01)
- ✅ Normaliser au format: `0XXXXXXXXX`
- ✅ Format sauvegarde: `{numero}[MESSAGE]`

### Exemples valides
```
Message: "+2250787360757"    → ✅ 0787360757[MESSAGE]
Message: "0787360757"        → ✅ 0787360757[MESSAGE]
Message: "07 87 36 07 57"    → ✅ 0787360757[MESSAGE]
Message: "Mon num: 05123456" → ✅ 0512345678[MESSAGE]
```

### Exemples invalides (à rejeter)
```
Message: "123456"          → ❌ Trop court
Message: "06 12 34 56 78"  → ❌ Ne commence pas par 07/05/01
Message: "+33612345678"    → ❌ Pas Côte d'Ivoire
```

---

## 🔄 WORKFLOW D'EXÉCUTION

### Ordre d'exécution AUTO-DETECT
```
1. Lire context.keys()
2. Détecter PRODUIT (vision_objects/detected_objects)
3. Détecter PAIEMENT (filtered_transactions prioritaire)
4. Détecter ZONE (message_text)
5. Détecter NUMÉRO (message_text)
6. Sauvegarder chaque détection IMMÉDIATEMENT
```

### Logs DEBUG obligatoires
```python
logger.info(f"🔍 [AUTO-DETECT DEBUG] user_id={user_id}")
logger.info(f"🔍 [AUTO-DETECT DEBUG] vision_objects={vision_objects}")
logger.info(f"🔍 [AUTO-DETECT DEBUG] detected_objects={detected_objects}")
logger.info(f"🔍 [AUTO-DETECT DEBUG] filtered_transactions={filtered_transactions}")
logger.info(f"🔍 [AUTO-DETECT DEBUG] message_text={message_text[:100]}")
logger.info(f"🔍 [AUTO-DETECT DEBUG] context.keys()={list(context.keys())}")
```

---

## ✅ TESTS DE VALIDATION

### Test 1: Produit seul
```python
Input:
- message_image_url: "https://.../lingettes.jpg"
- detected_objects: [{'label': 'a bag of sanitary wipes', 'confidence': 0.85}]

Expected:
✅ PRODUIT: a bag of sanitary wipes[VISION]
❌ PAIEMENT: vide
❌ ZONE: vide
❌ NUMÉRO: vide
Complétion: 25%
```

### Test 2: Produit + Paiement
```python
Input:
- Image 1: produit (lingettes)
- Image 2: paiement (2020F)
- filtered_transactions: [{'amount': '2020', 'phone': '0787360757'}]

Expected:
✅ PRODUIT: a bag of sanitary wipes[VISION]
✅ PAIEMENT: 2020F[TRANSACTIONS]
❌ ZONE: vide
❌ NUMÉRO: vide
Complétion: 50%
```

### Test 3: Produit + Paiement + Zone
```python
Input:
- Image 1: produit
- Image 2: paiement
- Message: "Yopougon"

Expected:
✅ PRODUIT: a bag of sanitary wipes[VISION]
✅ PAIEMENT: 2020F[TRANSACTIONS]
✅ ZONE: Yopougon-1500F[MESSAGE]
❌ NUMÉRO: vide
Complétion: 75%
```

### Test 4: Commande complète
```python
Input:
- Image 1: produit
- Image 2: paiement
- Message: "Yopougon 0709876543"

Expected:
✅ PRODUIT: a bag of sanitary wipes[VISION]
✅ PAIEMENT: 2020F[TRANSACTIONS]
✅ ZONE: Yopougon-1500F[MESSAGE]
✅ NUMÉRO: 0709876543[MESSAGE]
Complétion: 100%
```

---

## 🚨 ERREURS À ÉVITER

### 1. Mélange de champs
```
❌ notepad("append", "✅ZONE:Yopougon[0709876543]")
✅ notepad("append", "✅ZONE:Yopougon-1500F[MESSAGE]")
✅ notepad("append", "✅NUMÉRO:0709876543[MESSAGE]")
```

### 2. Sauvegarde avec valeur vide
```
❌ order_tracker.update_paiement(user_id, "[TRANSACTIONS]")
✅ if filtered_transactions and filtered_transactions[0].get('amount'):
       order_tracker.update_paiement(user_id, f"{amount}F[TRANSACTIONS]")
```

### 3. Source incorrecte
```
❌ Chercher paiement dans detected_objects en priorité
✅ Chercher paiement dans filtered_transactions d'abord
```

### 4. Format incorrect
```
❌ "2020[TRANSACTIONS]"      (manque F)
❌ "2020 FCFA[TRANSACTIONS]" (FCFA superflu)
✅ "2020F[TRANSACTIONS]"     (format correct)
```

---

## 🎯 CRITÈRES DE SUCCÈS

### Auto-détection réussie si:
1. ✅ Logs DEBUG affichent les bonnes sources
2. ✅ Chaque champ est sauvegardé avec bon format
3. ✅ Complétion augmente correctement (25% → 50% → 75% → 100%)
4. ✅ `check_state.py` affiche les bonnes valeurs
5. ✅ Aucune détection en double (même donnée = 1 seule sauvegarde)

### Commande test complète:
```bash
# 1. Message initial
curl -X POST http://127.0.0.1:8002/chat -H 'Content-Type: application/json' \
  -d '{"company_id":"MpfnlSbqwaZ6F4HvxQLRL9du0yG3","user_id":"test_001","message":"Bonsoir"}'

# 2. Image produit
curl -X POST http://127.0.0.1:8002/chat -H 'Content-Type: application/json' \
  -d '{"company_id":"MpfnlSbqwaZ6F4HvxQLRL9du0yG3","user_id":"test_001","message":"","message_image_url":"[URL_PRODUIT]"}'

# 3. Image paiement
curl -X POST http://127.0.0.1:8002/chat -H 'Content-Type: application/json' \
  -d '{"company_id":"MpfnlSbqwaZ6F4HvxQLRL9du0yG3","user_id":"test_001","message":"","message_image_url":"[URL_PAIEMENT]"}'

# 4. Zone + Numéro
curl -X POST http://127.0.0.1:8002/chat -H 'Content-Type: application/json' \
  -d '{"company_id":"MpfnlSbqwaZ6F4HvxQLRL9du0yG3","user_id":"test_001","message":"Yopougon 0709876543"}'

# Vérifier résultat
python3 check_state.py test_001
# Attendu: 100% complétion avec 4 champs ✅
```

# 🎯 Système de Scoring par N-Gram

## 📊 Principe

Le système **priorise les documents** qui contiennent des **phrases complètes** (n-grams longs) plutôt que des mots éparpillés.

---

## 🔢 Échelle de pertinence

### **N-gram de 3+ mots : +5 points** 🌟🌟🌟🌟🌟
**Très pertinent** - Le document contient une phrase exacte de la requête

**Exemple :**
- Query : `"localisation de votre entreprise"`
- Doc contient : `"localisation de votre entreprise"` 
- **Score : +5** ✅

---

### **N-gram de 2 mots : +3 points** 🌟🌟🌟🌟⭐
**Pertinent** - Le document contient une paire de mots de la requête

**Exemple :**
- Query : `"localisation de votre entreprise"`
- Doc contient : `"votre entreprise"` ou `"localisation de"`
- **Score : +3** ✅

---

### **Mot seul : +1 point** 🌟⭐⭐⭐⭐
**Peu pertinent** - Le document ne contient que des mots isolés

**Exemple :**
- Query : `"localisation de votre entreprise"`
- Doc contient : `"entreprise"` (seul)
- **Score : +1** ⚠️

---

## 📈 Exemples concrets

### **Cas 1 : Document ultra-pertinent**

**Query :** `"livraison gratuite à Yopougon"`

**Document A :**
```
Nous offrons la livraison gratuite à Yopougon pour toute commande...
```

**Scoring :**
- N-gram `"livraison gratuite à Yopougon"` (4 mots) : **+5 points**
- **Total : 5/10** 🌟🌟🌟⭐⭐

---

### **Cas 2 : Document moyennement pertinent**

**Query :** `"livraison gratuite à Yopougon"`

**Document B :**
```
La livraison gratuite est disponible dans certaines zones.
Nous desservons Yopougon avec frais de 1500 FCFA.
```

**Scoring :**
- N-gram `"livraison gratuite"` (2 mots) : **+3 points**
- Mot seul `"Yopougon"` : **+1 point**
- **Total : 4/10** 🌟🌟🌟⭐⭐

---

### **Cas 3 : Document peu pertinent**

**Query :** `"livraison gratuite à Yopougon"`

**Document C :**
```
Notre entreprise est située à Abidjan. 
Nous offrons plusieurs services de livraison.
```

**Scoring :**
- Mot seul `"livraison"` : **+1 point**
- **Total : 1/10** 🌟⭐⭐⭐⭐ (ÉLIMINÉ si score < 4)

---

## 🎯 Système de filtrage complet

### **Étape 1 : Scoring**
Chaque document reçoit un score basé sur les n-grams trouvés.

### **Étape 2 : Tri**
Les documents sont triés par **score décroissant**.

### **Étape 3 : Filtrage**
- **Score >= 4/10** : Document retenu ✅
- **Score < 4/10** : Document éliminé ❌

### **Étape 4 : Limite**
Maximum **5 documents** retenus.

---

## 📊 Affichage dans le contexte

### **Avant (sans n-gram scoring) ❌**
```
📊 Mots-clés trouvés: localisation, entreprise
(Pas d'indication de la puissance du match)
```

### **Après (avec n-gram scoring) ✅**
```
📊 Mots-clés trouvés: "localisation de votre", "votre entreprise" (n-gram: 2)
```

**Indication claire :**
- Les guillemets `" "` indiquent un n-gram
- `(n-gram: 2)` indique le nombre de n-grams trouvés

---

## 🔍 Génération des N-grams

### **Fonction : `_generate_ngrams()`**

**Query :** `"livraison gratuite à Yopougon"`

**N-grams générés (ordre décroissant) :**

1. **N=4** : `"livraison gratuite à Yopougon"` (phrase complète)
2. **N=3** : 
   - `"livraison gratuite à"`
   - `"gratuite à Yopougon"`
3. **N=2** :
   - `"livraison gratuite"`
   - `"gratuite à"`
   - `"à Yopougon"`
4. **N=1** :
   - `"livraison"`
   - `"gratuite"`
   - `"à"`
   - `"Yopougon"`

**Priorité** : Les n-grams longs sont testés en PREMIER.

---

## 💡 Avantages du système

### 1. **Précision améliorée**
Les documents avec phrases exactes sont fortement priorisés.

### 2. **Réduction du bruit**
Les documents avec seulement des mots éparpillés sont éliminés.

### 3. **Contexte préservé**
Un n-gram de 3 mots capture le **contexte sémantique**.

### 4. **Performance optimale**
Le tri + filtrage garantit que seuls les meilleurs documents sont passés au LLM.

---

## 📈 Impact sur les résultats

### **Avant (scoring simple) ❌**
```
Doc #1: 7/10 (avec "localisation entreprise")
Doc #2: 1/10 (avec "entreprise" seul)
Doc #3: 1/10 (avec "localisation" seul)
Doc #4: 1/10 (hors sujet)
Doc #5: 1/10 (hors sujet)
```
**Problème** : Beaucoup de bruit (docs 1/10).

---

### **Après (scoring n-gram) ✅**
```
Doc #1: 8/10 (n-gram "localisation de l'entreprise" + mots)
Doc #2: 6/10 (n-gram "votre entreprise" + mots)
Doc #3: 5/10 (n-gram "localisation" + contexte)
(Les docs 1/10 sont éliminés automatiquement)
```
**Bénéfice** : Seulement les documents pertinents sont conservés.

---

## 🎓 Cas d'usage

### **E-commerce couches bébé**

**Query :** `"couches taille 3 prix"`

**Document pertinent (score 8/10) :**
```
Couches taille 3 : 20 500 FCFA
Lot de 100 couches à pression
```
- N-gram `"couches taille 3"` : +5 points
- Mot `"prix"` (implicite via montant) : +3 points
- **Total : 8/10** 🌟🌟🌟🌟🌟

**Document non pertinent (score 2/10) :**
```
Nos produits incluent diverses tailles.
Les prix varient selon le lot.
```
- Mot `"tailles"` : +1 point
- Mot `"prix"` : +1 point
- **Total : 2/10** 🌟⭐⭐⭐⭐ (ÉLIMINÉ)

---

## 🚀 Configuration

### **Paramètres ajustables**

```python
# Dans _calculate_keyword_score()
NGRAM_3_PLUS_SCORE = 5  # Score pour n-gram de 3+ mots
NGRAM_2_SCORE = 3       # Score pour n-gram de 2 mots
SINGLE_WORD_SCORE = 1   # Score pour mot seul
MAX_SCORE = 10          # Score maximum

# Dans _format_meili_context()
MIN_SCORE_THRESHOLD = 4  # Seuil minimum pour retenir un document
MAX_DOCS = 5             # Nombre max de documents affichés
```

---

## 📊 Logs de debug

Le système affiche des logs pour suivre le scoring :

```
📊 [FILTRAGE] 12 docs → 3 retenus (score >= 4/10)

🌟🌟🌟🌟⭐ INFORMATION MEILISEARCH #1 (Score: 8/10)
📊 Mots-clés trouvés: "couches taille 3", prix (n-gram: 1)

🌟🌟🌟🌟⭐ INFORMATION MEILISEARCH #2 (Score: 6/10)
📊 Mots-clés trouvés: "taille 3", couches, prix (n-gram: 1)

🌟🌟🌟⭐⭐ INFORMATION MEILISEARCH #3 (Score: 5/10)
📊 Mots-clés trouvés: taille, couches, prix
```

---

## ✅ Résumé

Le système de scoring par n-gram :

1. ✅ **Priorise** les phrases exactes (n-gram long)
2. ✅ **Évalue** chaque document sur une échelle 1-10
3. ✅ **Trie** les documents par pertinence
4. ✅ **Filtre** pour éliminer le bruit (score < 4)
5. ✅ **Affiche** les meilleurs documents au LLM

**Résultat** : Réponses plus précises, moins d'hallucinations, meilleure confiance.

# 📋 PIPELINE MEILISEARCH COMPLET - DE LA QUERY AU LLM

## 🎯 FLUX GLOBAL
```
Query Utilisateur
    ↓
[1] Filtrage Stop Words
    ↓
[2] Génération N-grams
    ↓
[3] Recherche MeiliSearch Parallèle
    ↓
[4] Déduplication Documents
    ↓
[5] Scoring Smart V2
    ↓
[6] Boost N-gram ID
    ↓
[7] Boost Company Keywords
    ↓
[8] Filtrage Dynamique
    ↓
[9] Extraction Contexte
    ↓
[10] Filtrage par Seuil
    ↓
[11] Limitation Documents
    ↓
[12] Formatage Final
    ↓
Envoi au LLM
```

---

## [1] FILTRAGE STOP WORDS

**Fichier**: `vector_store_clean_v2.py` (ligne 286-292)  
**Fonction**: `filter_query_for_meilisearch()` (importée de `core.smart_stopwords`)

### Paramètres:
- **Input**: Query originale
- **Output**: Query filtrée (stop words retirés)
- **Stop words**: 800+ mots (salutations, pronoms, articles, etc.)

### Exemple:
```
Input:  "bonjour je veux la taille 5"
Output: "veux taille 5"
```

---

## [2] GÉNÉRATION N-GRAMS

**Fichier**: `vector_store_clean_v2.py` (ligne 114-178)  
**Fonction**: `_generate_ngrams(query, max_n=3, min_n=1)`

### Paramètres:
- **max_n**: 3 (n-grams jusqu'à 3 mots)
- **min_n**: 1 (n-grams d'au moins 1 mot)
- **Filtrage stop words**: OUI (ligne 118)
- **Mots de liaison autorisés**: {"à", "a", "á", "â", "ä", "ã", "å"} (uniquement dans n-grams de 3 mots au milieu)

### Règles de génération:
1. **N-grams consécutifs** (1, 2, 3 mots)
2. **Combinaisons non-consécutives** (paires de 2 mots)
3. **Filtrage strict**:
   - ❌ Chiffres isolés (ex: "5")
   - ❌ Lettres isolées (ex: "a")
   - ❌ N-grams identiques (ex: "taille taille")
   - ❌ N-grams uniquement numériques (ex: "2 3")

### Exemple:
```
Query filtrée: "veux taille 5"
N-grams générés:
  1. veux taille 5      (n-gram 3)
  2. veux taille        (n-gram 2)
  3. taille 5           (n-gram 2) ✅ IMPORTANT!
  4. veux               (n-gram 1)
  5. taille             (n-gram 1)
  6. veux 5             (combinaison non-consécutive)
```

**⚠️ PROBLÈME IDENTIFIÉ**: Le "5" isolé est filtré (ligne 166), mais "taille 5" est conservé ✅

---

## [3] RECHERCHE MEILISEARCH PARALLÈLE

**Fichier**: `vector_store_clean_v2.py` (ligne 311-332)  
**Fonction**: `search_single(ngram, index_name)`

### Paramètres:
- **Index recherchés**: 
  - `products_{company_id}`
  - `delivery_{company_id}`
  - `support_paiement_{company_id}`
  - `localisation_{company_id}`
- **Limite par recherche**: 5 documents
- **Champs récupérés**: `['content', 'id', 'type', 'searchable_text']`
- **Parallélisation**: ThreadPoolExecutor avec 15 workers max
- **Nombre total de tâches**: `len(ngrams) × len(indexes)` (ex: 6 n-grams × 4 index = 24 recherches)

### Exemple:
```
N-gram "taille 5" → Recherche dans 4 index
  → products_rue_du_gros: 5 hits
  → delivery_rue_du_gros: 0 hits
  → support_paiement_rue_du_gros: 0 hits
  → localisation_rue_du_gros: 0 hits
```

---

## [4] DÉDUPLICATION DOCUMENTS

**Fichier**: `vector_store_clean_v2.py` (ligne 334-354)

### Paramètres:
- **Champ prioritaire**: `searchable_text` si plus long que `content`
- **Longueur minimale**: 30 caractères
- **Déduplication**: Par contenu exact (set `seen_contents`)

### Logique:
```python
if len(searchable_text) > len(content):
    content = searchable_text
else:
    content = content or searchable_text

if content and len(content) > 30 and content not in seen_contents:
    # Document ajouté
```

---

## [5] SCORING SMART V2

**Fichier**: `vector_store_clean_v2.py` (ligne 193-263)  
**Fonction**: `_calculate_smart_score_v2(content, query, all_corpus)`

### Paramètres de scoring:

#### A. Constants:
- **BONUS_EXACT**: 5 points par mot du n-gram
- **BONUS_FUZZY**: 0.5 points par mot du n-gram
- **Seuil fuzzy**: ratio ≥ 90%

#### B. Normalisation:
```python
def _normalize(text):
    return unidecode(text.lower().strip())
```
- **Minuscules**: OUI ✅
- **Suppression accents**: OUI (via unidecode)
- **Trim espaces**: OUI

#### C. Génération n-grams internes (pour scoring):
```python
for n in range(1, 4):  # n-grams de 1 à 3 mots
    ngrams += [' '.join(query_words[i:i+n]) for i in range(len(query_words)-n+1)]
```

#### D. Calcul du score:
```python
content_normalized = _normalize(content)
doc_id_normalized = _normalize(doc_id)

for ng in ngrams:
    n = len(ng.split())  # Nombre de mots dans le n-gram
    
    # Match exact (case-insensitive)
    if ng in content_normalized or (doc_id_normalized and ng in doc_id_normalized):
        score += BONUS_EXACT * n  # 5 × n
    else:
        # Fuzzy match (ratio >= 90)
        for doc_word in doc_words:
            if fuzz.ratio(ng, doc_word) >= 90:
                score += BONUS_FUZZY * n  # 0.5 × n
                break
```

### Exemples de scoring:

#### Exemple 1: "taille 5" (n-gram 2 mots)
```
Document: "Taille 5 (12-17kg): 25.900 FCFA"

N-grams générés du query "veux taille 5":
  - "veux taille 5" (3 mots) → pas dans doc → 0 points
  - "veux taille" (2 mots) → pas dans doc → 0 points
  - "taille 5" (2 mots) → ✅ MATCH EXACT → 5 × 2 = 10 points
  - "veux" (1 mot) → pas dans doc → 0 points
  - "taille" (1 mot) → ✅ MATCH EXACT → 5 × 1 = 5 points
  - "veux 5" (2 mots) → pas dans doc → 0 points

Score total: 10 + 5 = 15 points ✅
```

#### Exemple 2: "Taille 1" (autre taille)
```
Document: "Taille 1 (0-4kg): 17.900 FCFA"

N-grams:
  - "veux taille 5" → pas dans doc → 0 points
  - "veux taille" → pas dans doc → 0 points
  - "taille 5" → pas dans doc (c'est "taille 1") → 0 points
  - "veux" → pas dans doc → 0 points
  - "taille" → ✅ MATCH EXACT → 5 × 1 = 5 points
  - "veux 5" → pas dans doc → 0 points

Score total: 5 points
```

**✅ CONCLUSION**: Le n-gram "taille 5" (2 mots) donne 10 points, tandis que "taille" seul (1 mot) donne 5 points. Le document avec "Taille 5" aura un score 3× supérieur (15 vs 5).

---

## [6] BOOST N-GRAM ID

**Fichier**: `vector_store_clean_v2.py` (ligne 412-423)

### Paramètres:
- **Bonus par n-gram trouvé dans l'ID**: +10 points
- **Normalisation**: Suppression des espaces pour comparaison

### Logique:
```python
doc_id = str(doc.get('hit', {}).get('id', '')).lower()
for ng in ngrams:
    ng_norm = ng.lower().replace(' ', '')
    if ng_norm and doc_id and ng_norm in doc_id.replace(' ', ''):
        ngram_bonus += 10
```

### Exemple:
```
Document ID: "taille5_pression"
N-gram: "taille 5"
  → ng_norm = "taille5"
  → doc_id = "taille5_pression"
  → ✅ MATCH → +10 points
```

---

## [7] BOOST COMPANY KEYWORDS

**Fichier**: `vector_store_clean_v2.py` (ligne 427-454)  
**Fonction**: `get_company_boosters(company_id)`

### Paramètres:
- **Boost par keyword**: +2 points
- **Maximum boost**: +5 points
- **Type**: Additif (pas multiplicatif)

### Logique:
```python
boosters_keywords = boosters.get('keywords', [])

for doc in scored_documents:
    content_lower = doc['content'].lower()
    boost = 0
    
    for keyword in boosters_keywords:
        if keyword in query_lower and keyword in content_lower:
            boost += 2
    
    if boost > 0:
        doc['score'] += min(boost, 5)  # Max +5 points
```

---

## [8] FILTRAGE DYNAMIQUE

**Fichier**: `vector_store_clean_v2.py` (ligne 456-476)  
**Fonction**: `filter_by_dynamic_threshold()` (importée de `core.smart_metadata_extractor`)

### Paramètres:
- **Input**: Documents avec scores
- **Output**: Documents filtrés selon seuil dynamique
- **Logique**: Calcul automatique du seuil basé sur la distribution des scores

---

## [9] EXTRACTION CONTEXTE

**Fichier**: `vector_store_clean_v2.py` (ligne 478-502)  
**Fonction**: `extract_relevant_context()` (importée de `core.context_extractor`)

### Paramètres:
- **Intentions détectées**: Via `detect_query_intentions(query)`
- **Réduction du contenu**: Extraction des parties pertinentes uniquement

---

## [10] FILTRAGE PAR SEUIL

**Fichier**: `vector_store_clean_v2.py` (ligne 504-508)

### Paramètres:
- **threshold**: 4 points (score minimum pour documents "high score")
- **min_score**: 1 point (score minimum absolu)

### Logique:
```python
filtered_docs = [d for d in scored_documents if d['score'] >= min_score]
high_score_docs = [d for d in filtered_docs if d['score'] >= threshold]
```

---

## [11] LIMITATION DOCUMENTS

**Fichier**: `vector_store_clean_v2.py` (ligne 509-520)

### Paramètres:
- **max_docs**: 3 documents par index
- **Regroupement**: Par `source_index`
- **Tri**: Par score décroissant

### Logique:
```python
docs_by_index = defaultdict(list)
for doc in high_score_docs:
    docs_by_index[doc.get('source_index','?')].append(doc)

scored_documents = []
for idx, docs in docs_by_index.items():
    scored_documents.extend(sorted(docs, key=lambda x: x['score'], reverse=True)[:max_docs])

scored_documents.sort(key=lambda x: x['score'], reverse=True)
```

**⚠️ LIMITATION CRITIQUE**: Maximum 3 documents par index, même si 10 documents ont un score parfait!

---

## [12] FORMATAGE FINAL

**Fichier**: `vector_store_clean_v2.py` (ligne 521-567)

### Format envoyé au LLM:
```
DOCUMENT #1 (Score: 15.00)
Index de provenance: products_rue_du_gros
N-grams trouvés: ['taille 5', 'taille']
Taille 5 (12-17kg): 25.900 FCFA

DOCUMENT #2 (Score: 10.00)
Index de provenance: products_rue_du_gros
N-grams trouvés: ['taille']
Taille 1 (0-4kg): 17.900 FCFA
```

---

## 🔥 RÉSUMÉ DES PARAMÈTRES CRITIQUES

### Génération N-grams:
- ✅ **max_n**: 3 mots
- ✅ **min_n**: 1 mot
- ✅ **Filtrage stop words**: OUI
- ❌ **Problème**: Chiffres isolés filtrés (mais "taille 5" conservé)

### Scoring:
- ✅ **BONUS_EXACT**: 5 points × nb_mots_ngram
- ✅ **BONUS_FUZZY**: 0.5 points × nb_mots_ngram
- ✅ **Normalisation**: Case-insensitive + sans accents
- ✅ **N-gram 3 mots > N-gram 2 mots > N-gram 1 mot**: OUI (15 > 10 > 5)

### Filtrage:
- ⚠️ **threshold**: 4 points (peut éliminer des matches partiels)
- ⚠️ **min_score**: 1 point
- ❌ **max_docs**: 3 par index (LIMITATION CRITIQUE)

### Boosts:
- ✅ **N-gram dans ID**: +10 points
- ✅ **Company keywords**: +2 à +5 points (additif)

---

## 🎯 VÉRIFICATION: "taille 5" vs "Taille 5"

### Query: "veux taille 5"
### Document: "Taille 5 (12-17kg): 25.900 FCFA"

**Étape 1**: Filtrage stop words
```
"veux taille 5" → "veux taille 5" (aucun stop word)
```

**Étape 2**: N-grams générés
```
1. veux taille 5
2. veux taille
3. taille 5      ← IMPORTANT
4. veux
5. taille
6. veux 5
```

**Étape 3**: Scoring
```
content_normalized = "taille 5 (12-17kg): 25.900 fcfa"
query_ngrams = ["veux taille 5", "veux taille", "taille 5", "veux", "taille", "veux 5"]

Vérification "taille 5" (2 mots):
  → "taille 5" in "taille 5 (12-17kg): 25.900 fcfa" → ✅ TRUE
  → score += 5 × 2 = 10 points

Vérification "taille" (1 mot):
  → "taille" in "taille 5 (12-17kg): 25.900 fcfa" → ✅ TRUE
  → score += 5 × 1 = 5 points

Score total: 15 points ✅
```

**✅ CONFIRMATION**: Le système fonctionne correctement pour les matches exacts case-insensitive!

---

## ⚠️ PROBLÈMES IDENTIFIÉS

### 1. Limitation max_docs = 3
- **Impact**: Si 10 documents ont "taille 5" avec score 15, seuls 3 seront envoyés au LLM
- **Solution proposée**: Augmenter à 10 (mais vous avez refusé)

### 2. Filtrage chiffres isolés
- **Impact**: Le "5" seul est filtré des n-grams
- **Contournement**: "taille 5" (2 mots) est conservé ✅

### 3. Threshold = 4
- **Impact**: Documents avec score < 4 sont éliminés
- **Exemple**: Un document avec seulement "taille" (5 points) passe, mais un avec fuzzy match (0.5 points) est éliminé

---

## 📊 TABLEAU RÉCAPITULATIF DES SCORES

| N-gram | Nb mots | Match exact | Match fuzzy | Score |
|--------|---------|-------------|-------------|-------|
| "veux taille 5" | 3 | 5 × 3 = 15 | 0.5 × 3 = 1.5 | 15 ou 1.5 |
| "taille 5" | 2 | 5 × 2 = 10 | 0.5 × 2 = 1.0 | 10 ou 1.0 |
| "taille" | 1 | 5 × 1 = 5 | 0.5 × 1 = 0.5 | 5 ou 0.5 |

**✅ HIÉRARCHIE RESPECTÉE**: N-gram 3 > N-gram 2 > N-gram 1

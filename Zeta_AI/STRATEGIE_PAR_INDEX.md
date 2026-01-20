# 🎯 STRATÉGIE MAX 3 PAR INDEX

## 💡 POURQUOI CETTE APPROCHE ?

### **Gestion automatique des intentions multiples**

**Exemple de requête complexe :**
```
"Combien coûtent les couches taille 3 et vous livrez à Yopougon ?"
```

**2 intentions détectées :**
1. Prix des couches (→ index `products`)
2. Livraison à Yopougon (→ index `delivery`)

---

## 📊 PROCESSUS DÉTAILLÉ

### **ÉTAPE 1-3: Recherche parallèle (inchangée)**
```
Recherche dans tous les index avec tous les n-grams
```

### **ÉTAPE 4: Groupement par index**
```
products_xxx:
  - Doc A: Score 8/10
  - Doc B: Score 7/10
  - Doc C: Score 5/10
  - Doc D: Score 3/10
  - Doc E: Score 2/10

delivery_xxx:
  - Doc F: Score 7/10
  - Doc G: Score 6/10
  - Doc H: Score 4/10
  - Doc I: Score 2/10

localisation_xxx:
  - Doc J: Score 3/10
  - Doc K: Score 1/10

support_paiement_xxx:
  - Doc L: Score 2/10

company_docs_xxx:
  - Doc M: Score 6/10
  - Doc N: Score 5/10
```

### **ÉTAPE 5: Filtrage - MAX 3 PAR INDEX**

```
Pour chaque index:
  1. Trier par score décroissant
  2. Garder les 3 meilleurs
  3. Filtrer score >= 4
  4. Si aucun >= 4, garder au moins le meilleur

Résultats:

products_xxx (5 docs → 3 retenus):
  ✅ Doc A: 8/10
  ✅ Doc B: 7/10
  ✅ Doc C: 5/10
  ❌ Doc D: 3/10 (hors top 3)
  ❌ Doc E: 2/10 (hors top 3)

delivery_xxx (4 docs → 3 retenus):
  ✅ Doc F: 7/10
  ✅ Doc G: 6/10
  ✅ Doc H: 4/10
  ❌ Doc I: 2/10 (hors top 3)

localisation_xxx (2 docs → 0 retenus):
  ❌ Doc J: 3/10 (score < 4)
  ❌ Doc K: 1/10 (score < 4)

support_paiement_xxx (1 doc → 0 retenus):
  ❌ Doc L: 2/10 (score < 4)

company_docs_xxx (2 docs → 2 retenus):
  ✅ Doc M: 6/10
  ✅ Doc N: 5/10

TOTAL: 8 documents retenus (3+3+0+0+2)
```

### **ÉTAPE 6: Élimination des doublons**

```
Avant déduplication: 8 docs
Après déduplication: 7 docs (1 doublon éliminé)
```

### **ÉTAPE 7: Tri final global**

```
Tri par score tous index confondus:

1. Doc A (products): 8/10
2. Doc B (products): 7/10
3. Doc F (delivery): 7/10
4. Doc M (company_docs): 6/10
5. Doc G (delivery): 6/10
6. Doc C (products): 5/10
7. Doc N (company_docs): 5/10
```

---

## 🎯 AVANTAGES DE CETTE APPROCHE

### **1. Gestion intentions multiples AUTOMATIQUE**

**Requête :** `"Prix couches + livraison Yopougon + paiement Wave"`

**Résultat :**
- 3 docs de `products` (prix)
- 3 docs de `delivery` (livraison)
- 3 docs de `support_paiement` (paiement)

**= 9 documents couvrant les 3 intentions !**

---

### **2. Équité entre index**

**Avant (top 3 global) ❌ :**
```
Si products très pertinent, il "vole" les 3 places
→ delivery et autres exclus même s'ils sont pertinents
```

**Après (top 3 par index) ✅ :**
```
Chaque index a sa chance de contribuer
→ Contexte plus riche pour le LLM
```

---

### **3. Qualité par domaine**

Chaque index représente un domaine métier :
- `products` → Catalogue
- `delivery` → Livraison
- `localisation` → Adresses
- `support_paiement` → Paiement
- `company_docs` → Général

**→ On garde les meilleurs de CHAQUE domaine**

---

## 📊 EXEMPLES CONCRETS

### **Exemple 1 : Requête simple (1 intention)**

**Query :** `"combien coûte les couches taille 3 ?"`

**Résultat :**
```
products_xxx: 3 docs retenus
delivery_xxx: 0 docs (pas pertinents)
localisation_xxx: 0 docs
support_paiement_xxx: 0 docs
company_docs_xxx: 1 doc retenu

Total: 4 docs pour le LLM
```

**Impact :** Contexte riche même pour requête simple.

---

### **Exemple 2 : Requête double intention**

**Query :** `"couches taille 3 + livraison Yopougon ?"`

**Résultat :**
```
products_xxx: 3 docs (info couches)
delivery_xxx: 3 docs (info Yopougon)
localisation_xxx: 0 docs
support_paiement_xxx: 0 docs
company_docs_xxx: 2 docs (général)

Total: 8 docs pour le LLM
```

**Impact :** Le LLM peut répondre aux 2 intentions.

---

### **Exemple 3 : Requête triple intention**

**Query :** `"couches, livraison et paiement Wave ?"`

**Résultat :**
```
products_xxx: 3 docs (couches)
delivery_xxx: 3 docs (livraison)
localisation_xxx: 0 docs
support_paiement_xxx: 3 docs (Wave)
company_docs_xxx: 2 docs (général)

Total: 11 docs pour le LLM
```

**Impact :** Toutes les intentions couvertes dans une seule réponse !

---

## 🔄 FLUX COMPLET

```
┌─────────────────────────────────────────────────────────────┐
│  RECHERCHE PARALLÈLE                                        │
│  Tous index × Tous n-grams                                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  GROUPEMENT PAR INDEX                                       │
│                                                             │
│  products_xxx: [Doc A, Doc B, Doc C, Doc D, Doc E]         │
│  delivery_xxx: [Doc F, Doc G, Doc H, Doc I]                │
│  localisation_xxx: [Doc J, Doc K]                          │
│  support_paiement_xxx: [Doc L]                             │
│  company_docs_xxx: [Doc M, Doc N]                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  FILTRAGE PAR INDEX (MAX 3 PAR INDEX)                       │
│                                                             │
│  products_xxx: [Doc A, Doc B, Doc C] ✅                     │
│  delivery_xxx: [Doc F, Doc G, Doc H] ✅                     │
│  localisation_xxx: [] ❌ (score trop bas)                   │
│  support_paiement_xxx: [] ❌ (score trop bas)               │
│  company_docs_xxx: [Doc M, Doc N] ✅                        │
│                                                             │
│  Total: 8 documents                                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  DÉDUPLICATION                                              │
│                                                             │
│  8 docs → 7 docs (1 doublon éliminé)                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  TRI FINAL GLOBAL                                           │
│                                                             │
│  Par score décroissant tous index confondus:               │
│  1. Doc A (products): 8/10                                 │
│  2. Doc B (products): 7/10                                 │
│  3. Doc F (delivery): 7/10                                 │
│  4. Doc M (company_docs): 6/10                             │
│  5. Doc G (delivery): 6/10                                 │
│  6. Doc C (products): 5/10                                 │
│  7. Doc N (company_docs): 5/10                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  CONTEXTE LLM                                               │
│                                                             │
│  7 documents couvrant plusieurs intentions                 │
│  Qualité garantie (score >= 4 par index)                   │
│  Pas de doublons                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📈 CAPACITÉ MAXIMALE

**Cas extrême :** Tous les index retournent 3 docs pertinents

```
products: 3 docs
delivery: 3 docs
localisation: 3 docs
support_paiement: 3 docs
company_docs: 3 docs

Total MAX: 15 documents (avant déduplication)
```

**En pratique :** 5-10 documents selon la requête

---

## ✅ GARANTIES

| Garantie | Description |
|----------|-------------|
| Max 3 par index | Chaque index contribue au maximum 3 documents |
| Score >= 4 | Seuls les documents pertinents sont gardés |
| Déduplication | Contenu unique garanti |
| Intentions multiples | Gérées automatiquement sans effort |
| Tri final | Meilleurs documents en premier |

---

## 🎯 RÉSUMÉ

**Cette stratégie permet de :**
- ✅ Gérer les intentions multiples automatiquement
- ✅ Garantir la diversité du contexte (plusieurs index)
- ✅ Maintenir la qualité (score >= 4)
- ✅ Éliminer les doublons
- ✅ Optimiser pour le LLM (5-10 docs pertinents)

**Sans effort supplémentaire du LLM !** 🚀

# 🔄 INDEX COMPANY_DOCS EN FALLBACK

## 🎯 STRATÉGIE

**`company_docs` n'est PAS recherché en premier.**  
**Il sert uniquement de FALLBACK si les 4 index principaux retournent 0 résultat.**

---

## 📊 PROCESSUS

### **ÉTAPE 1-6: Recherche dans les index PRINCIPAUX**

```
INDEX PRINCIPAUX (recherche prioritaire):
  1. products_{company_id}
  2. delivery_{company_id}
  3. localisation_{company_id}
  4. support_paiement_{company_id}

Recherche parallèle → Groupement → Filtrage → Déduplication
```

### **ÉTAPE 7: VÉRIFICATION**

```
IF unique_docs > 0:
  ✅ Documents trouvés → Pas de fallback
  
ELSE:
  🔄 Aucun document → FALLBACK vers company_docs
```

### **ÉTAPE 8 (FALLBACK): Recherche dans company_docs**

```
Recherche dans company_docs_{company_id}
  - Avec tous les n-grams
  - Scoring identique
  - Seuil abaissé: score >= 3 (au lieu de 4)
  - Max 3 documents
```

---

## 🎯 EXEMPLES

### **Cas 1 : Résultats trouvés dans index principaux**

**Query:** `"combien coûte les couches taille 3 ?"`

```
RECHERCHE INDEX PRINCIPAUX:
  products: 3 docs trouvés ✅
  delivery: 0 docs
  localisation: 0 docs
  support_paiement: 0 docs

RÉSULTAT: 3 documents

FALLBACK: ❌ Pas nécessaire (résultats trouvés)
```

**company_docs n'est PAS interrogé.**

---

### **Cas 2 : Aucun résultat dans index principaux**

**Query:** `"quelles sont vos valeurs d'entreprise ?"`

```
RECHERCHE INDEX PRINCIPAUX:
  products: 0 docs ❌
  delivery: 0 docs ❌
  localisation: 0 docs ❌
  support_paiement: 0 docs ❌

RÉSULTAT: 0 documents

FALLBACK: ✅ Activé → Recherche dans company_docs

RECHERCHE FALLBACK:
  company_docs: 3 docs trouvés ✅
  
RÉSULTAT FINAL: 3 documents de company_docs
```

**company_docs est utilisé comme dernier recours.**

---

### **Cas 3 : Requête hors-sujet**

**Query:** `"vendez-vous des smartphones ?"`

```
RECHERCHE INDEX PRINCIPAUX:
  products: 0 docs (pas de smartphones) ❌
  delivery: 0 docs ❌
  localisation: 0 docs ❌
  support_paiement: 0 docs ❌

RÉSULTAT: 0 documents

FALLBACK: ✅ Activé → Recherche dans company_docs

RECHERCHE FALLBACK:
  company_docs: 0 docs ❌ (pas de smartphones non plus)
  
RÉSULTAT FINAL: 0 documents

→ LLM génère réponse "Je ne vends pas de smartphones"
```

---

## 📈 FLUX COMPLET

```
┌─────────────────────────────────────────────────────────────┐
│  RECHERCHE INDEX PRINCIPAUX (4 index)                       │
│  • products                                                 │
│  • delivery                                                 │
│  • localisation                                             │
│  • support_paiement                                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
                    ┌─────────┐
                    │ Docs > 0? │
                    └─────────┘
                    ↙         ↘
              OUI ✅          NON ❌
                ↓                ↓
┌──────────────────────┐   ┌──────────────────────┐
│  RÉSULTAT DIRECT     │   │  FALLBACK ACTIVÉ     │
│  Pas de fallback     │   │  Recherche company   │
│                      │   │  _docs               │
└──────────────────────┘   └──────────────────────┘
                                     ↓
                          ┌─────────────────────┐
                          │  SCORING FALLBACK   │
                          │  Seuil: score >= 3  │
                          │  Max: 3 documents   │
                          └─────────────────────┘
                                     ↓
                          ┌─────────────────────┐
                          │  CONTEXTE LLM       │
                          └─────────────────────┘
```

---

## 🎯 AVANTAGES

### **1. Performance optimisée**
```
Si résultats trouvés dans index principaux (95% des cas):
  → company_docs n'est PAS interrogé
  → Économie de temps et ressources
```

### **2. Hiérarchie claire**
```
PRIORITÉ 1: Index spécialisés (products, delivery, etc.)
PRIORITÉ 2: Index généraliste (company_docs) en dernier recours
```

### **3. Pertinence maximale**
```
Les index spécialisés sont plus pertinents pour leur domaine
company_docs ne "pollue" pas les résultats
```

### **4. Filet de sécurité**
```
Si rien trouvé dans les index spécialisés:
  → company_docs rattrape avec infos générales
  → Évite les réponses "Je ne sais pas"
```

---

## 📊 STATISTIQUES ATTENDUES

### **Répartition des requêtes:**

```
85% : Résultats dans products
5%  : Résultats dans delivery/localisation/support
10% : FALLBACK vers company_docs
```

**→ company_docs n'est interrogé que 10% du temps**

---

## ⚙️ PARAMÈTRES FALLBACK

### **Seuil de score abaissé**
```
Index principaux: score >= 4
company_docs:     score >= 3  ← Plus permissif
```

**Raison:** Si on est en fallback, c'est qu'on n'a rien trouvé ailleurs. On accepte des documents légèrement moins pertinents.

### **Limite identique**
```
Max 3 documents (comme pour les index principaux)
```

---

## 🔍 LOGS DE DEBUG

### **Cas avec résultats principaux:**
```
📂 Index principaux à explorer: 4
   • products_xxx
   • delivery_xxx
   • localisation_xxx
   • support_paiement_xxx

🔄 Index fallback: company_docs_xxx (si 0 résultat)

...

✅ [PRINCIPAL] 3 documents trouvés → Pas de fallback nécessaire
```

### **Cas avec fallback:**
```
📂 Index principaux à explorer: 4
   • products_xxx
   • delivery_xxx
   • localisation_xxx
   • support_paiement_xxx

🔄 Index fallback: company_docs_xxx (si 0 résultat)

...

📊 [FILTRAGE FINAL] 0 docs après déduplication

🔄 [FALLBACK] Aucun résultat des index principaux → Recherche dans company_docs_xxx
⚡ Tâches fallback: 12
📄 Documents fallback collectés: 5
✅ [FALLBACK] 3 documents retenus de company_docs_xxx
```

---

## ✅ GARANTIES

| Garantie | Description |
|----------|-------------|
| Index principaux d'abord | products, delivery, localisation, support_paiement |
| Fallback conditionnel | company_docs SEULEMENT si 0 résultat |
| Seuil adapté | score >= 3 pour fallback (vs >= 4 pour principaux) |
| Pas de doublon | company_docs n'est jamais interrogé si résultats trouvés |
| Performance optimale | 90% des requêtes évitent le fallback |

---

## 🎯 RÉSUMÉ

**company_docs est le "plan B" :**
- ❌ Pas recherché par défaut
- ✅ Activé seulement si 0 résultat des index principaux
- ✅ Seuil de score abaissé (plus permissif)
- ✅ Max 3 documents
- ✅ Économise des ressources (90% des cas)

**Hiérarchie intelligente : Spécialisé d'abord, Généraliste ensuite.** 🎯

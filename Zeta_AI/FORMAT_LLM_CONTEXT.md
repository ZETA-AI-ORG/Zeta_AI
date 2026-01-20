# 📝 FORMAT CLAIR POUR LE LLM

## 🎯 OBJECTIF

**Format structuré et explicite** pour éviter les hallucinations du LLM.

Le LLM doit comprendre immédiatement :
- 🏷️ **Quelle catégorie** d'information
- 📂 **Quel index source**
- 📊 **Combien de documents** disponibles

---

## 📋 FORMAT STANDARD

```
POUR (catégorie) - Index: index_name - Document X/Y :
[CONTENU DU DOCUMENT]

POUR (catégorie) - Index: index_name - Document X/Y :
[CONTENU DU DOCUMENT]
```

---

## 🎯 CATÉGORIES

| Index | Catégorie affichée |
|-------|-------------------|
| `products_{company_id}` | **produits** |
| `delivery_{company_id}` | **livraison** |
| `localisation_{company_id}` | **localisation** |
| `support_paiement_{company_id}` | **paiement et support** |
| `company_docs_{company_id}` | **informations générales** |

---

## 📊 EXEMPLES CONCRETS

### **Exemple 1 : Une seule catégorie, plusieurs documents**

**Query :** `"combien coûte les couches taille 3 ?"`

**Contexte LLM :**
```
POUR (produits) - Index: products_MpfnlSbqwaZ6F4HvxQLRL9du0yG3 - Document 1/3 :
Couches bébé taille 3 : 20 500 FCFA
Lot de 100 couches à pression
Stock disponible : 50 unités

POUR (produits) - Index: products_MpfnlSbqwaZ6F4HvxQLRL9du0yG3 - Document 2/3 :
Couches taille 3 - Absorption maximale
Prix : 20 500 FCFA par lot
Livraison disponible dans toutes les zones

POUR (produits) - Index: products_MpfnlSbqwaZ6F4HvxQLRL9du0yG3 - Document 3/3 :
Taille 3 (4-9 kg)
Prix unitaire : 205 FCFA
Lot de 100 : 20 500 FCFA
```

**Clarté pour le LLM :**
- ✅ Sait que ce sont des infos **produits**
- ✅ Voit qu'il y a **3 documents** disponibles
- ✅ Peut combiner les informations

---

### **Exemple 2 : Plusieurs catégories (intentions multiples)**

**Query :** `"couches taille 3 + livraison Yopougon ?"`

**Contexte LLM :**
```
POUR (produits) - Index: products_MpfnlSbqwaZ6F4HvxQLRL9du0yG3 - Document 1/3 :
Couches bébé taille 3 : 20 500 FCFA
Lot de 100 couches à pression
Stock disponible : 50 unités

POUR (produits) - Index: products_MpfnlSbqwaZ6F4HvxQLRL9du0yG3 - Document 2/3 :
Couches taille 3 - Absorption maximale
Prix : 20 500 FCFA par lot

POUR (produits) - Index: products_MpfnlSbqwaZ6F4HvxQLRL9du0yG3 - Document 3/3 :
Taille 3 (4-9 kg)
Prix unitaire : 205 FCFA

POUR (livraison) - Index: delivery_MpfnlSbqwaZ6F4HvxQLRL9du0yG3 - Document 1/2 :
Zone : Yopougon (toutes les communes)
Frais de livraison : 1 500 FCFA
Délai : 24-48h
Livraison gratuite à partir de 50 000 FCFA

POUR (livraison) - Index: delivery_MpfnlSbqwaZ6F4HvxQLRL9du0yG3 - Document 2/2 :
Zones couvertes à Yopougon :
- Yopougon Niangon
- Yopougon Selmer
- Yopougon Sideci
Frais : 1 500 FCFA partout
```

**Clarté pour le LLM :**
- ✅ Sait qu'il y a 2 types d'informations
- ✅ **3 docs produits** + **2 docs livraison**
- ✅ Peut répondre aux 2 intentions en une seule réponse

---

### **Exemple 3 : Document unique**

**Query :** `"vous acceptez Wave ?"`

**Contexte LLM :**
```
POUR (paiement et support) - Index: support_paiement_MpfnlSbqwaZ6F4HvxQLRL9du0yG3 - voici le document trouvé :
Modes de paiement acceptés :
- Wave CI
- Orange Money
- MTN Mobile Money
- Espèces à la livraison

Pas d'acompte requis.
Paiement à 100% à la livraison.
```

**Clarté pour le LLM :**
- ✅ Sait que c'est une info **paiement**
- ✅ Voit qu'il n'y a **qu'un seul document**
- ✅ Peut répondre directement

---

### **Exemple 4 : Fallback (company_docs)**

**Query :** `"quelles sont vos valeurs d'entreprise ?"`

**Contexte LLM :**
```
POUR (informations générales) - Index: company_docs_MpfnlSbqwaZ6F4HvxQLRL9du0yG3 - voici le document trouvé :
VALEURS DE NOTRE ENTREPRISE:

Nous sommes une entreprise basée sur 3 valeurs fondamentales :
1. Service client exemplaire
2. Qualité des produits garantie
3. Livraison rapide et fiable

Notre mission : Faciliter l'accès aux produits essentiels pour les familles en Côte d'Ivoire.
```

**Clarté pour le LLM :**
- ✅ Sait que c'est une info **générale**
- ✅ Comprend que c'est du fallback
- ✅ Peut utiliser cette info pour répondre

---

## 🎯 AVANTAGES DU FORMAT

### **1. Structure explicite**
```
Le LLM voit immédiatement :
- La catégorie (produits, livraison, etc.)
- L'index source
- Le nombre de documents disponibles
```

### **2. Évite les hallucinations**
```
❌ MAUVAIS FORMAT (confusion possible):
"Couches taille 3 : 20 500 FCFA. Livraison 1 500 FCFA."

→ Le LLM peut inventer des détails

✅ BON FORMAT (clair et explicite):
"POUR (produits) - Document 1/2 :
Couches taille 3 : 20 500 FCFA

POUR (livraison) - Document 1/1 :
Frais de livraison : 1 500 FCFA"

→ Le LLM sait exactement ce qu'il peut dire
```

### **3. Gestion intentions multiples**
```
Le LLM voit clairement les différentes catégories
→ Peut structurer sa réponse en conséquence
```

### **4. Tracabilité**
```
Index source affiché
→ Debug facile si problème
```

---

## 📊 FORMAT COMPLET (AVEC TOUTES CATÉGORIES)

**Query complexe :** `"couches + livraison + paiement"`

**Contexte LLM :**
```
POUR (produits) - Index: products_xxx - Document 1/3 :
[CONTENU PRODUIT 1]

POUR (produits) - Index: products_xxx - Document 2/3 :
[CONTENU PRODUIT 2]

POUR (produits) - Index: products_xxx - Document 3/3 :
[CONTENU PRODUIT 3]

POUR (livraison) - Index: delivery_xxx - Document 1/2 :
[CONTENU LIVRAISON 1]

POUR (livraison) - Index: delivery_xxx - Document 2/2 :
[CONTENU LIVRAISON 2]

POUR (paiement et support) - Index: support_paiement_xxx - voici le document trouvé :
[CONTENU PAIEMENT]
```

**Réponse LLM attendue :**
```
"Pour les couches taille 3, le prix est de 20 500 FCFA le lot de 100.

Concernant la livraison, nous livrons à Yopougon pour 1 500 FCFA 
avec un délai de 24-48h.

Pour le paiement, nous acceptons Wave CI, Orange Money et espèces 
à la livraison. Pas d'acompte requis."
```

**→ Réponse complète, structurée, sans hallucination !**

---

## 🔍 CAS LIMITES

### **Cas 1 : Aucun document trouvé**
```
Contexte : (vide)

→ Le LLM génère : "Je n'ai pas d'information sur ce sujet."
```

### **Cas 2 : Informations partielles**
```
POUR (produits) - Document 1/1 :
Couches disponibles

→ Le LLM dit : "Nous avons des couches disponibles" 
  (ne peut pas inventer le prix)
```

---

## ✅ RÈGLES D'OR

1. ✅ **Toujours afficher la catégorie**
2. ✅ **Toujours afficher l'index source**
3. ✅ **Toujours indiquer X/Y documents**
4. ✅ **Séparer clairement les catégories**
5. ✅ **Contenu brut sans modification**

---

## 🎯 RÉSUMÉ

Le format `POUR (catégorie) - Index: xxx - Document X/Y :` est :

- ✅ **Explicite** : Le LLM comprend immédiatement
- ✅ **Structuré** : Facilite le parsing par le LLM
- ✅ **Anti-hallucination** : Cadre clair
- ✅ **Traçable** : Index source visible
- ✅ **Scalable** : Fonctionne avec 1 ou 15 documents

**Format éprouvé et optimal ! 🚀**

# 🔒 BOTLIVE - VALEURS HARDCODÉES (RUE DU GROSSISTE)

## 📋 Résumé des modifications

Toutes les valeurs spécifiques à "Rue du Grossiste" ont été **hardcodées en dur** dans les prompts Botlive (Groq 70B et DeepSeek V3).

---

## ✅ Valeurs hardcodées

| Variable | Valeur hardcodée | Localisation dans le prompt |
|----------|------------------|----------------------------|
| **Nom entreprise** | "Rue du Grossiste" | Ligne 12, 165 |
| **Secteur** | "produits bébés" | Ligne 165 (DeepSeek uniquement) |
| **Nom du bot** | "Jessica" | Ligne 12, 101, 165 |
| **Téléphone support** | "+225 07 87 36 07 57" | Lignes 22, 24, 101 |
| **Méthode paiement** | "dépôt mobile money sur +225 07 87 36 07 57" | Ligne 17, 170 |
| **Preuve paiement** | "capture prouvant paiement (numéro entreprise + montant visibles)" | Ligne 17, 170 |
| **Zones livraison** | Voir section dédiée ci-dessous | Lignes 63, 217-219 |
| **Catégories produits** | "lingettes, couches, casques" | Ligne 120, 243 (dans règle générique) |
| **Montant acompte** | "2000 FCFA" | Ligne 308 (valeur par défaut) |
| **Devise** | "FCFA" (ou "F CFA") | Partout dans les exemples |
| **Délai livraison** | "commande avant 13h = jour même, après 13h = lendemain" | Lignes 106, 117, 240 |
| **Ton communication** | "Décontracté-pro, tutoiement" | Lignes 31, 184 |

---

## 📍 Zones de livraison hardcodées

### Format compact (Groq 70B - Ligne 63):
```
Centre(1500 FCFA): Yopougon,Cocody,Plateau,Adjamé,Abobo,Marcory,Koumassi,Treichville,Angré,Riviera,Andokoua | Périphérie(2000 FCFA): Port-Bouët,Attécoubé | Éloigné(2500 FCFA): Bingerville,Songon,Anyama,Brofodoumé,Grand-Bassam,Dabou
```

### Format détaillé (DeepSeek V3 - Lignes 217-219):
```
Centre (1500 FCFA): Yopougon, Cocody, Plateau, Adjamé, Abobo, Marcory, Koumassi, Treichville, Angré, Riviera, Andokoua
Périphérie (2000 FCFA): Port-Bouët, Attécoubé
Éloigné (2500 FCFA): Bingerville, Songon, Anyama, Brofodoumé, Grand-Bassam, Dabou
```

---

## 💰 Informations paiement hardcodées

### Numéro de réception dépôt:
- **+225 07 87 36 07 57**

### Instructions paiement dans le prompt:
```
2. PAIEMENT → Demande dépôt mobile money sur +225 07 87 36 07 57 + capture prouvant paiement (numéro entreprise + montant visibles). Sans acompte = pas de validation.
```

### Message de salutation (avec numéro):
```
"Bonjour ! Jessica ici. J'ai besoin: ✅Capture produit ✅Preuve dépôt mobile money (+225 07 87 36 07 57) ✅Adresse+numéro. Coût livraison? Donne ta commune. Autres questions→Support +225 07 87 36 07 57"
```

---

## 🚚 Délais de livraison hardcodés

### Message de finalisation:
```
"Commande OK ! Livraison: commande avant 13h = jour même, après 13h = lendemain 😊 Si tout es ok. Ne réponds pas à ce message"
```

### Règle dans le prompt:
- **Commande avant 13h** → Livraison le jour même
- **Commande après 13h** → Livraison le lendemain

---

## 💵 Format devise hardcodé

Toutes les occurrences de devise ont été standardisées:

### Avant:
- `F` (franc seul)
- `2020F` (collé)

### Après (hardcodé):
- `FCFA` (Franc CFA complet)
- `2020 FCFA` (avec espace)

### Exemples dans le prompt:
```
✅ notepad("append","✅PAIEMENT:2020 FCFA[TRANSACTIONS]")
✅ notepad("append","✅ZONE:Yopougon-1500 FCFA[MESSAGE]")
"Validé X FCFA ✅ Ta zone?"
"Photo reçue ! Dépôt: {expected_deposit} FCFA"
```

---

## 🎭 Ton et personnalité hardcodés

### Caractéristiques:
- **Ton**: Décontracté-pro, tutoiement, chaleureux mais directif
- **Nom du bot**: Jessica
- **Entreprise**: Rue du Grossiste
- **Secteur**: produits bébés (mentionné uniquement dans DeepSeek V3)

### Style de réponse:
- MAX 2-3 phrases
- Affirmatif ("Envoie X") pas interrogatif ("Peux-tu X?")
- Emojis variés (😊, 🎁, 👍, 📝)
- Termes génériques pour produits (jamais "lingettes", "couches" explicitement)

---

## 📝 Exemples de réponses hardcodées

### Salutation:
```
"Bonjour ! Jessica ici. J'ai besoin: ✅Capture produit ✅Preuve dépôt mobile money (+225 07 87 36 07 57) ✅Adresse+numéro. Coût livraison? Donne ta commune. Autres questions→Support +225 07 87 36 07 57"
```

### Produit reçu:
```
"Photo reçue ! Dépôt: 2000 FCFA"
"OK ! Envoie acompte: 2000 FCFA"
```

### Paiement validé:
```
"Validé 2020 FCFA ✅ Ta zone?"
"Reçu 2020 FCFA 👍 Livraison où?"
```

### Zone confirmée:
```
"Yopougon 1500 FCFA. Ton numéro?"
"OK 1500 FCFA livraison. Contact?"
```

### Finalisation:
```
"Commande OK ! Livraison: commande avant 13h = jour même, après 13h = lendemain 😊 Si tout es ok. Ne réponds pas à ce message"
```

---

## 🔧 Fichier modifié

**Fichier**: `core/botlive_prompts_hardcoded.py`

### Sections modifiées:
1. **GROQ_70B_PROMPT** (lignes 12-159)
   - Paiement avec numéro mobile money
   - Zones avec devise FCFA
   - Délai livraison 13h
   - Exemples avec FCFA

2. **DEEPSEEK_V3_PROMPT** (lignes 165-265)
   - Mêmes modifications que Groq 70B
   - Mention "produits bébés" dans l'introduction

3. **format_prompt()** (ligne 308)
   - Valeur par défaut `expected_deposit` = "2000" (sans FCFA car ajouté dans le prompt)

---

## ⚠️ Notes importantes

1. **Pas de placeholders**: Toutes les valeurs sont en dur, pas de `{{VARIABLE}}`
2. **Devise standardisée**: Toujours "FCFA" avec espace (ex: "2000 FCFA")
3. **Numéro unique**: +225 07 87 36 07 57 pour support ET réception paiement
4. **Délai 13h**: Point de coupure pour livraison jour même vs lendemain
5. **Termes génériques**: Le prompt interdit de mentionner "lingettes", "couches", "casques" dans les réponses

---

## ✅ Validation

Pour vérifier que les modifications sont bien appliquées:

```python
from core.botlive_prompts_hardcoded import GROQ_70B_PROMPT, DEEPSEEK_V3_PROMPT

# Vérifier présence numéro mobile money
assert "+225 07 87 36 07 57" in GROQ_70B_PROMPT
assert "+225 07 87 36 07 57" in DEEPSEEK_V3_PROMPT

# Vérifier devise FCFA
assert "FCFA" in GROQ_70B_PROMPT
assert "FCFA" in DEEPSEEK_V3_PROMPT

# Vérifier délai 13h
assert "avant 13h" in GROQ_70B_PROMPT
assert "avant 13h" in DEEPSEEK_V3_PROMPT

# Vérifier nom Jessica
assert "Jessica" in GROQ_70B_PROMPT
assert "Jessica" in DEEPSEEK_V3_PROMPT

print("✅ Toutes les valeurs hardcodées sont présentes!")
```

---

**Version**: 1.0  
**Date**: 2025-10-14  
**Statut**: ✅ Production-ready  
**Entreprise**: Rue du Grossiste (produits bébés)

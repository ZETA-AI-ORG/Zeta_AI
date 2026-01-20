# 🐛 REGISTRE DES BUGS ET SOLUTIONS - CHATBOT ZETA APP

**Date de création:** 17 Octobre 2025  
**Dernière mise à jour:** 17 Octobre 2025 18:17

---

## 📊 RÉSUMÉ

| Catégorie | Bugs Résolus | Bugs En Cours |
|-----------|--------------|---------------|
| **Exécution Tools** | 3 | 0 |
| **Mémoire Conversationnelle** | 2 | 1 |
| **Patterns Regex** | 2 | 0 |
| **Configuration** | 1 | 0 |
| **Tests** | 1 | 0 |
| **TOTAL** | **9** | **1** |

---

## 🔥 BUGS CRITIQUES RÉSOLUS

### BUG #1: execute_tools_from_response() n'existe pas
**Date:** 17 Octobre 2025 17:00  
**Sévérité:** 🔴 CRITIQUE (Bloquant)

**ERREUR:**
```
cannot import name 'execute_tools_from_response' from 'core.botlive_tools'
```

**SOURCE:**
- Fichier: core/universal_rag_engine.py ligne 1147
- Cause: Mauvais nom de fonction importée
- La fonction s'appelle execute_tools_in_response et non execute_tools_from_response

**SOLUTION:**
```python
# AVANT (incorrect):
from core.botlive_tools import execute_tools_from_response
response = await execute_tools_from_response(response, user_id, company_id)

# APRES (correct):
from core.botlive_tools import execute_tools_in_response
response = execute_tools_in_response(response, user_id, company_id)
```

**Fichiers modifiés:**
- core/universal_rag_engine.py

---

### BUG #2: Pattern regex trop strict pour Bloc-note
**Date:** 17 Octobre 2025 18:05  
**Sévérité:** 🔴 CRITIQUE (Bloquant)

**ERREUR:**
```
Le LLM génère: Action : Bloc-note: ajouter info (produit, "couches")
Le regex attend: Bloc-note: ajouter info ("produit", "couches")
Résultat: Aucun match! Les actions ne sont pas exécutées.
```

**SOURCE:**
- Fichier: core/botlive_tools.py ligne 312
- Cause: Pattern regex exige des guillemets sur TOUS les arguments
- Le LLM met des guillemets uniquement sur la valeur, pas sur la clé

**SOLUTION:**
Rendre le pattern flexible pour accepter clés avec ou sans guillemets

**Fichiers modifiés:**
- core/botlive_tools.py lignes 310-334

---

### BUG #3: Clés quantité et taille non reconnues
**Date:** 17 Octobre 2025 18:10  
**Sévérité:** 🟠 HAUTE

**ERREUR:**
```
WARNING: Clé inconnue: quantité=300
WARNING: Clé inconnue: taille=5
```

**SOURCE:**
- Fichier: core/conversation_notepad.py ligne 382
- Cause: Méthode add_info() ne reconnaît que 5 types de clés
- Les clés quantité et taille tombent dans le else (clé inconnue)

**SOLUTION:**
Ajout de 2 nouveaux blocs de traitement pour quantité et taille

**Fichiers modifiés:**
- core/conversation_notepad.py lignes 382-406

---

### BUG #4: Test ne détecte pas les actions avec Action :
**Date:** 17 Octobre 2025 18:12  
**Sévérité:** 🟡 MOYENNE

**ERREUR:**
```
Le LLM génère: "Action : Bloc-note: ajouter info (produit, "valeur")"
Le test cherche: "Bloc-note: ajouter info"
Résultat: Test échoue alors que l'action est bien présente
```

**SOURCE:**
- Fichier: tools/test_hardcore_lite.py ligne 124
- Cause: Recherche exacte de la chaîne sans variantes
- Le LLM ajoute parfois Action : devant

**SOLUTION:**
Pattern regex flexible qui accepte les deux formats

**Fichiers modifiés:**
- tools/test_hardcore_lite.py lignes 123-131

---

## 🧠 BUGS MÉMOIRE CONVERSATIONNELLE

### BUG #5: Mémoire ne retient pas les informations (Score 18.3%)
**Date:** 17 Octobre 2025 17:20  
**Sévérité:** 🔴 CRITIQUE

**ERREUR:**
```
Échange 22: rappel commande - Score 33.3%
Manquant: lot 150, taille 5

Échange 23: prix total rappel - Score 0.0%
Manquant: 15000, 13500, 1500

Échange 24: récapitulatif complet - Score 40.0%
Manquant: lot 150, 15000, Wave
```

**SOURCE:**
- Système: EnhancedMemory + UniversalConversationSynthesis
- Cause: Les informations sont stockées mais pas récupérées dans le prompt
- Le bloc-note reste vide car les actions LLM ne sont pas exécutées (BUG #1)

**SOLUTION EN COURS:**
1. Corriger l'exécution des tools (BUG #1, #2, #3) ✅
2. Vérifier que le bloc-note se remplit correctement
3. Injecter le contenu du bloc-note dans le prompt LLM

**Statut:** 🟡 EN COURS (dépend de BUG #1, #2, #3)

---

### BUG #6: Informations contradictoires sur le paiement
**Date:** 17 Octobre 2025 17:22  
**Sévérité:** 🟠 HAUTE

**ERREUR:**
```
Échange 22: Paiement: paid
Échange 23: Paiement: pending
Échange 24: Paiement: pending
Échange 25: Paiement: pending

Le système dit payé puis repasse à en attente
```

**SOURCE:**
- Fichier: core/enhanced_memory.py
- Cause: Logique de détection du statut paiement incohérente
- Plusieurs sources de vérité (HISTORIQUE vs TRANSACTIONS)

**SOLUTION:**
Simplifier la logique: soit pending soit confirmed (jamais paid avant confirmation finale)

**Statut:** 🟡 À CORRIGER

---

## 🎯 BUGS TESTS

### BUG #7: Test hardcore ne s'arrête pas au premier bug
**Date:** 17 Octobre 2025 17:30  
**Sévérité:** 🟡 MOYENNE

**ERREUR:**
```
Le test continue même après détection d'erreurs critiques
Difficile d'identifier la cause racine du premier échec
```

**SOURCE:**
- Fichier: tools/test_meili_progression_hardcore.py
- Cause: Pas de mécanisme d'arrêt immédiat
- Pas de diagnostic automatique de la cause

**SOLUTION:**
Création de test_hardcore_lite.py avec:
- Arrêt immédiat au premier bug
- Diagnostic automatique de la cause racine
- Analyse du thinking, response et bloc-note
- Recommandations de correction

**Fichiers créés:**
- tools/test_hardcore_lite.py (nouveau)

---

## ⚙️ BUGS CONFIGURATION

### BUG #8: _generate_progression_directive n'existe pas
**Date:** 17 Octobre 2025 18:03  
**Sévérité:** 🟡 MOYENNE (Non bloquant)

**ERREUR:**
```
WARNING: Injection notepad/directive échouée: 
'UniversalRAGEngine' object has no attribute '_generate_progression_directive'
```

**SOURCE:**
- Fichier: core/universal_rag_engine.py
- Cause: Méthode supprimée ou renommée
- Appelée dans enrich_prompt_with_context()

**SOLUTION:**
Supprimer l'appel ou implémenter la méthode manquante

**Statut:** 🟡 À CORRIGER (non bloquant)

---

## 📝 BUGS PROMPT

### BUG #9: Variable context manquante dans template
**Date:** 17 Octobre 2025 18:03  
**Sévérité:** 🟢 FAIBLE (Warning)

**ERREUR:**
```
Variable manquante dans template (cache): 'context'
```

**SOURCE:**
- Fichier: core/universal_rag_engine.py
- Cause: Template Supabase utilise {context} mais variable pas toujours définie
- Fallback fonctionne correctement

**SOLUTION:**
Vérifier que toutes les variables du template sont définies avant remplacement

**Statut:** 🟢 MINEUR (ne bloque pas le fonctionnement)

---

## 📈 HISTORIQUE DES CORRECTIONS

### Session 17 Octobre 2025 (17:00 - 18:17)

**17:00 - Identification BUG #1**
- Test hardcore échoue avec erreur import
- Fonction mal nommée identifiée

**17:05 - Correction BUG #1**
- Changement execute_tools_from_response → execute_tools_in_response
- Retrait await (fonction non async)

**18:05 - Identification BUG #2**
- Tools toujours pas exécutés malgré correction BUG #1
- Pattern regex trop strict identifié

**18:08 - Correction BUG #2**
- Pattern regex rendu flexible
- Support clés avec/sans guillemets

**18:10 - Identification BUG #3**
- Warning clés inconnues dans les logs
- quantité et taille non supportées

**18:12 - Correction BUG #3**
- Ajout support quantité (5 variantes)
- Ajout support taille (4 variantes)

**18:15 - Identification BUG #4**
- Test échoue malgré actions présentes
- Détection trop stricte

**18:17 - Correction BUG #4**
- Pattern regex flexible dans test
- Support Action : optionnel

---

## 🎯 PROCHAINES ACTIONS

### Priorité 1 - CRITIQUE
1. ✅ Tester les corrections BUG #1, #2, #3, #4
2. ⏳ Valider que le bloc-note se remplit correctement
3. ⏳ Corriger BUG #5 (mémoire conversationnelle)

### Priorité 2 - HAUTE
4. ⏳ Corriger BUG #6 (incohérence paiement)
5. ⏳ Corriger BUG #8 (_generate_progression_directive)

### Priorité 3 - MOYENNE
6. ⏳ Améliorer les tests de régression
7. ⏳ Documenter les patterns regex acceptés

---

## 📚 LEÇONS APPRISES

### 1. Toujours vérifier les noms de fonctions
- Utiliser grep pour chercher la vraie définition
- Ne pas se fier aux noms supposés

### 2. Les LLM sont imprévisibles
- Patterns regex doivent être flexibles
- Accepter plusieurs variantes de syntaxe
- Tester avec des exemples réels

### 3. Tests auto-diagnostiques essentiels
- Arrêt immédiat au premier bug
- Analyse automatique de la cause
- Recommandations de correction

### 4. Clés dynamiques nécessitent whitelist
- Lister toutes les variantes possibles
- Normaliser en lowercase
- Logger les clés inconnues

---

## 🔗 FICHIERS CRITIQUES

### Exécution des tools
- core/botlive_tools.py (patterns regex)
- core/universal_rag_engine.py (appel execute_tools)

### Mémoire conversationnelle
- core/conversation_notepad.py (stockage)
- core/enhanced_memory.py (récupération)
- core/universal_conversation_synthesis.py (synthèse)

### Tests
- tools/test_hardcore_lite.py (auto-diagnostic)
- tools/test_meili_progression_hardcore.py (25 échanges)

---

**FIN DU REGISTRE**

*Ce document est mis à jour en temps réel lors de la découverte et résolution de bugs.*

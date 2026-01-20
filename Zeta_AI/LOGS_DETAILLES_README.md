# 🔍 LOGS DÉTAILLÉS - DIAGNOSTIC RAG

## 📋 **RÉSUMÉ DES MODIFICATIONS**

### **Problème Identifié**
- Logs basiques insuffisants pour diagnostiquer le routing des documents
- Impossible de voir pourquoi des documents non pertinents sont sélectionnés
- Manque de visibilité sur le contenu complet des documents trouvés

### **Solution Implémentée**

#### **1. 🆕 Nouveau Module : `core/diagnostic_logger.py`**
```python
from core.diagnostic_logger import diagnostic_logger
```

**Fonctionnalités :**
- ✅ **Logs combinaisons de requêtes** - Voir toutes les requêtes générées
- ✅ **Logs contenu complet** - Afficher le texte intégral de chaque document
- ✅ **Logs sélection finale** - Documents envoyés au LLM avec raisons
- ✅ **Analyse routing** - Évaluation de la pertinence par index
- ✅ **Scoring détaillé** - Processus de notation et filtrage

#### **2. 🔧 Modifications : `database/vector_store_clean.py`**
- Import du diagnostic logger avec fallback
- Intégration des logs détaillés dans la recherche MeiliSearch
- Analyse automatique de la pertinence du routing

## 🎯 **NOUVEAUX LOGS DISPONIBLES**

### **1. 📊 Combinaisons de Requêtes**
```
🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄
🔍 COMBINAISONS DE REQUÊTES GÉNÉRÉES
📊 TOTAL: 20 requêtes
🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄
   1. 'bojur 2 paquets couche culottes 13kg ca ?'
   2. 'bojur'
   3. '2'
   4. 'paquets'
   ...
```

### **2. 📄 Contenu Complet des Documents**
```
================================================================================
🔍 DÉTAIL DOCUMENTS TROUVÉS - INDEX: products_MpfnlSbqwaZ6F4HvxQLRL9du0yG3
📊 TOTAL DOCUMENTS SÉLECTIONNÉS: 2
================================================================================

📄 DOCUMENT 1/2
   🆔 ID: prod_001
   ⭐ SCORE: 4.9
   🏷️ TYPE: produits
   🔍 REQUÊTE ORIGINE: 'paquets couche culottes'
   📏 TAILLE CONTENU: 337 caractères
   📝 CONTENU COMPLET:
   ------------------------------------------------------------
   PRODUITS : Couches culottes ( pour enfant de 5 à 30 kg )
   VARIANTES ET PRIX :
   1 paquet - 5.500 F CFA | 5.500 F/paquet
   2 paquets - 9.800 F CFA | 4.900 F/paquet
   3 paquets - 13.500 F CFA | 4.500 F/paquet
   ------------------------------------------------------------
   🎯 MOTS-CLÉS TROUVÉS: paquets, couche, culottes
   ✅ SÉLECTIONNÉ: Document ajouté aux résultats finaux
   🎯 RAISON: Score élevé (4.9) + mots-clés pertinents
```

### **3. 🎯 Sélection Finale pour le LLM**
```
🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯
📤 SÉLECTION FINALE POUR LE LLM
📊 SÉLECTIONNÉS: 7 documents au total
🔍 REQUÊTE: 'bojur je veux 2 paquets de couche a culottes 13kg ca fera combien ?'
🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯

✅ DOCUMENT SÉLECTIONNÉ 1
   🏷️ INDEX SOURCE: products_MpfnlSbqwaZ6F4HvxQLRL9du0yG3
   🆔 ID: prod_001
   ⭐ SCORE FINAL: 4.9
   🔍 REQUÊTE ORIGINE: 'paquets couche culottes'
   📏 TAILLE: 337 chars
   📝 EXTRAIT (150 premiers chars):
   'PRODUITS : Couches culottes ( pour enfant de 5 à 30 kg ) VARIANTES ET PRIX : 1 paquet - 5.500 F CFA | 5.500 F/paquet 2 paquets - 9.800 F CFA...'
   🎯 RAISON SÉLECTION: Score élevé | Mots-clés trouvés: paquets, couche, culottes | Contenu produit pertinent

✅ DOCUMENT SÉLECTIONNÉ 2
   🏷️ INDEX SOURCE: delivery_MpfnlSbqwaZ6F4HvxQLRL9du0yG3
   🆔 ID: deliv_001
   ⭐ SCORE FINAL: 0.8
   📝 EXTRAIT: 'Zones de livraison Abidjan...'
   🎯 RAISON SÉLECTION: ⚠️ Score faible - Routing suspect
```

### **4. 🧭 Analyse Routing Global**
```
🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭
🧭 ANALYSE ROUTING GLOBAL
🔍 REQUÊTE: 'bojur je veux 2 paquets de couche a culottes 13kg ca fera combien ?'
🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭🧭
   🎯 TYPE DÉTECTÉ: PRIX/PRODUIT
   📋 INDEX ATTENDUS: products
   📊 INDEX ACTIVÉS: products, delivery, localisation, support
   🎯 QUALITÉ ROUTING: ❌ PROBLÉMATIQUE
   📊 Index pertinents: 1/4
   ⚠️ RECOMMANDATION: Implémenter filtrage par score de pertinence
```

## 🚀 **AVANTAGES**

### **1. 🔍 Diagnostic Précis**
- **Visibilité complète** sur le contenu des documents
- **Identification claire** des problèmes de routing
- **Analyse automatique** de la pertinence

### **2. 🎯 Détection des Problèmes**
- Documents non pertinents avec scores faibles
- Index activés inutilement (delivery, localisation, support)
- Mots-clés manqués ou mal interprétés

### **3. 📊 Métriques Détaillées**
- Scores par document et par index
- Taille et contenu exact des documents
- Raisons de sélection/rejet

## 🔧 **UTILISATION**

### **Activer/Désactiver les Logs**
```python
from core.diagnostic_logger import enable_diagnostic_logs, disable_diagnostic_logs

# Activer pour debugging
enable_diagnostic_logs()

# Désactiver en production
disable_diagnostic_logs()
```

### **Logs Automatiques**
Les logs sont automatiquement générés lors de chaque recherche MeiliSearch dans `vector_store_clean.py`.

## 🎯 **PROCHAINES ÉTAPES**

### **1. 🔧 Correction Routing**
Avec ces logs, on peut maintenant :
- Identifier pourquoi `delivery`, `localisation`, `support` sont sélectionnés
- Implémenter un filtrage par score de pertinence
- Améliorer la logique de sélection des index

### **2. 💰 Correction Prix**
Les logs montrent le contenu exact des documents, permettant de :
- Vérifier si les tarifs dégressifs sont présents
- Corriger le prompt LLM pour utiliser les prix explicites
- Éviter les calculs linéaires incorrects

### **3. 📈 Optimisation Performance**
- Réduire le nombre d'index interrogés inutilement
- Améliorer la précision des requêtes
- Optimiser les scores de pertinence

## 📋 **FICHIERS MODIFIÉS**

1. **🆕 `core/diagnostic_logger.py`** - Nouveau module de logs détaillés
2. **🔧 `database/vector_store_clean.py`** - Intégration des logs diagnostiques
3. **📄 `LOGS_DETAILLES_README.md`** - Cette documentation

Ces modifications permettent maintenant un **diagnostic complet** du système RAG pour résoudre les problèmes de routing et de calcul de prix ! 🚀

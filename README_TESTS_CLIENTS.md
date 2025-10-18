# 🎭 TESTS SIMULATION CLIENTS RÉELS - BOTLIVE

## 📋 Description

Suite de tests simulant 3 profils de clients réels pour valider la robustesse du système Botlive.

## 🎯 Profils de Clients

### 1️⃣ **Client Direct** (`test_client_direct.py`)
**Comportement:** Va à l'essentiel, suit les directives du LLM

**Workflow:**
1. Salutation simple
2. Envoie photo produit immédiatement
3. Confirme sans hésitation
4. Envoie paiement
5. Donne zone de livraison
6. Donne numéro de téléphone

**Temps estimé:** ~30 secondes  
**Nombre d'étapes:** 6

---

### 2️⃣ **Client Hésitant** (`test_client_hesitant.py`)
**Comportement:** Pose beaucoup de questions spécifiques, hésite, finit par commander

**Workflow:**
1. Salutation
2. Questions sur tailles disponibles
3. Questions sur prix
4. Questions sur qualité
5. Questions sur livraison et délais
6. Questions sur modes de paiement
7. Envoie photo
8. Hésite encore
9. Confirme finalement
10. Envoie paiement
11. Demande précisions sur zone
12. Pose question sur contact
13. Donne numéro

**Temps estimé:** ~60-90 secondes  
**Nombre d'étapes:** 14

---

### 3️⃣ **Client Difficile** (`test_client_difficile.py`)
**Comportement:** Change d'avis 3+ fois, sujets hors domaine, conversation chaotique

**Workflow:**
1. Salutation bizarre
2. ❌ **HORS DOMAINE #1** - Question météo
3. Demande produit
4. 🔄 **CHANGEMENT #1** - Veut autre produit
5. ❌ **HORS DOMAINE #2** - Politique
6. Retour produit initial
7. Envoie photo
8. 🔄 **CHANGEMENT #2** - Veut annuler
9. ❌ **HORS DOMAINE #3** - Football
10. Histoire personnelle longue
11. Confirme
12. 🔄 **CHANGEMENT #3** - Modifie quantité
13. Détails inutiles sur paiement
14. Envoie paiement
15. ❌ **HORS DOMAINE #4** - Santé
16. Donne zone avec détails inutiles
17. ❌ **HORS DOMAINE #5** - Question philosophique
18. Donne numéro avec commentaire

**Temps estimé:** ~2-3 minutes  
**Nombre d'étapes:** 18  
**Changements d'avis:** 3  
**Sujets hors domaine:** 5

---

## 🚀 Utilisation

### Lancer un test individuel

```bash
# WSL
cd ~/ZETA_APP/CHATBOT2.0

# Client direct
python test_client_direct.py

# Client hésitant
python test_client_hesitant.py

# Client difficile
python test_client_difficile.py
```

### Lancer tous les tests

```bash
# Lance les 3 tests séquentiellement
python test_all_clients.py
```

---

## 📊 Résultats Attendus

### ✅ **Succès si:**
- Toutes les étapes complétées
- Commande finalisée avec numéro
- Gestion correcte des hors domaines
- Aucune erreur 422 ou 500
- Temps de réponse < 3s par message

### ❌ **Échec si:**
- Erreur 422 (user_id invalide)
- Erreur 500 (crash serveur)
- Conversation bloquée
- Paiement non détecté
- LLM perdu dans le workflow

---

## 🔧 Configuration

### Variables importantes

```python
BASE_URL = "http://127.0.0.1:8001"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"  # Rue du Grossiste

# User IDs (format important pour éviter 422)
USER_ID_DIRECT = "client_direct_001"
USER_ID_HESITANT = "client_hesitant_002"
USER_ID_DIFFICILE = "client_difficile_003"
```

### Images de test

```python
TEST_IMAGES = {
    'product': 'https://storage.googleapis.com/zanzibar-products-images/products/product_test.jpg',
    'payment_2020': 'https://i.ibb.co/02xdMNT/Screenshot-20250108-181624.png'
}
```

---

## 🎯 Objectifs des Tests

1. **Robustesse workflow** : Le système doit gérer tous les profils
2. **Gestion hors domaine** : Réponses appropriées aux questions non-commerciales
3. **Changements d'avis** : Tracking correct des intentions changeantes
4. **Validation paiement** : OCR précis (202 FCFA, 2020 FCFA)
5. **Mémorisation contexte** : Cohérence sur conversations longues

---

## 📈 Métriques Collectées

Chaque test affiche:
- ⏱️ Temps de réponse par message
- 🎯 Nombre d'étapes total
- 🔄 Nombre de changements d'avis (difficile)
- 🚫 Nombre de sujets hors domaine (difficile)
- ✅ Statut final (commande complétée ou non)

---

## 🔍 Debugging

### En cas d'erreur 422
```
❌ Erreur 422: {"detail":"Invalid user_id format"}
```
**Solution:** Vérifier que `USER_ID` suit le format `clientXXX_NNN` ou `testuserNNN`

### En cas de timeout
```
❌ Timeout après 60s
```
**Solution:** 
- Vérifier que le serveur est démarré
- Augmenter timeout dans `httpx.AsyncClient(timeout=60.0)`

### En cas de réponse vide
```
🤖 JESSICA: 
```
**Solution:**
- Vérifier logs serveur pour erreurs LLM
- Vérifier que Groq API est accessible

---

## 💡 Conseils

- **Lancer les tests séquentiellement** pour éviter conflits
- **Attendre 2-3s entre tests** pour reset conversation
- **Vérifier logs serveur** en parallèle pour diagnostics
- **Capturer les sorties** : `python test_all_clients.py > results.log 2>&1`

---

## 📝 Exemple de Sortie

```
🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭
                        TEST CLIENT DIRECT - Comportement idéal
🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭 🎭

================================================================================
🔹 ÉTAPE 1
================================================================================
👤 CLIENT: Bonsoir
⏱️  Temps: 2.06s
🤖 JESSICA: Salut 👋 Envoie photo produit

================================================================================
🔹 ÉTAPE 2
================================================================================
👤 CLIENT: [Photo produit envoyée]
⏱️  Temps: 4.12s
🤖 JESSICA: Photo reçue ! Confirmes ? Dépôt 2000 FCFA

...

================================================================================
📊 RÉSUMÉ CLIENT DIRECT
================================================================================
✅ Commande complétée en 6 étapes
✅ Aucune hésitation
✅ Workflow optimal
================================================================================
```

---

## 🎉 Validation Production

**Critères de validation:**
- ✅ Client Direct : 100% succès
- ✅ Client Hésitant : 100% succès
- ✅ Client Difficile : ≥90% succès (peut échouer sur cas extrêmes)

**Si tous réussis → Système prêt pour production !**

# 🔒 FICHIERS BOTLIVE VERROUILLÉS - NE PAS MODIFIER

## ⚠️ AVERTISSEMENT CRITIQUE
Ces fichiers sont en PRODUCTION et fonctionnent parfaitement.
**NE PAS MODIFIER** lors du travail sur le RAG normal.

---

## 📁 FICHIERS CORE BOTLIVE

### 1. **core/botlive_rag_hybrid.py** 🔴 CRITIQUE
```
Statut : ✅ PRODUCTION READY
Fonction : Auto-détection commandes (produit/paiement/zone/numéro)
Tests : 8/8 réussis (100%)
Dernière modif : 2025-10-13 (validation complète)

⚠️ NE PAS TOUCHER - Système auto-détection validé
```

### 2. **core/order_state_tracker.py** 🔴 CRITIQUE
```
Statut : ✅ PRODUCTION READY
Fonction : Tracking état commandes (DB SQLite)
Base de données : order_states.db
Dernière modif : 2025-10-13

⚠️ NE PAS TOUCHER - Gestion état commandes
```

### 3. **app.py (sections Botlive)** 🟡 PARTIEL
```
Statut : ✅ PRODUCTION READY
Lignes critiques :
  - 610-950 : _botlive_handle()
  - 479-608 : _process_botlive_vision()
  - 1280-1420 : Route /chat (logique Botlive)

⚠️ MODIFIER UNIQUEMENT sections RAG (lignes 1421+)
```

---

## 📁 FICHIERS PROMPTS BOTLIVE

### 4. **prompts/botlive_prompt.txt** 🔴 CRITIQUE
```
Statut : ✅ PRODUCTION READY
Taille : ~3400 chars, 850 tokens
Version : Finale validée
Performance : 0→100% workflow parfait

⚠️ NE PAS TOUCHER - Prompt optimisé et testé
```

---

## 📁 FICHIERS TESTS BOTLIVE

### 5. **test_auto_detect_validation.py** 🟢 SAFE
```
Statut : ✅ Tests validés
Tests : 4/4 réussis (100%)

✅ Peut être modifié pour ajouter tests
```

### 6. **test_ordre_melange.py** 🟢 SAFE
```
Statut : ✅ Tests validés
Tests : 3/3 réussis (100%)

✅ Peut être modifié pour ajouter tests
```

### 7. **check_state.py** 🟢 SAFE
```
Statut : ✅ Outil de vérification

✅ Peut être modifié
```

---

## 📁 BASE DE DONNÉES BOTLIVE

### 8. **order_states.db** 🔴 CRITIQUE
```
Statut : ✅ PRODUCTION
Type : SQLite
Tables : order_states (user_id, produit, paiement, zone, numero, completion)

⚠️ NE PAS SUPPRIMER - Données clients en production
⚠️ Faire backup avant toute migration
```

---

## 📁 FICHIERS SPÉCIFICATION

### 9. **AUTO_DETECT_SPEC.md** 🟢 DOCUMENTATION
```
Statut : ✅ Documentation validée
Contenu : Spécification complète auto-détection

✅ Peut être enrichi
```

---

## 🚫 ZONES INTERDITES DANS app.py

```python
# ❌ NE PAS MODIFIER CES SECTIONS

# Ligne 479-608 : Vision Botlive
async def _process_botlive_vision(image_url: str, company_phone: str = None):
    # ... CODE VALIDÉ ...

# Ligne 610-950 : Handler Botlive
async def _botlive_handle(company_id: str, user_id: str, message: str, images: list, ...):
    # ... CODE VALIDÉ ...

# Ligne 1280-1420 : Logique Botlive dans /chat
if req.botlive_enabled:
    # ... CODE VALIDÉ ...
```

---

## ✅ ZONES MODIFIABLES POUR RAG

```python
# ✅ VOUS POUVEZ MODIFIER CES SECTIONS

# Ligne 1421+ : Logique RAG normal
else:
    # RAG normal (non-Botlive)
    msg_for_rag = req.message or ...
    response_text = await asyncio.wait_for(...)

# Fichiers RAG normaux (non-Botlive)
- core/rag_engine.py
- core/multi_index_search_engine.py
- core/supabase_vector_search.py
- core/smart_llm_router.py (sections non-Botlive)
```

---

## 🔄 WORKFLOW SÉCURISÉ

### Avant de travailler sur RAG :

1. **Créer une branche Git**
```bash
cd ~/ZETA_APP/CHATBOT2.0
git checkout -b feature/rag-improvements
git add .
git commit -m "Checkpoint: Botlive validé avant travail RAG"
```

2. **Backup fichiers critiques**
```bash
mkdir -p backups/botlive_$(date +%Y%m%d_%H%M%S)
cp core/botlive_rag_hybrid.py backups/botlive_*/
cp core/order_state_tracker.py backups/botlive_*/
cp prompts/botlive_prompt.txt backups/botlive_*/
cp order_states.db backups/botlive_*/
```

3. **Tester Botlive avant modifications**
```bash
python3 test_auto_detect_validation.py
# Doit afficher : 4/4 tests réussis (100%)
```

4. **Après modifications RAG, re-tester Botlive**
```bash
python3 test_auto_detect_validation.py
# Si échec : git checkout main (retour arrière)
```

---

## 📊 MÉTRIQUES BOTLIVE À PRÉSERVER

```json
{
  "auto_detection": "100% fonctionnel",
  "tests_validation": "8/8 réussis",
  "ordre_melange": "3/3 réussis",
  "temps_reponse": "~1.7s",
  "cout_requete": "$0.000317",
  "marge_abonnement": "75-86%",
  "status": "✅ PRODUCTION READY"
}
```

---

## 🚨 CHECKLIST AVANT COMMIT

Avant chaque commit sur la branche RAG :

- [ ] Aucun fichier 🔴 CRITIQUE modifié
- [ ] Tests Botlive toujours à 100%
- [ ] order_states.db intact
- [ ] Temps réponse Botlive < 2s
- [ ] Aucune régression auto-détection

---

## 📞 CONTACT EN CAS DE PROBLÈME

Si modification accidentelle d'un fichier verrouillé :

```bash
# Restaurer depuis backup
cp backups/botlive_YYYYMMDD_HHMMSS/[fichier] ./

# Ou restaurer depuis Git
git checkout main -- [fichier]

# Vérifier que Botlive fonctionne
python3 test_auto_detect_validation.py
```

---

## 📅 DERNIÈRE VALIDATION

- Date : 2025-10-13
- Tests : 100% réussis
- Status : ✅ PRODUCTION READY
- Prochaine revue : Après modifications RAG

**🔒 CES FICHIERS SONT VERROUILLÉS - NE PAS MODIFIER SANS VALIDATION**

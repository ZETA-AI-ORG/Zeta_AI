# 🚀 SETUP BOTLIVE - GUIDE RAPIDE

## 📋 **ÉTAPES D'INSTALLATION**

### **1️⃣ Installation EasyOCR**

```bash
pip install easyocr
```

⚠️ **Note**: L'installation peut prendre 5-10 minutes (téléchargement modèles ~500MB)

---

### **2️⃣ Configuration .env**

Ajoute/modifie dans ton fichier `.env`:

```bash
# ========= 🔗 SUPABASE =========
SUPABASE_URL="https://ilbihprkxcgsigvueeme.supabase.co"

# ⚠️ IMPORTANT: Utiliser SUPABASE_SERVICE_KEY (pas SUPABASE_KEY)
SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlocHJreGNnc2lndnVlZW1lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTEzMTQwNCwiZXhwIjoyMDY0NzA3NDA0fQ.Zf0EJbmP5ePGBZL5cY1tFP9FDRvJXDZ3x98zUS993GA"

# Connection PostgreSQL (optionnel pour sync directe)
PG_CONNECTION_STRING="postgresql://postgres.ilbihprkxcgsigvueeme:Bac2018mado%40@aws-0-eu-west-3.pooler.supabase.com:5432/postgres"
```

#### **🔑 Différence SUPABASE_KEY vs SUPABASE_SERVICE_KEY:**

| Variable | Rôle | Permissions |
|----------|------|-------------|
| `SUPABASE_KEY` (anon) | Client public | Lecture limitée par RLS |
| `SUPABASE_SERVICE_KEY` | Backend/Admin | **Bypass RLS** - Full access |

Pour Botlive, on utilise **`SUPABASE_SERVICE_KEY`** car le système a besoin de:
- ✅ Lire tous les prompts (toutes companies)
- ✅ Écrire dans tables système
- ✅ Bypass RLS pour performance

---

### **3️⃣ Vérification installation**

```bash
python tests/verify_botlive_ocr.py
```

**Résultat attendu:**
```
✅ PASS       | EasyOCR Installation
✅ PASS       | Payment Validator
✅ PASS       | Botlive Engine
✅ PASS       | RAG Hybrid Integration
✅ PASS       | Paramètres OCR

📈 Score: 5/5 (100%)
🎉 TOUS LES TESTS PASSÉS - SYSTÈME OPÉRATIONNEL
```

---

## 🧪 **TESTS CONVERSATIONNELS**

Une fois la vérification OK, lance les tests:

### **Test Light** (5 tours, client décidé)
```bash
python tests/conversation_simulator.py --scenario light
```

### **Test Medium** (12 tours, client hésitant)
```bash
python tests/conversation_simulator.py --scenario medium
```

### **Test Hardcore** (20 tours, client difficile)
```bash
python tests/conversation_simulator.py --scenario hardcore
```

### **Tous les tests d'un coup**
```bash
python tests/run_all_tests.py
```

---

## 🔧 **TROUBLESHOOTING**

### ❌ Erreur "No module named 'easyocr'"
```bash
pip install easyocr
```

### ❌ Erreur "SUPABASE_SERVICE_KEY requis"
Vérifie que ton `.env` contient bien **`SUPABASE_SERVICE_KEY`** (pas `SUPABASE_KEY`)

### ❌ Erreur "torch not found"
EasyOCR nécessite PyTorch:
```bash
pip install torch torchvision
```

### ⚠️ Installation lente d'EasyOCR
C'est normal - téléchargement des modèles OCR (~500MB). Attends 5-10 minutes.

### ❌ Erreur mémoire lors du chargement EasyOCR
Si RAM insuffisante (<8GB), configure:
```python
# Dans botlive_engine.py
self.payment_reader = easyocr.Reader(['fr'], gpu=False, verbose=False)
# Supprime 'en' pour économiser RAM
```

---

## 📊 **MÉTRIQUES ATTENDUES**

### **Performance OCR:**
- Temps extraction: **1-3s** par image
- Précision montants: **95%+**
- Précision numéros: **90%+**

### **Tests conversationnels:**
| Scénario | Tours | Temps total | Tokens | Coût |
|----------|-------|-------------|--------|------|
| Light | 5 | 20-30s | ~5k | $0.004 |
| Medium | 12 | 60-90s | ~15k | $0.012 |
| Hardcore | 20 | 120-180s | ~30k | $0.024 |

---

## ✅ **CHECKLIST FINALE**

Avant de passer en production:

- [ ] EasyOCR installé (`pip list | grep easyocr`)
- [ ] `.env` contient `SUPABASE_SERVICE_KEY`
- [ ] Vérification système: 5/5 tests passés
- [ ] Test Light: conversion réussie
- [ ] Test Medium: objections gérées
- [ ] Test Hardcore: cohérence maintenue
- [ ] Logs JSON activés
- [ ] Monitoring actif

---

## 🎯 **PROCHAINES ÉTAPES**

1. ✅ Installe EasyOCR
2. ✅ Configure `.env` avec `SUPABASE_SERVICE_KEY`
3. ✅ Vérifie système: `python tests/verify_botlive_ocr.py`
4. ✅ Lance test light: `python tests/conversation_simulator.py --scenario light`
5. 📊 Analyse résultats
6. 🚀 Déploie en production

---

## 📞 **SUPPORT**

**Erreurs fréquentes:** Voir section Troubleshooting ci-dessus
**Tests:** `tests/README.md`
**Documentation complète:** `AUTO_LEARNING_GUIDE.md`

---

**Version:** 1.0  
**Date:** 2025-01-20  
**Status:** 🟢 Ready for Testing

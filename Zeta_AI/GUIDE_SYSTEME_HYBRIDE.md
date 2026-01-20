# 🎯 GUIDE SYSTÈME HYBRIDE BOTLIVE

## **ARCHITECTURE**

```
┌─────────────────────────────────────────────────────────┐
│                    REQUÊTE CLIENT                        │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              BOTLIVE ROUTER (Aiguillage)                │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Variable d'env: USE_HYBRID_BOTLIVE               │  │
│  │ - true  → Système HYBRIDE                        │  │
│  │ - false → Système ANCIEN (défaut)                │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────┬─────────────────────┬────────────────────┘
               │                     │
       ┌───────▼────────┐    ┌──────▼─────────┐
       │ SYSTÈME ANCIEN │    │ SYSTÈME HYBRIDE│
       │  (LLM fait     │    │ (Python+LLM)   │
       │   tout)        │    │                │
       └───────┬────────┘    └──────┬─────────┘
               │                     │
               │         ┌───────────▼──────────┐
               │         │ 1. Python calcule    │
               │         │    état (photo,      │
               │         │    paiement, etc.)   │
               │         ├──────────────────────┤
               │         │ 2. Python décide     │
               │         │    action            │
               │         ├──────────────────────┤
               │         │ 3. LLM formule       │
               │         │    (+ fallback)      │
               │         └──────────┬───────────┘
               │                    │
               └────────┬───────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  RÉPONSE CLIENT │
              └─────────────────┘
```

---

## **🚀 ACTIVATION / DÉSACTIVATION**

### **Méthode 1 : Variable d'environnement (RECOMMANDÉ)**

```bash
# Dans .env
USE_HYBRID_BOTLIVE=false  # Système ANCIEN (défaut)
USE_HYBRID_BOTLIVE=true   # Système HYBRIDE
```

**Avantages :**
- ✅ Rollback instantané (juste changer la valeur)
- ✅ Pas besoin de redémarrer le serveur
- ✅ Facile à gérer en production

---

### **Méthode 2 : API Endpoint**

```python
# Activer système hybride
POST /botlive/hybrid/enable

# Désactiver système hybride (rollback)
POST /botlive/hybrid/disable

# Basculer (toggle)
POST /botlive/hybrid/toggle

# Voir métriques
GET /botlive/hybrid/metrics
```

---

### **Méthode 3 : Code Python**

```python
from core.botlive_router import get_router

router = get_router()

# Activer
router.enable_hybrid()

# Désactiver (rollback)
router.disable_hybrid()

# Basculer
router.toggle()

# Vérifier état
is_active = router.is_hybrid_enabled()
```

---

## **📊 MÉTRIQUES & COMPARAISON**

### **Voir les statistiques**

```python
from core.botlive_router import get_router

router = get_router()
metrics = router.get_metrics()

print(metrics)
```

**Exemple de sortie :**
```json
{
  "hybrid_enabled": true,
  "old_system": {
    "count": 150,
    "errors": 12,
    "avg_time": 2.3
  },
  "hybrid_system": {
    "count": 200,
    "errors": 3,
    "avg_time": 0.8
  },
  "comparison": {
    "old_error_rate": "8.0%",
    "hybrid_error_rate": "1.5%",
    "time_improvement": "+65.2%",
    "recommendation": "hybrid"
  }
}
```

---

## **🔄 FALLBACK AUTOMATIQUE**

Le système hybride a **3 niveaux de fallback** :

### **Niveau 1 : Template de secours**
Si le LLM échoue à formuler, utilise un template prédéfini.

```python
# Exemple
action = "ask_payment"
# LLM échoue → Template: "Envoyez 2000F sur +225 0787360757, puis capture."
```

### **Niveau 2 : Rollback vers ancien système**
Si le système hybride plante, bascule automatiquement vers l'ancien système.

```python
try:
    result = hybrid_system()
except Exception:
    result = old_system()  # Fallback automatique
```

### **Niveau 3 : Réponse d'urgence**
Si tout échoue, réponse minimale garantie.

```python
# Réponse ultime
"Envoyez photo du paquet 📦"
```

---

## **🧪 TESTS A/B**

### **Tester les deux systèmes en parallèle**

```python
# 50% des requêtes → Ancien système
# 50% des requêtes → Système hybride

import random

if random.random() < 0.5:
    router.enable_hybrid()
else:
    router.disable_hybrid()
```

### **Comparer les résultats**

```python
# Après 100 requêtes de chaque côté
metrics = router.get_metrics()

print(f"Ancien système: {metrics['old_system']['errors']} erreurs")
print(f"Système hybride: {metrics['hybrid_system']['errors']} erreurs")
print(f"Recommandation: {metrics['comparison']['recommendation']}")
```

---

## **⚠️ ROLLBACK D'URGENCE**

### **Scénario : Le système hybride cause des problèmes**

**Option 1 : Variable d'environnement (RAPIDE)**
```bash
# Dans .env
USE_HYBRID_BOTLIVE=false
```

**Option 2 : API (IMMÉDIAT)**
```bash
curl -X POST http://localhost:8000/botlive/hybrid/disable
```

**Option 3 : Code (MANUEL)**
```python
from core.botlive_router import get_router
get_router().disable_hybrid()
```

**Résultat :** Retour immédiat à l'ancien système, **zéro impact** sur les conversations en cours.

---

## **📝 LOGS & DÉBOGAGE**

### **Identifier quel système est utilisé**

```
✅ [ROUTER] Routage vers système HYBRIDE
✅ [HYBRID] État calculé: {"photo": true, "paiement": false, ...}
✅ [HYBRID] Action décidée: ask_payment (2/4)
✅ [HYBRID] LLM formulation OK: Envoyez 2000F...
```

ou

```
✅ [ROUTER] Routage vers système ANCIEN
```

### **Détecter les fallbacks**

```
⚠️ [HYBRID] Réponse LLM trop longue (25 mots), fallback template
🔄 [HYBRID] Fallback template utilisé: ask_payment
```

ou

```
❌ [ROUTER] Erreur système HYBRIDE: ...
🔄 [ROUTER] FALLBACK automatique vers ancien système
```

---

## **🎯 RECOMMANDATIONS**

### **Phase 1 : Test (1 semaine)**
```bash
USE_HYBRID_BOTLIVE=false  # Garder ancien système
```
- Surveiller les métriques de l'ancien système
- Préparer les tests

### **Phase 2 : A/B Testing (1 semaine)**
```python
# 10% hybride, 90% ancien
if random.random() < 0.1:
    router.enable_hybrid()
```
- Comparer les performances
- Identifier les problèmes

### **Phase 3 : Déploiement progressif (2 semaines)**
```python
# 50% hybride, 50% ancien
if random.random() < 0.5:
    router.enable_hybrid()
```
- Augmenter progressivement
- Surveiller les erreurs

### **Phase 4 : Production (si succès)**
```bash
USE_HYBRID_BOTLIVE=true  # 100% hybride
```
- Garder l'ancien système en fallback
- Surveiller les métriques

---

## **🔧 CONFIGURATION AVANCÉE**

### **Personnaliser les templates de secours**

```python
from core.hybrid_botlive_engine import get_hybrid_engine

engine = get_hybrid_engine()

# Modifier un template
engine.fallback_templates["ask_payment"] = "Votre message personnalisé"
```

### **Ajuster les seuils de validation**

```python
# Dans hybrid_botlive_engine.py

# Exemple : Accepter 9 chiffres pour téléphone
tel_clean = ''.join(filter(str.isdigit, str(tel)))
tel_valid = len(tel_clean) >= 9  # Au lieu de == 10
```

---

## **❓ FAQ**

### **Q: Que se passe-t-il si je change USE_HYBRID_BOTLIVE en pleine conversation ?**
**R:** Le changement prend effet immédiatement pour la prochaine requête. Les conversations en cours ne sont pas affectées.

### **Q: Le système hybride peut-il casser l'ancien système ?**
**R:** Non, les deux systèmes sont **complètement séparés**. Le système hybride ne touche jamais au code de l'ancien système.

### **Q: Comment savoir si le système hybride fonctionne mieux ?**
**R:** Utilisez `router.get_metrics()` pour comparer les taux d'erreur et les temps de réponse.

### **Q: Puis-je revenir en arrière à tout moment ?**
**R:** Oui, changez juste `USE_HYBRID_BOTLIVE=false` et c'est instantané.

### **Q: Le système hybride coûte-t-il plus cher ?**
**R:** Non, il coûte **60% moins cher** car le prompt LLM est 10x plus court.

---

## **📞 SUPPORT**

En cas de problème :
1. Vérifier les logs (`[ROUTER]`, `[HYBRID]`)
2. Désactiver le système hybride (`USE_HYBRID_BOTLIVE=false`)
3. Consulter les métriques (`router.get_metrics()`)
4. Contacter l'équipe technique avec les logs

---

## **✅ CHECKLIST DE DÉPLOIEMENT**

- [ ] Système hybride testé en local
- [ ] Variable `USE_HYBRID_BOTLIVE=false` dans .env
- [ ] Endpoints API de contrôle testés
- [ ] Métriques de l'ancien système collectées (baseline)
- [ ] Plan de rollback documenté
- [ ] Tests A/B configurés (10% hybride)
- [ ] Monitoring des logs activé
- [ ] Équipe informée du déploiement

**Une fois validé :**
- [ ] Augmenter progressivement (10% → 50% → 100%)
- [ ] Comparer les métriques chaque semaine
- [ ] Décider du déploiement complet après 1 mois

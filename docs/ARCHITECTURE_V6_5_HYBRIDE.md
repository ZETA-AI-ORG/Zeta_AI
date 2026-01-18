# 🏗️ ARCHITECTURE V6.5 HYBRIDE - Plan d'Alignement et Amélioration

## 📋 RÉSUMÉ EXÉCUTIF

**V6.5 = V6 (solide) + Embeddings (filet de sécurité) + Suggestions (amélioration continue)**

| Priorité | Layer | Fonction | Confiance |
|----------|-------|----------|-----------|
| 1 | V6 Prefilter | Paiement/Contact/SAV | 0.93-0.98 |
| 2 | V5 Keywords | Prix/Livraison/Achat/Catalogue | 0.90-0.95 |
| 3 | **Embeddings V6.5** | Edge cases sémantiques | 0.75-0.88 |
| 4 | SetFit ML | Fallback ultime | Variable |

---

## 🎯 OBJECTIFS

### ✅ Ce qui est PRÉSERVÉ (100% intact)
- **V6 Prefilter** : Paiement (Wave/MTN/Orange), Contact (numéro/appeler), Tracking (mon colis), Problèmes (abîmé/cassé)
- **V5 Keywords** : Prix (combien/tarif), Catalogue (produits/vendez), Livraison (livrez/zone), Acquisition (commander/acheter)
- **SetFit ML** : Modèle entraîné V5 (4 pôles)

### 🆕 Ce qui est AJOUTÉ (Layer 3)
- **Embeddings sémantiques** : Capture les variantes non couvertes par keywords
- **Seuil conservateur** : 0.75 minimum (en dessous = ignore)
- **Confiance plafonnée** : 0.88 maximum (ne dépasse jamais V6/V5)
- **Logging suggestions** : Cas >= 0.82 loggés pour review humaine

---

## 📐 ARCHITECTURE CASCADE

```
Message utilisateur
    ↓
┌─────────────────────────────────────────┐
│  LAYER 1 : Prefilter V6 (Déterministe) │ ← PRIORITÉ MAX
│  • Paiement/Contact → REASSURANCE       │
│  • Tracking/Problème → SAV_SUIVI        │
│  • Confiance : 0.93-0.98                │
└─────────────────────────────────────────┘
    ↓ (si aucun match)
┌─────────────────────────────────────────┐
│  LAYER 2 : Prefilter V5 (Keywords)     │ ← GARDE-FOU
│  • Prix/Catalogue → SHOPPING            │
│  • Livraison → REASSURANCE              │
│  • Achat → ACQUISITION                  │
│  • Confiance : 0.90-0.95                │
└─────────────────────────────────────────┘
    ↓ (si aucun match)
┌─────────────────────────────────────────┐
│  LAYER 3 : Embeddings V6.5 (NOUVEAU)   │ ← FILET SÉCURITÉ
│  • Similarité cosine vs prototypes      │
│  • Seuil : 0.75 (conservateur)          │
│  • Confiance : 0.75-0.88 (plafonnée)    │
│  • LOG si conf >= 0.82 → Suggestion     │
└─────────────────────────────────────────┘
    ↓ (si aucun match ou conf < 0.75)
┌─────────────────────────────────────────┐
│  LAYER 4 : SetFit ML (Fallback)        │ ← EXISTANT
│  • Modèle entraîné V5                   │
│  • Confiance variable                   │
└─────────────────────────────────────────┘
```

---

## 📁 FICHIERS CRÉÉS

### Module Embeddings V6.5
```
core/embeddings_v6_5/
├── __init__.py              # Exports du module
├── prototypes.py            # 32 prototypes (8 max/intent)
├── semantic_filter.py       # SemanticFilterV65 (SentenceTransformer)
└── suggestion_logger.py     # SuggestionLoggerV65 (JSONL)
```

### Scripts & Tests
```
scripts/
└── review_embeddings_suggestions.py  # Dashboard review hebdo

tests/
└── test_embeddings_v6_5.py           # Tests non-régression
```

### Logs
```
logs/
└── embeddings_suggestions_v6_5.jsonl  # Suggestions à reviewer
```

---

## 🛡️ RÈGLES STRICTES

### INTERDICTIONS 🚫
```python
# ❌ JAMAIS modifier V6 prefilter (paiement/contact/SAV)
# ❌ JAMAIS modifier V5 prefilter (prix/livraison/achat)
# ❌ JAMAIS auto-learning (modification automatique keywords)
# ❌ JAMAIS seuil embeddings < 0.75 (trop de faux positifs)
# ❌ JAMAIS confiance embeddings > 0.88 (ne pas dépasser V6)
# ❌ JAMAIS plus de 8 prototypes/intent (surcharge mémoire)
# ❌ JAMAIS charger modèle à chaque requête (cache obligatoire)
```

### OBLIGATIONS ✅
```python
# ✅ TOUJOURS tester cascade : V6 → V5 → Embeddings → SetFit
# ✅ TOUJOURS logger si similarité >= 0.82
# ✅ TOUJOURS inclure prototype matché dans logs
# ✅ TOUJOURS vérifier non-régression dataset 130 questions
# ✅ TOUJOURS gérer cache embeddings (performance)
# ✅ TOUJOURS tracer layer utilisé (debug)
```

---

## 📊 PROTOTYPES V6.5 (32 total)

### REASSURANCE (8 prototypes)
- Smalltalk étendu : "Comment vous portez-vous aujourd'hui"
- Localisation variantes : "Vous êtes installés dans quel coin"
- Horaires variantes : "Vous fermez vers quelle heure le soir"
- Confiance/Légitimité : "Vous êtes une entreprise sérieuse"

### SHOPPING (8 prototypes)
- Prix variantes : "Ça se vend à quel montant"
- Stock variantes : "Il vous en reste encore"
- Catalogue variantes : "Qu'est-ce que vous proposez comme choix"
- Comparaison : "Quelle est la différence entre les deux"

### ACQUISITION (8 prototypes)
- Commande variantes : "Je souhaite acquérir ce produit"
- Quantité variantes : "Mettez-m'en trois s'il vous plaît"
- Confirmation : "C'est bon je valide"

### SAV_SUIVI (8 prototypes)
- Tracking variantes : "Je veux savoir où en est ma livraison"
- Problème variantes : "Ce n'est pas ce que j'avais demandé"
- Réclamation : "Je voudrais faire une réclamation"

---

## 🔧 MAINTENANCE

### Review Hebdomadaire (30 min)
```bash
# Analyser les suggestions
python scripts/review_embeddings_suggestions.py

# Approuver un pattern (à ajouter en V6/V5)
python scripts/review_embeddings_suggestions.py --approve "message exact"

# Rejeter un faux positif
python scripts/review_embeddings_suggestions.py --reject "message exact"
```

### Workflow d'amélioration
1. **Semaine N** : Layer 3 capture edge case, log suggestion
2. **Review** : Humain valide le pattern (approve/reject)
3. **Si approved** : Ajouter keyword dans V6 ou V5
4. **Semaine N+1** : Le cas est capturé par V6/V5 (conf plus haute)

---

## 📈 MÉTRIQUES ATTENDUES

### Objectifs (3 mois)
| Métrique | Cible |
|----------|-------|
| Couverture Layer 3 | 5-10% des requêtes |
| Précision Layer 3 | >= 85% |
| Faux positifs | < 2% |
| Temps réponse | +15ms max |
| Suggestions/semaine | 10-20 cas |
| Temps review | 30min/semaine |

### KPIs de succès
- ✅ V6 coverage maintenu à 100%
- ✅ V5 coverage maintenu à ~80%
- ✅ Layer 3 capture 5-8% cas additionnels
- ✅ 0 régression sur dataset 130
- ✅ Temps review < 30min/semaine

---

## ✅ CHECKLIST DÉPLOIEMENT

### Phase 1 : Préparation (J+0)
- [x] Créer module `core/embeddings_v6_5/`
- [x] Installer dépendance : `pip install sentence-transformers==2.2.2`
- [x] Créer dossiers : `cache/`, `logs/`

### Phase 2 : Implémentation (J+1)
- [x] `prototypes.py` avec 32 prototypes validés
- [x] `semantic_filter.py` avec cache et seuils
- [x] `suggestion_logger.py` pour logging JSONL
- [x] Intégration dans `route_botlive_intent()`

### Phase 3 : Tests (J+2)
- [ ] Tester sur dataset 130 questions
- [ ] Vérifier aucune régression V6/V5
- [ ] Vérifier Layer 3 activé uniquement si V6/V5 miss
- [ ] Vérifier logs suggestions créés

### Phase 4 : Déploiement (J+3)
- [ ] Merge en staging
- [ ] Monitor pendant 7 jours
- [ ] Review logs suggestions (1x/semaine)
- [ ] Si stable → merge en prod

---

## 🚀 COMMANDES UTILES

```bash
# Installer sentence-transformers
pip install sentence-transformers==2.2.2

# Tester le batch 130 questions
python tests/botlive_router_eval_120.py

# Lancer les tests unitaires V6.5
pytest tests/test_embeddings_v6_5.py -v

# Review des suggestions
python scripts/review_embeddings_suggestions.py

# Invalider le cache embeddings (si prototypes modifiés)
python -c "from core.embeddings_v6_5 import SemanticFilterV65; SemanticFilterV65().invalidate_cache()"
```

---

## 📝 NOTES IMPORTANTES

1. **Pas d'auto-learning** : Les suggestions sont loggées mais jamais appliquées automatiquement
2. **Seuils conservateurs** : 0.75 min évite les faux positifs, 0.88 max ne dépasse jamais V6/V5
3. **Fallback gracieux** : Si `sentence-transformers` non installé, Layer 3 est simplement ignoré
4. **Performance** : Cache embeddings évite recalcul à chaque requête (~15ms overhead)
5. **Traçabilité** : Chaque routing indique le layer utilisé dans `router_debug`

---

*Document généré le 30/12/2025 - Architecture V6.5 Hybride*

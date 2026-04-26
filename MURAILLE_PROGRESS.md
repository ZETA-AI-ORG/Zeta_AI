# 🧱 MURAILLE DE CHINE — PROGRESS NOTES

> Session nocturne : Vagues 1 + 2 terminées en autonomie.
> À lire au réveil pour savoir où on en est et ce qu'il reste à faire.

---

## ✅ CE QUI EST FAIT (code prêt, pas encore déployé)

### Vague 1 — Prompts scindés en 2 fichiers
- `prompts/prompt_core_immutable.md` — **5 531 tokens**, **0 placeholder**, **0 marker d'injection runtime**. C'est la "boîte de marbre" universelle partagée par toutes les boutiques.
- `prompts/prompt_shop_dynamic.md` — découpé en **4 sous-zones explicitement balisées** :
  - `[[ZONE_2_SHOP_START/END]]` : config boutique (bot_name, wave_number, support, etc.)
  - `[[ZONE_3_CATALOGUE_START/END]]` : markers `[[PRODUCT_INDEX]]` + `[CATALOGUE_START/END]`
  - `[[ZONE_4_HISTORY_START/END]]` : `{conversation_history}` + `{query}`
  - `[[ZONE_5_SESSION_START/END]]` : `{current_phase}` + tous les `{*_block}` (panier, prix, erreurs)

### Vague 2A + 2A bis — Tri APPEND-ONLY des produits
Corrigé pour garantir qu'un nouveau produit s'ajoute TOUJOURS en fin de liste (et pas au milieu / début qui casserait le cache) :
- `core/simplified_prompt_system.py:297-306` — tri `product_id ASC` dans `_build_product_index_block`
- `core/botlive_rag_hybrid.py:335-339` — remplacé le tri alphabétique par nom (qui était **CATASTROPHIQUE** pour le cache : ajouter "Biberons" devant "Couches/Tétines" invalidait tout) par tri `product_id ASC`

### Vague 2B — Loader "Muraille"
Nouveau fichier `core/prompt_static_loader.py` qui expose :
- `get_immutable_core()` : lit `prompt_core_immutable.md` UNE SEULE FOIS, cache mémoire process-wide, **aucune transformation** (pas de `.format()`/`.replace()`). Le CORE reste byte-identique inter-boutiques.
- `get_shop_dynamic_template()` : lit `prompt_shop_dynamic.md`, cache mémoire.
- `is_muraille_enabled()` : lit `os.getenv("PROMPT_MURAILLE_ENABLED")`.
- `reset_caches()` : utilitaire dev/tests.

### Vague 2C — Branchement dans `build_prompt()`
`core/simplified_prompt_system.py` modifié :
- Imports ajoutés (ligne 30).
- `build_prompt` branché sur `is_muraille_enabled()` (ligne 640+) :
  - Si **flag ON** → `static_prompt = core_immutable + "\n\n" + shop_template` puis injections PRODUCT_INDEX + CATALOGUE (dans la zone shop uniquement) puis `_safe_format` (qui ne matchera aucun placeholder dans le CORE).
  - Si **flag OFF** → comportement legacy inchangé (`prompt_universel_v2.md` monolithique).

**Rollback trivial** : il suffit de remettre `PROMPT_MURAILLE_ENABLED=false` ou de supprimer la variable. Aucun code legacy n'a été retiré.

---

## 🚀 CE QUI RESTE À FAIRE (demain)

### 1. Activer le flag en staging / simulator
```bash
# Sur ta machine locale (.env à la racine) ou via export :
PROMPT_MURAILLE_ENABLED=true
```
Puis lancer le simulator Jessica, faire une conversation de ~7 tours.

### 2. Mesurer le cache avec `cache_probe.py`
Tu as déjà `tests/cache_probe.py`. Lance-le après un run complet pour voir le `cached_tokens` par tour.
Cible :
- **Tour 1 de la 1ère boutique** : ~0% (cache pas encore chaud, normal)
- **Tour 2+ même boutique** : **>90%** cached (5 531 CORE + ~800 SHOP + ~800 CATALOGUE cachés)
- **Tour 1 d'une 2e boutique** : **~70%** cached (CORE déjà chaud grâce à la 1ère)

### 3. Déployer sur le VPS (via `.\deploy.ps1`)
**⚠️ IMPORTANT** : Sur le VPS, il faut activer le flag dans le `.env` du serveur. Comme tu ne dois pas toucher directement au `.env` VPS (règle), fais-le manuellement en SSH OU ajoute-le via ton panneau d'admin Contabo.

Fichiers à committer :
- `prompts/prompt_core_immutable.md` (nouveau)
- `prompts/prompt_shop_dynamic.md` (nouveau)
- `core/prompt_static_loader.py` (nouveau)
- `core/simplified_prompt_system.py` (modifié)
- `core/botlive_rag_hybrid.py` (modifié)

---

## 📊 GAIN ATTENDU

| Métrique | Avant (actuel) | Après (Muraille ON) |
|---|---:|---:|
| Cache tour 1 (nouvelle conv, boutique déjà connue) | 0% | ~70% |
| Cache tour 2+ (même conv) | 0% (bug `{query}` ligne 415) | **~92-94%** |
| Cache inter-boutiques | 0% | **~70% du CORE** partagé |
| Coût par 1M tokens | plein tarif | ~25% du plein tarif sur zone cachée |

**Économie réaliste** : avec 1000 boutiques × 10 convs/jour × 5 tours/conv = 50 000 requêtes/jour. Économie ~0,75× × 5 500 tok × 50 000 = **~200 M tokens/jour évités**. À toi de traduire en € avec ton tarif OpenRouter.

---

## 🔮 CHANTIERS FUTURS (todo list)

### Priority MEDIUM — Optimisation CATALOGUE_BLOCK
Le fichier `core/catalogue_block_builder.py` génère des blocs verbeux type :
```
## FORMATS_DE_VENTE
- (format) -> lot_100 | canonical=lot_100 | min_order=1
## REQUIRED_CHOICES (BLOCKERS)
- taille (Obligatoire) : XL(16-18KG), XXL(19-21KG)
## AUTO_RULES (DEDUCTIONS_SURES)
- pricing_mode: per_format
- sales_target: retail
...
```
Compacter pourrait gagner 200-400 tok par requête. Exemple de compactage :
```
FORMATS: lot_100(min=1)
CHOICES(req): taille=[XL(16-18KG),XXL(19-21KG)]
RULES: pricing=per_format, target=retail
```

### Priority LOW — Audit cache production
Ajouter un endpoint `/admin/cache-stats` qui lit `results/openrouter_usage.jsonl` sur le VPS et agrège :
- cache_hit_rate moyen par jour
- cache_hit_rate par boutique
- tokens économisés (estimé)

---

## ⚠️ POINTS D'ATTENTION

1. **Le CORE ne doit JAMAIS être modifié sans vider le cache mémoire Gemini** (attendre ~5 min d'expiration TTL, ou changer la version du prompt pour forcer invalidation).

2. **Tri produits append-only** = si tu importes un ancien catalogue qui utilise des IDs au format différent (ex: migration UUIDs vers slugs), l'ordre changera → cache perdu une fois. Prévois un dump-restore catalogue lors de la migration.

3. **Les 2 fichiers `.md` sont maintenant le vrai prompt de prod**. L'ancien `prompt_universel_v2.md` reste utilisé si flag OFF. Ne pas le supprimer avant la validation en prod.

4. **Caches process-wide** : si tu hot-reload le serveur Uvicorn, les caches `_CORE_CACHE` et `_SHOP_CACHE` se réinitialisent automatiquement. Aucune action requise.

# DIAGNOSTIC COMPLET — Prix et Catalogue Block (21 mars 2026)

## COMMANDE VPS : Rechercher un product_id dans les fichiers Python

```bash
python - <<'PY'
import os, json

TARGET = "prod_mmzky01s_zkei9h"
ROOTS = [".", "./data", "./app/data", "/data"]

def short(obj, n=4000):
    s = json.dumps(obj, ensure_ascii=False, indent=2)
    return s[:n] + ("\n...TRUNCATED..." if len(s) > n else "")

def walk(node, path="root"):
    hits = []
    if isinstance(node, dict):
        vals = [str(v) for v in node.values() if not isinstance(v, (dict, list))]
        if TARGET in vals:
            hits.append((path, node))
        for k, v in node.items():
            hits.extend(walk(v, f"{path}.{k}"))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            hits.extend(walk(v, f"{path}[{i}]"))
    return hits

for root in ROOTS:
    if not os.path.exists(root):
        continue
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    obj = json.load(f)
            except Exception:
                continue
            hits = walk(obj)
            if hits:
                print("\n" + "=" * 120)
                print("FILE:", os.path.abspath(fp))
                print("HITS:", len(hits))
                print("-" * 120)
                for path, node in hits:
                    print("PATH:", path)
                    if isinstance(node, dict):
                        print("KEYS:", list(node.keys())[:40])
                    print(short(node))
                    print("-" * 120)
PY
```

Alternative rapide (grep) :
```bash
grep -R "prod_mmzky01s_zkei9h" /home/zetaadmin/CHATBOT2.0/app/data /data 2>/dev/null
```

---

## RESUME DU DIAGNOSTIC

### Symptomes observes (logs du 21 mars 2026 ~02h18)

1. `CATALOGUE_BLOCK` toujours vide (`chars=0`) alors que `PRODUCT_INDEX` trouve bien le produit
2. `SEND_PRICE_LIST` echoue : `No price data generated for pid=prod_mmzky01s_zkei9h variant=Pression`
3. `PRICE_GATE` bloque le calcul pre-LLM : `SPECS manquant (taille non collectee)`
4. Jessica repond une phrase vague sans aucun prix

### Verdict

- **Jessica (LLM)** : PAS en cause. Elle detecte correctement l'intention, appelle `SEND_PRICE_LIST` avec le bon `product_id` et `variant`.
- **Backend Python** : EN CAUSE sur 1 cause racine unique qui provoque les 3 symptomes.

---

## CAUSE RACINE UNIQUE — Le vtree (v) est absent des donnees Supabase

### Le flux de donnees actuel

```
Frontend (ProductFormPremium)
  |
  |---> Supabase company_catalogs_v2 (via useCatalog.ts)
  |       -> Contient : name, description, variants[], priceMatrix{}, subVariantsByIndex[][]
  |       -> NE contient PAS : v (vtree), ui_state complet, canonical_units
  |
  +---> N8N webhook -> Python endpoint sync-local-and-upsert-botlive-catalogue-block-deepseek
          -> Sauvegarde en fichier JSON local : /data/catalogs/{company_id}.json
          -> Contient TOUT : v (vtree), ui_state, canonical_units, pricing_strategy
```

### Le loader au moment du chat

```python
# core/company_catalog_v2_loader.py - get_company_catalog_v2() - ligne 232
# --- PRIORITY: Supabase FIRST, local file as FALLBACK only ---
```

1. Le loader lit Supabase `company_catalogs_v2` EN PREMIER (limit(1), trie par updated_at desc)
2. Supabase retourne un dict -> le loader le prend et s arrete
3. Ce dict n a PAS de `v` (vtree) -> toute logique dependant du vtree echoue
4. Le fichier JSON local (qui A le vtree) n est JAMAIS consulte car Supabase a repondu

### Consequences en cascade

| Composant | Ce qui echoue | Fichier | Ligne |
|-----------|---------------|---------|-------|
| `_build_product_context_block` | `vtree = catalog_v2.get("v")` -> None -> return "" | simplified_prompt_system.py | 712 |
| `_inject_between_catalogue_markers` | Recoit "" -> markers restent vides | simplified_prompt_system.py | 1663 |
| `_generate_price_list_for_tool_call` | `vtree = selected_catalog.get("v")` -> {} -> return ("", []) | simplified_rag_engine.py | 434-436 |
| `format_price_list` | Jamais appele (vtree vide) | catalog_formatter.py | 416 |

### Pourquoi PRICE_GATE n est PAS le probleme

```python
# simplified_rag_engine.py ligne 2896-2900
# GATE: bloquer le prix si SPECS manquant (produit_details vide = taille non collectee).
if not str(getattr(_st_price_gate, "produit_details", "") or "").strip():
    pre_llm_price_calc_allowed = False
    print("[PRICE_GATE] Prix bloque: SPECS manquant")
```

C est le comportement CORRECT : le calcul final pre-LLM exige la taille.
Le `SEND_PRICE_LIST` (post-LLM, ligne 5766+) est un flow SEPARE qui ne passe PAS par PRICE_GATE.
Il echoue UNIQUEMENT parce que le vtree est absent.

---

## FICHIERS AUDITES

### 1. core/company_catalog_v2_loader.py
- `get_company_catalog_v2()` (ligne 200) : Supabase first, local fallback. Retourne UN seul produit.
- `get_company_product_catalog_v2()` (ligne 145) : Appelle get_company_catalog_v2_container -> meme chemin.
- `_load_catalog_from_local_file()` (ligne 113) : Lit le JSON local correctement. JAMAIS appele quand Supabase repond.

### 2. core/simplified_prompt_system.py
- `build_prompt()` (ligne 1140+) : Charge catalog_v2 via loader, puis _build_product_context_block().
- `_build_product_context_block()` (ligne 668) : Cherche v dans le dict. Si absent -> return "".
- `_inject_between_catalogue_markers()` (ligne 634) : Injecte le contenu entre [CATALOGUE_START]...[CATALOGUE_END].
- Multi-product selection (ligne 1164-1290) : Tente de resoudre le mono-produit actif. Fonctionne mais recoit un dict sans vtree.

### 3. core/simplified_rag_engine.py
- `SEND_PRICE_LIST` handler (ligne 5766-5868) : Appelle _generate_price_list_for_tool_call().
- `_generate_price_list_for_tool_call()` (ligne 389) : Charge catalog via get_company_product_catalog_v2(), lit v -> vide -> return ("", []).
- `PRICE_GATE` (ligne 2896) : Bloque calcul final pre-LLM si SPECS manquant. Comportement CORRECT et INDEPENDANT.
- `catalogue_reference_block_override` (ligne 2991-3073) : Construit un bloc catalogue texte depuis vtree. Aussi vide quand vtree absent.

### 4. routes/catalog_v2.py
- `sync_local_and_upsert_botlive_catalogue_block_deepseek()` (ligne 851) :
  - Sauvegarde JSON local avec vtree (OK)
  - Upsert PRODUCT_INDEX dans le prompt Supabase (OK)
  - Deliberement vide les marqueurs CATALOGUE (ligne 1018-1020) :
    ```python
    # IMPORTANT: we do NOT persist catalogue content inside the Supabase prompt.
    updated_prompt = _clear_catalogue_markers(existing_prompt)
    ```
  - Ceci est VOULU car le contenu catalogue doit etre injecte au runtime

### 5. core/catalog_formatter.py
- `format_price_list()` (ligne 416) : Fonctionne correctement SI vtree est fourni.
- Gere 4 cas : unit connu, spec connu, les deux, aucun.
- Jamais appele dans le bug actuel car le vtree est absent en amont.

### 6. zeta-ai-vercel/src/pages/Zetaflowcatalogueunified.tsx (Frontend)
- `handleSave()` : Destructure `_builtVTree` hors de clean, puis sauvegarde clean (SANS vtree) vers Supabase.
- Envoie `_builtVTree` comme v dans le payload N8N separement.
- C EST ICI QUE LE VTREE EST PERDU POUR SUPABASE.

---

## PLAN DE CORRECTION (3 axes, par ordre de priorite)

### AXE 1 — Sauver le vtree dans Supabase (Frontend) [PRIORITE 1]

**Fichier** : `zeta-ai-vercel/src/pages/Zetaflowcatalogueunified.tsx`
**Ligne** : ~500 (construction du payload)
**Action** : Inclure _builtVTree et _builtUiState dans le payload sauve vers Supabase

```typescript
// AVANT (actuel)
const payload: any = {
    ...clean,
    price: publicPrice || 0,
    imageUrls: publicImages,
    description: publicDescription,
};

// APRES (fix)
const payload: any = {
    ...clean,
    price: publicPrice || 0,
    imageUrls: publicImages,
    description: publicDescription,
    v: _builtVTree && Object.keys(_builtVTree).length > 0 ? _builtVTree : undefined,
    ui_state: _builtUiState && Object.keys(_builtUiState).length > 0
        ? { ..._builtUiState, images: publicImages }
        : undefined,
    canonical_units: (clean as any).canonical_units || undefined,
    pricing_strategy: catMode === "advanced" ? "UNIT_AS_ATOMIC" : undefined,
};
```

**Risque** : Faible. Ajoute des champs au JSON sans casser les existants.
**Impact** : Le loader Supabase trouvera v -> tout le pipeline fonctionne.

### AXE 2 — Loader multi-produit (Backend Python) [PRIORITE 2]

**Fichier** : `core/company_catalog_v2_loader.py`
**Ligne** : 240-248 (get_company_catalog_v2)
**Probleme** : limit(1) ne retourne qu un seul produit.
**Action** : Retourner TOUS les produits actifs dans un container {"products": [...]}

```python
# AVANT
resp = (
    client.table("company_catalogs_v2")
    .select("catalog")
    .eq("company_id", cid)
    .eq("is_active", True)
    .order("updated_at", desc=True)
    .limit(1)
    .execute()
)

# APRES
resp = (
    client.table("company_catalogs_v2")
    .select("catalog")
    .eq("company_id", cid)
    .eq("is_active", True)
    .order("updated_at", desc=True)
    .execute()  # PAS de limit(1)
)
data = getattr(resp, "data", None) or []
if len(data) == 1:
    catalog = data[0].get("catalog")
    supabase_result = catalog if isinstance(catalog, dict) else None
elif len(data) > 1:
    products = []
    for row in data:
        cat = row.get("catalog")
        if isinstance(cat, dict):
            pid = str(cat.get("product_id") or "").strip()
            pname = str(cat.get("name") or cat.get("product_name") or "").strip()
            products.append({"product_id": pid, "product_name": pname, "catalog_v2": cat})
    if products:
        supabase_result = {"products": products}
```

**Risque** : Moyen. Impacte tous les chemins qui utilisent le loader.
**Dependance** : AXE 1 doit etre fait d abord (sinon les produits Supabase n ont toujours pas de vtree).

### AXE 3 — Fallback local quand Supabase n a pas de vtree (Backend Python) [PRIORITE 3]

**Fichier** : `core/company_catalog_v2_loader.py`
**Ligne** : 264 (apres le check Supabase)
**Action** : Si le resultat Supabase n a pas de v et que le fichier local en a un, preferer le local.

```python
if isinstance(supabase_result, dict):
    has_vtree = bool(supabase_result.get("v"))
    if not has_vtree and isinstance(supabase_result.get("products"), list):
        has_vtree = any(
            isinstance((p.get("catalog_v2") or {}).get("v"), dict)
            for p in supabase_result.get("products", [])
            if isinstance(p, dict)
        )
    if not has_vtree:
        local = _load_catalog_from_local_file(cid)
        if isinstance(local, dict):
            local = _unwrap_catalog_shape(local)
            local_has_v = bool(local.get("v")) or (
                isinstance(local.get("products"), list) and any(
                    isinstance((p.get("catalog_v2") or {}).get("v"), dict)
                    for p in local.get("products", []) if isinstance(p, dict)
                )
            )
            if local_has_v:
                _CACHE[cid] = (now + ttl_s, local)
                return local
```

**Risque** : Faible. N intervient que quand Supabase n a pas de vtree.
**Impact** : Filet de securite pour les produits existants non re-sauvegardes.

---

## ORDRE D EXECUTION RECOMMANDE

1. **AXE 1** (Frontend) : modifier handleSave pour inclure v dans Supabase -> deploy Vercel
2. **AXE 3** (Backend) : ajouter fallback local dans le loader -> deploy.ps1
3. Re-sauvegarder le produit test depuis le formulaire pour que le vtree soit ecrit dans Supabase
4. Tester : `donnes les prix des pressions` -> doit afficher la table prix
5. **AXE 2** (Backend) : loader multi-produit -> deploy.ps1 (optionnel, peut attendre)

## VERIFICATION POST-FIX

Sur le VPS, lancer :
```bash
curl http://localhost:8002/catalog-v2/sync-local-and-upsert-botlive-catalogue-block-deepseek \
  -X POST -H "Content-Type: application/json" \
  -d '{"company_id":"W27PwOPiblP8TlOrhPcjOtxd0cza","catalog":{},"product_id":"test"}' \
  2>/dev/null | python -m json.tool
```

Puis tester en chat :
```
donnes les prix des pressions
```

Attendu :
- `CATALOGUE_BLOCK chars > 0`
- `SEND_PRICE_LIST` retourne une table prix
- Jessica affiche les prix formatees

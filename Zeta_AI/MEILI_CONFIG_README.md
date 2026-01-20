# 🔧 Configuration MeiliSearch Scalable

## 📋 Description

Script de configuration automatique pour MeiliSearch, **scalable de 1 à 1000+ entreprises**.

Configure automatiquement tous les attributs nécessaires :
- ✅ **Searchable** (50+ attributs)
- ✅ **Filterable** (35+ attributs)  
- ✅ **Sortable** (15+ attributs)
- ✅ Synonymes, Stop words, Typo tolerance

---

## 🚀 Utilisation

### 1. **Auto-détection de TOUTES les entreprises**
```bash
python configure_meili_complete.py --all
```

### 2. **Entreprise spécifique**
```bash
python configure_meili_complete.py --company MpfnlSbqwaZ6F4HvxQLRL9du0yG3
```

### 3. **Plusieurs entreprises**
```bash
python configure_meili_complete.py --company ID1 --company ID2 --company ID3
```

### 4. **Mode verbeux (logs détaillés)**
```bash
python configure_meili_complete.py --all --verbose
```

### 5. **Mode interactif (sans arguments)**
```bash
python configure_meili_complete.py
```

---

## 📊 Index configurés par entreprise

Pour chaque entreprise, 5 types d'index sont configurés :

1. **`company_docs_{company_id}`** - Index unifié principal
2. **`products_{company_id}`** - Catalogue produits
3. **`delivery_{company_id}`** - Informations livraison
4. **`support_paiement_{company_id}`** - Support et paiement
5. **`localisation_{company_id}`** - Localisations

---

## 🎯 Exemples d'utilisation

### Scenario 1 : Nouvelle entreprise onboardée
```bash
# Configurer uniquement la nouvelle entreprise
python configure_meili_complete.py --company ABC123XYZ456
```

### Scenario 2 : Mise à jour globale
```bash
# Reconfigurer toutes les entreprises existantes
python configure_meili_complete.py --all
```

### Scenario 3 : Production avec 100+ entreprises
```bash
# Mode silencieux, rapide, toutes entreprises
python configure_meili_complete.py --all
```

### Scenario 4 : Debug d'une entreprise
```bash
# Mode verbeux pour une entreprise
python configure_meili_complete.py --company ID --verbose
```

---

## ⚙️ Configuration appliquée

### Searchable Attributes (50)
- Texte : `searchable_text`, `content`, `content_fr`, `text`
- Produits : `product_name`, `name`, `description`, `brand`, `color`, `category`, `subcategory`, `size`, `tags`
- Livraison : `zone`, `zone_name`, `zone_group`, `city`, `commune`, `quartier`
- Paiement : `method`, `payment_method`, `contact_info`
- Support : `question`, `answer`, `faq_question`, `faq_answer`
- Général : `title`, `details`, `notes`, `slug`

### Filterable Attributes (35)
- IDs : `company_id`, `id`, `type`, `doc_type`
- Produits : `category`, `subcategory`, `color`, `brand`, `size`, `stock`, `in_stock`, `available`
- Prix : `price`, `min_price`, `max_price`, `currency`, `fee`, `delivery_fee`
- Zones : `zone`, `zone_group`, `city`, `free_delivery`, `express_available`
- Paiement : `method`, `payment_method`, `payment_accepted`
- Conditions : `acompte_required`, `prepaid_only`, `policy_kind`
- Métadonnées : `tags`, `section`, `language`, `is_active`, `visibility`
- Dates : `created_at`, `updated_at`, `last_modified`

### Sortable Attributes (15)
- `price`, `min_price`, `max_price`, `fee`, `delivery_fee`
- `stock`, `quantity`
- `created_at`, `updated_at`, `last_modified`
- `priority`, `order`, `rank`, `popularity`

### Synonymes
- **Villes** : cocody, yopougon, abidjan, etc.
- **Produits** : couche, culotte, bébé, etc.
- **Couleurs** : noir, bleu, rouge, blanc, gris, vert, jaune, rose
- **Paiement** : wave, paiement, acompte
- **Livraison** : livraison, gratuit, express

---

## 📈 Performance

- **1 entreprise** : ~2-3 secondes
- **10 entreprises** : ~15-20 secondes
- **100 entreprises** : ~2-3 minutes
- **1000 entreprises** : ~20-30 minutes

---

## 🔍 Vérification

Après configuration, vérifier :

```bash
# Lister tous les index
curl http://localhost:7700/indexes

# Stats d'un index
curl http://localhost:7700/indexes/company_docs_YOUR_ID/stats

# Settings d'un index
curl http://localhost:7700/indexes/company_docs_YOUR_ID/settings
```

---

## ⚠️ Prérequis

- MeiliSearch en cours d'exécution
- Variables d'environnement configurées :
  - `MEILI_URL` (défaut: http://127.0.0.1:7700)
  - `MEILI_MASTER_KEY`

---

## 🛠️ Maintenance

### Ajouter un nouvel attribut searchable
Modifier `OPTIMAL_SETTINGS['searchableAttributes']` dans le script.

### Ajouter un synonyme
Modifier `OPTIMAL_SETTINGS['synonyms']` dans le script.

### Changer les ranking rules
Modifier `OPTIMAL_SETTINGS['rankingRules']` dans le script.

---

## 📞 Support

En cas d'erreur, le script affiche :
- ✅ Index configurés avec succès
- ❌ Index en erreur avec le message d'erreur
- 📊 Statistiques globales
- 📈 Statistiques par entreprise

Mode `--verbose` pour logs détaillés.

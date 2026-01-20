# 🔥 DISCUSSION: CORRECTIONS MAJEURES SYSTÈME RAG

## ❌ PROBLÈMES CRITIQUES IDENTIFIÉS

### **1. LIMITE 3 DOCS GLOBALE AU LIEU DE 3 PAR INDEX** 🔴

#### **Problème actuel**:
```python
# Flux actuel (CASSÉ):
1. Recherche parallèle sur 4 index (products, delivery, faq, company_docs)
2. Collecte TOUS les résultats (10 docs)
3. Déduplication globale
4. Filtrage global → 5 docs
5. LIMITE GLOBALE → 3 docs finaux

# Résultat:
📦 [MEILI_DEBUG] Documents collectés: 10 après déduplication
🔍 [MEILI_FILTER] 5/10 docs retenus après filtrage
📦 [MEILI_DEBUG] 3 docs retenus, scores: [82, 72, 72]

# ❌ TOUS les 3 docs viennent de products_index!
# ❌ Les docs de delivery_index sont perdus!
```

#### **Impact**:
- ❌ Question "Prix + Livraison Bingerville" → Seulement prix, pas livraison
- ❌ Double intention cassée
- ❌ Docs delivery ignorés même s'ils matchent

#### **Solution proposée**:
```python
# ✅ ANCIEN SYSTÈME (TON SYSTÈME - PARFAIT):
def search_parallel_by_index(query, company_id, max_docs_per_index=3):
    """
    Recherche avec limite PAR INDEX
    """
    results_by_index = {}
    
    for index_name in ['products', 'delivery', 'faq', 'company_docs']:
        # Recherche dans cet index
        docs = search_in_index(query, index_name, company_id)
        
        # Garder TOP 3 pour CET index
        results_by_index[index_name] = docs[:3]
    
    # Fusionner TOUS les résultats
    all_docs = []
    for index_name, docs in results_by_index.items():
        all_docs.extend(docs)
    
    return all_docs  # 3*4 = 12 docs max (3 par index)

# Résultat:
# ✅ 3 docs de products (prix)
# ✅ 3 docs de delivery (livraison Bingerville)
# ✅ 3 docs de faq (si pertinent)
# = 9-12 docs au total
```

#### **Code à modifier**:
`database/vector_store_clean_v2.py` ligne 334-360

---

### **2. SYSTÈME REGEX LIVRAISON INCOMPLET** 🟡

#### **Problème actuel**:
```python
# Le système fonctionne:
🚚 Zone détectée: Bingerville
💰 FRAIS EXACTS: 2 500 FCFA
⏰ HEURE CI: Il est 08h19

# MAIS ensuite:
🔍 [FILTRAGE] Zone trouvée par regex → Suppression docs livraison MeiliSearch
✅ [FILTRAGE] Docs livraison supprimés → -0 chars économisés

# ❌ Les docs delivery de MeiliSearch sont supprimés!
# ❌ Le LLM n'a que le bloc regex, pas les docs originaux
```

#### **Impact**:
- ⚠️ Perte d'informations détaillées (délais, conditions, etc.)
- ⚠️ Si regex échoue, aucun fallback

#### **Solution proposée**:
```python
# ✅ GARDER LES DEUX:
# 1. Bloc regex (prioritaire, injecté en haut)
# 2. Docs delivery MeiliSearch (fallback, contexte additionnel)

# Prompt LLM:
"""
═══════════════════════════════════════════════════════════════
⚠️ INFORMATION PRIORITAIRE - FRAIS DE LIVRAISON (REGEX)
═══════════════════════════════════════════════════════════════
🚚 ZONE: Bingerville
💰 FRAIS EXACTS: 2 500 FCFA
⏰ HEURE CI: 08h19
═══════════════════════════════════════════════════════════════

<context>
DOCUMENT #1 (products): Couches taille 4 - 24 000 FCFA
DOCUMENT #2 (delivery): Bingerville - Détails complets...  # ← GARDER!
DOCUMENT #3 (delivery): Zones périphériques...  # ← GARDER!
</context>
"""
```

---

### **3. PROMPT LLM - SOURCES MANQUANTES** 🔴

#### **Problème actuel**:
```xml
<thinking>
Phase 2 – Validation
- 🚨 ANTI-HALLUCINATION : Prix/produits → UNIQUEMENT `<context>`
- Confiance : ÉLEVÉE
</thinking>

<response>
💰 Prix: 24 000 FCFA
</response>
```

**Manque**:
- ❌ Pas de mention SOURCE pour chaque info
- ❌ Pas de vérification `<context>` ligne par ligne
- ❌ Pas de citation doc exact

#### **Solution proposée**:
```xml
<thinking>
Phase 2 – Validation STRICTE

🔍 INFO 1: Prix lot 300 taille 4
   - SOURCE: <context> DOCUMENT #1 "24.000 F CFA" ✅
   - LIGNE EXACTE: "VARIANTE: Taille 4 - 9 à 14 kg - 300 couches | 24.000 F CFA"
   - CONFIANCE: 100% (trouvé mot-à-mot)
   - DÉCISION: INCLURE

🔍 INFO 2: Livraison Bingerville
   - SOURCE: BLOC REGEX "2 500 FCFA" ✅
   - FALLBACK: <context> DOCUMENT #2 (delivery) ✅
   - CONFIANCE: 100%
   - DÉCISION: INCLURE

🔍 INFO 3: Total
   - CALCUL: 24000 + 2500 = 26500 ✅
   - ACTION: Calculatrice Python (24000 + 2500)
   - RÉSULTAT: 26500 FCFA
   - DÉCISION: INCLURE

🚨 VÉRIFICATION ANTI-HALLUCINATION:
   ✅ Toutes les infos ont une SOURCE vérifiable
   ✅ Aucune invention
   ✅ Calculs validés
</thinking>

<response>
💰 Prix lot 300 taille 4: 24 000 FCFA (source: catalogue)
🚚 Livraison Bingerville: 2 500 FCFA (source: grille tarifaire)
💵 Total: 26 500 FCFA (24 000 + 2 500)
Votre numéro de téléphone?
</response>
```

#### **Nouveau format thinking**:
```python
PHASE 2 - VALIDATION STRICTE:

Pour CHAQUE information à donner:
1. 🔍 Identifier l'info
2. 📍 Trouver la SOURCE exacte (<context> ligne X, <history> message Y, REGEX, CALCUL)
3. ✅ Vérifier présence mot-à-mot
4. 📊 Calculer confiance (0-100%)
5. ⚖️ Décision: INCLURE si confiance >80%, IGNORER sinon
6. 🚨 Si aucune source → NE PAS MENTIONNER (même si probable)
```

---

### **4. HARDCODING "LOT X TAILLE Y"** 🔴

#### **Problème**:
```python
# ❌ MON ERREUR dans smart_context_manager.py:
lot_taille_match = re.search(r'lot\s*(?:de\s*)?(\d+)\s+.*?taille\s+(\d+)', ...)

# Fonctionne pour:
# ✅ "lot 300 taille 4" (Rue du Grossiste)

# Ne fonctionne PAS pour:
# ❌ "Consultation 2h" (Services)
# ❌ "Chargeur USB-C" (Électronique)
# ❌ "T-shirt rouge M" (Vêtements)
```

#### **Solution proposée - EXTRACTION BASÉE SUR THINKING LLM**:

```python
# ✅ SYSTÈME ÉVOLUTIF (TON IDÉE - GÉNIALE!):

class DynamicContextExtractor:
    """
    Extraction basée sur le THINKING du LLM
    Évolutif et auto-apprenant
    """
    
    def __init__(self):
        self.patterns_db = {}  # Patterns appris par user_id
        self.global_patterns = {}  # Patterns communs (tous users)
    
    def extract_from_thinking(self, thinking_text: str, user_id: str) -> Dict[str, str]:
        """
        Extrait les infos depuis <thinking>
        
        Le LLM mentionne déjà les infos clés:
        "- Produit: lot 300 taille 4"
        "- Zone: Bingerville"
        "- Prix: 24 000 FCFA"
        
        On parse ces mentions!
        """
        extracted = {}
        
        # Pattern générique: "- Clé: Valeur"
        pattern = r'-\s*([^:]+):\s*([^\n]+)'
        matches = re.findall(pattern, thinking_text)
        
        for key, value in matches:
            key_clean = key.strip().lower()
            value_clean = value.strip()
            
            # Mapper les clés
            key_mapping = {
                'produit': 'produit',
                'product': 'produit',
                'lot': 'produit',
                'zone': 'zone',
                'commune': 'zone',
                'livraison': 'zone',
                'prix': 'prix_produit',
                'price': 'prix_produit',
                'téléphone': 'telephone',
                'phone': 'telephone',
                'paiement': 'paiement',
                'payment': 'paiement'
            }
            
            if key_clean in key_mapping:
                extracted[key_mapping[key_clean]] = value_clean
        
        # Sauvegarder les patterns pour cet user
        self._learn_patterns(user_id, extracted)
        
        return extracted
    
    def _learn_patterns(self, user_id: str, extracted: Dict[str, str]):
        """
        Apprentissage automatique des patterns
        
        Si on voit 5 fois "lot 300 taille 4" pour user_001:
        → Pattern appris: "lot \d+ taille \d+"
        
        Si on voit ce pattern pour 10 users différents:
        → Pattern global (pour tous)
        """
        if user_id not in self.patterns_db:
            self.patterns_db[user_id] = {}
        
        for key, value in extracted.items():
            if key not in self.patterns_db[user_id]:
                self.patterns_db[user_id][key] = []
            
            self.patterns_db[user_id][key].append(value)
            
            # Si 5+ occurrences similaires → Créer pattern
            if len(self.patterns_db[user_id][key]) >= 5:
                pattern = self._generate_pattern(self.patterns_db[user_id][key])
                self.global_patterns[key] = pattern
    
    def _generate_pattern(self, values: List[str]) -> str:
        """
        Génère un pattern regex depuis des exemples
        
        Exemples:
        ["lot 150 taille 4", "lot 300 taille 4", "lot 300 taille 3"]
        → Pattern: r'lot \d+ taille \d+'
        
        ["Consultation 2h", "Consultation 3h", "Consultation 1h30"]
        → Pattern: r'Consultation \d+h?\d*'
        """
        # Algorithme de génération de pattern
        # (à implémenter - analyse des similarités)
        pass
```

#### **Avantages**:
- ✅ **Évolutif**: Apprend automatiquement
- ✅ **Scalable**: Fonctionne pour TOUTES les entreprises
- ✅ **Pas de hardcoding**: Basé sur les données réelles
- ✅ **Auto-amélioration**: Plus il est utilisé, plus il est précis

---

## 🎯 PLAN D'ACTION PROPOSÉ

### **PRIORITÉ 1: 3 DOCS PAR INDEX** (Impact immédiat)
```bash
Fichier: database/vector_store_clean_v2.py
Temps: 30min
Impact: ✅ Double intentions fonctionnent
```

### **PRIORITÉ 2: PROMPT LLM SOURCES** (Anti-hallucination)
```bash
Fichier: Prompt système (Supabase)
Temps: 1h
Impact: ✅ Traçabilité complète, 0% hallucination
```

### **PRIORITÉ 3: EXTRACTION THINKING** (Scalabilité)
```bash
Fichier: core/dynamic_context_extractor.py (nouveau)
Temps: 2h
Impact: ✅ Fonctionne pour 1000+ entreprises
```

### **PRIORITÉ 4: GARDER DOCS DELIVERY** (Contexte complet)
```bash
Fichier: core/universal_rag_engine.py
Temps: 15min
Impact: ✅ Fallback si regex échoue
```

---

## 💬 QUESTIONS POUR TOI

### **Q1: Ordre des priorités OK?**
- Priorité 1: 3 docs par index
- Priorité 2: Prompt sources
- Priorité 3: Extraction thinking
- Priorité 4: Garder docs delivery

### **Q2: Extraction thinking - Détails?**
- Parser le `<thinking>` du LLM?
- Apprendre patterns par user_id?
- Patterns globaux après X occurrences?

### **Q3: Prompt LLM - Format sources?**
```xml
<thinking>
🔍 INFO: Prix
   - SOURCE: <context> DOC #1 ligne 5
   - TEXTE EXACT: "24.000 F CFA"
   - CONFIANCE: 100%
   - DÉCISION: INCLURE
</thinking>
```
Ce format te convient?

### **Q4: 3 docs par index - Fusion?**
Après avoir 3 docs par index (12 docs total):
- Les garder TOUS dans le prompt?
- Ou filtrer/scorer globalement?

---

## 🚀 PRÊT À IMPLÉMENTER

Dis-moi:
1. **Ordre des priorités** (1, 2, 3, 4 OK?)
2. **Détails extraction thinking** (parser comment?)
3. **Format prompt sources** (OK ou modifier?)
4. **Fusion 3 docs/index** (garder tous ou filtrer?)

Et on implémente! 🔥

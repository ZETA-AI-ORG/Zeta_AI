// ============================================
// N8N CODE NODE - GÉNÉRATION SYSTEM_PROMPT_TEMPLATE UNIQUEMENT
// ============================================
// À exécuter en parallèle avec le node BOTLIVE existant
// Génère uniquement le prompt universel pour company_rag_configs

// ============================================
// TEMPLATE UNIVERSEL
// ============================================

const UNIVERSAL_PROMPT_TEMPLATE = `# {{ASSISTANT_NAME}} - Assistant {{COMPANY_NAME}}

## 🎯 IDENTITÉ
Tu es **{{ASSISTANT_NAME}}**, assistant(e) de **{{COMPANY_NAME}}** ({{COMPANY_SECTOR}}).  
**Contact:** WhatsApp {{WHATSAPP_PHONE}} | Wave {{WAVE_PHONE}} | 24h/7 | {{COMPANY_LOCATION}} | Acompte de validation de commande : {{DEPOSIT_AMOUNT}} Fcfa

---

## ⚠️ FORMAT OBLIGATOIRE DE SORTIE

**TU DOIS OBLIGATOIREMENT retourner tes réponses dans ce format exact :**

\`\`\`xml
<thinking>
# EXTRACTION
question: "[texte exact]"
intentions: [intention_1, intention_2]
patterns_positifs: [mot1, mot2, mot3]
patterns_negatifs: [mot_oppose1, mot_oppose2]

# COLLECTE
deja_collecte: {type_produit: valeur, quantite: valeur, zone: valeur, telephone: valeur, paiement: valeur}
nouvelles_donnees: [{cle: nom, valeur: val, source: context/history/question, confiance: HAUTE/MOYENNE/FAIBLE}]

# VALIDATION
sources: [context/history/collecte]
prix_trouve: [oui/non - citation exacte si oui]
ambiguite: [oui/non - raison si oui]
confiance: [0-100]%

# ANTI-RÉPÉTITION
check: {type_produit: true/false, quantite: true/false, zone: true/false, telephone: true/false, paiement: true/false}
regle: "Info true → NE PAS redemander"

# DÉCISION
action: [repondre/clarifier/calculer]
completude: [X/5]
prochaine_etape: "[action précise]"
strategie: {phase: decouverte/interet/decision/action, objectif: texte, technique: texte}
</thinking>

<response>
[Ta réponse au client en 2 phrases maximum]
</response>
\`\`\`

**AUCUNE EXCEPTION. Commence TOUJOURS par <thinking> et termine par </response>.**

---

## 📊 ENTRÉE: DONNÉES DYNAMIQUES

<context>
{context}
</context>

{history}

**📋 CONTEXTE COLLECTÉ:** [Rempli automatiquement - NE JAMAIS redemander]

**❓ QUESTION:** {question}

---

## 🎯 RÈGLES MÉTIER (Sources Strictes)

### 📦 Qualification Produit
**RÈGLE CRITIQUE:** Toujours clarifier \`type_produit\` ET \`quantite\` avant de donner un prix.

**Produits disponibles :**
{{PRODUCTS_LIST}}

**Fourchette de prix :** {{PRICE_MIN}} - {{PRICE_MAX}} FCFA

**Étapes obligatoires :**
1. **Type produit** : "Quel type de {{PRODUCT_CATEGORY}} souhaitez-vous ?" (attendre réponse)
2. **Quantité** : "Quel lot vous intéresse ?" (mentionner UNIQUEMENT quantités disponibles pour ce type)
3. **Prix** : Donner prix UNIQUEMENT si type ET quantité validés (source: \`<context>\` UNIQUEMENT)

**Si ambiguïté détectée :**
- Bloquer progression
- Demander clarification (type → quantité → prix)
- JAMAIS donner prix sans type_produit ET quantite validés

### 🚚 Livraison
- **Source:** \`<context>\` UNIQUEMENT
- **Format:** Zone + Frais + Délai

**Zones disponibles :**
{{DELIVERY_ZONES_LIST}}

### 💳 Paiement
**Méthodes acceptées :**
{{PAYMENT_METHODS_LIST}}

**Acompte obligatoire :** {{DEPOSIT_AMOUNT}} FCFA

### 📞 Contact
- **Téléphone:** Extraire de \`<history>\` ou CONTEXTE COLLECTÉ UNIQUEMENT
- **WhatsApp:** {{WHATSAPP_PHONE}}

---

## 🚨 RÈGLES CRITIQUES

### Hiérarchie Sources
1. **Prix/Produits/Quantités/Livraison:** \`<context>\` UNIQUEMENT
2. **Téléphone/Adresse:** \`<history>\` ou CONTEXTE COLLECTÉ UNIQUEMENT
3. **Si absent:** NE PAS inventer → Demander clarification

### Validation Obligatoire
\`\`\`yaml
avant_reponse:
  - Vérifier source pour CHAQUE info
  - Citer ligne exacte dans prix_trouve
  - Calculer confiance
  - Si confiance < 80% → Clarifier
\`\`\`

### Qualification Progressive (Système 4/40)
\`\`\`yaml
decouverte:
  objectif: "Identifier besoin précis"
  donnees: [type_produit, quantite]
  ordre: ["Type?", "Quantité?"]

interet:
  objectif: "Créer urgence/valeur"
  donnees: [zone, delai]
  techniques: ["Livraison <3h", "Stock limité"]

decision:
  objectif: "Lever objections"
  donnees: [prix_total, facilite]
  techniques: ["Acompte {{DEPOSIT_AMOUNT}} FCFA", "{{PAYMENT_METHOD}} instantané"]

action:
  objectif: "Closer vente"
  donnees: [telephone, confirmation]
  techniques: ["Je prépare?", "Envoyez acompte"]
\`\`\`

---

## 📤 SORTIE: FORMAT RÉPONSE

### <response> (MAX 2 phrases)

**Structure:**
\`\`\`
[Réponse DIRECTE à la question] + [1 question ciblée 5-8 mots]
\`\`\`

**Style:**
- **Emojis:** 💰 prix | 🚚 livraison | 💳 paiement | 📞 contact | 📦 produit
- **Montants:** "22 900 FCFA" (espaces)
- **Ton:** Direct, efficace, chaleureux

**Anti-verbosité:**
- Répondre UNIQUEMENT ce qui est demandé
- 0 info superflue
- 0 répétition d'info déjà collectée

---

## ⚠️ RAPPEL FINAL

**FORMAT OBLIGATOIRE :**
1. Commence TOUJOURS par \`<thinking>\` avec les 5 sections
2. Termine TOUJOURS par \`<response>\` avec réponse client (max 2 phrases)

**Si tu ne respectes pas ce format, ta réponse sera rejetée et tu devras recommencer.**
`;

// ============================================
// FONCTIONS D'EXTRACTION
// ============================================

function extractProductsList(catalog) {
  if (!catalog || !Array.isArray(catalog) || catalog.length === 0) {
    return '- Aucun produit configuré';
  }
  
  const products = [];
  for (const product of catalog) {
    if (product.variants && product.variants.length > 0) {
      const prices = product.variants.map(v => v.price);
      const minPrice = Math.min(...prices);
      const maxPrice = Math.max(...prices);
      const minFormatted = minPrice.toLocaleString('fr-FR').replace(/,/g, ' ');
      const maxFormatted = maxPrice.toLocaleString('fr-FR').replace(/,/g, ' ');
      products.push('- ' + product.name + ' (' + minFormatted + ' - ' + maxFormatted + ' FCFA)');
    }
  }
  
  return products.length > 0 ? products.join('\n') : '- Aucun produit configuré';
}

function extractPriceRange(catalog) {
  if (!catalog || !Array.isArray(catalog) || catalog.length === 0) {
    return { min: 0, max: 0 };
  }
  
  let allPrices = [];
  for (const product of catalog) {
    if (product.variants && product.variants.length > 0) {
      const prices = product.variants.map(v => v.price);
      allPrices = allPrices.concat(prices);
    }
  }
  
  if (allPrices.length === 0) {
    return { min: 0, max: 0 };
  }
  
  return {
    min: Math.min(...allPrices),
    max: Math.max(...allPrices)
  };
}

function extractDeliveryZonesList(deliveryZonesText) {
  if (!deliveryZonesText) {
    return '- Aucune zone configurée';
  }
  
  const lines = deliveryZonesText.split('\n').filter(line => line.trim());
  const zones = [];
  
  for (const line of lines) {
    if (line.includes('FCFA') && !line.includes('Délais') && !line.includes('Tarif :')) {
      const cleanLine = line.trim().replace(/^-\s*/, '');
      zones.push('- ' + cleanLine);
    }
  }
  
  return zones.length > 0 ? zones.join('\n') : '- Aucune zone configurée';
}

function extractPaymentMethodsList(payment) {
  if (!payment || !payment.payment_methods) {
    return '- Aucun moyen de paiement configuré';
  }
  
  const methods = [];
  const paymentMethods = Array.isArray(payment.payment_methods) 
    ? payment.payment_methods 
    : [payment.payment_methods];
  
  for (const method of paymentMethods) {
    const depositAmount = payment.deposit_amount || 2000;
    const depositFormatted = depositAmount.toLocaleString('fr-FR').replace(/,/g, ' ');
    methods.push('- ' + method + ' (Acompte: ' + depositFormatted + ' FCFA)');
  }
  
  return methods.join('\n');
}

function formatNumber(num) {
  return num.toLocaleString('fr-FR').replace(/,/g, ' ');
}

// ============================================
// FONCTION DE REMPLISSAGE
// ============================================

function fillUniversalPrompt(data) {
  const companyInfo = data.companyInfo || {};
  const payment = data.payment || {};
  const delivery = data.delivery || {};
  const contact = data.contact || {};
  const catalog = data.catalog || [];
  
  // Extraction des données
  const priceRange = extractPriceRange(catalog);
  const productsList = extractProductsList(catalog);
  const deliveryZonesList = extractDeliveryZonesList(delivery.delivery_zones);
  const paymentMethodsList = extractPaymentMethodsList(payment);
  
  // Extraction du numéro WhatsApp
  const whatsappMatch = contact.phone ? contact.phone.match(/\+?\d[\d\s]+/) : null;
  const whatsappPhone = whatsappMatch ? whatsappMatch[0].trim() : '+225 0160924560';
  
  // Extraction du numéro Wave
  const wavePhone = payment.payment_numbers && payment.payment_numbers.Wave 
    ? payment.payment_numbers.Wave 
    : '+225 0787360757';
  
  // Mapping des variables
  const variables = {
    '{{ASSISTANT_NAME}}': companyInfo.ai_name || 'Jessica',
    '{{COMPANY_NAME}}': companyInfo.company_name || 'ENTREPRISE',
    '{{COMPANY_SECTOR}}': companyInfo.secteur_activite || 'Commerce',
    '{{COMPANY_LOCATION}}': 'Abidjan, CI',
    '{{WHATSAPP_PHONE}}': whatsappPhone,
    '{{WAVE_PHONE}}': wavePhone,
    '{{DEPOSIT_AMOUNT}}': formatNumber(payment.deposit_amount || 2000),
    '{{PRODUCTS_LIST}}': productsList,
    '{{PRICE_MIN}}': formatNumber(priceRange.min),
    '{{PRICE_MAX}}': formatNumber(priceRange.max),
    '{{PRODUCT_CATEGORY}}': companyInfo.secteur_activite ? companyInfo.secteur_activite.toLowerCase() : 'produits',
    '{{DELIVERY_ZONES_LIST}}': deliveryZonesList,
    '{{PAYMENT_METHODS_LIST}}': paymentMethodsList,
    '{{PAYMENT_METHOD}}': Array.isArray(payment.payment_methods) 
      ? payment.payment_methods[0] 
      : payment.payment_methods || 'Wave'
  };
  
  // Remplacement de toutes les variables
  let filledPrompt = UNIVERSAL_PROMPT_TEMPLATE;
  for (const placeholder in variables) {
    const value = variables[placeholder];
    const regex = new RegExp(placeholder.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g');
    filledPrompt = filledPrompt.replace(regex, value);
  }
  
  return filledPrompt;
}

// ============================================
// LOGIQUE PRINCIPALE
// ============================================

const inputData = $input.all();
const results = [];

for (const item of inputData) {
  const data = item.json.body || item.json;
  
  // Génération du prompt universel
  const systemPromptTemplate = fillUniversalPrompt(data);
  
  // Préparation pour Supabase (company_rag_configs)
  const supabasePayload = {
    company_id: data.companyId,
    system_prompt_template: systemPromptTemplate,
    rag_enabled: true,
    updated_at: new Date().toISOString()
  };
  
  // Résultat
  results.push({
    json: {
      // Pour Supabase (company_rag_configs)
      supabase: supabasePayload,
      
      // Métadonnées
      metadata: {
        processed_at: new Date().toISOString(),
        prompt_generated: true,
        company_id: data.companyId,
        prompt_length: systemPromptTemplate.length,
        prompt_type: 'universal_v1'
      }
    }
  });
}

return results;

// INPUT: items = $input.all() (n8n webhook onboarding)
// OUTPUT: [{ json: { company_id, text_documents, purge_before, processed_count } }]

const items = $input.all();

/* ===== MOTS-CLÉS GÉNÉRIQUES PAR TYPE DE DOCUMENT ===== */
const KEYWORDS_BY_TYPE = {
  location: [
    // Localisation / Adresse
    "localisation", "adresse", "où êtes-vous", "où vous trouvez", "où trouver",
    "emplacement", "situé", "situation géographique", "géolocalisation",
    // Boutique physique
    "boutique physique", "magasin", "point de vente", "local commercial",
    "boutique en ligne", "e-commerce", "commerce électronique", "vente en ligne",
    "shop", "store", "enseigne", "commerce",
    // Visite / Déplacement
    "se rendre", "venir", "venir sur place", "passer", "visiter", "se déplacer",
    "passer dans vos locaux", "venir en magasin", "venir au magasin",
    "rendez-vous", "se présenter", "venir vous voir",
    // Structure entreprise
    "siège social", "bureau", "locaux", "établissement", "adresse physique",
    "adresse postale", "coordonnées", "où êtes-vous basés"
  ],
  
  delivery: [
    // Livraison générale
    "livraison", "livrer", "livraison à domicile", "vous livrez", "livraison possible",
    "délai de livraison", "délai", "temps de livraison", "livraison rapide",
    "livraison express", "shipping", "expédition", "envoi",
    // Zones géographiques
    "zones", "zone de livraison", "communes", "quartiers", "secteurs",
    "Abidjan", "Yopougon", "Cocody", "Plateau", "Adjamé", "Abobo",
    "Marcory", "Koumassi", "Treichville", "Angré", "Riviera",
    "Port-Bouët", "Attécoubé", "Bingerville", "Songon", "Anyama",
    "hors Abidjan", "provinces", "toute la Côte d'Ivoire",
    // Frais et tarifs
    "frais de livraison", "coût livraison", "prix livraison", "tarif livraison",
    "frais d'envoi", "frais de transport", "combien coûte la livraison",
    "gratuit", "livraison gratuite", "frais offerts"
  ],
  
  product: [
    // Produits généraux
    "produit", "article", "item", "marchandise", "référence",
    "catalogue", "gamme", "assortiment", "stock", "inventaire",
    // Caractéristiques
    "disponible", "disponibilité", "en stock", "rupture de stock",
    "taille", "couleur", "modèle", "marque", "type", "version",
    "qualité", "description", "caractéristiques", "spécifications",
    // Prix et achat
    "prix", "coût", "coûte", "combien", "tarif", "montant",
    "acheter", "achat", "commander", "commande", "réserver",
    "payer", "paiement", "promotion", "offre", "solde", "réduction",
    // Variantes
    "variante", "option", "choix", "déclinaison", "version",
    "lot", "pack", "paquet", "unité", "quantité"
  ],
  
  support: [
    // Contact
    "contact", "contacter", "joindre", "téléphone", "téléphoner",
    "appeler", "numéro", "WhatsApp", "email", "mail",
    "message", "écrire", "chat", "assistance", "aide",
    // Horaires
    "horaires", "heures d'ouverture", "ouvert", "fermé", "disponible",
    "quand", "à quelle heure", "horaires de service",
    // Support et SAV
    "service client", "support", "assistance", "aide", "question",
    "problème", "réclamation", "plainte", "retour", "remboursement",
    "garantie", "SAV", "service après-vente", "échange",
    // Paiement
    "payer", "paiement", "modes de paiement", "méthodes de paiement",
    "Wave", "Orange Money", "MTN", "Moov", "mobile money",
    "espèces", "cash", "carte bancaire", "virement",
    "acompte", "avance", "paiement anticipé"
  ]
};

/* ===== Fonction pour ajouter mots-clés au contenu (OBSOLÈTE - gardée pour compatibilité) ===== */
function addKeywords(content, type) {
  // Cette fonction n'est plus utilisée
  // Les mots-clés sont maintenant ajoutés dans searchable_text
  return content;
}

/* ===== Helpers - Slug & Utils ===== */
function slugifyDash(s) {
  return (s || "doc")
    .toString().trim().toLowerCase()
    .normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[_\s]+/g, "-")
    .replace(/[^a-z0-9-]/g, "")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function slugifyId(s) {
  return String(s || "doc")
    .normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
    .toLowerCase().trim()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

/* ===== Create text document ===== */
function createDocument(content, fileName, metadata, companyId, addKeywordsFlag = true) {
  if (!metadata.company_id) metadata.company_id = companyId;
  if (!metadata.id) metadata.id = slugifyId(fileName);
  if (!metadata.document_id) metadata.document_id = metadata.id;
  metadata.id_slug = slugifyDash(fileName);
  metadata.id_raw = fileName;
  
  const cleanContent = content.trim();
  
  // Construire le MEGA CHAMP searchable_text
  let searchableText = cleanContent; // Commencer avec le contenu
  
  // Ajouter TOUTES les métadonnées importantes au searchable_text
  const metaValues = [];
  
  // Infos générales
  if (metadata.name) metaValues.push(metadata.name);
  if (metadata.ai_name) metaValues.push(metadata.ai_name);
  if (metadata.sector) metaValues.push(metadata.sector);
  if (metadata.zone) metaValues.push(metadata.zone);
  if (metadata.country) metaValues.push(metadata.country);
  
  // Produits
  if (metadata.product_name) metaValues.push(metadata.product_name);
  if (metadata.category) metaValues.push(metadata.category);
  if (metadata.subcategory) metaValues.push(metadata.subcategory);
  if (metadata.price_min) metaValues.push(metadata.price_min + " FCFA");
  if (metadata.price_max) metaValues.push(metadata.price_max + " FCFA");
  if (metadata.variants_count) metaValues.push(metadata.variants_count + " variantes");
  
  // Livraison
  if (metadata.delivery_zone) metaValues.push(metadata.delivery_zone);
  if (metadata.zone_names && Array.isArray(metadata.zone_names)) {
    metaValues.push(...metadata.zone_names);
  }
  if (metadata.price) metaValues.push(metadata.price + " FCFA");
  
  // Contact & Support
  if (metadata.phone) metaValues.push(metadata.phone);
  if (metadata.location_type) metaValues.push(metadata.location_type);
  if (metadata.has_physical_store !== undefined) {
    metaValues.push(metadata.has_physical_store ? "boutique physique" : "en ligne uniquement");
  }
  
  // Paiement
  if (metadata.payment_methods && Array.isArray(metadata.payment_methods)) {
    metaValues.push(...metadata.payment_methods);
  }
  if (metadata.acompte_required) metaValues.push("acompte obligatoire");
  
  // FAQ & autres
  if (metadata.questions_count) metaValues.push(metadata.questions_count + " questions");
  
  // Ajouter les métadonnées au searchable_text
  if (metaValues.length > 0) {
    searchableText += " " + metaValues.join(" ");
  }
  
  // ❌ MOTS-CLÉS GÉNÉRIQUES SUPPRIMÉS (polluent trop les documents)
  // Le searchable_text contient maintenant UNIQUEMENT:
  // - Le contenu réel
  // - Les métadonnées importantes (nom, zone, prix, etc.)
  
  return {
    content: cleanContent,  // Contenu PROPRE pour Supabase/LLM
    searchable_text: searchableText,  // MEGA CHAMP optimisé (sans pollution)
    file_name: fileName,
    metadata: metadata
  };
}

/* ===== Main pipeline ===== */
return items.map((item, idx) => {
  const body = item.json?.body ?? item.json ?? {};
  const company_id = body.company_id || "UNKNOWN_COMPANY";
  const identity = body.identity || {};
  const catalogue = body.catalogue || [];
  const finalisation = body.finalisation || {};
  
  const text_documents = [];
  
  console.log(`🚀 Processing onboarding for company: ${company_id}`);
  
  // ===== 1. DOCUMENT IDENTITÉ ENTREPRISE =====
  if (identity.companyName) {
    const identityContent = `
IDENTITÉ ENTREPRISE:
Nom: ${identity.companyName}
Assistant IA: ${identity.iaName || 'Assistant'}
Zone d'activité: ${identity.activityZone || 'Non spécifié'}
Secteur: ${catalogue[0]?.category?.replace('_', ' ') || 'Commerce'}

DESCRIPTION:
${identity.description || ''}

MISSION:
${identity.mission || ''}

OBJECTIF IA:
${identity.iaObjective || 'Assister les clients'}
    `.trim();
    
    text_documents.push(createDocument(
      identityContent,
      `${slugifyDash(identity.companyName)}-identite.txt`,
      {
        type: "company",
        name: identity.companyName,
        ai_name: identity.iaName,
        zone: identity.activityZone,
        sector: catalogue[0]?.category || 'commerce'
      },
      company_id,
      false // Pas de mots-clés pour identité (document général)
    ));
    
    console.log(`✅ Document identité créé`);
  }
  
  // ===== 1.5 DOCUMENT INFOS SUR L'ENTREPRISE (NOUVEAU) =====
  if (identity.companyName && (identity.description || identity.mission)) {
    const infosContent = `
INFORMATIONS SUR L'ENTREPRISE:

🏢 NOM: ${identity.companyName}
🤖 ASSISTANT IA: ${identity.iaName || 'Assistant'}
🌍 ZONE D'ACTIVITÉ: ${identity.activityZone || 'Côte d\'Ivoire'}
📊 SECTEUR: ${catalogue[0]?.category?.replace('_', ' ') || 'Commerce'}

📝 DESCRIPTION:
${identity.description || 'Non spécifié'}

🎯 MISSION:
${identity.mission || 'Non spécifié'}

🤖 OBJECTIF ASSISTANT IA:
${identity.iaObjective || 'Assister et guider les clients'}

💼 TYPE D'ENTREPRISE:
${finalisation.contact?.hasPhysicalStore ? 'Commerce physique + en ligne' : 'E-commerce 100% en ligne'}
    `.trim();
    
    text_documents.push(createDocument(
      infosContent,
      `${slugifyDash(identity.companyName)}-infos-entreprise.txt`,
      {
        type: "company_info",
        name: identity.companyName,
        ai_name: identity.iaName,
        zone: identity.activityZone,
        sector: catalogue[0]?.category || 'commerce',
        has_description: !!identity.description,
        has_mission: !!identity.mission
      },
      company_id,
      false // Pas de mots-clés pour infos générales
    ));
    
    console.log(`✅ Document infos entreprise créé`);
  }
  
  // ===== 1.6 DOCUMENT LOCALISATION ENTREPRISE (SÉPARÉ, SANS ZONES DE LIVRAISON) =====
  if (identity.companyName && finalisation.contact) {
    const hasPhysicalStore = finalisation.contact.hasPhysicalStore || false;
    
    const localisationContent = `
LOCALISATION ET ADRESSE ENTREPRISE:

🏢 NOM: ${identity.companyName}
📍 TYPE: ${hasPhysicalStore ? 'Boutique physique + en ligne' : 'E-commerce 100% en ligne (boutique virtuelle)'}

${hasPhysicalStore ? '✅ BOUTIQUE PHYSIQUE DISPONIBLE' : '❌ BOUTIQUE PHYSIQUE: Aucune'}
${!hasPhysicalStore ? '❌ MAGASIN PHYSIQUE: Non disponible' : ''}
${!hasPhysicalStore ? '❌ POINT DE VENTE: Pas de local commercial' : ''}
${!hasPhysicalStore ? '❌ ADRESSE PHYSIQUE: N/A - Uniquement en ligne' : ''}

${!hasPhysicalStore ? 'Vous ne pouvez PAS vous rendre dans nos locaux car nous n\'avons pas de boutique physique.' : ''}
${!hasPhysicalStore ? 'Nous sommes une entreprise exclusivement en ligne.' : ''}

📞 CONTACT:
${finalisation.contact.phone ? `${finalisation.contact.phone}` : 'Non spécifié'}
Horaires: ${finalisation.contact.hours || '24/7 (toujours disponible)'}

🌍 ZONE D'ACTIVITÉ: ${identity.activityZone || 'Côte d\'Ivoire'}
🚚 MODÈLE: ${hasPhysicalStore ? 'Boutique physique + Livraison à domicile' : 'Livraison à domicile uniquement'}
    `.trim();
    
    text_documents.push(createDocument(
      localisationContent,
      `${slugifyDash(identity.companyName)}-localisation.txt`,
      {
        type: "localisation",  // ✅ TYPE "localisation" pour routage correct
        name: identity.companyName,
        zone: identity.activityZone,
        country: "Côte d'Ivoire",
        has_physical_store: hasPhysicalStore,
        location_type: hasPhysicalStore ? "hybrid" : "online_only",
        phone: finalisation.contact.phone
      },
      company_id,
      true // ✅ AJOUTER MOTS-CLÉS LOCATION
    ));
    
    console.log(`✅ Document localisation créé (${hasPhysicalStore ? 'HYBRID' : 'ONLINE ONLY'})`);
  }
  
  // ===== 2. DOCUMENTS PRODUITS =====
  if (Array.isArray(catalogue) && catalogue.length > 0) {
    catalogue.forEach((product, pIndex) => {
      if (!product.name) return;
      
      let productContent = `
PRODUIT: ${product.name}
Catégorie: ${product.category?.replace('_', ' ') || 'Non catégorisé'}
Sous-catégorie: ${product.subcategory || 'Aucune'}

VARIANTES ET PRIX:
`;
      
      // Ajouter les variantes
      if (Array.isArray(product.variants) && product.variants.length > 0) {
        product.variants.forEach((variant, vIndex) => {
          productContent += `
${vIndex + 1}. ${variant.name}
   - Prix: ${variant.price?.toLocaleString('fr-FR')} FCFA
   - Quantité: ${variant.quantity} ${variant.unit || 'unités'}
   - Prix unitaire: ${variant.pricePerUnit?.toFixed(2)} FCFA/${variant.unit || 'unité'}
   ${variant.description ? `- Description: ${variant.description}` : ''}
`;
        });
      }
      
      if (product.usage) {
        productContent += `\nUSAGE:\n${product.usage}`;
      }
      
      if (product.notes) {
        productContent += `\nNOTES IMPORTANTES:\n${product.notes}`;
      }
      
      text_documents.push(createDocument(
        productContent.trim(),
        `produit-${slugifyDash(product.name)}.txt`,
        {
          type: "product",
          product_name: product.name,
          category: product.category,
          subcategory: product.subcategory,
          variants_count: product.variants?.length || 0,
          price_min: Math.min(...(product.variants?.map(v => v.price) || [0])),
          price_max: Math.max(...(product.variants?.map(v => v.price) || [0]))
        },
        company_id,
        true // ✅ AJOUTER MOTS-CLÉS PRODUCT
      ));
    });
    
    console.log(`✅ ${catalogue.length} documents produits créés`);
  }
  
  // ===== 3. DOCUMENTS LIVRAISON (3 ZONES SÉPARÉES) - UNIQUEMENT ZONES, PAS DE LOCALISATION =====
  if (finalisation.delivery) {
    const deliveryText = finalisation.delivery;
    
    // Document 1: Livraison Zones Centrales
    const centralMatch = deliveryText.match(/===\s*LIVRAISON ABIDJAN - ZONES CENTRALES\s*===([\s\S]*?)(?===|$)/i);
    if (centralMatch) {
      const centralContent = `
ZONES DE LIVRAISON - ABIDJAN CENTRE

${centralMatch[1].trim()}

🚚 SERVICE: Livraison à domicile uniquement
📍 COUVERTURE: Zones centrales d'Abidjan
⏰ DÉLAI: Commande avant 11h → Livraison jour même | Après 11h → Lendemain
      `.trim();
      
      text_documents.push(createDocument(
        centralContent,
        "livraison-zones-centrales.txt",
        {
          type: "livraison",
          delivery_zone: "centre",
          zone_names: ["Yopougon", "Cocody", "Plateau", "Adjamé", "Abobo", "Marcory", "Koumassi", "Treichville", "Angré", "Riviera"],
          price: 1500
        },
        company_id,
        true // ✅ AJOUTER MOTS-CLÉS DELIVERY
      ));
      console.log(`✅ Document livraison ZONES CENTRALES créé`);
    }
    
    // Document 2: Livraison Zones Périphériques
    const peripheriqueMatch = deliveryText.match(/===\s*LIVRAISON ABIDJAN - ZONES PÉRIPHÉRIQUES\s*===([\s\S]*?)(?===|$)/i);
    if (peripheriqueMatch) {
      const peripheriqueContent = `
ZONES DE LIVRAISON - ABIDJAN PÉRIPHÉRIE

${peripheriqueMatch[1].trim()}

🚚 SERVICE: Livraison à domicile uniquement
📍 COUVERTURE: Zones périphériques d'Abidjan
⏰ DÉLAI: Commande avant 11h → Livraison jour même | Après 11h → Lendemain
      `.trim();
      
      text_documents.push(createDocument(
        peripheriqueContent,
        "livraison-zones-peripheriques.txt",
        {
          type: "livraison",
          delivery_zone: "peripherie",
          zone_names: ["Port-Bouët", "Attécoubé", "Bingerville", "Songon", "Anyama", "Brofodoumé", "Grand-Bassam", "Dabou"],
          price_min: 2000,
          price_max: 2500
        },
        company_id,
        true // ✅ AJOUTER MOTS-CLÉS DELIVERY
      ));
      console.log(`✅ Document livraison ZONES PÉRIPHÉRIQUES créé`);
    }
    
    // Document 3: Livraison Hors Abidjan
    const horsAbidjanMatch = deliveryText.match(/===\s*EXPÉDITION HORS ABIDJAN\s*===([\s\S]*?)$/i);
    if (horsAbidjanMatch) {
      const horsAbidjanContent = `
ZONES DE LIVRAISON - HORS ABIDJAN (NATIONAL)

${horsAbidjanMatch[1].trim()}

🚚 SERVICE: Livraison à domicile dans toute la Côte d'Ivoire
📍 COUVERTURE: Toutes les villes hors Abidjan
⏰ DÉLAI: Variable selon la ville (confirmation par téléphone)
      `.trim();
      
      text_documents.push(createDocument(
        horsAbidjanContent,
        "livraison-hors-abidjan.txt",
        {
          type: "livraison",
          delivery_zone: "national",
          zone_names: ["Hors Abidjan", "Autres villes", "Provinces"],
          price_min: 3500,
          price_max: 5000
        },
        company_id,
        true // ✅ AJOUTER MOTS-CLÉS DELIVERY
      ));
      console.log(`✅ Document livraison HORS ABIDJAN créé`);
    }
    
    // Fallback: Si le parsing échoue, créer un document unique
    if (!centralMatch && !peripheriqueMatch && !horsAbidjanMatch) {
      const fallbackContent = `
CONDITIONS DE LIVRAISON:

${deliveryText}

🚚 SERVICE: Livraison à domicile
📍 COUVERTURE: Côte d'Ivoire
      `.trim();
      
      text_documents.push(createDocument(
        fallbackContent,
        "livraison-conditions.txt",
        {
          type: "livraison",
          delivery_zone: "all"
        },
        company_id,
        true // ✅ AJOUTER MOTS-CLÉS DELIVERY
      ));
      console.log(`✅ Document livraison UNIQUE créé (fallback)`);
    }
  }
  
  // ===== 4. DOCUMENT PAIEMENT & SUPPORT =====
  if (finalisation.payment || finalisation.contact) {
    let supportContent = '';
    
    // Section Paiement
    if (finalisation.payment) {
      const payment = finalisation.payment;
      supportContent += `
MODES DE PAIEMENT ACCEPTÉS:
${payment.methods?.join(', ') || 'Non spécifié'}

NUMÉROS DE PAIEMENT:
`;
      
      if (payment.numbers) {
        Object.entries(payment.numbers).forEach(([method, number]) => {
          supportContent += `${method.toUpperCase()}: ${number}\n`;
        });
      }
      
      if (payment.acompteRequired) {
        supportContent += `\n⚠️ ACOMPTE OBLIGATOIRE pour valider la commande`;
      }
      
      if (payment.prepaidOnly) {
        supportContent += `\n⚠️ PAIEMENT INTÉGRAL AVANT LIVRAISON`;
      }
    }
    
    // Section Contact
    if (finalisation.contact) {
      const contact = finalisation.contact;
      supportContent += `

CONTACT & SUPPORT:

📞 Téléphone/WhatsApp: ${contact.phone || 'Non spécifié'}
⏰ Horaires: ${contact.hours || 'Non spécifié'}

POLITIQUE DE RETOUR:
${contact.returnPolicy || 'Non spécifié'}
      `;
    }
    
    text_documents.push(createDocument(
      supportContent.trim(),
      "paiement-support.txt",
      {
        type: "support",
        phone: finalisation.contact?.phone,
        payment_methods: finalisation.payment?.methods || [],
        acompte_required: finalisation.payment?.acompteRequired || false
      },
      company_id,
      true // ✅ AJOUTER MOTS-CLÉS SUPPORT
    ));
    
    console.log(`✅ Document paiement & support créé`);
  }
  
  // ===== 5. DOCUMENTS FAQ =====
  if (Array.isArray(finalisation.faq) && finalisation.faq.length > 0) {
    let faqContent = "QUESTIONS FRÉQUENTES (FAQ):\n\n";
    
    finalisation.faq.forEach((item, fIndex) => {
      faqContent += `Q${fIndex + 1}: ${item.question}\nR: ${item.answer}\n\n`;
    });
    
    text_documents.push(createDocument(
      faqContent.trim(),
      "faq.txt",
      {
        type: "faq",
        questions_count: finalisation.faq.length
      },
      company_id,
      false // Pas de mots-clés pour FAQ (déjà question/réponse format)
    ));
    
    console.log(`✅ Document FAQ créé (${finalisation.faq.length} questions)`);
  }
  
  console.log(`🎉 TOTAL: ${text_documents.length} documents créés pour ${company_id}`);
  console.log(`📊 Répartition: identite=1, infos_entreprise=1, localisation=1, products=${catalogue.length}, delivery=3, support=1, faq=${finalisation.faq?.length || 0}`);
  
  return {
    json: {
      company_id,
      text_documents,
      purge_before: true, // Purge les anciens docs avant d'indexer
      processed_count: text_documents.length,
      original_input: {
        company_name: identity.companyName,
        products_count: catalogue.length,
        timestamp: body.timestamp
      }
    },
    pairedItem: { item: idx }
  };
});

// INPUT: items = $input.all() (n8n webhook onboarding)
// OUTPUT: [{ json: { company_id, text_documents, purge_before, processed_count } }]

const items = $input.all();

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
    .replace(/^_+|_+$/g, "");
}

/* ===== Create document with searchable_text ===== */
function createDocument(content, fileName, metadata, company_id) {
  // Normaliser les IDs
  const cleanName = fileName.replace(/\.txt$/, '').replace(/[^a-z0-9_\-]+/gi, '_');
  const globalId = `global_${cleanName}`;
  
  // Ajouter company_id aux métadonnées
  metadata.company_id = company_id;
  metadata.id = cleanName;
  metadata.document_id = cleanName;
  metadata.id_slug = fileName.replace(/\.txt$/, '').replace(/\s+/g, '').toLowerCase();
  metadata.id_raw = fileName;
  
  // PRODUITS: Garder seulement le JSON (pas d'enrichissement)
  if (metadata.type === "product") {
    return {
      content: content,  // JSON pur pour parsing
      file_name: fileName,
      metadata: metadata
    };
  }
  
  // AUTRES TYPES: Enrichir avec métadonnées
  let searchableText = content;
  const metaValues = [];
  
  // Identité & Infos
  if (metadata.name) metaValues.push(metadata.name);
  if (metadata.ai_name) metaValues.push(metadata.ai_name);
  if (metadata.sector) metaValues.push(metadata.sector);
  if (metadata.zone) metaValues.push(metadata.zone);
  if (metadata.country) metaValues.push(metadata.country);
  
  // Livraison
  if (metadata.delivery_zone) metaValues.push(metadata.delivery_zone);
  if (metadata.zone_names && Array.isArray(metadata.zone_names)) {
    metaValues.push(...metadata.zone_names);
  }
  if (metadata.price) metaValues.push(metadata.price + " FCFA");
  if (metadata.price_min && metadata.price_max) {
    metaValues.push(metadata.price_min + " FCFA", metadata.price_max + " FCFA");
  }
  
  // Contact & Support
  if (metadata.phone) metaValues.push(metadata.phone);
  if (metadata.location_type) metaValues.push(metadata.location_type.replace('_', ' '));
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
  
  // Ajouter métadonnées au searchable_text
  if (metaValues.length > 0) {
    searchableText += " " + metaValues.join(" ");
  }
  
  // UN SEUL CHAMP content = contenu + métadonnées (pas de searchable_text séparé)
  return {
    content: searchableText,  // Contenu enrichi pour MeiliSearch ET Supabase
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
    const identityContent = `IDENTITÉ ENTREPRISE:
Nom: ${identity.companyName}
Assistant IA: ${identity.iaName || 'Assistant'}
Zone d'activité: ${identity.activityZone || 'Non spécifié'}
Secteur: ${catalogue[0]?.category?.replace('_', ' ') || 'Commerce'}

DESCRIPTION:
${identity.description || ''}

MISSION:
${identity.mission || ''}

OBJECTIF IA:
${identity.iaObjective || 'Assister les clients'}`;
    
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
      company_id
    ));
    
    console.log(`✅ Document identité créé`);
  }
  
  // ===== 2. DOCUMENT INFOS SUR L'ENTREPRISE =====
  if (identity.companyName && (identity.description || identity.mission)) {
    const infosContent = `INFORMATIONS SUR L'ENTREPRISE:

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
${finalisation.contact?.hasPhysicalStore ? 'Commerce physique + en ligne' : 'E-commerce 100% en ligne'}`;
    
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
      company_id
    ));
    
    console.log(`✅ Document infos entreprise créé`);
  }
  
  // ===== 3. DOCUMENT LOCALISATION ENTREPRISE =====
  if (identity.companyName && finalisation.contact) {
    const hasPhysicalStore = finalisation.contact.hasPhysicalStore || false;
    
    const localisationContent = `LOCALISATION ET ADRESSE ENTREPRISE:

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
🚚 MODÈLE: ${hasPhysicalStore ? 'Boutique physique + Livraison à domicile' : 'Livraison à domicile uniquement'}`;
    
    text_documents.push(createDocument(
      localisationContent,
      `${slugifyDash(identity.companyName)}-localisation.txt`,
      {
        type: "localisation",
        name: identity.companyName,
        zone: identity.activityZone,
        country: "Côte d'Ivoire",
        has_physical_store: hasPhysicalStore,
        location_type: hasPhysicalStore ? "hybrid" : "online_only",
        phone: finalisation.contact.phone
      },
      company_id
    ));
    
    console.log(`✅ Document localisation créé`);
  }
  
  // ===== 4. DOCUMENTS PRODUITS (JSON pour parsing automatique) =====
  if (Array.isArray(catalogue) && catalogue.length > 0) {
    catalogue.forEach((product, pIndex) => {
      if (!product.name) return;
      
      // Créer JSON array des variantes pour parsing automatique (avec id explicite)
      const variantsJson = (product.variants || []).map(v => ({
        product: product.name,
        variant: v.name,
        price: v.price || 0,
        quantity: v.quantity || 0,
        unit: v.unit || "unités",
        description: v.description || "",
        id: v.id || slugifyDash(`${product.name} ${v.name} ${v.price || ''}`)
      }));
      
      // Format JSON pour le parser ingestion_api.py
      const productContent = variantsJson.map(variant => {
        // Champ content explicite avec id en titre
        return `ID: ${variant.id}\nProduit: ${variant.product}\nVariante: ${variant.variant}\nPrix: ${variant.price} FCFA\nQuantité: ${variant.quantity}\nUnité: ${variant.unit}\nDescription: ${variant.description}`;
      }).join('\n\n');
      
      // Utiliser l'id de la première variante comme fileName/id principal
      const mainId = variantsJson[0]?.id || slugifyDash(product.name);
      
      text_documents.push(createDocument(
        productContent,
        `${mainId}.txt`,
        {
          type: "product",
          product_name: product.name,
          category: product.category,
          subcategory: product.subcategory,
          variants_count: product.variants?.length || 0,
          price_min: Math.min(...(product.variants?.map(v => v.price) || [0])),
          price_max: Math.max(...(product.variants?.map(v => v.price) || [0])),
          usage: product.usage,
          notes: product.notes,
          id: mainId
        },
        company_id
      ));
    });
    
    console.log(`✅ ${catalogue.length} documents produits créés (JSON format)`);
  }
  
  // ===== 5. DOCUMENTS LIVRAISON =====
  if (finalisation.delivery) {
    const deliveryText = finalisation.delivery;
    
    // Document 1: Zones Centrales
    const centralMatch = deliveryText.match(/===\s*LIVRAISON ABIDJAN - ZONES CENTRALES\s*===([\s\S]*?)(?===|$)/i);
    if (centralMatch) {
      const centralContent = `ZONES DE LIVRAISON - ABIDJAN CENTRE

${centralMatch[1].trim()}

🚚 SERVICE: Livraison à domicile uniquement
📍 COUVERTURE: Zones centrales d'Abidjan
⏰ DÉLAI: Commande avant 11h → Livraison jour même | Après 11h → Lendemain`;
      
      text_documents.push(createDocument(
        centralContent,
        "livraison-zones-centrales.txt",
        {
          type: "livraison",
          delivery_zone: "centre",
          zone_names: ["Yopougon", "Cocody", "Plateau", "Adjamé", "Abobo", "Marcory", "Koumassi", "Treichville", "Angré", "Riviera"],
          price: 1500
        },
        company_id
      ));
      console.log(`✅ Document livraison ZONES CENTRALES créé`);
    }
    
    // Document 2: Zones Périphériques
    const peripheriqueMatch = deliveryText.match(/===\s*LIVRAISON ABIDJAN - ZONES PÉRIPHÉRIQUES\s*===([\s\S]*?)(?===|$)/i);
    if (peripheriqueMatch) {
      const peripheriqueContent = `ZONES DE LIVRAISON - ABIDJAN PÉRIPHÉRIE

${peripheriqueMatch[1].trim()}

🚚 SERVICE: Livraison à domicile uniquement
📍 COUVERTURE: Zones périphériques d'Abidjan
⏰ DÉLAI: Commande avant 11h → Livraison jour même | Après 11h → Lendemain`;
      
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
        company_id
      ));
      console.log(`✅ Document livraison ZONES PÉRIPHÉRIQUES créé`);
    }
    
    // Document 3: Hors Abidjan
    const horsAbidjanMatch = deliveryText.match(/===\s*EXPÉDITION HORS ABIDJAN\s*===([\s\S]*?)$/i);
    if (horsAbidjanMatch) {
      const horsAbidjanContent = `ZONES DE LIVRAISON - HORS ABIDJAN (NATIONAL)

${horsAbidjanMatch[1].trim()}

🚚 SERVICE: Livraison à domicile dans toute la Côte d'Ivoire
📍 COUVERTURE: Toutes les villes hors Abidjan
⏰ DÉLAI: Variable selon la ville (confirmation par téléphone)`;
      
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
        company_id
      ));
      console.log(`✅ Document livraison HORS ABIDJAN créé`);
    }
  }
  
  // ===== 6. DOCUMENT PAIEMENT & SUPPORT =====
  if (finalisation.payment || finalisation.contact) {
    let supportContent = '';
    
    // Section Paiement
    if (finalisation.payment) {
      const payment = finalisation.payment;
      supportContent += `MODES DE PAIEMENT ACCEPTÉS:
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
    }
    
    // Section Contact
    if (finalisation.contact) {
      const contact = finalisation.contact;
      supportContent += `

CONTACT & SUPPORT:

📞 Téléphone/WhatsApp: ${contact.phone || 'Non spécifié'}
⏰ Horaires: ${contact.hours || 'Non spécifié'}

POLITIQUE DE RETOUR:
${contact.returnPolicy || 'Non spécifié'}`;
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
      company_id
    ));
    
    console.log(`✅ Document paiement & support créé`);
  }
  
  // ===== 7. DOCUMENTS FAQ =====
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
      company_id
    ));
    
    console.log(`✅ Document FAQ créé (${finalisation.faq.length} questions)`);
  }
  
  console.log(`🎉 TOTAL: ${text_documents.length} documents créés pour ${company_id}`);
  
  return {
    json: {
      company_id,
      text_documents,
      purge_before: true,
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

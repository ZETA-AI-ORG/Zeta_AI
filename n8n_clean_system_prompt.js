// N8N - Génération system_prompt_template UNIQUEMENT
// Code minimal et propre

const PROMPT_TEMPLATE = 'Jessica - Assistant RUEDUGROSSISTE\n\nIDENTITE:\nTu es Jessica, assistante de RUEDUGROSSISTE (Bebe et Puericulture).\nContact: WhatsApp PHONE_WA | Wave PHONE_WAVE | Acompte: DEPOSIT Fcfa\n\nFORMAT OBLIGATOIRE:\n<thinking>\nquestion: "[texte]"\nintentions: [int1, int2]\npatterns_positifs: [mot1, mot2]\n</thinking>\n<response>[Reponse 2 phrases max]</response>\n\nPRODUITS:\nPRODUCTS_LIST\nPrix: PRICE_MIN - PRICE_MAX FCFA\n\nLIVRAISON:\nDELIVERY_ZONES\n\nPAIEMENT:\nPAYMENT_METHODS\nAcompte: DEPOSIT FCFA';

function extractProducts(catalog) {
  if (!catalog || catalog.length === 0) return 'Aucun produit';
  let result = '';
  for (let i = 0; i < catalog.length; i++) {
    const p = catalog[i];
    if (p.variants && p.variants.length > 0) {
      const prices = [];
      for (let j = 0; j < p.variants.length; j++) {
        prices.push(p.variants[j].price);
      }
      const min = Math.min.apply(null, prices);
      const max = Math.max.apply(null, prices);
      result += '- ' + p.name + ' (' + min + ' - ' + max + ' FCFA)\n';
    }
  }
  return result || 'Aucun produit';
}

function extractPrices(catalog) {
  if (!catalog || catalog.length === 0) return {min: 0, max: 0};
  const allPrices = [];
  for (let i = 0; i < catalog.length; i++) {
    const p = catalog[i];
    if (p.variants) {
      for (let j = 0; j < p.variants.length; j++) {
        allPrices.push(p.variants[j].price);
      }
    }
  }
  if (allPrices.length === 0) return {min: 0, max: 0};
  return {min: Math.min.apply(null, allPrices), max: Math.max.apply(null, allPrices)};
}

function extractZones(text) {
  if (!text) return 'Aucune zone';
  const lines = text.split('\n');
  let result = '';
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.indexOf('FCFA') > -1 && line.indexOf('Délais') === -1) {
      result += '- ' + line.trim() + '\n';
    }
  }
  return result || 'Aucune zone';
}

function extractPayment(payment) {
  if (!payment || !payment.payment_methods) return 'Aucun moyen';
  const methods = Array.isArray(payment.payment_methods) ? payment.payment_methods : [payment.payment_methods];
  const deposit = payment.deposit_amount || 2000;
  let result = '';
  for (let i = 0; i < methods.length; i++) {
    result += '- ' + methods[i] + ' (Acompte: ' + deposit + ' FCFA)\n';
  }
  return result;
}

function fillPrompt(data) {
  const info = data.companyInfo || {};
  const payment = data.payment || {};
  const delivery = data.delivery || {};
  const contact = data.contact || {};
  const catalog = data.catalog || [];
  
  const prices = extractPrices(catalog);
  const phoneMatch = contact.phone ? contact.phone.match(/\+?\d[\d\s]+/) : null;
  const phoneWa = phoneMatch ? phoneMatch[0].trim() : '+225 0160924560';
  const phoneWave = payment.payment_numbers && payment.payment_numbers.Wave ? payment.payment_numbers.Wave : '+225 0787360757';
  
  let prompt = PROMPT_TEMPLATE;
  prompt = prompt.replace(/PHONE_WA/g, phoneWa);
  prompt = prompt.replace(/PHONE_WAVE/g, phoneWave);
  prompt = prompt.replace(/DEPOSIT/g, String(payment.deposit_amount || 2000));
  prompt = prompt.replace(/PRODUCTS_LIST/g, extractProducts(catalog));
  prompt = prompt.replace(/PRICE_MIN/g, String(prices.min));
  prompt = prompt.replace(/PRICE_MAX/g, String(prices.max));
  prompt = prompt.replace(/DELIVERY_ZONES/g, extractZones(delivery.delivery_zones));
  prompt = prompt.replace(/PAYMENT_METHODS/g, extractPayment(payment));
  
  return prompt;
}

const inputData = $input.all();
const results = [];

for (let i = 0; i < inputData.length; i++) {
  const item = inputData[i];
  const data = item.json.body || item.json;
  const prompt = fillPrompt(data);
  
  results.push({
    json: {
      supabase: {
        company_id: data.companyId,
        system_prompt_template: prompt,
        rag_enabled: true,
        updated_at: new Date().toISOString()
      },
      metadata: {
        company_id: data.companyId,
        prompt_length: prompt.length
      }
    }
  });
}

return results;

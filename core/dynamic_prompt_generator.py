"""
Générateur de prompt dynamique universel basé sur company_booster
Architecture multi-tenant avec cache intégré
"""

import json
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

from core.company_booster_models import CompanyBooster

logger = logging.getLogger(__name__)


# Cache en mémoire pour les prompts générés
_prompt_cache: Dict[str, Dict] = {}
_cache_ttl = timedelta(minutes=10)


# Template de prompt universel
PROMPT_TEMPLATE = """# {assistant_name} - Assistant {company_name}

## 🎯 IDENTITÉ
Tu es **{assistant_name}**, assistant(e) de **{company_name}** ({company_sector}).  
**Contact:** WhatsApp {whatsapp_phone} | Wave {wave_phone} | 24h/7 | {company_location} | Acompte de validation de commande : {deposit_amount} Fcfa

---

## ⚠️ FORMAT OBLIGATOIRE DE SORTIE

**TU DOIS OBLIGATOIREMENT retourner tes réponses dans ce format exact :**

```xml
<thinking>
# EXTRACTION
question: "[texte exact]"
intentions: [intention_1, intention_2]
patterns_positifs: [mot1, mot2, mot3]
patterns_negatifs: [mot_oppose1, mot_oppose2]

# COLLECTE
deja_collecte: {{type_produit: valeur, quantite: valeur, zone: valeur, telephone: valeur, paiement: valeur}}
nouvelles_donnees: [{{cle: nom, valeur: val, source: context/history/question, confiance: HAUTE/MOYENNE/FAIBLE}}]

# VALIDATION
sources: [context/history/collecte]
prix_trouve: [oui/non - citation exacte si oui]
ambiguite: [oui/non - raison si oui]
confiance: [0-100]%

# ANTI-RÉPÉTITION
check: {{type_produit: true/false, quantite: true/false, zone: true/false, telephone: true/false, paiement: true/false}}
regle: "Info true → NE PAS redemander"

# DÉCISION
action: [repondre/clarifier/calculer]
completude: [X/5]
prochaine_etape: "[action précise]"
strategie: {{phase: decouverte/interet/decision/action, objectif: texte, technique: texte}}
</thinking>

<response>
[Ta réponse au client en 2 phrases maximum]
</response>
```

**AUCUNE EXCEPTION. Commence TOUJOURS par <thinking> et termine par </response>.**

---

## 📊 ENTRÉE: DONNÉES DYNAMIQUES

<context>
{{context}}
</context>

{{history}}

**📋 CONTEXTE COLLECTÉ:** [Rempli automatiquement - NE JAMAIS redemander]

**❓ QUESTION:** {{question}}

---

## 🎯 RÈGLES MÉTIER (Sources Strictes)

### 📦 Qualification Produit
**RÈGLE CRITIQUE:** Toujours clarifier `type_produit` ET `quantite` avant de donner un prix.

**Produits disponibles :**
{products_list}

**Fourchette de prix :** {price_min} - {price_max} FCFA

**Étapes obligatoires :**
1. **Type produit** : "Quel type de {product_category} souhaitez-vous ?" (attendre réponse)
2. **Quantité** : "Quel lot vous intéresse ?" (mentionner UNIQUEMENT quantités disponibles pour ce type)
3. **Prix** : Donner prix UNIQUEMENT si type ET quantité validés (source: `<context>` UNIQUEMENT)

**Si ambiguïté détectée :**
- Bloquer progression
- Demander clarification (type → quantité → prix)
- JAMAIS donner prix sans type_produit ET quantite validés

### 🚚 Livraison
- **Source:** `<context>` UNIQUEMENT
- **Format:** Zone + Frais + Délai

**Zones disponibles :**
{delivery_zones_list}

### 💳 Paiement
**Méthodes acceptées :**
{payment_methods_list}

**Acompte obligatoire :** {deposit_amount} FCFA

### 📞 Contact
- **Téléphone:** Extraire de `<history>` ou CONTEXTE COLLECTÉ UNIQUEMENT
- **WhatsApp:** {whatsapp_phone}

---

## 🚨 RÈGLES CRITIQUES

### Hiérarchie Sources
1. **Prix/Produits/Quantités/Livraison:** `<context>` UNIQUEMENT
2. **Téléphone/Adresse:** `<history>` ou CONTEXTE COLLECTÉ UNIQUEMENT
3. **Si absent:** NE PAS inventer → Demander clarification

### Validation Obligatoire
```yaml
avant_reponse:
  - Vérifier source pour CHAQUE info
  - Citer ligne exacte dans prix_trouve
  - Calculer confiance
  - Si confiance < 80% → Clarifier
```

### Qualification Progressive (Système 4/40)
```yaml
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
  techniques: ["Acompte {deposit_amount} FCFA", "{payment_method} instantané"]

action:
  objectif: "Closer vente"
  donnees: [telephone, confirmation]
  techniques: ["Je prépare?", "Envoyez acompte"]
```

---

## 📤 SORTIE: FORMAT RÉPONSE

### <response> (MAX 2 phrases)

**Structure:**
```
[Réponse DIRECTE à la question] + [1 question ciblée 5-8 mots]
```

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
1. Commence TOUJOURS par `<thinking>` avec les 5 sections
2. Termine TOUJOURS par `<response>` avec réponse client (max 2 phrases)

**Si tu ne respectes pas ce format, ta réponse sera rejetée et tu devras recommencer.**
"""


def generate_prompt_from_booster(booster_data: Dict, assistant_name: str = "Jessica") -> str:
    """
    Génère un prompt dynamique à partir des données company_booster
    
    Args:
        booster_data: Dictionnaire contenant les données company_booster
        assistant_name: Nom de l'assistant (par défaut: Jessica)
        
    Returns:
        Prompt complet formaté avec les données de l'entreprise
    """
    try:
        # Validation avec Pydantic
        booster = CompanyBooster(**booster_data)
        categories = booster.categories
        
        # Extraction des données
        company_name = categories.ENTREPRISE.name or "ENTREPRISE"
        company_sector = categories.ENTREPRISE.sector or "Commerce"
        
        # Contact
        whatsapp_phone = categories.CONTACT.phones[0] if categories.CONTACT.phones else "+225 XXXXXXXXXX"
        
        # Paiement
        payment_method = categories.PAIEMENT.methods[0] if categories.PAIEMENT.methods else None
        wave_phone = "+225 0787360757"  # Peut être extrait de la config si besoin
        deposit_amount = payment_method.deposit if payment_method else 2000
        payment_method_name = payment_method.name if payment_method else "Wave"
        
        # Produits
        products = categories.PRODUIT.products
        products_list = "\n".join([
            f"- {p.name} ({p.price_min:,} - {p.price_max:,} FCFA)".replace(',', ' ')
            for p in products
        ]) if products else "- Aucun produit configuré"
        
        price_min = booster.filters.price_range.min
        price_max = booster.filters.price_range.max
        
        # Livraison
        zones = categories.LIVRAISON.zones
        delivery_zones_list = "\n".join([
            f"- {z.name}: {z.price:,} FCFA".replace(',', ' ')
            for z in zones
        ]) if zones else "- Aucune zone configurée"
        
        # Paiement (liste)
        payment_methods_list = "\n".join([
            f"- {m.name} (Acompte: {m.deposit:,} FCFA)".replace(',', ' ')
            for m in categories.PAIEMENT.methods
        ]) if categories.PAIEMENT.methods else "- Aucun moyen de paiement configuré"
        
        # Génération du prompt
        prompt = PROMPT_TEMPLATE.format(
            assistant_name=assistant_name,
            company_name=company_name,
            company_sector=company_sector,
            company_location="Abidjan, CI",  # Peut être extrait de la config
            whatsapp_phone=whatsapp_phone,
            wave_phone=wave_phone,
            deposit_amount=f"{deposit_amount:,}".replace(',', ' '),
            payment_method=payment_method_name,
            products_list=products_list,
            price_min=f"{price_min:,}".replace(',', ' '),
            price_max=f"{price_max:,}".replace(',', ' '),
            product_category=company_sector.lower(),
            delivery_zones_list=delivery_zones_list,
            payment_methods_list=payment_methods_list
        )
        
        logger.info(f"✅ Prompt généré pour {company_name} ({len(prompt)} chars)")
        return prompt
        
    except Exception as e:
        logger.error(f"❌ Erreur génération prompt: {e}")
        raise


def get_prompt_for_company(company_id: str, booster_data: Optional[Dict] = None, 
                           supabase_client=None, force_refresh: bool = False) -> str:
    """
    Récupère le prompt pour une entreprise (avec cache)
    
    Args:
        company_id: ID de l'entreprise
        booster_data: Données company_booster (optionnel si supabase_client fourni)
        supabase_client: Client Supabase pour récupérer les données
        force_refresh: Forcer le rafraîchissement du cache
        
    Returns:
        Prompt complet pour l'entreprise
    """
    global _prompt_cache
    
    # Vérifier le cache
    if not force_refresh and company_id in _prompt_cache:
        cached = _prompt_cache[company_id]
        if datetime.now() - cached['timestamp'] < _cache_ttl:
            logger.info(f"✅ [CACHE HIT] Prompt pour {company_id}")
            return cached['prompt']
    
    # Récupérer les données si non fournies
    if booster_data is None:
        if supabase_client is None:
            raise ValueError("booster_data ou supabase_client requis")
        
        logger.info(f"🔍 Récupération company_booster pour {company_id}")
        response = supabase_client.table("company_booster").select("*").eq("company_id", company_id).execute()
        
        if not response.data:
            raise ValueError(f"Aucune donnée company_booster pour {company_id}")
        
        booster_data = response.data[0]
        
        # Parser les champs JSON si nécessaire
        if isinstance(booster_data.get('categories'), str):
            booster_data['categories'] = json.loads(booster_data['categories'])
        if isinstance(booster_data.get('filters'), str):
            booster_data['filters'] = json.loads(booster_data['filters'])
    
    # Générer le prompt
    prompt = generate_prompt_from_booster(booster_data)
    
    # Mettre en cache
    _prompt_cache[company_id] = {
        'prompt': prompt,
        'timestamp': datetime.now()
    }
    
    logger.info(f"💾 [CACHE MISS] Prompt généré et mis en cache pour {company_id}")
    return prompt


def clear_prompt_cache(company_id: Optional[str] = None):
    """
    Vide le cache des prompts
    
    Args:
        company_id: ID spécifique à vider (ou None pour tout vider)
    """
    global _prompt_cache
    
    if company_id:
        if company_id in _prompt_cache:
            del _prompt_cache[company_id]
            logger.info(f"🗑️ Cache vidé pour {company_id}")
    else:
        _prompt_cache.clear()
        logger.info("🗑️ Cache complet vidé")

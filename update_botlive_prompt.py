#!/usr/bin/env python3
"""
Script pour mettre à jour le prompt Botlive dans Supabase
SYSTÈME DUAL: Prompt Statique ↔ Dynamique
"""
import httpx
import asyncio
import re
import os

COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"
SUPABASE_URL = "https://ilbihprkxcgsigvueeme.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlocHJreGNnc2lndnVlZW1lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTEzMTQwNCwiZXhwIjoyMDY0NzA3NDA0fQ.Zf0EJbmP5ePGBZL5cY1tFP9FDRvJXDZ3x98zUS993GA"

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION SWITCHABLE
# ═══════════════════════════════════════════════════════════════════════════════
USE_DYNAMIC_PROMPT = False  # FORCE STATIQUE POUR UTILISER SUPABASE
print(f"🔧 Mode: {'DYNAMIQUE' if USE_DYNAMIC_PROMPT else 'STATIQUE'}")

# Configuration entreprise
COMPANY_CONFIG = {
    'assistant_name': 'Jessica',
    'company_name': 'Rue du Grossiste',
    'payment_number': '+225 07 87 36 07 57',
    'support_number': '+225 07 87 36 07 57',
    'zone_centre_price': '1500 FCFA',
    'zone_centre_communes': 'Yopougon, Cocody, Plateau, Adjamé, Abobo, Marcory, Koumassi, Treichville, Angré, Riviera',
    'zone_periph_2000_communes': 'Port-Bouët, Attécoubé',
    'zone_periph_2000_price': '2000 FCFA',
    'zone_periph_2500_communes': 'Bingerville, Songon, Anyama, Brofodoumé, Grand-Bassam, Dabou',
    'zone_periph_2500_price': '2500 FCFA',
    'delivery_cutoff_time': '11h'
}

# ═══════════════════════════════════════════════════════════════════════════════
# VERSION STATIQUE (FULL PROMPT - TOUJOURS CHARGÉ)
# ═══════════════════════════════════════════════════════════════════════════════
STATIC_PROMPT = """Jessica, assistante commandes live Rue du Grossiste (produits bébés).

HISTORIQUE: {conversation_history}
MESSAGE: {question}
VISION: {detected_objects}
TRANSACTIONS: {filtered_transactions}
ACOMPTE: {expected_deposit}

═══════════════════════════════════════════════════════════════════════════════
TARIFS LIVRAISON
═══════════════════════════════════════════════════════════════════════════════
Abidjan Centre (1500 FCFA): Yopougon, Cocody, Plateau, Adjamé, Abobo, Marcory, Koumassi, Treichville, Angré, Riviera
Abidjan Périphérie (2000-2500 FCFA): Port-Bouët, Attécoubé (2000), Bingerville, Songon, Anyama, Brofodoumé, Grand-Bassam, Dabou (2500)
Délais: Commande avant 11h → jour même | Après 11h → lendemain ouvré
Hors Abidjan: Expédition (délais/coût confirmés par téléphone)

═══════════════════════════════════════════════════════════════════════════════
FORMAT OBLIGATOIRE
═══════════════════════════════════════════════════════════════════════════════
<thinking>
CHECKLIST:
☐ Produit: [✓/✗] SOURCE: [VISION/HISTORIQUE]
☐ Détails: [✓/✗] SOURCE: [MESSAGE/HISTORIQUE]
☐ Paiement: [✓/✗] SOURCE: [TRANSACTIONS]
☐ Adresse: [✓/✗] SOURCE: [MESSAGE/HISTORIQUE]
☐ Téléphone: [✓/✗] SOURCE: [MESSAGE/HISTORIQUE]

Étape: [0-5]
Action: [ce qu'on fait]
</thinking>

<response>
[2-3 lignes max, tutoiement, 1 emoji max]
</response>

═══════════════════════════════════════════════════════════════════════════════
WORKFLOW
═══════════════════════════════════════════════════════════════════════════════
0. Produit ✗ → "Salut ! 👋 Envoie la photo du produit"
1. Produit ✓, Paiement ✗ → "Photo reçue ! Des précisions ? Sinon envoie la capture de ton dépôt {expected_deposit}"
2. Détails donnés → "Noté [détails] ! Envoie la capture de ton dépôt"
3. Paiement ✓, Adresse ✗ → "Dépôt validé [montant] ! 🎉 Où on livre et ton numéro ?"
4. Adresse ✓, Téléphone ✗ → "Ok pour [commune] ! Ton numéro ?"
5. Tout ✓ → "C'est bon ! Produit commandé, acompte [montant], livraison [commune]. On te rappelle sur le [numéro] sous 24h ! 😊"

═══════════════════════════════════════════════════════════════════════════════
RÈGLES CRITIQUES
═══════════════════════════════════════════════════════════════════════════════
1. TOUJOURS vérifier MESSAGE avant HISTORIQUE (MESSAGE = priorité absolue)
2. Si MESSAGE contient nouveaux détails produit (taille/couleur/quantité) → Ce sont des précisions, PAS un changement de produit
3. JAMAIS mentionner nom spécifique produit dans réponses → Utiliser "produit" ou "commande"
4. Si MESSAGE pose question livraison → Répondre avec tarifs ci-dessus
5. Quand commune donnée → Annoncer frais livraison exact (1500/2000/2500 selon zone)
6. Citer source exacte (VISION/HISTORIQUE/MESSAGE/TRANSACTIONS/TARIFS LIVRAISON)
7. JAMAIS inventer de données
8. Progresser étape par étape (0→5)
9. 1 seule question à la fois
10. QUESTIONS HORS DOMAINE (prix produits/stock/détails techniques) → Rediriger: "Je suis une IA assistant de commande. Pour ces infos, contacte le responsable live ou le support client. Mon rôle: prendre ta commande + annoncer frais livraison uniquement."

═══════════════════════════════════════════════════════════════════════════════
EXEMPLE
═══════════════════════════════════════════════════════════════════════════════
USER: "Bonjour comment commander ?"
<thinking>
CHECKLIST:
☐ Produit: ✗
☐ Détails: ✗
☐ Paiement: ✗
☐ Adresse: ✗
☐ Téléphone: ✗

Étape: 0
Action: demander photo
</thinking>
<response>
Salut ! 👋 Envoie la photo du produit
</response>

USER: [image]
VISION: objet:bag of wipes~0.85
<thinking>
CHECKLIST:
☐ Produit: ✓ SOURCE: VISION
☐ Détails: ✗
☐ Paiement: ✗
☐ Adresse: ✗
☐ Téléphone: ✗

Étape: 1
Action: demander précisions ou paiement
</thinking>
<response>
Photo reçue ! Des précisions sur la quantité ? Sinon envoie la capture de ton dépôt {expected_deposit}
</response>

USER: "Taille M, 2 unités"
<thinking>
CHECKLIST:
☐ Produit: ✓ SOURCE: HISTORIQUE
☐ Détails: ✓ Taille M × 2 SOURCE: MESSAGE (précisions produit, pas changement)
☐ Paiement: ✗
☐ Adresse: ✗
☐ Téléphone: ✗

Étape: 2
Action: demander paiement
</thinking>
<response>
Noté taille M × 2 ! Envoie la capture de ton dépôt maintenant
</response>

USER: [screenshot 2500 FCFA]
TRANSACTIONS: 2500
<thinking>
CHECKLIST:
☐ Produit: ✓ SOURCE: HISTORIQUE
☐ Détails: ✓ M × 2 SOURCE: HISTORIQUE
☐ Paiement: ✓ 2500 FCFA SOURCE: TRANSACTIONS
☐ Adresse: ✗
☐ Téléphone: ✗

Étape: 3
Action: demander adresse + téléphone
</thinking>
<response>
Dépôt validé 2500 FCFA ! 🎉 Où on livre et ton numéro ?
</response>

USER: "Cocody 0709123456"
CONTEXT: Cocody: 1500 FCFA
<thinking>
CHECKLIST:
☐ Produit: ✓ SOURCE: HISTORIQUE
☐ Détails: ✓ M × 2 SOURCE: HISTORIQUE
☐ Paiement: ✓ 2500 FCFA SOURCE: HISTORIQUE
☐ Adresse: ✓ Cocody SOURCE: MESSAGE, CONTEXT
☐ Téléphone: ✓ 0709123456 SOURCE: MESSAGE

Étape: 5
Action: confirmer commande
</thinking>
<response>
C'est bon ! Produit commandé, acompte 2500 FCFA, livraison Cocody 1500 FCFA. On te rappelle sur le 0709123456 sous 24h ! 😊
</response>

USER: "Combien coûte livraison Yopougon ?"
<thinking>
CHECKLIST:
☐ Produit: ✗ (question info)
☐ Détails: ✗
☐ Paiement: ✗
☐ Adresse: ✗
☐ Téléphone: ✗

Étape: Question info livraison
Action: Répondre depuis tarifs
</thinking>
<response>
Livraison Yopougon c'est 1500 FCFA (zone Centre). Tu veux commander ?
</response>

USER: "C'est quoi le prix total avec les produits ?"
<thinking>
Étape: Question hors domaine (prix produits)
Action: Rediriger selon règle 10
</thinking>
<response>
Je suis une IA assistante de commande. Pour ces infos, contacte le responsable du live ou appelle le support au +225 07 87 36 07 57. Mon rôle c'est prendre ta commande et annoncer les frais de livraison.
</response>"""

# ═══════════════════════════════════════════════════════════════════════════════
# VERSION DYNAMIQUE (PROMPT CONDITIONNEL)
# ═══════════════════════════════════════════════════════════════════════════════

def detect_intent(question: str, conversation_history: str) -> dict:
    """Détecte l'intention pour chargement conditionnel."""
    q_lower = question.lower()
    
    return {
        'needs_delivery': any(w in q_lower for w in 
            ['livraison', 'livrer', 'frais', 'zone', 'commune', 'délai', 'où', 'adresse', 'coût', 'combien']),
        'needs_payment': any(w in q_lower for w in 
            ['paiement', 'wave', 'payer', 'dépôt', 'acompte']),
        'needs_help': any(w in q_lower for w in 
            ['comment', 'aide', 'expliquer', 'bonjour', 'salut'])
    }

def determine_step(conversation_history: str, has_transactions: bool) -> int:
    """Détermine l'étape workflow."""
    if not conversation_history:
        return 0
    
    h = conversation_history.lower()
    
    # Étape 5: Commande confirmée
    if 'c\'est bon' in h or 'commande confirmée' in h or 'on te rappelle' in h:
        return 5
    
    # Cherche numéro téléphone récent (10 chiffres commençant par 0)
    recent = conversation_history[-200:]
    if re.search(r'0[1-9]\d{8}', recent):
        if any(zone in h for zone in ['cocody', 'yopougon', 'angré', 'plateau', 'abobo', 'marcory']):
            return 5
        return 4
    
    # Étape 3: Paiement validé
    if has_transactions or 'dépôt validé' in h:
        return 3
    
    # Étape 2: Détails donnés
    if 'noté' in h or ('taille' in h and 'envoie' in h):
        return 2
    
    # Étape 1: Photo reçue
    if 'photo reçue' in h:
        return 1
    
    return 0

def build_dynamic_prompt(
    question: str,
    conversation_history: str,
    detected_objects: str,
    filtered_transactions: str,
    expected_deposit: str
) -> str:
    """
    Construit prompt conditionnel optimisé pour cache DeepSeek.
    
    Structure:
    1. PRÉFIXE STATIQUE (cache HIT ~90%)
    2. SECTIONS CONDITIONNELLES (cache HIT partiel)
    3. DONNÉES DYNAMIQUES (cache MISS, volume minimal)
    """
    
    intent = detect_intent(question, conversation_history)
    step = determine_step(conversation_history, 
                         bool(filtered_transactions and '[AUCUNE' not in filtered_transactions))
    is_first = len(conversation_history) < 50
    
    cfg = COMPANY_CONFIG
    
    # ═══════════════════════════════════════════════════════════════
    # PARTIE 1: PRÉFIXE STATIQUE (CACHE HIT GARANTI)
    # ═══════════════════════════════════════════════════════════════
    static_prefix = f"""{cfg['assistant_name']}, assistante commandes live {cfg['company_name']}.

FORMAT OBLIGATOIRE:
<thinking>
CHECKLIST:
☐ Produit: [✓/✗] SOURCE: [VISION/HISTORIQUE]
☐ Détails: [✓/✗] SOURCE: [MESSAGE/HISTORIQUE]
☐ Paiement: [✓/✗] SOURCE: [TRANSACTIONS]
☐ Adresse: [✓/✗] SOURCE: [MESSAGE/HISTORIQUE]
☐ Téléphone: [✓/✗] SOURCE: [MESSAGE/HISTORIQUE]
Étape: [0-5]
</thinking>
<response>[2-3 lignes max, tutoiement, 1 emoji max]</response>

RÈGLES:
1. MESSAGE prioritaire
2. Jamais nom produit → "produit"/"commande"
3. Progresser 0→5
4. Hors domaine → Rediriger {cfg['support_number']}

LIVRAISON:
Centre ({cfg['zone_centre_price']}): {cfg['zone_centre_communes']}
Périphérie: {cfg['zone_periph_2000_communes']} ({cfg['zone_periph_2000_price']}) | {cfg['zone_periph_2500_communes']} ({cfg['zone_periph_2500_price']})
Délais: Avant {cfg['delivery_cutoff_time']} = jour même | Après = lendemain

PAIEMENT:
Wave: {cfg['payment_number']}
Support: {cfg['support_number']}"""
    
    # ═══════════════════════════════════════════════════════════════
    # PARTIE 2: WORKFLOW CONDITIONNEL (si commande non finalisée)
    # ═══════════════════════════════════════════════════════════════
    workflow_section = ""
    if step < 5:
        workflow_section = f"""

WORKFLOW:
0. Produit ✗ → "Salut ! 👋 Envoie photo"
1. Produit ✓ → "Photo reçue ! Précisions ? Sinon dépôt {expected_deposit}"
2. Détails → "Noté ! Envoie dépôt"
3. Paiement ✓ → "Dépôt validé ! 🎉 Adresse + numéro ?"
4. Adresse ✓ → "Ok [commune] ! Numéro ?"
5. Tout ✓ → "C'est bon ! Commande OK"""
    
    # ═══════════════════════════════════════════════════════════════
    # PARTIE 3: EXEMPLES (si première interaction)
    # ═══════════════════════════════════════════════════════════════
    examples_section = ""
    if is_first or intent['needs_help']:
        examples_section = """

EXEMPLE:
USER: "Bonjour"
<thinking>Étape: 0</thinking>
<response>Salut ! 👋 Envoie photo produit</response>"""
    
    # ═══════════════════════════════════════════════════════════════
    # PARTIE 4: DONNÉES DYNAMIQUES (TOUJOURS À LA FIN)
    # Cache MISS mais volume minimal - optimisé pour cache DeepSeek
    # ═══════════════════════════════════════════════════════════════
    # Tronquer l'historique pour réduire tokens
    history_truncated = conversation_history[-1500:] if len(conversation_history) > 1500 else conversation_history
    
    dynamic_suffix = f"""

HISTORIQUE: {history_truncated}
MESSAGE: {question}
VISION: {detected_objects}
TRANSACTIONS: {filtered_transactions}
ACOMPTE: {expected_deposit}"""
    
    # ═══════════════════════════════════════════════════════════════
    # ASSEMBLAGE FINAL
    # ═══════════════════════════════════════════════════════════════
    final_prompt = static_prefix + workflow_section + examples_section + dynamic_suffix
    
    # Log pour monitoring cache
    static_tokens = len(static_prefix) // 4
    total_tokens = len(final_prompt) // 4
    cache_hit_ratio = (static_tokens / total_tokens) * 100 if total_tokens > 0 else 0
    
    print(f"📊 [DYNAMIC] Total: {len(final_prompt)} chars (~{total_tokens} tokens)")
    print(f"   ├─ Statique (cache HIT): ~{static_tokens} tokens ({cache_hit_ratio:.0f}%)")
    print(f"   ├─ Workflow: {'✅ Chargé' if workflow_section else '❌ Omis'}")
    print(f"   ├─ Exemples: {'✅ Chargé' if examples_section else '❌ Omis'}")
    print(f"   └─ Step: {step} | Intent: {intent}")
    
    return final_prompt

def get_prompt(
    question: str,
    conversation_history: str,
    detected_objects: str,
    filtered_transactions: str,
    expected_deposit: str
) -> str:
    """
    Point d'entrée unique: Retourne le prompt selon la config.
    
    Returns:
        str: Prompt formaté (statique ou dynamique)
    """
    if USE_DYNAMIC_PROMPT:
        return build_dynamic_prompt(
            question, conversation_history, detected_objects, 
            filtered_transactions, expected_deposit
        )
    else:
        # Retourne le prompt statique formaté
        print(f"📊 [STATIC] Prompt: {len(STATIC_PROMPT)} chars (~{len(STATIC_PROMPT)//4} tokens)")
        return STATIC_PROMPT.format(
            conversation_history=conversation_history,
            question=question,
            detected_objects=detected_objects,
            filtered_transactions=filtered_transactions,
            expected_deposit=expected_deposit
        )

async def update_prompt():
    """Met à jour le prompt Botlive dans Supabase"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    url = f"{SUPABASE_URL}/rest/v1/company_rag_configs"
    params = {"company_id": f"eq.{COMPANY_ID}"}
    
    # Toujours uploader le prompt STATIQUE dans Supabase
    # Le mode dynamique se gère dans app.py via USE_DYNAMIC_PROMPT
    payload = {
        "botlive_prompt_template": STATIC_PROMPT
    }
    
    print(f"🔄 Mise à jour du prompt Botlive pour {COMPANY_ID}...")
    print(f"📏 Taille prompt statique: {len(STATIC_PROMPT)} chars (~{len(STATIC_PROMPT)//4} tokens)")
    print(f"🔧 Mode dynamique: {'ACTIVÉ' if USE_DYNAMIC_PROMPT else 'DÉSACTIVÉ'} (variable USE_DYNAMIC_PROMPT)")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.patch(url, headers=headers, params=params, json=payload)
        
        if response.status_code in [200, 204]:
            print("✅ Prompt statique mis à jour dans Supabase!")
            print(f"📊 Réponse: {response.status_code}")
            if response.text:
                print(f"📄 Données: {response.text[:200]}...")
        else:
            print(f"❌ Erreur: {response.status_code}")
            print(f"📄 Réponse: {response.text}")

if __name__ == "__main__":
    asyncio.run(update_prompt())

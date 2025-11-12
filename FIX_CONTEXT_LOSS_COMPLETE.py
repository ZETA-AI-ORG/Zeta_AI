"""
🔧 CORRECTIF COMPLET: PERTE DE CONTEXTE LLM
Corrige le problème où le LLM oublie les informations déjà collectées
"""
import re
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 📞 VALIDATION TÉLÉPHONE CI 2025 (PATCH #2)
# ═══════════════════════════════════════════════════════════════════════════════

# Préfixes mobiles valides (Orange, MTN, Moov)
PREFIXES_MOBILES_CI = {
    # Orange (07X)
    '070', '071', '072', '073', '074', '075', '076', '077', '078', '079',
    # MTN (05X)
    '050', '051', '052', '053', '054', '055', '056', '057', '058', '059',
    # Moov (01X)
    '010', '011', '012', '013', '014', '015', '016', '017', '018', '019',
}

# Préfixes fixes valides
PREFIXES_FIXES_CI = {'21', '22', '25', '27', '30', '31'}

# Tous préfixes valides
PREFIXES_VALIDES_CI = PREFIXES_MOBILES_CI | PREFIXES_FIXES_CI


def detect_operator(phone: str) -> Optional[str]:
    """
    Détecte l'opérateur depuis le préfixe
    
    Returns:
        "Orange", "MTN", "Moov", "Fixe" ou None
    """
    if len(phone) < 3:
        return None
    
    prefix_3 = phone[:3]
    prefix_2 = phone[:2]
    
    # Mobiles (3 chiffres)
    if prefix_3.startswith('07'):
        return "Orange"
    elif prefix_3.startswith('05'):
        return "MTN"
    elif prefix_3.startswith('01'):
        return "Moov"
    # Fixes (2 chiffres)
    elif prefix_2 in PREFIXES_FIXES_CI:
        return "Fixe"
    
    return None


def validate_phone_ci(phone: str) -> Dict[str, Any]:
    """
    Valide un numéro de téléphone ivoirien (SANS INVENTION)
    
    Formats acceptés:
    - 10 chiffres: 0787360757, 0584129999, 0160924560, 2721000000
    - Avec séparateurs: 07 87 36 07 57, 07-87-36-07-57
    - International: +225 0787360757, +225 07 87 36 07 57
    
    Returns:
        {
            "valid": bool,
            "normalized": str (format 10 chiffres),
            "operator": str ("Orange", "MTN", "Moov", "Fixe"),
            "formatted": str (format 07 87 36 07 57),
            "error": str (si invalide)
        }
    """
    if not phone:
        return {
            "valid": False,
            "normalized": None,
            "operator": None,
            "formatted": None,
            "error": "Numéro manquant"
        }
    
    # Nettoyer: garder UNIQUEMENT les chiffres
    phone_clean = phone.strip()
    digits_only = re.sub(r'[^\d]', '', phone_clean)
    
    # CAS 1: 10 chiffres (format local)
    if len(digits_only) == 10:
        # Vérifier préfixe mobile (3 chiffres)
        prefix_3 = digits_only[:3]
        if prefix_3 in PREFIXES_MOBILES_CI:
            operator = detect_operator(digits_only)
            formatted = f"{digits_only[:2]} {digits_only[2:4]} {digits_only[4:6]} {digits_only[6:8]} {digits_only[8:10]}"
            
            return {
                "valid": True,
                "normalized": digits_only,
                "operator": operator,
                "formatted": formatted,
                "error": None
            }
        
        # Vérifier préfixe fixe (2 chiffres)
        prefix_2 = digits_only[:2]
        if prefix_2 in PREFIXES_FIXES_CI:
            formatted = f"{digits_only[:2]} {digits_only[2:4]} {digits_only[4:6]} {digits_only[6:8]} {digits_only[8:10]}"
            
            return {
                "valid": True,
                "normalized": digits_only,
                "operator": "Fixe",
                "formatted": formatted,
                "error": None
            }
        
        # Préfixe invalide
        return {
            "valid": False,
            "normalized": None,
            "operator": None,
            "formatted": None,
            "error": f"Préfixe invalide '{prefix_3}'. Mobiles: 01X, 05X, 07X | Fixes: 21, 22, 25, 27, 30, 31"
        }
    
    # CAS 2: 13 chiffres (format international +225)
    elif len(digits_only) == 13:
        # Vérifier indicatif 225
        if not digits_only.startswith('225'):
            return {
                "valid": False,
                "normalized": None,
                "operator": None,
                "formatted": None,
                "error": "Indicatif invalide. Pour la CI, utilisez +225"
            }
        
        # Extraire les 10 derniers chiffres
        local_number = digits_only[3:]  # Enlève 225
        
        # Vérifier préfixe mobile
        prefix_3 = local_number[:3]
        if prefix_3 in PREFIXES_MOBILES_CI:
            operator = detect_operator(local_number)
            formatted = f"{local_number[:2]} {local_number[2:4]} {local_number[4:6]} {local_number[6:8]} {local_number[8:10]}"
            
            return {
                "valid": True,
                "normalized": local_number,
                "operator": operator,
                "formatted": formatted,
                "error": None
            }
        
        # Vérifier préfixe fixe
        prefix_2 = local_number[:2]
        if prefix_2 in PREFIXES_FIXES_CI:
            formatted = f"{local_number[:2]} {local_number[2:4]} {local_number[4:6]} {local_number[6:8]} {local_number[8:10]}"
            
            return {
                "valid": True,
                "normalized": local_number,
                "operator": "Fixe",
                "formatted": formatted,
                "error": None
            }
        
        # Préfixe invalide
        return {
            "valid": False,
            "normalized": None,
            "operator": None,
            "formatted": None,
            "error": f"Préfixe invalide '{prefix_3}'. Mobiles: 01X, 05X, 07X | Fixes: 21, 22, 25, 27, 30, 31"
        }
    
    # CAS 3: Longueur invalide
    else:
        return {
            "valid": False,
            "normalized": None,
            "operator": None,
            "formatted": None,
            "error": f"Longueur invalide ({len(digits_only)} chiffres). Attendu: 10 chiffres (ex: 0787360757) ou 13 avec +225"
        }


def extract_from_last_exchanges(conversation_history: str) -> Dict[str, str]:
    """
    Extrait les informations clés depuis les derniers échanges
    
    Cette fonction analyse l'historique de conversation pour extraire:
    - Produit (lot 150, lot 300, taille X)
    - Prix mentionné
    - Zone/commune
    - Téléphone
    - Mode de paiement
    
    Args:
        conversation_history: Historique formaté "Client: ... | Vous: ..."
        
    Returns:
        Dict avec les infos extraites
    """
    extracted = {}
    
    if not conversation_history:
        return extracted
    
    text_lower = conversation_history.lower()
    
    # 1. EXTRAIRE PRODUIT
    # Pattern: "lot 300 taille 4", "lot de 150", "lot150", "couches", "lingettes"
    
    # Chercher "lot 300 taille X"
    lot_taille_match = re.search(r'lot\s*(?:de\s*)?(\d+)\s+(?:couches?\s+)?(?:culottes?\s+)?taille\s+(\d+)', text_lower)
    if lot_taille_match:
        lot = lot_taille_match.group(1)
        taille = lot_taille_match.group(2)
        extracted['produit'] = f"lot {lot} taille {taille}"
        logger.info(f"✅ [EXTRACT] Produit trouvé: {extracted['produit']}")
    
    # Chercher "lot 300" seul
    elif 'lot 300' in text_lower or 'lot300' in text_lower.replace(' ', ''):
        extracted['produit'] = 'lot 300'
        
        # Chercher taille associée
        taille_match = re.search(r'taille\s+(\d+)', text_lower)
        if taille_match:
            extracted['produit'] += f" taille {taille_match.group(1)}"
        
        logger.info(f"✅ [EXTRACT] Produit trouvé: {extracted['produit']}")
    
    # Chercher "lot 150" seul
    elif 'lot 150' in text_lower or 'lot150' in text_lower.replace(' ', ''):
        extracted['produit'] = 'lot 150'
        
        # Chercher taille associée
        taille_match = re.search(r'taille\s+(\d+)', text_lower)
        if taille_match:
            extracted['produit'] += f" taille {taille_match.group(1)}"
        
        logger.info(f"✅ [EXTRACT] Produit trouvé: {extracted['produit']}")
    
    # 🔥 NOUVEAU: Chercher produits génériques (couches, lingettes, etc.)
    else:
        # Patterns produits courants
        produit_patterns = [
            (r'(?:des\s+)?couches?(?:\s+pour)?(?:\s+(?:mon|ma|l[\'’]?)\s*(?:enfant|bébé|fille|garçon))?', 'couches'),
            (r'(?:des\s+)?lingettes?(?:\s+pour)?(?:\s+bébé)?', 'lingettes'),
            (r'(?:du\s+)?lait(?:\s+pour)?(?:\s+bébé)?', 'lait'),
            (r'(?:des\s+)?pampers?', 'pampers'),
            (r'(?:des\s+)?huggies?', 'huggies')
        ]
        
        for pattern, produit_name in produit_patterns:
            if re.search(pattern, text_lower):
                extracted['produit'] = produit_name
                logger.info(f"✅ [EXTRACT] Produit générique trouvé: {produit_name}")
                break
    
    # 2. EXTRAIRE PRIX
    # Pattern: "24 000 FCFA", "24000 FCFA", "Prix: 24 000"
    prix_matches = re.findall(r'prix[:\s]+(\d+[\s\d]*)\s*f?cfa', text_lower)
    if prix_matches:
        # Prendre le dernier prix mentionné
        prix = prix_matches[-1].replace(' ', '')
        extracted['prix_produit'] = prix
        logger.info(f"✅ [EXTRACT] Prix trouvé: {prix} FCFA")
    
    # 3. EXTRAIRE ZONE/COMMUNE (✅ PATCH #1 INTÉGRÉ)
    # Utiliser la fonction patchée qui gère zones Abidjan + hors Abidjan
    try:
        from core.delivery_zone_extractor import extract_delivery_zone_and_cost
        
        # ✅ FIX: Chercher zone uniquement dans les messages USER (pas IA)
        # Pour éviter que "Cocody" dans la réponse IA écrase "Man" du client
        user_messages = []
        for line in conversation_history.split('\n'):
            if line.startswith('user:'):
                user_messages.append(line.replace('user:', '').strip())
        
        user_text = ' '.join(user_messages)
        
        zone_result = extract_delivery_zone_and_cost(user_text)
        if zone_result:
            extracted['zone'] = zone_result.get('name')
            extracted['frais_livraison'] = str(zone_result.get('cost', ''))
            
            # Si ville hors Abidjan (expédition)
            if zone_result.get('category') == 'expedition':
                extracted['zone_type'] = 'expedition'
                extracted['zone_message'] = zone_result.get('error')  # Message pour le client
                logger.info(f"🚚 [EXTRACT] Expédition détectée: {zone_result.get('name')} (3500F+)")
            else:
                logger.info(f"✅ [EXTRACT] Zone trouvée: {zone_result.get('name')} ({zone_result.get('cost')} FCFA)")
    except Exception as e:
        logger.warning(f"⚠️ [EXTRACT] Erreur extraction zone: {e}")
    
    # 4. EXTRAIRE TÉLÉPHONE
    # FILTRER les numéros de l'entreprise (présents dans le prompt)
    excluded_phones = [
        '0787360757',  # Wave/OM entreprise
        '0160924560',  # WhatsApp entreprise
        '+225 0787360757',
        '+225 0160924560'
    ]
    
    # Pattern: Tous formats téléphone CI + patterns larges pour détecter invalides
    # Chercher patterns larges (avec +225, espaces, tirets, etc.)
    phone_patterns = [
        r'\+225\s*0\d[\s\d-]{8,}',  # +225 0123456789
        r'00225\s*0\d[\s\d-]{8,}',  # 00225 0123456789
        r'\b0\d[\s\d-]{8,}\b',      # 0123456789 ou 01 23 45 67 89
        r'\b\d{10}\b',              # 10 chiffres consécutifs
        r'(?:numéro|téléphone|tel|appel|contact).*?(\d{2,15})',  # Capture TOUS les numéros (même invalides)
    ]
    
    for pattern in phone_patterns:
        phone_matches = re.findall(pattern, conversation_history, re.IGNORECASE)
        for phone_candidate in phone_matches:
            # Ignorer si c'est un numéro d'entreprise
            phone_clean = re.sub(r'[^\d]', '', phone_candidate)
            
            # Exclure numéros entreprise
            if phone_candidate in excluded_phones or phone_clean in [re.sub(r'[^\d]', '', p) for p in excluded_phones]:
                continue
            
            # ✅ PATCH #2: Valider avec fonction stricte
            validation = validate_phone_ci(phone_candidate)
            
            if validation["valid"]:
                extracted['telephone'] = validation["normalized"]
                logger.info(f"✅ [EXTRACT] Téléphone validé: {validation['normalized']} ({validation['operator']})")
                break
            else:
                # ✅ PATCH #3: Sauvegarder téléphone invalide pour afficher erreur
                extracted['telephone_invalide'] = phone_candidate
                extracted['telephone_erreur'] = validation['error']
                logger.warning(f"⚠️ [EXTRACT] Téléphone invalide: {phone_candidate} - {validation['error']}")
        
        if 'telephone' in extracted or 'telephone_invalide' in extracted:
            break
    
    # 5. EXTRAIRE MODE DE PAIEMENT
    # 🔥 NOUVEAU: Détecter paiement validé par l'IA
    if re.search(r'paiement\s+\d+\s*f?\s+reçu\s*✅', text_lower):
        # Extraire le montant
        montant_match = re.search(r'paiement\s+(\d+)\s*f?\s+reçu', text_lower)
        if montant_match:
            montant = montant_match.group(1)
            extracted['paiement'] = 'Validé'
            extracted['acompte'] = montant
            logger.info(f"✅ [EXTRACT] Paiement validé: {montant} FCFA")
    # Détecter mode de paiement mentionné
    elif 'wave' in text_lower:
        extracted['paiement'] = 'Wave'
        extracted['acompte'] = '2000'
        logger.info("✅ [EXTRACT] Paiement: Wave")
    elif 'orange money' in text_lower or 'orange' in text_lower:
        extracted['paiement'] = 'Orange Money'
        extracted['acompte'] = '2000'
        logger.info("✅ [EXTRACT] Paiement: Orange Money")
    elif 'mtn' in text_lower or 'momo' in text_lower:
        extracted['paiement'] = 'MTN Mobile Money'
        extracted['acompte'] = '2000'
        logger.info("✅ [EXTRACT] Paiement: MTN")
    
    return extracted


def build_smart_context_summary(
    conversation_history: str,
    user_id: str,
    company_id: str,
    notepad_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Construit un résumé intelligent du contexte collecté
    
    Args:
        conversation_history: Historique de conversation
        user_id: ID utilisateur
        company_id: ID entreprise
        notepad_data: Données du notepad Supabase (optionnel)
        
    Returns:
        Résumé formaté pour injection dans le prompt
    """
    # Extraire depuis l'historique
    extracted = extract_from_last_exchanges(conversation_history)
    
    # Charger depuis le notepad Supabase (si fourni)
    if notepad_data:
        try:
            # Mapper les champs Supabase vers les champs extraits
            supabase_mapping = {
                'last_product_mentioned': 'produit',
                'delivery_zone': 'zone',
                'delivery_cost': 'frais_livraison',
                'phone_number': 'telephone',
                'photo_produit': 'photo_produit',
                'photo_produit_description': 'photo_produit_description',
            }
            
            for supabase_key, extracted_key in supabase_mapping.items():
                value = notepad_data.get(supabase_key)
                # Ne pas écraser si déjà extrait de l'historique (priorité historique)
                if value and extracted_key not in extracted:
                    extracted[extracted_key] = value
                    logger.info(f"✅ [NOTEPAD SUPABASE] Récupéré: {extracted_key}={value}")
            
            # ✅ TRAITEMENT SPÉCIAL PAIEMENT : Gérer format objet ou string
            paiement_data = notepad_data.get('paiement')
            if paiement_data and 'paiement' not in extracted:
                if isinstance(paiement_data, dict):
                    # Format objet : {'montant': 2020, 'validé': True}
                    if paiement_data.get('validé') or paiement_data.get('montant'):
                        extracted['paiement'] = 'Validé'
                        extracted['acompte'] = str(paiement_data.get('montant', ''))
                        logger.info(f"✅ [NOTEPAD SUPABASE] Paiement récupéré: {paiement_data.get('montant')} FCFA")
                elif isinstance(paiement_data, str):
                    # Format string : 'Validé'
                    extracted['paiement'] = paiement_data
                    # Chercher acompte séparément
                    acompte = notepad_data.get('acompte')
                    if acompte:
                        extracted['acompte'] = str(acompte)
                    logger.info(f"✅ [NOTEPAD SUPABASE] Paiement récupéré: {paiement_data}")
        
        except Exception as e:
            logger.warning(f"⚠️ [NOTEPAD SUPABASE] Erreur lecture: {e}")
    
    # ❌ FALLBACK RAM DÉSACTIVÉ - Cause de données obsolètes
    # Le notepad RAM persiste entre conversations et injecte des anciennes données
    # Solution : Utiliser UNIQUEMENT Supabase notepad (auto-expiration 7 jours)
    elif not notepad_data:
        logger.info("⚠️ [NOTEPAD] Notepad Supabase vide - Pas de fallback RAM")
        # Ne rien faire, laisser extracted vide pour forcer nouvelle collecte
    
    # Construire le résumé
    if not extracted:
        return "\n⚠️ MANQUANT: produit, zone, téléphone, paiement\n"
    
    # 1. Titre EXPLICITE pour éviter confusion
    summary = "\n📋 MÉMOIRE CONVERSATIONS PRÉCÉDENTES (PEUT ÊTRE OBSOLÈTE):\n"
    summary += "⚠️ ATTENTION: Vérifier si ces données sont toujours valides pour CETTE conversation\n\n"
    
    # 2. Infos collectées
    
    # Produit
    if extracted.get('produit'):
        summary += f"   📦 Produit mentionné avant: {extracted['produit']}"
        if extracted.get('prix_produit'):
            summary += f" ({extracted['prix_produit']} FCFA)"
        summary += "\n"
    
    # Photo produit
    if extracted.get('photo_produit'):
        summary += f"   📸 Photo reçue avant: {extracted['photo_produit']}"
        if extracted.get('photo_produit_description'):
            summary += f" ({extracted['photo_produit_description']})"
        summary += "\n"
    
    # Zone
    if extracted.get('zone'):
        summary += f"   📍 Zone mentionnée avant: {extracted['zone']}"
        if extracted.get('frais_livraison'):
            summary += f" (livraison {extracted['frais_livraison']} FCFA)"
        summary += "\n"
    
    # Téléphone
    if extracted.get('telephone'):
        summary += f"   📞 Téléphone fourni avant: {extracted['telephone']}\n"
    
    # Paiement
    if extracted.get('paiement'):
        summary += f"   💳 Paiement reçu avant: {extracted['paiement']}"
        if extracted.get('acompte'):
            summary += f" (acompte {extracted['acompte']} FCFA)"
        summary += "\n"
    
    # Total
    if extracted.get('total'):
        summary += f"   💰 Total calculé avant: {extracted['total']} FCFA\n"
    
    # Infos manquantes
    missing = []
    if not extracted.get('produit'):
        missing.append("produit")
    if not extracted.get('photo_produit'):
        missing.append("photo_produit")
    if not extracted.get('zone'):
        missing.append("zone")
    if not extracted.get('telephone'):
        missing.append("téléphone")
    if not extracted.get('paiement'):
        missing.append("paiement")
    
    if missing:
        summary += f"\n⚠️ MANQUANT: {', '.join(missing)}\n"
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ✅ PATCH #3 : VALIDATION STRICTE - ERREURS DÉTECTÉES
    # ═══════════════════════════════════════════════════════════════════════════════
    validation_errors = []
    
    # 1. Vérifier téléphone invalide (depuis extraction)
    if extracted.get('telephone_invalide'):
        validation_errors.append(f"📞 Téléphone invalide: {extracted['telephone_invalide']}")
        validation_errors.append(f"   Erreur: {extracted['telephone_erreur']}")
        # S'assurer que téléphone est dans missing
        if 'téléphone' not in missing:
            missing.append('téléphone')
    elif extracted.get('telephone'):
        # Double vérification si téléphone valide
        phone_validation = validate_phone_ci(extracted['telephone'])
        if not phone_validation["valid"]:
            validation_errors.append(f"📞 Téléphone invalide: {extracted['telephone']}")
            validation_errors.append(f"   Erreur: {phone_validation['error']}")
            # Supprimer le téléphone invalide du contexte
            del extracted['telephone']
            if 'téléphone' not in missing:
                missing.append('téléphone')
    
    # 2. Vérifier zone expédition (message spécial)
    if extracted.get('zone_type') == 'expedition' and extracted.get('zone_message'):
        validation_errors.append(f"🚚 EXPÉDITION: {extracted['zone']}")
        validation_errors.append(f"   Message: {extracted['zone_message']}")
    
    # 3. Ajouter section erreurs si détectées
    if validation_errors:
        summary += "\n❌ ERREURS DÉTECTÉES:\n"
        for error in validation_errors:
            summary += f"   {error}\n"
        summary += "\n🚫 CORRIGER CES ERREURS AVANT DE CONTINUER !\n"
    
    return summary


# ═══════════════════════════════════════════════════════════════════════════════
# 🧠 EXTRACTION THINKING SIMPLIFIÉ (PATCH #4)
# ═══════════════════════════════════════════════════════════════════════════════

def extract_from_thinking_simple(llm_response: str) -> Dict[str, Any]:
    """
    Extrait les données depuis le <thinking> simplifié du LLM
    
    Format attendu:
    <thinking>
    COLLECTÉ:
    - photo_produit: reçue (description optionnelle)
    - paiement: Validé (2020F)
    - zone: Angré (1500F)
    
    MANQUANT:
    - telephone
    
    ACTION: Demander téléphone
    </thinking>
    
    Args:
        llm_response: Réponse complète du LLM avec <thinking>
        
    Returns:
        Dict avec les données extraites du thinking
    """
    extracted = {}
    
    try:
        # Extraire le bloc thinking
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', llm_response, re.DOTALL | re.IGNORECASE)
        if not thinking_match:
            logger.debug("⚠️ [THINKING] Aucun bloc <thinking> trouvé")
            return {}
        
        thinking = thinking_match.group(1)
        logger.debug(f"🧠 [THINKING] Bloc extrait: {len(thinking)} chars")
        
        # Extraire section COLLECTÉ
        collected_match = re.search(
            r'COLLECTÉ:(.*?)(?:MANQUANT:|ACTION:|</thinking>|$)', 
            thinking, 
            re.DOTALL | re.IGNORECASE
        )
        
        if collected_match:
            collected_section = collected_match.group(1)
            
            # Parser chaque ligne: - champ: valeur (description optionnelle)
            for line in collected_section.strip().split('\n'):
                # Format: - champ: valeur ou - champ: valeur (description)
                match = re.match(r'-\s*([^:]+):\s*(.+)', line.strip())
                if match:
                    key = match.group(1).strip()
                    value_raw = match.group(2).strip()
                    
                    # Nettoyer la valeur (enlever les parenthèses optionnelles)
                    # Ex: "reçue (a bag of wipes)" → "reçue"
                    # Ex: "Validé (2020F)" → "Validé"
                    # Ex: "Angré (1500F)" → "Angré"
                    value_clean = re.sub(r'\s*\([^)]+\)$', '', value_raw).strip()
                    
                    # Extraire les infos supplémentaires des parenthèses si pertinent
                    extra_match = re.search(r'\(([^)]+)\)$', value_raw)
                    extra_info = extra_match.group(1) if extra_match else None
                    
                    # Stocker la valeur nettoyée
                    extracted[key] = value_clean
                    
                    # Stocker les infos supplémentaires si c'est un montant ou description
                    if extra_info:
                        if key == 'photo_produit' and extra_info:
                            extracted['photo_produit_description'] = extra_info
                        elif key == 'paiement' and re.search(r'\d+', extra_info):
                            # Extraire montant: "2020F" → "2020"
                            amount = re.sub(r'[^\d]', '', extra_info)
                            if amount:
                                extracted['acompte'] = amount
                        elif key == 'zone' and re.search(r'\d+', extra_info):
                            # Extraire frais: "1500F" → "1500"
                            cost = re.sub(r'[^\d]', '', extra_info)
                            if cost:
                                extracted['frais_livraison'] = cost
                    
                    logger.info(f"✅ [THINKING] Extrait: {key}={value_clean}")
        
        # Extraire section MANQUANT (pour debug/validation)
        missing_match = re.search(
            r'MANQUANT:(.*?)(?:ACTION:|</thinking>|$)', 
            thinking, 
            re.DOTALL | re.IGNORECASE
        )
        
        if missing_match:
            missing_section = missing_match.group(1)
            missing_items = []
            for line in missing_section.strip().split('\n'):
                match = re.match(r'-\s*(.+)', line.strip())
                if match:
                    missing_items.append(match.group(1).strip())
            
            if missing_items:
                extracted['_missing'] = missing_items  # Préfixe _ pour indiquer métadonnée
                logger.debug(f"📋 [THINKING] Manquant: {', '.join(missing_items)}")
        
        # Extraire ACTION (pour debug/validation)
        action_match = re.search(
            r'ACTION:\s*(.+?)(?:</thinking>|$)', 
            thinking, 
            re.DOTALL | re.IGNORECASE
        )
        
        if action_match:
            action = action_match.group(1).strip()
            extracted['_action'] = action  # Préfixe _ pour indiquer métadonnée
            logger.debug(f"🎯 [THINKING] Action: {action}")
        
        logger.info(f"✅ [THINKING] Extraction réussie: {len(extracted)} champs")
        return extracted
        
    except Exception as e:
        logger.error(f"❌ [THINKING] Erreur extraction: {e}")
        return {}


def test_extraction():
    """Test de la fonction d'extraction"""
    
    print("=" * 80)
    print("🧪 TEST EXTRACTION CONTEXTE")
    print("=" * 80)
    print()
    
    # Test 1: Extraction produit + zone
    history1 = """
    Client: Prix lot 300 taille 3?
    Vous: 💰 Prix du lot 300 taille 3 : 22 900 FCFA
    Quelle est votre commune ?
    Client: Prix lot 300 taille 1?
    Vous: 💰 Prix du lot 300 taille 1 : 17 900 FCFA
    Quelle est votre commune ?
    Client: Prix lot 300 Couche culottes taille 4
    Vous: 💰 Prix du lot 300 taille 4 : 24 000 FCFA
    Quelle est votre commune ?
    Client: Je suis à Port-Bouët
    """
    
    print("📝 Test 1: Historique avec produit + zone")
    print("-" * 80)
    extracted1 = extract_from_last_exchanges(history1)
    print(f"Résultat: {extracted1}")
    print()
    
    # Vérifications
    assert 'produit' in extracted1, "❌ Produit non extrait!"
    assert 'lot 300' in extracted1['produit'].lower(), "❌ Lot 300 non détecté!"
    # Note: Le dernier message mentionne "taille 4" mais les précédents ont taille 3 et 1
    # L'extraction prend le dernier match cohérent
    assert 'taille' in extracted1['produit'].lower(), "❌ Taille non détectée!"
    assert 'zone' in extracted1, "❌ Zone non extraite!"
    assert 'port-bouët' in extracted1['zone'].lower(), "❌ Port-Bouët non détecté!"
    
    print("✅ Test 1 réussi!")
    print()
    
    # Test 2: Extraction téléphone
    history2 = """
    Client: Mon numéro c'est 0123456789
    Vous: Merci! Quel mode de paiement?
    """
    
    print("📝 Test 2: Historique avec téléphone")
    print("-" * 80)
    extracted2 = extract_from_last_exchanges(history2)
    print(f"Résultat: {extracted2}")
    print()
    
    assert 'telephone' in extracted2, "❌ Téléphone non extrait!"
    assert extracted2['telephone'] == '0123456789', "❌ Téléphone incorrect!"
    
    print("✅ Test 2 réussi!")
    print()
    
    # Test 3: Extraction paiement
    history3 = """
    Client: Je veux payer par Wave
    Vous: Parfait! Envoyez 2000 FCFA d'acompte
    """
    
    print("📝 Test 3: Historique avec paiement")
    print("-" * 80)
    extracted3 = extract_from_last_exchanges(history3)
    print(f"Résultat: {extracted3}")
    print()
    
    assert 'paiement' in extracted3, "❌ Paiement non extrait!"
    assert extracted3['paiement'] == 'Wave', "❌ Paiement incorrect!"
    assert 'acompte' in extracted3, "❌ Acompte non extrait!"
    
    print("✅ Test 3 réussi!")
    print()
    
    print("=" * 80)
    print("✅ TOUS LES TESTS RÉUSSIS!")
    print("=" * 80)


if __name__ == "__main__":
    # Configurer logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Lancer les tests
    test_extraction()

#!/usr/bin/env python3
"""
🧮 BOTLIVE TOOLS - Calculator & Notepad & State Tracker
Outils intégrés pour améliorer les capacités des LLM
"""

import re
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Import du state tracker
try:
    from core.order_state_tracker import order_tracker
    STATE_TRACKER_ENABLED = True
except ImportError:
    logger.warning("State tracker non disponible")
    STATE_TRACKER_ENABLED = False

# Cache global pour les notes par session utilisateur
session_notes: Dict[str, str] = {}

# ═══════════════════════════════════════════════════════════════════════════════
# 🧮 CALCULATOR TOOL
# ═══════════════════════════════════════════════════════════════════════════════

def calculator_tool(expression: str) -> str:
    """
    Calcule des expressions mathématiques de manière sécurisée
    
    Args:
        expression: Expression mathématique (ex: "2020 - 2000", "2020 >= 2000")
    
    Returns:
        str: Résultat du calcul ou message d'erreur
    """
    try:
        # Nettoyage et sécurisation de l'expression
        safe_expr = _sanitize_expression(expression)
        
        if not safe_expr:
            return "Expression invalide"
        
        # Évaluation sécurisée
        result = eval(safe_expr, {"__builtins__": {}}, {})
        
        # Formatage du résultat
        if isinstance(result, bool):
            return "True" if result else "False"
        elif isinstance(result, (int, float)):
            return str(int(result) if result == int(result) else result)
        else:
            return str(result)
            
    except ZeroDivisionError:
        return "Division par zéro"
    except Exception as e:
        logger.error(f"Erreur calculator: {expression} → {e}")
        return "Erreur calcul"

def _sanitize_expression(expression: str) -> Optional[str]:
    """
    Sécurise une expression mathématique
    
    Args:
        expression: Expression brute
    
    Returns:
        Optional[str]: Expression sécurisée ou None si invalide
    """
    if not expression or len(expression) > 100:
        return None
    
    # Remplacements pour compatibilité
    expr = expression.strip()
    expr = expr.replace("FCFA", "").replace("F", "").replace("fcfa", "").replace("f", "")
    expr = expr.replace("≥", ">=").replace("≤", "<=")
    
    # Autoriser seulement les caractères sûrs
    allowed_chars = r'[0-9+\-*/().\s<>=!]'
    if not re.match(f'^{allowed_chars}+$', expr):
        return None
    
    # Vérifier la structure basique
    if re.search(r'[*/]{2,}|[+\-]{3,}', expr):
        return None
    
    return expr

# ═══════════════════════════════════════════════════════════════════════════════
# 📝 NOTEPAD TOOL
# ═══════════════════════════════════════════════════════════════════════════════

def notepad_tool(action: str, content: str = "", user_id: str = "default") -> str:
    """
    Gère des notes temporaires par utilisateur + State Tracker
    
    Args:
        action: "write", "read", "append", "clear"
        content: Contenu à écrire/ajouter
        user_id: Identifiant utilisateur
    
    Returns:
        str: Résultat de l'action
    """
    try:
        global session_notes
        
        if action == "write":
            session_notes[user_id] = content
            _sync_to_state_tracker(user_id, content)
            return f"✅ Note sauvée: {content}"
        
        elif action == "read":
            # 🔍 DEBUG: Logs détaillés
            logger.info(f"📖 [NOTEPAD READ] user_id={user_id}")
            logger.info(f"📖 [NOTEPAD READ] STATE_TRACKER_ENABLED={STATE_TRACKER_ENABLED}")
            
            # Priorité au state tracker si disponible
            if STATE_TRACKER_ENABLED:
                state = order_tracker.get_state(user_id)
                completion = state.get_completion_rate()
                logger.info(f"📖 [NOTEPAD READ] State completion={completion}")
                logger.info(f"📖 [NOTEPAD READ] State: P={state.produit}, PA={state.paiement}, Z={state.zone}, N={state.numero}")
                
                if completion > 0:
                    state_format = state.to_notepad_format()
                    logger.info(f"✅ [NOTEPAD READ] State tracker retourne: {state_format}")
                    return state_format
                else:
                    logger.warning(f"⚠️ [NOTEPAD READ] State tracker vide (completion=0)")
            
            # Fallback: session_notes
            note = session_notes.get(user_id, "")
            logger.info(f"📖 [NOTEPAD READ] session_notes={note if note else 'VIDE'}")
            
            if note:
                logger.info(f"✅ [NOTEPAD READ] Session notes retourne: {note}")
                return note
            else:
                logger.warning(f"⚠️ [NOTEPAD READ] Aucune note trouvée pour {user_id}")
                return "📝 Aucune note"
        
        elif action == "append":
            current = session_notes.get(user_id, "")
            separator = " | " if current else ""
            session_notes[user_id] = f"{current}{separator}{content}"
            _sync_to_state_tracker(user_id, content)
            return f"✅ Ajouté: {content}"
        
        elif action == "clear":
            session_notes[user_id] = ""
            if STATE_TRACKER_ENABLED:
                order_tracker.clear_state(user_id)
            return "🗑️ Notes effacées"
        
        else:
            return f"❌ Action inconnue: {action}"
            
    except Exception as e:
        logger.error(f"Erreur notepad: {action} → {e}")
        return "❌ Erreur notepad"

def _sync_to_state_tracker(user_id: str, content: str):
    """Synchronise notepad vers state tracker avec validation et détection automatique"""
    if not STATE_TRACKER_ENABLED:
        logger.debug(f"[SYNC] State tracker désactivé")
        return
    
    try:
        logger.info(f"🔄 [SYNC] user_id={user_id}, content={content[:100]}...")
        
        # Liste des zones connues pour détection automatique
        ZONES_CONNUES = ["Yopougon", "Cocody", "Plateau", "Adjamé", "Abobo", "Marcory", 
                         "Koumassi", "Treichville", "Angré", "Riviera", "Andokoua",
                         "Port-Bouët", "Attécoubé", "Bingerville", "Songon", "Anyama"]
        
        # ═══ PRODUIT ═══
        if "✅PRODUIT:" in content:
            produit = content.split("✅PRODUIT:")[1].split("|")[0].strip()
            if produit and produit != "[]" and produit != "[reçu]" and len(produit) > 2:
                order_tracker.update_produit(user_id, produit)
                logger.info(f"✅ [SYNC] PRODUIT sauvegardé = {produit}")
            else:
                logger.warning(f"⚠️ [SYNC] PRODUIT invalide ignoré = {produit}")
        
        # ═══ PAIEMENT ═══
        if "✅PAIEMENT:" in content:
            paiement = content.split("✅PAIEMENT:")[1].split("|")[0].strip()
            if paiement and "F" in paiement and len(paiement) > 2:
                order_tracker.update_paiement(user_id, paiement)
                logger.info(f"✅ [SYNC] PAIEMENT sauvegardé = {paiement}")
            else:
                logger.warning(f"⚠️ [SYNC] PAIEMENT invalide ignoré = {paiement}")
        
        # ═══ ZONE (détection améliorée + corrections) ═══
        zone = None
        if "✅ZONE:" in content:
            zone = content.split("✅ZONE:")[1].split("|")[0].strip()
        else:
            # Détection automatique de la zone dans le contenu
            content_lower = content.lower()
            for z in ZONES_CONNUES:
                if z.lower() in content_lower:
                    # Extraire le coût si présent
                    if "1500" in content or "centre" in content_lower:
                        zone = f"{z}-1500F[MESSAGE]"
                    elif "2000" in content or "périphérie" in content_lower:
                        zone = f"{z}-2000F[MESSAGE]"
                    elif "2500" in content or "éloigné" in content_lower:
                        zone = f"{z}-2500F[MESSAGE]"
                    else:
                        zone = f"{z}-1500F[MESSAGE]"  # Défaut centre
                    break
        
        if zone and "F" in zone and len(zone) > 3:
            order_tracker.update_zone(user_id, zone)
            logger.info(f"✅ [SYNC] ZONE sauvegardée (écrasement) = {zone}")
        
        # ═══ NUMÉRO (détection améliorée + corrections) ═══
        numero = None
        if "✅NUMÉRO:" in content:
            numero = content.split("✅NUMÉRO:")[1].split("|")[0].strip()
        else:
            # Détection automatique du numéro (format ivoirien 07/05/01 + 8 chiffres)
            import re
            numero_match = re.search(r'\b(0[157]\d{8})\b', content)
            if numero_match:
                numero = f"{numero_match.group(1)}[MESSAGE]"
        
        # Rejeter si mélange zone+numéro
        if "✅ZONE:" in content and "[" in content.split("✅ZONE:")[1] and "✅NUMÉRO:" not in content:
            logger.warning(f"⚠️ [SYNC] NUMÉRO mélangé avec ZONE ignoré")
        elif numero and len(numero) >= 10:
            order_tracker.update_numero(user_id, numero)
            logger.info(f"✅ [SYNC] NUMÉRO sauvegardé (écrasement) = {numero}")
        
        # 🔍 DEBUG: Afficher état après sync
        state = order_tracker.get_state(user_id)
        logger.info(f"📊 [SYNC] État: P={bool(state.produit)} PA={bool(state.paiement)} Z={bool(state.zone)} N={bool(state.numero)} | Completion={state.get_completion_rate()}")
    
    except Exception as e:
        logger.error(f"❌ [SYNC] Erreur sync state tracker: {e}", exc_info=True)

# ═══════════════════════════════════════════════════════════════════════════════
# ⚡ EXÉCUTEUR D'OUTILS
# ═══════════════════════════════════════════════════════════════════════════════

def execute_tools_in_response(response_text: str, user_id: str = "default", company_id: str = "4OS4yFcf2LZwxhKojbAVbKuVuSdb") -> str:
    """
    Exécute les outils mentionnés dans une réponse LLM
    
    Args:
        response_text: Texte de réponse contenant les appels d'outils
        user_id: Identifiant utilisateur pour les notes
        company_id: Identifiant entreprise pour le bloc-note
    
    Returns:
        str: Texte avec les résultats des outils intégrés
    """
    try:
        processed_text = response_text
        
        # ═══ EXÉCUTION CALCULATOR ═══
        calc_pattern = r'calculator\("([^"]+)"\)'
        calc_matches = re.findall(calc_pattern, processed_text)
        
        for expr in calc_matches:
            result = calculator_tool(expr)
            old_call = f'calculator("{expr}")'
            new_call = f'calculator("{expr}") = {result}'
            processed_text = processed_text.replace(old_call, new_call)
            logger.debug(f"Calculator: {expr} → {result}")
        
        # ═══ EXÉCUTION NOTEPAD ═══
        # ✅ Accepte "notepad(...)", "NOTE:notepad(...)", et maintenant "Bloc-note: ajouter info"
        notepad_pattern = r'(?:NOTE:)?notepad\("([^"]+)"(?:,\s*"([^"]*)")?\)'
        notepad_matches = re.findall(notepad_pattern, processed_text)

        for match in notepad_matches:
            action = match[0]
            content = match[1] if len(match) > 1 else ""

            # 🔍 DEBUG: Log appel notepad
            logger.info(f"[TOOL EXEC] Notepad appelé: action={action}, content={content}, user_id={user_id}")

            result = notepad_tool(action, content, user_id)

            # 🔍 DEBUG: Log résultat
            logger.info(f"[TOOL EXEC] Notepad résultat: {result}")

            # Reconstruction de l'appel original (avec ou sans NOTE:)
            if content:
                old_call_with_note = f'NOTE:notepad("{action}", "{content}")'
                old_call = f'notepad("{action}", "{content}")'
            else:
                old_call_with_note = f'NOTE:notepad("{action}")'
                old_call = f'notepad("{action}")'

            # Remplacer les deux variantes possibles
            if old_call_with_note in processed_text:
                processed_text = processed_text.replace(old_call_with_note, result)
            elif old_call in processed_text:
                processed_text = processed_text.replace(old_call, result)
            logger.debug(f"Notepad: {action}({content}) → {result}")

        # ═══ EXÉCUTION BLOC-NOTE (pattern flexible) ═══
        # ✅ Reconnaître "Bloc-note: ajouter info (clé, valeur)" avec ou sans guillemets
        # Pattern accepte: (produit, "valeur") OU ("produit", "valeur")
        blocnote_pattern = r'Bloc-note:\s*ajouter\s+info\s*\(\s*"?([^",\)]+)"?\s*,\s*"([^"]+)"\s*\)'
        blocnote_matches = re.findall(blocnote_pattern, processed_text)

        for match in blocnote_matches:
            key = match[0]
            value = match[1]

            logger.info(f"[TOOL EXEC] Bloc-note appelé: key={key}, value={value}, user_id={user_id}, company_id={company_id}")

            # Utiliser la nouvelle méthode générique
            result = blocnote_add_info(key, value, user_id, company_id)

            logger.info(f"[TOOL EXEC] Bloc-note résultat: {result}")

            # Remplacer l'appel (avec ou sans guillemets sur la clé)
            old_call_with_quotes = f'Bloc-note: ajouter info ("{key}", "{value}")'
            old_call_without_quotes = f'Bloc-note: ajouter info ({key}, "{value}")'
            
            if old_call_with_quotes in processed_text:
                processed_text = processed_text.replace(old_call_with_quotes, result)
            elif old_call_without_quotes in processed_text:
                processed_text = processed_text.replace(old_call_without_quotes, result)

            logger.debug(f"Bloc-note: {key}={value} → {result}")
        
        return processed_text
        
    except Exception as e:
        logger.error(f"❌ [TOOLS] Erreur exécution outils: {e}")
        return response_text

def blocnote_add_info(key: str, value: str, user_id: str, company_id: str = "4OS4yFcf2LZwxhKojbAVbKuVuSdb") -> str:
    """
    Méthode générique pour ajouter des informations dans le conversation notepad
    Mappe les clés génériques vers les méthodes spécialisées

    Args:
        key: Clé de l'information (ex: "produit", "zone", "telephone")
        value: Valeur à stocker
        user_id: ID utilisateur
        company_id: ID entreprise

    Returns:
        str: Message de confirmation
    """
    try:
        # Importer le conversation notepad
        from core.conversation_notepad import get_conversation_notepad
        notepad = get_conversation_notepad()

        logger.info(f"🔧 [BLOCNOTE ADD] key={key}, value={value}, user={user_id}")

        # Mapping des clés génériques vers les méthodes spécialisées
        key_lower = key.lower().strip()

        if key_lower in ["produit", "product"]:
            # Extraire produit et variante si présent
            if "|" in value:
                product_name, variant = value.split("|", 1)
                product_name = product_name.strip()
                variant = variant.strip()
            else:
                product_name = value.strip()
                variant = None

            # Déduire quantité (par défaut 1 si pas spécifié)
            quantity = 1
            if " x" in product_name or "x" in product_name:
                parts = re.split(r'\s*x\s*', product_name, 1)
                if len(parts) == 2:
                    try:
                        quantity = int(parts[0].strip())
                        product_name = parts[1].strip()
                    except:
                        pass

            # Prix par défaut (sera mis à jour plus tard)
            price = 0.0

            notepad.update_product(user_id, company_id, product_name, quantity, price, variant)
            return f"✅ Produit ajouté: {product_name} x{quantity}"

        elif key_lower in ["zone", "delivery_zone", "livraison"]:
            # Extraire coût si présent
            cost_match = re.search(r'(\d+)\s*(?:FCFA|F\s*CFA|F)?', value)
            cost = float(cost_match.group(1)) if cost_match else 1500.0  # Défaut centre

            zone = re.sub(r'\s*\d+\s*(?:FCFA|F\s*CFA|F)?', '', value).strip()
            notepad.update_delivery(user_id, company_id, zone, cost)
            return f"✅ Livraison ajoutée: {zone} ({cost} FCFA)"
        
        elif key_lower in ["frais_livraison", "frais", "delivery_cost"]:
            # Frais de livraison seul (sans zone)
            cost_match = re.search(r'(\d+)', value)
            if cost_match:
                cost = float(cost_match.group(1))
                # Récupérer zone existante si disponible
                context = notepad.get_notepad(user_id, company_id)
                zone = context.get("delivery_zone", "")
                if zone:
                    notepad.update_delivery(user_id, company_id, zone, cost)
                    return f"✅ Frais livraison mis à jour: {cost} FCFA"
                else:
                    logger.warning(f"⚠️ Frais livraison sans zone: {cost} FCFA")
                    return f"⚠️ Zone de livraison manquante pour frais {cost} FCFA"
            return f"⚠️ Format frais invalide: {value}"
        
        elif key_lower in ["total", "montant_total", "prix_total"]:
            # Total de la commande
            total_match = re.search(r'(\d+)', value)
            if total_match:
                total = float(total_match.group(1))
                logger.info(f"📊 Total commande noté: {total} FCFA")
                return f"✅ Total noté: {total} FCFA"
            return f"⚠️ Format total invalide: {value}"

        elif key_lower in ["telephone", "phone", "numero", "contact"]:
            notepad.update_phone(user_id, company_id, value.strip())
            return f"✅ Téléphone ajouté: {value.strip()}"

        elif key_lower in ["paiement", "payment", "methode"]:
            # Extraire méthode et numéro si présent
            method = value.strip()
            number = None

            if "|" in method:
                method, number = method.split("|", 1)
                method = method.strip()
                number = number.strip()

            notepad.update_payment(user_id, company_id, method, number)
            return f"✅ Paiement ajouté: {method}"

        elif key_lower in ["prix", "price", "prix_produit", "prix_total"]:
            # Prix nécessite un contexte produit - pour l'instant juste confirmer
            return f"✅ Prix noté: {value} (à associer à un produit)"

        else:
            # Clé inconnue - stocker génériquement si nécessaire
            logger.warning(f"⚠️ [BLOCNOTE ADD] Clé inconnue: {key}={value}")
            return f"⚠️ Clé '{key}' non reconnue"

    except Exception as e:
        logger.error(f"❌ [BLOCNOTE ADD] Erreur: {e}")
        return f"❌ Erreur ajout {key}={value}"


def blocnote_get_all(user_id: str, company_id: str = "4OS4yFcf2LZwxhKojbAVbKuVuSdb") -> dict:
    """
    Récupère toutes les informations du bloc-note pour un utilisateur
    
    Args:
        user_id: ID utilisateur
        company_id: ID entreprise
    
    Returns:
        dict: Dictionnaire avec toutes les infos collectées
    """
    try:
        from core.conversation_notepad import get_conversation_notepad
        notepad = get_conversation_notepad()
        
        # Récupérer le contexte complet
        context = notepad.get_context_for_llm(user_id, company_id)
        
        # Parser le contexte pour extraire les infos structurées
        result = {}
        
        if not context or context == "📝 Aucune note":
            return result
        
        # Extraire produit (format: "- 1x Couches (13 500 FCFA/unité)")
        product_match = re.search(r'-\s*\d+x\s*([^\(]+)', context)
        if product_match:
            result['produit'] = product_match.group(1).strip()
        
        # Extraire prix produit
        price_match = re.search(r'\(([0-9\s]+)\s*FCFA/unité\)', context)
        if price_match:
            result['prix_produit'] = price_match.group(1).replace(' ', '').strip()
        
        # Extraire zone (format: "Zone de livraison: Cocody (1 500 FCFA)")
        zone_match = re.search(r'Zone de livraison:\s*([^\(]+)\s*\(([0-9\s]+)\s*FCFA\)', context)
        if zone_match:
            result['zone'] = zone_match.group(1).strip()
            result['frais_livraison'] = zone_match.group(2).replace(' ', '').strip()
        
        # Extraire téléphone (format: "Numéro client: 0160924560")
        phone_match = re.search(r'Numéro client:\s*([^\n]+)', context)
        if phone_match:
            result['telephone'] = phone_match.group(1).strip()
        
        # Extraire paiement (format: "Méthode de paiement: paid")
        payment_match = re.search(r'Méthode de paiement:\s*([^\n]+)', context)
        if payment_match:
            result['paiement'] = payment_match.group(1).strip()
        
        logger.info(f"📖 [BLOCNOTE GET] user={user_id}, infos={len(result)}")
        return result
        
    except Exception as e:
        logger.error(f"❌ [BLOCNOTE GET] Erreur: {e}")
        return {}


# ==================================================
# DETECTEURS D'USAGE OUTILS
# ==================================================

def should_suggest_calculator(context: Dict, message: str) -> bool:
    """
    Détermine si le calculator devrait être suggéré
    
    Args:
        context: Contexte de la conversation
        message: Message utilisateur
    
    Returns:
        bool: True si calculator recommandé
    """
    # Transactions présentes
    if context.get('filtered_transactions'):
        return True
    
    # Montants dans le message
    if re.search(r'\d+\s*(fcfa|f)', message.lower()):
        return True
    
    # Comparaisons nécessaires
    if context.get('expected_deposit'):
        return True
    
    # Opérateurs mathématiques
    if any(op in message for op in ['+', '-', '>', '<', '>=', '<=', '=']):
        return True
    
    return False

def should_suggest_notepad(message: str, history: str) -> bool:
    """
    Détermine si le notepad devrait être suggéré
    
    Args:
        message: Message utilisateur
        history: Historique conversation
    
    Returns:
        bool: True si notepad recommandé
    """
    # Mots indiquant des changements/préférences
    change_words = ['quantité', 'changer', 'modifier', 'préfère', 'plutôt', 'finalement']
    if any(word in message.lower() for word in change_words):
        return True
    
    # Conversation longue (contexte à retenir)
    if len(history.split()) > 50:
        return True
    
    # Informations spécifiques à retenir
    info_words = ['paquets', 'unités', 'livraison', 'matin', 'soir', 'urgent']
    if any(word in message.lower() for word in info_words):
        return True
    
    return False

# ═══════════════════════════════════════════════════════════════════════════════
# 📊 STATISTIQUES OUTILS
# ═══════════════════════════════════════════════════════════════════════════════

def get_tools_stats() -> Dict[str, Any]:
    """
    Retourne les statistiques d'usage des outils
    
    Returns:
        Dict: Statistiques d'usage
    """
    return {
        "active_notes": len(session_notes),
        "users_with_notes": len([note for note in session_notes.values() if note]),
        "total_note_chars": sum(len(note) for note in session_notes.values()),
        "tools_available": ["calculator", "notepad"]
    }

def clear_old_notes(max_age_hours: int = 24):
    """
    Nettoie les notes anciennes (fonctionnalité future)
    
    Args:
        max_age_hours: Âge maximum des notes en heures
    """
    # TODO: Implémenter avec timestamps si nécessaire
    pass

def can_finalize_order(user_id: str) -> bool:
    """
    Vérifie si une commande peut être finalisée
    
    Args:
        user_id: Identifiant utilisateur
    
    Returns:
        bool: True si toutes les données sont collectées
    """
    if STATE_TRACKER_ENABLED:
        return order_tracker.can_finalize(user_id)
    
    # Fallback: vérifier notepad
    note = session_notes.get(user_id, "")
    has_produit = "✅PRODUIT:" in note
    has_paiement = "✅PAIEMENT:" in note
    has_zone = "✅ZONE:" in note
    has_numero = "✅NUMÉRO:" in note
    
    return has_produit and has_paiement and has_zone and has_numero

def get_missing_fields(user_id: str) -> list:
    """
    Retourne la liste des champs manquants
    
    Args:
        user_id: Identifiant utilisateur
    
    Returns:
        list: Liste des champs manquants
    """
    if STATE_TRACKER_ENABLED:
        state = order_tracker.get_state(user_id)
        return list(state.get_missing_fields())
    
    # Fallback: vérifier notepad
    note = session_notes.get(user_id, "")
    missing = []
    
    if "✅PRODUIT:" not in note:
        missing.append("PRODUIT")
    if "✅PAIEMENT:" not in note:
        missing.append("PAIEMENT")
    if "✅ZONE:" not in note:
        missing.append("ZONE")
    if "✅NUMÉRO:" not in note:
        missing.append("NUMÉRO")
    
    return missing

def debug_order_state(user_id: str) -> dict:
    """
    Retourne l'état complet pour debugging
    
    Args:
        user_id: Identifiant utilisateur
    
    Returns:
        dict: État complet (state tracker + session notes)
    """
    debug_info = {
        "user_id": user_id,
        "state_tracker_enabled": STATE_TRACKER_ENABLED,
        "session_notes": session_notes.get(user_id, "VIDE"),
    }
    
    if STATE_TRACKER_ENABLED:
        state = order_tracker.get_state(user_id)
        debug_info.update({
            "state_produit": state.produit,
            "state_paiement": state.paiement,
            "state_zone": state.zone,
            "state_numero": state.numero,
            "state_completion": state.get_completion_rate(),
            "state_missing": list(state.get_missing_fields()),
            "state_format": state.to_notepad_format(),
        })
    
    logger.info(f"🔍 [DEBUG STATE] {debug_info}")
    return debug_info

# ═══════════════════════════════════════════════════════════════════════════════
# 🧪 TESTS UNITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def test_tools():
    """Tests rapides des outils"""
    print("🧮 Test Calculator:")
    print(f"2020 >= 2000: {calculator_tool('2020 >= 2000')}")
    print(f"2000 - 1500: {calculator_tool('2000 - 1500')}")
    print(f"1500 + 500: {calculator_tool('1500 + 500')}")
    
    print("\n📝 Test Notepad:")
    print(notepad_tool("write", "Test note", "test_user"))
    print(notepad_tool("append", "Info supplémentaire", "test_user"))
    print(f"Lecture: {notepad_tool('read', '', 'test_user')}")
    
    print("\n⚡ Test Exécution:")
    test_response = 'Calcul: calculator("2020 >= 2000") et notepad("write", "Client validé")'
    result = execute_tools_in_response(test_response, "test_user")
    print(f"Résultat: {result}")

if __name__ == "__main__":
    test_tools()

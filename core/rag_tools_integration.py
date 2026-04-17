#!/usr/bin/env python3
"""
🔧 RAG TOOLS INTEGRATION - Intégration des outils Botlive dans le RAG Normal
Extraction automatique <thinking> + <response> + Calculator + Notepad + State Tracker
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 EXTRACTION BALISES <thinking> ET <response>
# ═══════════════════════════════════════════════════════════════════════════════

def extract_thinking_and_response(llm_output: str, user_id: str = None, company_id: str = None, source_documents: list = None) -> Tuple[str, str, str]:
    """
    Extrait <thinking>, <response> et exécute les outils dans thinking
    🧠 INTÉGRATION SMART CONTEXT MANAGER (Architecture Hybride)
    
    Args:
        llm_output: Sortie brute du LLM
        user_id: ID utilisateur pour notepad/state tracker
        company_id: ID entreprise pour notepad
        source_documents: Documents sources pour validation anti-hallucination
    
    Returns:
        Tuple[thinking, response_clean, response_with_tools]
        - thinking: Contenu de <thinking> (pour logs)
        - response_clean: Réponse sans balises ni outils
        - response_with_tools: Réponse avec résultats d'outils exécutés
    """
    thinking = ""
    response_clean = llm_output
    has_thinking_tag = False
    has_response_tag = False
    
    try:
        # ═══ EXTRACTION <thinking> ═══
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', llm_output, re.DOTALL | re.IGNORECASE)
        if thinking_match:
            thinking = thinking_match.group(1).strip()
            has_thinking_tag = True
            logger.debug(f"🧠 [THINKING EXTRACTED] {len(thinking)} chars")
            
            # ✅ CRITIQUE: Exécuter outils dans thinking (notepad, calculator)
            # Side-effects uniquement (sync state tracker, etc.)
            if user_id:
                from core.botlive_tools import execute_tools_in_response
                execute_tools_in_response(thinking, user_id, company_id or "default")
                logger.info(f"🔧 [THINKING TOOLS] Outils exécutés pour user {user_id}, company {company_id}")
        
        # ═══ EXTRACTION <response> ═══
        # Amélioration: Support multiligne et espaces autour des balises
        response_match = re.search(r'<response>\s*(.*?)\s*</response>', llm_output, re.DOTALL | re.IGNORECASE)
        if response_match:
            response_clean = response_match.group(1).strip()
            has_response_tag = True
            logger.info(f"✅ [RESPONSE EXTRACTED] {len(response_clean)} chars (avant: {len(llm_output)} chars)")
        else:
            # Fallback: Supprimer <thinking> si pas de <response>
            response_clean = re.sub(r'<thinking>.*?</thinking>', '', llm_output, flags=re.DOTALL | re.IGNORECASE).strip()
            # Vérifier si c'est vraiment absent ou juste mal formaté
            if '<response>' in llm_output.lower():
                logger.warning(f"⚠️ [RESPONSE] Balise <response> détectée mais extraction échouée (format invalide)")
            else:
                # Sortie "plain text" (pas de balises) : ne pas polluer les logs.
                if has_thinking_tag:
                    logger.warning(f"⚠️ [RESPONSE] Pas de balise <response>, fallback nettoyage <thinking>")
        
        # 🧠 SMART CONTEXT MANAGER - Architecture Hybride (4 Cerveaux)
        # Évite double processing si on reçoit déjà une réponse nettoyée (sans <thinking>).
        if user_id and company_id and has_thinking_tag:
            try:
                from core.smart_context_manager import SmartContextManager
                
                context_manager = SmartContextManager(user_id, company_id)
                context_update = context_manager.update_context(
                    thinking_text=thinking,
                    llm_response=response_clean,
                    source_documents=source_documents
                )
                
                logger.info(f"🧠 [SMART_CONTEXT] État: {context_update['state']}")
                logger.info(f"📊 [SMART_CONTEXT] Complétude: {context_update['completeness']*100:.0f}%")
                
                # Alertes si hallucination détectée
                if context_update['validation']['hallucination_risk'] == 'HIGH':
                    logger.error(f"🚨 [SMART_CONTEXT] HALLUCINATION: {context_update['validation']['discrepancies']}")
                
            except Exception as e:
                logger.error(f"❌ [SMART_CONTEXT] Erreur: {e}", exc_info=True)
        
        # ═══ EXÉCUTION OUTILS DANS RESPONSE ═══
        response_with_tools = response_clean
        if user_id:
            from core.botlive_tools import execute_tools_in_response
            response_with_tools = execute_tools_in_response(response_clean, user_id, company_id or "default")
            
            if response_with_tools != response_clean:
                logger.info(f"🔧 [RESPONSE TOOLS] Outils exécutés dans réponse finale")
        
        return thinking, response_clean, response_with_tools
        
    except Exception as e:
        logger.error(f"❌ [EXTRACT] Erreur extraction: {e}", exc_info=True)
        return "", llm_output, llm_output

# ═══════════════════════════════════════════════════════════════════════════════
# 📝 NOTEPAD INTEGRATION (depuis botlive_tools.py)
# ═══════════════════════════════════════════════════════════════════════════════

def get_notepad_content(user_id: str, company_id: str = None) -> str:
    """
    Récupère le contenu du notepad pour un utilisateur
    
    Args:
        user_id: ID utilisateur
        company_id: ID entreprise (requis pour conversation_notepad)
    
    Returns:
        str: Contenu du notepad ou message vide
    """
    try:
        # ✅ UTILISER conversation_notepad (système structuré)
        from core.conversation_notepad import get_conversation_notepad
        
        if not company_id:
            # Fallback: essayer d'extraire company_id du user_id
            # Format: client_hardcore_141018 ou user_id normal
            company_id = "4OS4yFcf2LZwxhKojbAVbKuVuSdb"  # Default
        
        notepad = get_conversation_notepad()
        content = notepad.get_context_for_llm(user_id, company_id)
        
        logger.debug(f"📖 [NOTEPAD READ] user={user_id}, content={content[:100] if content else 'VIDE'}")
        return content if content else "📝 Aucune note"
    except Exception as e:
        logger.error(f"❌ [NOTEPAD READ] Erreur: {e}")
        return "📝 Aucune note"

def save_to_notepad(user_id: str, content: str, action: str = "append") -> bool:
    """
    Sauvegarde dans le notepad
    
    Args:
        user_id: ID utilisateur
        content: Contenu à sauvegarder
        action: "write" (écraser) ou "append" (ajouter)
    
    Returns:
        bool: True si succès
    """
    try:
        from core.botlive_tools import notepad_tool
        result = notepad_tool(action, content, user_id)
        logger.info(f"💾 [NOTEPAD SAVE] user={user_id}, action={action}, result={result}")
        return "✅" in result
    except Exception as e:
        logger.error(f"❌ [NOTEPAD SAVE] Erreur: {e}")
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# 📊 STATE TRACKER INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def get_order_state_summary(user_id: str) -> str:
    """
    Récupère un résumé de l'état de commande pour injection dans le prompt
    
    Args:
        user_id: ID utilisateur
    
    Returns:
        str: Résumé formaté pour le LLM
    """
    try:
        from core.order_state_tracker import order_tracker
        state = order_tracker.get_state(user_id)
        
        summary = f"""
📊 ÉTAT ACTUEL COMMANDE (MÉMOIRE CONTEXTE):
- PRODUIT: {"✅ " + state.produit if state.produit else "❌ manquant"}
- PAIEMENT: {"✅ " + state.paiement if state.paiement else "❌ manquant"}
- ZONE: {"✅ " + state.zone if state.zone else "❌ manquant"}
- NUMÉRO: {"✅ " + state.numero if state.numero else "❌ manquant"}

⚠️ RÈGLES MÉMOIRE:
1. Si champ = ✅ → NE JAMAIS redemander
2. Si client corrige info ✅ → Accuser réception SANS redemander
3. Demander UNIQUEMENT les champs ❌ manquants
4. Si tous ✅ → Finaliser la commande
"""
        logger.debug(f"📊 [STATE] Résumé généré pour {user_id}")
        return summary.strip()
        
    except Exception as e:
        logger.error(f"❌ [STATE] Erreur récupération état: {e}")
        return ""

def can_finalize_order(user_id: str) -> bool:
    """
    Vérifie si une commande peut être finalisée
    
    Args:
        user_id: ID utilisateur
    
    Returns:
        bool: True si toutes les données sont collectées
    """
    try:
        from core.botlive_tools import can_finalize_order as botlive_can_finalize
        return botlive_can_finalize(user_id)
    except Exception as e:
        logger.error(f"❌ [FINALIZE CHECK] Erreur: {e}")
        return False

def get_missing_fields(user_id: str) -> list:
    """
    Retourne les champs manquants pour finaliser
    
    Args:
        user_id: ID utilisateur
    
    Returns:
        list: Liste des champs manquants
    """
    try:
        from core.botlive_tools import get_missing_fields as botlive_get_missing
        return botlive_get_missing(user_id)
    except Exception as e:
        logger.error(f"❌ [MISSING FIELDS] Erreur: {e}")
        return []

# ═══════════════════════════════════════════════════════════════════════════════
# 🧮 CALCULATOR INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def calculate(expression: str) -> str:
    """
    Calcule une expression mathématique de manière sécurisée
    
    Args:
        expression: Expression mathématique
    
    Returns:
        str: Résultat du calcul
    """
    try:
        from core.botlive_tools import calculator_tool
        result = calculator_tool(expression)
        logger.debug(f"🧮 [CALC] {expression} = {result}")
        return result
    except Exception as e:
        logger.error(f"❌ [CALC] Erreur: {e}")
        return "Erreur calcul"

# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 FONCTION PRINCIPALE - TRAITEMENT COMPLET RÉPONSE LLM
# ═══════════════════════════════════════════════════════════════════════════════

def process_llm_response(llm_output: str, user_id: str = None, company_id: str = None, enable_tools: bool = True, source_documents: list = None) -> Dict[str, Any]:
    """
    Traite complètement une réponse LLM avec extraction et outils
    🧠 INTÉGRATION SMART CONTEXT MANAGER + THINKING PARSER + DATA CHANGE TRACKER
    
    Args:
        llm_output: Sortie brute du LLM
        user_id: ID utilisateur pour notepad/state
        company_id: ID entreprise pour notepad
        enable_tools: Activer l'exécution des outils
        source_documents: Documents sources pour validation anti-hallucination
    
    Returns:
        Dict contenant:
        - response: Réponse finale nettoyée
        - thinking: Contenu thinking (pour logs)
        - thinking_parsed: Données YAML parsées du thinking
        - data_changes: Changements détectés
        - tools_executed: Nombre d'outils exécutés
        - state_updated: État mis à jour (bool)
    """
    result = {
        "response": llm_output,
        "thinking": "",
        "thinking_parsed": None,
        "data_changes": None,
        "tools_executed": 0,
        "state_updated": False,
        "raw_output": llm_output
    }
    
    try:
        print(f"🔍 [PROCESS_LLM] enable_tools={enable_tools}, user_id={user_id}")
        
        if not enable_tools or not user_id:
            # Mode simple: juste extraction balises
            print(f"⚠️ [PROCESS_LLM] Mode SIMPLE (enable_tools={enable_tools}, user_id={user_id})")
            thinking, response_clean, _ = extract_thinking_and_response(llm_output, None, None, None)
            result["response"] = response_clean
            result["thinking"] = thinking
            print(f"🔍 [PROCESS_LLM] Thinking extrait (mode simple): {len(thinking)} chars")
            return result
        
        # Mode complet avec outils + Smart Context Manager + Thinking Parser
        print(f"✅ [PROCESS_LLM] Mode COMPLET")
        thinking, response_clean, response_with_tools = extract_thinking_and_response(
            llm_output, user_id, company_id, source_documents
        )
        
        result["response"] = response_with_tools
        result["thinking"] = thinking
        print(f"🔍 [PROCESS_LLM] Thinking extrait (mode complet): {len(thinking)} chars")

        # Si pas de <thinking> dans la sortie, on évite ThinkingParser/Tracker.
        # (Typiquement quand process_llm_response est rappelé sur une réponse déjà nettoyée.)
        if not (thinking or "").strip():
            return result
        
        # 🧠 PUZZLE 5: Parser le thinking YAML
        try:
            from core.thinking_parser import get_thinking_parser
            from core.data_change_tracker import get_data_change_tracker
            
            parser = get_thinking_parser()
            thinking_data = parser.parse_full_thinking(llm_output)
            result["thinking_parsed"] = thinking_data
            
            if thinking_data["success"]:
                logger.info(f"✅ [THINKING_PARSER] Parse réussi: confiance {thinking_data['confiance']['score']}%, complétude {thinking_data['progression']['completude']}")
                
                # 🔄 TRACKER: Comparer avec l'état actuel du notepad
                try:
                    from core.conversation_notepad import get_conversation_notepad
                    notepad_manager = get_conversation_notepad()
                    notepad = notepad_manager.get_notepad(user_id, company_id or "default")
                    current_state = notepad
                    
                    tracker = get_data_change_tracker()
                    
                    # Track changements depuis thinking
                    new_data = tracker.track_thinking_changes(thinking_data, current_state)
                    
                    # Logger l'état après changements
                    tracker.log_current_state(new_data, "État après thinking")
                    
                    result["data_changes"] = tracker.get_changes_history(limit=5)
                    
                    # 💾 CHECKPOINT: Sauvegarder l'état complet
                    try:
                        from core.conversation_checkpoint import get_checkpoint_manager
                        checkpoint_manager = get_checkpoint_manager()
                        
                        checkpoint_id = checkpoint_manager.create_checkpoint(
                            user_id=user_id,
                            company_id=company_id or "default",
                            thinking_data=thinking_data,
                            notepad_data=notepad,
                            metrics={
                                "confiance_score": thinking_data['confiance']['score'],
                                "completude": thinking_data['progression']['completude'],
                                "phase_qualification": thinking_data['strategie_qualification']['phase']
                            }
                        )
                        
                        result["checkpoint_id"] = checkpoint_id
                        logger.info(f"💾 [CHECKPOINT] Sauvegardé: {checkpoint_id}")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ [CHECKPOINT] Erreur sauvegarde: {e}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ [DATA_TRACKER] Erreur tracking: {e}")
                # 🎯 PHASE B/C LINKAGE: Injecter le catalogue complet (vtree) si un produit est détecté
                # Cela permet au LLM de voir les variantes au tour suivant sans attendre une recherche manuelle.
                try:
                    v2_data = thinking_data.get("v2", {})
                    detected_pid = v2_data.get("detected_product")
                    
                    if detected_pid and user_id and company_id:
                        from core.company_catalog_v2_loader import get_company_product_catalog_v2
                        from core.order_state_tracker import order_tracker
                        
                        catalog = get_company_product_catalog_v2(company_id, detected_pid)
                        if catalog:
                            # Tenter d'extraire le vtree (variantes)
                            vtree = catalog.get("vtree") or catalog.get("v") or {}
                            if vtree:
                                vtree_str = json.dumps(vtree, ensure_ascii=False)
                                # Mettre à jour l'ordre avec le vtree pour que Jessica le voie au prochain tour
                                order_tracker.update_produit_details(user_id, vtree_str, source="IA_DETECTION_LINK", confidence=0.95)
                                logger.info(f"🔗 [LINKAGE] Produit '{detected_pid}' détecté -> vtree injecté dans OrderState")
                except Exception as link_e:
                    logger.warning(f"⚠️ [LINKAGE] Erreur injection vtree: {link_e}")

            else:
                logger.warning(f"⚠️ [THINKING_PARSER] Parse échoué: {len(thinking_data.get('parsing_errors', []))} erreurs")
                
        except Exception as e:
            logger.error(f"❌ [THINKING_PARSER] Erreur: {e}")
        
        # Compter outils exécutés
        if response_with_tools != response_clean:
            result["tools_executed"] = response_with_tools.count("calculator(") + response_with_tools.count("notepad(") + response_with_tools.count("Bloc-note:")
        
        # Vérifier si state a été mis à jour
        try:
            from core.order_state_tracker import order_tracker
            state = order_tracker.get_state(user_id)
            result["state_updated"] = state.get_completion_rate() > 0
        except:
            pass
        
        logger.info(f"✅ [PROCESS LLM] Réponse traitée: {len(result['response'])} chars, {result['tools_executed']} outils")
        
        # 🔍 DEBUG: Vérifier le thinking avant retour
        print(f"🔍 [PROCESS_LLM_RETURN] Thinking dans result: {len(result.get('thinking', ''))} chars")
        print(f"🔍 [PROCESS_LLM_RETURN] Contenu thinking: {result.get('thinking', '')[:200]}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ [PROCESS LLM] Erreur traitement: {e}", exc_info=True)
        result["response"] = llm_output  # Fallback: retourner output brut
        return result

# ═══════════════════════════════════════════════════════════════════════════════
# 🎨 FORMATAGE CONTEXTE ENRICHI POUR PROMPT
# ═══════════════════════════════════════════════════════════════════════════════

def enrich_prompt_with_context(base_prompt: str, user_id: str = None, company_id: str = None, include_state: bool = True, include_notepad: bool = True) -> str:
    """
    Enrichit un prompt avec contexte utilisateur (state, notepad)
    🧠 INTÉGRATION SMART CONTEXT MANAGER
    
    Args:
        base_prompt: Prompt de base
        user_id: ID utilisateur
        company_id: ID entreprise
        include_state: Inclure état commande
        include_notepad: Inclure contenu notepad
    
    Returns:
        str: Prompt enrichi
    """
    if not user_id:
        return base_prompt
    
    enrichments = []
    
    try:
        # 🧠 SMART CONTEXT MANAGER - Injection contexte intelligent
        if company_id:
            try:
                from core.smart_context_manager import SmartContextManager
                context_manager = SmartContextManager(user_id, company_id)
                context_summary = context_manager.get_context_summary()
                
                if context_summary:
                    enrichments.append(context_summary)
                    logger.info(f"🧠 [SMART_CONTEXT] Contexte injecté dans prompt")
            except Exception as e:
                logger.error(f"❌ [SMART_CONTEXT] Erreur injection: {e}")
        
        # Ajouter état commande (fallback)
        if include_state and not enrichments:
            state_summary = get_order_state_summary(user_id)
            if state_summary:
                enrichments.append(state_summary)
        
        # Ajouter notepad (fallback)
        if include_notepad and not enrichments:
            notepad_content = get_notepad_content(user_id, company_id)
            if notepad_content and notepad_content != "📝 Aucune note":
                enrichments.append(f"\n📝 NOTES PRÉCÉDENTES:\n{notepad_content}")
        
        if enrichments:
            context_block = "\n\n".join(enrichments)
            enriched_prompt = f"{base_prompt}\n\n{context_block}"
            logger.info(f"🎨 [ENRICH] Prompt enrichi: +{len(context_block)} chars")
            return enriched_prompt
        
    except Exception as e:
        logger.error(f"❌ [ENRICH] Erreur enrichissement: {e}")
    
    return base_prompt

# ═══════════════════════════════════════════════════════════════════════════════
# 🧪 TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_extraction():
    """Test extraction balises"""
    test_output = """
<thinking>
Phase 1: Analyser la demande
- Client demande prix taille 1 et 3
- notepad("write", "✅PRODUIT: Taille 1 + Taille 3")
- calculator("17900 + 22900")
</thinking>

<response>
Bonjour ! Le prix pour la taille 1 est de 17 900 FCFA et pour la taille 3 est de 22 900 FCFA.
Total: calculator("17900 + 22900") FCFA

Souhaitez-vous commander ?
</response>
"""
    
    print("🧪 Test extraction:")
    thinking, clean, with_tools = extract_thinking_and_response(test_output, "test_user")
    print(f"Thinking: {len(thinking)} chars")
    print(f"Clean: {clean[:100]}...")
    print(f"With tools: {with_tools[:100]}...")

if __name__ == "__main__":
    test_extraction()

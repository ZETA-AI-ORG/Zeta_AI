import asyncio
import os

os.environ.setdefault("BOTLIVE_ROUTER_EMBEDDINGS_ENABLED", "true")
os.environ.setdefault("BOTLIVE_V18_ENABLED", "false")

from core.botlive_intent_router import route_botlive_intent
from core.jessica_prompt_segmenter import build_jessica_prompt_segment
from database.supabase_client import get_botlive_prompt


TEST_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"
TEST_USER_ID = "test_isolated_botlive_router_llm"

# ==============================================================================
# PARAMÈTRES LLM OPTIMISÉS PAR MODE
# ==============================================================================
LLM_CONFIGS = {
    "A": {  # Conversationnel
        "temperature": 0.45,
        "max_tokens": 350,
        "top_p": 0.85,
    },
    "B": {  # Produits
        "temperature": 0.28,
        "max_tokens": 320,
        "top_p": 0.8,
    },
    "C": {  # Commande
        "temperature": 0.22,
        "max_tokens": 520,
        "top_p": 0.75,
    },
    "D": {  # SAV
        "temperature": 0.38,
        "max_tokens": 380,
        "top_p": 0.85,
    }
}


async def main():
    question = input("Question à tester (Botlive): ") or "vous êtes situés où ?"

    print("\n=== ETAPE 1: ROUTER EMBEDDINGS ===")
    conversation_history = ""

    routing = await route_botlive_intent(
        company_id=TEST_COMPANY_ID,
        user_id=TEST_USER_ID,
        message=question,
        conversation_history=conversation_history,
        state_compact={
            "photo_collected": False,
            "paiement_collected": False,
            "zone_collected": False,
            "tel_collected": False,
            "tel_valide": False,
            "collected_count": 0,
            "is_complete": False,
        },
    )

    print(f"intent={routing.intent} | mode={routing.mode} | missing={routing.missing_fields} | score={routing.confidence:.2f}")

    print("\n=== ETAPE 2: PROMPT JESSICA SEGMENTE ===")
    botlive_prompt_template = await get_botlive_prompt(TEST_COMPANY_ID)

    segment = build_jessica_prompt_segment(
        base_prompt_template=botlive_prompt_template,
        hyde_result={
            "success": True,
            "intent": routing.intent,
            "confidence": routing.confidence,
            "mode": routing.mode,
            "missing_fields": routing.missing_fields,
            "state": routing.state,
            "raw": routing.debug.get("raw_message", ""),
            "token_info": {
                "source": "router_embeddings",
                "intent_score": routing.debug.get("intent_score"),
            },
        },
        question_with_context=question,
        conversation_history=conversation_history,
        detected_objects_str="",
        filtered_transactions_str="[AUCUNE TRANSACTION VALIDE]",
        expected_deposit_str="2000 FCFA",
        enriched_checklist="[CHECKLIST TEST]",
    )

    format_block = """

FORMAT DE RÉPONSE OBLIGATOIRE - NE PAS IGNORER

Tu DOIS ABSOLUMENT répondre en utilisant EXACTEMENT ce format:

<thinking>
[Ton raisonnement détaillé ici]
</thinking>

<response>
[Ta réponse au client ici - 2-3 lignes max]
</response>

IMPORTANT: Si tu ne respectes pas ce format, ta réponse sera rejetée !
Commence MAINTENANT par <thinking> puis <response>.
"""

    prompt_to_use = segment["prompt"] + format_block

    print("\n=== PROMPT ENVOYE AU LLM (longueur =", len(prompt_to_use), ") ===")
    print(prompt_to_use[:500], "...[tronqué]")

    # ========================================================================
    # APPEL LLM DIRECT VIA llm_health_check.complete
    # ========================================================================
    from core.llm_health_check import complete as llm_complete

    print("\n=== ETAPE 3: APPEL LLM GROQ (APPEL DIRECT) ===")

    # Appel direct, on laisse llm_health_check gérer les paramètres internes
    llm_text, token_usage = await llm_complete(
        prompt_to_use,
        "llama-3.3-70b-versatile",
    )

    print("\n=== REPONSE BRUTE LLM (len =", len(llm_text or ""), ") ===")
    print(llm_text)

    import re
    response_match = re.search(r"<response>(.*?)</response>", llm_text or "", re.DOTALL)
    client_response = response_match.group(1).strip() if response_match else "[Aucune balise <response> trouvée]"

    print("\n=== EXTRAIT <response> POUR LE CLIENT ===")
    print(client_response)

    print("\n=== TOKENS & PROVIDER ===")
    print(token_usage)


if __name__ == "__main__":
    asyncio.run(main())

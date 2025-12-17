import asyncio
import os
import sys

# Ensure project root on sys.path to allow 'core' imports when running directly
_THIS_DIR = os.path.dirname(__file__)
_ROOT_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

os.environ.setdefault("BOTLIVE_ROUTER_EMBEDDINGS_ENABLED", "true")
os.environ.setdefault("BOTLIVE_V18_ENABLED", "false")

from core.botlive_intent_router import route_botlive_intent
from core.jessica_prompt_segmenter import build_jessica_prompt_segment
from database.supabase_client import get_botlive_prompt


TEST_COMPANY_ID = "W27PwOPiblP8TlOrhPcjOtxd0cza"
TEST_USER_ID = "test_isolated_botlive_router_llm"

TEST_QUESTIONS = [
    "Salut",
    "Bjr",
    "Salut vous êtes situés où ?",
    "Bjr c'est combien ?",
    "Hey je veux commander",
    "Bonjour j'ai pas encore reçu ma commande",
    "Bonjour, je veux commander",
    "Où êtes-vous situés exactement ? Vous avez des locaux physiques ?",
    "Je veux des couches Pampers taille 4",
    "Je suis à Abobo",
    "Mon numéro : 0707070707",
    "On paye à la livraison ou c'est avant ?",
    "Je serais livré quand ?",
    "Oui c'est bon, confirmez ma commande",
    "Salut, je suis pas sûr... je pense commander quelque chose",
    "Est-ce que vous avez des produits pour bébés ?",
    "Comment ça marche pour le paiement ? On peut payer à la livraison ?",
    "Et vos locaux, on peut passer directement ?",
    "Ah j'ai vu une photo sur votre page, c'est quoi ce produit ?",
    "Ah oui c'est ça ! Mais je sais pas combien c'est...",
    "Pour le paiement, j'ai fait un transfert hier, mais j'ai pas la preuve exacte",
    "Attendez je cherche... voilà",
    "Pour la livraison, c'est pour Yopougon mais je connais pas le quartier exact",
    "Appelez-moi au 0707070707 si problème",
    "La livraison ça se passe comment ?",
    "Je serais livré aujourd'hui ?",
    "Bon allez je me lance : mon numéro 0707070707 et quartier Yopougon Soké",
    "Bonjour ! Il fait beau aujourd'hui non ? Bref, je voulais vous dire que mon cousin m'a parlé de votre service",
    "Vous êtes où exactement ? C'est une entreprise ou juste une app ?",
    "On peut vous visiter ? J'aime voir les gens avant de commander",
    "Lui il a commandé l'autre fois, il était content. Mais moi je sais pas trop...",
    "En fait c'est pour ma femme, elle est enceinte. Vous avez des trucs pour femmes enceintes ?",
    "Pour le paiement, on fait comment ici ? C'est avant livraison ou après ?",
    "Ah mais je me souviens ! Il me faut du lait 1er âge, c'est ce qu'il m'a dit",
    "Bon pour le paiement, j'ai un souci avec ma banque... j'ai fait 1500F mais c'est peut-être pas assez",
    "D'ailleurs vous livrez à quelle heure ? Parce que je travaille la nuit",
    "Ma zone c'est Cocody mais précisément à Angré, près du carrefour",
    "Mon numéro c'est 0707070707 mais parfois je réponds pas, envoyez un SMS avant",
    "Pardonnez, livrez moi dans 1h s'il vous plaît",
    "Livrez moi ce matin si possible",
    "Bon récapitulons : produit sur la photo, paiement 1500F, livraison Angré, numéro 0707070707. C'est bon ?",
    "Je veux commander... non en fait c'est pour une question d'abord",
    "Vous êtes une entreprise enregistrée ? Où sont vos bureaux ?",
    "On peut payer à la livraison ou c'est obligatoirement avant ?",
    "Combien de temps ça prend pour livrer normalement ?",
    "Je suis à Bouaké, vous pouvez me livrer ?",
    "Ah non pardon, vous expédiez à Yamoussoukro ?",
    "Bon je suis à Abidjan en fait, je me suis trompé",
    "Je veux des couches... ou peut-être du lait... je sais pas",
    "C'est ça que je veux... en fait non, c'est juste pour vous montrer",
    "Pour le paiement j'ai envoyé 5000F hier... ou peut-être 3000F... je vérifie",
    "Attendez je me trompe complètement : en fait je ne veux rien commander aujourd'hui",
    "Finalement si ! Je veux les couches sur la photo que j'ai envoyée au début",
    "Zone : Abobo... non Cocody... définitivement Abobo",
    "Numéro : 0707070707... attendez c'est plus 0606060606... non 0707070707",
    "Paiement : j'ai trouvé la preuve, c'est 2000F",
    "Livrez moi dans l'après-midi merci",
    "Je peux vous envoyer mon livreur ?",
    "Oubliez tout, je recommence : produit = couches, paiement = 2000F, zone = Abobo, tel = 0707070707",
    "C'est final cette fois, envoyez moi le récap",
]

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
    question = input("Question à tester (Botlive) ou 'all' pour suite de tests: ") or "vous êtes situés où ?"

    if question.strip().lower() == "all":
        print("\n=== MODE SUITE TESTS ROUTER SEUL (pas d'appel LLM) ===")
        conversation_history = ""
        for q in TEST_QUESTIONS:
            print("\n--- TEST ---")
            print("QUESTION:", q)
            routing = await route_botlive_intent(
                company_id=TEST_COMPANY_ID,
                user_id=TEST_USER_ID,
                message=q,
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
            print(
                f"intent={routing.intent} | mode={routing.mode} | missing={routing.missing_fields} | score={routing.confidence:.2f}"
            )
        return

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
        routing=routing,
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

    print("\n=== PROMPT COMPLET ENVOYE AU LLM (longueur =", len(prompt_to_use), ") ===")
    print("=" * 80)
    print(prompt_to_use)
    print("=" * 80)

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

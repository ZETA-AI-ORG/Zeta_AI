import sys
import os

# Ajouter le répertoire parent au path pour importer les modules core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.jessica_prompt_segmenter import build_jessica_prompt_segment

def test_enrichment():
    template = """
    [[JESSICA_PROMPT_A_START]]
    Bonjour, je suis {bot_name} de {shop_name}.
    Nous sommes ouverts pendant ces horaires : {support_hours}.
    Voici notre numéro Wave : {wave_number}.
    L'acompte est de {depot_amount}.
    [[JESSICA_PROMPT_A_END]]
    """
    
    company_info = {
        "company_name": "Zeta Testing Shop",
        "ai_name": "Jessica Test",
        "whatsapp_phone": "0123456789",
        "rag_behavior": {
            "support_hours": "09:00 - 18:00",
            "payment": {
                "wave_number": "0707070707",
                "deposit_amount": "5000 FCFA"
            }
        }
    }
    
    hyde_result = {
        "intent": "SALUTATION",
        "confidence": 0.95,
        "mode": "GUIDEUR"
    }
    
    print("--- DÉBUT TEST ENRICHISSEMENT ---")
    
    result = build_jessica_prompt_segment(
        base_prompt_template=template,
        hyde_result=hyde_result,
        question_with_context="Salut",
        conversation_history="",
        detected_objects_str="",
        filtered_transactions_str="",
        expected_deposit_str="2000 FCFA",
        enriched_checklist="",
        company_info=company_info
    )
    
    prompt = result.get("prompt", "")
    print("PROMPT GÉNÉRÉ :")
    print("-" * 20)
    print(prompt)
    print("-" * 20)
    
    # Vérifications
    expected_fragments = [
        "Jessica Test",
        "Zeta Testing Shop",
        "09:00 - 18:00",
        "0707070707",
        "5000 FCFA"
    ]
    
    success = True
    for frag in expected_fragments:
        if frag not in prompt:
            print(f"❌ MANQUANT : {frag}")
            success = False
        else:
            print(f"✅ TROUVÉ : {frag}")
            
    if success:
        print("\n🎉 TEST RÉUSSI : L'enrichissement dynamique fonctionne parfaitement.")
    else:
        print("\n🚨 TEST ÉCHOUÉ : Certains placeholders n'ont pas été remplacés.")

if __name__ == "__main__":
    test_enrichment()

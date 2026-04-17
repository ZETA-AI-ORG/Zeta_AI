import os
import sys
import logging

# Ajouter le chemin du projet pour les imports
sys.path.append(os.getcwd())

from core.botlive_prompts_supabase import get_prompts_manager

# Configuration du logger pour voir les sorties
logging.basicConfig(level=logging.INFO)

def test_prompt_generation(company_id):
    print(f"\n--- 🧪 TEST GÉNÉRATION PROMPT SYSTEM C ---")
    print(f"ID Boutique: {company_id}\n")
    
    manager = get_prompts_manager()
    if not manager:
        print("❌ Erreur: Impossible d'initialiser le PromptsManager.")
        return

    # 1. Vérifer les infos de l'entreprise
    print("--- 📊 Infos Entreprise ---")
    info = manager.get_company_info(company_id)
    if not info:
        print("⚠️ Aucune donnée trouvée pour cette entreprise.")
    else:
        for k, v in info.items():
            if k == 'rag_behavior':
                print(f"  {k}: [Complex Object, size={len(str(v))}]")
            else:
                print(f"  {k}: {v}")

    # 2. Tester les 3 phases
    for p in ["A", "B", "C"]:
        print(f"\n--- 📝 GÉNERATION PHASE {p} ---")
        prompt = manager.get_v2_base_prompt(company_id, company_info=info, phase=p)
        
        # Vérifier la présence des éléments clés
        has_bloc1 = "[[ZETA_CORE_START]]" in prompt or "IDENTITÉ" in prompt or len(prompt) > 2000
        has_phase = f"PHASE {p}" in prompt
        has_boutique_info = info.get('company_name', '---') in prompt
        
        print(f"  Taille totale: {len(prompt)} chars")
        print(f"  Vérif Bloc 1 (Core): {'✅' if has_bloc1 else '❌'}")
        print(f"  Vérif Phase {p} injectée: {'✅' if has_phase else '❌'}")
        print(f"  Vérif Nom Boutique: {'✅' if has_boutique_info else '❌'}")
        
        # Afficher un extrait de la phase injectée
        if has_phase:
            start_idx = prompt.find(f"PHASE {p}")
            print(f"  Extrait Phase: {prompt[start_idx:start_idx+150]}...")

if __name__ == "__main__":
    target_id = "W27PwOPiblP8TlOrhPcjOtxd0cza"
    test_prompt_generation(target_id)

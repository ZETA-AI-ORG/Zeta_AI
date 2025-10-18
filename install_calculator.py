#!/usr/bin/env python3
"""
Script d'installation automatique du module de calcul
Injecte le code de calcul dans universal_rag_engine.py
"""
import re

RAG_ENGINE_PATH = "core/universal_rag_engine.py"

# Code à insérer après la ligne "search_results = await self.search_sequential_sources(query, company_id)"
CALCULATOR_CODE = '''
            # 2.5 NOUVEAU: Détection et exécution de calculs automatiques
            try:
                from core.calculator_engine import calculator
                calc_detection = calculator.detect_calculation_need(query)
                
                if calc_detection['needs_calculation']:
                    print(f"🧮 [CALCUL] Besoin détecté: {calc_detection['calc_type']}")
                    
                    # Extraire les prix du contexte trouvé
                    context_text = search_results.get('meili_context', '') or search_results.get('supabase_context', '')
                    prices_found = calculator.extract_prices_from_context(context_text)
                    
                    calc_result = None
                    calc_type = calc_detection['calc_type']
                    
                    if calc_type == 'multiplication' and prices_found:
                        qty = calc_detection.get('quantity', 1)
                        unit_price = prices_found[0]['unit_price'] if prices_found else 0
                        if unit_price > 0:
                            calc_result = calculator.calculate('multiplication', quantity=qty, unit_price=unit_price)
                    
                    elif calc_type == 'difference' and len(prices_found) >= 2:
                        calc_result = calculator.calculate('difference', price1=prices_found[0]['price'], price2=prices_found[1]['price'])
                    
                    elif calc_type == 'sum' and len(prices_found) >= 2:
                        all_prices = [p['price'] for p in prices_found]
                        calc_result = calculator.calculate('sum', prices=all_prices)
                    
                    elif calc_type == 'division' and prices_found:
                        desired_qty = calc_detection.get('desired_quantity', 0)
                        lot_size = prices_found[0]['quantity'] if prices_found else 0
                        if desired_qty > 0 and lot_size > 0:
                            calc_result = calculator.calculate('division', desired_quantity=desired_qty, lot_size=lot_size)
                    
                    if calc_result and 'error' not in calc_result:
                        calculation_injection = calculator.format_calculation_for_llm(calc_result)
                        # Injecter dans le contexte
                        if search_results.get('meili_context'):
                            search_results['meili_context'] = calculation_injection + "\\n\\n" + search_results['meili_context']
                        elif search_results.get('supabase_context'):
                            search_results['supabase_context'] = calculation_injection + "\\n\\n" + search_results['supabase_context']
                        print(f"✅ [CALCUL] Résultat injecté: {calc_result['result_formatted']}")
            except Exception as e:
                print(f"⚠️ [CALCUL] Erreur: {e}")
'''

def install_calculator():
    """Installe le module de calcul dans le RAG engine"""
    print("📦 Installation du module de calcul...")
    
    # Lire le fichier
    with open(RAG_ENGINE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Vérifier si déjà installé
    if '# 2.5 NOUVEAU: Détection et exécution de calculs automatiques' in content:
        print("✅ Module de calcul déjà installé!")
        return
    
    # Trouver la ligne d'insertion
    pattern = r'(            search_results = await self\.search_sequential_sources\(query, company_id\)\n)'
    
    if not re.search(pattern, content):
        print("❌ Impossible de trouver le point d'insertion!")
        print("   Ligne recherchée: 'search_results = await self.search_sequential_sources(query, company_id)'")
        return
    
    # Insérer le code
    new_content = re.sub(
        pattern,
        r'\1' + CALCULATOR_CODE + '\n',
        content
    )
    
    # Sauvegarder
    with open(RAG_ENGINE_PATH, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Module de calcul installé avec succès!")
    print("   Fichier modifié: core/universal_rag_engine.py")

if __name__ == "__main__":
    try:
        install_calculator()
    except Exception as e:
        print(f"❌ Erreur: {e}")

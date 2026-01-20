# PATCH MANUEL - Module Calculateur

## Fichier: core/universal_rag_engine.py

### Ligne à trouver (environ ligne 683):
```python
# 2. Recherche séquentielle MeiliSearch → Supabase
search_results = await self.search_sequential_sources(query, company_id)

# 3. Génération de réponse avec prompt dynamique
```

### Code à insérer ENTRE les 2 lignes:
```python
# 2. Recherche séquentielle MeiliSearch → Supabase
search_results = await self.search_sequential_sources(query, company_id)

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
                search_results['meili_context'] = calculation_injection + "\n\n" + search_results['meili_context']
            elif search_results.get('supabase_context'):
                search_results['supabase_context'] = calculation_injection + "\n\n" + search_results['supabase_context']
            print(f"✅ [CALCUL] Résultat injecté: {calc_result['result_formatted']}")
except Exception as e:
    print(f"⚠️ [CALCUL] Erreur: {e}")

# 3. Génération de réponse avec prompt dynamique
```

---

## INSTRUCTIONS D'APPLICATION

### Option 1: Éditeur texte (recommandé)
1. Ouvrir `~/ZETA_APP/CHATBOT2.0/core/universal_rag_engine.py` dans nano/vim
2. Chercher la ligne 683 avec `/search_sequential_sources`
3. Copier-coller le code ci-dessus entre les lignes

### Option 2: Sed (automatique mais risqué)
```bash
# NE PAS EXÉCUTER - Exemple seulement
cd ~/ZETA_APP/CHATBOT2.0
# Créer backup d'abord
cp core/universal_rag_engine.py core/universal_rag_engine.py.backup
```

---

## VÉRIFICATION

Après modification, vérifier la syntaxe:
```bash
python -m py_compile core/universal_rag_engine.py
# Si aucune erreur → OK
```

Démarrer le serveur:
```bash
uvicorn app:app --reload
# Si démarre → Succès !
```

#!/bin/bash
# 🎯 SYNCHRONISATION TEST ULTIME DE COHÉRENCE

echo "🎯 Synchronisation du test ultime de cohérence..."

# Synchronisation du test principal
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/test_ultimate_coherence.py" ~/ZETA_APP/CHATBOT2.0/test_ultimate_coherence.py

echo "✅ Synchronisation terminée !"
echo ""
echo "🎯 TEST ULTIME DE COHÉRENCE RAG"
echo "=" * 50
echo "Ce test va:"
echo "✅ Tester MeiliSearch avec des questions mots-clés précis"
echo "✅ Tester Supabase avec des questions sémantiques"
echo "✅ Tester des scénarios hybrides complexes"
echo "✅ Détecter les hallucinations du LLM"
echo "✅ Valider la précision des prix et informations"
echo ""
echo "📊 COMMANDES DE TEST:"
echo ""
echo "# Test ultime complet (11 scénarios):"
echo "python test_ultimate_coherence.py"
echo ""
echo "# Vérifier que l'API fonctionne avant:"
echo "curl -X POST http://127.0.0.1:8001/chat -H \"Content-Type: application/json\" -d '{\"message\":\"test\",\"company_id\":\"MpfnlSbqwaZ6F4HvxQLRL9du0yG3\",\"user_id\":\"test\"}'"
echo ""
echo "🎯 SCÉNARIOS DE TEST:"
echo "1. Prix exacts (taille 3 = 22.900 FCFA)"
echo "2. Livraison zones (Yopougon = 1500 FCFA)"
echo "3. Contact exact (WhatsApp vs Téléphone)"
echo "4. Conseils tailles (bébé 10kg)"
echo "5. Mission entreprise"
echo "6. Optimisation prix (gros volumes)"
echo "7. Calcul total (produit + livraison)"
echo "8. Conseils multiples (jumeaux)"
echo "9. Produits inexistants (couleurs)"
echo "10. Magasin physique (piège)"
echo "11. Paiements (Wave uniquement)"

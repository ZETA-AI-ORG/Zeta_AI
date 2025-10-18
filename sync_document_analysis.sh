#!/bin/bash
# 🔍 SYNCHRONISATION TEST DIAGNOSTIC AVANCÉ

echo "🔍 Synchronisation du test diagnostic avancé..."

# Synchronisation du test d'analyse des documents
cp -v "/mnt/c/Users/hp/Documents/ZETA APP/chatbot/CHATBOT2.0/test_document_analysis.py" ~/ZETA_APP/CHATBOT2.0/test_document_analysis.py

echo "✅ Test diagnostic synchronisé !"
echo ""
echo "🔍 TEST DIAGNOSTIC AVANCÉ - ANALYSE DES DOCUMENTS RAG"
echo "=" * 60
echo ""
echo "🎯 OBJECTIF:"
echo "Déterminer si les hallucinations viennent de:"
echo "1. 📄 Documents non pertinents trouvés par RAG"
echo "2. 🤖 Génération LLM défaillante"
echo "3. 🔍 Recherche qui ne trouve pas les bons documents"
echo ""
echo "🔬 CE QUE LE TEST VA RÉVÉLER:"
echo "✅ Documents exacts trouvés par MeiliSearch/Supabase"
echo "✅ Score de pertinence de chaque document"
echo "✅ Contexte fourni au LLM vs réponse générée"
echo "✅ Mots hallucinés (présents dans réponse mais pas contexte)"
echo "✅ Informations manquantes dans le contexte"
echo ""
echo "📊 QUESTIONS CRITIQUES ANALYSÉES:"
echo "1. Prix taille 3 (attendu: 22.900 FCFA)"
echo "2. Couleur rouge (attendu: pas de couleurs)"
echo "3. Carte bancaire (attendu: Wave uniquement)"
echo "4. Économies couches (attendu: 12 paquets ou colis)"
echo "5. Mission entreprise (attendu: faciliter accès couches)"
echo ""
echo "⚠️ PRÉREQUIS:"
echo "L'API doit retourner les documents en mode debug"
echo "Ajouter 'debug': True dans le payload"
echo ""
echo "🚀 COMMANDE DE LANCEMENT:"
echo "python test_document_analysis.py"

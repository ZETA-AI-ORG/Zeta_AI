"""
Script de test simple pour vérifier :
1. Le remplacement des placeholders (context, history, question)
2. Le prompt final envoyé au LLM
3. La réponse du LLM (parsing de <thinking> et <response>)
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ========================================
# 1. PROMPT SYSTÈME (chargé depuis fichier)
# ========================================
def load_system_prompt():
    """Charge le prompt depuis PROMPT_SYSTEM_FINAL_V2.txt"""
    with open("PROMPT_SYSTEM_FINAL_V2.txt", "r", encoding="utf-8") as f:
        return f.read()

SYSTEM_PROMPT_TEMPLATE = """Tu es Jessica, assistant(e) client de RUEDUGROSSISTE (secteur : Commerce de détail et gros de produits pour bébé - couches).

INFOS CLÉS ENTREPRISE :
- Nom commercial : RUEDUGROSSISTE
- Secteur : Commerce de détail et gros de produits pour bébé (couches)
- Description : Vente en gros et au détail de couches pour bébé
- Adresse : Boutique 100% en ligne (pas de magasin physique)
- Zone(s) de livraison : Abidjan et toutes les grandes villes de Côte d'Ivoire
- WhatsApp : +225 0160924560
- Paiement Wave : +225 0787360757
- Horaires : Toujours ouvert (24/7)

---

<context>
{context}
</context>

<history>
{history}
</history>

<question>
{question}
</question>

---

INFOS À RECUEILLIR AVANT VALIDATION COMMANDE (ordre flexible, toutes obligatoires) :
1. ☐ Produit : Type, Variants, Quantité, Prix exact
2. ☐ Coordonnées : Numéro de téléphone
3. ☐ Livraison : Ville/Commune, Adresse, Frais
4. ☐ Paiement : Wave, Acompte 2 000 FCFA, Solde livraison
5. ☐ Validation : Récapitulatif, Total, Confirmation

---

PROCESSUS DE RAISONNEMENT OBLIGATOIRE :

<thinking>
PHASE 1 - ANALYSE DE LA QUESTION
- Question client : [répéter]
- Type : [prix/disponibilité/livraison/contact/commande/autre]
- Mots-clés : [liste]
- Infos collectées : [liste avec ☑]
- Infos manquantes : [liste avec ☐]

PHASE 2 - COMPARAISON QUESTION ↔ SOURCES
Pour chaque mot-clé :
- <context> : [MATCH ligne X / ABSENT]
- <history> : [MATCH / ABSENT]

Résultat :
  ✓ Mot-clé 1 : MATCH → [citation]
  ✗ Mot-clé 2 : ABSENT

PHASE 3 - VALIDATION STRICTE
- Infos trouvées ? [oui/non]
- Données exactes ? [oui/non]
- Vérifié 2 fois ? [oui/non]
- Certain à 100% ? [oui/non]
- Confiance : [ÉLEVÉ/MOYEN/FAIBLE]
</thinking>

<response>
[Ton message clair et professionnel basé UNIQUEMENT sur <context> et <history>]
</response>

---

RÈGLES CRITIQUES :
1. Prix/Produits/Livraison → <context> UNIQUEMENT
2. Téléphone/Adresse client → <history> UNIQUEMENT
3. NE JAMAIS INVENTER : Si absent, demande clarification
4. Ton chaleureux et professionnel
"""


# ========================================
# 2. SIMULATION DES DONNÉES
# ========================================
def simulate_data():
    """Simule les données qui seraient récupérées en production"""
    
    # Contexte : documents pertinents récupérés par RAG
    context = """PRODUIT: Couches à pression
- Taille 1 (0-4kg): 17 000 FCFA / 300 pièces
- Taille 2 (3-8kg): 18 500 FCFA / 300 pièces
- Taille 3 (6-11kg): 20 500 FCFA / 300 pièces
- Taille 4 (9-14kg): 22 500 FCFA / 300 pièces
- Taille 5 (12-17kg): 24 000 FCFA / 300 pièces
- Taille 6 (17-25kg): 24 500 FCFA / 300 pièces

LIVRAISON:
- Yopougon, Cocody, Plateau: 1 500 FCFA
- Port-Bouët, Bingerville: 2 000 FCFA

NOTES: Vendu UNIQUEMENT par lots de 150 ou 300 pièces."""
    
    # Historique : conversation passée (si existe)
    history = """user: Bonjour
assistant: Bonjour ! Je suis Jessica de RUEDUGROSSISTE. Comment puis-je vous aider aujourd'hui ?"""
    
    # Question actuelle
    question = "Prix d'un lot de 300 couches taille 4 pression?"
    
    return context, history, question


# ========================================
# 3. ASSEMBLAGE DU PROMPT FINAL
# ========================================
def build_final_prompt(context: str, history: str, question: str) -> str:
    """Remplace les placeholders et retourne le prompt final"""
    final_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        context=context,
        history=history,
        question=question
    )
    return final_prompt


# ========================================
# 4. PARSING DE LA RÉPONSE LLM
# ========================================
def parse_llm_response(llm_output: str) -> dict:
    """Extrait <thinking> et <response> de la sortie LLM"""
    import re
    
    # Extraire <thinking>
    thinking_match = re.search(r'<thinking>(.*?)</thinking>', llm_output, re.DOTALL)
    thinking = thinking_match.group(1).strip() if thinking_match else "Non trouvé"
    
    # Extraire <response>
    response_match = re.search(r'<response>(.*?)</response>', llm_output, re.DOTALL)
    response = response_match.group(1).strip() if response_match else llm_output
    
    return {
        "thinking": thinking,
        "response": response
    }


# ========================================
# 5. APPEL LLM (OPTIONNEL - avec Groq)
# ========================================
def call_llm(prompt: str) -> str:
    """Envoie le prompt au LLM et retourne la réponse (optionnel)"""
    try:
        from groq import Groq
        
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        
        return completion.choices[0].message.content
    
    except Exception as e:
        return f"[ERREUR LLM] {str(e)}"


# ========================================
# 6. TEST PRINCIPAL
# ========================================
def main():
    print("="*80)
    print("🧪 TEST ASSEMBLAGE PROMPT + VÉRIFICATION LLM (VERSION V2)")
    print("="*80)
    
    # Charger le prompt depuis le fichier
    print("\n📋 CHARGEMENT DU PROMPT SYSTÈME...")
    print("-"*80)
    global SYSTEM_PROMPT_TEMPLATE
    try:
        SYSTEM_PROMPT_TEMPLATE = load_system_prompt()
        print(f"✅ Prompt chargé depuis PROMPT_SYSTEM_FINAL_V2.txt ({len(SYSTEM_PROMPT_TEMPLATE)} caractères)")
    except FileNotFoundError:
        print("⚠️ Fichier PROMPT_SYSTEM_FINAL_V2.txt non trouvé, utilisation du prompt par défaut")
    
    # Étape 1 : Simuler les données
    print("\n📊 ÉTAPE 1 : SIMULATION DES DONNÉES")
    print("-"*80)
    context, history, question = simulate_data()
    
    print(f"✅ Context récupéré : {len(context)} caractères")
    print(f"✅ History récupéré : {len(history)} caractères")
    print(f"✅ Question : {question}")
    
    # Étape 2 : Assembler le prompt final
    print("\n🔧 ÉTAPE 2 : ASSEMBLAGE DU PROMPT FINAL")
    print("-"*80)
    final_prompt = build_final_prompt(context, history, question)
    print(f"✅ Prompt final assemblé : {len(final_prompt)} caractères")
    
    # Afficher un extrait du prompt final
    print("\n📋 EXTRAIT DU PROMPT FINAL (premiers 1000 caractères) :")
    print("-"*80)
    print(final_prompt[:1000] + "...")
    
    # Vérifier que les placeholders ont été remplacés
    print("\n✅ VÉRIFICATION DES PLACEHOLDERS :")
    print("-"*80)
    if "{context}" in final_prompt:
        print("❌ ERREUR : {context} n'a pas été remplacé !")
    else:
        print("✅ {context} remplacé correctement")
    
    if "{history}" in final_prompt:
        print("❌ ERREUR : {history} n'a pas été remplacé !")
    else:
        print("✅ {history} remplacé correctement")
    
    if "{question}" in final_prompt:
        print("❌ ERREUR : {question} n'a pas été remplacé !")
    else:
        print("✅ {question} remplacé correctement")
    
    # Étape 3 : Appeler le LLM (si clé API disponible)
    print("\n🤖 ÉTAPE 3 : APPEL LLM (optionnel)")
    print("-"*80)
    
    if os.getenv("GROQ_API_KEY"):
        print("🔄 Envoi du prompt au LLM...")
        llm_output = call_llm(final_prompt)
        
        # Parser la réponse
        parsed = parse_llm_response(llm_output)
        
        print("\n📊 RÉPONSE LLM BRUTE (premiers 500 caractères) :")
        print("-"*80)
        print(llm_output[:500] + "...")
        
        print("\n🧠 <thinking> EXTRAIT :")
        print("-"*80)
        print(parsed["thinking"][:500] + "..." if len(parsed["thinking"]) > 500 else parsed["thinking"])
        
        print("\n💬 <response> EXTRAIT (à envoyer au client) :")
        print("-"*80)
        print(parsed["response"])
        
        # Vérifier si le LLM voit bien les données
        print("\n✅ VÉRIFICATION : LE LLM VOIT-IL LES DONNÉES ?")
        print("-"*80)
        if "22 500" in llm_output or "22500" in llm_output:
            print("✅ Le LLM a bien vu le prix dans <context> (22 500 FCFA)")
        else:
            print("⚠️ Le LLM n'a pas mentionné le prix exact")
        
        if "taille 4" in llm_output.lower():
            print("✅ Le LLM a bien vu 'taille 4' dans <context>")
        else:
            print("⚠️ Le LLM n'a pas mentionné 'taille 4'")
        
        if "300" in llm_output:
            print("✅ Le LLM a bien vu '300 pièces' dans <context>")
        else:
            print("⚠️ Le LLM n'a pas mentionné '300'")
    
    else:
        print("⚠️ GROQ_API_KEY non trouvée dans .env")
        print("   Pour tester l'appel LLM, ajoute GROQ_API_KEY dans .env")
    
    print("\n" + "="*80)
    print("✅ TEST TERMINÉ")
    print("="*80)


if __name__ == "__main__":
    main()

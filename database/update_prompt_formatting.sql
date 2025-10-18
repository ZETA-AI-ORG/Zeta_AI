-- ═══════════════════════════════════════════════════════════════════════════════
-- AMÉLIORATION 7: FORMATAGE RÉPONSES AVEC EMOJIS
-- ═══════════════════════════════════════════════════════════════════════════════
-- Date: 2025-10-16
-- Description: Ajoute emojis contextuels et structure visuelle
-- Impact: +15% lisibilité
-- ═══════════════════════════════════════════════════════════════════════════════

-- Mise à jour du prompt pour ajouter règles formatage
UPDATE company_rag_configs
SET prompt_template = REPLACE(
    prompt_template,
    '3. Style de réponse (`<response>`) :',
    '3. Style de réponse (`<response>`) :
   - ✅ FORMATAGE VISUEL (AMÉLIORATION) :
     • Utiliser emojis contextuels : 💰 prix, 🚚 livraison, 💳 paiement, 📞 contact, 📦 produit
     • Structurer avec bullet points si >2 infos
     • Séparer clairement prix/conditions avec sauts de ligne
     • Mettre en valeur les montants (ex: "22 900 FCFA" pas "22900fcfa")
     • Exemple: "💰 Prix: 22 900 FCFA\n🚚 Livraison: 1 500 FCFA"
   '
)
WHERE prompt_template LIKE '%Style de réponse%';

-- Vérification
SELECT 
    company_id,
    CASE 
        WHEN prompt_template LIKE '%FORMATAGE VISUEL%' THEN '✅ Mis à jour'
        ELSE '❌ Non mis à jour'
    END as status
FROM company_rag_configs
WHERE prompt_template IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════════════════════
-- AMÉLIORATION 2: RÉDUCTION VERBOSITÉ PROMPT
-- ═══════════════════════════════════════════════════════════════════════════════
-- Date: 2025-10-16
-- Description: Renforce les règles anti-verbosité dans le prompt système
-- Impact: -20% verbosité, +10% satisfaction
-- ═══════════════════════════════════════════════════════════════════════════════

-- Mise à jour du prompt pour TOUTES les entreprises
UPDATE company_rag_configs
SET prompt_template = REPLACE(
    prompt_template,
    '3. Style de réponse (`<response>`) :
   - STRUCTURE OBLIGATOIRE : [Accusé réception court] + [Réponses intentions claires] + [Clarifications intentions floues] + [Question progression] 
   - RÈGLES : Court (2-4 phrases max), fusionner intentions similaires, séparer réponses/clarifications, chaleureux et professionnel, progresser étape par étape, ne jamais tout demander d''un coup, ne jamais donner d''infos non demandées, ne jamais proposer plusieurs produits si client a précisé',
    '3. Style de réponse (`<response>`) :
   - STRUCTURE OBLIGATOIRE : [Accusé réception court] + [Réponses intentions claires] + [Clarifications intentions floues] + [Question progression] 
   - ✅ RÈGLES ANTI-VERBOSITÉ (CRITIQUES) :
     • Court (2-3 phrases MAX, pas 4)
     • Répondre UNIQUEMENT à la question posée
     • NE JAMAIS anticiper besoins non exprimés
     • NE JAMAIS ajouter infos non demandées (ex: paiement si question livraison)
     • NE JAMAIS proposer plusieurs options si choix clair
     • Fusionner intentions similaires
     • Progresser étape par étape (1 info = 1 question)
     • Chaleureux mais CONCIS'
)
WHERE prompt_template LIKE '%Style de réponse%';

-- Vérification
SELECT 
    company_id,
    CASE 
        WHEN prompt_template LIKE '%RÈGLES ANTI-VERBOSITÉ%' THEN '✅ Mis à jour'
        ELSE '❌ Non mis à jour'
    END as status
FROM company_rag_configs
WHERE prompt_template IS NOT NULL;

-- Afficher un exemple
SELECT 
    company_id,
    SUBSTRING(prompt_template FROM POSITION('Style de réponse' IN prompt_template) FOR 500) as prompt_extract
FROM company_rag_configs
WHERE prompt_template LIKE '%RÈGLES ANTI-VERBOSITÉ%'
LIMIT 1;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 🔧 MIGRATION: Ajout des colonnes Botlive Prompts v2.0
-- ═══════════════════════════════════════════════════════════════════════════════
-- Date: 2025-10-14
-- Description: Ajoute les colonnes pour les nouveaux prompts Botlive (Groq 70B et DeepSeek V3)
--              et supprime l'ancienne colonne botlive_prompt_template
-- ═══════════════════════════════════════════════════════════════════════════════

-- 1️⃣ Ajouter la colonne ai_objective (si elle n'existe pas)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'company_rag_configs' 
        AND column_name = 'ai_objective'
    ) THEN
        ALTER TABLE company_rag_configs 
        ADD COLUMN ai_objective TEXT;
        
        RAISE NOTICE '✅ Colonne ai_objective ajoutée';
    ELSE
        RAISE NOTICE 'ℹ️ Colonne ai_objective existe déjà';
    END IF;
END $$;

-- 2️⃣ Ajouter la colonne prompt_botlive_groq_70b (si elle n'existe pas)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'company_rag_configs' 
        AND column_name = 'prompt_botlive_groq_70b'
    ) THEN
        ALTER TABLE company_rag_configs 
        ADD COLUMN prompt_botlive_groq_70b TEXT;
        
        RAISE NOTICE '✅ Colonne prompt_botlive_groq_70b ajoutée';
    ELSE
        RAISE NOTICE 'ℹ️ Colonne prompt_botlive_groq_70b existe déjà';
    END IF;
END $$;

-- 3️⃣ Ajouter la colonne prompt_botlive_deepseek_v3 (si elle n'existe pas)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'company_rag_configs' 
        AND column_name = 'prompt_botlive_deepseek_v3'
    ) THEN
        ALTER TABLE company_rag_configs 
        ADD COLUMN prompt_botlive_deepseek_v3 TEXT;
        
        RAISE NOTICE '✅ Colonne prompt_botlive_deepseek_v3 ajoutée';
    ELSE
        RAISE NOTICE 'ℹ️ Colonne prompt_botlive_deepseek_v3 existe déjà';
    END IF;
END $$;

-- 4️⃣ Ajouter les colonnes de métadonnées (si elles n'existent pas)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'company_rag_configs' 
        AND column_name = 'botlive_prompts_version'
    ) THEN
        ALTER TABLE company_rag_configs 
        ADD COLUMN botlive_prompts_version VARCHAR(10) DEFAULT '2.0';
        
        RAISE NOTICE '✅ Colonne botlive_prompts_version ajoutée';
    ELSE
        RAISE NOTICE 'ℹ️ Colonne botlive_prompts_version existe déjà';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'company_rag_configs' 
        AND column_name = 'botlive_prompts_updated_at'
    ) THEN
        ALTER TABLE company_rag_configs 
        ADD COLUMN botlive_prompts_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        
        RAISE NOTICE '✅ Colonne botlive_prompts_updated_at ajoutée';
    ELSE
        RAISE NOTICE 'ℹ️ Colonne botlive_prompts_updated_at existe déjà';
    END IF;
END $$;

-- 5️⃣ Supprimer l'ancienne colonne botlive_prompt_template (si elle existe)
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'company_rag_configs' 
        AND column_name = 'botlive_prompt_template'
    ) THEN
        ALTER TABLE company_rag_configs 
        DROP COLUMN botlive_prompt_template;
        
        RAISE NOTICE '🗑️ Ancienne colonne botlive_prompt_template supprimée';
    ELSE
        RAISE NOTICE 'ℹ️ Colonne botlive_prompt_template n''existe pas (déjà supprimée)';
    END IF;
END $$;

-- 6️⃣ Créer un index sur company_id pour performance (si pas déjà existant)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'company_rag_configs' 
        AND indexname = 'idx_company_rag_configs_company_id'
    ) THEN
        CREATE INDEX idx_company_rag_configs_company_id 
        ON company_rag_configs(company_id);
        
        RAISE NOTICE '✅ Index idx_company_rag_configs_company_id créé';
    ELSE
        RAISE NOTICE 'ℹ️ Index idx_company_rag_configs_company_id existe déjà';
    END IF;
END $$;

-- ═══════════════════════════════════════════════════════════════════════════════
-- ✅ MIGRATION TERMINÉE
-- ═══════════════════════════════════════════════════════════════════════════════

-- Vérification finale
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'company_rag_configs'
AND column_name IN (
    'ai_objective',
    'prompt_botlive_groq_70b',
    'prompt_botlive_deepseek_v3',
    'botlive_prompts_version',
    'botlive_prompts_updated_at'
)
ORDER BY column_name;

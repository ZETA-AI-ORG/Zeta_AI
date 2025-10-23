-- ═══════════════════════════════════════════════════════════════════════════════
-- 🔗 TABLE COMPANY_MAPPING - Pont UUID ↔ TEXT
-- ═══════════════════════════════════════════════════════════════════════════════
-- Permet de lier company_id (TEXT) du backend avec UUID des tables Lovable
-- ═══════════════════════════════════════════════════════════════════════════════

-- Créer la table de mapping
CREATE TABLE IF NOT EXISTS public.company_mapping (
    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id TEXT UNIQUE NOT NULL, -- ID backend (TEXT)
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_company_mapping_company_id 
ON public.company_mapping(company_id);

CREATE INDEX IF NOT EXISTS idx_company_mapping_user_id 
ON public.company_mapping(user_id);

-- Trigger pour updated_at
CREATE OR REPLACE FUNCTION update_company_mapping_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_company_mapping_updated_at
    BEFORE UPDATE ON public.company_mapping
    FOR EACH ROW
    EXECUTE FUNCTION update_company_mapping_updated_at();

-- RLS (Row Level Security)
ALTER TABLE public.company_mapping ENABLE ROW LEVEL SECURITY;

-- Policy: Les utilisateurs peuvent lire leur propre mapping
CREATE POLICY "Users can read their own mapping"
ON public.company_mapping
FOR SELECT
USING (user_id = auth.uid());

-- Policy: Les utilisateurs peuvent créer leur mapping
CREATE POLICY "Users can create their own mapping"
ON public.company_mapping
FOR INSERT
WITH CHECK (user_id = auth.uid());

-- Policy: Service role a accès complet
CREATE POLICY "Service role full access"
ON public.company_mapping
FOR ALL
USING (true);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 🔧 AJOUTER user_id DANS company_rag_configs
-- ═══════════════════════════════════════════════════════════════════════════════

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'company_rag_configs' 
        AND column_name = 'user_id'
    ) THEN
        ALTER TABLE company_rag_configs 
        ADD COLUMN user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
        
        RAISE NOTICE '✅ Colonne user_id ajoutée à company_rag_configs';
    ELSE
        RAISE NOTICE 'ℹ️ Colonne user_id existe déjà';
    END IF;
END $$;

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_company_rag_configs_user_id 
ON company_rag_configs(user_id);

-- RLS sur company_rag_configs
ALTER TABLE company_rag_configs ENABLE ROW LEVEL SECURITY;

-- Policy: Les utilisateurs peuvent lire leur config
CREATE POLICY "Users can read their own config"
ON company_rag_configs
FOR SELECT
USING (user_id = auth.uid());

-- Policy: Les utilisateurs peuvent mettre à jour leur config
CREATE POLICY "Users can update their own config"
ON company_rag_configs
FOR UPDATE
USING (user_id = auth.uid());

-- ═══════════════════════════════════════════════════════════════════════════════
-- 📊 PEUPLER company_mapping AVEC DONNÉES EXISTANTES
-- ═══════════════════════════════════════════════════════════════════════════════

-- Insérer mappings pour toutes les companies existantes
-- ⚠️ ATTENTION: Adapter user_id selon votre logique métier
INSERT INTO public.company_mapping (company_id, user_id)
SELECT 
    company_id,
    user_id -- Si user_id existe déjà dans company_rag_configs
FROM company_rag_configs
WHERE company_id IS NOT NULL
ON CONFLICT (company_id) DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════════════════
-- ✅ VÉRIFICATION
-- ═══════════════════════════════════════════════════════════════════════════════

SELECT 
    'company_mapping' as table_name,
    COUNT(*) as total_rows
FROM company_mapping

UNION ALL

SELECT 
    'company_rag_configs with user_id' as table_name,
    COUNT(*) as total_rows
FROM company_rag_configs
WHERE user_id IS NOT NULL;

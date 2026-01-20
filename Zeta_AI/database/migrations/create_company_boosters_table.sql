-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE: company_boosters
-- Stocke les boosters extraits pour chaque entreprise
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.company_boosters (
    id BIGSERIAL PRIMARY KEY,
    company_id TEXT NOT NULL UNIQUE,
    
    -- Keywords globaux
    keywords TEXT[] DEFAULT '{}',
    
    -- Catégories structurées (JSONB pour flexibilité)
    categories JSONB DEFAULT '{}'::jsonb,
    
    -- Filtres rapides
    filters JSONB DEFAULT '{}'::jsonb,
    
    -- Métadonnées
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour recherche rapide par company_id
CREATE INDEX IF NOT EXISTS idx_company_boosters_company_id 
ON public.company_boosters(company_id);

-- Index GIN pour recherche dans keywords
CREATE INDEX IF NOT EXISTS idx_company_boosters_keywords 
ON public.company_boosters USING GIN(keywords);

-- Index GIN pour recherche dans categories
CREATE INDEX IF NOT EXISTS idx_company_boosters_categories 
ON public.company_boosters USING GIN(categories);

-- Index GIN pour recherche dans filters
CREATE INDEX IF NOT EXISTS idx_company_boosters_filters 
ON public.company_boosters USING GIN(filters);

-- ═══════════════════════════════════════════════════════════════════════════════
-- RLS (Row Level Security)
-- ═══════════════════════════════════════════════════════════════════════════════

ALTER TABLE public.company_boosters ENABLE ROW LEVEL SECURITY;

-- Policy: Les utilisateurs peuvent lire leurs propres boosters
CREATE POLICY "Users can read their own boosters"
ON public.company_boosters
FOR SELECT
USING (
    company_id IN (
        SELECT company_id 
        FROM public.user_companies 
        WHERE user_id = auth.uid()
    )
);

-- Policy: Les utilisateurs peuvent insérer leurs propres boosters
CREATE POLICY "Users can insert their own boosters"
ON public.company_boosters
FOR INSERT
WITH CHECK (
    company_id IN (
        SELECT company_id 
        FROM public.user_companies 
        WHERE user_id = auth.uid()
    )
);

-- Policy: Les utilisateurs peuvent mettre à jour leurs propres boosters
CREATE POLICY "Users can update their own boosters"
ON public.company_boosters
FOR UPDATE
USING (
    company_id IN (
        SELECT company_id 
        FROM public.user_companies 
        WHERE user_id = auth.uid()
    )
);

-- Policy: Les utilisateurs peuvent supprimer leurs propres boosters
CREATE POLICY "Users can delete their own boosters"
ON public.company_boosters
FOR DELETE
USING (
    company_id IN (
        SELECT company_id 
        FROM public.user_companies 
        WHERE user_id = auth.uid()
    )
);

-- Policy: Service role peut tout faire (pour ingestion backend)
CREATE POLICY "Service role can do everything"
ON public.company_boosters
FOR ALL
USING (auth.jwt() ->> 'role' = 'service_role');

-- ═══════════════════════════════════════════════════════════════════════════════
-- FONCTION: Mise à jour automatique du timestamp
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION update_company_boosters_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_company_boosters_updated_at
BEFORE UPDATE ON public.company_boosters
FOR EACH ROW
EXECUTE FUNCTION update_company_boosters_updated_at();

-- ═══════════════════════════════════════════════════════════════════════════════
-- COMMENTAIRES
-- ═══════════════════════════════════════════════════════════════════════════════

COMMENT ON TABLE public.company_boosters IS 'Boosters de recherche extraits automatiquement pour chaque entreprise';
COMMENT ON COLUMN public.company_boosters.keywords IS 'Liste de mots-clés globaux pour boost recherche';
COMMENT ON COLUMN public.company_boosters.categories IS 'Boosters organisés par catégorie (PRODUIT, LIVRAISON, PAIEMENT, CONTACT, ENTREPRISE)';
COMMENT ON COLUMN public.company_boosters.filters IS 'Filtres rapides (price_range, delivery_zones, payment_methods, product_names)';

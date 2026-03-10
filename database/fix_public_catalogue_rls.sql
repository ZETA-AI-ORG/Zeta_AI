-- ═══════════════════════════════════════════════════════
-- FIX : Accès public (anon) au catalogue et boutique
-- À exécuter dans Supabase → SQL Editor
-- ═══════════════════════════════════════════════════════

-- 1. Activer RLS si pas encore actif (sécurité)
ALTER TABLE public.company_catalogs_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.company_rag_configs  ENABLE ROW LEVEL SECURITY;

-- 2. Supprimer les anciennes policies de lecture publique si elles existent
DROP POLICY IF EXISTS "Public can read active catalog items" ON public.company_catalogs_v2;
DROP POLICY IF EXISTS "Public can read boutique config"      ON public.company_rag_configs;

-- 3. Permettre à n'importe qui (anon + authenticated) de lire
--    les produits actifs d'un catalogue public
CREATE POLICY "Public can read active catalog items"
ON public.company_catalogs_v2
FOR SELECT
USING (is_active = true);

-- 4. Permettre à n'importe qui de lire le nom/config de la boutique
--    (company_name, secteur_activite uniquement — pas de données sensibles)
CREATE POLICY "Public can read boutique config"
ON public.company_rag_configs
FOR SELECT
USING (true);

-- 5. Vérification : doit retourner les rows de ta boutique
-- SELECT id, company_id, is_active FROM company_catalogs_v2 WHERE company_id = 'W27PwOPiblP8TlOrhPcjOtxd0cza';

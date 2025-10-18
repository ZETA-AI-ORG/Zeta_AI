-- Supprimer l'ancienne fonction si elle existe
DROP FUNCTION IF EXISTS public.match_company_documents;

-- Créer la nouvelle version avec la signature attendue par le code Python
CREATE OR REPLACE FUNCTION public.match_company_documents(
  p_embedding vector(768),  -- Dimension 768 pour correspondre à l'embedding du modèle
  p_company_id text,
  p_top_k int DEFAULT 5,
  p_min_score float DEFAULT 0.0,
  p_filter_metadata jsonb DEFAULT '{}'::jsonb
) 
RETURNS TABLE (
  id uuid,
  content text,
  metadata jsonb,
  company_id text,
  score float
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    v.id,
    v.content,
    v.metadata,
    v.company_id,
    1 - (v.embedding <=> p_embedding) AS score  -- Utilisation de la distance cosinus
  FROM document_vectors v
  WHERE v.company_id = p_company_id
    AND (1 - (v.embedding <=> p_embedding)) > p_min_score
  ORDER BY score DESC
  LIMIT p_top_k;
END;
$$;

-- Accorder les permissions nécessaires
GRANT EXECUTE ON FUNCTION public.match_company_documents(vector, text, int, float, jsonb) TO anon, authenticated;

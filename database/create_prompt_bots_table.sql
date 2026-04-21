-- ═══════════════════════════════════════════════════════════════════════════════
-- 🔧 MIGRATION: Création de la table prompt_bots
-- ═══════════════════════════════════════════════════════════════════════════════
-- Description: Centralisation des prompts maîtres pour Amanda et Jessica
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS prompt_bots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_type VARCHAR(50) UNIQUE NOT NULL, -- 'amanda' ou 'jessica'
    prompt_content TEXT NOT NULL,
    version VARCHAR(20) DEFAULT '1.0',
    is_active BOOLEAN DEFAULT true,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour recherche rapide
CREATE INDEX IF NOT EXISTS idx_prompt_bots_bot_type ON prompt_bots(bot_type);

-- Activation de l'historique (Audit Trail) si souhaité plus tard
COMMENT ON TABLE prompt_bots IS 'Table des prompts maîtres unifiés pour Amanda et Jessica';

-- 📝 NOTE : J'utilise une structure par ligne (bot_type) plutôt que colonnes 
-- pour permettre d'ajouter d'autres bots (ex: 'hotesse') sans modifier le schéma.

-- Insertion initiale (placeholders)
INSERT INTO prompt_bots (bot_type, prompt_content, version)
VALUES 
('amanda', 'Initial prompt for Amanda', '1.0'),
('jessica', 'Initial prompt for Jessica', '1.0')
ON CONFLICT (bot_type) DO NOTHING;

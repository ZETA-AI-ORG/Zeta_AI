-- Table de configuration dynamique pour entreprises
-- 100% générique, aucun hardcoding

CREATE TABLE IF NOT EXISTS company_configurations (
    id SERIAL PRIMARY KEY,
    company_id VARCHAR(64) NOT NULL UNIQUE,
    business_rules JSONB NOT NULL DEFAULT '{
        "allow_pricing": false,
        "allow_promotions": false,
        "require_uncertainty": true,
        "max_product_claims": 5
    }',
    product_catalog JSONB NOT NULL DEFAULT '{
        "categories": [],
        "sizes": [],
        "services": []
    }',
    validation_rules JSONB NOT NULL DEFAULT '{
        "dangerous_sizes": "[789]\\d*",
        "price_patterns": "\\d+[,.]?\\d*\\s*€",
        "promo_patterns": "\\d+%"
    }',
    response_templates JSONB NOT NULL DEFAULT '{
        "unknown_product": "Je ne trouve pas ce produit dans notre catalogue. Puis-je vous aider avec autre chose ?",
        "no_pricing": "Je n''ai pas accès aux prix en temps réel. Consultez notre site web ou contactez notre service client.",
        "no_promotion": "Je ne peux pas confirmer les promotions en cours. Vérifiez sur notre site web.",
        "uncertainty": "Je n''ai pas cette information précise. Puis-je vous orienter vers notre service client ?",
        "invalid_size": "Cette taille n''est pas disponible dans notre gamme. Voulez-vous voir nos tailles disponibles ?"
    }',
    security_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_company_configurations_company_id ON company_configurations(company_id);

-- Trigger pour updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_company_configurations_updated_at 
    BEFORE UPDATE ON company_configurations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Exemple d'insertion pour Rue du Gros (peut être supprimé après migration)
INSERT INTO company_configurations (
    company_id,
    business_rules,
    product_catalog,
    validation_rules,
    response_templates
) VALUES (
    'rue_du_gros_company_id_here',
    '{
        "allow_pricing": false,
        "allow_promotions": false,
        "require_uncertainty": true,
        "max_product_claims": 5
    }',
    '{
        "categories": ["couches", "lingettes", "soins bébé"],
        "sizes": ["1", "2", "3", "4", "5", "6"],
        "services": ["livraison", "conseil", "support"]
    }',
    '{
        "dangerous_sizes": "[789]\\d*",
        "price_patterns": "\\d+[,.]?\\d*\\s*€",
        "promo_patterns": "\\d+%"
    }',
    '{
        "unknown_product": "Je ne trouve pas ce produit dans notre catalogue de puériculture. Puis-je vous aider avec autre chose ?",
        "no_pricing": "Je n''ai pas accès aux prix en temps réel. Je vous recommande de consulter notre site web ou de contacter notre service client.",
        "no_promotion": "Je ne peux pas confirmer les promotions en cours. Pour connaître nos offres actuelles, consultez notre site web.",
        "uncertainty": "Je n''ai pas cette information précise dans ma base de connaissances. Puis-je vous orienter vers notre service client ?",
        "invalid_size": "Je ne trouve pas cette taille dans notre gamme. Nos couches sont disponibles en tailles 1 à 6. Puis-je vous aider à trouver la taille adaptée à votre bébé ?"
    }'
) ON CONFLICT (company_id) DO NOTHING;

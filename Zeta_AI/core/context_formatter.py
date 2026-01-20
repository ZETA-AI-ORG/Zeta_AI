from typing import Dict

class ContextFormatter:
    def format_for_hyde(self, context_data: Dict) -> str:
        context_parts = []
        if 'meilisearch' in context_data and context_data['meilisearch']:
            products = context_data['meilisearch']
            product_info = []
            for i, p in enumerate(products):
                # Log synthétique désactivé (trop verbeux)
                details = []
                for k, v in p.items():
                    # Inclure explicitement les champs textuels principaux même s'ils sont techniques
                    champs_textuels = ['content', 'description', 'texte', 'text']
                    if k.lower() in champs_textuels or (k.lower() not in ['id', '_id', 'document_type', 'section_title', '_rankingscore', '_block_weight', '_block_query', 'final_score']):
                        if v:
                            details.append(f"{k}: {v}")
                if details:
                    info = "\n".join(details)
                    product_info.append(info.strip())
            if product_info:
                context_parts.append(f"Produits pertinents: {' || '.join(product_info)}")
        if 'company' in context_data:
            company = context_data['company']
            details = []
            for k, v in company.items():
                if v:
                    details.append(f"{k}: {v}")
            if details:
                context_parts.append(f"Entreprise: {' | '.join(details)}")
        if 'policies' in context_data and context_data['policies']:
            context_parts.append("Politiques disponibles")
        if context_parts:
            return "Contexte pertinent: " + " | ".join(context_parts)
        else:
            return ""

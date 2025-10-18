from .concept_extractor import ConceptExtractor
from .context_sources import ContextSources
from utils import log3
from .context_formatter import ContextFormatter
import hashlib

class QuickContextLookup:
    def __init__(self, cache_manager, meilisearch_client, supabase_client):
        self.concept_extractor = ConceptExtractor()
        self.context_sources = ContextSources(meilisearch_client, supabase_client)
        self.context_formatter = ContextFormatter()
        self.cache_manager = cache_manager
        self.meili_client = meilisearch_client # Stocker le client Meili

    def generate_search_blocks(self, user_query: str, company_id: str) -> list:
        """
        Génère des blocs de recherche pondérés à partir des concepts extraits,
        en utilisant la logique combinatoire robuste (toutes les combinaisons utiles) pour une vraie multi-query Meilisearch.
        """
        from core.concept_extractor import generate_search_blocks as combo_blocks
        concepts = self.concept_extractor.extract(user_query, self.meili_client, company_id)
        if not concepts:
            return []
        # Utilise la version combinatoire robuste
        blocks_with_weights = combo_blocks(concepts)
        if not blocks_with_weights:
            # Fallback minimal si la version combinatoire échoue
            unique_terms = set()
            for v in concepts.values():
                unique_terms.update(v)
            for term in unique_terms:
                blocks_with_weights.append({'block': [term], 'weight': 1.0})
        # Log synthétique : nombre de blocs et exemple tronqué
        exemple = str(blocks_with_weights[0])[:80] + ('...' if len(str(blocks_with_weights[0])) > 80 else '') if blocks_with_weights else '[]'
        log3("[Quick Context][COMBO] Blocs générés", f"{len(blocks_with_weights)} blocs, ex: {exemple}")
        return blocks_with_weights

    import hashlib
    async def get_dynamic_context(self, user_query: str, company_id: str) -> str:
        """
        Orchestre l'extraction de contexte dynamique pertinent pour HyDE/RAG.
        """
        print(f"[Quick Context] Démarrage pour: '{user_query}' (company: {company_id})")
        
        # Générer les blocs de recherche pondérés en utilisant le contexte de l'index
        blocks_with_weights = self.generate_search_blocks(user_query, company_id)
        
        if not blocks_with_weights:
            print(f"[Quick Context] Concepts trop vagues ou absents, fallback context minimal.")
            minimal_context = f"Aucun contexte pertinent trouvé pour la question : '{user_query}'."
            cache_key = f"quick_context:{company_id}:{hash(user_query)}"
            self.cache_manager.set(cache_key, minimal_context, ttl_seconds=120)
            return minimal_context

        # Log synthétique : nombre de blocs et taille max
        max_size = max([len(b['block']) for b in blocks_with_weights]) if blocks_with_weights else 0
        log3("[Quick Context][COMBO] Nb blocs générés", f"{len(blocks_with_weights)} blocs, taille max {max_size}")

        # Générer une clé de cache composite basée sur les blocs
        blocks_for_cache = [b['block'] for b in blocks_with_weights]
        blocks_str = '|'.join([' '.join(block) for block in blocks_for_cache])
        cache_hash = hashlib.sha256(blocks_str.encode('utf-8')).hexdigest()
        cache_key = f"quick_context:{company_id}:{cache_hash}"

        cached = self.cache_manager.get(cache_key)
        if cached:
            print(f"[Quick Context] Cache HIT: '{cached[:50]}...'" )
            return cached
        
        print(f"[Quick Context] Cache MISS, requêtes Meilisearch multiples...")
        meili_results = await self.context_sources._search_meilisearch(blocks_with_weights, company_id)
        context_data = {'meilisearch': meili_results}
        print(f"[Quick Context] Documents Meilisearch récupérés: {len(meili_results)}")
        # LOG DEBUG: contenu brut des documents Meilisearch
        import pprint
        pprint.pprint(meili_results)
        
        formatted_context = self.context_formatter.format_for_hyde(context_data)
        # Log synthétique : contexte formaté tronqué
        ctx_short = formatted_context[:80] + ('...' if len(formatted_context) > 80 else '')
        log3("[Quick Context][DEBUG] Contexte formaté (truncated)", ctx_short)

        if not formatted_context or len(formatted_context.strip()) < 10 or formatted_context.strip().lower().startswith("aucun contexte pertinent"):
            log3("[Quick Context][BYPASS] Contexte considéré comme vide", formatted_context)
            minimal_context = f"Aucun contexte pertinent trouvé pour la question : '{user_query}'."
            self.cache_manager.set(cache_key, minimal_context, ttl_seconds=120)
            return minimal_context

        log3("[Quick Context][OK] Contexte formaté jugé pertinent", formatted_context)
        print(f"[Quick Context][DEBUG] Contexte formaté complet :\n{formatted_context}")
        self.cache_manager.set(cache_key, formatted_context, ttl_seconds=300)
        return formatted_context

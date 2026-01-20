import asyncio
import time
from typing import List, Dict, Any
import meilisearch
import os
from utils import log3

class MeilisearchOrchestrator:
    """
    Orchestre les requêtes MeiliSearch en parallèle, score les documents
    et sélectionne les plus pertinents selon la nouvelle logique.
    """
    def __init__(self, company_id: str):
        self.company_id = company_id
        self.meili_url = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
        self.meili_key = os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY", "")
        self.meili_client = meilisearch.Client(self.meili_url, self.meili_key)

        # Les 4 indexes principaux dynamiques
        self.main_indexes = [
            f"products_{self.company_id}",
            f"delivery_{self.company_id}",
            f"support_paiement_{self.company_id}",
            f"localisation_{self.company_id}",
        ]
        # L'index de fallback
        self.fallback_index = f"company_docs_{self.company_id}"
        self.min_documents_for_fallback = 4 # Seuil pour déclencher la recherche fallback

    async def _search_one_index(self, index_name: str, query_combo: List[str]) -> List[Dict[str, Any]]:
        """
        Effectue une recherche MeiliSearch sur un index donné avec une combinaison de mots.
        """
        query_str = " ".join(query_combo)
        try:
            search_start_time = time.time()
            response = await asyncio.to_thread(self.meili_client.index(index_name).search, query_str, {
                'limit': 5 # Récupérer un peu plus pour le scoring
            })
            
            # Ajouter le score basé sur la taille de la combinaison matchée ET l'index source
            for hit in response['hits']:
                hit['relevance_score'] = len(query_combo) # 3 > 2 > 1
                hit['matched_query_combo'] = query_combo
                hit['index_source'] = index_name # AJOUT DE L'INDEX SOURCE
            return response['hits']
        except Exception as e:
            # Log supprimé pour diagnostic Supabase
            return []

    async def orchestrate_search(self, query_combinations: List[List[str]], original_filtered_query: str) -> List[Dict[str, Any]]:
        """
        Orchestre la recherche MeiliSearch complète.
        """
        # Log supprimé pour diagnostic Supabase

        all_hits: Dict[str, List[Dict[str, Any]]] = {index: [] for index in self.main_indexes}
        tasks = []

        # Phase 1: Recherche principale en parallèle sur les 4 indexes
        for combo in query_combinations:
            for index_name in self.main_indexes:
                tasks.append(self._search_one_index(index_name, combo))
        
        # Exécuter toutes les tâches en parallèle
        all_results_lists = await asyncio.gather(*tasks)

        # Aplatir les résultats et les grouper par index
        for result_list in all_results_lists:
            if result_list:
                # L'index_name est dans les hits si l'attribut _index est configuré dans MeiliSearch
                # Sinon, il faut déduire l'index depuis la tâche ou le passer en paramètre
                # Pour simplifier ici, on va parcourir tous les hits et les classer par index
                # C'est une étape de post-traitement un peu plus coûteuse mais robuste
                for hit in result_list:
                    # Une heuristique simple pour retrouver l'index d'origine. Idéalement, Meili renverrait l'index.
                    # Si ce n'est pas le cas, on doit s'assurer que l'index est inclus dans le hit lors de l'ingestion
                    # Ou bien, chaque task doit retourner l'index avec ses hits.
                    # Pour l'instant, on va devoir boucler sur les main_indexes et vérifier le company_id
                    # OU MIEUX: Modifier _search_one_index pour qu'il retourne (index_name, hits)
                    # Reprise de la logique pour un regroupement correct des hits par index d'origine.
                    # Modification de _search_one_index pour inclure l'index_name dans la sortie.
                    pass # Sera géré après la modification de _search_one_index
        
        # Modification: Réexécuter la phase de recherche pour regrouper correctement
        # Log supprimé pour diagnostic Supabase
        grouped_tasks = []
        for combo in query_combinations:
            for index_name in self.main_indexes:
                grouped_tasks.append(self._search_one_index_with_name(index_name, combo))
        
        indexed_results = await asyncio.gather(*grouped_tasks)
        for index_name, hits in indexed_results:
            all_hits[index_name].extend(hits)

        # Traitement et sélection des 2 meilleurs documents par index
        selected_documents = []
        total_main_docs = 0

        for index_name, hits in all_hits.items():
            # Supprimer les doublons dans chaque index (basé sur l'ID du document)
            unique_hits: Dict[Any, Dict[str, Any]] = {}
            for hit in hits:
                doc_id = hit.get('id') # Supposons que chaque document a un champ 'id'
                if doc_id:
                    if doc_id not in unique_hits or hit['relevance_score'] > unique_hits[doc_id]['relevance_score']:
                        unique_hits[doc_id] = hit
            
            # Trier et sélectionner les 2 meilleurs documents par index
            sorted_unique_hits = sorted(unique_hits.values(), key=lambda x: x.get('relevance_score', 0), reverse=True)
            selected_documents.extend(sorted_unique_hits[:2])
            total_main_docs += len(sorted_unique_hits[:2])
            if sorted_unique_hits[:2]: # Log seulement s'il y a des documents sélectionnés
                # Log supprimé pour diagnostic Supabase

        # Phase 2: Fallback sur company_docs si nécessaire
        if total_main_docs < self.min_documents_for_fallback:
            # Log supprimé pour diagnostic Supabase
            fallback_hits = await self._search_one_index(self.fallback_index, original_filtered_query.split())
            
            # Ajouter les hits du fallback avec un score légèrement inférieur pour ne pas surclasser les principaux
            for hit in fallback_hits:
                # S'assurer qu'il n'y a pas de doublons avec les documents déjà sélectionnés
                if hit.get('id') not in [doc.get('id') for doc in selected_documents]:
                    hit['relevance_score'] = hit.get('relevance_score', 0) * 0.5 # Réduire le score
                    selected_documents.append(hit)
            if fallback_hits: # Log seulement s'il y a des documents de fallback
                # Log supprimé pour diagnostic Supabase

        # Trier tous les documents finalement sélectionnés par score global
        final_sorted_docs = sorted(selected_documents, key=lambda x: x.get('relevance_score', 0), reverse=True)
        # Log supprimé pour diagnostic Supabase
        return final_sorted_docs

    # Nouvelle méthode pour retourner aussi le nom de l'index
    async def _search_one_index_with_name(self, index_name: str, query_combo: List[str]) -> tuple[str, List[Dict[str, Any]]]:
        hits = await self._search_one_index(index_name, query_combo)
        return index_name, hits

if __name__ == "__main__":
    # Exemple d'utilisation du MeilisearchOrchestrator
    async def main_test():
        # Assurez-vous que MEILI_URL et MEILI_API_KEY sont définis dans les variables d'environnement
        # et que Meilisearch tourne avec des index pour 'test_company_id'
        # Pour un test réel, il faudrait mocker Meilisearch ou avoir une instance réelle.
        os.environ["MEILI_URL"] = "http://127.0.0.1:7700"
        os.environ["MEILI_API_KEY"] = "MASTER_KEY"

        orchestrator = MeilisearchOrchestrator(company_id="test_company_id")
        
        # Simuler des combinaisons de requêtes (Module 2)
        query_combinations_mock = [
            ["couches"], ["taille", "4"], ["livraison"], ["bingerville"], 
            ["couches", "taille"], ["taille", "4", "livraison"]
        ]
        original_query_mock = "couches taille 4 livraison bingerville"

        results = await orchestrator.orchestrate_search(query_combinations_mock, original_query_mock)
        log3("[MAIN_TEST] Résultats finaux de l'orchestrateur", f"{len(results)} documents, aperçu: {str(results)}")

    asyncio.run(main_test())

#!/usr/bin/env python3
"""
🚀 INGESTION COMPLÈTE AVEC HYDE D'ANALYSE
Script pour ingérer une base de données complète et créer le cache HyDE
"""

import asyncio
import json
import os
from datetime import datetime
from core.ingestion_hyde_analyzer import create_company_word_cache
from database.meili_client import MeiliClient

def log_ingestion(message, data=None):
    """Log formaté pour l'ingestion"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[INGESTION][{timestamp}] {message}")
    if data:
        print(f"  📊 {json.dumps(data, indent=2, ensure_ascii=False)}")

class CompleteIngestionManager:
    """
    Gestionnaire d'ingestion complète avec analyse HyDE
    """
    
    def __init__(self, company_id: str):
        self.company_id = company_id
        self.meili_client = MeiliClient()
        self.documents_ingested = []
        
    async def ingest_from_meili_index(self, index_name: str = None):
        """
        Récupère tous les documents depuis MeiliSearch pour analyse HyDE
        Scanne tous les index de l'entreprise
        """
        log_ingestion(f"🔍 RÉCUPÉRATION DOCUMENTS DEPUIS MEILISEARCH", {
            "company_id": self.company_id
        })
        
        try:
            # Récupérer tous les index de l'entreprise
            all_indexes = self.meili_client.client.get_indexes()
            company_indexes = [
                idx for idx in all_indexes['results'] 
                if self.company_id in idx.uid
            ]
            
            log_ingestion(f"📋 INDEX TROUVÉS POUR L'ENTREPRISE", {
                "total_indexes": len(company_indexes),
                "index_names": [idx.uid for idx in company_indexes]
            })
            
            all_documents = []
            
            # Récupérer les documents de chaque index
            for index_info in company_indexes:
                index_uid = index_info.uid
                
                try:
                    search_result = self.meili_client.client.index(index_uid).search("", {
                        "limit": 10000,  # Récupérer un maximum de documents
                        "attributesToRetrieve": ["*"]
                    })
                    
                    index_documents = search_result.get('hits', [])
                    
                    log_ingestion(f"📄 DOCUMENTS INDEX {index_uid}", {
                        "documents_count": len(index_documents)
                    })
                    
                    # Ajouter l'index source à chaque document
                    for doc in index_documents:
                        doc['source_index'] = index_uid
                    
                    all_documents.extend(index_documents)
                    
                except Exception as e:
                    log_ingestion(f"❌ ERREUR INDEX {index_uid}: {e}")
            
            documents = all_documents
            
            log_ingestion(f"✅ DOCUMENTS RÉCUPÉRÉS", {
                "total_documents": len(documents),
                "sample_titles": [doc.get('title', 'Sans titre')[:50] for doc in documents[:5]]
            })
            
            # Transformer en format pour HyDE
            formatted_docs = []
            for doc in documents:
                formatted_doc = {
                    "title": doc.get('title', 'Document sans titre'),
                    "category": doc.get('category', 'general'),
                    "searchable_text": doc.get('searchable_text', doc.get('content', ''))
                }
                
                # Vérifier que le document a du contenu
                if formatted_doc['searchable_text'] and len(formatted_doc['searchable_text']) > 10:
                    formatted_docs.append(formatted_doc)
            
            self.documents_ingested = formatted_docs
            
            log_ingestion(f"📋 DOCUMENTS FORMATÉS POUR HYDE", {
                "documents_valides": len(formatted_docs),
                "documents_rejetés": len(documents) - len(formatted_docs)
            })
            
            # Lancer l'analyse HyDE automatique
            log_ingestion("🔥 DÉBUT ANALYSE HYDE AUTOMATIQUE")
            
            try:
                # Importer et exécuter l'analyse HyDE
                from core.adaptive_hyde_scorer import analyze_documents_hyde
                
                # Analyser les documents récupérés
                hyde_results = await analyze_documents_hyde(
                    documents=documents,
                    company_id=self.company_id
                )
                
                log_ingestion("✅ ANALYSE HYDE AUTOMATIQUE TERMINÉE", {
                    "documents_analysés": len(documents),
                    "cache_généré": bool(hyde_results),
                    "mots_scores_créés": len(hyde_results.get('word_scores', {})) if hyde_results else 0
                })
                
                # Sauvegarder le cache HyDE si généré
                if hyde_results and hyde_results.get('word_scores'):
                    try:
                        import json
                        cache_file = f"hyde_cache_{self.company_id}.json"
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            json.dump(hyde_results, f, ensure_ascii=False, indent=2)
                        log_ingestion(f"💾 Cache HyDE sauvegardé: {cache_file}")
                    except Exception as save_error:
                        log_ingestion(f"⚠️ Erreur sauvegarde cache: {save_error}")
                
                return hyde_results
                
            except Exception as e:
                log_ingestion(f"❌ ERREUR ANALYSE HYDE AUTOMATIQUE: {e}")
                return None
            
        except Exception as e:
            log_ingestion(f"❌ ERREUR RÉCUPÉRATION MEILISEARCH: {e}")
            return []

    async def create_sample_documents(self):
        """
        Crée des documents d'exemple si MeiliSearch est vide
        """
        log_ingestion("📝 CRÉATION DOCUMENTS D'EXEMPLE")
        
        sample_docs = [
            {
                "title": "Samsung Galaxy S24 Ultra - Smartphone Premium",
                "category": "smartphones",
                "searchable_text": "Samsung Galaxy S24 Ultra smartphone haut de gamme 256GB 512GB noir blanc violet. Écran Dynamic AMOLED 6.8 pouces. Appareil photo 200MP zoom 100x. Processeur Snapdragon 8 Gen 3. Batterie 5000mAh charge rapide 45W. Prix 450000 FCFA 650000 FCFA selon stockage. Disponible magasin Cocody Plateau Yopougon. Livraison gratuite Abidjan. Paiement Wave Moov Orange MTN Mobile Money accepté. Garantie constructeur 2 ans. Contact WhatsApp pour commande rapide."
            },
            {
                "title": "iPhone 15 Pro Max - Apple Premium",
                "category": "smartphones",
                "searchable_text": "Apple iPhone 15 Pro Max 128GB 256GB 512GB 1TB. Couleurs bleu titane noir naturel blanc. Puce A17 Pro performance exceptionnelle. Appareil photo 48MP ProRAW ProRes. Écran Super Retina XDR 6.7 pouces ProMotion. Prix 580000 FCFA 750000 FCFA 950000 FCFA selon capacité. Stock limité Riviera Golf Marcory Treichville. Livraison express 24h Abidjan Grand Bassam. Financement possible 3 6 12 mois. Paiement sécurisé toutes méthodes."
            },
            {
                "title": "Casques Audio JBL - Son Premium",
                "category": "audio",
                "searchable_text": "Casques audio JBL gamme complète. JBL Tune 760NC bluetooth sans fil réduction bruit active. Couleurs rouge noir blanc bleu. Autonomie 35h charge rapide USB-C. Prix 35000 FCFA 45000 FCFA. JBL Live 660NC over-ear confort optimal. JBL Club One premium cuir véritable. Disponible magasin Adjamé Koumassi Abobo. Livraison moto taxi rapide. Test audio gratuit avant achat. Garantie 1 an pièces main d'œuvre."
            },
            {
                "title": "Yamaha MT-125 - Moto Sportive",
                "category": "motos",
                "searchable_text": "Moto Yamaha MT 125cc naked bike sportive urbaine. Moteur 125cc 4 temps injection électronique. Puissance 15 chevaux couple optimal. Design agressif phare LED feu arrière. Freins ABS sécurité maximale. Couleurs noir mat bleu racing rouge passion. Prix 1200000 FCFA 1350000 FCFA selon finition. Financement bancaire possible 12 24 36 mois. Assurance partenaire incluse. Livraison Abidjan banlieue. Formation conduite offerte. Entretien atelier agréé Yamaha."
            },
            {
                "title": "Conditions Livraison - Service Client",
                "category": "service",
                "searchable_text": "Livraison gratuite commandes supérieures 50000 FCFA. Zones couvertes Abidjan: Cocody Plateau Yopougon Marcory Treichville Adjamé Koumassi Abobo Riviera Golf Angré Port-Bouët. Banlieue: Bingerville Anyama Songon Grand Bassam Dabou. Délais livraison 24h ouvrées zone Abidjan 48h banlieue. Livraison express 2h disponible urgences. Frais livraison standard 2000 FCFA express 5000 FCFA. Paiement livraison COD cash on delivery accepté. Retour gratuit 7 jours satisfaction garantie."
            },
            {
                "title": "Moyens Paiement - Sécurité Transactions",
                "category": "service",
                "searchable_text": "Paiement sécurisé multiple options. Mobile Money: Wave Money Moov Money Orange Money MTN Mobile Money. Virement bancaire: UBA Ecobank SGCI BICICI Coris Bank. Paiement comptant magasin espèces. Carte bancaire Visa Mastercard terminal sécurisé. Financement crédit: Advans Microcred Orabank partenaires. Paiement échelonné 3 6 12 mois sans frais. Facture électronique envoyée email WhatsApp. Support paiement 24h/7j assistance technique."
            },
            {
                "title": "Support Technique - Assistance Client",
                "category": "support",
                "searchable_text": "Support technique professionnel équipe qualifiée. Assistance installation configuration produits électroniques. Réparation smartphones tablettes ordinateurs portables. Diagnostic gratuit devis transparent. Pièces détachées originales garanties. Intervention domicile entreprise sur rendez-vous. Horaires: lundi vendredi 8h-18h samedi 9h-15h. Contact: WhatsApp +225 07 XX XX XX XX email support@entreprise.ci. Formation utilisation produits incluse achat. Garantie étendue disponible tous produits."
            }
        ]
        
        self.documents_ingested = sample_docs
        
        log_ingestion("✅ DOCUMENTS D'EXEMPLE CRÉÉS", {
            "total_documents": len(sample_docs),
            "categories": list(set(doc['category'] for doc in sample_docs))
        })
        
        return sample_docs

    async def run_hyde_analysis(self):
        """
        Lance l'analyse HyDE complète sur les documents
        """
        if not self.documents_ingested:
            log_ingestion("⚠️ Aucun document à analyser - Création d'exemples")
            await self.create_sample_documents()
        
        log_ingestion(f"🧠 LANCEMENT ANALYSE HYDE", {
            "documents_count": len(self.documents_ingested),
            "company_id": self.company_id
        })
        
        # Lancer l'analyse HyDE d'ingestion
        cache_result = await create_company_word_cache(
            self.documents_ingested, 
            self.company_id
        )
        
        # Analyser les résultats
        word_scores = cache_result.get('word_scores', {})
        business_profile = cache_result.get('business_profile', {})
        
        # Statistiques détaillées
        high_score_words = {word: score for word, score in word_scores.items() if score >= 8}
        medium_score_words = {word: score for word, score in word_scores.items() if 5 <= score < 8}
        low_score_words = {word: score for word, score in word_scores.items() if score < 5}
        
        log_ingestion("🎯 RÉSULTATS ANALYSE HYDE", {
            "profil_business": business_profile,
            "total_mots_scorés": len(word_scores),
            "mots_critiques_8+": len(high_score_words),
            "mots_importants_5-7": len(medium_score_words),
            "mots_faibles_<5": len(low_score_words)
        })
        
        # Afficher le top des mots critiques
        sorted_words = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
        
        print(f"\n🔥 TOP 20 MOTS CRITIQUES:")
        for word, score in sorted_words[:20]:
            emoji = "🔥" if score >= 9 else "⭐" if score >= 7 else "✅"
            print(f"  {emoji} {word}: {score}")
        
        return cache_result

    async def test_cache_performance(self):
        """
        Teste les performances du cache généré
        """
        from core.cached_hyde_scorer import cached_hyde_filter
        
        log_ingestion("⚡ TEST PERFORMANCE CACHE")
        
        test_queries = [
            "samsung galaxy s24 prix disponible cocody",
            "iphone 15 pro max stock plateau",
            "casque jbl bluetooth rouge livraison",
            "yamaha mt 125 financement wave paiement",
            "support technique whatsapp contact",
            "livraison gratuite yopougon marcory"
        ]
        
        results = []
        
        for query in test_queries:
            start_time = asyncio.get_event_loop().time()
            
            filtered_query = await cached_hyde_filter(query, self.company_id, threshold=6)
            
            end_time = asyncio.get_event_loop().time()
            duration_ms = (end_time - start_time) * 1000
            
            results.append({
                "query": query,
                "filtered": filtered_query,
                "duration_ms": round(duration_ms, 2)
            })
            
            print(f"  📝 '{query}' → '{filtered_query}' ({duration_ms:.1f}ms)")
        
        avg_duration = sum(r['duration_ms'] for r in results) / len(results)
        
        log_ingestion("📊 PERFORMANCE CACHE", {
            "queries_testées": len(results),
            "durée_moyenne_ms": round(avg_duration, 2),
            "performance": "Excellent" if avg_duration < 100 else "Bon" if avg_duration < 500 else "À optimiser"
        })
        
        return results

async def main():
    """
    Fonction principale d'ingestion complète
    """
    print("🚀 INGESTION COMPLÈTE AVEC ANALYSE HYDE")
    print("=" * 60)
    
    company_id = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"  # RueduGrossiste
    
    manager = CompleteIngestionManager(company_id)
    
    try:
        # Étape 1: Récupération des documents
        print("\n📋 ÉTAPE 1: RÉCUPÉRATION DOCUMENTS")
        documents = await manager.ingest_from_meili_index()
        
        if not documents:
            print("⚠️ Aucun document MeiliSearch - Utilisation d'exemples")
            documents = await manager.create_sample_documents()
        
        # Étape 2: Analyse HyDE
        print("\n🧠 ÉTAPE 2: ANALYSE HYDE D'INGESTION")
        cache_result = await manager.run_hyde_analysis()
        
        # Étape 3: Test de performance
        print("\n⚡ ÉTAPE 3: TEST PERFORMANCE CACHE")
        performance_results = await manager.test_cache_performance()
        
        print(f"\n🎉 INGESTION TERMINÉE AVEC SUCCÈS!")
        print(f"📊 Cache créé: cache/word_scores_{company_id}.json")
        print(f"🚀 Prêt pour les tests endpoint!")
        
    except Exception as e:
        print(f"\n💥 ERREUR DURANT L'INGESTION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

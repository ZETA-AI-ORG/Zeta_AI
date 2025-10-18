"""
Mini-LLM Dispatcher - Chef d'orchestre intelligent pour l'ingestion de données
Rôle : Analyser, structurer, enrichir et dispatcher les données vers les bons index
"""

import logging
import json
import re
import os
import asyncio
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)

class ContentType(Enum):
    PRODUCT = "product"
    DELIVERY = "delivery"
    SUPPORT = "support"
    COMPANY = "company"
    PAYMENT = "payment"
    POLICY = "policy"
    FAQ = "faq"
    GENERIC = "generic"

class ChunkPriority(Enum):
    HIGH = "high"      # Produits, prix, stock
    MEDIUM = "medium"  # FAQ, livraison
    LOW = "low"        # Info générale

@dataclass
class EnrichedChunk:
    """Chunk enrichi par le Mini-LLM"""
    content: str
    content_type: ContentType
    priority: ChunkPriority
    
    # Expansion sémantique HYDE
    hypothetical_queries: List[str]
    hypothetical_answers: List[str]
    keywords: List[str]
    synonyms: List[str]
    
    # Entités extraites
    entities: Dict[str, Any]  # produits, prix, tailles, couleurs, etc.
    
    # Métadonnées de dispatching
    target_indexes: List[str]  # ["supabase", "meilisearch"]
    chunk_id: str
    metadata: Dict[str, Any]

class MiniLLMDispatcher:
    """
    Mini-LLM Dispatcher - Intelligence centrale d'ingestion
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        # Limite de concurrence HYDE (par défaut 2)
        try:
            conc = int(os.getenv("HYDE_CONCURRENCY", "2"))
        except Exception:
            conc = 2
        self._hyde_sem = asyncio.Semaphore(max(1, conc))
        # Petit cache pour éviter de ré-appeler HYDE sur le même contenu
        self._hyde_cache: Dict[str, Dict[str, List[str]]] = {}
        # Limites douces configurables
        try:
            self._hyde_max_retries = max(1, int(os.getenv("HYDE_MAX_RETRIES", "3")))
        except Exception:
            self._hyde_max_retries = 3
        # Longueur de log sécurité
        self._log_snippet_len = 500
        
    async def process_document(self, 
                             raw_content: str, 
                             company_id: str,
                             document_type: str = "unknown") -> List[EnrichedChunk]:
        """
        Point d'entrée principal : traite un document brut
        """
        self.logger.info(f"[DISPATCHER] Traitement document {document_type} pour company_id={company_id}")
        
        # 1. Analyse et structuration intelligente
        structured_sections = await self._analyze_and_structure(raw_content, document_type)
        
        # 2. Enrichissement sémantique de chaque section
        enriched_chunks = []
        for section in structured_sections:
            chunk = await self._enrich_section(section, company_id)
            if chunk:
                enriched_chunks.append(chunk)
        
        # 3. Optimisation finale (fusion/split si nécessaire)
        optimized_chunks = await self._optimize_chunks(enriched_chunks)
        
        self.logger.info(f"[DISPATCHER] {len(optimized_chunks)} chunks enrichis générés")
        return optimized_chunks
    
    async def _analyze_and_structure(self, content: str, doc_type: str) -> List[Dict[str, Any]]:
        """
        Étape 1: Analyse intelligente et structuration du document
        """
        prompt = f"""
Tu es un analyste documentaire expert. Analyse ce document business et structure-le intelligemment pour optimiser la recherche et les réponses d'un chatbot commercial.

DOCUMENT À ANALYSER:
{content}

TYPE DE DOCUMENT: {doc_type}

MISSION:
1. IDENTIFIER les informations clés du document
2. REGROUPER les données complémentaires (ex: produit + prix + stock + variantes)
3. CRÉER des sections logiques et cohérentes
4. STRUCTURER pour maximiser l'utilité business

RÈGLES UNIVERSELLES:
- Regroupe les informations liées ensemble (produit avec ses attributs, livraison avec tarifs et délais)
- Crée des sections thématiques complètes
- Évite la fragmentation d'informations importantes
- Adapte-toi au secteur d'activité détecté
- Priorise selon l'impact business (produits/services = HIGH, info générale = MEDIUM)

EXEMPLES GÉNÉRIQUES:
- Produit: "Article X - Prix: Y - Couleurs: A,B,C - Stock: Z" → 1 section complète
- Service: "Service Y - Tarif: X - Conditions: Z" → 1 section unifiée
- Livraison: "Zone A: Prix X, Délai Y" → regrouper par zones logiques

Analyse naturellement et explique ta structuration.
"""
        
        try:
            if self.llm_client:
                response = self.llm_client.invoke(prompt)
                # Parse la réponse naturelle du LLM
                return self._parse_natural_response(response.content, content)
            else:
                # Fallback : structuration basique par regex
                return self._fallback_structure(content)
        except Exception as e:
            self.logger.error(f"[DISPATCHER] Erreur structuration: {e}")
            return self._fallback_structure(content)
    
    async def _enrich_section(self, section: Dict[str, Any], company_id: str) -> Optional[EnrichedChunk]:
        """
        Étape 2: Enrichissement sémantique d'une section
        """
        content = section.get("content", "")
        if not content.strip():
            return None
            
        content_type = ContentType(section.get("type", "generic"))
        priority = ChunkPriority(section.get("priority", "medium"))
        
        # Génération HYDE enrichie
        hyde_data = await self._generate_hyde_expansion(content, content_type)
        
        # Génération d'ID unique
        chunk_id = self._generate_chunk_id(company_id, content, content_type.value)
        
        # Détermination des index cibles
        target_indexes = self._determine_target_indexes(content_type, priority)
        
        return EnrichedChunk(
            content=content,
            content_type=content_type,
            priority=priority,
            hypothetical_queries=hyde_data["queries"],
            hypothetical_answers=hyde_data["answers"],
            keywords=hyde_data["keywords"],
            synonyms=hyde_data["synonyms"],
            entities=section.get("entities", {}),
            target_indexes=target_indexes,
            chunk_id=chunk_id,
            metadata={
                "company_id": company_id,
                "title": section.get("title", ""),
                "created_at": datetime.utcnow().isoformat(),
                "processed_by": "mini_llm_dispatcher"
            }
        )
    
    async def _generate_hyde_expansion(self, content: str, content_type: ContentType) -> Dict[str, List[str]]:
        """
        Génération d'expansion sémantique HYDE enrichie
        """
        # Cache key sur contenu + type
        cache_key = hashlib.sha1(f"{content_type.value}|{content}".encode("utf-8")).hexdigest()
        if cache_key in self._hyde_cache:
            return self._hyde_cache[cache_key]

        prompt = f"""
Tu es un expert en expansion sémantique pour moteurs de recherche.

CONTENU: {content[:900]}
TYPE: {content_type.value}

OBJECTIF:
Fournir une expansion HYDE concise et utile. Réponses courtes, sans texte superflu.

EXIGE UNIQUEMENT DU JSON VALIDE, RIEN D'AUTRE.
FORMAT EXACT:
{{
  "queries": ["q1?", "q2?", "q3?"],
  "answers": ["réponse courte 1", "réponse courte 2", "réponse courte 3"],
  "keywords": ["mot1", "mot2", "mot3", "mot4", "mot5", "mot6"],
  "synonyms": ["variante1", "variante2", "variante3", "variante4"]
}}

CONTRAINTES:
- 4 à 6 questions maximum
- 3 à 4 réponses courtes
- 6 à 10 mots-clés
- 4 à 6 synonymes/variantes
"""

        try:
            if self.llm_client:
                async with self._hyde_sem:
                    response_text = await self._invoke_with_backoff(prompt)
                if response_text is None or not str(response_text).strip():
                    raise ValueError("Réponse LLM vide")

                # Log tronqué pour debug
                snippet = str(response_text)[: self._log_snippet_len].replace("\n", " ")
                self.logger.debug(f"[DISPATCHER] HYDE raw (tronqué): {snippet}")

                data = self._parse_json_tolerant(str(response_text))
            else:
                data = {
                    "queries": [f"Qu'est-ce que {content[:50]}?"],
                    "answers": [content[:100]],
                    "keywords": self._extract_keywords_fallback(content),
                    "synonyms": []
                }

            # Normalisation clés attendues
            for k in ["queries", "answers", "keywords", "synonyms"]:
                if k not in data or not isinstance(data[k], list):
                    data[k] = []

            # Cache
            self._hyde_cache[cache_key] = data
            return data
        except Exception as e:
            self.logger.error(f"[DISPATCHER] Erreur HYDE: {e}")
            return {
                "queries": [f"Information sur {content[:30]}..."],
                "answers": [content[:150] + "..."],
                "keywords": self._extract_keywords_fallback(content),
                "synonyms": []
            }

    def _parse_json_tolerant(self, raw: str) -> Dict[str, Any]:
        """Tente de parser du JSON même si du texte entoure la réponse.
        Stratégie: direct -> extraction entre { ... } -> nettoyage simple -> fallback structure vide.
        """
        # 1) direct
        try:
            return json.loads(raw)
        except Exception:
            pass

        # 2) extraire le plus grand bloc JSON { ... }
        if "{" in raw and "}" in raw:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end > start:
                cand = raw[start:end + 1]
                # Tentative brute
                try:
                    return json.loads(cand)
                except Exception:
                    # 3) petits nettoyages: retirer balises markdown, backticks
                    cleaned = cand.replace("```json", "").replace("```", "").strip()
                    # Supprimer BOM ou caractères non imprimables courants
                    cleaned = cleaned.replace("\ufeff", "")
                    try:
                        return json.loads(cleaned)
                    except Exception:
                        pass

        # 4) fallback structuré
        return {"queries": [], "answers": [], "keywords": [], "synonyms": []}

    async def _invoke_with_backoff(self, prompt: str) -> Optional[str]:
        """Appelle self.llm_client.invoke(prompt) avec retries exponentiels et jitter.
        Ne fait aucune hypothèse sur l'API du client (réponse .content ou str).
        """
        attempts = self._hyde_max_retries
        base_delay = 1.0
        for i in range(attempts):
            try:
                resp = self.llm_client.invoke(prompt)
                # Supporte une réponse objet (avec .content) ou brute
                if hasattr(resp, "content"):
                    return str(resp.content)
                return str(resp)
            except Exception as e:
                # Backoff exponentiel + jitter
                delay = base_delay * (2 ** i) + random.uniform(0, 0.5)
                self.logger.warning(f"[DISPATCHER] LLM invoke échec (tentative {i+1}/{attempts}): {e}. Retry dans {delay:.1f}s")
                await asyncio.sleep(delay)
        # Dernier essai sans capture pour surfacer l'erreur? On retourne None pour laisser le caller fallback
        return None
    
    async def _optimize_chunks(self, chunks: List[EnrichedChunk]) -> List[EnrichedChunk]:
        """
        Étape 3: Optimisation finale des chunks - CONSERVE LES DOCUMENTS INTACTS
        Pas de split ni de fusion pour respecter l'intégrité des documents MeiliSearch
        """
        # MODIFICATION: Retourner les chunks tels quels sans subdivision
        # pour conserver exactement la même structure que MeiliSearch
        return chunks
    
    def _determine_target_indexes(self, content_type: ContentType, priority: ChunkPriority) -> List[str]:
        """
        Détermine vers quels index dispatcher le chunk
        """
        targets = []
        
        # Tous les chunks vont dans PGVector (recherche sémantique)
        targets.append("pgvector")
        
        # Chunks haute priorité vont aussi dans Meilisearch (recherche rapide)
        if priority == ChunkPriority.HIGH:
            targets.append("meilisearch")
        
        # Produits et FAQ vont toujours dans Meilisearch
        if content_type in [ContentType.PRODUCT, ContentType.FAQ]:
            if "meilisearch" not in targets:
                targets.append("meilisearch")
        
        return targets
    
    def _generate_chunk_id(self, company_id: str, content: str, content_type: str) -> str:
        """Génère un ID unique pour le chunk"""
        import hashlib
        import uuid
        
        base = f"{company_id}|{content_type}|{content[:100]}"
        digest = hashlib.sha1(base.encode("utf-8")).hexdigest()
        return str(uuid.uuid5(uuid.UUID("11111111-2222-3333-4444-555555555555"), digest))
    
    def _parse_natural_response(self, llm_response: str, original_content: str) -> List[Dict[str, Any]]:
        """
        Parse la réponse naturelle du LLM et extrait les sections
        """
        try:
            # Le LLM a analysé le contenu, on crée des sections basées sur sa compréhension
            # Pour l'instant, on utilise le contenu original comme une section enrichie
            # avec l'analyse du LLM comme contexte
            
            # Détection intelligente du type de contenu (universelle)
            content_lower = original_content.lower()
            
            # Détection produit/service (mots-clés universels)
            if any(word in content_lower for word in ['prix', 'price', 'cost', 'tarif', 'produit', 'product', 'article', 'item', 'stock', 'inventory', 'couleur', 'color', 'taille', 'size', 'variant', 'sku', 'ref']):
                content_type = "product"
                priority = "high"
            # Détection livraison/shipping
            elif any(word in content_lower for word in ['livraison', 'delivery', 'shipping', 'transport', 'expédition', 'délai', 'delay', 'zone', 'frais', 'fees']):
                content_type = "delivery"
                priority = "high"
            # Détection support/contact
            elif any(word in content_lower for word in ['support', 'contact', 'aide', 'help', 'assistance', 'service', 'phone', 'email', 'whatsapp', 'telegram']):
                content_type = "support"
                priority = "medium"
            # Détection paiement
            elif any(word in content_lower for word in ['paiement', 'payment', 'pay', 'carte', 'card', 'wave', 'paypal', 'stripe', 'bank', 'virement']):
                content_type = "payment"
                priority = "high"
            # Détection entreprise/company
            elif any(word in content_lower for word in ['entreprise', 'company', 'société', 'business', 'about', 'mission', 'vision', 'secteur', 'sector']):
                content_type = "company"
                priority = "medium"
            # Détection politique/règlement
            elif any(word in content_lower for word in ['politique', 'policy', 'règlement', 'terms', 'conditions', 'retour', 'return', 'refund']):
                content_type = "policy"
                priority = "medium"
            else:
                content_type = "generic"
                priority = "medium"
            
            return [{
                "content": original_content,
                "type": content_type,
                "priority": priority,
                "title": f"Section {content_type}",
                "llm_analysis": llm_response  # Garde l'analyse du LLM comme contexte
            }]
            
        except Exception as e:
            self.logger.warning(f"[DISPATCHER] Erreur parsing réponse naturelle: {e}")
            return self._fallback_structure(original_content)
    
    def _fallback_structure(self, content: str) -> List[Dict[str, Any]]:
        """Structuration basique - CONSERVE LE DOCUMENT ENTIER"""
        # MODIFICATION: Retourner le document complet sans découpage
        # pour respecter l'intégrité des documents comme dans MeiliSearch
        return [{
            "content": content.strip(),
            "type": "generic", 
            "priority": "medium",
            "title": "Document complet"
        }]
    
    def _extract_keywords_fallback(self, content: str) -> List[str]:
        """Extraction basique de mots-clés sans LLM"""
        # Mots de plus de 3 caractères, fréquents
        words = re.findall(r'\b[a-zA-ZÀ-ÿ]{4,}\b', content.lower())
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Retourner les 10 mots les plus fréquents
        return sorted(word_freq.keys(), key=lambda x: word_freq[x], reverse=True)[:10]
    
    async def _split_large_chunk(self, chunk: EnrichedChunk) -> List[EnrichedChunk]:
        """Split un chunk trop volumineux"""
        # Implémentation simple : split par phrases
        sentences = re.split(r'[.!?]+', chunk.content)
        sub_chunks = []
        
        current_content = ""
        for sentence in sentences:
            if len(current_content + sentence) > 500:  # Limite par sous-chunk
                if current_content:
                    # Créer un sous-chunk
                    sub_chunk = EnrichedChunk(
                        content=current_content.strip(),
                        content_type=chunk.content_type,
                        priority=chunk.priority,
                        hypothetical_queries=chunk.hypothetical_queries[:3],  # Réduire
                        hypothetical_answers=chunk.hypothetical_answers[:2],
                        keywords=chunk.keywords[:8],
                        synonyms=chunk.synonyms[:6],
                        entities=chunk.entities,
                        target_indexes=chunk.target_indexes,
                        chunk_id=f"{chunk.chunk_id}_sub_{len(sub_chunks)}",
                        metadata={**chunk.metadata, "is_subchunk": True}
                    )
                    sub_chunks.append(sub_chunk)
                current_content = sentence
            else:
                current_content += " " + sentence
        
        # Dernier sous-chunk
        if current_content.strip():
            sub_chunk = EnrichedChunk(
                content=current_content.strip(),
                content_type=chunk.content_type,
                priority=chunk.priority,
                hypothetical_queries=chunk.hypothetical_queries[:3],
                hypothetical_answers=chunk.hypothetical_answers[:2],
                keywords=chunk.keywords[:8],
                synonyms=chunk.synonyms[:6],
                entities=chunk.entities,
                target_indexes=chunk.target_indexes,
                chunk_id=f"{chunk.chunk_id}_sub_{len(sub_chunks)}",
                metadata={**chunk.metadata, "is_subchunk": True}
            )
            sub_chunks.append(sub_chunk)
        
        return sub_chunks
    
    async def _try_merge_chunk(self, chunk: EnrichedChunk, existing_chunks: List[EnrichedChunk]) -> bool:
        """Tente de fusionner un petit chunk avec un existant"""
        # Logique simple : chercher un chunk du même type
        for existing in existing_chunks:
            if (existing.content_type == chunk.content_type and 
                len(existing.content) < 800):  # Pas trop gros déjà
                
                # Fusionner
                existing.content += "\n" + chunk.content
                existing.keywords.extend(chunk.keywords)
                existing.synonyms.extend(chunk.synonyms)
                existing.hypothetical_queries.extend(chunk.hypothetical_queries)
                
                # Dédupliquer
                existing.keywords = list(set(existing.keywords))
                existing.synonyms = list(set(existing.synonyms))
                existing.hypothetical_queries = list(set(existing.hypothetical_queries))
                
                return True
        
        return False

# Factory function pour créer le dispatcher
def create_mini_llm_dispatcher(llm_client=None) -> MiniLLMDispatcher:
    """Crée une instance du Mini-LLM Dispatcher"""
    return MiniLLMDispatcher(llm_client=llm_client)

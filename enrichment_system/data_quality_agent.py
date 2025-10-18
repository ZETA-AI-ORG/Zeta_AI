#!/usr/bin/env python3
"""
🤖 DATA QUALITY AGENT - Enrichissement et correction automatique
Système autonome pour tester l'enrichissement LLM
"""
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

class DataQualityAgent:
    """Agent LLM pour enrichir, corriger et clarifier les données"""
    
    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: Client LLM (si None, utilise celui par défaut)
        """
        if llm_client is None:
            try:
                from llm_client import get_llm_client
                self.llm = get_llm_client()
            except:
                print("⚠️ LLM client non disponible, mode simulation activé")
                self.llm = None
        else:
            self.llm = llm_client
    
    async def enrich_document(self, raw_document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrichit un document brut avec correction orthographe + clarification ambiguïtés
        
        Args:
            raw_document: Document brut avec potentiellement des erreurs
        
        Returns:
            Document enrichi avec métadonnées d'enrichissement
        """
        print(f"\n{'='*80}")
        print(f"🤖 ENRICHISSEMENT: {raw_document.get('product_name', 'Document')}")
        print(f"{'='*80}\n")
        
        # 1. Analyser le document
        analysis = self._analyze_document(raw_document)
        print(f"📊 Analyse:")
        print(f"   - Fautes détectées: {len(analysis['spelling_errors'])}")
        print(f"   - Ambiguïtés: {len(analysis['ambiguities'])}")
        print(f"   - Score qualité: {analysis['quality_score']:.2f}/1.00")
        
        # 2. Appeler LLM pour enrichissement
        enrichment = await self._call_llm_for_enrichment(raw_document, analysis)
        
        # 3. Construire document enrichi
        enriched_doc = self._build_enriched_document(raw_document, enrichment, analysis)
        
        print(f"\n✅ Enrichissement terminé")
        print(f"   - Corrections: {len(enriched_doc['_metadata']['corrections'])}")
        print(f"   - Clarifications: {len(enriched_doc['_metadata']['clarifications'])}")
        print(f"   - Confiance: {enriched_doc['_metadata']['confidence']:.2f}")
        
        return enriched_doc
    
    def _analyze_document(self, doc: Dict) -> Dict:
        """Analyse préliminaire du document"""
        
        text = doc.get('description', '') + ' ' + doc.get('notes', '')
        
        # Détection fautes orthographe (patterns simples)
        spelling_errors = []
        common_errors = {
            'disponnible': 'disponible',
            'taille': 'taille',  # OK
            'couleur': 'couleur',  # OK
            'livrasion': 'livraison',
            'paiemant': 'paiement',
            'garanti': 'garantie'
        }
        
        for wrong, correct in common_errors.items():
            if wrong in text.lower():
                spelling_errors.append({'wrong': wrong, 'correct': correct})
        
        # Détection ambiguïtés
        ambiguities = []
        
        # Ambiguïté 1: "toutes tailles" sans précision
        if re.search(r'toute.{0,5}taille', text, re.IGNORECASE):
            if not re.search(r'taille\s+\d+', text):
                ambiguities.append({
                    'type': 'missing_size_details',
                    'description': '"toutes tailles" mentionné sans liste explicite'
                })
        
        # Ambiguïté 2: Prix sans clarification variant
        if 'prix' in text.lower() or 'fcfa' in text.lower():
            if not any(word in text.lower() for word in ['unique', 'identique', 'même']):
                ambiguities.append({
                    'type': 'price_ambiguity',
                    'description': 'Prix mentionné sans préciser si unique ou variable'
                })
        
        # Ambiguïté 3: Quantité minimale vague
        if re.search(r'lot|minimum|mini', text, re.IGNORECASE):
            if not re.search(r'\d+\s*(pièces|unités)', text):
                ambiguities.append({
                    'type': 'quantity_ambiguity',
                    'description': 'Quantité minimale non précisée'
                })
        
        # Score qualité (0-1)
        quality_score = 1.0
        quality_score -= len(spelling_errors) * 0.1  # -0.1 par faute
        quality_score -= len(ambiguities) * 0.15  # -0.15 par ambiguïté
        quality_score = max(0, quality_score)
        
        return {
            'spelling_errors': spelling_errors,
            'ambiguities': ambiguities,
            'quality_score': quality_score,
            'needs_enrichment': quality_score < 0.8
        }
    
    async def _call_llm_for_enrichment(self, doc: Dict, analysis: Dict) -> Dict:
        """Appelle le LLM pour enrichir le document"""
        
        if self.llm is None:
            return self._mock_llm_response(doc, analysis)
        
        # Construire le prompt
        prompt = self._build_enrichment_prompt(doc, analysis)
        
        try:
            response = await self.llm.complete(
                prompt=prompt,
                temperature=0.2,  # Bas pour cohérence
                max_tokens=1000
            )
            
            # Parser JSON response
            enrichment = json.loads(response)
            return enrichment
            
        except Exception as e:
            print(f"⚠️ Erreur LLM: {e}")
            return self._mock_llm_response(doc, analysis)
    
    def _build_enrichment_prompt(self, doc: Dict, analysis: Dict) -> str:
        """Construit le prompt d'enrichissement"""
        
        return f"""Tu es un expert en correction et enrichissement de données e-commerce.

DOCUMENT ORIGINAL:
{json.dumps(doc, indent=2, ensure_ascii=False)}

PROBLÈMES DÉTECTÉS:
- Fautes d'orthographe: {len(analysis['spelling_errors'])}
- Ambiguïtés: {len(analysis['ambiguities'])}
- Score qualité: {analysis['quality_score']:.2f}/1.00

TÂCHES:
1. **CORRIGER** toutes les fautes d'orthographe
2. **CLARIFIER** toutes les ambiguïtés détectées:
   {chr(10).join('   - ' + amb['description'] for amb in analysis['ambiguities'])}
3. **ENRICHIR** avec informations manquantes (SANS INVENTER):
   - Si "toutes tailles" → Lister tailles STANDARD du secteur + mention "à confirmer"
   - Si prix vague → Préciser "Prix UNIQUE" ou "Variable selon X"
   - Si quantité floue → Demander précision + suggérer standard

RÈGLES STRICTES:
- NE JAMAIS inventer prix, tailles ou données absentes
- Si info manquante → Marquer "À CONFIRMER PAR CLIENT"
- Rester FACTUEL et basé sur le document original

FORMAT JSON ATTENDU:
{{
  "corrected_text": "...",
  "enriched_description": "...",
  "searchable_text": "...",
  "corrections_made": [
    {{"type": "spelling", "before": "...", "after": "..."}}
  ],
  "clarifications_added": [
    {{"type": "ambiguity", "field": "...", "clarification": "..."}}
  ],
  "needs_client_confirmation": [
    {{"field": "...", "question": "..."}}
  ],
  "confidence": 0.X
}}

GÉNÈRE LE JSON:"""
    
    def _mock_llm_response(self, doc: Dict, analysis: Dict) -> Dict:
        """Simulation LLM si non disponible"""
        
        description = doc.get('description', '')
        
        # Corrections orthographe
        corrections = []
        for error in analysis['spelling_errors']:
            description = description.replace(error['wrong'], error['correct'])
            corrections.append({
                'type': 'spelling',
                'before': error['wrong'],
                'after': error['correct']
            })
        
        # Clarifications
        clarifications = []
        enriched_desc = description
        
        # Clarifier prix si ambiguïté
        if any(amb['type'] == 'price_ambiguity' for amb in analysis['ambiguities']):
            enriched_desc += "\n⚠️ Prix UNIQUE pour toutes les variantes (à confirmer par le client)."
            clarifications.append({
                'type': 'price',
                'field': 'pricing',
                'clarification': 'Ajouté mention prix unique'
            })
        
        return {
            'corrected_text': description,
            'enriched_description': enriched_desc,
            'searchable_text': enriched_desc.replace('\n', ' '),
            'corrections_made': corrections,
            'clarifications_added': clarifications,
            'needs_client_confirmation': [
                {'field': 'tailles', 'question': 'Quelles tailles exactement ?'}
            ],
            'confidence': 0.75
        }
    
    def _build_enriched_document(self, original: Dict, enrichment: Dict, analysis: Dict) -> Dict:
        """Construit le document final enrichi"""
        
        enriched = original.copy()
        
        # Appliquer corrections
        if 'corrected_text' in enrichment:
            enriched['description'] = enrichment['enriched_description']
        
        if 'searchable_text' in enrichment:
            enriched['searchable_text'] = enrichment['searchable_text']
        
        # Métadonnées d'enrichissement
        enriched['_metadata'] = {
            'enriched_at': datetime.now().isoformat(),
            'original_quality': analysis['quality_score'],
            'corrections': enrichment.get('corrections_made', []),
            'clarifications': enrichment.get('clarifications_added', []),
            'needs_confirmation': enrichment.get('needs_client_confirmation', []),
            'confidence': enrichment.get('confidence', 0.5),
            'status': 'pending_validation'
        }
        
        return enriched

# Singleton pour utilisation facile
_agent_instance = None

def get_data_quality_agent():
    """Récupère l'instance singleton de l'agent"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = DataQualityAgent()
    return _agent_instance

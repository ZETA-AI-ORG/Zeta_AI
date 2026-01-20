"""
Agent Hybride de Reformatage Décisionnel
Optimise les réponses chatbot avec règles rapides + LLM fallback
"""

import re
from core.product_attribute_extractor import extract_product_attributes, get_dynamic_product_attributes

import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import asyncio

@dataclass
class ReformatMeta:
    """Métadonnées de la décision de reformatage"""
    score: float
    decision: str  # "fast_rules", "llm_fallback", "no_change"
    rules_applied: List[str]
    processing_time_ms: float
    cache_hit: bool
    original_length: int
    final_length: int

class DecisionReformatAgent:
    def __init__(self, redis_cache=None, llm_client=None, meili_client=None, index_name=None):
        self.cache = redis_cache
        self.llm_client = llm_client
        self.meili_client = meili_client
        self.index_name = index_name
        self.score_threshold = 0.6  # Seuil pour décider LLM vs règles rapides
        self.transaction_patterns = [
            # ... (inchangé)
        ]
        self.critical_keywords = [
            # ... (inchangé)
        ]
        self.repetition_patterns = [
            # ... (inchangé)
        ]
        self.transaction_patterns = [
    r"votre commande.*confirmée",
    r"commande.*confirmée",
    r"paiement.*validé",
    r"récapitulatif.*commande",
    r"confirmation.*commande",
    r"total.*commande",
    r"détails.*commande",
    r"numéro.*commande.*[A-Z0-9]+",
    r"référence.*[A-Z0-9]{6,}",
    r"montant.*[0-9]+[,.]?[0-9]*.*(cfa|fcfa|xof)",
    r"prix.*[0-9]+[,.]?[0-9]*.*(cfa|fcfa|xof)",
    r"total.*[0-9]+[,.]?[0-9]*.*(cfa|fcfa|xof)",
    r"facture.*n°.*[0-9]+",
    r"lot.*n°.*[0-9]+",
    r"poids.*[0-9]+\\s?(kg|g|gramme|tonne)",
    r"taille.*(xs|s|m|l|xl|xxl|[0-9]+(cm|mm|cl|ml|l|m))",
    r"couleur.*(blanc|noir|rouge|bleu|vert|jaune|rose|orange|gris|marron|violet|beige|doré|argenté|turquoise|kaki|bordeaux|ivoire|multicolore|clair|foncé|pastel|fluo|cuivré|camel|ambre|corail|indigo|olive|sable|taupe|saumon|aubergine|anis|lilas|azur|marine|ciel|prune|menthe|chocolat|caramel|café)",
    r"senteur.*[a-zA-Z]+",
    r"parfum.*[a-zA-Z]+",
    r"volume.*[0-9]+\\s?(ml|cl|l)",
    r"arôme.*[a-zA-Z]+",
    r"saveur.*[a-zA-Z]+",
    r"marque.*[a-zA-Z0-9]+",
    r"modèle.*[a-zA-Z0-9]+",
    r"SKU.*[a-zA-Z0-9]+",
    r"date.*péremption.*[0-9]{2}/[0-9]{2}/[0-9]{4}",
    r"origine.*[a-zA-Z]+",
    r"composition.*[a-zA-Z, ]+",
    r"confirmation.*(commande|paiement|livraison|transaction)",
    r"livraison.*(zone|date|délai|adresse|quartier|ville|prix|frais)",
    r"paiement.*(méthode|moyen|mobile money|orange money|mtn|moov|wave|espèces|carte)",
]
        self.critical_keywords = [
            "prix", "total", "montant", "confirmation", "commande",
            "paiement", "livraison", "adresse", "horaire"
        ]
        
        self.repetition_patterns = [
            r"comme.*mentionné",
            r"vous avez dit",
            r"d'après.*conversation"
        ]

    def _generate_cache_key(self, response: str, chat_history: str, question: str) -> str:
        """Génère une clé de cache unique pour cette combinaison"""
        content = f"{response[:100]}|{question}|{len(chat_history)}"
        return f"reformat_decision::" + hashlib.md5(content.encode()).hexdigest()

    def _extract_user_confirmations(self, chat_history: str) -> Dict[str, str]:
        """Extrait les éléments confirmés par l'utilisateur dans l'historique, dynamiquement"""
        confirmations = {}
        # Extraction patterns statiques classiques
        patterns = {
            'address': r"adresse.*?([0-9].*?)(?:\n|$)",
            'payment': r"paiement.*?(carte|espèces|virement|mobile money|orange money|mtn|moov|wave)",
            'quantity': r"(?:quantité|nombre).*?([0-9]+)",
            'color': r"couleur.*?(blanc|noir|rouge|bleu|vert|jaune|rose|orange|gris|marron|violet|beige|doré|argenté|turquoise|kaki|bordeaux|ivoire|multicolore|clair|foncé|pastel|fluo|cuivré|camel|ambre|corail|indigo|olive|sable|taupe|saumon|aubergine|anis|lilas|azur|marine|ciel|prune|menthe|chocolat|caramel|café)",
            'size': r"taille.*?(xs|s|m|l|xl|xxl|[0-9]+(cm|mm|cl|ml|l|m))",
            'weight': r"poids.*?([0-9]+\s?(kg|g|gramme|tonne))",
            'scent': r"senteur.*?([a-zA-Z]+)",
            'flavor': r"saveur.*?([a-zA-Z]+)",
            'aroma': r"arôme.*?([a-zA-Z]+)",
            'brand': r"marque.*?([a-zA-Z0-9]+)",
            'model': r"modèle.*?([a-zA-Z0-9]+)",
            'reference': r"référence.*?([A-Z0-9]{6,})",
            'sku': r"SKU.*?([A-Z0-9]+)",
            'expiry': r"date.*péremption.*?([0-9]{2}/[0-9]{2}/[0-9]{4})",
            'origin': r"origine.*?([a-zA-Z]+)",
            'composition': r"composition.*?([a-zA-Z, ]+)",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, chat_history.lower())
            if match:
                confirmations[key] = match.group(1).strip()
        # Extraction dynamique via Meilisearch/base si dispo
        if hasattr(self, 'meili_client') and self.meili_client and hasattr(self, 'index_name') and self.index_name:
            attr_list = get_dynamic_product_attributes(self.meili_client, self.index_name)
            dyn_attrs = extract_product_attributes(chat_history, attr_list)
            confirmations.update(dyn_attrs)
        return confirmations

    def score_response_complexity(self, response: str, chat_history: str, question: str) -> float:
        score = 0.0
        words_count = len(response.split())
        if words_count > 50:
            score += 0.3
        elif words_count > 30:
            score += 0.2
        elif words_count > 15:
            score += 0.1
        repetition_count = 0
        for pattern in self.repetition_patterns:
            if re.search(pattern, response.lower()):
                repetition_count += 1
        score += min(repetition_count * 0.1, 0.2)
        critical_count = sum(1 for keyword in self.critical_keywords 
                           if keyword in response.lower())
        score += min(critical_count * 0.05, 0.3)
        confirmation_detected = any(re.search(pattern, response.lower()) 
                                  for pattern in self.confirmation_patterns)
        if confirmation_detected:
            score -= 0.2
        explicit_questions = ['quel', 'combien', 'comment', 'quand', 'où', 'prix']
        if any(q in question.lower() for q in explicit_questions):
            score += 0.2
        return max(0.0, min(1.0, score))

    def shorten_acknowledgement(self, response: str, known_intent_phrases: list = None, ack_phrases: list = None) -> str:
        """
        Remplace le rappel d’intention par un accusé de réception si détecté en début de réponse.
        """
        if known_intent_phrases is None:
            known_intent_phrases = [
                "vous souhaitez", "je comprends que", "votre demande concerne", "vous avez demandé", "je note que"
            ]
        if ack_phrases is None:
            ack_phrases = ["Bien reçu,", "D’accord,", "OK,"]
        response_strip = response.strip().lower()
        for phrase in known_intent_phrases:
            if response_strip.startswith(phrase):
                # Trouver la fin du segment à remplacer (jusqu’à la première virgule, point, ou ‘?’)
                splitters = [',', '.', '?', ':']
                min_idx = min([response_strip.find(s) for s in splitters if response_strip.find(s) > 0] or [len(response_strip)])
                suite = response[min_idx+1:].lstrip()
                return f"{ack_phrases[0]} {suite}" if suite else ack_phrases[0]
        return response

    def format_response_by_intent(self, response: str, question: str, intent_type: str, next_step: str = "") -> str:
        """
        Formate la réponse selon l'intention détectée (DEMANDE INFO, FOURNITURE INFO, CONFIRMATION).
        """
        if intent_type == "DEMANDE_INFO":
            # Réponse directe + question de relance
            return f"{response.strip()} {next_step}".strip()
        elif intent_type == "FOURNITURE_INFO":
            ack = "Parfait !" if not response.lower().startswith("parfait") else response.split('.')[0]
            return f"{ack} {next_step}".strip()
        elif intent_type == "CONFIRMATION":
            valid = "Noté !" if not response.lower().startswith("noté") else response.split('.')[0]
            return f"{valid} {next_step}".strip()
        else:
            return response

    def apply_fast_rules(self, response: str, chat_history: str, question: str) -> Tuple[str, List[str]]:
        rules_applied = []
        # Remplacement automatique du rappel d’intention par un accusé de réception concis
        result = self.shorten_acknowledgement(response)

        # Détection et formatage par type d'intention
        from core.intent_classifier import intent_classifier, IntentType
        intent_type, _ = intent_classifier.classify_intent(question)
        # Mapping local pour adapter à la structure souhaitée
        if intent_type == IntentType.INFORMATION_SEARCH:
            format_type = "DEMANDE_INFO"
        elif intent_type == IntentType.CONFIRMATION:
            format_type = "CONFIRMATION"
        else:
            format_type = "FOURNITURE_INFO"
        # Pour l'instant next_step est vide, mais on peut l'enrichir si besoin
        result = self.format_response_by_intent(result, question, format_type)

        user_confirmations = self._extract_user_confirmations(chat_history)
        for conf_type, conf_value in user_confirmations.items():
            if conf_value.lower() in result.lower():
                acknowledgments = ["Noté !", "Parfait !", "D'accord !", "Bien reçu !"]
                ack = acknowledgments[hash(conf_value) % len(acknowledgments)]
                pattern = rf".*{re.escape(conf_value)}.*?(?=\.|$)"
                if re.search(pattern, result, re.IGNORECASE):
                    result = re.sub(pattern, ack, result, count=1, flags=re.IGNORECASE)
                    rules_applied.append(f"repetition_replacement_{conf_type}")
        has_critical_confirmation = any(re.search(pattern, result.lower()) 
                                      for pattern in self.confirmation_patterns)
        if has_critical_confirmation:
            rules_applied.append("critical_confirmation_preserved")
            return result, rules_applied
        sentences = result.split('.')
        if len(sentences) > 3:
            result = '. '.join(sentences[:2]).strip()
            if not result.endswith('.'):
                result += '.'
            if not any(word in result.lower() for word in ['puis-je', 'souhaitez', 'voulez']):
                result += " Puis-je vous aider pour autre chose ?"
            rules_applied.append("intelligent_truncation")
        if not result.strip().endswith('?') and 'puis-je' not in result.lower():
            action_phrases = [
                "Autre chose ?", 
                "Je peux vous aider davantage ?",
                "Souhaitez-vous continuer ?"
            ]
            action = action_phrases[len(result) % len(action_phrases)]
            result = result.strip() + f" {action}"
            rules_applied.append("action_orientation")
        return result.strip(), rules_applied

    async def llm_fallback_reformat(self, response: str, chat_history: str, question: str) -> str:
        if not self.llm_client:
            return response
        # Utiliser le même modèle que HyDE (llama3-8b-8192)
        hyde_model = "llama3-8b-8192"
        prompt = f"""
Tu es un expert en concision métier e-commerce. Reformule la réponse ci-dessous en 1 à 2 phrases maximum, SANS RIEN MODIFIER si la réponse est déjà concise, directe, ou contient une confirmation critique (commande, paiement, récapitulatif, données sensibles). 

Réponse à reformuler : "{response}"
Historique récent : "{chat_history[-200:]}"
Question utilisateur : "{question}"

Règles impératives :
- Si la réponse est déjà concise, directe, ou critique, NE MODIFIE RIEN.
- Si la réponse contient une confirmation de commande, de paiement, ou un récapitulatif, NE MODIFIE RIEN.
- Sinon, reformule en 1 à 2 phrases, sans ajouter de mini-synthèse inutile.
- Remplace toute répétition par un accusé de réception simple.
- Garde l'essentiel, oriente vers l'action ou la prochaine étape.
- Ne jamais tronquer ou reformuler les infos sensibles, transactionnelles ou critiques.

Réponse reformulée :"""
        try:
            llm_response = await self.llm_client.complete(
                prompt=prompt,
                model_name=hyde_model,
                temperature=0.3,
                max_tokens=100
            )
            return llm_response.strip()
        except Exception as e:
            print(f"[REFORMAT] Erreur LLM fallback: {e}")
            return response

    async def reformat_decision(
        self, 
        response: str, 
        chat_history: str, 
        question: str
    ) -> Tuple[str, ReformatMeta]:
        import time
        start_time = time.time()
        original_length = len(response)
        cache_key = self._generate_cache_key(response, chat_history, question)
        cache_hit = False
        if self.cache:
            try:
                cached_result = self.cache.generic_get(cache_key)
                if cached_result:
                    import json
                    if isinstance(cached_result, str):
                        cached_result = json.loads(cached_result)
                    processing_time = (time.time() - start_time) * 1000
                    meta = ReformatMeta(
                        score=cached_result['score'],
                        decision=cached_result['decision'],
                        rules_applied=cached_result['rules_applied'],
                        processing_time_ms=processing_time,
                        cache_hit=True,
                        original_length=original_length,
                        final_length=len(cached_result['result'])
                    )
                    return cached_result['result'], meta
            except Exception as e:
                print(f"[REFORMAT] Erreur cache lecture: {e}")
        # === RÈGLES HIÉRARCHIQUES STRICTES ===
        
        # CONDITION 1 (Priorité Absolue) : Préservation Intégrale des Confirmations
        transaction_patterns = [
            r"votre commande.*confirmée",
            r"commande.*confirmée", 
            r"paiement.*validé",
            r"récapitulatif.*commande",
            r"confirmation.*commande",
            r"total.*commande",
            r"détails.*commande"
        ]
        
        is_transaction_confirmation = any(
            re.search(pattern, response.lower()) for pattern in transaction_patterns
        )
        
        is_recap_request = any(
            word in question.lower() for word in ["récapitulatif", "détails", "résumé", "commande"]
        )
        
        if is_transaction_confirmation or is_recap_request:
            final_response = response  # AUCUNE MODIFICATION
            rules_applied = ["critical_transaction_preserved"]
            decision = "no_change"
            print(f"[REFORMAT] PRÉSERVATION INTÉGRALE: Transaction/Récap détecté")
        else:
            # CONDITION 2 : Évaluation d'Impact par Score
            complexity_score = self.score_response_complexity(response, chat_history, question)
            
            if complexity_score < 0.5:  # Seuil critique abaissé
                final_response = response  # PAS DE MODIFICATION
                rules_applied = ["low_impact_preserved"]
                decision = "no_change"
                print(f"[REFORMAT] PRÉSERVATION: Score impact faible ({complexity_score:.2f})")
            else:
                # CONDITION 3 : Application de Concision Standard
                if complexity_score < self.score_threshold:
                    final_response, rules_applied = self.apply_fast_rules(response, chat_history, question)
                    decision = "fast_rules"
                else:
                    final_response = await self.llm_fallback_reformat(response, chat_history, question)
                    rules_applied = ["llm_fallback"]
                    decision = "llm_fallback"
                print(f"[REFORMAT] CONCISION APPLIQUÉE: Score {complexity_score:.2f}")
        if len(final_response.split('.')) > 3 and decision != "llm_fallback":
            print(f"[REFORMAT] Warning: Réponse dépasse 3 phrases malgré le reformatage")
        # === Contrôle de cohérence attribut/quantité ↔ prix (post-processing strict) ===
        try:
            if self.meili_client and self.index_name:
                attr_list = get_dynamic_product_attributes(self.meili_client, self.index_name)
                extracted_attrs = extract_product_attributes(final_response, attr_list)
                # On cherche les attributs de quantité/variante et prix dans la réponse
                # Exemples d'attributs typiques : 'quantité', 'paquet', 'colis', 'prix', 'tarif', 'prix_unitaire', 'prix_total', 'variants', 'prices'
                # On cherche aussi les quantités connues (ex: 60, 300) et prix connus dans les produits de la base
                index = self.meili_client.index(self.index_name)
                # On récupère tous les produits pour croiser les quantités/prix
                try:
                    all_products = index.get_documents({"limit": 200})  # Limite arbitraire, à adapter si besoin
                except Exception as e:
                    all_products = []
                    print(f"[REFORMAT][COHERENCE] Erreur récupération produits: {e}")
                # Extraction des couples quantité/variante → prix dans la base
                valid_pairs = set()
                for prod in all_products:
                    # On tente d'extraire quantité/variante et prix
                    for k in ['quantité', 'paquet', 'colis', 'variants', 'variante', 'conditionnement']:
                        quant = str(prod.get(k, '')).strip()
                        for p in ['prix', 'tarif', 'prix_unitaire', 'prix_total', 'prices', 'tarifs']:
                            price = str(prod.get(p, '')).replace('FCFA','').replace('XOF','').replace(' ','').replace(',','').replace('.','').strip()
                            if quant and price:
                                valid_pairs.add((quant, price))
                # Extraction des quantités/prix mentionnés dans la réponse
                import re
                quant_regex = r"(\b[0-9]{2,4}\b)"  # Ex: 60, 300, 1200
                price_regex = r"([0-9]{3,6})\s*(?:fcfa|xof)?"
                quant_in_resp = re.findall(quant_regex, final_response.lower())
                price_in_resp = re.findall(price_regex, final_response.lower())
                # Correction si un couple quantité/prix n'existe pas dans la base
                incoherent = False
                for q in quant_in_resp:
                    for p in price_in_resp:
                        if (q, p) not in valid_pairs:
                            incoherent = True
                            # Cherche la bonne valeur dans la base pour la quantité q
                            correct_price = None
                            for (qq, pp) in valid_pairs:
                                if qq == q:
                                    correct_price = pp
                                    break
                            if correct_price:
                                # Remplace le mauvais prix par le bon dans la réponse
                                old = f"{q} à {p}"
                                new = f"{q} à {correct_price}"
                                final_response = re.sub(rf"{q}\s*[a-zà ]+{p}", new, final_response, flags=re.IGNORECASE)
                                print(f"[REFORMAT][COHERENCE] Correction automatique: {old} → {new}")
                            else:
                                print(f"[REFORMAT][COHERENCE] Alerte: Quantité {q} sans prix connu dans la base")
                if incoherent:
                    rules_applied = rules_applied + ["auto_correction_attribut_prix"]
                    decision = decision if decision != "no_change" else "auto_corrected"
        except Exception as e:
            print(f"[REFORMAT][COHERENCE] Erreur post-processing cohérence: {e}")
        processing_time = (time.time() - start_time) * 1000
        final_length = len(final_response)
        if self.cache:
            try:
                cache_data = {
                    'result': final_response,
                    'score': complexity_score,
                    'decision': decision,
                    'rules_applied': rules_applied
                }
                self.cache.generic_set(cache_key, cache_data, ttl=3600)
            except Exception as e:
                print(f"[REFORMAT] Erreur cache écriture: {e}")
        meta = ReformatMeta(
            score=complexity_score,
            decision=decision,
            rules_applied=rules_applied,
            processing_time_ms=processing_time,
            cache_hit=cache_hit,
            original_length=original_length,
            final_length=final_length
        )
        return final_response, meta

async def integrate_reformat_agent(
    response: str,
    chat_history: str, 
    question: str,
    redis_cache=None,
    llm_client=None
) -> Tuple[str, dict]:
    agent = DecisionReformatAgent(redis_cache, llm_client)
    final_response, meta = await agent.reformat_decision(response, chat_history, question)
    meta_dict = {
        'score': meta.score,
        'decision': meta.decision,
        'rules_applied': meta.rules_applied,
        'processing_time_ms': meta.processing_time_ms,
        'cache_hit': meta.cache_hit,
        'compression_ratio': meta.final_length / meta.original_length if meta.original_length > 0 else 1.0,
        'original_length': meta.original_length,
        'final_length': meta.final_length
    }
    return final_response, meta_dict

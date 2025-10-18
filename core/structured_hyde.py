import re
from typing import List, Dict, Any
from utils import log3, timing_metric

def _convert_hypothesis_to_regex(query: str) -> str:
    """Convertit une hypothèse en format regex pour améliorer le matching."""
    if not query or len(query.strip()) < 2:
        return query
    
    # Nettoyer la requête
    clean_query = re.sub(r'[^\w\s]', '', query.strip().lower())
    words = clean_query.split()
    
    if len(words) == 1:
        # Mot unique: recherche partielle avec wildcards
        word = words[0]
        if len(word) >= 3:
            return f"{word}*"
        return word
    
    # Mots multiples: chaque mot avec wildcard pour correspondances partielles
    regex_words = []
    for word in words:
        if len(word) >= 3:
            # Ajouter wildcard pour correspondances partielles
            regex_words.append(f"{word}*")
        else:
            regex_words.append(word)
    
    return " ".join(regex_words)

# --- StructureOrientedHyDE : Génération d'hypothèses structurées et scoring ---

class StructureOrientedHyDE:
    def __init__(self):
        # Attributs fixes par type de document (baseés sur la vraie structure Meilisearch)
        self.data_structure = {
            'company_profile': [
                'companyName', 'aiName', 'creationDate', 'description', 'mission', 'sector', 'legalForm', 'activityZone'
            ],
            'product_info': [
                'name', 'category', 'description', 'price', 'variants', 'prices'
            ],
            'payment_info': [
                'payment_methods'
            ],
            'contact_info': [
                'supportContact', 'contact_channel', 'contact_number'
            ],
            'delivery_info': [
                'deliveryZonesFees', 'avgDeliveryTime', 'avg_delivery_time_abidjan', 'avg_delivery_time_other_cities', 'delivery_zones'
            ],
            'policy_info': [
                'returnPolicy', 'policy_type', 'details', 'stockPolicy'
            ],
            'process_info': [
                'orderingProcess', 'process_name', 'details'
            ],
            'location_info': [
                'physicalAddress', 'servedAreas', 'openingHours', 'physical_address_details', 'served_areas'
            ],
            'media_info': [
                'galleryLink', 'videoLink', 'gallery_link', 'video_link'
            ],
            'faq_entry': [
                'faq_question', 'faq_answer'
            ],
            'company_summary_field': [
                'field_name', 'field_value', 'company_name_summary'
            ]
        }
        # Patterns pour détecter le type de question
        self.patterns = {
            'company_profile': re.compile(r'(qui|entreprise|soci[eé]t[eé]|mission|secteur|activit[eé]|objectif|aiName)', re.I),
            'product_info': re.compile(r'(produit|couche|article|prix|tarif|taille|cat[ée]gorie|variant|paquet|quantit[eé]|mod[eè]le)', re.I),
            'contact_info': re.compile(r'(contact|t[eé]l[eé]phone|email|whatsapp|adresse|heures|horaire)', re.I),
            'delivery_info': re.compile(r'(livraison|d[eé]lai|zone|exp[eé]dition|transport|frais)', re.I),
            'policy_info': re.compile(r'(retour|garantie|politique|stock|disponibilit[eé])', re.I),
            'process_info': re.compile(r'(commande|processus|proc[eé]dure|achat)', re.I),
            'location_info': re.compile(r'(adresse|zone|localisation|ouvert|ville|boutique)', re.I),
            'media_info': re.compile(r'(galerie|vid[eé]o|photo|media|contenu visuel)', re.I),
            'faq_entry': re.compile(r'(faq|question|r[eé]ponse|promotions?)', re.I),
            'company_summary_field': re.compile(r'(mission|secteur|nom|objectif|r[eé]sum[eé])', re.I)
        }
        # Trois templates par type pour générer des hypothèses variées
        self.templates = {
            'company_profile': [
                "L'entreprise {companyName} est spécialisée dans {description} et a pour mission {mission}.",
                "Notre société ({companyName}) intervient dans le secteur {sector}, forme juridique {legalForm}, basée à {activityZone}.",
                "L'assistant IA {aiName} accompagne {companyName} créée en {creationDate} pour {mission}."
            ],
            'product_info': [
                "Nous proposons {name} ({category}) : {description}. Tarifs : {price}. Variantes : {variants}.",
                "Produit : {name} - Catégorie : {category}. Prix : {price}. Détails : {description}.",
                "Découvrez nos produits tels que {name} avec différentes tailles ({variants}) et prix ({price})."
            ],
            'contact_info': [
                "Contactez-nous via {contact_channel} au {contact_number} ou sur WhatsApp.",
                "Support client disponible : {supportContact}. Adresse : {address}. Heures : {hours}.",
                "Pour toute question, appelez le {contact_number} ({contact_channel})."
            ],
            'delivery_info': [
                "Livraison en {avgDeliveryTime} en moyenne. Zones : {deliveryZonesFees}.",
                "Délais de livraison : Abidjan ({avg_delivery_time_abidjan}), autres villes ({avg_delivery_time_other_cities}).",
                "Nous livrons dans les zones suivantes : {delivery_zones}."
            ],
            'policy_info': [
                "Notre politique de retour ({policy_type}) : {details}.",
                "Politique de stock : {stockPolicy}.",
                "Conditions de retour des produits : {returnPolicy}."
            ],
            'process_info': [
                "Processus de commande ({process_name}) : {details}.",
                "Comment commander : {orderingProcess}.",
                "Étapes pour passer une commande : {process_name}."
            ],
            'location_info': [
                "Notre adresse physique : {physicalAddress}.",
                "Boutique : {physical_address_details}. Zones : {served_areas}.",
                "Ouverture : {openingHours}."
            ],
            'media_info': [
                "Voir notre galerie de produits : {galleryLink}.",
                "Vidéo de présentation disponible ici : {videoLink}.",
                "Photos : {gallery_link}, Vidéos : {video_link}."
            ],
            'faq_entry': [
                "Question fréquente : {faq_question}. Réponse : {faq_answer}.",
                "FAQ : {faq_question} - {faq_answer}.",
                "Réponse à la question '{faq_question}' : {faq_answer}."
            ],
            'company_summary_field': [
                "Résumé sur {field_name} : {field_value}.",
                "Information clé pour {company_name_summary} sur {field_name} : {field_value}.",
                "{field_name} de l'entreprise : {field_value}."
            ]
        }

    def detect_type(self, user_query: str) -> str:
        for doc_type, pattern in self.patterns.items():
            if pattern.search(user_query):
                return doc_type
        return 'product_info'  # Fallback par défaut

    @timing_metric("generate_structured_hypotheses")
    async def generate_structured_hypotheses(self, user_query: str, context: Dict[str, Any], dynamic_context: str = ""):
        """
        Génère 3 hypothèses structurées robustes pour la recherche HyDE.
        - Validation stricte : aucune hypothèse vide ou non pertinente ne passe.
        - Fallback multi-niveaux si le LLM échoue ou génère des hypothèses non exploitables.
        - Utilise des templates structurés et un contexte dynamique pour guider le LLM.
        - Contrôle de diversité et scoring croisé possible (à utiliser dans la pipeline RAG).
        """
        doc_type = self.detect_type(user_query)
        templates = self.templates.get(doc_type, [])
        
        # Importer le manifeste des mots-clés autorisés
        from .index_manifest import get_allowed_keywords_for_prompt
        allowed_keywords = get_allowed_keywords_for_prompt()
        
        pilot_prompt = (
            f"Tu es un extracteur de MOTS-CLÉS pour recherche. Analyse l'intention puis\n"
            f"Génère exactement 3 requêtes MOTS-CLÉS (pas de phrases).\n"
            f"Question: '{user_query}'. Contexte entreprise: {context.get('companyName', 'N/A')} | secteur: {context.get('sector', 'N/A')}. Contexte dynamique: '{dynamic_context}'.\n"
            f"RÈGLES STRICTES:\n"
            f"- 1 à 3 mots par requête (idéal: 2)\n"
            f"- UNIQUEMENT utiliser ces mots-clés autorisés: {allowed_keywords}\n"
            f"- INTERDICTION d'inventer des mots non listés ci-dessus\n"
            f"- Pas d'introduction, pas de guillemets, pas de ponctuation\n"
            f"- Exemples valides: 'livraison abobo', 'produit prix', 'contact support'\n"
            f"FORMAT EXACT (3 lignes, rien d'autre):\n"
            f"requête une\nrequête deux\nrequête trois"
        )
        try:
            from core.llm_client import complete  # Import absolu pour éviter les erreurs de package
            
            # Tentative de génération avec le LLM
            llm_output = await complete(pilot_prompt, model_name="llama-3.1-8b-instant", temperature=0)
            log3("[HyDE] Réponse LLM reçue", {"longueur": len(str(llm_output)) if llm_output else 0})
            
            # Si la réponse est vide ou invalide, on passe au fallback
            if not llm_output or not isinstance(llm_output, str):
                raise ValueError("Réponse LLM vide ou invalide")
            
            # Nettoyage et validation de la sortie
            hypotheses = clean_hyde_output(llm_output)
            
            # Validation et filtrage des mots-clés générés
            from .index_manifest import validate_generated_keywords
            for hypothesis in hypotheses:
                if isinstance(hypothesis, dict) and "requete" in hypothesis:
                    original_query = hypothesis["requete"]
                    # Extraire et valider les mots-clés
                    words = original_query.split()
                    validated_words = validate_generated_keywords(words)
                    if validated_words:
                        hypothesis["requete"] = _convert_hypothesis_to_regex(" ".join(validated_words))
                    else:
                        # Si aucun mot valide, garder l'original mais le signaler
                        hypothesis["requete"] = _convert_hypothesis_to_regex(original_query)
                        hypothesis["validation_warning"] = "Mots-clés non validés"
            
            # Vérification de la qualité des hypothèses
            if not hypotheses or len(hypotheses) < 2:
                raise ValueError(f"Pas assez d'hypothèses valides: {len(hypotheses) if hypotheses else 0}")
            
            # Log des hypothèses générées
            log3("[HyDE] Hypothèses générées par LLM", {
                "nombre": len(hypotheses),
                "exemples": [h.get("requete", "") for h in hypotheses[:3] if isinstance(h, dict)]
            })
            
            return hypotheses
            
        except Exception as e:
            # Fallback en cas d'échec du LLM
            log3("[HyDE] Fallback: Erreur génération hypothèses (LLM)", str(e))
            
            # Génération des requêtes de fallback
            hypotheses = self._extract_key_terms(user_query)
            
            # Conversion des hypothèses de fallback en format regex
            for hypothesis in hypotheses:
                if isinstance(hypothesis, dict) and "requete" in hypothesis:
                    original_query = hypothesis["requete"]
                    hypothesis["requete"] = _convert_hypothesis_to_regex(original_query)
            
            doc_type = self.detect_type(user_query)
            
            # Ne pas préfixer avec le type de document (on garde uniquement des mots-clés concis)
            
            # Log des requêtes générées
            log3("[HyDE] Fallback intelligent activé", {
                "raison": str(e),
                "requetes_générées": len(hypotheses),
                "type_document": doc_type,
                "exemples_requêtes": [h.get("requete", "") for h in hypotheses[:3] if isinstance(h, dict)]
            })
            
            # Vérification finale des hypothèses avant retour
            if not hypotheses:
                try:
                    from .concept_extractor import extract_key_concepts
                    concepts = extract_key_concepts(str(user_query), top_n=6)
                    # Construire jusqu'à 3 requêtes de 1–3 tokens à partir des concepts
                    kw_reqs = []
                    for c in concepts:
                        toks = re.findall(r"\b\w+\b", c.lower())
                        # Filtrer tokens trop courts et limiter à 3
                        toks = [t for t in toks if len(t) > 2][:3]
                        if not toks:
                            continue
                        q = " ".join(toks)
                        if q not in [x.get("requete") for x in kw_reqs]:
                            kw_reqs.append({"intention": "recherche", "requete": q, "filtres": {}})
                        if len(kw_reqs) >= 3:
                            break
                    if kw_reqs:
                        log3("[HyDE] Fallback final (concepts)", {"exemples": [x["requete"] for x in kw_reqs]})
                        return kw_reqs
                except Exception as e2:
                    log3("[HyDE] Fallback final - concept extractor KO", str(e2))
                # Si tout échoue, retourner vide pour éviter phrases inutiles
                return []
                
            log3("[HyDE] Hypothèses finales", {
                "nombre": len(hypotheses),
                "exemples": [h.get("requete", "") for h in hypotheses[:3] if isinstance(h, dict)]
            })
            
            return hypotheses[:3]  # Retourne au maximum 3 hypothèses

    def _extract_key_terms(self, text: str) -> List[str]:
        """
        Extrait les termes clés et génère des combinaisons de recherche progressives.
        Retourne une liste de requêtes optimisées pour la recherche.
        """
        # Liste des mots vides à exclure
        stop_words = {
            'bonjour', 'salut', 'coucou', 'hello', 'hey', 'hi',
            'est', 'et', 'ou', 'le', 'la', 'les', 'un', 'une', 'des',
            'de', 'du', 'au', 'aux', 'pour', 'avec', 'dans', 'sur',
            'quel', 'quelle', 'quels', 'quelles', 'es', 'est', 'sont',
            'ce', 'cet', 'cette', 'ces', 'mon', 'ma', 'mes', 'ton',
            'ta', 'tes', 'son', 'sa', 'ses', 'notre', 'nos', 'votre',
            'vos', 'leur', 'leurs', 'on', 'nous', 'vous', 'ils', 'elles',
            'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles',
            'y', 'en', 'là', 'ici', 'voici', 'voilà', 'plus', 'moins',
            'très', 'trop', 'peu', 'beaucoup', 'tout', 'tous', 'toute',
            'toutes', 'autre', 'même', 'comme', 'si', 'que', 'quand',
            'où', 'comment', 'pourquoi', 'combien', 'quel', 'quelle',
            'quels', 'quelles', 'ceci', 'cela', 'ça', 'rien', 'personne',
            'aucun', 'aucune', 'certains', 'certaines', 'plusieurs',
            'chaque', 'plusieurs', 'tout', 'tous', 'toute', 'toutes',
            'sans', 'sous', 'vers', 'par', 'dès', 'depuis', 'pendant',
            'jusque', "jusqu'à", 'afin', 'alors', 'aussi', 'bien',
            'car', 'donc', 'ensuite', 'mais', 'ni', 'ou', 'où', 'puis',
            'quand', 'que', 'quoi', 'si', 'sinon', 'soit', 'avez', 'avez-vous',
            # verbes/politesse courants à exclure des requêtes clés
            'souhaiter', 'souhaiterais', 'souhaiterait', 'souhaite', 'souhaitons',
            'connaitre', 'connaître', 'connais', 'connaissons', 'connaissez',
            'savoir', 'sais', 'savons', 'savez',
            'vouloir', 'voudrais', 'voudrait', 'voudrions', 'voudriez',
            'pouvoir', 'peux', 'peut', 'pouvons', 'pouvez', 'pourrais', 'pourrait',
            'aimer', 'aimerais', 'aimerait',
            'demander', 'demande', 'demandez', 'veuillez', 'merci',
            'plait', 'plaît', 'svp', 's il', 'sil',
            # verbes/pronoms problématiques pour nos requêtes
            'donner', 'donne', 'donnes', 'donnez', 'moi'
        }

        # Verbes fréquents à exclure des requêtes (FR/EN)
        verbs_stop = {
            # FR auxiliaires / courants
            'avoir','ai','as','avons','avez','ont',
            'etre','être','suis','es','sommes','êtes','etes','sont',
            'faire','fais','fait','faisons','faites','font',
            'aller','vais','vas','va','allons','allez','vont',
            'acheter','achetez','achete','achète','achetons','achat',
            'vendre','vends','vend','vendons','vendez','vente',
            'trouver','trouve','trouvez','trouvons',
            'chercher','cherche','cherchez','cherchons',
            'obtenir','obtiens','obtient','obtenez','obtenons',
            'besoin','vouloir','souhaiter','demander','donner','payer',
            # EN common
            'be','am','is','are','was','were','been','being',
            'have','has','had','having',
            'do','does','did','doing',
            'get','gets','got','getting','give','gives','giving',
            'need','needs','needing','want','wants','wanting',
            'buy','buys','buying','sell','sells','selling',
            'ask','asks','asking','know','knows','knowing'
        }

        # Nettoyage du texte
        text = text.lower().strip()
        words = re.findall(r'\b\w+\b', text)

        # Filtrage des mots vides et des mots trop courts
        key_terms = [w for w in words if w not in stop_words and w not in verbs_stop and len(w) > 2]

        # Supprimer explicitement les termes liés au prix
        pricing_terms = {'prix', 'tarif', 'tarifs', 'coût', 'cout', 'montant', 'price', 'combien'}
        key_terms = [w for w in key_terms if w not in pricing_terms]

        # Lexiques d'intention (renforcement delivery/product/location)
        delivery_kw = {
            # FR
            'livraison','délai','delai','délais','delais','zones','zone','frais','coût','cout','expédition','expedition','transport','envoi','expédier','expedier',
            'livrer','livré','livre','suivi','retard','horaire','créneau','creneau','point','retrait','ramassage',
            # EN
            'delivery','deliver','shipped','ship','shipping','carrier','courier','zone','zones','fee','fees','cost','time','eta','delay','tracking','slot','pickup','pick-up','pickup-point'
        }
        product_kw = {
            # FR
            'produit','produits','article','articles','marque','modele','modèle','reference','référence','variant','variante','taille','couleur','categorie','catégorie','gamme',
            # EN
            'product','products','item','items','brand','model','reference','sku','variant','size','color','category','range'
        }
        location_kw = {
            # FR
            'adresse','boutique','magasin','point','retrait','agence','localisation','ville','zone','quartier','pays','région','region','siège','siege','entrepot','entrepôt','dépôt','depot',
            # EN
            'address','store','shop','branch','office','location','city','area','region','country','hq','warehouse','depot','pickup','pickup-point'
        }

        # Entités légères
        entities = []
        try:
            phones = re.findall(r"\b(?:\+?\d[\d\s\-]{7,})\b", text)
            emails = re.findall(r"\b[\w\.-]+@[\w\.-]+\.[A-Za-z]{2,}\b", text)
            if phones:
                entities.extend(['telephone contact', 'numero telephone'])
            if emails:
                entities.extend(['adresse email', 'contact email'])
            if 'whatsapp' in text.lower():
                entities.extend(['contact whatsapp', 'numero whatsapp'])
        except Exception:
            pass

        # Construire n-grammes (1 à 3) depuis les mots originaux filtrés
        filtered_words = [w for w in words if w not in stop_words and w not in verbs_stop and w not in pricing_terms]
        ngram_candidates = []
        for n in range(1, 4):
            if len(filtered_words) >= n:
                for i in range(len(filtered_words) - n + 1):
                    ngram = ' '.join(filtered_words[i:i+n])
                    ngram_candidates.append(ngram)

        # Ajouter aussi n-grammes basés sur key_terms (maintient 1–3 mots)
        for n in range(1, 4):
            if len(key_terms) >= n:
                for i in range(len(key_terms) - n + 1):
                    ngram = ' '.join(key_terms[i:i+n])
                    ngram_candidates.append(ngram)

        # Ajouter entités brutes
        ngram_candidates.extend(entities)

        # Scoring simple
        def score(q: str) -> int:
            toks = q.split()
            s = 0
            # Longueur préférée 2–3
            if 2 <= len(toks) <= 3:
                s += 1
            # Intent boosts
            if any(t in delivery_kw for t in toks):
                s += 2
            if any(t in product_kw for t in toks):
                s += 1
            if any(t in location_kw for t in toks):
                s += 2
            # Entités
            if any(t in {'whatsapp', 'telephone', 'téléphone', 'email', 'contact'} for t in toks):
                s += 2
            return s

        # Nettoyage, filtrage, dédup, tri par score
        pool = []
        seen_tmp = set()
        for q in ngram_candidates:
            q2 = re.sub(r"\s+", " ", q.strip())
            if not q2:
                continue
            parts = q2.split()
            if not (1 <= len(parts) <= 3):
                continue
            if any(p in stop_words or p in verbs_stop or p in pricing_terms for p in parts):
                continue
            if q2 in seen_tmp:
                continue
            seen_tmp.add(q2)
            pool.append((score(q2), q2))

        pool.sort(key=lambda x: x[0], reverse=True)

        # Sélection top 3
        final = []
        for _, q in pool:
            final.append({"intention": "recherche", "requete": q, "filtres": {}})
            if len(final) >= 3:
                break

        return final

    def score_hypothesis(self, hits_meili: List[Any], hits_supabase: List[Any]) -> float:
        # Score = nb de hits + diversité + score moyen
        score = 0.0
        if hits_meili:
            score += len(hits_meili) * 1.2
        if hits_supabase:
            score += len(hits_supabase)
        # Bonus diversité (uniquement sur les hits supabase qui sont des dict)
        doc_types = set()
        for h in hits_supabase:
            if isinstance(h, dict) and h.get('document_type'):
                doc_types.add(h.get('document_type'))
        score += len(doc_types) * 0.5
        # Bonus si au moins 1 hit dans chaque source
        if hits_meili and hits_supabase:
            score += 2
        return score

# --- Post-processing robuste pour la sortie HyDE ---
def clean_hyde_output(hypotheses):
    """
    Nettoie et valide la sortie HyDE pour garantir un format strict.
    
    Args:
        hypotheses: Sortie HyDE (chaîne, dictionnaire, liste ou objet déjà formaté)
        
    Returns:
        Liste des hypothèses formatées [{"intention": str, "requete": str, "filtres": dict}]
    """
    # Si l'entrée est None ou vide, retourner une liste vide
    if not hypotheses:
        return []
    
    # Si c'est une chaîne, essayer de la parser comme du JSON
    if isinstance(hypotheses, str):
        try:
            import json
            hypotheses = json.loads(hypotheses)
        except (json.JSONDecodeError, TypeError):
            # Si ce n'est pas du JSON valide, traiter comme du texte brut multi-lignes
            raw_text = str(hypotheses)
            # Normaliser les sauts de ligne
            lines = [l.strip() for l in raw_text.splitlines()]
            # Filtrer lignes vides et introduc/phrases non requêtes
            filtered = []
            for l in lines:
                if not l:
                    continue
                # Supprimer bullets/numéros: '- ', '* ', '1. ', '• '
                l = re.sub(r"^(?:[-*•]\s+|\d+\.|\d+\))\s*", "", l)
                # Ignorer phrases d'introduction
                if re.match(r"^(voici|here are|bien s[uû]r|les requ[eê]tes)\b", l.strip().lower()):
                    continue
                # Retirer guillemets/ponctuation terminale superflue
                l = l.strip().strip('"\'').strip()
                # Remplacer virgules par espace pour éviter rejets
                l = l.replace(",", " ")
                # Condenser espaces
                l = re.sub(r"\s+", " ", l).strip()
                if l:
                    filtered.append(l)
            # Si on a des lignes candidates, transformer en liste d'items string
            if filtered:
                hypotheses = filtered
    
    # Si c'est un dictionnaire unique, le mettre dans une liste
    if isinstance(hypotheses, dict):
        hypotheses = [hypotheses]
    
    # Si c'est une liste, la traiter
    if isinstance(hypotheses, list):
        seen_queries = set()
        cleaned_hypotheses = []
        # Définitions pour le nettoyage des requêtes
        pricing_terms = {'prix', 'tarif', 'tarifs', 'coût', 'cout', 'montant', 'price', 'combien'}
        color_terms_ref = {
            'noir','blanc','gris','rouge','bleu','vert','jaune','orange','marron','violet','rose','beige','doré','argent','argenté','kaki'
        }
        product_terms_ref = {'casque', 'casques', 'helmet'}
        # Verbes fréquents à exclure (FR/EN)
        verbs_stop = {
            # FR auxiliaires / courants
            'avoir','ai','as','avons','avez','ont',
            'etre','être','suis','es','sommes','êtes','etes','sont',
            'faire','fais','fait','faisons','faites','font',
            'aller','vais','vas','va','allons','allez','vont',
            'acheter','achetez','achete','achète','achetons','achat',
            'vendre','vends','vend','vendons','vendez','vente',
            'trouver','trouve','trouvez','trouvons',
            'chercher','cherche','cherchez','cherchons',
            'obtenir','obtiens','obtient','obtenez','obtenons',
            'besoin','vouloir','souhaiter','demander','donner','payer',
            # EN common
            'be','am','is','are','was','were','been','being',
            'have','has','had','having',
            'do','does','did','doing',
            'get','gets','got','getting','give','gives','giving',
            'need','needs','needing','want','wants','wanting',
            'buy','buys','buying','sell','sells','selling',
            'ask','asks','asking','know','knows','knowing'
        }

        def sanitize_query(q: str) -> str:
            # Normalise
            q = q.lower().strip()
            # Supprime termes liés au prix
            tokens = re.findall(r"\b\w+\b", q)
            # Retire prix et verbes
            tokens = [t for t in tokens if t not in pricing_terms and t not in verbs_stop]
            if not tokens:
                return ''
            # Compacte les espaces
            q2 = ' '.join(tokens[:3])
            # Rejette si un verbe a glissé
            if any(t in verbs_stop for t in tokens):
                return ''
            # Heuristique: si produit et couleur présents, réduire à 'produit couleur'
            if any(p in tokens for p in product_terms_ref):
                for t in tokens:
                    if t in color_terms_ref:
                        # Choisir le premier terme produit présent
                        for p in tokens:
                            if p in product_terms_ref:
                                return f"{p} {t}"
                # Sinon, garder au plus 3 mots en priorité
                return ' '.join(tokens[:3])
            # Par défaut, garder entre 1 et 3 mots max
            return ' '.join(tokens[:3])

        # Helpers regex
        import itertools, unicodedata

        def _normalize_token(tok: str) -> str:
            s = ''.join(c for c in unicodedata.normalize('NFD', tok) if unicodedata.category(c) != 'Mn')
            return s.lower()

        def _token_to_regex(tok: str) -> str:
            t = _normalize_token(tok)
            return rf"\\b{re.escape(t)}s?\\b"

        def _build_and_regex(tokens):
            toks = [_token_to_regex(t) for t in tokens]
            parts = [rf"(?=.*{t})" for t in toks]
            return rf"(?i){''.join(parts)}.*"

        def _build_k_of_n_regex(tokens, k: int = 2):
            toks = [_token_to_regex(t) for t in tokens]
            musts = []
            for comb in itertools.combinations(toks, min(k, len(toks))):
                parts = [rf"(?=.*{t})" for t in comb]
                musts.append(''.join(parts))
            if not musts:
                return r"(?i).*"
            return rf"(?i)(?:{'|'.join(musts)}).*"
        
        for h in hypotheses:
            try:
                # Si c'est déjà bien formaté avec une requête
                if isinstance(h, dict) and h.get('requete'):
                    query = sanitize_query(str(h['requete']))
                    word_count = len(query.split())
                    if query and 1 <= word_count <= 3 and query not in seen_queries and not any(t in verbs_stop for t in query.split()):
                        seen_queries.add(query)
                        toks = query.split()
                        k = 2 if len(toks) >= 2 else 1
                        cleaned_hypotheses.append({
                            "intention": str(h.get("intention", "recherche")),
                            "requete": query,
                            "filtres": h.get("filtres", {}),
                            "regex_and": _build_and_regex(toks),
                            "regex_k2": _build_k_of_n_regex(toks, k=k)
                        })
                # Sinon, essayer d'extraire une requête d'un dictionnaire
                elif isinstance(h, dict):
                    # Essayer différents champs possibles pour la requête
                    possible_query_fields = ['query', 'text', 'content', 'question']
                    for field in possible_query_fields:
                        if field in h and h[field]:
                            query = sanitize_query(str(h[field]))
                            word_count = len(query.split())
                            if query and 1 <= word_count <= 3 and query not in seen_queries and not any(t in verbs_stop for t in query.split()):
                                seen_queries.add(query)
                                toks = query.split()
                                k = 2 if len(toks) >= 2 else 1
                                cleaned_hypotheses.append({
                                    "intention": str(h.get("intent", "recherche")),
                                    "requete": query,
                                    "filtres": h.get("filters", {}),
                                    "regex_and": _build_and_regex(toks),
                                    "regex_k2": _build_k_of_n_regex(toks, k=k)
                                })
                                break
                # Si c'est une chaîne, l'utiliser comme requête
                elif isinstance(h, str):
                    # Nettoyage léger similaire au parsing texte brut
                    tmp = h.replace(",", " ").strip()
                    tmp = re.sub(r"\s+", " ", tmp)
                    query = sanitize_query(tmp)
                    word_count = len(query.split())
                    if query and query not in seen_queries and 1 <= word_count <= 3 and not any(t in verbs_stop for t in query.split()):
                        seen_queries.add(query)
                        toks = query.split()
                        k = 2 if len(toks) >= 2 else 1
                        cleaned_hypotheses.append({
                            "intention": "recherche",
                            "requete": query,
                            "filtres": {},
                            "regex_and": _build_and_regex(toks),
                            "regex_k2": _build_k_of_n_regex(toks, k=k)
                        })
            except Exception as e:
                log3("ERREUR_NETTOYAGE_HYDE", f"Erreur lors du nettoyage d'une hypothèse: {str(e)}", level='error')
                continue
        
        # Si on a des hypothèses valides, les retourner
        if cleaned_hypotheses:
            return cleaned_hypotheses[:3]  # Max 3 hypothèses
    
    # Fallback: Si on arrive ici, essayer d'extraire des termes clés
    try:
        from .concept_extractor import extract_key_concepts
        fallback_query = " ".join(extract_key_concepts(str(hypotheses), top_n=5))
        if fallback_query:
            return [{"intention": "recherche", "requete": fallback_query, "filtres": {}}]
    except Exception as e:
        log3("ERREUR_FALLBACK_HYDE", f"Échec de la génération de fallback: {str(e)}", level='error')
    
    # Dernier recours: ne rien retourner (liste vide) pour éviter les requêtes vides en aval
    return []

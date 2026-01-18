"""
🎯 OPTIMISEUR DE CONTEXTE RAG
Réduit les coûts en tokens tout en gardant la qualité
"""

import re
from typing import List, Dict, Tuple

def optimize_context_for_tokens(supabase_context: str, meili_context: str, target_chars: int = 2500) -> str:
    """
    🔧 OPTIMISE LE CONTEXTE POUR RÉDUIRE LES COÛTS EN TOKENS
    
    Args:
        supabase_context: Contexte sémantique Supabase
        meili_context: Contexte textuel MeiliSearch  
        target_chars: Objectif de caractères (défaut: 2500)
    
    Returns:
        Contexte optimisé et dédupliqué
    """
    
    # 1. DÉDUPLICATION INTELLIGENTE
    optimized_context = deduplicate_content(supabase_context, meili_context)
    
    # 2. COMPRESSION DU FORMATAGE
    optimized_context = compress_formatting(optimized_context)
    
    # 3. PRIORISATION DU CONTENU
    if len(optimized_context) > target_chars:
        optimized_context = prioritize_content(optimized_context, target_chars)
    
    return optimized_context

def deduplicate_content(supabase_context: str, meili_context: str) -> str:
    """
    🔄 SUPPRIME LES DOUBLONS ENTRE SUPABASE ET MEILISEARCH
    """
    
    # Extraire les sections uniques de chaque source
    supabase_sections = extract_product_sections(supabase_context)
    meili_sections = extract_meili_sections(meili_context)
    
    # Identifier les doublons
    unique_content = {}
    
    # Prioriser MeiliSearch (plus structuré avec headers)
    for section_id, content in meili_sections.items():
        unique_content[section_id] = content
    
    # Ajouter Supabase seulement si nouveau contenu
    for section_id, content in supabase_sections.items():
        if section_id not in unique_content:
            unique_content[section_id] = content
    
    # Reconstruire le contexte optimisé
    optimized_parts = []
    
    # Grouper par catégorie
    products = []
    delivery = []
    support = []
    
    for section_id, content in unique_content.items():
        if 'produit' in section_id.lower() or 'couches' in content.lower():
            products.append(content)
        elif 'livraison' in content.lower() or 'delivery' in section_id.lower():
            delivery.append(content)
        elif 'support' in content.lower() or 'contact' in content.lower():
            support.append(content)
    
    # Construire le contexte final optimisé
    if products:
        optimized_parts.append("=== PRODUITS ===")
        optimized_parts.extend(products)
    
    if delivery:
        optimized_parts.append("=== LIVRAISON ===")
        optimized_parts.extend(delivery)
    
    if support:
        optimized_parts.append("=== SUPPORT ===")
        optimized_parts.extend(support)
    
    return "\n\n".join(optimized_parts)

def extract_product_sections(context: str) -> Dict[str, str]:
    """
    📦 EXTRAIT LES SECTIONS PRODUITS DU CONTEXTE
    """
    sections = {}
    
    # Regex pour identifier les produits
    product_pattern = r"PRODUITS\s*:\s*([^n]+(?:\n[^=]+)*)"
    matches = re.findall(product_pattern, context, re.MULTILINE | re.IGNORECASE)
    
    for i, match in enumerate(matches):
        product_type = "couches_adultes" if "adultes" in match.lower() else f"produit_{i+1}"
        sections[product_type] = f"PRODUITS : {match.strip()}"
    
    return sections

def extract_meili_sections(context: str) -> Dict[str, str]:
    """
    🔍 EXTRAIT LES SECTIONS MEILISEARCH AVEC HEADERS
    """
    sections = {}
    
    # Regex pour les sections MeiliSearch
    meili_pattern = r"POUR \(([^)]+)\)[^:]*:([^=]+)(?===|$)"
    matches = re.findall(meili_pattern, context, re.MULTILINE | re.DOTALL)
    
    for category, content in matches:
        clean_content = content.strip()
        if clean_content:
            sections[f"meili_{category}"] = clean_content
    
    return sections

def compress_formatting(context: str) -> str:
    """
    📝 COMPRESSE LE FORMATAGE REDONDANT
    """
    
    # Supprimer les headers redondants
    context = re.sub(r"=== INFORMATIONS [^=]+ ===\n", "", context)
    
    # Supprimer les index IDs longs
    context = re.sub(r"Index: [a-zA-Z_]+_[a-zA-Z0-9]{28,} - ", "", context)
    
    # Compresser les séparateurs
    context = re.sub(r"\n---\n\n", "\n\n", context)
    context = re.sub(r"\n{3,}", "\n\n", context)
    
    # Supprimer les métadonnées inutiles
    context = re.sub(r"Document \d+/\d+ :", "", context)
    
    return context.strip()

def prioritize_content(context: str, target_chars: int) -> str:
    """
    🎯 PRIORISE LE CONTENU LE PLUS IMPORTANT
    """
    
    sections = context.split("=== ")
    prioritized_sections = []
    current_length = 0
    
    # Ordre de priorité
    priority_order = ["PRODUITS", "LIVRAISON", "SUPPORT"]
    
    for priority in priority_order:
        for section in sections:
            if section.startswith(priority) and current_length + len(section) < target_chars:
                prioritized_sections.append("=== " + section if not section.startswith("===") else section)
                current_length += len(section)
                break
    
    return "\n\n".join(prioritized_sections)

def get_context_stats(context: str) -> Dict[str, int]:
    """
    📊 STATISTIQUES DU CONTEXTE
    """
    return {
        "characters": len(context),
        "tokens_estimate": len(context) // 4,
        "lines": len(context.split("\n")),
        "sections": len(re.findall(r"===.*===", context))
    }

# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 NOUVELLES OPTIMISATIONS CHIRURGICALES (v2.0)
# ═══════════════════════════════════════════════════════════════════════════════

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MeiliQualityMetrics:
    """Métriques de qualité du contexte Meili"""
    context_length: int
    avg_score: float
    index_diversity: int  # Nombre d'index différents qui ont matché
    has_delivery: bool
    has_products: bool
    has_payment: bool
    total_docs: int


class SmartFallbackManager:
    """
    🎯 GESTIONNAIRE DE FALLBACK INTELLIGENT
    
    Décide si Supabase doit être utilisé en complément de Meili
    basé sur des métriques de qualité.
    
    Stratégie: Meili priority + Supabase fallback conditionnel
    """
    
    # Seuils de qualité pour déclencher fallback
    MIN_CONTEXT_LENGTH = 100  # Meili "faible" si < 100 chars
    MIN_AVG_SCORE = 15.0      # Score moyen minimum acceptable
    MIN_INDEX_DIVERSITY = 1   # Au moins 1 index doit matcher
    MIN_DOCS = 1              # Au moins 1 doc
    
    def __init__(self):
        self.last_decision = None
        self.last_metrics = None
    
    def evaluate_meili_quality(self, meili_context: str, scored_docs: list = None) -> MeiliQualityMetrics:
        """
        📊 Évalue la qualité du contexte Meili
        
        Args:
            meili_context: Contexte formaté retourné par Meili
            scored_docs: Liste des docs avec scores (optionnel)
        
        Returns:
            MeiliQualityMetrics avec toutes les métriques
        """
        context_lower = (meili_context or "").lower()
        
        # Calculer métriques
        context_length = len(meili_context or "")
        
        # Score moyen (si docs disponibles)
        avg_score = 0.0
        if scored_docs:
            scores = [d.get('score', 0) for d in scored_docs if isinstance(d, dict)]
            avg_score = sum(scores) / len(scores) if scores else 0.0
        
        # Diversité d'index (compter les index uniques)
        index_diversity = 0
        if scored_docs:
            unique_indexes = set(d.get('source_index', '') for d in scored_docs if isinstance(d, dict))
            index_diversity = len([idx for idx in unique_indexes if idx])
        else:
            # Estimation depuis le contexte
            if "products_" in context_lower or "produit" in context_lower:
                index_diversity += 1
            if "delivery_" in context_lower or "livraison" in context_lower:
                index_diversity += 1
            if "support_paiement" in context_lower or "paiement" in context_lower:
                index_diversity += 1
            if "localisation_" in context_lower:
                index_diversity += 1
        
        # Détection des types de contenu
        has_delivery = any(kw in context_lower for kw in ["livraison", "zone", "frais", "fcfa", "délai"])
        has_products = any(kw in context_lower for kw in ["produit", "prix", "taille", "variante", "couche"])
        has_payment = any(kw in context_lower for kw in ["paiement", "wave", "orange money", "mtn"])
        
        # Compter docs
        total_docs = len(scored_docs) if scored_docs else meili_context.count('\n\n') + 1 if meili_context else 0
        
        return MeiliQualityMetrics(
            context_length=context_length,
            avg_score=avg_score,
            index_diversity=index_diversity,
            has_delivery=has_delivery,
            has_products=has_products,
            has_payment=has_payment,
            total_docs=total_docs
        )
    
    def should_use_supabase_fallback(
        self, 
        meili_context: str, 
        query: str,
        scored_docs: list = None
    ) -> tuple[bool, str]:
        """
        🎯 Décide si Supabase doit être utilisé
        
        Returns:
            (use_supabase: bool, reason: str)
        """
        metrics = self.evaluate_meili_quality(meili_context, scored_docs)
        self.last_metrics = metrics
        
        query_lower = query.lower()
        
        # Cas 1: Meili vide → Supabase obligatoire
        if metrics.context_length < self.MIN_CONTEXT_LENGTH:
            self.last_decision = ("supabase", "meili_empty_or_too_short")
            logger.info(f"🔄 [FALLBACK] Meili trop court ({metrics.context_length} chars) → Supabase")
            return True, "meili_empty_or_too_short"
        
        # Cas 2: Score moyen trop faible (si disponible)
        if scored_docs and metrics.avg_score < self.MIN_AVG_SCORE:
            self.last_decision = ("supabase", "meili_low_score")
            logger.info(f"🔄 [FALLBACK] Score Meili faible ({metrics.avg_score:.1f}) → Supabase")
            return True, "meili_low_score"
        
        # Cas 3: Query demande livraison mais Meili n'a pas de contenu livraison
        delivery_keywords = ["livraison", "livrer", "frais", "zone", "quartier", "commune"]
        query_wants_delivery = any(kw in query_lower for kw in delivery_keywords)
        if query_wants_delivery and not metrics.has_delivery:
            self.last_decision = ("supabase", "missing_delivery_context")
            logger.info(f"🔄 [FALLBACK] Query livraison mais Meili sans delivery → Supabase")
            return True, "missing_delivery_context"
        
        # Cas 4: Query demande produit mais Meili n'a pas de contenu produit
        product_keywords = ["prix", "produit", "couche", "taille", "combien"]
        query_wants_product = any(kw in query_lower for kw in product_keywords)
        if query_wants_product and not metrics.has_products:
            self.last_decision = ("supabase", "missing_product_context")
            logger.info(f"🔄 [FALLBACK] Query produit mais Meili sans products → Supabase")
            return True, "missing_product_context"
        
        # Cas 5: Query demande paiement mais Meili n'a pas de contenu paiement
        payment_keywords = ["paiement", "payer", "wave", "orange", "mtn", "mobile money"]
        query_wants_payment = any(kw in query_lower for kw in payment_keywords)
        if query_wants_payment and not metrics.has_payment:
            self.last_decision = ("supabase", "missing_payment_context")
            logger.info(f"🔄 [FALLBACK] Query paiement mais Meili sans payment → Supabase")
            return True, "missing_payment_context"
        
        # Cas 6: Meili OK → Pas besoin de Supabase
        self.last_decision = ("meili_only", "meili_sufficient")
        logger.info(f"✅ [MEILI_PRIORITY] Meili suffisant ({metrics.context_length} chars, {metrics.index_diversity} index)")
        return False, "meili_sufficient"


class ContextBudgetManager:
    """
    💰 GESTIONNAIRE DE BUDGET TOKENS PAR SECTION
    
    Applique des limites strictes par type de contenu
    pour optimiser l'utilisation des tokens.
    """
    
    # Budgets par intent principal (en caractères, ~4 chars = 1 token)
    BUDGETS = {
        'product': {
            'catalog': 2000,    # ~500 tokens
            'delivery': 400,    # ~100 tokens
            'payment': 400,     # ~100 tokens
            'company': 300,     # ~75 tokens
            'supabase': 400     # ~100 tokens (fallback)
        },
        'delivery': {
            'catalog': 600,     # ~150 tokens
            'delivery': 1600,   # ~400 tokens
            'payment': 400,     # ~100 tokens
            'company': 300,     # ~75 tokens
            'supabase': 500     # ~125 tokens
        },
        'payment': {
            'catalog': 600,     # ~150 tokens
            'delivery': 400,    # ~100 tokens
            'payment': 1600,    # ~400 tokens
            'company': 300,     # ~75 tokens
            'supabase': 500     # ~125 tokens
        },
        'contact': {
            'catalog': 400,     # ~100 tokens
            'delivery': 300,    # ~75 tokens
            'payment': 300,     # ~75 tokens
            'company': 1200,    # ~300 tokens
            'supabase': 600     # ~150 tokens
        },
        'default': {
            'catalog': 1200,    # ~300 tokens
            'delivery': 600,    # ~150 tokens
            'payment': 600,     # ~150 tokens
            'company': 400,     # ~100 tokens
            'supabase': 600     # ~150 tokens
        }
    }
    
    def __init__(self):
        self.stats = {}
    
    def detect_primary_intent(self, query: str, keywords: dict = None) -> str:
        """
        🎯 Détecte l'intent principal de la query
        """
        query_lower = query.lower()
        
        # Utiliser keywords si disponibles
        if keywords:
            if keywords.get('has_product') or keywords.get('has_price'):
                return 'product'
            if keywords.get('has_delivery') or keywords.get('has_zone'):
                return 'delivery'
            if keywords.get('has_payment'):
                return 'payment'
            if keywords.get('has_contact'):
                return 'contact'
        
        # Détection par mots-clés
        if any(kw in query_lower for kw in ["prix", "produit", "couche", "taille", "combien coûte", "acheter"]):
            return 'product'
        if any(kw in query_lower for kw in ["livraison", "livrer", "zone", "quartier", "frais", "délai"]):
            return 'delivery'
        if any(kw in query_lower for kw in ["paiement", "payer", "wave", "orange money", "mtn"]):
            return 'payment'
        if any(kw in query_lower for kw in ["contact", "téléphone", "whatsapp", "adresse", "situé"]):
            return 'contact'
        
        return 'default'
    
    def truncate_to_budget(self, text: str, max_chars: int) -> str:
        """
        ✂️ Tronque le texte au budget alloué
        
        Coupe intelligemment aux limites de phrases/paragraphes
        """
        if not text or len(text) <= max_chars:
            return text
        
        # Essayer de couper à un paragraphe
        truncated = text[:max_chars]
        
        # Chercher le dernier saut de ligne
        last_newline = truncated.rfind('\n\n')
        if last_newline > max_chars * 0.7:  # Au moins 70% du budget
            return truncated[:last_newline].strip() + "\n..."
        
        # Sinon chercher le dernier point
        last_period = truncated.rfind('.')
        if last_period > max_chars * 0.7:
            return truncated[:last_period + 1].strip()
        
        # Dernier recours: couper au mot
        last_space = truncated.rfind(' ')
        if last_space > max_chars * 0.8:
            return truncated[:last_space].strip() + "..."
        
        return truncated.strip() + "..."
    
    def apply_budgets(
        self, 
        contexts: Dict[str, str], 
        query: str,
        keywords: dict = None
    ) -> Dict[str, str]:
        """
        💰 Applique les budgets à chaque section
        
        Args:
            contexts: {
                'catalog': str,
                'delivery': str,
                'payment': str,
                'company': str,
                'supabase': str
            }
            query: Question utilisateur
            keywords: Keywords détectés (optionnel)
        
        Returns:
            Contextes tronqués selon budget
        """
        primary_intent = self.detect_primary_intent(query, keywords)
        budget_plan = self.BUDGETS.get(primary_intent, self.BUDGETS['default'])
        
        logger.info(f"💰 [BUDGET] Intent: {primary_intent} → Budgets: {budget_plan}")
        
        truncated = {}
        self.stats = {
            'intent': primary_intent,
            'before': {},
            'after': {},
            'savings': {}
        }
        
        for section, content in contexts.items():
            if not content:
                truncated[section] = ""
                continue
            
            max_chars = budget_plan.get(section, 800)
            original_len = len(content)
            
            truncated[section] = self.truncate_to_budget(content, max_chars)
            new_len = len(truncated[section])
            
            self.stats['before'][section] = original_len
            self.stats['after'][section] = new_len
            self.stats['savings'][section] = original_len - new_len
            
            if original_len > max_chars:
                logger.info(f"✂️ [{section.upper()}] {original_len} → {new_len} chars (-{original_len - new_len})")
        
        return truncated
    
    def get_total_savings(self) -> int:
        """Retourne le total de caractères économisés"""
        return sum(self.stats.get('savings', {}).values())


class ConversationHistoryOptimizer:
    """
    🧠 OPTIMISEUR D'HISTORIQUE CONVERSATION
    
    Garde uniquement les N derniers messages pertinents
    avec un budget tokens strict.
    """
    
    MAX_MESSAGES = 5
    MAX_CHARS = 1200  # ~300 tokens
    MAX_MESSAGE_LENGTH = 200  # Tronquer les messages longs
    
    def optimize_history(self, history: list, query: str = None) -> str:
        """
        🧠 Optimise l'historique de conversation
        
        Args:
            history: Liste de messages [{"role": "user/assistant", "content": "..."}]
            query: Query actuelle (pour contexte)
        
        Returns:
            Historique formaté et optimisé
        """
        if not history:
            return ""
        
        # Garder les N derniers messages
        recent = history[-self.MAX_MESSAGES:] if len(history) > self.MAX_MESSAGES else history
        
        # Formater
        lines = []
        for msg in recent:
            role = "Client" if msg.get('role') == 'user' else "Jessica"
            content = msg.get('content', '')
            
            # Tronquer messages trop longs
            if len(content) > self.MAX_MESSAGE_LENGTH:
                content = content[:self.MAX_MESSAGE_LENGTH] + "..."
            
            lines.append(f"{role}: {content}")
        
        formatted = "\n".join(lines)
        
        # Vérifier budget total
        if len(formatted) > self.MAX_CHARS:
            # Garder seulement 3 derniers messages
            lines = lines[-3:]
            formatted = "\n".join(lines)
            
            # Si toujours trop long, tronquer
            if len(formatted) > self.MAX_CHARS:
                formatted = formatted[:self.MAX_CHARS] + "\n..."
        
        logger.info(f"🧠 [HISTORY] {len(history)} msgs → {len(recent)} msgs, {len(formatted)} chars")
        
        return formatted


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES EXPORTÉES
# ═══════════════════════════════════════════════════════════════════════════════

# Instances singleton
_fallback_manager = None
_budget_manager = None
_history_optimizer = None


def get_fallback_manager() -> SmartFallbackManager:
    """Retourne l'instance singleton du fallback manager"""
    global _fallback_manager
    if _fallback_manager is None:
        _fallback_manager = SmartFallbackManager()
    return _fallback_manager


def get_budget_manager() -> ContextBudgetManager:
    """Retourne l'instance singleton du budget manager"""
    global _budget_manager
    if _budget_manager is None:
        _budget_manager = ContextBudgetManager()
    return _budget_manager


def get_history_optimizer() -> ConversationHistoryOptimizer:
    """Retourne l'instance singleton de l'optimiseur d'historique"""
    global _history_optimizer
    if _history_optimizer is None:
        _history_optimizer = ConversationHistoryOptimizer()
    return _history_optimizer


def optimize_rag_context(
    meili_context: str,
    supabase_context: str,
    query: str,
    scored_docs: list = None,
    keywords: dict = None
) -> Dict[str, any]:
    """
    🚀 FONCTION PRINCIPALE D'OPTIMISATION DU CONTEXTE RAG
    
    Applique toutes les optimisations en une seule fonction:
    1. Évalue si Supabase est nécessaire (fallback intelligent)
    2. Applique les budgets tokens par section
    3. Retourne le contexte optimisé
    
    Args:
        meili_context: Contexte MeiliSearch
        supabase_context: Contexte Supabase
        query: Question utilisateur
        scored_docs: Documents scorés (optionnel)
        keywords: Keywords détectés (optionnel)
    
    Returns:
        {
            'optimized_context': str,
            'used_supabase': bool,
            'fallback_reason': str,
            'total_chars_saved': int,
            'metrics': dict
        }
    """
    fallback_mgr = get_fallback_manager()
    budget_mgr = get_budget_manager()
    
    # 1. Décider si Supabase est nécessaire
    use_supabase, fallback_reason = fallback_mgr.should_use_supabase_fallback(
        meili_context, query, scored_docs
    )
    
    # 2. Préparer les contextes par section
    contexts = {
        'catalog': "",
        'delivery': "",
        'payment': "",
        'company': "",
        'supabase': ""
    }
    
    # Parser le contexte Meili pour extraire les sections
    meili_lower = (meili_context or "").lower()
    
    if meili_context:
        # Extraction basique par mots-clés
        lines = meili_context.split('\n')
        current_section = 'catalog'  # Par défaut
        
        for line in lines:
            line_lower = line.lower()
            
            # Détecter changement de section
            if 'livraison' in line_lower or 'delivery' in line_lower or 'zone' in line_lower:
                current_section = 'delivery'
            elif 'paiement' in line_lower or 'wave' in line_lower or 'payment' in line_lower:
                current_section = 'payment'
            elif 'entreprise' in line_lower or 'contact' in line_lower or 'company' in line_lower:
                current_section = 'company'
            elif 'produit' in line_lower or 'prix' in line_lower or 'catalog' in line_lower:
                current_section = 'catalog'
            
            contexts[current_section] += line + '\n'
    
    # Ajouter Supabase si nécessaire
    if use_supabase and supabase_context:
        contexts['supabase'] = supabase_context
    
    # 3. Appliquer les budgets
    truncated_contexts = budget_mgr.apply_budgets(contexts, query, keywords)
    
    # 4. Assembler le contexte final
    final_parts = []
    for section in ['catalog', 'delivery', 'payment', 'company', 'supabase']:
        content = truncated_contexts.get(section, "").strip()
        if content:
            final_parts.append(content)
    
    optimized_context = "\n\n".join(final_parts)
    
    # 5. Calculer les économies
    original_total = len(meili_context or "") + (len(supabase_context or "") if use_supabase else 0)
    final_total = len(optimized_context)
    chars_saved = original_total - final_total
    
    logger.info(f"🚀 [OPTIMIZE] {original_total} → {final_total} chars (-{chars_saved}, -{(chars_saved/original_total*100) if original_total > 0 else 0:.1f}%)")
    
    return {
        'optimized_context': optimized_context,
        'used_supabase': use_supabase,
        'fallback_reason': fallback_reason,
        'total_chars_saved': chars_saved,
        'metrics': {
            'meili_quality': fallback_mgr.last_metrics.__dict__ if fallback_mgr.last_metrics else {},
            'budget_stats': budget_mgr.stats,
            'original_chars': original_total,
            'final_chars': final_total
        }
    }


# EXEMPLE D'UTILISATION
if __name__ == "__main__":
    # Test avec données exemple
    sample_meili = """🚚 LIVRAISON:
Zone Cocody: 1500 FCFA
Zone Yopougon: 2000 FCFA
Délai: 24-48h

📦 CATALOGUE:
PRODUIT: Couches à pression
Taille 1 - 300 couches | 17.900 F CFA
Taille 2 - 300 couches | 18.900 F CFA
Taille 3 - 300 couches | 22.900 F CFA"""
    
    sample_supabase = """Informations complémentaires sur les couches...
Livraison possible dans toute la ville d'Abidjan."""
    
    result = optimize_rag_context(
        meili_context=sample_meili,
        supabase_context=sample_supabase,
        query="Prix couches taille 3 livraison Cocody"
    )
    
    print(f"📊 Résultat optimisation:")
    print(f"   Supabase utilisé: {result['used_supabase']}")
    print(f"   Raison: {result['fallback_reason']}")
    print(f"   Chars économisés: {result['total_chars_saved']}")
    print(f"\n📝 Contexte optimisé:\n{result['optimized_context']}")





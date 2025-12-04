import logging
from typing import Any, Dict

PROMPT_BASE_FAILSAFE = """
# JESSICA - ASSISTANTE COMMANDES E-COMMERCE

## TON RÔLE FONDAMENTAL (TOUJOURS VALABLE)
Tu es Jessica, assistante IA chargée d'aider les clients à passer commande.

**CE QUE TU FAIS :**
✅ Aider le client avec sa demande actuelle
✅ Collecter les infos de commande si pertinent (photo, paiement, zone, téléphone)
✅ Rediriger vers humains si tu ne peux pas aider

**CE QUE TU NE FAIS JAMAIS :**
❌ Inventer des prix, stocks ou détails techniques
❌ Promettre des délais ou conditions sans confirmation
❌ Insister si le client hésite ou refuse
❌ Redemander une info déjà fournie

## RÈGLES DE SÉCURITÉ CRITIQUES

### Si tu ne sais pas quoi répondre :
"Je ne suis pas sûre de bien comprendre. Pouvez-vous reformuler ou contactez le {support_number} pour une aide directe ?"

### Si le client pose une question technique/produit :
"Pour les détails techniques et spécifications produits, le mieux est de contacter directement le {support_number}."

### Si tu es bloquée après 2-3 échanges :
"Je vois que c'est compliqué par message. Un collègue peut mieux vous aider au {support_number}."

### Si demande hors sujet :
"Je gère uniquement les commandes {product_type}. Pour autre chose, je ne peux pas aider."

## TON STYLE
- 1-3 phrases maximum
- Ton chaleureux mais professionnel
- Toujours proposer une solution (même si c'est rediriger)

---
"""

SEGMENTS_SPECIALISES: Dict[str, Dict[str, Any]] = {
    "A": {
        "confiance_min": 0.7,
        "segment": """
## MODE CONVERSATIONNEL ACTIVÉ (Confiance: {confidence:.0%})
Le client fait de la conversation générale ou demande des clarifications.

**Actions :**
1. Réponds chaleureusement (2 phrases max)
2. Ne donne AUCUNE info commerciale
3. Termine par une question d'ouverture

**Exemple :** "Je vais bien merci ! 😊 Comment puis-je vous aider aujourd'hui ?"
""",
        "segment_light": """
## CONTEXTE : Message de type conversationnel
Réponds poliment et demande comment tu peux aider.
""",
    },
    "B": {
        "confiance_min": 0.7,
        "segment": """
## MODE PRODUITS ACTIVÉ (Confiance: {confidence:.0%})
Le client pose des questions sur produits/prix/stock.

**Actions :**
1. Rappelle que tu enregistres les commandes
2. Redirige détails techniques vers {support_number} ou live
3. Si client veut acheter → Propose de passer commande

**Exemple :** "Je m'occupe d'enregistrer les commandes. Pour les prix exacts, mieux vaut vérifier sur le live ou appeler le {support_number}."
""",
        "segment_light": """
## CONTEXTE : Question produit/prix
Redirige vers support pour détails, propose d'enregistrer commande si client veut acheter.
""",
    },
    "C": {
        "confiance_min": 0.65,
        "segment": """
## MODE COMMANDE ACTIVÉ (Confiance: {confidence:.0%})
Le client veut passer commande ou donne des infos.

**État actuel :**
{checklist}

**Actions :**
1. Traiter la demande du client d'abord
2. Guider DOUCEMENT vers infos manquantes (SANS FORCER)
3. Si tout complet (4/4) → Faire récap + demander confirmation

**Exemple :** "Parfait ! Il me manque juste votre zone de livraison pour finaliser."
""",
        "segment_light": """
## CONTEXTE : Processus commande en cours
État: {checklist}
Guide doucement vers les infos manquantes sans forcer.
""",
    },
    "D": {
        "confiance_min": 0.7,
        "segment": """
## MODE SAV ACTIVÉ (Confiance: {confidence:.0%})
Le client a un problème avec sa commande.

**Actions :**
1. Montrer de l'empathie
2. Rassurer
3. Passer le relais à {support_number}

**Exemple :** "Je comprends votre souci 😔. Un collègue du service client va reprendre avec vous pour vous aider."
""",
        "segment_light": """
## CONTEXTE : Problème client
Montre empathie et transfère vers support {support_number}.
""",
    },
}


def build_failsafe_prompt(
    routing_result: Dict[str, Any],
    company_config: Dict[str, Any],
    checklist: str = "",
) -> Dict[str, Any]:
    mode = routing_result.get("mode", "A") or "A"
    confidence = float(routing_result.get("confidence") or 0.5)

    base_prompt = PROMPT_BASE_FAILSAFE.format(
        support_number=company_config.get("support_number", "+225 0787360757"),
        product_type=company_config.get("product_type", "produits"),
    )

    segment_config = SEGMENTS_SPECIALISES.get(mode, SEGMENTS_SPECIALISES["A"])
    confidence_threshold = float(segment_config.get("confiance_min", 0.7))

    if confidence >= confidence_threshold:
        segment = segment_config["segment"].format(
            confidence=confidence,
            support_number=company_config.get("support_number", "+225 0787360757"),
            checklist=checklist or "[Aucune info collectée]",
        )
        strategy = "specialized"
        safety_level = "high"
    elif confidence >= 0.5:
        segment = segment_config["segment_light"].format(
            support_number=company_config.get("support_number", "+225 0787360757"),
            checklist=checklist or "[Aucune info collectée]",
        )
        strategy = "light"
        safety_level = "medium"
    else:
        segment = """
## ⚠️ ATTENTION : Confiance de routage faible ({confidence:.0%})
Si tu n'es pas sûre de comment aider :
1. Demande au client de reformuler
2. OU redirige vers {support_number}

Ne devine pas l'intention du client.
""".format(
            confidence=confidence,
            support_number=company_config.get("support_number", "+225 0787360757"),
        )
        strategy = "base_only"
        safety_level = "low"

    final_prompt = base_prompt + "\n" + segment

    if confidence < 0.6:
        final_prompt += """

---
⚠️ NOTE DE SÉCURITÉ (Confiance routage: {confidence:.0%})
Tu as détecté une incertitude dans la demande du client.
Sois prudente et n'hésite pas à demander clarification ou rediriger.
---
""".format(confidence=confidence)

    return {
        "prompt": final_prompt,
        "strategy": strategy,
        "safety_level": safety_level,
        "confidence": confidence,
        "mode_detected": mode,
        "base_length": len(base_prompt),
        "segment_length": len(segment),
        "total_length": len(final_prompt),
    }


def validate_llm_response(
    llm_response: str,
    routing_result: Dict[str, Any],
    company_config: Dict[str, Any],
) -> Dict[str, Any]:
    warnings = []
    should_fallback = False

    response_lower = (llm_response or "").lower()

    price_patterns = [
        r"\d+\s*(fcfa|f|francs|euros)",
        r"(prix|coute|coûte).*[0-9]",
        r"[0-9].*disponible",
    ]

    import re

    for pattern in price_patterns:
        if re.search(pattern, response_lower):
            warnings.append("⚠️ Prix/stock potentiellement inventé détecté")
            break

    if routing_result.get("mode") == "C":
        missing = routing_result.get("missing_fields", []) or []
        all_fields = ["photo", "paiement", "zone", "telephone"]
        collected_fields = [f for f in all_fields if f not in missing]

        field_keywords = {
            "photo": ["photo", "image", "envoie la photo", "capture"],
            "paiement": ["paiement", "payé", "versement", "preuve"],
            "zone": ["zone", "commune", "quartier", "adresse"],
            "telephone": ["téléphone", "numéro", "portable", "contact"],
        }

        for field in collected_fields:
            if any(kw in response_lower for kw in field_keywords.get(field, [])):
                warnings.append(f"⚠️ Redemande '{field}' déjà collecté")
                should_fallback = True
                break

    if len(llm_response or "") > 500:
        warnings.append("⚠️ Réponse trop longue (>500 chars)")

    if len(llm_response or "") < 20:
        warnings.append("⚠️ Réponse trop courte")
        should_fallback = True

    fallback_response = None
    if should_fallback:
        fallback_response = (
            f"Je ne suis pas sûre de bien comprendre votre demande. "
            f"Pouvez-vous reformuler ou contactez directement le "
            f"{company_config.get('support_number', 'support')} pour une aide personnalisée ?"
        )

    return {
        "is_valid": len(warnings) == 0 and not should_fallback,
        "warnings": warnings,
        "should_fallback": should_fallback,
        "fallback_response": fallback_response,
    }


async def safe_llm_call_with_failsafe(
    routing_result: Dict[str, Any],
    company_config: Dict[str, Any],
    checklist: str,
    user_message: str,
):
    from core.llm_health_check import complete as llm_complete

    prompt_data = build_failsafe_prompt(
        routing_result=routing_result,
        company_config=company_config,
        checklist=checklist,
    )

    print(f"🛡️ Prompt strategy: {prompt_data['strategy']}")
    print(f"🛡️ Safety level: {prompt_data['safety_level']}")
    print(f"🛡️ Confidence: {prompt_data['confidence']:.2%}")

    try:
        llm_response, tokens = await llm_complete(
            prompt_data["prompt"] + f"\n\nClient: {user_message}\n\nJessica:",
            "llama-3.3-70b-versatile",
        )

        validation = validate_llm_response(
            llm_response=llm_response,
            routing_result=routing_result,
            company_config=company_config,
        )

        if validation["should_fallback"]:
            print("⚠️ Validation failed - Using fallback response")
            print(f"   Warnings: {validation['warnings']}")
            final_response = validation["fallback_response"]
        else:
            final_response = llm_response
            if validation["warnings"]:
                print(f"⚠️ Warnings (non-blocking): {validation['warnings']}")

        return {
            "response": final_response,
            "tokens": tokens,
            "validation": validation,
            "prompt_strategy": prompt_data["strategy"],
            "safety_level": prompt_data["safety_level"],
        }

    except Exception as e:  # pragma: no cover - ultime filet
        print(f"❌ LLM Error: {e}")
        return {
            "response": (
                f"Désolée, je rencontre un problème technique. "
                f"Contactez directement le {company_config.get('support_number', 'support')} "
                f"pour une aide immédiate."
            ),
            "tokens": {},
            "validation": {"error": str(e)},
            "prompt_strategy": "error_fallback",
            "safety_level": "emergency",
        }


def log_failsafe_metrics(
    company_id: str,
    routing_result: Dict[str, Any],
    prompt_data: Dict[str, Any],
    validation: Dict[str, Any],
) -> None:
    logger = logging.getLogger(__name__)
    logger.info(
        """
📊 FAILSAFE METRICS [%s]
├─ Confidence: %.2f
├─ Strategy: %s
├─ Safety Level: %s
├─ Validation: %s
├─ Warnings: %d
└─ Fallback Used: %s
""",
        company_id,
        float(routing_result.get("confidence") or 0.0),
        prompt_data.get("strategy"),
        prompt_data.get("safety_level"),
        "✅ PASS" if validation.get("is_valid") else "⚠️ WARNINGS",
        len(validation.get("warnings", [])),
        validation.get("should_fallback", False),
    )

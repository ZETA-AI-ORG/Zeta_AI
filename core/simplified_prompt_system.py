"""
🎯 SYSTÈME DE PROMPT SIMPLIFIÉ - ARCHITECTURE RADICALE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Philosophie : Prompt statique enrichi avec SEULEMENT les infos dynamiques essentielles
- ✅ Prompt statique : Infos entreprise, règles, style
- ✅ Regex livraison : Détection zone + frais en temps réel
- ✅ Cache Gemini : Descriptions produits
- ✅ Meili : UNIQUEMENT coûts temps réel + stock
- ✅ Checklist commande : P[photo] S[specs] Z[zone] T[tel] $[pay]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
import os
from pathlib import Path

from core.order_state_tracker import order_tracker
from core.company_catalog_v2_loader import get_company_catalog_v2, get_company_product_catalog_v2

@dataclass
class OrderChecklistState:
    """État de la checklist de commande"""
    model: bool = False     # Modèle/nom produit (prioritaire pour recherche catalogue)
    details: bool = False   # Détails produit (taille/type/variante)
    quantity: bool = False  # Quantité
    zone: bool = False
    telephone: bool = False
    payment: bool = False
    photo: bool = False  # Optionnelle
    
    def to_string(self) -> str:
        """Format: P[✓] S[✓] Z[✓] T[✓] $[✓]"""
        return (
            f"M[{'✓' if self.model else '○'}] "
            f"D[{'✓' if self.details else '○'}] "
            f"Q[{'✓' if self.quantity else '○'}] "
            f"Z[{'✓' if self.zone else '○'}] "
            f"T[{'✓' if self.telephone else '○'}] "
            f"$[{'✓' if self.payment else '○'}] "
            f"P[{'✓' if self.photo else '○'}]"
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "model": bool(self.model),
                "details": bool(self.details),
                "quantity": bool(self.quantity),
                "zone": bool(self.zone),
                "telephone": bool(self.telephone),
                "payment": bool(self.payment),
                "photo": bool(self.photo),
            },
            ensure_ascii=False,
        )

    def completion(self) -> tuple[int, int]:
        """Retourne (done, total) sur les champs obligatoires."""
        fields = [self.model, self.details, self.quantity, self.zone, self.telephone, self.payment]
        done = sum(1 for v in fields if v)
        total = len(fields)
        return done, total
    
    def get_next_step(self) -> str:
        """Retourne la prochaine action prioritaire"""
        if not self.model:
            return "Identifier modèle/nom du produit"
        if not self.details:
            return "Préciser détails produit (taille/type)"
        if not self.quantity:
            return "Demander quantité (paquets/cartons)"
        if not self.zone:
            return "Demander zone de livraison"
        if not self.telephone:
            return "Demander numéro téléphone"
        if not self.payment:
            return "Confirmer paiement acompte 2000F"
        return "Finaliser commande"
    
    def is_complete(self) -> bool:
        """Vérifie si la checklist est complète"""
        # Photo volontairement optionnelle
        return all([self.model, self.details, self.quantity, self.zone, self.telephone, self.payment])

    @property
    def specs(self) -> bool:
        return bool(self.details)

    @specs.setter
    def specs(self, value: bool) -> None:
        self.details = bool(value)


class SimplifiedPromptSystem:
    """Système de prompt simplifié avec injection dynamique minimale"""
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # PROMPT STATIQUE (FALLBACK SI SUPABASE ÉCHOUE)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    FALLBACK_STATIC_PROMPT = """# JESSICA - ASSISTANTE WHATSAPP RUE DU GROSSISTE

## 🎯 TON IDENTITÉ

Tu es Jessica, assistante commerciale WhatsApp de "Rue du Grossiste" (Côte d'Ivoire).
Tu vends des couches bébé en gros/semi-gros.

**Ton objectif final** : Convertir chaque prospect en client payant.

## 💬 TON STYLE

- Ton WhatsApp ivoirien : direct, chaleureux, naturel
- 1 à 2 phrases max (15-35 mots)
- Max 2 emojis
- 1 question max par message
- Zéro blabla, zéro répétition

## 🧠 TA BOUSSOLE (COMPRENDRE LE CLIENT EN TEMPS RÉEL)

À chaque message, tu te poses 3 questions :

### 1. QU'EST-CE QUE LE CLIENT VEUT VRAIMENT ?
- Poser une question ? → Réponds d'abord avec les infos que tu as
- Donner une info ? → Accuse réception (3-7 mots) puis avance
- Hésiter/explorer ? → Guide doucement vers le produit qui lui convient
- Urgence/problème ? → Empathie + escalade SAV

### 2. OÙ EN EST-ON DANS LA COMMANDE ?
Regarde `<status_slots>` dans le contexte :
- Quels slots sont déjà remplis (`PRESENT`) ?
- Quel est le prochain slot manquant (`MISSING`) ?
- Est-ce que tout est complet ?

### 3. QUELLE EST LA PROCHAINE ACTION UTILE ?
- Si le client pose une question → Réponds
- Si une info manque → Demande-la naturellement
- Si tout est complet → Récap + "Je valide ?"
- Si le client bloque → Propose un choix fermé

**Règle d'or** : Écoute ce que le client dit MAINTENANT, pas ce que tu voulais demander.

## 📊 TES OUTILS (CONTEXTE FOURNI)

Tu reçois dans `<instruction_immediate>` :

### `<intention_client>`
- **intent** : Ce que Python a détecté (ASK_PRICE, ASK_DELIVERY, PAYMENT_DISCUSSION, etc.)
- **certainty** : CERTAIN / PROBABLE / HYPOTHESE
- **reformulation** : Reformulation factuelle de l'intention
- **user_question** : Question exacte du client (si présente)

**Utilise ça pour comprendre le client**, mais ne te limite pas à ça.

### `<status_slots>`
État de chaque champ :
- `status="PRESENT"` → Déjà rempli, ne redemande JAMAIS
- `status="MISSING"` → À collecter

### `<must_ack>` (optionnel)
Si présent, reconnais la donnée reçue (paiement/zone/tel) en 3-7 mots.

### `<must_do>` (optionnel)
Suggestion de question à poser. **C'est une suggestion, pas un ordre.**
Si le client vient de poser une question, réponds d'abord.

## 🛠️ COLLECTE COMMANDE (6 INFOS)

Pour finaliser une commande, tu as besoin de :
1. **PRODUIT** : Quel type ? (Culottes / Pressions)
2. **SPECS** : Quelle taille ? (T1-T7 pour pressions, paquets pour culottes)
3. **QUANTITÉ** : Combien ? (lots/paquets/cartons)
4. **ZONE** : Où livrer ? (commune/quartier)
5. **TÉLÉPHONE** : Numéro pour le livreur
6. **PAIEMENT** : Acompte 2000F Wave (+225 0787360757)

**Collecte naturellement**, pas comme un interrogatoire.

## 📋 INFOS ENTREPRISE (VÉRITÉS ABSOLUES)

### Paiement
- **Abidjan/autour** : Acompte 2000F Wave → Solde à la livraison
- **Intérieur** : Paiement intégral d'avance
- **Numéro Wave** : +225 0787360757

### Livraison
- **Abidjan centre** (Cocody, Plateau, Yopougon, etc.) : 1500F
- **Abidjan périphérie** (Port-Bouët, Bingerville) : 2000F
- **Zones éloignées** (Songon, Anyama, Bassam) : 2500F
- **Intérieur** : 3500F à 5000F selon distance

### Délais
- Commande avant 13h → Livraison jour même
- Commande après 13h → Livraison lendemain

### Produits & Prix

**Couches à pression** (vendues par lot de 300) :
- T1 (0-4kg) : 17.900F | T2 (3-8kg) : 18.900F | T3 (6-11kg) : 22.900F
- T4 (9-14kg) : 25.900F | T5 (12-17kg) : 25.900F | T6 (15-25kg) : 27.900F | T7 (20-30kg) : 28.900F

**Couches culottes** (vendues par paquet de 50) :
- 1 paquet : 5.500F | 2 paquets : 9.800F | 3 paquets : 13.500F
- 6 paquets : 25.000F | 12 paquets : 48.000F | 1 colis (48 paquets) : 168.000F

## 🚨 RÈGLES CRITIQUES (LES SEULES)

### 1. HIÉRARCHIE DE VÉRITÉ
- Verdicts système (`PAYMENT_VERDICT`, `PHONE_VERDICT`) = vérité absolue
- `status_slots` = vérité absolue
- Prix/tailles = uniquement catalogue ci-dessus
- Ce que dit le client ≠ preuve (sauf si confirmé par verdicts)

### 2. ANTI-CONFIRMATION PRÉMATURÉE
Interdit de dire "commande confirmée/validée" si un slot est `MISSING`.

### 3. FINALISATION
Tu finalises uniquement si :
- Tous les 6 slots sont `PRESENT`
- Paiement validé (verdict `VALID` ou acompte confirmé)

Alors tu fais : Récap court + "Je valide ?"

### 4. RÉPONDRE AUX QUESTIONS D'ABORD
Si le client pose une question (prix/livraison/délai), **réponds d'abord**.
Ensuite tu peux demander une info manquante.

## 🔄 FORMAT SORTIE

### Structure Obligatoire

```xml
<thinking>
  <!-- Ce que je vois -->
  <q_exact>[Message client exact]</q_exact>
  
  <intention_client>
    <intent>[ASK_PRICE|ASK_DELIVERY|PAYMENT_DISCUSSION|COMMIT_ORDER|etc.]</intent>
    <certainty>[CERTAIN|PROBABLE|HYPOTHÈSE]</certainty>
    <reformulation>[Reformulation factuelle de Python]</reformulation>
    <user_question topic="[DELIVERY|PRICE|AVAILABILITY|]">[Question exacte si présente]</user_question>
  </intention_client>
  
  <!-- Ce que je comprends -->
  <comprehension>
    Le client veut vraiment : [Analyse contextuelle]
    Où on en est : PRODUIT[✓/?] SPECS[✓/?] QTÉ[✓/?] ZONE[✓/?] TEL[✓/?] PAIEMENT[✓/?]
    Prochaine action utile : [Action concrète]
  </comprehension>
  
  <!-- Détection pour backend (CRITIQUE pour persistance) -->
  <detection>
    - PRODUIT: [Nom produit détecté ou ∅]
    - SPECS: [Taille/détails ou ∅]
    - QUANTITÉ: [Nombre + unité ou ∅]
    - PRIX_CITÉ: [Prix mentionné ou ∅]
  </detection>
  
  <!-- Méta-données pour backend -->
  <intent>[SOCIAL|QUESTION_INFO|EXPLORATION|COMMANDE|SAV|AMBIGU]</intent>
  <priority>[REPLY_FIRST|FOLLOW_NEXT|ESCALADE|CLARIFY]</priority>
  <next>[Description de l'action]</next>
</thinking>

<response>
[Ton message WhatsApp naturel - PAS de balises XML visibles]
</response>
```

### ⚠️ RÈGLES CRITIQUES POUR <detection>

**CHAQUE SLOT = UNE SEULE INFO. NE JAMAIS MÉLANGER.**

✅ **BON** :
```xml
<detection>
  - PRODUIT: Pressions
  - SPECS: T3
  - QUANTITÉ: 1 lot
  - PRIX_CITÉ: 22.900F
</detection>
```

❌ **MAUVAIS** (quantité dans SPECS) :
```xml
<detection>
  - PRODUIT: Pressions
  - SPECS: T3 | Quantité: 1 lot | Prix: 22.900F
  - QUANTITÉ: ∅
  - PRIX_CITÉ: ∅
</detection>
```

**Pourquoi c'est critique ?**
Si tu mets la quantité dans SPECS, le système ne la voit pas dans le slot QUANTITÉ et va redemander "Tu veux combien de lots ?" même si le client l'a déjà dit.

### ⚠️ INTERDICTIONS DE SORTIE

❌ Ne jamais écrire ```xml ou ``` dans <response>
❌ Ne jamais copier-coller la question du client mot pour mot
❌ Ne jamais dépasser 35 mots dans <response>

### 💡 EXEMPLES CONCRETS

#### Exemple 1 : Question Prix
**Client** : "C'est combien les pressions taille 3 ?"
**Contexte** : Tous les slots sont vides

```xml
<thinking>
  <q_exact>C'est combien les pressions taille 3 ?</q_exact>
  
  <intention_client>
    <intent>ASK_PRODUCT_INFO</intent>
    <certainty>CERTAIN</certainty>
    <reformulation>Le client demande le prix des pressions taille 3</reformulation>
    <user_question topic="PRICE">C'est combien les pressions taille 3 ?</user_question>
  </intention_client>
  
  <comprehension>
    Le client veut vraiment : Connaître le prix avant de décider
    Où on en est : PRODUIT[détecté: pressions] SPECS[détecté: T3] QTÉ[?] ZONE[?] TEL[?] PAIEMENT[?]
    Prochaine action utile : Répondre au prix, puis demander quantité
  </comprehension>
  
  <detection>
    - PRODUIT: Pressions
    - SPECS: Taille 3
    - QUANTITÉ: ∅
    - PRIX_CITÉ: ∅
  </detection>
  
  <intent>QUESTION_INFO</intent>
  <priority>REPLY_FIRST</priority>
  <next>Donner prix T3, puis demander quantité</next>
</thinking>

<response>22.900F le lot de 300. Tu en veux combien ?</response>
```

#### Exemple 2 : Info Donnée Spontanément
**Client** : "Je suis à Cocody"
**Contexte** : PRODUIT[✓ Pressions], SPECS[✓ T3], QTÉ[✓ 2 cartons], ZONE[?], TEL[?], PAIEMENT[?]

```xml
<thinking>
  <q_exact>Je suis à Cocody</q_exact>
  
  <intention_client>
    <intent>CONTINUE_ORDER</intent>
    <certainty>CERTAIN</certainty>
    <reformulation>Le client donne sa zone de livraison</reformulation>
    <user_question topic=""></user_question>
  </intention_client>
  
  <comprehension>
    Le client veut vraiment : Avancer dans la commande en donnant sa zone
    Où on en est : PRODUIT[✓] SPECS[✓] QTÉ[✓] ZONE[✓ Cocody reçue] TEL[?] PAIEMENT[?]
    Prochaine action utile : Accuser réception zone + donner frais + demander téléphone
  </comprehension>
  
  <detection>
    - PRODUIT: ∅
    - SPECS: ∅
    - QUANTITÉ: ∅
    - PRIX_CITÉ: ∅
  </detection>
  
  <intent>COMMANDE</intent>
  <priority>FOLLOW_NEXT</priority>
  <next>Confirmer zone, donner frais livraison, demander téléphone</next>
</thinking>

<response>Zone notée ✅ Livraison 1500F. Ton numéro pour le livreur ?</response>
```

#### Exemple 3 : Paiement Reçu (Image)
**Client** : [Envoie capture Wave]
**Contexte** : PRODUIT[✓], SPECS[✓], QTÉ[✓], ZONE[✓ Cocody], TEL[?], PAIEMENT[?]
PAYMENT_VERDICT=VALID (détecté par système)

```xml
<thinking>
  <q_exact>Média envoyé: IMAGE</q_exact>
  
  <intention_client>
    <intent>PAYMENT_DISCUSSION</intent>
    <certainty>CERTAIN</certainty>
    <reformulation>Le client a envoyé une capture de paiement</reformulation>
    <user_question topic=""></user_question>
  </intention_client>
  
  <comprehension>
    Le client veut vraiment : Confirmer qu'il a payé l'acompte
    Où on en est : PRODUIT[✓] SPECS[✓] QTÉ[✓] ZONE[✓] TEL[?] PAIEMENT[✓ VALID]
    Prochaine action utile : Accuser réception paiement + demander dernier slot manquant (TEL)
  </comprehension>
  
  <detection>
    - PRODUIT: ∅
    - SPECS: ∅
    - QUANTITÉ: ∅
    - PRIX_CITÉ: ∅
  </detection>
  
  <intent>COMMANDE</intent>
  <priority>FOLLOW_NEXT</priority>
  <next>Confirmer paiement, demander téléphone pour finaliser</next>
</thinking>

<response>Paiement reçu ✅ Ton numéro pour le livreur ?</response>
```

#### Exemple 4 : Question Hypothétique
**Client** : "Et si je prends 2 cartons ça fait combien ?"
**Contexte** : PRODUIT[✓ Pressions], SPECS[✓ T3], QTÉ[?], autres vides

```xml
<thinking>
  <q_exact>Et si je prends 2 cartons ça fait combien ?</q_exact>
  
  <intention_client>
    <intent>ASK_PRODUCT_INFO</intent>
    <certainty>HYPOTHÈSE</certainty>
    <reformulation>Le client explore le prix pour 2 cartons mais ne s'engage pas</reformulation>
    <user_question topic="PRICE">Et si je prends 2 cartons ça fait combien ?</user_question>
  </intention_client>
  
  <comprehension>
    Le client veut vraiment : Explorer les prix, il hésite encore
    Où on en est : PRODUIT[✓] SPECS[✓] QTÉ[hypothèse: 2 cartons] ZONE[?] TEL[?] PAIEMENT[?]
    Prochaine action utile : Répondre au prix, puis proposer gentiment de confirmer
  </comprehension>
  
  <detection>
    - PRODUIT: ∅
    - SPECS: ∅
    - QUANTITÉ: 2 cartons
    - PRIX_CITÉ: ∅
  </detection>
  
  <intent>EXPLORATION</intent>
  <priority>REPLY_FIRST</priority>
  <next>Donner prix 2 cartons T3, puis demander confirmation quantité</next>
</thinking>

<response>Pour 2 cartons taille 3 c'est 45.800F. Tu prends ça ?</response>
```

#### Exemple 5 : Image Après Question Téléphone
**Client** : [Envoie une image]
**Contexte** : 
- Tour précédent : Jessica a demandé "Ton numéro pour le livreur ?"
- Tour actuel : Client envoie image (capture paiement)
- PAYMENT_VERDICT=VALID détecté
- PRODUIT[✓], SPECS[✓], QTÉ[✓], ZONE[✓], TEL[?], PAIEMENT[?→✓]

```xml
<thinking>
  <q_exact>Média envoyé: IMAGE</q_exact>
  
  <intention_client>
    <intent>PAYMENT_DISCUSSION</intent>
    <certainty>CERTAIN</certainty>
    <reformulation>Le client envoie une capture de paiement</reformulation>
    <user_question topic=""></user_question>
  </intention_client>
  
  <comprehension>
    Le client veut vraiment : Confirmer le paiement (pas donner son téléphone)
    Où on en est : PRODUIT[✓] SPECS[✓] QTÉ[✓] ZONE[✓] TEL[?] PAIEMENT[✓ VALID]
    Prochaine action utile : Accuser paiement, puis demander téléphone (mais PAS répéter la question identique)
    Pattern détecté : Image après question = client change de sujet
  </comprehension>
  
  <detection>
    - PRODUIT: ∅
    - SPECS: ∅
    - QUANTITÉ: ∅
    - PRIX_CITÉ: ∅
  </detection>
  
  <intent>COMMANDE</intent>
  <priority>FOLLOW_NEXT</priority>
  <next>Confirmer paiement validé, reformuler demande téléphone différemment</next>
</thinking>

<response>Paiement validé ✅ Pour la livraison, ton numéro ?</response>
```

**Note** : On NE répète PAS "Ton numéro pour le livreur ?". On reformule : "Pour la livraison, ton numéro ?"

## 🎯 TON MANTRA

**"Comprendre le client MAINTENANT, pas appliquer des règles."**

Si tu hésites, demande-toi :
- Qu'est-ce que le client veut vraiment ?
- Quelle est l'action la plus utile pour lui ?
- Est-ce que je réponds à sa question avant de demander quelque chose ?

Fais confiance à ton jugement. Tu es Jessica, pas un robot."""

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEMPLATE CONTEXTE DYNAMIQUE
    # ═══════════════════════════════════════════════════════════════════════════════
    
    DYNAMIC_TEMPLATE = """
<dynamic_input>
  <catalogue_reference>
{catalogue_reference_block}
  </catalogue_reference>

  <total_snapshot>
{total_snapshot_block}
  </total_snapshot>

  <status_slots>
    <!-- ⚠️ CRITIQUE: État persisté en DB - NE JAMAIS redemander un slot PRESENT -->
    <PRODUIT status="{slot_produit_status}">{slot_produit_value}</PRODUIT>
    <SPECS status="{slot_specs_status}">{slot_specs_value}</SPECS>
    <QUANTITÉ status="{slot_quantite_status}">{slot_quantite_value}</QUANTITÉ>
    <ZONE status="{slot_zone_status}">{slot_zone_value}</ZONE>
    <TÉLÉPHONE status="{slot_telephone_status}">{slot_telephone_value}</TÉLÉPHONE>
    <PAIEMENT status="{slot_paiement_status}">{slot_paiement_value}</PAIEMENT>
  </status_slots>

  <etat_collecte>
    <checklist>
      <produit status="{checklist_produit_status}" valeur="{checklist_produit_value}"/>
      <specs status="{checklist_specs_status}" valeur="{checklist_specs_value}"/>
      <quantite status="{checklist_quantite_status}" valeur="{checklist_quantite_value}"/>
      <zone status="{checklist_zone_status}" valeur="{checklist_zone_value}"/>
      <telephone status="{checklist_telephone_status}" valeur="{checklist_telephone_value}"/>
      <paiement status="{checklist_paiement_status}" valeur="{checklist_paiement_value}"/>
      <photo status="{checklist_photo_status}" valeur="{checklist_photo_value}"/>
    </checklist>
    <next_step>{next_step}</next_step>
  </etat_collecte>

  <livraison>
    <zone>{detected_location}</zone>
    <frais>{shipping_fee}</frais>
    <delai>{delivery_time}</delai>
  </livraison>

  <price_calculation>
{price_calculation_block}
  </price_calculation>

  <verdicts_systeme>
{verdicts_block}
  </verdicts_systeme>

  <validation_errors>
{validation_errors_block}
  </validation_errors>

  <instruction_immediate>
{instruction_block}
  </instruction_immediate>

  <vision_gemini>
{vision_block}
  </vision_gemini>

  <catalogue_context>
{catalogue_block}
  </catalogue_context>

  <historique>
{conversation_history}
  </historique>

  <message_client>
    <texte>{question}</texte>
    <has_image>{has_image}</has_image>
  </message_client>
</dynamic_input>
"""

    @staticmethod
    def _build_product_index_block(catalog_v2: Optional[Dict[str, Any]]) -> str:
        try:
            if not isinstance(catalog_v2, dict):
                return ""

            def _norm_pid(s: str) -> str:
                try:
                    import unicodedata

                    t = str(s or "").strip()
                    t = unicodedata.normalize("NFKD", t)
                    t = "".join(ch for ch in t if not unicodedata.combining(ch))
                    t = re.sub(r"\s+", " ", t).strip()
                    return t.upper()
                except Exception:
                    return str(s or "").strip().upper()

            products: List[str] = []

            # Preferred: explicit products list
            plist = catalog_v2.get("products")
            if isinstance(plist, list):
                for p in plist:
                    if isinstance(p, str) and p.strip():
                        products.append(p.strip())
                    elif isinstance(p, dict):
                        name = str(p.get("name") or p.get("product_name") or p.get("label") or "").strip()
                        if name:
                            products.append(name)

            # Fallback: single product_name
            if not products:
                pn = str(catalog_v2.get("product_name") or catalog_v2.get("name") or "").strip()
                if pn:
                    products.append(pn)

            products = [_norm_pid(x) for x in products if str(x).strip()]
            products = sorted(set([x for x in products if x]))
            if not products:
                return ""

            lines = ["PRODUCT_INDEX:"]
            for pid in products:
                lines.append(f"- product_id={pid}")
            return "\n".join(lines).strip()
        except Exception:
            return ""

    @staticmethod
    def _inject_between_catalogue_markers(prompt: str, content: str) -> str:
        """Inject content only inside [CATALOGUE_START]...[CATALOGUE_END] markers.

        If markers are missing (common with older Supabase prompts), we append a
        marker section at the end so runtime injection always works.
        """
        try:
            import re

            base = str(prompt or "")
            if not base.strip():
                return base
            start_marker = "[CATALOGUE_START]"
            end_marker = "[CATALOGUE_END]"

            pat = r"\[CATALOGUE_START\](.*?)\[CATALOGUE_END\]"
            matches = list(re.finditer(pat, base, flags=re.IGNORECASE | re.DOTALL))
            c = str(content or "").strip()
            replacement = start_marker + "\n" + c + "\n" + end_marker if c else (start_marker + "\n\n" + end_marker)

            if not matches:
                # Fallback: create a catalogue section if prompt doesn't have markers.
                # This prevents silent "empty injection" when Supabase prompt is outdated.
                glue = "\n\n" if base.endswith("\n") else "\n\n"
                return (base.rstrip() + glue + replacement).strip() + "\n"

            # Replace the last occurrence to keep deterministic behavior.
            m = matches[-1]
            out = base[: m.start()] + replacement + base[m.end() :]
            return str(out)
        except Exception:
            return str(prompt or "")

    @staticmethod
    def _build_product_context_block(catalog_v2: Optional[Dict[str, Any]], product_id: str) -> str:
        try:
            pid = str(product_id or "").strip()
            if not pid or not isinstance(catalog_v2, dict):
                return ""

            # Multi-product container: select sub-catalog by product_id
            try:
                plist = catalog_v2.get("products")
                if isinstance(plist, list):
                    selected = None
                    try:
                        # Reuse loader selection (normalizes ids)
                        selected = get_company_product_catalog_v2(str(catalog_v2.get("company_id") or "").strip(), pid)
                    except Exception:
                        selected = None
                    if not isinstance(selected, dict):
                        # Fallback selection by scanning container
                        def _norm_pid2(s: str) -> str:
                            try:
                                import unicodedata

                                t = str(s or "").strip()
                                t = unicodedata.normalize("NFKD", t)
                                t = "".join(ch for ch in t if not unicodedata.combining(ch))
                                t = re.sub(r"\s+", " ", t).strip()
                                return t.upper()
                            except Exception:
                                return str(s or "").strip().upper()

                        pid_norm2 = _norm_pid2(pid)
                        for p in plist:
                            if not isinstance(p, dict):
                                continue
                            ppid = _norm_pid2(str(p.get("product_id") or p.get("product_name") or ""))
                            if ppid and ppid == pid_norm2 and isinstance(p.get("catalog_v2"), dict):
                                selected = p.get("catalog_v2")
                                break
                    if isinstance(selected, dict):
                        # Recurse with mono-product catalog
                        return SimplifiedPromptSystem._build_product_context_block(selected, pid)
            except Exception:
                pass

            vtree = catalog_v2.get("v")
            if not isinstance(vtree, dict):
                return ""

            # If the active_product_id is a stable hashed id (prod_xxxxxxxx), we still want
            # a useful aggregated context over variants/specs/units.
            # In mono-product catalogs, vtree keys are usually variant names (e.g. "Pression").
            # So the prod_ id cannot be used as a vtree lookup key.
            if pid.lower().startswith("prod_"):
                lines_prod: List[str] = [f"PRODUCT_CONTEXT: product_id={pid}"]
                variant_keys_prod = [str(k).strip() for k in vtree.keys() if str(k).strip()]
                variant_keys_prod = sorted(set(variant_keys_prod))
                if variant_keys_prod:
                    lines_prod.append("VARIANTS:")
                for vk in variant_keys_prod:
                    node = vtree.get(vk)
                    if not isinstance(node, dict):
                        continue
                    units_set: set[str] = set()
                    s_map = node.get("s")
                    u_map = node.get("u") if isinstance(node.get("u"), dict) else None
                    if isinstance(u_map, dict) and u_map:
                        for uk in u_map.keys():
                            if str(uk).strip():
                                units_set.add(str(uk).strip())
                    if isinstance(s_map, dict) and s_map:
                        for sub in s_map.values():
                            if not isinstance(sub, dict):
                                continue
                            uu = sub.get("u")
                            if not isinstance(uu, dict):
                                continue
                            for uk in uu.keys():
                                if str(uk).strip():
                                    units_set.add(str(uk).strip())
                    units_sorted = sorted(units_set)
                    if units_sorted:
                        lines_prod.append(f"- variant={vk} | units={', '.join(units_sorted)}")
                    else:
                        lines_prod.append(f"- variant={vk} | units=(none)")
                return "\n".join(lines_prod).strip()

            def _norm_pid(s: str) -> str:
                try:
                    import unicodedata

                    t = str(s or "").strip()
                    t = unicodedata.normalize("NFKD", t)
                    t = "".join(ch for ch in t if not unicodedata.combining(ch))
                    t = re.sub(r"\s+", " ", t).strip()
                    return t.upper()
                except Exception:
                    return str(s or "").strip().upper()

            pid_norm = _norm_pid(pid)
            business_norm = _norm_pid(str(catalog_v2.get("product_name") or catalog_v2.get("name") or ""))

            # Case A: active_product_id refers to a business product (single product_name).
            # Build an aggregated context over variants (vtree keys).
            if business_norm and pid_norm == business_norm:
                lines: List[str] = [f"PRODUCT_CONTEXT: product_id={business_norm}"]
                variant_keys = [str(k).strip() for k in vtree.keys() if str(k).strip()]
                variant_keys = sorted(set(variant_keys))
                if variant_keys:
                    lines.append("VARIANTS:")
                for vk in variant_keys:
                    node = vtree.get(vk)
                    if not isinstance(node, dict):
                        continue
                    # Collect units for this variant
                    units_set: set[str] = set()
                    s_map = node.get("s")
                    u_map = node.get("u") if isinstance(node.get("u"), dict) else None
                    if isinstance(u_map, dict) and u_map:
                        for uk in u_map.keys():
                            if str(uk).strip():
                                units_set.add(str(uk).strip())
                    if isinstance(s_map, dict) and s_map:
                        for sub in s_map.values():
                            if not isinstance(sub, dict):
                                continue
                            uu = sub.get("u")
                            if not isinstance(uu, dict):
                                continue
                            for uk in uu.keys():
                                if str(uk).strip():
                                    units_set.add(str(uk).strip())
                    units_sorted = sorted(units_set)
                    if units_sorted:
                        lines.append(f"- variant={vk} | units={', '.join(units_sorted)}")
                    else:
                        lines.append(f"- variant={vk} | units=(none)")
                return "\n".join(lines).strip()

            # Case B: active_product_id refers to a variant key in vtree (backward compatible).
            node = vtree.get(pid) or vtree.get(pid_norm) or vtree.get(pid.strip())
            if not isinstance(node, dict):
                return ""

            lines2: List[str] = [f"PRODUCT_CONTEXT: variant={pid}"]
            s_map2 = node.get("s")
            if isinstance(s_map2, dict) and s_map2:
                for spec_k in sorted([str(k).strip() for k in s_map2.keys() if str(k).strip()]):
                    sub = s_map2.get(spec_k)
                    if not isinstance(sub, dict):
                        continue
                    u_map2 = sub.get("u")
                    if not isinstance(u_map2, dict):
                        continue
                    units = [str(k).strip() for k in u_map2.keys() if str(k).strip()]
                    units = sorted(set(units))
                    if units:
                        lines2.append(f"- specs={spec_k} | units={', '.join(units)}")
            else:
                u_map2 = node.get("u")
                if isinstance(u_map2, dict) and u_map2:
                    units = [str(k).strip() for k in u_map2.keys() if str(k).strip()]
                    units = sorted(set(units))
                    if units:
                        lines2.append(f"- units={', '.join(units)}")

            return "\n".join(lines2).strip()
        except Exception:
            return ""

    @staticmethod
    def _safe_format(template: str, **kwargs) -> str:
        """Format un template sans casser si un placeholder manque."""
        class _SafeDict(dict):
            def __missing__(self, key):
                return "{" + key + "}"

        try:
            return template.format_map(_SafeDict(**kwargs))
        except Exception:
            return template

    @staticmethod
    def _build_compact_context(
        detected_location: str,
        shipping_fee: str,
        delivery_time: str,
        product_context: str,
        pricing_context: str,
        conversation_history: str,
    ) -> str:
        parts = []
        if detected_location and detected_location != "Non détecté":
            parts.append(f"Livraison: {detected_location} | {shipping_fee} | {delivery_time}")
        if product_context and product_context != "Aucune info produit disponible":
            parts.append(f"Catalogue: {product_context}")
        if pricing_context and pricing_context != "Aucun tarif temps réel disponible":
            parts.append(f"Temps réel: {pricing_context}")
        if conversation_history and conversation_history != "Première interaction":
            parts.append(f"Historique: {conversation_history}")
        return "\n".join(parts) if parts else "Aucun contexte supplémentaire"

    @staticmethod
    def _infer_mode(query: str, checklist: OrderChecklistState) -> str:
        q = (query or "").lower()
        order_keywords = ["je prends", "je commande", "commander", "acheter", "vas-y", "je valide", "je veux", "je prends ça"]
        if any(k in q for k in order_keywords):
            return "CLOSER"
        if any([checklist.model, checklist.details, checklist.zone, checklist.telephone, checklist.payment]):
            return "CLOSER"
        return "HOTESSE"

    def __init__(self):
        """Initialise le système de prompt simplifié"""
        self.checklist_states: Dict[str, OrderChecklistState] = {}
        self._prompt_cache: Dict[str, str] = {}  # Cache des prompts par company_id
        self._prompt_cache_meta: Dict[str, Dict[str, Any]] = {}
    
    async def get_static_prompt(self, company_id: str) -> str:
        """
        Récupère le prompt statique depuis Supabase (table company_rag_configs)
        
        Args:
            company_id: ID de l'entreprise
        
        Returns:
            Prompt statique (depuis Supabase ou fallback hardcodé)
        """
        # Vérifier cache
        if company_id in self._prompt_cache:
            meta = self._prompt_cache_meta.get(company_id) or {}
            src = str(meta.get("source") or "unknown").strip() or "unknown"
            chars = meta.get("chars")
            try:
                chars_i = int(chars) if chars is not None else len(self._prompt_cache[company_id])
            except Exception:
                chars_i = len(self._prompt_cache[company_id])
            print(f"📦 [PROMPT CACHE] Hit pour {company_id} | source={src} | chars={chars_i}")
            return self._prompt_cache[company_id]

        # Charger depuis fichier local (RAG) si activé.
        # IMPORTANT: c'est le prompt attendu pour /chat (pas Botlive).
        try:
            use_local_raw = (os.getenv("SIMPLIFIED_RAG_USE_LOCAL_PROMPT", "true") or "true").strip().lower()
            use_local = use_local_raw in {"1", "true", "yes", "y", "on"}
            if use_local:
                rel_path = (os.getenv("SIMPLIFIED_RAG_LOCAL_PROMPT_PATH") or "prompts/JESSICA_SIMPLIFIED_COMPASS.md").strip()
                p = Path(__file__).resolve().parent.parent / rel_path
                if p.exists() and p.is_file():
                    local_prompt = p.read_text(encoding="utf-8")
                    if local_prompt and len(local_prompt) > 50:
                        self._prompt_cache[company_id] = local_prompt
                        self._prompt_cache_meta[company_id] = {
                            "source": f"local_file:{rel_path}",
                            "chars": int(len(local_prompt)),
                        }
                        print(f"✅ [PROMPT] Chargé depuis fichier local: {rel_path} ({len(local_prompt)} chars)")
                        return local_prompt
        except Exception as _local_e:
            print(f"⚠️ [PROMPT] Échec chargement prompt local: {type(_local_e).__name__}: {_local_e}")
        
        # Charger depuis Supabase
        try:
            from core.botlive_prompts_supabase import BotlivePromptsManager
            
            print(f"🔍 [SUPABASE] Chargement prompt pour {company_id}...")
            manager = BotlivePromptsManager()
            prompt = manager.get_prompt(company_id=company_id, llm_choice="deepseek-v3")
            
            if prompt and len(prompt) > 50:
                # Certains environnements stockent un placeholder Supabase qui renvoie vers
                # core/botlive_prompts_hardcoded.py. Dans ce cas, on charge le vrai prompt.
                p_str = str(prompt)
                if "voir fichier botlive_prompts_hardcoded.py" in p_str.lower() or p_str.strip().startswith("[PROMPT"):
                    try:
                        from core.botlive_prompts_hardcoded import get_prompt_for_llm

                        real_prompt = get_prompt_for_llm("deepseek-v3")
                        if real_prompt and len(real_prompt) > 200:
                            print(f"✅ [PROMPT] Placeholder Supabase détecté → prompt hardcodé chargé: {len(real_prompt)} chars")
                            self._prompt_cache[company_id] = real_prompt
                            self._prompt_cache_meta[company_id] = {
                                "source": "placeholder_hardcoded",
                                "chars": int(len(real_prompt)),
                            }
                            return real_prompt
                    except Exception as _hp_e:
                        print(f"⚠️ [PROMPT] Fallback hardcoded failed: {type(_hp_e).__name__}: {_hp_e}")

                print(f"✅ [SUPABASE] Prompt chargé: {len(p_str)} chars")
                self._prompt_cache[company_id] = p_str
                self._prompt_cache_meta[company_id] = {
                    "source": "supabase",
                    "chars": int(len(p_str)),
                }
                return p_str
            else:
                print(f"⚠️ [SUPABASE] Prompt vide ou trop court, fallback hardcodé")
                fb = self.FALLBACK_STATIC_PROMPT
                self._prompt_cache[company_id] = fb
                self._prompt_cache_meta[company_id] = {
                    "source": "fallback_static_supabase_empty",
                    "chars": int(len(fb)),
                }
                return fb
        
        except Exception as e:
            print(f"❌ [SUPABASE] Erreur chargement prompt: {e}")
            print(f"🔄 [FALLBACK] Utilisation prompt hardcodé")
            fb = self.FALLBACK_STATIC_PROMPT
            self._prompt_cache[company_id] = fb
            self._prompt_cache_meta[company_id] = {
                "source": f"fallback_static_supabase_error:{type(e).__name__}",
                "chars": int(len(fb)),
            }
            return fb
    
    def get_checklist_state(self, user_id: str, company_id: str) -> OrderChecklistState:
        """Récupère l'état de la checklist pour un utilisateur"""
        key = f"{company_id}:{user_id}"
        if key not in self.checklist_states:
            self.checklist_states[key] = OrderChecklistState()
        return self.checklist_states[key]
    
    def update_checklist_from_message(
        self, 
        user_id: str, 
        company_id: str, 
        message: str,
        has_image: bool = False
    ) -> OrderChecklistState:
        """Met à jour la checklist en fonction du message utilisateur"""
        checklist = self.get_checklist_state(user_id, company_id)
        message_lower = message.lower()
        
        # Photo
        if has_image:
            checklist.photo = True

        # Modèle/nom produit (prioritaire)
        # Heuristique légère: marques/modèles + mention explicite de couches + variante
        has_model = bool(
            re.search(
                r"\b(pampers|molfix|huggies|couche(s)?\s+(pampers|molfix|huggies)|baby\s*dry|premium\s*care)\b",
                message_lower,
            )
        )
        if has_model:
            checklist.model = True
        
        # Détails (taille/type/variante)
        has_size = bool(re.search(r'\b(taille|size|t\s?\d+|\bt\d+\b|newborn|nb|xl|xxl|l|m|s)\b', message_lower))
        has_variant = bool(re.search(r'\b(baby\s*dry|premium\s*care|pants|culotte|tape|adhésive|nuit|jour)\b', message_lower))
        if has_size or has_variant:
            checklist.details = True

        # Quantité
        has_quantity = bool(re.search(r'\b(\d+)\s*(cartons?|carton|paquets?|packs?|unités?)\b', message_lower))
        if has_quantity or "quantité" in message_lower:
            checklist.quantity = True
        
        # Zone
        if re.search(r'\b(cocody|yopougon|plateau|adjamé|abobo|marcory|koumassi|treichville|abidjan|bouaké|yamoussoukro|daloa|san-pedro|korhogo|man)\b', message_lower):
            checklist.zone = True
        
        # Téléphone
        if re.search(r'(\+225\s?\d{10}|0\d{9}|\d{10})', message):
            checklist.telephone = True
        
        # Paiement (mention acompte/wave/payer)
        # IMPORTANT: ne pas valider le slot paiement sur simple mention.
        # Le paiement est considéré collecté uniquement si confirmé par la preuve (verdict/état persisté).

        return checklist
    
    async def build_prompt(
        self,
        query: str,
        user_id: str,
        company_id: str,
        detected_location: Optional[str] = None,
        shipping_fee: Optional[str] = None,
        delivery_time: Optional[str] = None,
        product_context: str = "",
        pricing_context: str = "",
        conversation_history: str = "",
        instruction_block: str = "",
        validation_errors_block: str = "",
        price_calculation_block: str = "",
        catalogue_reference_block: str = "",
        has_image: bool = False
    ) -> str:
        """
        Construit le prompt final avec injection dynamique minimale
        
        Args:
            query: Question utilisateur
            user_id: ID utilisateur
            company_id: ID entreprise
            detected_location: Zone détectée par regex
            shipping_fee: Frais de livraison détectés
            delivery_time: Délai de livraison
            product_context: Descriptions produits (Cache Gemini)
            pricing_context: Coûts temps réel (Meili)
            conversation_history: Historique conversation
            has_image: Si le message contient une image
        
        Returns:
            Prompt complet prêt pour le LLM
        """
        # Mettre à jour la checklist
        checklist = self.update_checklist_from_message(
            user_id, company_id, query, has_image
        )

        # Load catalog_v2 from backend cache/local file (token-safe multi-product runtime).
        try:
            catalog_v2 = get_company_catalog_v2(company_id)
        except Exception:
            catalog_v2 = None

        # Active product id (hot-swap) persisted by simplified_rag_engine from detected_items_json.
        try:
            active_product_id = str(order_tracker.get_custom_meta(user_id, "active_product_id", default="") or "").strip()
        except Exception:
            active_product_id = ""

        # Human-readable product label (optional) persisted by simplified_rag_engine.
        # Useful when active_product_id is a stable prod_xxxx which may not match the catalog's product_name.
        try:
            active_product_label = str(order_tracker.get_custom_meta(user_id, "active_product_label", default="") or "").strip()
        except Exception:
            active_product_label = ""

        # Valeurs réelles déjà collectées (source: OrderStateTracker)
        st = None
        try:
            st = order_tracker.get_state(user_id)
        except Exception:
            st = None

        expected_deposit_str = str(os.getenv("EXPECTED_DEPOSIT", "2000 FCFA") or "2000 FCFA").strip()

        company_name_s = str(os.getenv("COMPANY_NAME", "Rue du Grossiste") or "Rue du Grossiste").strip()
        company_phone_s = str(os.getenv("COMPANY_PHONE", "+225 0160924560") or "+225 0160924560").strip()
        payment_phone_s = str(os.getenv("PAYMENT_PHONE", "+225 0787360757") or "+225 0787360757").strip()
        payment_methods_s = str(os.getenv("PAYMENT_METHODS", "Wave") or "Wave").strip()

        def _mask_phone(s: str) -> str:
            s = str(s or "").strip()
            if not s:
                return ""
            digits = re.sub(r"\D+", "", s)
            # Format CI typique: 10 chiffres (0XXXXXXXXX) ou 12 (225XXXXXXXXXX)
            if len(digits) <= 6:
                return s
            # conserver début + fin, masquer milieu
            keep_head = 4
            keep_tail = 2
            head = digits[:keep_head]
            tail = digits[-keep_tail:]
            return f"{head}{'X' * max(0, len(digits) - keep_head - keep_tail)}{tail}"

        def _as_value(v: Optional[str]) -> str:
            return str(v or "").strip()

        def _kv_parse(line: str) -> Dict[str, str]:
            parts = [p.strip() for p in str(line or "").split("|")]
            out: Dict[str, str] = {}
            for p in parts:
                if not p:
                    continue
                if "=" in p:
                    k, val = p.split("=", 1)
                    out[k.strip().lower()] = val.strip()
                elif ":" in p:
                    k, val = p.split(":", 1)
                    out[k.strip().lower()] = val.strip()
                else:
                    # token brut
                    out.setdefault("_raw", "")
                    out["_raw"] = (out["_raw"] + " | " + p).strip(" |")
            return out

        def _extract_quantity_value(text: str) -> str:
            m = re.search(r"\b(\d+)\s*(cartons?|carton|paquets?|packs?|unités?)\b", str(text or ""), flags=re.IGNORECASE)
            if not m:
                return ""
            n = m.group(1)
            u = m.group(2)
            return f"{n} {u}".strip()

        # Checklist value mapping
        produit_val = _as_value(getattr(st, "produit", None) if st else None)
        specs_val = _as_value(getattr(st, "produit_details", None) if st else None)
        zone_val = detected_location or _as_value(getattr(st, "zone", None) if st else None)
        tel_val = _as_value(getattr(st, "numero", None) if st else None)
        paiement_val = _as_value(getattr(st, "paiement", None) if st else None)
        quantite_val = _as_value(getattr(st, "quantite", None) if st else None) or _extract_quantity_value(query) or _extract_quantity_value(conversation_history)

        # Forcer l'état checklist.payment depuis l'état persistant uniquement si paiement validé.
        try:
            if paiement_val and str(paiement_val).lower().startswith("validé_"):
                checklist.payment = True
        except Exception:
            pass

        # Séparer verdicts/vision (lignes techniques) du reste du catalogue context
        product_context_s = product_context or "Aucune info produit disponible"
        verdict_lines: List[str] = []
        vision_lines: List[str] = []
        catalogue_lines: List[str] = []

        try:
            for raw_line in str(product_context_s).splitlines():
                line = str(raw_line or "").strip()
                if not line:
                    continue
                up = line.upper()
                if up.startswith("PAYMENT_VERDICT") or up.startswith("PHONE_VERDICT") or up.startswith("LOCATION_VERDICT"):
                    verdict_lines.append(line)
                elif up.startswith("VISION_GEMINI"):
                    vision_lines.append(line)
                else:
                    catalogue_lines.append(line)
        except Exception:
            catalogue_lines = [product_context_s]

        # Verdicts structurés (attributs XML) + fallback brut
        verdicts_xml_lines: List[str] = []
        if verdict_lines:
            for v in verdict_lines:
                up = str(v).upper()
                data = _kv_parse(v)
                if up.startswith("PAYMENT_VERDICT"):
                    status = (data.get("payment_verdict", "") or data.get("status", "")).upper()
                    amount = data.get("amount", "") or data.get("montant", "")
                    received = data.get("received", "") or data.get("recu", "")
                    required = data.get("required", "") or data.get("requis", "")
                    diff = data.get("diff", "") or data.get("difference", "")
                    missing = data.get("missing", "") or data.get("manque", "")
                    provider = data.get("provider", "")
                    conf = data.get("confidence", "") or data.get("confiance", "")
                    reason = data.get("reason", "")
                    expected = _mask_phone(data.get("expected", ""))
                    got = _mask_phone(data.get("got", ""))
                    # statut affichable
                    statut_aff = "VALID" if status == "VALID" else ("REFUSED" if status == "REFUSED" else (status or "∅"))
                    montant_aff = (amount if amount else "∅")
                    received_aff = (received if received else "∅")
                    required_aff = (required if required else "∅")
                    diff_aff = (diff if diff else "∅")
                    missing_aff = (missing if missing else "∅")
                    provider_aff = (provider if provider else "∅")
                    conf_aff = (conf if conf else "∅")
                    reason_aff = (reason if reason else "∅")
                    expected_aff = (expected if expected else "∅")
                    got_aff = (got if got else "∅")
                    verdicts_xml_lines.append(
                        "    <payment_verdict"
                        f" status=\"{statut_aff}\""
                        f" montant=\"{montant_aff}\""
                        f" received=\"{received_aff}\""
                        f" required=\"{required_aff}\""
                        f" diff=\"{diff_aff}\""
                        f" missing=\"{missing_aff}\""
                        f" provider=\"{provider_aff}\""
                        f" confiance=\"{conf_aff}\""
                        f" raison=\"{reason_aff}\""
                        f" beneficiaire_attendu=\"{expected_aff}\""
                        f" beneficiaire_recu=\"{got_aff}\""
                        "/>"
                    )
                elif up.startswith("PHONE_VERDICT"):
                    status = (data.get("phone_verdict", "") or data.get("status", "")).upper()
                    statut_aff = "OK" if status == "OK" else ("MANQUANT" if status in ("MISSING", "ABSENT") else (status or "∅"))
                    tel_aff = _mask_phone(tel_val) if tel_val else "∅"
                    verdicts_xml_lines.append(
                        "    <phone_verdict"
                        f" status=\"{statut_aff}\""
                        f" valeur=\"{tel_aff}\""
                        "/>"
                    )
                elif up.startswith("LOCATION_VERDICT"):
                    status = (data.get("location_verdict", "") or data.get("status", "")).upper()
                    statut_aff = "OK" if status in ("OK", "DETECTED") else (status or "∅")
                    zone_aff = zone_val or "∅"
                    verdicts_xml_lines.append(
                        "    <location_verdict"
                        f" status=\"{statut_aff}\""
                        f" zone=\"{zone_aff}\""
                        "/>"
                    )
                else:
                    verdicts_xml_lines.append(f"    <raw>{v}</raw>")
        verdicts_block = "\n".join(verdicts_xml_lines) if verdicts_xml_lines else "    <empty>∅</empty>"

        # Vision structurée (best-effort)
        vision_xml_lines: List[str] = []
        if vision_lines:
            for v in vision_lines:
                txt = str(v)
                # tenter d'extraire un montant
                amount_m = re.search(r"\bamount\b\s*[=:]?\s*(\d+)", txt, flags=re.IGNORECASE)
                conf_m = re.search(r"\bconfidence\b\s*[=:]?\s*(\d*\.?\d+)", txt, flags=re.IGNORECASE)
                amount = amount_m.group(1) if amount_m else ""
                conf = conf_m.group(1) if conf_m else ""
                resume = txt
                if txt.upper().startswith("VISION_GEMINI="):
                    resume = txt.split("=", 1)[1].strip()
                vision_xml_lines.append(
                    "    <vision>\n"
                    f"      <type>GeminiVision</type>\n"
                    f"      <resume>{resume}</resume>\n"
                    f"      <montant_detecte>{(amount + ' FCFA') if amount else '∅'}</montant_detecte>\n"
                    f"      <confiance>{conf or '∅'}</confiance>\n"
                    "    </vision>"
                )
        vision_block = "\n".join(vision_xml_lines) if vision_xml_lines else "    <empty>∅</empty>"
        catalogue_block = "\n".join([f"    <line>{v}</line>" for v in catalogue_lines]) if catalogue_lines else "    <line>∅</line>"

        # Fallback: si aucun catalogue_reference explicite n'est fourni, on recycle le catalogue_context.
        # Cela garantit que le LLM a bien un bloc <catalogue_reference> à lire (même si simplifié).
        catalogue_reference_block_s = str(catalogue_reference_block or "").strip()
        if not catalogue_reference_block_s:
            catalogue_reference_block_s = catalogue_block

        # Construire le contexte dynamique
        # Delivery fee must be based ONLY on the detected zone (not on product/qty).
        # IMPORTANT: the zone might be detected POST-LLM (so not yet persisted in zone_val).
        # To avoid empty shipping fee on the same turn, we best-effort extract from the current query.
        detected_location_s = zone_val or detected_location or "Non détecté"
        shipping_fee_s = ""
        try:
            from core.delivery_zone_extractor import extract_delivery_zone_and_cost

            zone_for_fee = str(zone_val or "").strip()
            if not zone_for_fee:
                try:
                    zinfo_q = extract_delivery_zone_and_cost(str(query or ""))
                    if isinstance(zinfo_q, dict):
                        zname = str(zinfo_q.get("name") or "").strip()
                        if zname:
                            detected_location_s = zname
                        zone_for_fee = zname or zone_for_fee
                except Exception:
                    pass

            if zone_for_fee:
                zinfo = extract_delivery_zone_and_cost(zone_for_fee)
                fee = (zinfo or {}).get("cost") if isinstance(zinfo, dict) else None
                if isinstance(fee, (int, float)) and fee > 0:
                    shipping_fee_s = f"{int(fee)} FCFA"
        except Exception:
            shipping_fee_s = ""

        if not str(shipping_fee_s or "").strip():
            shipping_fee_s = str(shipping_fee or "").strip() or "À confirmer"

        delivery_time_s = delivery_time or "À confirmer"
        pricing_context_s = pricing_context or "Aucun tarif temps réel disponible"
        conversation_history_s = conversation_history or "Première interaction"

        delai_message_s = ""
        delai_calc_failed = False
        try:
            from core.timezone_helper import get_current_time_ci, is_same_day_delivery_possible

            now_ci = get_current_time_ci()
            delai_s = "aujourd'hui" if is_same_day_delivery_possible() else "demain"
            bucket = ""
            if now_ci is not None:
                h = int(getattr(now_ci, "hour", 0) or 0)
                if 5 <= h < 11:
                    bucket = "Matin"
                elif 11 <= h < 14:
                    bucket = "Midi"
                elif 14 <= h < 19:
                    bucket = "Après-midi"
                else:
                    bucket = "Soir"

            if bucket and delai_s:
                delai_message_s = f"⏰ HEURE CI: {bucket}. Livraison prévue {delai_s}."
            elif bucket:
                delai_message_s = f"⏰ HEURE CI: {bucket}."
            elif delai_s:
                delai_message_s = f"Livraison prévue {delai_s}."
        except Exception as _delai_e:
            delai_message_s = ""
            delai_calc_failed = True
            try:
                if str(os.getenv("LOG_PLACEORDER_PROMPT", "") or "").strip().lower() in {"1", "true", "yes", "on"}:
                    logger.warning(f"[PROMPT][PLACEORDER] delai_message_compute_failed: {type(_delai_e).__name__}: {_delai_e}")
            except Exception:
                pass

        # Snapshot total (persisté en meta) pour résister au tronquage de l'historique.
        # Le LLM doit s'en servir comme référence si le client reparle du total.
        snap = None
        try:
            snap = order_tracker.get_custom_meta(user_id, "last_total_snapshot", default=None)
        except Exception:
            snap = None

        total_snapshot_lines: List[str] = []
        if isinstance(snap, dict):
            zone_snap = str(snap.get("zone") or "").strip()
            total_val = snap.get("total")
            subtotal_val = snap.get("product_subtotal")
            delivery_val = snap.get("delivery_fee")
            ts = str(snap.get("timestamp") or "").strip()
            if total_val is not None:
                total_snapshot_lines.append(f"    <total_fcfa>{int(total_val)}</total_fcfa>")
            if subtotal_val is not None:
                total_snapshot_lines.append(f"    <product_subtotal_fcfa>{int(subtotal_val)}</product_subtotal_fcfa>")
            if delivery_val is not None:
                total_snapshot_lines.append(f"    <delivery_fee_fcfa>{int(delivery_val)}</delivery_fee_fcfa>")
            if zone_snap:
                total_snapshot_lines.append(f"    <zone>{zone_snap}</zone>")
            if ts:
                total_snapshot_lines.append(f"    <timestamp>{ts}</timestamp>")
        else:
            pass

        total_snapshot_block = "\n".join(total_snapshot_lines) if total_snapshot_lines else "    <empty>∅</empty>"

        def _status(v: bool) -> str:
            return "✓" if v else "∅"

        def _value_or_empty(v: str) -> str:
            vv = str(v or "").strip()
            return vv if vv else ""

        def _check_value(status_bool: bool, value: str) -> str:
            if not status_bool:
                return ""
            vv = _value_or_empty(value)
            return vv if vv else "(confirmé)"

        # Statuts slots persistés
        # IMPORTANT: pour PAIEMENT, seul un paiement VALIDÉ compte comme PRESENT.
        def _slot_status(val: str) -> str:
            return "PRESENT" if (val and str(val).strip()) else "MISSING"

        def _slot_status_paiement(val: str) -> str:
            v = str(val or "").strip()
            if not v:
                return "MISSING"
            v_up = v.upper()
            if v_up.startswith("VALIDÉ_") or v_up.startswith("VALIDE_") or v_up.startswith("VALIDE"):
                return "PRESENT"
            return "MISSING"
        
        dynamic_context = self.DYNAMIC_TEMPLATE.format(
            slot_produit_status=_slot_status(produit_val),
            slot_produit_value=produit_val or "",
            slot_specs_status=_slot_status(specs_val),
            slot_specs_value=specs_val or "",
            slot_quantite_status=_slot_status(quantite_val),
            slot_quantite_value=quantite_val or "",
            slot_zone_status=_slot_status(zone_val),
            slot_zone_value=zone_val or "",
            slot_telephone_status=_slot_status(tel_val),
            slot_telephone_value=_mask_phone(tel_val) if tel_val else "",
            slot_paiement_status=_slot_status_paiement(paiement_val),
            slot_paiement_value=paiement_val or "",
            checklist_produit_status=_status(checklist.model),
            checklist_produit_value=_check_value(checklist.model, produit_val),
            checklist_specs_status=_status(checklist.details),
            checklist_specs_value=_check_value(checklist.details, specs_val),
            checklist_quantite_status=_status(checklist.quantity),
            checklist_quantite_value=_check_value(checklist.quantity, quantite_val),
            checklist_zone_status=_status(checklist.zone),
            checklist_zone_value=_check_value(checklist.zone, zone_val),
            checklist_telephone_status=_status(checklist.telephone),
            checklist_telephone_value=_check_value(checklist.telephone, _mask_phone(tel_val)),
            checklist_paiement_status=_status(checklist.payment),
            checklist_paiement_value=_check_value(checklist.payment, paiement_val),
            checklist_photo_status=_status(checklist.photo),
            checklist_photo_value=_check_value(checklist.photo, ""),
            next_step=checklist.get_next_step(),
            detected_location=detected_location_s,
            shipping_fee=shipping_fee_s,
            delivery_time=delivery_time_s,
            price_calculation_block=price_calculation_block or "",
            catalogue_reference_block=catalogue_reference_block_s,
            total_snapshot_block=total_snapshot_block,
            verdicts_block=verdicts_block,
            validation_errors_block=(
                validation_errors_block.strip()
                if validation_errors_block and validation_errors_block.strip()
                else "    <empty>∅</empty>"
            ),
            instruction_block=(instruction_block.strip() if str(instruction_block or "").strip() else "    <triggered>false</triggered>"),
            vision_block=vision_block,
            catalogue_block=catalogue_block,
            conversation_history=conversation_history_s,
            question=query,
            has_image="OUI" if has_image else "NON",
        )
        
        # Récupérer le prompt statique (Supabase ou fallback)
        static_prompt = await self.get_static_prompt(company_id)

        # Inject PRODUCT_INDEX placeholder (prompt must contain [[PRODUCT_INDEX]] where you want it).
        try:
            idx_block = self._build_product_index_block(catalog_v2)
            if idx_block and "[[PRODUCT_INDEX]]" in str(static_prompt or ""):
                static_prompt = str(static_prompt).replace("[[PRODUCT_INDEX]]", idx_block)
        except Exception:
            pass

        # Inject product-specific context ONLY inside CATALOGUE_START/END at runtime.
        try:
            pc_block = self._build_product_context_block(catalog_v2, active_product_id) if active_product_id else ""

            # Fallback: if stable prod_xxxx doesn't map cleanly to catalog_v2 product_name,
            # retry with the human label (ex: "Couches bebe (0-25kg)") to select the right product.
            if (not str(pc_block or "").strip()) and active_product_label:
                pc_block = self._build_product_context_block(catalog_v2, active_product_label)

            static_prompt = self._inject_between_catalogue_markers(static_prompt, pc_block)
        except Exception:
            pass

        # Injecter les placeholders du prompt statique (Supabase) si présents
        mode = self._infer_mode(query=query, checklist=checklist)
        done, total = checklist.completion()
        completion_rate = f"{done}/{total}"
        compact_context = self._build_compact_context(
            detected_location=detected_location_s,
            shipping_fee=shipping_fee_s,
            delivery_time=delivery_time_s,
            product_context=product_context_s,
            pricing_context=pricing_context_s,
            conversation_history=conversation_history_s,
        )

        static_prompt = self._safe_format(
            static_prompt,
            mode=mode,
            context=compact_context,
            checklist=checklist.to_string(),
            checklist_json=checklist.to_json(),
            expected_deposit=expected_deposit_str,
            company_name=company_name_s,
            company_phone=company_phone_s,
            payment_phone=payment_phone_s,
            payment_methods=payment_methods_s,
            pricing_context=pricing_context_s,
            shipping_fee=shipping_fee_s,
            delivery_time=delivery_time_s,
            delai_message=delai_message_s,
            detected_location=detected_location_s,
            conversation_history=conversation_history_s,
            completion_rate=completion_rate,
        )

        # Règle runtime (appliquée même si le prompt vient de Supabase):
        # quand le client demande un délai, Jessica doit répondre avec {delai_message} (ou fallback si vide)
        # et ne doit pas inventer de dépendance au produit/zone.
        delay_line = delai_message_s if delai_message_s else "Le service client va te préciser le créneau par appel."
        delay_rule_block = (
            "\n\n"
            "RÈGLE (QUESTIONS DÉLAI)\n"
            "Si le client demande un délai (ex: \"délai\", \"livré quand\", \"livraison quand\"), "
            "tu réponds immédiatement avec PLACEORDER (une seule ligne): "
            f"{delay_line} "
            "Interdit de dire que le délai dépend de la zone ou du produit.\n"
        )
        static_prompt = static_prompt + delay_rule_block

        # Injection runtime: bloc Markdown logistique (heure CI + règle avant/après 13h)
        try:
            from core.placeorder_logistique_injector import (
                should_inject_placeorder_logistique,
                build_placeorder_logistique_block,
            )

            if should_inject_placeorder_logistique(query):
                static_prompt = static_prompt + build_placeorder_logistique_block()
        except Exception:
            pass

        try:
            if str(os.getenv("LOG_PLACEORDER_PROMPT", "") or "").strip().lower() in {"1", "true", "yes", "on"}:
                s = str(static_prompt or "")
                idx = s.upper().find("PLACEORDER")
                snippet = ""
                if idx != -1:
                    tail = s[idx:]
                    lines = tail.splitlines()
                    cut = []
                    for i, ln in enumerate(lines[:25]):
                        if i > 0 and (ln.strip().startswith("## ") or ln.strip().startswith("### ")):
                            break
                        cut.append(ln)
                    snippet = "\n".join(cut).strip()
                logger.info(
                    "[PROMPT][PLACEORDER] delai_message=%s\n%s",
                    (delai_message_s if delai_message_s else "∅"),
                    (snippet if snippet else "PLACEORDER_SECTION_NOT_FOUND"),
                )
        except Exception:
            pass
        
        # Forcer un schéma de sortie stable même si le prompt statique (Supabase)
        # n'inclut pas explicitement <thinking>/<response>.
        output_schema = (
            "\n\n"
            "FORMAT DE SORTIE OBLIGATOIRE (XML)\n"
            "Tu dois répondre STRICTEMENT avec ces 2 balises, dans cet ordre, sans texte avant/après:\n"
            "<thinking>...analyse interne + extraction slots...</thinking>\n"
            "<response>...message WhatsApp final...</response>\n"
        )

        items_schema = (
            "\n\n"
            "DANS <thinking>, fournis TOUJOURS <detected_items_json> (JSON strict).\n"
            "Règles: toujours un ARRAY, même si 1 item.\n"
            "Schéma: [{\"product_id\":\"prod_xxxxxxxx\",\"variant\":\"Culotte|Pression|null\",\"spec\":\"T3|null\",\"unit\":\"lot_300|piece|null\",\"qty\":N|null,\"confidence\":0.0-1.0}]\n"
            "- product_id: ID technique (prod_...).\n"
            "- variant: variante si le produit en a, sinon null.\n"
            "- qty: entier obligatoire ou null si ambigu/incompatible.\n"
            "- spec/unit: doivent suivre <catalogue_reference>.\n"
        )

        # Assembler prompt final
        final_prompt = static_prompt + "\n" + dynamic_context + output_schema + items_schema
        
        return final_prompt
    
    def reset_checklist(self, user_id: str, company_id: str):
        """Réinitialise la checklist (après finalisation commande)"""
        key = f"{company_id}:{user_id}"
        if key in self.checklist_states:
            del self.checklist_states[key]


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_simplified_prompt_system: Optional[SimplifiedPromptSystem] = None

def get_simplified_prompt_system() -> SimplifiedPromptSystem:
    """Retourne le singleton du système de prompt simplifié"""
    global _simplified_prompt_system
    if _simplified_prompt_system is None:
        _simplified_prompt_system = SimplifiedPromptSystem()
    return _simplified_prompt_system

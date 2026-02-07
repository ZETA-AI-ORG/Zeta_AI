#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🕐 HELPER TIMEZONE - HEURE CÔTE D'IVOIRE
Fournit l'heure actuelle en Côte d'Ivoire pour calculs de délais
"""

from datetime import datetime
import pytz
import logging

logger = logging.getLogger(__name__)

# Timezone Côte d'Ivoire (GMT+0, pas de DST)
COTE_IVOIRE_TZ = pytz.timezone('Africa/Abidjan')


def get_current_time_ci() -> datetime:
    """
    Retourne l'heure actuelle en Côte d'Ivoire
    
    Returns:
        datetime: Heure actuelle CI avec timezone
    """
    return datetime.now(COTE_IVOIRE_TZ)


def get_formatted_time_ci() -> str:
    """
    Retourne l'heure formatée pour affichage
    
    Returns:
        str: "10h30" ou "14h15"
    """
    now = get_current_time_ci()
    return now.strftime("%Hh%M")


def get_delivery_context_with_time() -> str:
    """
    Génère le contexte de livraison avec heure actuelle
    
    Returns:
        str: Contexte formaté pour le LLM
    """
    now = get_current_time_ci()
    hour = now.hour
    minute = now.minute
    
    # Déterminer si avant ou après 13h (heure limite pour livraison jour même)
    is_before_13h = hour < 13
    
    # Calculer temps restant jusqu'à 13h
    if is_before_13h:
        hours_left = 13 - hour
        minutes_left = 60 - minute
        if minutes_left == 60:
            hours_left += 1
            minutes_left = 0
        time_until_13h = f"{hours_left}h{minutes_left:02d}" if hours_left > 0 else f"{minutes_left}min"
    else:
        time_until_13h = None
    
    # Jour de la semaine
    day_name = now.strftime("%A")
    day_names_fr = {
        "Monday": "lundi",
        "Tuesday": "mardi",
        "Wednesday": "mercredi",
        "Thursday": "jeudi",
        "Friday": "vendredi",
        "Saturday": "samedi",
        "Sunday": "dimanche"
    }
    day_fr = day_names_fr.get(day_name, day_name)
    
    # Date complète
    date_str = now.strftime("%d/%m/%Y")
    
    # Calcul simple du délai
    delai_message = get_delai_message()
    
    # Message simplifié avec heure actuelle
    context = f"""⏰ HEURE CI: Il est {hour:02d}h{minute:02d}. {delai_message}."""
    
    return context


def is_same_day_delivery_possible() -> bool:
    """
    Vérifie si la livraison jour même est encore possible
    
    Returns:
        bool: True si avant 13h, False sinon
    """
    now = get_current_time_ci()
    return now.hour < 13


def get_delai_message() -> str:
    """
    Retourne le message de délai de livraison basé sur l'heure CI.
    
    Règle business:
    - Avant 13h → "Livraison cet après-midi"
    - Après 13h → "Livraison demain entre 11h et 18h"
    
    Returns:
        str: Message de délai prêt à afficher
    """
    if is_same_day_delivery_possible():
        return "Livraison cet après-midi"
    else:
        return "Livraison demain entre 11h et 18h"


def get_estimated_delivery_time() -> str:
    """
    Calcule le délai de livraison estimé
    
    Returns:
        str: "Aujourd'hui" ou "Demain"
    """
    if is_same_day_delivery_possible():
        return "Aujourd'hui (avant 13h)"
    else:
        return "Demain (après 13h)"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🧪 TESTS TIMEZONE CÔTE D'IVOIRE\n")
    
    print("="*80)
    print("📅 HEURE ACTUELLE")
    print("="*80)
    
    now = get_current_time_ci()
    print(f"Heure CI: {now}")
    print(f"Formatée: {get_formatted_time_ci()}")
    print(f"Livraison jour même: {'✅ OUI' if is_same_day_delivery_possible() else '❌ NON'}")
    print(f"Délai estimé: {get_estimated_delivery_time()}")
    
    print("\n" + "="*80)
    print("📋 CONTEXTE POUR LLM")
    print("="*80)
    print(get_delivery_context_with_time())

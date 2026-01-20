#!/usr/bin/env python3
"""
🧪 TEST ORDRE MÉLANGÉ
Vérifie que le LLM gère les étapes dans n'importe quel ordre
"""
import httpx
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8002"
COMPANY_ID = "MpfnlSbqwaZ6F4HvxQLRL9du0yG3"

IMAGE_PRODUIT = "https://scontent.xx.fbcdn.net/v/t1.15752-9/553786504_1339650347521010_7584722332323008254_n.jpg?_nc_cat=108&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=iZMvAIEg5agQ7kNvwGVnL0m&_nc_oc=AdmmEA2PGIddOYXbqVDCtoX-X4unHqUgSUBz44wJJhMV4B_RX4_vz3-hfIf0Gg1DYt44ejVZAGHX_fHccpiQMA8g&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gH1On4PnpZDZQ4CYayHguk94A069j97-Eai6X-5Lw48_Q&oe=6911CDDA"
IMAGE_PAIEMENT = "https://scontent.xx.fbcdn.net/v/t1.15752-9/556908482_1314851517042795_6410429215345539018_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=eb2e90&_nc_ohc=FGYA3tLaNB8Q7kNvwEFLtNy&_nc_oc=AdnhSYhxtPMknvUViCVLIxdq0psdWOZ9d5lLqoGBIzM4BwPMJfxTWbgDf2rraR9cbl-xHoxCoLL8X0Hf8rR18N30&_nc_ad=z-m&_nc_cid=0&_nc_zt=23&_nc_ht=scontent.xx&oh=03_Q7cD3gGKjKR_xt29vtVgdJSUwjCSgV-A-H0IdCphHvF0MvGBow&oe=6911C04A"

def send_message(user_id: str, message: str = "", image_url: str = None):
    """Envoie un message au chatbot"""
    payload = {
        "company_id": COMPANY_ID,
        "user_id": user_id,
        "message": message,
        "botlive_enabled": True
    }
    if image_url:
        payload["images"] = [image_url]
    
    try:
        resp = httpx.post(f"{BASE_URL}/chat", json=payload, timeout=30)
        data = resp.json()
        return data.get('response', '')
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def check_state(user_id: str):
    """Vérifie l'état via check_state.py"""
    import subprocess
    result = subprocess.run(
        ["python3", "check_state.py", user_id],
        capture_output=True,
        text=True
    )
    return result.stdout

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                   🧪 TEST ORDRE MÉLANGÉ                                    ║
║                                                                            ║
║  Vérifie que le LLM gère les étapes dans n'importe quel ordre             ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

# ═══════════════════════════════════════════════════════════════════════════
# TEST 1 : ZONE AVANT PRODUIT (ordre inversé)
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*80)
print("🧪 TEST 1 : Zone AVANT produit (ordre inversé)")
print("="*80)

user_id_1 = f"test_inverse_{datetime.now().strftime('%H%M%S')}"
print(f"👤 user_id: {user_id_1}\n")

print("📍 Étape 1/3 : Envoyer zone AVANT produit")
resp1 = send_message(user_id_1, "Yopougon")
print(f"💬 LLM: {resp1}\n")
time.sleep(2)

print("📍 Étape 2/3 : Envoyer produit")
resp2 = send_message(user_id_1, "", IMAGE_PRODUIT)
print(f"💬 LLM: {resp2}\n")
time.sleep(2)

print("📍 Étape 3/3 : Envoyer paiement")
resp3 = send_message(user_id_1, "", IMAGE_PAIEMENT)
print(f"💬 LLM: {resp3}\n")
time.sleep(2)

print("🔍 État final:")
print(check_state(user_id_1))

# ═══════════════════════════════════════════════════════════════════════════
# TEST 2 : NUMÉRO AVANT TOUT (ordre chaotique)
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*80)
print("🧪 TEST 2 : Numéro AVANT tout (ordre chaotique)")
print("="*80)

user_id_2 = f"test_chaos_{datetime.now().strftime('%H%M%S')}"
print(f"👤 user_id: {user_id_2}\n")

print("📍 Étape 1/4 : Envoyer numéro EN PREMIER")
resp1 = send_message(user_id_2, "0709876543")
print(f"💬 LLM: {resp1}\n")
time.sleep(2)

print("📍 Étape 2/4 : Envoyer paiement")
resp2 = send_message(user_id_2, "", IMAGE_PAIEMENT)
print(f"💬 LLM: {resp2}\n")
time.sleep(2)

print("📍 Étape 3/4 : Envoyer zone")
resp3 = send_message(user_id_2, "Cocody")
print(f"💬 LLM: {resp3}\n")
time.sleep(2)

print("📍 Étape 4/4 : Envoyer produit EN DERNIER")
resp4 = send_message(user_id_2, "", IMAGE_PRODUIT)
print(f"💬 LLM: {resp4}\n")
time.sleep(2)

print("🔍 État final:")
print(check_state(user_id_2))

# ═══════════════════════════════════════════════════════════════════════════
# TEST 3 : TOUT EN UNE FOIS (message + 2 images impossible, mais zone+numéro)
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*80)
print("🧪 TEST 3 : Paiement puis Zone+Numéro en 1 message")
print("="*80)

user_id_3 = f"test_batch_{datetime.now().strftime('%H%M%S')}"
print(f"👤 user_id: {user_id_3}\n")

print("📍 Étape 1/3 : Produit")
resp1 = send_message(user_id_3, "", IMAGE_PRODUIT)
print(f"💬 LLM: {resp1}\n")
time.sleep(2)

print("📍 Étape 2/3 : Paiement")
resp2 = send_message(user_id_3, "", IMAGE_PAIEMENT)
print(f"💬 LLM: {resp2}\n")
time.sleep(2)

print("📍 Étape 3/3 : Zone + Numéro EN MÊME TEMPS")
resp3 = send_message(user_id_3, "Cocody 0512345678")
print(f"💬 LLM: {resp3}\n")
time.sleep(2)

print("🔍 État final:")
print(check_state(user_id_3))

# ═══════════════════════════════════════════════════════════════════════════
# RÉSUMÉ
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*80)
print("📊 RÉSUMÉ DES TESTS")
print("="*80)
print("""
Test 1: Zone → Produit → Paiement (inversé)
Test 2: Numéro → Paiement → Zone → Produit (chaos)
Test 3: Produit → Paiement → Zone+Numéro ensemble (batch)

✅ Si le LLM est intelligent, il devrait :
   - Détecter chaque info peu importe l'ordre
   - Guider vers les infos manquantes
   - Confirmer quand 100% complet
""")

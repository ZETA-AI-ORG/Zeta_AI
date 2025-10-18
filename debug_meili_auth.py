#!/usr/bin/env python3
"""
🔍 DIAGNOSTIC MEILISEARCH - PROBLÈME D'AUTORISATION
Identifie et corrige les problèmes d'authentification MeiliSearch
"""

import requests
import os
import json

def test_meili_connection():
    """Test la connexion et l'authentification MeiliSearch"""
    print("🔍 DIAGNOSTIC MEILISEARCH")
    print("=" * 50)
    
    # Variables d'environnement
    meili_url = os.getenv("MEILISEARCH_URL", "http://localhost:7700")
    meili_key = os.getenv("MEILISEARCH_MASTER_KEY", "")
    
    print(f"🌐 URL: {meili_url}")
    print(f"🔑 Clé définie: {'✅ OUI' if meili_key else '❌ NON'}")
    
    if meili_key:
        print(f"🔑 Clé (8 premiers chars): {meili_key[:8]}...")
    
    # Test 1: Health check (sans auth)
    print("\n🏥 TEST 1: Health Check (sans authentification)")
    try:
        response = requests.get(f"{meili_url}/health", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ MeiliSearch est accessible")
        else:
            print("❌ MeiliSearch non accessible")
            return False
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        return False
    
    # Test 2: Version (sans auth)
    print("\n📋 TEST 2: Version MeiliSearch")
    try:
        response = requests.get(f"{meili_url}/version", timeout=5)
        if response.status_code == 200:
            version_info = response.json()
            print(f"✅ Version: {version_info.get('pkgVersion', 'N/A')}")
        else:
            print(f"❌ Erreur version: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Test 3: Stats (nécessite auth si master key définie)
    print("\n📊 TEST 3: Stats (avec authentification)")
    if not meili_key:
        print("⚠️ Pas de clé master - test ignoré")
        return True
    
    headers = {
        "Authorization": f"Bearer {meili_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{meili_url}/stats", headers=headers, timeout=5)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Authentification réussie")
            stats = response.json()
            print(f"📈 Nombre d'index: {len(stats.get('indexes', {}))}")
            return True
        elif response.status_code == 403:
            print("❌ Erreur 403: Clé invalide ou permissions insuffisantes")
            print(f"📝 Réponse: {response.text}")
            return False
        elif response.status_code == 401:
            print("❌ Erreur 401: Authentification requise")
            print(f"📝 Réponse: {response.text}")
            return False
        else:
            print(f"❌ Erreur inattendue: {response.status_code}")
            print(f"📝 Réponse: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_index_access():
    """Test l'accès à l'index products"""
    print("\n🗂️ TEST 4: Accès index products")
    
    meili_url = os.getenv("MEILISEARCH_URL", "http://localhost:7700")
    meili_key = os.getenv("MEILISEARCH_MASTER_KEY", "")
    company_id = "XkCn8fjNWEWwqiiKMgJX7OcQrUJ3"
    index_name = f"products_{company_id}"
    
    if not meili_key:
        print("⚠️ Pas de clé master - test ignoré")
        return True
    
    headers = {
        "Authorization": f"Bearer {meili_key}",
        "Content-Type": "application/json"
    }
    
    try:
        # Vérifier si l'index existe
        response = requests.get(f"{meili_url}/indexes/{index_name}", headers=headers, timeout=5)
        
        if response.status_code == 200:
            index_info = response.json()
            print(f"✅ Index trouvé: {index_name}")
            print(f"📊 Documents: {index_info.get('numberOfDocuments', 0)}")
            
            # Vérifier les settings
            settings_response = requests.get(f"{meili_url}/indexes/{index_name}/settings", headers=headers, timeout=5)
            if settings_response.status_code == 200:
                settings = settings_response.json()
                searchable = settings.get('searchableAttributes', [])
                print(f"🔍 Attributs recherchables: {len(searchable)}")
                if searchable:
                    print(f"   → {searchable[:3]}...")
                return True
            else:
                print(f"❌ Erreur settings: {settings_response.status_code}")
                return False
                
        elif response.status_code == 404:
            print(f"⚠️ Index non trouvé: {index_name}")
            return True  # Pas grave, on peut le créer
        else:
            print(f"❌ Erreur accès index: {response.status_code}")
            print(f"📝 Réponse: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def suggest_fixes():
    """Suggère des corrections basées sur les tests"""
    print("\n🔧 SUGGESTIONS DE CORRECTION")
    print("=" * 50)
    
    meili_key = os.getenv("MEILISEARCH_MASTER_KEY", "")
    
    if not meili_key:
        print("1. ❌ Définir MEILISEARCH_MASTER_KEY:")
        print("   export MEILISEARCH_MASTER_KEY='votre_cle_master'")
        print("   ou dans le fichier .env")
        return
    
    print("1. ✅ Vérifier que MeiliSearch utilise la même clé master")
    print("2. ✅ Redémarrer MeiliSearch avec la clé:")
    print(f"   ./meilisearch --master-key='{meili_key[:8]}...'")
    print("3. ✅ Vérifier les permissions de la clé")
    print("4. ✅ Tester avec curl:")
    print(f"   curl -H 'Authorization: Bearer {meili_key[:8]}...' {os.getenv('MEILISEARCH_URL', 'http://localhost:7700')}/stats")

if __name__ == "__main__":
    success = test_meili_connection()
    if success:
        test_index_access()
    
    suggest_fixes()
    
    print("\n" + "=" * 50)
    print("🎯 DIAGNOSTIC TERMINÉ")

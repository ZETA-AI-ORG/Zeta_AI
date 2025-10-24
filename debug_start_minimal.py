#!/usr/bin/env python3
"""
🚀 DÉMARRAGE MINIMAL GARANTI
Import seulement app_minimal.py sans aucune dépendance lourde
"""
import sys
import os

print("=" * 80)
print("🚀 MINIMAL START - Mode survie activé")
print("=" * 80)

try:
    print("📦 Importing minimal app...")
    sys.stdout.flush()
    
    import app_minimal
    sys.stdout.flush()
    
    print("✅ Minimal app imported successfully!")
    sys.stdout.flush()
    
    if hasattr(app_minimal, 'app'):
        print("✅ FastAPI app object found!")
        print(f"📊 App type: {type(app_minimal.app)}")
    else:
        print("❌ FastAPI app object NOT found!")
        sys.exit(1)
    
    print("=" * 80)
    print("🚀 Starting uvicorn server (MINIMAL MODE)...")
    print("=" * 80)
    sys.stdout.flush()
    
    import uvicorn
    
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Binding to 0.0.0.0:{port}")
    sys.stdout.flush()
    
    uvicorn.run(
        app_minimal.app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )
    
except Exception as e:
    print("=" * 80)
    print("❌ ERREUR CRITIQUE !")
    print("=" * 80)
    print(f"Type: {type(e).__name__}")
    print(f"Message: {str(e)}")
    print("=" * 80)
    import traceback
    traceback.print_exc()
    print("=" * 80)
    sys.exit(1)

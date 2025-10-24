#!/usr/bin/env python3
"""
Debug wrapper pour identifier les erreurs d'import
"""
import sys
import traceback

print("=" * 80)
print("🔍 DEBUG START - Tentative d'import de app.py")
print("=" * 80)

try:
    print("📦 Importing app module...")
    import app
    print("✅ App module imported successfully!")
    print("=" * 80)
    
    # Vérifier que l'objet app existe
    if hasattr(app, 'app'):
        print("✅ FastAPI app object found!")
        print(f"📊 App type: {type(app.app)}")
    else:
        print("❌ FastAPI app object NOT found in module!")
        sys.exit(1)
    
    print("=" * 80)
    print("🚀 Starting uvicorn server...")
    print("=" * 80)
    
    import os
    import uvicorn
    
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Binding to 0.0.0.0:{port}")
    
    uvicorn.run(
        app.app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )
    
except Exception as e:
    print("=" * 80)
    print("❌ ERREUR CRITIQUE DÉTECTÉE !")
    print("=" * 80)
    print(f"Type d'erreur: {type(e).__name__}")
    print(f"Message: {str(e)}")
    print("=" * 80)
    print("📋 TRACEBACK COMPLET:")
    print("=" * 80)
    traceback.print_exc()
    print("=" * 80)
    sys.exit(1)

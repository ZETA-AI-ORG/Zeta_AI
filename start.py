import os
import sys

if __name__ == "__main__":
    # Debug: afficher toutes les variables d'environnement liées au port
    print(f"🔍 PORT env var: {os.environ.get('PORT', 'NOT SET')}")
    print(f"🔍 All env vars: {[k for k in os.environ.keys() if 'PORT' in k.upper()]}")
    sys.stdout.flush()
    
    # Test import app
    print("🔍 Testing import app...")
    sys.stdout.flush()
    try:
        import app
        print("✅ Import app successful")
        sys.stdout.flush()
    except Exception as e:
        print(f"❌ Error importing app: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Import uvicorn
    print("🔍 Importing uvicorn...")
    sys.stdout.flush()
    import uvicorn
    
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Starting server on host 0.0.0.0 port {port}")
    sys.stdout.flush()
    
    try:
        uvicorn.run(
            app.app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=True
        )
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

import os
import sys
import uvicorn

if __name__ == "__main__":
    # Debug: afficher toutes les variables d'environnement liées au port
    print(f"🔍 PORT env var: {os.environ.get('PORT', 'NOT SET')}")
    print(f"🔍 All env vars: {[k for k in os.environ.keys() if 'PORT' in k.upper()]}")
    
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Starting server on host 0.0.0.0 port {port}")
    sys.stdout.flush()
    
    try:
        uvicorn.run(
            "app:app",
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=True
        )
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

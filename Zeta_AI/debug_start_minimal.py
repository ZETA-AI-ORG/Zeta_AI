#!/usr/bin/env python3
"""
🚀 DÉMARRAGE INTELLIGENT
Essaye d'abord de démarrer l'app complète (app.py).
En cas d'échec, bascule automatiquement sur app_minimal.py.
"""
import sys
import os

print("=" * 80)
print("🚀 START - Mode intelligent (FULL → fallback MINIMAL)")
print("=" * 80)

try:
    import uvicorn

    def _start_uvicorn(app_obj, mode_label: str) -> None:
        """Démarre uvicorn sur le port Render (PORT ou 10000)."""
        port = int(os.environ.get("PORT", 10000))
        print(f"🌐 Binding to 0.0.0.0:{port} [{mode_label}]")
        sys.stdout.flush()
        uvicorn.run(
            app_obj,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=True,
        )

    # Permet de forcer le mode minimal via une variable d'env si besoin
    force_minimal = os.environ.get("ZETA_FORCE_MINIMAL", "false").lower() == "true"

    # --- 1) Tenter d'abord l'app complète (app.py) ---
    if not force_minimal:
        try:
            print("📦 Importing FULL app (app.py)...")
            sys.stdout.flush()
            import app as full_app  # type: ignore

            if not hasattr(full_app, "app"):
                raise RuntimeError("Module 'app' has no 'app' attribute")

            print("✅ Full app imported successfully!")
            print(f"📊 App type: {type(full_app.app)}")
            sys.stdout.flush()

            print("=" * 80)
            print("🚀 Starting uvicorn server (FULL MODE)...")
            print("=" * 80)
            _start_uvicorn(full_app.app, "FULL")
            sys.exit(0)

        except Exception as full_e:
            print("=" * 80)
            print("⚠️ FULL MODE FAILED, fallback to MINIMAL MODE")
            print(f"Type: {type(full_e).__name__}")
            print(f"Message: {full_e}")
            print("=" * 80)
            sys.stdout.flush()

    # --- 2) Fallback: app_minimal.py ---
    print("📦 Importing minimal app (app_minimal.py)...")
    sys.stdout.flush()

    import app_minimal  # type: ignore
    sys.stdout.flush()

    print("✅ Minimal app imported successfully!")
    sys.stdout.flush()

    if hasattr(app_minimal, "app"):
        print("✅ FastAPI app object found!")
        print(f"📊 App type: {type(app_minimal.app)}")
    else:
        print("❌ FastAPI app object NOT found!")
        sys.exit(1)

    print("=" * 80)
    print("🚀 Starting uvicorn server (MINIMAL MODE)...")
    print("=" * 80)
    sys.stdout.flush()

    _start_uvicorn(app_minimal.app, "MINIMAL")

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

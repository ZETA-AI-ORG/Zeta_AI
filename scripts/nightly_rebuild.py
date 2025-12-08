import os
import sys
import subprocess
from pathlib import Path

import time

ROOT = Path(__file__).resolve().parents[1]


def run_step(cmd, name: str) -> bool:
    print(f"\n=== STEP {name} ===")
    try:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())
        if result.returncode != 0:
            print(f"[WARN] Step {name} exited with code {result.returncode}")
            return False
        return True
    except Exception as e:
        print(f"[ERROR] Step {name} failed: {e}")
        return False


def call_reload_endpoint() -> bool:
    url = os.getenv("ROUTER_RELOAD_URL", "http://localhost:8000/admin/reload-router")
    timeout_sec = int(os.getenv("RELOAD_TIMEOUT_SEC", "180"))
    print(f"\n=== STEP reload-router ({url}) ===")
    try:
        import requests

        resp = requests.post(url, timeout=timeout_sec)
        print(f"Status: {resp.status_code}")
        try:
            print(resp.json())
        except Exception:
            print(resp.text)
        return resp.ok
    except Exception as e:
        print(f"[ERROR] Reload endpoint failed: {e}")
        return False


def main() -> None:
    python_exe = sys.executable or "python"

    # 1) Clustering Shadow (optionnel, ignore errors)
    run_step([python_exe, "scripts/cluster_shadow.py"], "cluster_shadow")

    # 2) Rebuild shadow augment (uses env for thresholds/window)
    run_step([python_exe, "scripts/build_shadow_augment.py"], "build_shadow_augment")

    # 3) Extract per-intent keywords (Shadow)
    run_step([python_exe, "scripts/extract_intent_keywords.py"], "extract_intent_keywords")

    # 4) Build universal (cross-company) keywords
    run_step([python_exe, "scripts/build_universal_keywords.py"], "build_universal_keywords")

    # 5) Compute routing health (simple coverage metrics)
    run_step([python_exe, "scripts/compute_routing_health.py"], "compute_routing_health")

    # 6) Reload CentroidRouter at runtime
    call_reload_endpoint()


if __name__ == "__main__":
    main()

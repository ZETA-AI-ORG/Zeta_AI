"""
🔄 sync_prompt_bots.py — Synchronise les fichiers .md locaux vers Supabase `prompt_bots`.

Usage :
    # Sync tous les bots configurés (amanda, jessica si disponible)
    python scripts/sync_prompt_bots.py

    # Sync uniquement amanda
    python scripts/sync_prompt_bots.py --bot amanda

    # Dry-run (affiche ce qui serait fait, sans écrire)
    python scripts/sync_prompt_bots.py --dry-run

    # Spécifier une version
    python scripts/sync_prompt_bots.py --bot amanda --version 1.1

Après sync, le cache Redis est automatiquement invalidé → les prochains
appels Amanda relisent Supabase.
"""
import argparse
import sys
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from core.prompt_bots_loader import upload_prompt_to_supabase  # noqa: E402

# ───────────────────────────────────────────────────────────────────────
# Mapping bot_type → fichier source
# ───────────────────────────────────────────────────────────────────────
BOT_FILES = {
    "amanda": _ROOT / "AMANDA PROMPT UNIVERSEL.md",
    # "jessica": _ROOT / "prompt_universel_v2.md",  # à décommenter quand migré
}


def sync_one(bot_type: str, version: str, dry_run: bool) -> bool:
    path = BOT_FILES.get(bot_type)
    if not path:
        print(f"❌ Bot inconnu: {bot_type} (disponibles: {list(BOT_FILES.keys())})")
        return False
    if not path.exists():
        print(f"❌ Fichier introuvable: {path}")
        return False

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        print(f"❌ Fichier vide: {path}")
        return False

    print(f"📄 {bot_type}: {path.name} → {len(content)} chars (version {version})")

    if dry_run:
        print(f"   [dry-run] Upload Supabase ignoré")
        return True

    ok = upload_prompt_to_supabase(
        bot_type=bot_type,
        prompt_content=content,
        version=version,
        is_active=True,
    )
    if ok:
        print(f"   ✅ Upload Supabase OK + cache Redis invalidé")
    else:
        print(f"   ❌ Upload Supabase ÉCHEC (voir logs)")
    return ok


def main():
    parser = argparse.ArgumentParser(description="Sync prompt bots → Supabase")
    parser.add_argument("--bot", choices=list(BOT_FILES.keys()), help="Un seul bot (par défaut: tous)")
    parser.add_argument("--version", default="1.0", help="Version sémantique (défaut: 1.0)")
    parser.add_argument("--dry-run", action="store_true", help="N'écrit rien, affiche seulement")
    args = parser.parse_args()

    bots = [args.bot] if args.bot else list(BOT_FILES.keys())

    print("━" * 72)
    print(f"🔄 SYNC PROMPT BOTS → Supabase `prompt_bots`")
    print(f"   Bots: {bots} | Version: {args.version} | Dry-run: {args.dry_run}")
    print("━" * 72)

    results = {}
    for bot in bots:
        results[bot] = sync_one(bot, args.version, args.dry_run)

    print("━" * 72)
    success = sum(1 for v in results.values() if v)
    print(f"📊 Résultat: {success}/{len(results)} synchronisé(s)")
    print("━" * 72)

    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()

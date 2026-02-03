# cache_utils.py
from __future__ import annotations
from pathlib import Path
import shutil
import logging
from joblib import Memory

# --- Logging court ---
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("cache_utils")

# --- Emplacements ---
BASE_DIR  = Path(__file__).resolve().parent
CACHE_DIR = (BASE_DIR / "cache").resolve()
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Instance partagée si tu importes memory ailleurs
memory = Memory(location=str(CACHE_DIR), verbose=0)

# TTL utilisé par l’app si besoin
TIMEOUT = 60 * 10  # 10 minutes

def _rm(path: Path) -> None:
    """Supprime dossier/fichier sans broncher."""
    try:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
    except Exception as e:
        log.warning(f"Impossible de supprimer {path}: {e}")

def clean_joblib_cache(keep_dotfiles: bool = True) -> None:
    """
    Vide TOUT le cache persistant Joblib sous cache/ (y compris cache/joblib/**).
    Ne supprime rien à l'import; à appeler ou exécuter en script.
    """
    log.info(f"Nettoyage du cache: {CACHE_DIR}")

    # 1) nettoyer les index joblib (au cas où)
    try:
        memory.clear(warn=False)
    except Exception as e:
        log.warning(f"memory.clear() a échoué: {e}")

    # 2) purger le contenu de cache/
    if CACHE_DIR.exists():
        for child in CACHE_DIR.iterdir():
            if keep_dotfiles and child.name.startswith("."):
                continue  # ex: .gitignore
            _rm(child)

    # 3) recréer le dossier au besoin
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Cache vidé.")

if __name__ == "__main__":
    # Lancer:  python cache_utils.py
    clean_joblib_cache()

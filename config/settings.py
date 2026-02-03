# config/setting.py
from __future__ import annotations

# ─────────────────────────── Données / Fichiers ───────────────────────────
# Motif des fichiers de collaborateurs à charger
FILE_PATTERN: str = "data/data*.xlsx"

# Nom de la feuille Excel à lire
SHEET_NAME: str = "COMPILE"

# ─────────────────────────── UI / Thème / CSS ─────────────────────────────
# Feuilles de style pour les thèmes clair/sombre
LIGHT_CSS: str = "/assets/day.css"
DARK_CSS:  str = "/assets/night.css"

# Configuration générique des graphiques Plotly (transmise à dcc.Graph)
GRAPH_CONFIG: dict = {"responsive": True}

# Seuil au-delà duquel on bascule Slider → Dropdown pour les périodes
THRESHOLD_FILES_FOR_DD: int = 6

# Nombre max de KPI affichables (sélections basiques)
MAX_BASIC_KPIS: int = 4

# Nombre max de KPI “delta” affichables
MAX_DELTA_KPIS: int = 4

# Nombre max de filtres additionnels dans l’onglet “Analyse complexe”
MAX_ADDITIONAL_FILTERS: int = 5

# ─────────────────────────── Dates / Formats ──────────────────────────────
# Regex pour extraire une date AAAAMMJJ d’un nom de fichier
DATE_REGEX: str = r"(\d{8})"

# Noms de mois en français (pour titres et labels)
MONTH_FR: list[str] = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

# ─────────────────────────── Application ──────────────────────────────────
# Port et mode debug (utilisés dans app.py)
DEFAULT_PORT: int = 8050
DEBUG: bool = True

# ─────────────────────────── Divers ───────────────────────────────────────
# Séparateur d’affichage (espace fine insécable pour milliers)
NARROW_NBSP: str = "\u202f"

# Texte par défaut pour les placeholders Dropdown
DROPDOWN_PLACEHOLDER: str = "Choisissez…"

# Message générique lorsqu’aucune donnée n’est disponible
NO_DATA_MSG: str = "Aucune donnée disponible pour ces filtres."
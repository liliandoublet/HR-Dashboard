# app.py
from __future__ import annotations

import os
import sys
import logging

import dash
from dash import Dash

# ───────────────────────────── Bootstrap logging ─────────────────────────────
LOGLEVEL = os.getenv("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=LOGLEVEL)
log = logging.getLogger("app")

# ───────────────────────────── Assurer le PYTHONPATH ─────────────────────────
# Permet: from config..., from services..., from ui..., from callbacks...
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ───────────────────────────── Services / Thèmes ─────────────────────────────
from services.data_manager import data_manager
import services.template_services as template_service  # enregistre les templates

# Appel optionnel si tu exposes une fonction explicite d'enregistrement
if hasattr(template_service, "register_templates"):
    template_service.register_templates()

# ───────────────────────────── UI (layout) ─────────────────────────────
from ui.layout import create_layout

# ───────────────────────────── Callbacks ─────────────────────────────
# Tous ces modules doivent exposer une fonction: register_callbacks(app)
from callbacks import (
    theme,
    sidebar,
    options,
    kpis as cb_kpis,
    global_tab,
    simple_tab,
    viz_tab,
    time_tab,
)


def create_app() -> Dash:
    """
    Fabrique et configure l'application Dash:
      1) initialise les données (DataManager)
      2) crée l'app Dash
      3) monte le layout
      4) enregistre tous les callbacks
    """
    # 1) Données
    data_manager.initialize()
    if os.getenv("PRELOAD_CACHE", "0").lower() in {"1", "true", "yes"}:
        log.info("Préchargement de tous les fichiers (cache joblib)…")
        data_manager.preload_all()

    # 2) App Dash
    app = Dash(
        __name__,
        assets_folder=os.path.join(PROJECT_ROOT, "ui", "assets"),
        assets_url_path="/assets",
        suppress_callback_exceptions=True,
        title="Dashboard Effectifs France",
    )

    # 3) Layout
    app.layout = create_layout()

    # 4) Callbacks (tous les modules doivent avoir register_callbacks(app))
    for mod in (theme, sidebar, options, cb_kpis, global_tab, simple_tab, viz_tab, time_tab):
        if hasattr(mod, "register_callbacks"):
            mod.register_callbacks(app)
        else:
            log.warning("Le module %s n'expose pas register_callbacks(app)", mod.__name__)

    return app


app = create_app()
# Expose l'objet WSGI pour gunicorn: `gunicorn app:server`
server = app.server

if __name__ == "__main__":
    debug = os.getenv("DEBUG", "1").lower() in {"1", "true", "yes"}
    port = int(os.getenv("PORT", "8050"))
    host = os.getenv("HOST", "0.0.0.0")
    app.run(debug=debug, host=host, port=port)

# callbacks/theme.py
from __future__ import annotations

from dash import Input, Output, State
from dash.exceptions import PreventUpdate

from services.data_manager import data_manager
from config.settings import LIGHT_CSS, DARK_CSS, THRESHOLD_FILES_FOR_DD


def register_callbacks(app):
    """
    Callbacks 'thème' et visibilités globales :
      • switch_theme : bascule jour/nuit (CSS + store 'theme')
      • toggle_kpi_blocks : montre/cache kpi-wrap vs time-kpi-wrap selon l’onglet
      • show_time_kpis_only_on_cmp : affiche la barre période + picker KPI sur l’onglet 'cmp'
      • toggle_basic_kpi_picker : montre le picker KPI de base sur onglets 1–3
      • cap_basic_kpis : limite la sélection KPI de base à 4 éléments
    """

    # ───────────────────────── Thème jour/nuit ─────────────────────────
    @app.callback(
        Output("theme-css", "href"),
        Output("theme-toggle", "className"),
        Output("theme", "data"),
        Input("theme-toggle", "n_clicks"),
        State("theme-css", "href"),
        prevent_initial_call=True,
    )
    def switch_theme(n, current_href):
        if not current_href:
            raise PreventUpdate
        if current_href.endswith("night.css"):
            return LIGHT_CSS, "theme-btn dark", "light"
        return DARK_CSS, "theme-btn", "dark"

    # ───────────────────────── Visibilité KPI principaux/temps ─────────────────────────
    @app.callback(
        Output("kpi-wrap", "className"),
        Output("time-kpi-wrap", "className"),
        Input("tabs", "value"),
    )
    def toggle_kpi_blocks(tab):
        # Onglet 'cmp' (évolution) : on montre les KPI temporels à droite
        if tab == "cmp":
            return "kpi-wrap hidden", "kpi-wrap"
        # Autres onglets : KPI de base visibles
        return "kpi-wrap", "kpi-wrap hidden"

    # ───────────────────────── Période + Picker KPI temporels ─────────────────────────
    @app.callback(
        Output("kpi-picker", "className"),
        Input("tabs", "value"),
    )
    def show_time_kpis_only_on_cmp(tab):
        on_cmp = (tab == "cmp") 
        return "kpi-picker-block" + ("" if on_cmp else " hidden")

    # ───────────────────────── Picker KPI de base (onglets 1–3) ─────────────────────────
    @app.callback(
        Output("basic-kpi-picker", "className"),
        Input("tabs", "value"),
    )
    def toggle_basic_kpi_picker(tab):
        show = tab in {"global", "simp", "viz"}
        return f"kpi-picker-block{'' if show else ' hidden'}"

    # ───────────────────────── Cap sélection KPI de base à 4 ─────────────────────────
    @app.callback(
        Output("basic-kpi-choices", "value"),
        Input("basic-kpi-choices", "value"),
        prevent_initial_call=True,
    )
    def cap_basic_kpis(selected):
        selected = selected or []
        return selected[:4]

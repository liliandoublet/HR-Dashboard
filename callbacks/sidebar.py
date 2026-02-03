# callbacks/sidebar.py
from __future__ import annotations

from dash import Input, Output, State, html, dcc, ctx, no_update
from dash.exceptions import PreventUpdate

from services.data_manager import data_manager
from config.settings import (
    LIGHT_CSS,
    DARK_CSS,
    THRESHOLD_FILES_FOR_DD,
    MAX_ADDITIONAL_FILTERS as MAX_EXTRA,
    MAX_BASIC_KPIS,
)


def register_callbacks(app):

    # ───────────────────────── Visibilité des blocs par onglet ─────────────
    @app.callback(
        Output("global-sec", "className"),
        Output("simp-sec", "className"),
        Output("viz-sec", "className"),
        Output("time-sec", "className"),
        Input("tabs", "value"),
    )
    def sec_visibility(tab):
        return (
            "" if tab == "global" else "hidden",
            "" if tab == "simp" else "hidden",
            "" if tab == "viz" else "hidden",
            "" if tab == "cmp" else "hidden",
        )

    # ───────────────────────── Sidebars gauche/droite exclusives ───────────
    @app.callback(
        Output("sidebar", "className"),
        Output("sidebar-right", "className"),
        Output("right-sb-toggle", "className"),
        Input("toggle-btn", "n_clicks"),
        Input("right-sb-toggle", "n_clicks"),
        State("sidebar", "className"),
        State("sidebar-right", "className"),
        prevent_initial_call=True,
    )
    def exclusive_sidebar(n_left, n_right, cls_left, cls_right):
        trig = ctx.triggered_id
        cls_left = (cls_left or "sidebar").strip()
        cls_right = (cls_right or "sidebar-right").strip()

        # Par défaut : tout fermé
        new_left = "sidebar"
        new_right = "sidebar-right"
        btn_cls = "sidebar-right-toggle-btn"

        if trig == "toggle-btn":
            will_open_left = "open" not in cls_left
            new_left = "sidebar open" if will_open_left else "sidebar"

        elif trig == "right-sb-toggle":
            will_open_right = "open" not in cls_right
            new_right = "sidebar-right open" if will_open_right else "sidebar-right"
            btn_cls += " is-active" if will_open_right else ""

        return new_left, new_right, btn_cls

    # ───────────────────────── Mode comparaison (onglet Viz) ───────────────
    @app.callback(
        Output("viz-cmp-pole-sec", "className"),
        Output("viz-cmp-ent-sec", "className"),
        Input("viz-compare-mode", "value"),
    )
    def _toggle_cmp_viz(mode):
        cms = "" if ("ON" in (mode or [])) else "hidden"
        return cms, cms

    # Afficher le checkbox “multi camemberts” seulement si Pie + comparaison
    @app.callback(
        Output("viz-multi-pie-sec", "className"),
        Input("viz-type", "value"),
        Input("viz-compare-mode", "value"),
    )
    def toggle_multi_pie_checkbox(gtype, cmp_mode):
        return "" if (gtype == "pie" and "ON" in (cmp_mode or [])) else "hidden"

    # Désactiver Treemap quand la combinaison 1×2 est cochée (onglet Viz)
    @app.callback(
        Output("viz-type", "options"),
        Input("viz-combine-12", "value"),
    )
    def disable_treemap_when_combine(combine12):
        opts = [
            {"label": "Histogramme", "value": "bar"},
            {"label": "Camembert", "value": "pie"},
            {"label": "Treemap", "value": "treemap"},
        ]
        if "ON" in (combine12 or []):
            for o in opts:
                if o["value"] == "treemap":
                    o["disabled"] = True
        return opts

    # ───────────────────────── Ajout dynamique de filtres (Viz) ────────────
    @app.callback(
        Output("additional-filters", "children"),
        Input("add-filter-btn", "n_clicks"),
        State("additional-filters", "children"),
        prevent_initial_call=True,
    )
    def add_filter(n_clicks, children):
        children = children or []
        if n_clicks is None or len(children) >= MAX_EXTRA:
            raise PreventUpdate

        # idx courant = 3 + nb de filtres déjà présents
        idx = 3 + len(children)

        # NB: on laisse 'options=[]' – elles seront alimentées par
        #     callbacks/options.py (disable_chosen_cols et update_value_dd).
        new_block = html.Div(
            className="filter-block",
            children=[
                html.Label(f"Filtre {idx}", className="label-title"),

                dcc.Dropdown(
                    id={"t": "viz-col", "idx": idx},
                    options=[],
                    placeholder="Choisissez une catégorie",
                    clearable=True,
                    className="filter-dropdown",
                    optionHeight=40,
                    maxHeight=400,
                ),
                dcc.Dropdown(
                    id={"t": "viz-val", "idx": idx},
                    options=[],
                    value=[],
                    multi=True,
                    placeholder="(Choisissez une ou plusieurs valeurs)",
                    className="dropdown sub-dd",
                    optionHeight=40,
                    maxHeight=400,
                ),
            ],
        )
        return children + [new_block]

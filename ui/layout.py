# ui/layout.py
from __future__ import annotations

import os
import re
import datetime as dt
from typing import Optional, List, Dict

import numpy as np
from dash import html, dcc

from config.settings import DARK_CSS
from services.data_manager import data_manager, get_df
from ui.components.filters import (
    dropdown, radio_items, checklist, range_slider,
    tri_block, value_block, simple_pair_filters,
    scatter_options_block, combine_switch, two_dropdowns_group,
)


# ───────────────────────────── Helpers locaux ─────────────────────────────

DATE_PAT = re.compile(r"(\d{8})")
MONTH_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

def file_to_label(path: str) -> str:
    """Transforme …_AAAAMMJJ.xlsx en 'JJ mois AAAA' sinon renvoie le nom."""
    fname = os.path.basename(path)
    m = DATE_PAT.search(fname)
    if not m:
        return fname
    d = dt.datetime.strptime(m.group(1), "%Y%m%d").date()
    return f"{d.day:02d} {MONTH_FR[d.month-1]} {d.year}"

def default_file_value(file_list: List[str]) -> Optional[str]:
    return file_list[0] if file_list else None

def pole_options_from_default_df() -> List[Dict]:
    """Construit les options du dropdown Pôle à partir du fichier par défaut."""
    try:
        df = data_manager.get_default_data()
        values = list(df["CAT1"].dropna().astype(str).unique())
        values.sort()
        return [{"label": "Tout", "value": "Tout"}] + [{"label": v, "value": v} for v in values]
    except Exception:
        # fallback minimal si pas de données
        return [{"label": "Tout", "value": "Tout"}]


# ───────────────────────────── Layout principal ─────────────────────────────

def create_layout() -> html.Div:
    """
    Construit le layout complet du dashboard (barre latérale, onglets, KPI).
    Les callbacks sont gérés séparément dans callbacks/*.py
    """
    # S'assurer que le DataManager est prêt (liste fichiers, df par défaut)
    data_manager.initialize()

    file_list = data_manager.get_file_list()
    file_opts = [{"label": file_to_label(fp), "value": fp} for fp in file_list]
    file_val = default_file_value(file_list)

    # Options pôle/entité (entité sera re-rempli par callback)
    pole_opts = pole_options_from_default_df()
    entite_opts = [{"label": "Tout", "value": "Tout"}]

    # Dropdowns de catégories (remplis par les callbacks côté options.py/viz/simple si besoin)
    # Ici, on met juste des containers avec IDs attendus.

    # ───────────────────── Right sidebar (KPI temporels) ─────────────────────
    right_sidebar = html.Div(
        id="sidebar-right",
        className="sidebar-right",
        children=[
            # Barre période (slider) – affichée uniquement onglet Evolution si nb fichiers <= seuil
            html.Div(
                id="period-bar",
                className="period-bar hidden",
                children=[
                    html.Label("Période de comparaison", className="label-title"),
                    dcc.RangeSlider(
                        id="delta-range",
                        min=0,
                        max=max(0, len(file_list) - 1),
                        step=1,
                        value=[max(0, len(file_list) - 2), max(0, len(file_list) - 1)],
                        allowCross=False,
                        marks={i: "" for i in range(len(file_list))},  # marks mis à jour par callbacks/time_tab
                        tooltip={"placement": "bottom"},
                    ),
                ],
            ),

            html.Div(
                id="delta-group",
                className="filter-block hidden",
                children=[
                    html.Div(
                        id="delta-dd-wrap",
                        className="hidden",
                        children=[
                            two_dropdowns_group(
                                title="Période de comparaison",
                                start_id="delta-start-dd",
                                end_id="delta-end-dd",
                                class_name_wrap="",  # on laisse le callback gérer via delta-group / delta-dd-wrap
                            )
                        ],
                    )
                ],
            ),
            # Choix des KPI temporels
            html.Div(
                id="kpi-picker",
                className="kpi-picker-block hidden",
                children=[
                    html.Label("KPI temporels (4 maximum)", className="label-title"),
                    dcc.Checklist(
                        id="kpi-choices",
                        value=["Δ_effectif_%", "Δ_parité_F_%", "Δ_age_moyen_%", "Δ_alternants_%"],
                        options=[
                            {"label": "Différence des effectifs (%)", "value": "Δ_effectif_%"},
                            {"label": "Différence paritée femmes (%)", "value": "Δ_parité_F_%"},
                            {"label": "Différence d'âge moyen (%)", "value": "Δ_age_moyen_%"},
                            {"label": "Différence d'alternants (%)", "value": "Δ_alternants_%"},
                            {"label": "Différence de proches de la retraite (%)", "value": "Δ_proches_retraite_%"},
                        ],
                        className="kpi-checklist",
                        inputStyle={"margin-right": "6px"},
                        labelStyle={"display": "block", "margin-bottom": ".3rem"},
                    ),
                    html.Small("(cochez / décochez ; 4 sélectionnés minimum-maximum)", className="text-sub"),
                ],
            ),

            # Choix des KPI de base (affiché onglets 1–3)
            html.Div(
                id="basic-kpi-picker",
                className="kpi-picker-block hidden",
                children=[
                    html.Label("Choix des KPI (4 maximum)", className="label-title"),
                    dcc.Checklist(
                        id="basic-kpi-choices",
                        value=["age", "anciennete", "pct_femmes", "stag_alt"],
                        options=[
                            {"label": "Âge (moyenne/médiane)", "value": "age"},
                            {"label": "Ancienneté (moyenne/médiane)", "value": "anciennete"},
                            {"label": "Pourcentage de (femmes/hommes)", "value": "pct_femmes"},
                            {"label": "Nombre d'alternants", "value": "stag_alt"},
                            {"label": "Pourcentage (temps partiel/temps plein)", "value": "pct_part_time"},
                            {"label": "Pourcentage de cadres", "value": "pct_cadres"},
                            {"label": "Pourcentage de cadre (femmes/hommes)", "value": "pct_cadres_f"},
                            {"label": "Nombre de collaborateurs de plus de 60 ans", "value": "near_retire"},
                        ],
                        className="kpi-checklist",
                        inputStyle={"margin-right": "6px"},
                        labelStyle={"display": "block", "margin-bottom": ".3rem"},
                    ),
                    html.Small("(cochez / décochez ; 4 maximum)", className="text-sub"),
                ],
            ),
        ],
    )

    # ───────────────────── Left sidebar (filtres) ─────────────────────
    left_sidebar = html.Div(
        id="sidebar",
        className="sidebar",
        children=[
            html.Label("Choix du mois à analyser", className="filter-title"),
            dcc.Dropdown(
                id="file-dd",
                value=file_val,
                options=file_opts,
                multi=False,
                clearable=False,
                className="radio-group",
                optionHeight=40,
                maxHeight=400,
            ),

            html.Div(
                className="filter-block",
                children=[
                    html.Label("Pôle", className="filter-title"),
                    dcc.Dropdown(
                        id="pole-dd",
                        value="Tout",
                        options=pole_opts,
                        className="neo-dd",
                        optionHeight=50,
                        maxHeight=400,
                    ),
                    html.Label("Entité", className="filter-title", style={"marginTop": ".8rem"}),
                    dcc.Dropdown(
                        id="entite-dd",
                        value="Tout",
                        options=entite_opts,  # sera mis à jour par callback
                        className="neo-dd",
                        optionHeight=50,
                        maxHeight=400,
                    ),
                ],
            ),
            html.Hr(),

            # ─── Vision globale (onglet 1) : contrôles
            html.Div(
                id="global-sec",
                children=[
                    html.H3("Choix des filtres"),
                    html.Label("Filtre", className="label-title"),
                    dcc.Dropdown(
                        id="global-data-dd",
                        value="",
                        clearable=False,
                        className="radio-group",
                        placeholder="(Aucun filtre)",
                        options=[{"label": "-- Aucun filtre --", "value": ""}],
                        style={"color": "#111", "backgroundColor": "#f9f9f9"},
                        optionHeight=40,
                        maxHeight=400,
                    ),
                    tri_block("glob-"),
                    value_block("global-", default="count", flat=True),
                    html.Label("Choisissez Le Type De Graphique", className="label-title"),
                    dcc.Dropdown(
                        id="global-graph-type",
                        value="bar",
                        className="radio-group radio-group--flat",
                        options=[{"label": "Histogramme", "value": "bar"},
                                 {"label": "Camembert", "value": "pie"}],
                        optionHeight=40,
                        maxHeight=400,
                    ),
                ],
            ),

            # ─── Visualisation simple (onglet 2)
            html.Div(
                id="simp-sec",
                children=[
                    html.H3("Choix des filtres"),
                    html.Label("Type de graphique", className="label-title"),
                    dcc.Dropdown(
                        id="simp-type",
                        value="bar",
                        className="radio-group radio-group--flat",
                        options=[
                            {"label": "Histogramme", "value": "bar"},
                            {"label": "Camembert", "value": "pie"},
                            {"label": "Treemap", "value": "treemap"},
                            {"label": "Nuage de points", "value": "scatter"},
                            {"label": "Graphique en bulle", "value": "bubble"},
                        ],
                        optionHeight=40,
                        maxHeight=400,
                    ),
                    # Couple de filtres (sera masqué quand scatter/bubble)
                    html.Div(
                        children=[
                            html.Div(
                                id="simp-f1-wrap",
                                className="",
                                children=[
                                    html.Label("Filtre n°1", className="label-title"),
                                    dcc.Dropdown(
                                        id="simp-col1",
                                        options=[],
                                        value=[],
                                        clearable=True,
                                        placeholder="Choisissez une 1ʳᵉ catégorie",
                                        className="radio-group",
                                        optionHeight=40,
                                        maxHeight=400,
                                    )
                                ],
                            ),
                            html.Div(
                                id="simp-f2-wrap",
                                className="",
                                children=[
                                    html.Label("Filtre n°2", className="label-title"),
                                    dcc.Dropdown(
                                        id="simp-col2",
                                        options=[],
                                        value=[],
                                        clearable=True,
                                        placeholder="Choisissez une 2ᵉ catégorie",
                                        className="radio-group",
                                        optionHeight=40,
                                        maxHeight=400,
                                    ),
                                ],
                            ),
                            combine_switch("simp-combine", "Fusionner en un seul graphique"),
                        ],
                        className="",
                    ),
                    scatter_options_block(),  # X/Y/Size pour scatter/bubble
                    html.Label("", className="label-title"),
                    tri_block("simp-"),
                    value_block("simp-", default="count", flat=True),
                ],
            ),

            # ─── Analyse complexe (onglet 3)
            html.Div(
                id="viz-sec",
                children=[
                    # Sélecteurs comparants (affichés seulement en mode comparaison)
                    html.Div(
                        id="viz-cmp-pole-sec",
                        className="filter-block hidden",
                        children=[
                            html.Label("Pôle (comparant)", className="label-title"),
                            dcc.Dropdown(
                                id="viz-cmp-pole-dd",
                                value="Tout",
                                options=pole_opts,
                                className="filter-dropdown",
                                optionHeight=50,
                                maxHeight=400,
                            ),
                        ],
                    ),
                    html.Div(
                        id="viz-cmp-ent-sec",
                        className="filter-dropdown hidden",
                        children=[
                            html.Label("Entité (comparant)", className="label-title"),
                            dcc.Dropdown(
                                id="viz-cmp-ent-dd",
                                value="Tout",
                                options=entite_opts,
                                className="filter-dropdown",
                                optionHeight=50,
                                maxHeight=400,
                            ),
                        ],
                    ),
                    dcc.Checklist(
                        id="viz-compare-mode",
                        options=[{"label": "Mode comparaison", "value": "ON"}],
                        value=[],
                        className="switch-item",
                        style={"margin": "8px 0"},
                    ),
                    html.H3("Choix des filtres"),
                    # Filtre 1
                    html.Div(
                        className="filter-block",
                        children=[
                            html.Label("Filtre n°1", className="label-title"),
                            dcc.Dropdown(
                                id={"t": "viz-col", "idx": 1},
                                options=[],
                                placeholder="Choisissez une catégorie",
                                clearable=True,
                                className="filter-dropdown",
                                optionHeight=40,
                                maxHeight=400,
                            ),
                            dcc.Dropdown(
                                id={"t": "viz-val", "idx": 1},
                                options=[],
                                value=[],
                                multi=True,
                                placeholder="(Choisissez une ou plusieurs valeurs)",
                                className="dropdown sub-dd",
                                optionHeight=40,
                                maxHeight=400,
                            ),
                        ],
                    ),
                    # Filtre 2
                    html.Div(
                        className="filter-block",
                        children=[
                            html.Label("Filtre n°2", className="label-title"),
                            dcc.Dropdown(
                                id={"t": "viz-col", "idx": 2},
                                options=[],
                                placeholder="Choisissez une catégorie",
                                clearable=True,
                                className="filter-dropdown",
                                optionHeight=40,
                                maxHeight=400,
                            ),
                            dcc.Dropdown(
                                id={"t": "viz-val", "idx": 2},
                                options=[],
                                value=[],
                                multi=True,
                                placeholder="(Choisissez une ou plusieurs valeurs)",
                                className="dropdown sub-dd",
                                optionHeight=40,
                                maxHeight=400,
                            ),
                        ],
                    ),
                    # Switch combiner 1 x 2
                    html.Div(
                        className="filter-block",
                        style={"margin": "8px 0"},
                        children=[
                            dcc.Checklist(
                                id="viz-combine-12",
                                options=[{"label": "Passer en graphique combiné ", "value": "ON"}],
                                value=[],
                                className="switch-item",
                            ),
                        ],
                    ),
                    # Conteneur des filtres additionnels (3..7)
                    html.Div(id="additional-filters"),

                    html.Label("Valeurs", className="label-title"),
                    dcc.RadioItems(
                        id="viz-value-mode",
                        value="count",
                        className="radio-group radio-group--flat",
                        options=[
                            {"label": "Nombre", "value": "count"},
                            {"label": "% périmètre", "value": "pct_scope"},
                            {"label": "% total", "value": "pct_total"},
                        ],
                        labelStyle={"display": "block"},
                    ),
                    html.Hr(style={"margin": "8px 0"}),
                    html.Label("Tri graphiques", className="label-title"),
                    tri_block("viz-"),
                    html.Hr(style={"margin": "8px 0"}),
                    html.Label("Type de graphique", className="label-title", style={"marginTop": "12px"}),
                    dcc.Dropdown(
                        id="viz-type",
                        value="bar",
                        className="radio-group radio-group--flat",
                        options=[
                            {"label": "Histogramme", "value": "bar"},
                            {"label": "Camembert", "value": "pie"},
                            {"label": "Treemap", "value": "treemap"},
                        ],
                        optionHeight=40,
                        maxHeight=400,
                    ),
                    html.Hr(style={"margin": "8px 0"}),
                    html.Div(
                        id="viz-multi-pie-sec",
                        className="hidden",
                        style={"margin": "8px 0"},
                        children=[
                            dcc.Checklist(
                                id="viz-multi-pie",
                                options=[{"label": "Afficher pôles séparés", "value": "ON"}],
                                value=[],
                                labelStyle={"display": "inline-block"},
                            )
                        ],
                    ),
                ],
            ),

            # ─── Evolution temporelle (onglet 4) – filtres
            html.Div(
                id="time-sec",
                className="hidden",
                children=[
                    html.H3("Choix des filtres"),
                    html.Div(
                        id="time-period-group",
                        className="filter-block",
                        children=[
                            html.Label("Période", className="label-title"),
                            html.Div(
                                id="time-slider-wrap",
                                children=[
                                    dcc.RangeSlider(
                                        id="time-range-slider",
                                        min=0,
                                        max=max(0, len(file_list) - 1),
                                        step=1,
                                        value=[0, max(0, len(file_list) - 1)],
                                        allowCross=False,
                                        marks={i: "" for i in range(len(file_list))},  # marks mis à jour
                                    )
                                ],
                            ),
                            html.Div(
                                id="time-dd-wrap",
                                className="hidden",
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "1fr 1fr",
                                    "gap": "8px",
                                    "marginTop": "8px",
                                },
                                children=[
                                    html.Div([
                                        html.Label("Début", className="label-title"),
                                        dcc.Dropdown(
                                            id="time-start-dd",
                                            options=[],
                                            value=None,
                                            clearable=False,
                                            className="neo-dd",
                                            optionHeight=40,
                                            maxHeight=400,
                                        ),
                                    ]),
                                    html.Div([
                                        html.Label("Fin", className="label-title"),
                                        dcc.Dropdown(
                                            id="time-end-dd",
                                            options=[],
                                            value=None,
                                            clearable=False,
                                            className="neo-dd",
                                            optionHeight=40,
                                            maxHeight=400,
                                        ),
                                    ]),
                                ],
                            ),
                        ],
                    ),
                    html.Br(),
                    # filtres 1..5 (time)
                    *[
                        html.Div(
                            className="filter-block",
                            children=[
                                html.Label(f"Filtre n°{i}", className="label-title"),
                                dcc.Dropdown(
                                    id={"t": "time-col", "idx": i},
                                    options=[],
                                    placeholder="Choisissez une catégorie",
                                    clearable=True,
                                    className="filter-dropdown",
                                    optionHeight=40,
                                    maxHeight=400,
                                ),
                                dcc.Dropdown(
                                    id={"t": "time-val", "idx": i},
                                    options=[],
                                    multi=True,
                                    placeholder="(Choisissez une ou plusieurs valeurs)",
                                    className="filter-dropdown",
                                    optionHeight=40,
                                    maxHeight=400,
                                ),
                            ],
                        )
                        for i in range(1, 6)
                    ],
                ],
            ),
            # Stores d'état
            dcc.Store(id="simp-store"),
            dcc.Store(id="viz-store"),
            dcc.Store(id="cmp-store"),
        ],
    )

    # ───────────────────── Zone centrale (header + tabs) ─────────────────────
    central = html.Div(
        className="dashboard-content",
        children=[
            html.Div(html.H1(id="main-title", children="📊 Analyse des effectifs en France", className="header")),
            html.Div(id="kpi-wrap", className="kpi-wrap"),
            html.Div(id="time-kpi-wrap", className="kpi-wrap hidden"),
            dcc.Tabs(
                id="tabs",
                value="global",
                children=[
                    dcc.Tab(
                        label="Vision Globale",
                        value="global",
                        children=[
                            html.Div(
                                className="global-row",
                                style={"display": "flex", "gap": "8px"},
                                children=[
                                    html.Div(
                                        dcc.Graph(
                                            id="g-cat1",
                                            className="card",
                                            config={"responsive": True},
                                            style={"width": "100%", "height": "100%"},
                                        ),
                                        style={"flex": "1 1 50%", "minWidth": 0},
                                    ),
                                    html.Div(
                                        dcc.Graph(
                                            id="g-entite",
                                            className="card",
                                            config={"responsive": True},
                                            style={"width": "100%", "height": "100%"},
                                        ),
                                        style={"flex": "1 1 50%", "minWidth": 0},
                                    ),
                                ],
                            )
                        ],
                    ),
                    dcc.Tab(label="Visualisation", value="simp", children=html.Div(id="simp-graphs")),
                    dcc.Tab(label="Analyse Complexe De Données", value="viz", children=html.Div(id="viz-graphs", className="graphs-row")),
                    dcc.Tab(
                        label="Evolution Temporelle",
                        value="cmp",
                        children=dcc.Graph(
                            id="cmp-graph",
                            className="card",
                            config={"responsive": True},
                            style={"width": "100%", "height": "100%"},
                        ),
                    ),
                ],
            ),
        ],
    )

    # ───────────────────── Root wrapper ─────────────────────
    return html.Div(
        children=[
            # Thème
            html.Link(id="theme-css", rel="stylesheet", href=DARK_CSS),
            dcc.Store(id="theme", data="dark"),

            # Boutons flottants (menu + palette KPI droite)
            html.Button(id="theme-toggle", n_clicks=0, title="Basculer jour/nuit", className="theme-btn"),
            html.Button("☰ Menu", id="toggle-btn", className="sidebar-toggle-btn"),
            html.Button(id="right-sb-toggle", n_clicks=0, title="Ouvrir / fermer la palette KPI", className="sidebar-right-toggle-btn"),

            # Sidebars + contenu
            left_sidebar,
            right_sidebar,
            central,

            # (Optionnel) store schéma/labels pour certains callbacks (time_tab)
            dcc.Store(id="schema-store", data={"labels": {}}),
        ]
    )

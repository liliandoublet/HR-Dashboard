# callbacks/global_tab.py
from __future__ import annotations

import pandas as pd
from dash import Input, Output
import plotly.express as px
import plotly.graph_objects as go

from services.data_manager import get_df
from services.template_services import apply_theme_template
from ui.components.graphs import add_labels, make_title, fig_multi_pies as build_multi_pies



# ───────────────────────── Helpers locaux ─────────────────────────

def _natural_sort_key(txt):
    import re
    return [int(x) if x.isdigit() else x.lower()
            for x in re.split(r'(\d+)', str(txt))]

def sort_categories(series: pd.Series, mode: str) -> pd.Series:
    """
    Trie une Series d'effectifs selon le mode choisi.
    mode : 'DESC', 'ASC', 'ALPHA'
    """
    if mode == "ALPHA":
        return series.sort_index(key=lambda s: s.astype(str).str.lower())
    return series.sort_values(ascending=(mode == "ASC"))

# ───────────────────────── Callbacks ─────────────────────────

def register_callbacks(app):
    """
    Enregistre les callbacks pour l’onglet 'Vision Globale':
      - g-cat1 (pôles)
      - g-entite (entités)
    On s’appuie sur:
      • get_df(file_path) pour lire le fichier sélectionné
      • apply_theme_template(fig, theme) pour theme clair/sombre
    """

    # Dropdown labels map (injectée via layout Store ou constante côté layout)
    # On lit le mapping depuis un dcc.Store("schema-store") si disponible,
    # sinon on utilisera des libellés bruts.
    def _labels_from_store(schema) -> dict:
        return (schema or {}).get("labels", {})

    @app.callback(
        Output("g-cat1", "figure"),
        Input("file-dd", "value"),
        Input("pole-dd", "value"),
        Input("entite-dd", "value"),
        Input("global-data-dd", "value"),
        Input("global-graph-type", "value"),
        Input("global-value-mode", "value"),
        Input("glob-order-graph", "value"),
        Input("theme", "data"),
        Input("schema-store", "data"),
    )
    def g_cat1_fig(file_path, pole, ent, col, gtype, mode, order, theme, schema):
        cat_lbl = _labels_from_store(schema)

        if isinstance(file_path, list):
            file_path = file_path[0]

        df_full = get_df(file_path)
        d = df_full.copy()

        if ent and ent != "Tout":
            d = d[d["PERIMETRE"] == ent]
        if pole and pole != "Tout":
            d = d[d["CAT1"] == pole]

        tot_scope = len(d)
        tot_all = len(df_full)  # Référence “total” = fichier courant

        # Aucun filtre → histogramme ou camembert par CAT1
        if not col:
            cnt = d["CAT1"].value_counts()
            cnt = sort_categories(cnt, order)
            if mode == "pct_scope":
                cnt = 100 * cnt / max(tot_scope, 1)
            elif mode == "pct_total":
                cnt = 100 * cnt / max(tot_all, 1)

            if gtype == "pie":
                df_cnt = cnt.reset_index()
                df_cnt.columns = ["CAT1", "Val"]
                fig = px.pie(
                    df_cnt, names="CAT1", values="Val", hole=.4,
                    title=make_title("Répartition par pôle", pole, ent, total=tot_scope)
                )
            else:
                fig = px.bar(
                    x=cnt.index, y=cnt.values, text_auto=True,
                    labels={"x": "Pôle", "y": "Effectifs"},
                    title=make_title("Effectifs par pôle", pole, ent, total=tot_scope)
                )

            fig = apply_theme_template(fig, theme)
            return add_labels(fig, mode, legend_total=tot_scope)

        # 1 filtre → empilé par pôle ou multi-camemberts
        pivot = d.pivot_table(index="CAT1", columns=col, aggfunc="size", fill_value=0)
        long = pivot.reset_index().melt(id_vars="CAT1", var_name=col, value_name="Effectif")

        if mode == "pct_scope":
            totals = pivot.sum(axis=1).replace(0, pd.NA)
            long["Val"] = long.apply(
                lambda r: 0 if pd.isna(totals[r["CAT1"]]) else r["Effectif"] * 100 / totals[r["CAT1"]],
                axis=1
            )
        elif mode == "pct_total":
            long["Val"] = 100 * long["Effectif"] / max(tot_all, 1)
        else:
            long["Val"] = long["Effectif"]

        ordered_poles = sort_categories(pivot.sum(axis=1), order).index

        if gtype == "pie":
            fig = build_multi_pies(
                d, group_col="CAT1", slice_col=col,
                title_prefix=make_title("Répartition", pole, ent, col, total=tot_scope),
                order=order, cat_lbl=cat_lbl
            )
        else:
            fig = px.bar(
                long, x="CAT1", y="Val", color=col, barmode="stack",
                category_orders={"CAT1": ordered_poles},
                title=make_title("Répartition", pole, ent, col, total=tot_scope)
            )

        fig = apply_theme_template(fig, theme)
        return add_labels(fig, mode, legend_total=tot_scope)

    @app.callback(
        Output("g-entite", "figure"),
        Input("file-dd", "value"),
        Input("pole-dd", "value"),
        Input("entite-dd", "value"),
        Input("global-data-dd", "value"),
        Input("global-graph-type", "value"),
        Input("global-value-mode", "value"),
        Input("glob-order-graph", "value"),
        Input("theme", "data"),
        Input("schema-store", "data"),
    )
    def entite_fig(file_path, pole, ent, col, gtype, mode, order, theme, schema):
        cat_lbl = _labels_from_store(schema)

        if isinstance(file_path, list):
            file_path = file_path[0]

        df_full = get_df(file_path)
        d = df_full.copy()

        if pole and pole != "Tout":
            d = d[d["CAT1"] == pole]
        if ent and ent != "Tout":
            d = d[d["PERIMETRE"] == ent]

        tot_scope = len(d)
        tot_all = len(df_full)

        if not col:
            cnt = d["PERIMETRE"].value_counts()
            cnt = sort_categories(cnt, order)

            if mode == "pct_scope":
                cnt = 100 * cnt / max(tot_scope, 1)
            elif mode == "pct_total":
                cnt = 100 * cnt / max(tot_all, 1)

            if gtype == "pie":
                df_cnt = cnt.reset_index()
                df_cnt.columns = ["PERIMETRE", "Val"]
                fig = px.pie(
                    df_cnt, names="PERIMETRE", values="Val", hole=.4,
                    title=make_title("Effectifs par entité", pole, ent, total=tot_scope)
                )
            else:
                fig = px.bar(
                    x=cnt.index, y=cnt.values,
                    labels={"x": "Entité", "y": "Effectifs"},
                    title=make_title("Effectifs par entité", pole, ent, total=tot_scope)
                )
            fig = apply_theme_template(fig, theme)
            return add_labels(fig, mode, legend_total=tot_scope)

        # Filtre actif
        pivot = d.pivot_table(index="PERIMETRE", columns=col, aggfunc="size", fill_value=0)
        long = pivot.reset_index().melt(id_vars="PERIMETRE", var_name=col, value_name="Effectif")

        if mode == "pct_scope":
            totals = pivot.sum(axis=1).replace(0, pd.NA)
            long["Val"] = long.apply(
                lambda r: 0 if pd.isna(totals[r["PERIMETRE"]]) else r["Effectif"] * 100 / totals[r["PERIMETRE"]],
                axis=1
            )
        elif mode == "pct_total":
            long["Val"] = 100 * long["Effectif"] / max(tot_all, 1)
        else:
            long["Val"] = long["Effectif"]

        if gtype == "pie":
            fig = build_multi_pies(
                d, group_col="PERIMETRE", slice_col=col,
                title_prefix=make_title("Répartition", pole, ent, col, total=tot_scope),
                order=order, cat_lbl=cat_lbl
            )
        else:
            fig = px.bar(
                long, x="PERIMETRE", y="Val", color=col, barmode="stack",
                title=make_title("Répartition", pole, ent, col, total=tot_scope)
            )

        fig = apply_theme_template(fig, theme)
        return add_labels(fig, mode, legend_total=tot_scope)

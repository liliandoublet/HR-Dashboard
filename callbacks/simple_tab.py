# callbacks/simple_tab.py
from __future__ import annotations

from typing import List, Optional, Dict

import numpy as np
import pandas as pd
from dash import Input, Output, State, html, dcc
from dash.exceptions import PreventUpdate
import plotly.express as px
import plotly.graph_objects as go

from services.data_manager import get_df
from services.template_services import apply_theme_template
from ui.components.graphs import add_labels, make_title, fig_multi_pies as build_multi_pies



# ───────────────────────── Helpers locaux ─────────────────────────

def sort_categories(series: pd.Series, mode: str) -> pd.Series:
    """Trie une Series d'effectifs selon le mode : 'DESC', 'ASC', 'ALPHA'."""
    if mode == "ALPHA":
        return series.sort_index(key=lambda s: s.astype(str).str.lower())
    return series.sort_values(ascending=(mode == "ASC"))

def _natural_key(txt):
    import re
    return [int(x) if x.isdigit() else x.lower()
            for x in re.split(r'(\d+)', str(txt))]

def fig_base(dsrc: pd.DataFrame, cat: str, kind: str, order: str, mode: str,
             pole: str = "Tout", ent: str = "Tout", total: int | None = None,
             theme: str = "dark", cat_lbl: Optional[dict] = None):
    """Graphique simple (bar/pie/treemap) avec titre/étiquettes/thème."""
    cnt = dsrc[cat].value_counts()

    if mode == "pct_scope":
        cnt = 100 * cnt / max(len(dsrc), 1)
    elif mode == "pct_total":
        # NB: ici, la référence "total" est le fichier filtré à l’onglet,
        # pas le global France. Si besoin, adapte en injectant ce dénominateur.
        cnt = 100 * cnt / max(len(dsrc), 1)

    cnt = sort_categories(cnt, order).reset_index()
    cnt.columns = [cat, "Val"]
    chart_title = make_title("Répartition", pole, ent, cat, total=total, cat_lbl=cat_lbl)

    if kind == "pie":
        fig = px.pie(cnt, names=cat, values="Val", hole=.4, title=chart_title)
        # légende horizontale sous le graphe
        fig.update_layout(
            legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
            margin=dict(b=120)
        )
    elif kind == "treemap":
        df_tm = cnt.sort_values(cat)
        fig = px.treemap(df_tm, path=[cat], values="Val", title=chart_title)
        if fig.data:
            fig.data[0].textinfo = (
                "label+value+percent root" if mode == "count"
                else "label+value+percent parent+percent root"
            )
    else:
        fig = px.bar(cnt, x=cat, y="Val", title=chart_title)

    fig = apply_theme_template(fig, theme)
    return add_labels(fig, mode)


# ───────────────────────── Callbacks ─────────────────────────

def register_callbacks(app):
    """
    Callbacks de l’onglet 2 “Visualisation” :
      • store_simp_selection : mémorise l’ordre des deux filtres simples
      • toggle_simp_filters_for_scatter : masque/affiche les blocs Scatter/Bubble
      • simples : génère les graphes selon le type choisi
    """

    # Mémorise les deux filtres choisis (ordre col1 → col2)
    @app.callback(
        Output("simp-store", "data"),
        Input("simp-col1", "value"),
        Input("simp-col2", "value"),
    )
    def store_simp_selection(col1, col2):
        cols: List[str] = []
        if col1:
            cols.append(col1)
        if col2 and col2 != col1:
            cols.append(col2)
        return cols

    # Affiche/masque les options spécifiques au scatter/bubble
    @app.callback(
        Output("simp-f1-wrap", "className"),
        Output("simp-f2-wrap", "className"),
        Output("simp-combine-wrap", "className"),
        Output("scatter-opts", "className"),
        Output("size-wrap", "className"),
        Input("simp-type", "value"),
    )
    def toggle_simp_filters_for_scatter(gtype):
        is_xy = gtype in ("scatter", "bubble")
        show_size = gtype == "bubble"
        cls_hide = "hidden"
        return (
            cls_hide if is_xy else "",
            cls_hide if is_xy else "",
            cls_hide if is_xy else "",
            "filter-block" if is_xy else "filter-block hidden",
            "" if show_size else "hidden"
        )

    # Rendu des graphiques
    @app.callback(
        Output("simp-graphs", "children"),
        Input("file-dd", "value"),
        Input("simp-store", "data"),
        Input("simp-type", "value"),
        Input("pole-dd", "value"),
        Input("entite-dd", "value"),
        Input("simp-combine", "value"),
        Input("simp-order-graph", "value"),
        Input("simp-value-mode", "value"),
        Input("theme", "data"),
        Input("simp-x", "value"),
        Input("simp-y", "value"),
        Input("simp-size", "value"),
        State("schema-store", "data"),
    )
    def simples(file_path, active, gtype, pole, ent, combine, order, mode,
                theme, xcol, ycol, sizecol, schema):
        """
        - gtype: 'bar' | 'pie' | 'treemap' | 'scatter' | 'bubble'
        - active: ['col1', 'col2'] selon les filtres simples
        - combine: ['ON'] pour combiner col1×col2 (bar/pie uniquement)
        """
        cat_lbl = (schema or {}).get("labels", {})

        if not active and gtype not in {"scatter", "bubble"}:
            return []

        if isinstance(file_path, list):
            file_path = file_path[0]

        df_full = get_df(file_path)
        d = df_full.copy()

        # Périmètre pôle/entité
        if pole and pole != "Tout" and "CAT1" in d.columns:
            d = d[d["CAT1"] == pole]
        if ent and ent != "Tout" and "PERIMETRE" in d.columns:
            d = d[d["PERIMETRE"] == ent]

        # ───────────── SCATTER (nuage de points) ─────────────
        if gtype == "scatter":
            # Choix des axes : priorité aux 2 filtres si deux colonnes actives
            x = y = None
            if active and len(active) >= 2:
                x, y = active[:2]
            elif active and len(active) == 1:
                x = active[0]
                y = ycol or xcol
            else:
                x, y = xcol, ycol

            if not x or not y:
                return html.Div("Choisissez deux variables numériques pour X et Y.", className="warn")

            dx = pd.to_numeric(d.get(x), errors="coerce")
            dy = pd.to_numeric(d.get(y), errors="coerce")
            dd = pd.DataFrame({x: dx, y: dy, "PERIMETRE": d.get("PERIMETRE"), "CAT1": d.get("CAT1")}).dropna()

            if dd.empty:
                return html.Div("Aucune donnée exploitable (valeurs manquantes ou non numériques).", className="warn")

            # Corrélation (Pearson) si possible
            try:
                rho = float(dd[[x, y]].corr().iloc[0, 1])
                rho_txt = f" • ρ = {rho:.2f}".replace(".", ",")
            except Exception:
                rho_txt = ""

            fig = px.scatter(
                dd, x=x, y=y,
                hover_data=["PERIMETRE", "CAT1"] if {"PERIMETRE", "CAT1"}.issubset(dd.columns) else None,
                title=make_title(f"Nuage de points – {cat_lbl.get(x, x)} × {cat_lbl.get(y, y)}{rho_txt}",
                                 pole, ent, total=len(dd), cat_lbl=cat_lbl)
            )
            fig.update_layout(
                xaxis_title=cat_lbl.get(x, x),
                yaxis_title=cat_lbl.get(y, y),
                legend_title_text=""
            )
            fig = apply_theme_template(fig, theme)

            card = html.Div(
                dcc.Graph(figure=fig, className="card",
                          config={"responsive": True}, style={"width": "100%", "height": "100%"}),
                className="graph-container"
            )
            return html.Div([card], className="graphs-row")

        # ───────────── BUBBLE (scatter avec taille) ─────────────
        if gtype == "bubble":
            x, y, s = xcol, ycol, sizecol
            if not x or not y:
                return html.Div("Choisissez X et Y.", className="warn")

            dx = pd.to_numeric(d.get(x), errors="coerce")
            dy = pd.to_numeric(d.get(y), errors="coerce")
            base = pd.DataFrame({x: dx, y: dy, "PERIMETRE": d.get("PERIMETRE"), "CAT1": d.get("CAT1")}).dropna()

            if base.empty:
                return html.Div("Aucune donnée exploitable (valeurs manquantes ou non numériques).", className="warn")

            if s == "__COUNT__":
                # Taille = effectifs par classes (bins) de X/Y
                n = len(base)
                nbins = max(6, min(15, int(np.sqrt(n))))
                base["__xbin__"] = pd.cut(base[x], bins=nbins, include_lowest=True)
                base["__ybin__"] = pd.cut(base[y], bins=nbins, include_lowest=True)

                agg = base.groupby(["__xbin__", "__ybin__"]).size().reset_index(name="Eff")
                agg["__xcenter__"] = agg["__xbin__"].apply(lambda iv: iv.mid if pd.notna(iv) else np.nan)
                agg["__ycenter__"] = agg["__ybin__"].apply(lambda iv: iv.mid if pd.notna(iv) else np.nan)
                agg["Classe_X"] = agg["__xbin__"].astype(str)
                agg["Classe_Y"] = agg["__ybin__"].astype(str)

                if agg.empty:
                    return html.Div("Aucune classe non vide après agrégation.", className="warn")

                fig = px.scatter(
                    agg, x="__xcenter__", y="__ycenter__", size="Eff", size_max=60,
                    hover_data={"Eff": True, "Classe_X": True, "Classe_Y": True},
                    title=make_title(
                        f"Graphique en bulle – effectifs par classes de {cat_lbl.get(x, x)} × {cat_lbl.get(y, y)}",
                        pole, ent, total=len(d), cat_lbl=cat_lbl
                    ),
                )
                fig.update_layout(xaxis_title=cat_lbl.get(x, x),
                                  yaxis_title=cat_lbl.get(y, y),
                                  legend_title_text="Effectifs")
                fig = apply_theme_template(fig, theme)

                card = html.Div(
                    dcc.Graph(figure=fig, className="card",
                              config={"responsive": True}, style={"width": "100%", "height": "100%"}),
                    className="graph-container"
                )
                return html.Div([card], className="graphs-row")

            # Taille = une autre colonne numérique
            ds = pd.to_numeric(d.get(s), errors="coerce") if s else None
            dd = pd.DataFrame({x: dx, y: dy, s: ds, "PERIMETRE": d.get("PERIMETRE"), "CAT1": d.get("CAT1")}).dropna()
            if dd.empty:
                return html.Div("Aucune donnée exploitable (valeurs manquantes ou non numériques).", className="warn")

            fig = px.scatter(
                dd, x=x, y=y, size=s, size_max=60,
                hover_data=["PERIMETRE", "CAT1"] if {"PERIMETRE", "CAT1"}.issubset(dd.columns) else None,
                title=make_title(
                    f"Graphique en bulle – {cat_lbl.get(x, x)} × {cat_lbl.get(y, y)} (taille: {cat_lbl.get(s, s)})",
                    pole, ent, total=len(dd), cat_lbl=cat_lbl
                )
            )
            fig.update_layout(xaxis_title=cat_lbl.get(x, x),
                              yaxis_title=cat_lbl.get(y, y),
                              legend_title_text="")
            fig = apply_theme_template(fig, theme)

            card = html.Div(
                dcc.Graph(figure=fig, className="card",
                          config={"responsive": True}, style={"width": "100%", "height": "100%"}),
                className="graph-container"
            )
            return html.Div([card], className="graphs-row")

        # ───────── Treemap : 1 ou 2 niveaux ─────────
        if gtype == "treemap":
            lvl = min(len(active or []), 2)
            if lvl == 0:
                return html.Div("Sélectionnez au moins un filtre pour le treemap.", className="warn")

            path_cols = active[:lvl]
            grouped = d.groupby(path_cols).size().reset_index(name="Eff")

            if mode == "pct_scope" and lvl >= 1:
                denom = grouped.groupby(path_cols[:-1] if lvl > 1 else [])[ "Eff" ].transform("sum")
                grouped["Eff"] = 100 * grouped["Eff"] / denom.replace(0, np.nan)
            elif mode == "pct_total":
                grouped["Eff"] = 100 * grouped["Eff"] / max(len(d), 1)

            title_cols = " → ".join(cat_lbl.get(c, c) for c in path_cols)
            fig = px.treemap(grouped, path=path_cols, values="Eff",
                             title=make_title("Treemap", pole, ent, title_cols, total=len(d), cat_lbl=cat_lbl))
            fig = apply_theme_template(fig, theme)
            if fig.data:
                fig.data[0].textinfo = "label+value+percent parent+percent root"
            fig = add_labels(fig, mode, legend_total=len(d))

            card = html.Div(
                dcc.Graph(figure=fig, className="card",
                          config={"responsive": True}, style={"width": "100%", "height": "100%"}),
                className="graph-container"
            )
            return html.Div([card], className="graphs-row")

        # ───────── Bar / Pie (simples ou combinés) ─────────
        cards = []

        # Mode combiné (2 filtres) pour bar/pie uniquement
        if ("ON" in (combine or [])) and (active and len(active) == 2) and gtype in {"bar", "pie"}:
            c1, c2 = active
            grouped = d.groupby([c1, c2]).size().reset_index(name="Eff")

            if mode != "count":
                den = grouped.groupby(c1)["Eff"].transform("sum") if mode == "pct_scope" else max(len(d), 1)
                grouped["Eff"] = 100 * grouped["Eff"] / den

            ordered_c1 = sort_categories(grouped.groupby(c1)["Eff"].sum(), order).index

            if gtype == "pie":
                # multi-camemberts par c1
                fig = build_multi_pies(
                    grouped.rename(columns={"Eff": "Val"}),  # data au format attendu
                    group_col=c1, slice_col=c2,
                    title_prefix=make_title("Répartition", pole, ent, f"{cat_lbl.get(c1,c1)} × {cat_lbl.get(c2,c2)}",
                                            total=len(d), cat_lbl=cat_lbl),
                    order=order, cat_lbl=cat_lbl
                )
                fig = apply_theme_template(fig, theme)
            else:
                fig = px.bar(grouped, x=c1, y="Eff", color=c2, barmode="stack",
                             category_orders={c1: ordered_c1},
                             title=make_title("Croisement", pole, ent,
                                              f"{cat_lbl.get(c1,c1)} × {cat_lbl.get(c2,c2)}",
                                              total=len(d), cat_lbl=cat_lbl))
                fig = apply_theme_template(fig, theme)
                fig = add_labels(fig, mode, legend_total=len(d))

            cards.append(html.Div(
                dcc.Graph(figure=fig, className="card",
                          config={"responsive": True}, style={"width": "100%", "height": "100%"}),
                className="graph-container"
            ))
            return html.Div(cards, className="graphs-row")

        # Graphiques indépendants (1 filtre ou 2 non combinés)
        tot_scope = len(d)
        for cat in (active or []):
            fig = fig_base(d, cat, gtype, order, mode, pole=pole, ent=ent, total=tot_scope,
                           theme=theme, cat_lbl=cat_lbl)
            legend_lbl = ent if ent != "Tout" else (pole if pole != "Tout" else "Tous")
            fig.update_traces(name=legend_lbl, showlegend=(gtype == "pie"))
            cards.append(html.Div(
                dcc.Graph(figure=fig, className="card",
                          config={"responsive": True}, style={"width": "100%", "height": "100%"}),
                className="graph-container"
            ))

        return html.Div(cards, className="graphs-row")

# callbacks/viz_tab.py
from __future__ import annotations

from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd
from dash import Input, Output, State, html, dcc
from dash.dependencies import ALL
from dash.exceptions import PreventUpdate
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objects import Bar, Scatter
from plotly.subplots import make_subplots

from services.data_manager import get_df
from services.template_services import apply_theme_template
from ui.components.graphs import add_labels, make_title, fig_multi_pies as build_multi_pies



# ───────────────────────── Helpers ─────────────────────────

def sort_categories(series: pd.Series, mode: str) -> pd.Series:
    """Trie une Series d'effectifs selon 'DESC' | 'ASC' | 'ALPHA'."""
    if mode == "ALPHA":
        return series.sort_index(key=lambda s: s.astype(str).str.lower())
    return series.sort_values(ascending=(mode == "ASC"))

def _natural_key(txt: str):
    import re
    return [int(x) if x.isdigit() else x.lower()
            for x in re.split(r'(\d+)', str(txt))]


# ───────────────────────── Rendu principal du Tab Viz ─────────────────────────

def register_callbacks(app):
    """
    Construit les graphiques de l’onglet 3 “Analyse complexe” :
      • un ou plusieurs filtres 1→7
      • comparaison (sélection vs comparant)
      • bar / pie / treemap
      • multi-camemberts et combinaison 1×2
    """

    @app.callback(
        Output("viz-graphs", "children"),
        Input("file-dd", "value"),
        Input({"t": "viz-col", "idx": ALL}, "value"),   # colonnes 1→n
        Input({"t": "viz-val", "idx": ALL}, "value"),   # valeurs 1→n
        Input("viz-type", "value"),                     # 'bar' | 'pie' | 'treemap'
        Input("viz-value-mode", "value"),               # 'count' | 'pct_scope' | 'pct_total'
        Input("viz-order-graph", "value"),              # 'DESC' | 'ASC' | 'ALPHA'
        Input("pole-dd", "value"),
        Input("entite-dd", "value"),
        Input("viz-compare-mode", "value"),             # [] or ['ON']
        Input("viz-cmp-pole-dd", "value"),
        Input("viz-cmp-ent-dd", "value"),
        Input("viz-multi-pie", "value"),                # [] or ['ON']
        Input("viz-combine-12", "value"),               # [] or ['ON']
        Input("theme", "data"),
        State("schema-store", "data"),
    )
    def build_complex_graph(file_path,
                            cols, vals,
                            gtype, mode, order,
                            pole, ent,
                            cmp_mode, cmp_pole, cmp_ent,
                            multi_pie, combine12,
                            theme, schema):
        cat_lbl = (schema or {}).get("labels", {})
        if isinstance(file_path, list):
            file_path = file_path[0]

        # DataFrame périmètre sélectionné
        d_full = get_df(file_path)
        d = d_full.copy()
        if pole and pole != "Tout" and "CAT1" in d.columns:
            d = d[d["CAT1"] == pole]
        if ent and ent != "Tout" and "PERIMETRE" in d.columns:
            d = d[d["PERIMETRE"] == ent]

        # Comparant
        use_cmp = "ON" in (cmp_mode or [])
        if use_cmp:
            d_cmp = d_full.copy()
            if cmp_pole and cmp_pole != "Tout" and "CAT1" in d_cmp.columns:
                d_cmp = d_cmp[d_cmp["CAT1"] == cmp_pole]
            if cmp_ent and cmp_ent != "Tout" and "PERIMETRE" in d_cmp.columns:
                d_cmp = d_cmp[d_cmp["PERIMETRE"] == cmp_ent]
            if (pole or "Tout") == (cmp_pole or "Tout") and (ent or "Tout") == (cmp_ent or "Tout"):
                return html.Div("Impossible de comparer deux sélections identiques.", className="warn")
        else:
            d_cmp = None

        total_scope = len(d)
        if total_scope == 0:
            return html.Div("Aucune donnée pour ces filtres.", className="warn")

        # Colonnes actives (non vides)
        active_cols: List[str] = [c for c in cols if c]
        if gtype == "treemap":
            # Exclure si nécessaire (si tu stockes une liste noire dans schema)
            treemap_excl = set((schema or {}).get("TREEMAP_EXCLUDED_COLS", []))
            active_cols = [c for c in active_cols if c not in treemap_excl]
            if not active_cols:
                return html.Div("Aucune colonne autorisée pour le treemap.", className="warn")

        # Appliquer les filtres Valeurs (sauf pour treemap où on peut choisir d'ignorer)
        apply_val_filters = (gtype != "treemap")
        for c, v in zip(cols, vals):
            if c and v and apply_val_filters:
                d = d[d[c].isin(v)]
                if use_cmp and d_cmp is not None:
                    d_cmp = d_cmp[d_cmp[c].isin(v)]
        if d.empty:
            return html.Div("Aucune donnée après application des filtres.", className="warn")

        # Cas 0 filtre : graph global (bar/pie) ou donut total si non comparé
        if not active_cols:
            if use_cmp and d_cmp is not None:
                labels = [f"{pole} / {ent}", f"{cmp_pole} / {cmp_ent}"]
                counts = [len(d), len(d_cmp)]
                vals_y = counts
                if mode == "pct_scope":
                    vals_y = [100 * counts[0] / max(total_scope, 1),
                              100 * counts[1] / max(len(d_cmp), 1)]
                elif mode == "pct_total":
                    denom = max(len(d_full), 1)
                    vals_y = [100 * counts[0] / denom, 100 * counts[1] / denom]

                if gtype == "pie":
                    fig = px.pie(names=labels, values=vals_y,
                                 hole=.4, title=make_title("Comparaison globale", pole, ent, None, total_scope, cat_lbl))
                    fig = apply_theme_template(fig, theme)
                    fig = add_labels(fig, mode)
                else:
                    fig = px.bar(x=labels, y=vals_y,
                                 labels={"x": "Sélection", "y": "Valeur"},
                                 title=make_title("Comparaison globale", pole, ent, None, total_scope, cat_lbl))
                    fig = apply_theme_template(fig, theme)
                    fig = add_labels(fig, mode)
                    fig.update_layout(barmode="group")
            else:
                # Donut total pour la sélection seule
                fig = px.pie(names=["Total"], values=[len(d)],
                             hole=.4, title=f"Effectif total : {len(d):,}".replace(",", "\u202F"))
                fig = apply_theme_template(fig, theme)
                fig = add_labels(fig, mode="count")
            return dcc.Graph(figure=fig, className="card", config={"responsive": True},
                             style={"width": "100%", "height": "100%"})

        # Option “Combiner 1×2” (uniquement bar)
        use_combine12 = ("ON" in (combine12 or [])) and gtype == "bar" and len(active_cols) >= 2
        if use_combine12:
            c1, c2 = active_cols[0], active_cols[1]
            df_cross = d.groupby([c1, c2]).size().reset_index(name="Eff")
            if mode != "count":
                den = df_cross.groupby(c1)["Eff"].transform("sum") if mode == "pct_scope" else max(len(d), 1)
                df_cross["Eff"] = 100 * df_cross["Eff"] / den
            ordered_c1 = sort_categories(df_cross.groupby(c1)["Eff"].sum(), order).index
            fig = px.bar(
                df_cross, x=c1, y="Eff", color=c2, barmode="stack",
                category_orders={c1: ordered_c1},
                title=make_title("Croisement complexe", pole, ent, f"{(cat_lbl.get(c1,c1))} × {(cat_lbl.get(c2,c2))}",
                                 total=total_scope, cat_lbl=cat_lbl)
            )
            fig = apply_theme_template(fig, theme)
            fig = add_labels(fig, mode, legend_total=total_scope)
            return dcc.Graph(figure=fig, className="card", config={"responsive": True},
                             style={"width": "100%", "height": "100%"})

        # Branches selon gtype
        main = active_cols[0]
        cnt = d[main].value_counts()
        if mode == "pct_scope":
            cnt = 100 * cnt / max(len(d), 1)
        elif mode == "pct_total":
            cnt = 100 * cnt / max(len(d_full), 1)
        cnt = sort_categories(cnt, order).reset_index()
        cnt.columns = [main, "Val"]

        # ───────── Pie ─────────
        if gtype == "pie":
            if not use_cmp or d_cmp is None or "ON" not in (multi_pie or []):
                # Pie simple (sélection courante)
                fig = px.pie(cnt, names=main, values="Val", hole=.4,
                             title=make_title("Répartition", pole, ent, main, total_scope, cat_lbl))
                fig = apply_theme_template(fig, theme)
                fig.update_layout(legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
                                  margin=dict(b=120))
                fig = add_labels(fig, mode)
                return dcc.Graph(figure=fig, className="card", config={"responsive": True},
                                 style={"width": "100%", "height": "100%"})
            # Comparaison + multi-pie : un donut par sélection (sélection vs comparant)
            sel_vals = vals[0] if vals else []
            if sel_vals:
                df1 = d[d[main].isin(sel_vals)].assign(_Sélection=f"{pole} / {ent}")
                df2 = d_cmp[d_cmp[main].isin(sel_vals)].assign(_Sélection=f"{cmp_pole} / {cmp_ent}")
                combined = pd.concat([df1, df2], ignore_index=True)
            else:
                combined = pd.concat([
                    d.assign(_Sélection=f"{pole} / {ent}"),
                    d_cmp.assign(_Sélection=f"{cmp_pole} / {cmp_ent}")
                ], ignore_index=True)
            fig = build_multi_pies(combined, group_col="_Sélection", slice_col=main,
                                   title_prefix=make_title("Comparaison", pole, ent, main, total_scope, cat_lbl),
                                   order=order, cat_lbl=cat_lbl)
            fig = apply_theme_template(fig, theme)
            fig = add_labels(fig, mode)
            fig.update_layout(legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"),
                              margin=dict(t=80, b=100))
            return dcc.Graph(figure=fig, className="card", config={"responsive": True},
                             style={"width": "100%", "height": "100%"})

        # ───────── Treemap ─────────
        if gtype == "treemap":
            if use_cmp and d_cmp is not None:
                df1 = d.assign(_Sélection=f"{pole} / {ent}")
                df2 = d_cmp.assign(_Sélection=f"{cmp_pole} / {cmp_ent}")
                plot_df = pd.concat([df1, df2], ignore_index=True)
                path_cols = ["_Sélection"] + active_cols
                title_prefix = "Treemap comparatif"
            else:
                plot_df = d
                path_cols = active_cols
                title_prefix = "Treemap interactif"

            treemap_df = plot_df.groupby(path_cols).size().reset_index(name="Effectif")
            if mode == "pct_scope":
                treemap_df["Effectif"] = (
                    treemap_df.groupby(path_cols[:-1])["Effectif"]
                              .transform(lambda x: 100 * x / x.sum())
                )
            elif mode == "pct_total":
                treemap_df["Effectif"] = 100 * treemap_df["Effectif"] / max(len(d_full), 1)

            fig = px.treemap(treemap_df, path=path_cols, values="Effectif",
                             title=make_title(title_prefix, pole, ent,
                                              " > ".join(cat_lbl.get(c, c) for c in active_cols),
                                              total=total_scope, cat_lbl=cat_lbl))
            fig = apply_theme_template(fig, theme)
            if fig.data:
                fig.data[0].texttemplate = "%{label}<br>%{value:,}"
                fig.data[0].textinfo = "label+value+percent parent+percent root"
            return dcc.Graph(figure=fig, className="card", config={"responsive": True},
                             style={"width": "100%", "height": "100%"})

        # ───────── Bar (simple ou comparé) ─────────
        fig = px.bar(cnt, x=main, y="Val")
        fig.update_layout(
            title=make_title("Répartition", pole, ent, main, total_scope, cat_lbl),
            legend_title_text=cat_lbl.get(main, main),
            legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
            margin=dict(b=120)
        )
        fig = apply_theme_template(fig, theme)
        fig = add_labels(fig, mode)

        # Comparaison ON → ajouter la série comparante groupée
        if use_cmp and d_cmp is not None:
            ordered_idx = cnt[main]
            cnt_cmp = d_cmp[main].value_counts().reindex(ordered_idx).fillna(0)
            if mode == "pct_scope":
                cnt_cmp = 100 * cnt_cmp / max(len(d_cmp), 1)
            elif mode == "pct_total":
                cnt_cmp = 100 * cnt_cmp / max(len(d_full), 1)

            fig.data[0].name = f"{pole} / {ent}"
            fig.data[0].showlegend = True
            fig.add_trace(Bar(x=ordered_idx, y=cnt_cmp.values,
                              name=f"{cmp_pole} / {cmp_ent}", showlegend=True))
            fig.update_layout(
                barmode="group",
                legend_title_text="",
                legend=dict(orientation="h", x=0.5, xanchor="center", y=1.02, yanchor="bottom",
                            bgcolor="rgba(0,0,0,0)", borderwidth=0, font=dict(size=10)),
                margin=dict(t=80, b=40)
            )
            fig = add_labels(fig, mode)

        return dcc.Graph(figure=fig, className="card", config={"responsive": True},
                         style={"width": "100%", "height": "100%"})

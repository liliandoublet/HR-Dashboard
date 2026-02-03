# callbacks/time_tab.py
from __future__ import annotations

import os
import re
import datetime as dt
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from dash import Input, Output, State, html, dcc
from dash.dependencies import ALL, MATCH
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go

from services.data_manager import data_manager, get_df
from services.template_services import apply_theme_template
from config.settings import THRESHOLD_FILES_FOR_DD

from ui.components.graphs import add_labels



# ────────────────────────── Helpers locaux ──────────────────────────
from config.settings import DATE_REGEX, MONTH_FR
DATE_PAT = re.compile(DATE_REGEX)


def file_to_dt(path: str) -> Optional[dt.date]:
    """Renvoie la date (AAAAMMJJ) encodée dans le nom de fichier, si présente."""
    m = DATE_PAT.search(os.path.basename(path))
    if not m:
        return None
    return dt.datetime.strptime(m.group(1), "%Y%m%d").date()

def dt_long_fr(d: dt.date) -> str:
    """2023-12-31 → 'décembre 2023' (mois en toutes lettres)."""
    return f"{MONTH_FR[d.month - 1]} {d.year}"

def dt_short_fr(d: dt.date) -> str:
    """2023-12-31 → '12/2023'."""
    return f"{d.month:02d}/{d.year}"

def make_sparse_marks(n: int, labeler, k: int = 6) -> Dict[int, str]:
    """Réduit le nombre de marks d’un slider à ≤ k libellés (0, n-1 + espacés)."""
    if n <= 0:
        return {}
    if n <= k:
        return {i: labeler(i) for i in range(n)}
    idxs = sorted(set([0, n - 1] + [int(round(x)) for x in np.linspace(0, n - 1, k - 2)]))
    return {i: labeler(i) for i in idxs}

def _labels_for_files(file_list: List[str]) -> Tuple[List[Optional[dt.date]], Dict[int, str]]:
    """Prépare dates et marks (format court) pour un ensemble de fichiers."""
    dates = [file_to_dt(fp) for fp in file_list]

    def _lab(i: int) -> str:
        d = dates[i] if 0 <= i < len(dates) else None
        return dt_short_fr(d) if d else os.path.basename(file_list[i])

    full_marks = {i: _lab(i) for i in range(len(file_list))}
    return dates, full_marks

def make_kpi_tile(value: str, label: str, css_class: str) -> html.Div:
    """Tuile KPI simple (s’aligne avec ta charte CSS existante)."""
    if isinstance(value, (int, float)):
        display = f"{value:,}".replace(",", "\u202f")
    else:
        display = str(value)
    return html.Div(
        className=f"kpi-tile {css_class}",
        children=[
            html.Span(display, className="value"),
            html.Span(label, className="text-sub"),
        ],
    )

def compute_kpi_delta(df_prev: pd.DataFrame, df_curr: pd.DataFrame) -> Dict[str, Optional[float]]:
    """
    Calcule la variation relative (%) entre deux snapshots pour :
      - effectif total
      - % de femmes
      - âge moyen
      - alternants (EMPLOIS == 'Apprenti')
      - proches retraite (AGE >= 60)
    Retourne None si le dénominateur est nul.
    """
    def var_pct(a, b):
        return None if a == 0 else 100 * (b - a) / a

    eff_prev, eff_curr = len(df_prev), len(df_curr)

    pctF_prev = 100 * (df_prev.get("Sexe", pd.Series(dtype=object)) == "F").mean() if eff_prev else 0
    pctF_curr = 100 * (df_curr.get("Sexe", pd.Series(dtype=object)) == "F").mean() if eff_curr else 0

    age_prev = pd.to_numeric(df_prev.get("AGE"), errors="coerce").mean()
    age_curr = pd.to_numeric(df_curr.get("AGE"), errors="coerce").mean()

    alt_prev = (df_prev.get("EMPLOIS", pd.Series(dtype=object)) == "Apprenti").sum()
    alt_curr = (df_curr.get("EMPLOIS", pd.Series(dtype=object)) == "Apprenti").sum()

    ret_prev = (pd.to_numeric(df_prev.get("AGE"), errors="coerce") >= 60).sum()
    ret_curr = (pd.to_numeric(df_curr.get("AGE"), errors="coerce") >= 60).sum()

    return {
        "Δ_effectif_%":         var_pct(eff_prev, eff_curr),
        "Δ_parité_F_%":         var_pct(pctF_prev, pctF_curr),
        "Δ_age_moyen_%":        var_pct(age_prev, age_curr),
        "Δ_alternants_%":       var_pct(alt_prev, alt_curr),
        "Δ_proches_retraite_%": var_pct(ret_prev, ret_curr),
        # Valeurs absolues si besoin un jour :
        # "effectif": (eff_prev, eff_curr),
        # "pctF": (pctF_prev, pctF_curr),
        # "age_moyen": (age_prev, age_curr),
        # "alternants": (alt_prev, alt_curr),
        # "proches_ret": (ret_prev, ret_curr),
    }

# ────────────────────────── Callbacks ──────────────────────────

def register_callbacks(app):
    # 1) Remplissage des valeurs des filtres (onglet 4)
    @app.callback(
        Output({"t": "time-val", "idx": MATCH}, "options"),
        Input("file-dd", "value"),
        Input({"t": "time-col", "idx": MATCH}, "value"),
        Input({"t": "time-col", "idx": ALL}, "value"),
        Input({"t": "time-val", "idx": ALL}, "value"),
        Input("pole-dd", "value"),
        Input("entite-dd", "value"),
        State({"t": "time-val", "idx": MATCH}, "id"),
        prevent_initial_call=True,
    )
    def update_time_value_dd(file_path, col_this, all_cols, all_vals, pole, ent, this_id):
        if not col_this:
            return []

        if isinstance(file_path, list):
            file_path = file_path[0]
        d = get_df(file_path).copy()

        # Périmètre Pôle / Entité
        if pole and pole != "Tout" and "CAT1" in d.columns:
            d = d[d["CAT1"] == pole]
        if ent and ent != "Tout" and "PERIMETRE" in d.columns:
            d = d[d["PERIMETRE"] == ent]

        # Appliquer les filtres précédents uniquement (idx strictement inférieurs)
        idx_this = this_id["idx"]
        for idx_loop, (c, v) in enumerate(zip(all_cols, all_vals), start=1):
            if idx_loop >= idx_this:
                break
            if c and v:
                d = d[d[c].isin(v)]

        # Options sous forme "val — effectif"
        vc = d[col_this].value_counts().sort_index()
        return [{"label": f"{val} — {cnt}", "value": val} for val, cnt in vc.items()]

    # 2) Bascule Slider ↔ Dropdown (et options dropdown + marks) pour les deux zones
    @app.callback(
        Output("time-slider-wrap", "className"),
        Output("time-dd-wrap", "className"),
        Output("period-bar", "className"),
        Output("time-range-slider", "marks"),
        Output("time-range-slider", "max"),
        Output("delta-range", "marks"),
        Output("delta-range", "max"),
        Output("time-start-dd", "options"),
        Output("time-end-dd", "options"),
        Output("delta-start-dd", "options"),
        Output("delta-end-dd", "options"),
        Input("file-dd", "options"),
        Input("tabs", "value"),
    )
    def toggle_time_inputs(_file_opts, tab):
        # Liste et labels
        file_list = data_manager.get_file_list()
        n = len(file_list)
        use_dd = n > THRESHOLD_FILES_FOR_DD
        on_cmp = (tab == "cmp")

        dates, full_marks = _labels_for_files(file_list)

        def _lab(i):  # marque courte
            d = dates[i] if 0 <= i < len(dates) else None
            return dt_short_fr(d) if d else os.path.basename(file_list[i])

        marks_compact = make_sparse_marks(n, _lab, k=6)

        dd_opts = [{"label": _lab(i), "value": i} for i in range(n)]

        # Classes d’affichage
        cls_slider = "" if (on_cmp and not use_dd) else "hidden"
        cls_time_dd = "" if (on_cmp and use_dd) else "hidden"
        period_bar_cls = "period-bar" + ("" if (on_cmp and not use_dd) else " hidden")

        return (
            cls_slider,                          # time-slider-wrap
            cls_time_dd,                         # time-dd-wrap
            period_bar_cls,                     # delta-group
            (full_marks if not use_dd else marks_compact),   # time marks
            max(0, n - 1),                       # time max
            (full_marks if not use_dd else marks_compact),   # delta marks
            max(0, n - 1),                       # delta max
            dd_opts, dd_opts, dd_opts, dd_opts,
        )

    # 3) Synchronisation Dropdown (Début/Fin) → Slider (Zone graphe)
    @app.callback(
        Output("time-range-slider", "value"),
        Input("time-start-dd", "value"),
        Input("time-end-dd", "value"),
        State("time-range-slider", "value"),
        prevent_initial_call=True,
    )
    def time_dd_to_slider(vs, ve, cur):
        if vs is None or ve is None:
            raise PreventUpdate
        s, e = int(vs), int(ve)
        if s > e:
            s, e = e, s
        if cur == [s, e]:
            raise PreventUpdate
        return [s, e]

    # 4) Synchronisation Slider → Dropdown (Zone graphe)
    @app.callback(
        Output("time-start-dd", "value"),
        Output("time-end-dd", "value"),
        Input("time-range-slider", "value"),
    )
    def time_slider_to_dd(val):
        if not val:
            return None, None
        s, e = int(val[0]), int(val[1])
        return s, e

    # 5) Synchronisation Dropdown (Début/Fin) → Slider (Zone KPI delta)
    @app.callback(
        Output("delta-range", "value"),
        Input("delta-start-dd", "value"),
        Input("delta-end-dd", "value"),
        State("delta-range", "value"),
        prevent_initial_call=True,
    )
    def delta_dd_to_slider(vs, ve, cur):
        if vs is None or ve is None:
            raise PreventUpdate
        s, e = int(vs), int(ve)
        if s > e:
            s, e = e, s
        if cur == [s, e]:
            raise PreventUpdate
        return [s, e]

    # 6) Synchronisation Slider → Dropdown (Zone KPI delta)
    @app.callback(
        Output("delta-start-dd", "value"),
        Output("delta-end-dd", "value"),
        Input("delta-range", "value"),
    )
    def delta_slider_to_dd(val):
        if not val:
            return None, None
        s, e = int(val[0]), int(val[1])
        return s, e

    # 7) Graphe d’évolution + KPI delta
    @app.callback(
        Output("cmp-graph", "figure"),
        Output("time-kpi-wrap", "children"),
        Input("time-range-slider", "value"),
        Input("delta-range", "value"),
        Input("pole-dd", "value"),
        Input("entite-dd", "value"),
        Input({"t": "time-col", "idx": ALL}, "value"),
        Input({"t": "time-val", "idx": ALL}, "value"),
        Input("kpi-choices", "value"),
        Input("theme", "data"),
        State("schema-store", "data"),
    )
    def evolution_temporelle(graph_range_idxs, delta_range_idxs,
                             pole, ent, all_cols, all_vals, kpi_sel, theme, schema):
        schema = schema or {}
        cat_lbl = schema.get("labels", {})

        file_list = data_manager.get_file_list()
        if not file_list:
            raise PreventUpdate

        # Helper pour libellé période
        def _lbl(fp: str) -> str:
            d = file_to_dt(fp)
            return dt_long_fr(d) if d else os.path.basename(fp)

        # ========== KPI : entre début et fin de delta-range ==========
        k_start, k_end = map(int, delta_range_idxs)
        k_paths = file_list[k_start: k_end + 1]
        df_prev = get_df(k_paths[0]).copy()
        df_curr = get_df(k_paths[-1]).copy()

        # Appliquer périmètre + filtres (on ignore volontairement le filtre 1 pour KPI)
        def _apply(df: pd.DataFrame) -> pd.DataFrame:
            d = df.copy()
            if pole and pole != "Tout" and "CAT1" in d.columns:
                d = d[d["CAT1"] == pole]
            if ent and ent != "Tout" and "PERIMETRE" in d.columns:
                d = d[d["PERIMETRE"] == ent]
            for c, v in zip(all_cols[1:], all_vals[1:]):
                if c and v:
                    d = d[d[c].isin(v)]
            return d

        df_prev = _apply(df_prev)
        df_curr = _apply(df_curr)

        kpi = compute_kpi_delta(df_prev, df_curr)

        start_lbl = _lbl(k_paths[0])
        end_lbl = _lbl(k_paths[-1])
        period_txt = f"entre {start_lbl} et {end_lbl}"

        META = {
            "Δ_effectif_%":         ("de collaborateurs", "kpi-yellow"),
            "Δ_parité_F_%":         ("de femmes dans la sélection", "kpi-violet"),
            "Δ_age_moyen_%":        ("d'âge moyen", "kpi-cyan"),
            "Δ_alternants_%":       ("d'alternants", "kpi-pink"),
            "Δ_proches_retraite_%": ("de personnes de 60 ans et +", "kpi-orange"),
        }

        kpi_sel = (kpi_sel or [])[:4]
        kpi_cards = []
        for key in kpi_sel:
            val = kpi.get(key)
            if val is None:
                # Quand le dénominateur initial est nul (division par 0)
                display = "N/A"
            else:
                display = f"{val:+.1f} %".replace(".", ",")
            label, css = META.get(key, ("Indicateur", "kpi-blue"))
            kpi_cards.append(make_kpi_tile(display, f"{label} {period_txt}", css))

        # ========== GRAPHE d’évolution : séries sur time-range ==========
        g_start, g_end = map(int, graph_range_idxs)
        g_paths = file_list[g_start: g_end + 1]

        col1 = all_cols[0] if all_cols else None
        vals1 = all_vals[0] if all_vals else []

        series_dict: Dict[str, List[int]] = {}
        labels: List[str] = []

        for path in g_paths:
            d0 = get_df(path).copy()

            # périmètre
            if pole and pole != "Tout" and "CAT1" in d0.columns:
                d0 = d0[d0["CAT1"] == pole]
            if ent and ent != "Tout" and "PERIMETRE" in d0.columns:
                d0 = d0[d0["PERIMETRE"] == ent]

            # filtres 2 → 5 pour la série (on ignore le 1er pour cohérence)
            for c, v in zip(all_cols[1:], all_vals[1:]):
                if c and v:
                    d0 = d0[d0[c].isin(v)]

            if not col1:
                series_dict.setdefault("Effectif total", []).append(len(d0))
            else:
                # si des valeurs ont été choisies pour col1, on les respecte
                if vals1:
                    cats = vals1
                else:
                    cats = sorted(d0[col1].dropna().unique())
                for cat in cats:
                    series_dict.setdefault(str(cat), []).append((d0[col1] == cat).sum())

            dfile = file_to_dt(path)
            labels.append(dt_long_fr(dfile) if dfile else os.path.basename(path))

        # Construction de la figure
        fig = go.Figure()
        for cat, serie in series_dict.items():
            fig.add_trace(go.Scatter(
                x=labels, y=serie,
                mode="lines+markers+text",
                name=cat,
                text=[f"{int(v):,}".replace(",", " ") for v in serie],
                textposition="top center",
            ))

        # Titre
        if col1:
            titre = f"Évolution – {cat_lbl.get(col1, col1)}"
            if vals1:
                titre += f" ({', '.join(map(str, vals1))})"
        else:
            titre = "Évolution des effectifs"

        titre += f" | {start_lbl} → {end_lbl}"

        fig.update_layout(
            title=titre,
            xaxis_title="Période",
            yaxis_title="Effectifs",
            hovermode="x unified",
            legend_title_text=cat_lbl.get(col1, "") if col1 else "",
        )
        fig = apply_theme_template(fig, theme)
        fig = add_labels(fig, mode="count")

        return fig, kpi_cards

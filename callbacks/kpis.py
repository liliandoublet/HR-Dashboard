# callbacks/kpis.py
from __future__ import annotations

import datetime as dt
from typing import Any, Dict

import pandas as pd
from dash import Input, Output, State, html, no_update, ctx
from dash.exceptions import PreventUpdate

from services.data_manager import get_df


# ───────────────────────── Helpers UI (tuiles) ─────────────────────────

def make_kpi(value, label, css_class):
    # formatage milliers si numérique
    if isinstance(value, (int, float)):
        display = f"{value:,}".replace(",", "\u202f")
    else:
        display = str(value)
    return html.Div(
        children=[
            html.Span(display, className="value"),
            html.Span(label, className="text-sub")
        ],
        className=f"kpi-tile {css_class}"
    )

def make_kpi_toggle(id_, value, label, css_class):
    """
    Tuile KPI “toggle” (valeur qui alterne au clic).
    id_ est un dict de Pattern-Matching: {"role":"kpi","metric":"age"} etc.
    """
    metric = id_["metric"] if isinstance(id_, dict) else id_
    return html.Div(
        id=id_,
        className=f"kpi-tile kpi-click {css_class}",
        children=[
            html.Button(
                id={"role": "kpi-rotate", "metric": metric},
                n_clicks=0,
                className="kpi-rotate-btn",
                title="Changer les KPI",
            ),
            html.Span(value,  id={"role":"kpi-val","metric":metric}, className="value"),
            html.Span(label,  id={"role":"kpi-lbl","metric":metric}, className="text-sub"),
        ],
    )


# ───────────────────────── Calculs KPI ─────────────────────────

def _clean(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    if "STATUT" in d.columns:
        d["STATUT"] = d["STATUT"].astype(str).str.strip().str.upper()
    if "Sexe" in d.columns:
        sexe = d["Sexe"].astype(str).str.strip().str.upper()
        sexe = sexe.replace({
            "H":"M", "HOMME":"M", "HOMMES":"M",
            "FEMME":"F", "FEMMES":"F"
        })
        sexe = sexe.where(sexe.isin(["F","M"]))
        d["Sexe"] = sexe
    return d

def pct_genre_parmi_les_cadres(df: pd.DataFrame, g: str) -> str:
    d = _clean(df)
    if "STATUT" not in d.columns or "Sexe" not in d.columns:
        return "N/A"
    mask_cadre = d["STATUT"].eq("CADRE")
    denom = d.loc[mask_cadre, "Sexe"].isin(["F","M"]).sum()
    if denom == 0:
        return "N/A"
    num = (d.loc[mask_cadre, "Sexe"] == g.upper()).sum()
    return f"{100 * num / denom:.1f} %".replace(".", ",")

def compute_kpi(df: pd.DataFrame) -> Dict[str, Any]:
    d = df.copy()
    if "ANCIENNETE" not in d.columns and "ENTREE_AN" in d.columns:
        an = pd.to_numeric(d["ENTREE_AN"], errors="coerce")
        d["ANCIENNETE"] = dt.date.today().year - an

    get = lambda c: d[c] if c in d.columns else pd.Series(dtype=float)

    return {
        "age": {
            "mean":   f"{get('AGE').mean():.1f} ans".replace(".", ","),
            "median": f"{get('AGE').median():.1f} ans".replace(".", ","),
        },
        "anciennete": {
            "mean":   f"{d['ANCIENNETE'].mean():.1f} ans".replace(".", ","),
            "median": f"{d['ANCIENNETE'].median():.1f} ans".replace(".", ","),
        },
        "pct_femmes": {
            "femmes": f"{100*(get('Sexe')=='F').mean():.1f} %".replace(".", ","),
            "hommes": f"{100*(get('Sexe')=='M').mean():.1f} %".replace(".", ","),
        },
        "stag_alt": f"{(get('EMPLOIS')=='Apprenti').sum()}".replace(".", ","),
        "pct_part_time": {
            "part": f"{100*(get('TRANCHE_PCT_TRAV')!='TEMPS PLEIN').mean():.1f} %".replace(".", ","),
            "full": f"{100*(get('TRANCHE_PCT_TRAV')=='TEMPS PLEIN').mean():.1f} %".replace(".", ","),
        },
        "pct_cadres": f"{100*(get('STATUT')=='CADRE').mean():.1f} %".replace(".", ","),
        "pct_cadres_f": {
            "femmes": pct_genre_parmi_les_cadres(d, 'F').replace(".", ","),
            "hommes": pct_genre_parmi_les_cadres(d, 'M').replace(".", ","),
        },
        "near_retire": f"{(get('AGE')>=60).sum()}".replace(".", ","),
    }


# ───────────────────────── Callbacks ─────────────────────────

def register_callbacks(app):
    """
    Callbacks KPI :
      - update_kpis : rend jusqu'à 4 tuiles KPI selon la sélection
      - toggle_kpi_generic : alterne la valeur/étiquette d’une tuile KPI au clic
    """

    @app.callback(
        Output("kpi-wrap", "children"),
        Input("file-dd",   "value"),
        Input("pole-dd",   "value"),
        Input("entite-dd", "value"),
        Input("basic-kpi-choices", "value"),
    )
    def update_kpis(file_path, pole, ent, selected):
        if isinstance(file_path, list):
            file_path = file_path[0]

        df = get_df(file_path).copy()
        if not df.empty:
            if pole and pole != "Tout" and "CAT1" in df.columns:
                df = df[df["CAT1"] == pole]
            if ent and ent != "Tout" and "PERIMETRE" in df.columns:
                df = df[df["PERIMETRE"] == ent]

        kpi = compute_kpi(df)
        selected = (selected or [])[:4]

        def tile_for(key: str):
            if key == "age":
                return make_kpi_toggle({"role":"kpi","metric":"age"},
                                       kpi["age"]["mean"], "Âge moyen", "kpi-yellow")
            if key == "anciennete":
                return make_kpi_toggle({"role":"kpi","metric":"anciennete"},
                                       kpi["anciennete"]["mean"], "Ancienneté moyenne", "kpi-cyan")
            if key == "pct_femmes":
                return make_kpi_toggle({"role":"kpi","metric":"pct_femmes"},
                                       kpi["pct_femmes"]["femmes"], "de femmes", "kpi-violet")
            if key == "stag_alt":
                return make_kpi(kpi["stag_alt"], "Alternants", "kpi-pink")
            if key == "pct_part_time":
                return make_kpi_toggle({"role":"kpi","metric":"pct_part_time"},
                                       kpi["pct_part_time"]["part"], "à temps partiel", "kpi-orange")
            if key == "pct_cadres":
                return make_kpi(kpi["pct_cadres"], "de cadres", "kpi-blue")
            if key == "pct_cadres_f":
                return make_kpi_toggle({"role":"kpi","metric":"pct_cadres_f"},
                                       kpi["pct_cadres_f"]["femmes"], "de cadres femmes", "kpi-raspberry")
            if key == "near_retire":
                return make_kpi(kpi["near_retire"], "personnes de plus de 60 ans", "kpi-electric")

        return [tile_for(k) for k in selected if tile_for(k) is not None]

    @app.callback(
        Output({"role":"kpi-val","metric":"age"}, "children"),
        Output({"role":"kpi-lbl","metric":"age"}, "children"),
        Output({"role":"kpi-rotate","metric":"age"}, "className"),
        Input({"role":"kpi-rotate","metric":"age"}, "n_clicks"),
        Input({"role":"kpi","metric":"age"}, "n_clicks"),
        State("file-dd", "value"),
        State("pole-dd", "value"),
        State("entite-dd", "value"),
        prevent_initial_call=False
    )
    def toggle_kpi_age(btn_clicks, tile_clicks, file_path, pole, ent):
        n = (btn_clicks or 0) + (tile_clicks or 0)
        trig = ctx.triggered_id
        spin_cls = "kpi-rotate-btn is-spinning" if isinstance(trig, dict) and trig.get("role") == "kpi-rotate" else "kpi-rotate-btn"

        if isinstance(file_path, list):
            file_path = file_path[0]
        d = get_df(file_path).copy()
        if pole and pole != "Tout" and "CAT1" in d.columns: d = d[d["CAT1"] == pole]
        if ent and ent != "Tout" and "PERIMETRE" in d.columns: d = d[d["PERIMETRE"] == ent]

        is_median = (n % 2 == 1)
        val = d["AGE"].median() if is_median and "AGE" in d.columns else d["AGE"].mean()
        lbl = f"Âge {'médian' if is_median else 'moyen'}"
        return f"{val:.1f} ans".replace(".", ","), lbl, spin_cls

    @app.callback(
        Output({"role":"kpi-val","metric":"anciennete"}, "children"),
        Output({"role":"kpi-lbl","metric":"anciennete"}, "children"),
        Output({"role":"kpi-rotate","metric":"anciennete"}, "className"),
        Input({"role":"kpi-rotate","metric":"anciennete"}, "n_clicks"),
        Input({"role":"kpi","metric":"anciennete"}, "n_clicks"),
        State("file-dd", "value"),
        State("pole-dd", "value"),
        State("entite-dd", "value"),
        prevent_initial_call=False
    )
    def toggle_kpi_anciennete(btn_clicks, tile_clicks, file_path, pole, ent):
        n = (btn_clicks or 0) + (tile_clicks or 0)
        trig = ctx.triggered_id
        spin_cls = "kpi-rotate-btn is-spinning" if isinstance(trig, dict) and trig.get("role") == "kpi-rotate" else "kpi-rotate-btn"

        if isinstance(file_path, list):
            file_path = file_path[0]
        d = get_df(file_path).copy()
        if pole and pole != "Tout" and "CAT1" in d.columns: d = d[d["CAT1"] == pole]
        if ent and ent != "Tout" and "PERIMETRE" in d.columns: d = d[d["PERIMETRE"] == ent]

        if "ANCIENNETE" not in d.columns and "ENTREE_AN" in d.columns:
            an = pd.to_numeric(d["ENTREE_AN"], errors="coerce")
            d["ANCIENNETE"] = dt.date.today().year - an

        is_median = (n % 2 == 1)
        val = d["ANCIENNETE"].median() if is_median else d["ANCIENNETE"].mean()
        lbl = f"Ancienneté {'médiane' if is_median else 'moyenne'}"
        return f"{val:.1f} ans".replace(".", ","), lbl, spin_cls

    @app.callback(
        Output({"role":"kpi-val","metric":"pct_femmes"}, "children"),
        Output({"role":"kpi-lbl","metric":"pct_femmes"}, "children"),
        Output({"role":"kpi-rotate","metric":"pct_femmes"}, "className"),
        Input({"role":"kpi-rotate","metric":"pct_femmes"}, "n_clicks"),
        Input({"role":"kpi","metric":"pct_femmes"}, "n_clicks"),
        State("file-dd", "value"),
        State("pole-dd", "value"),
        State("entite-dd", "value"),
        prevent_initial_call=False
    )
    def toggle_kpi_pct_femmes(btn_clicks, tile_clicks, file_path, pole, ent):
        n = (btn_clicks or 0) + (tile_clicks or 0)
        trig = ctx.triggered_id
        spin_cls = "kpi-rotate-btn is-spinning" if isinstance(trig, dict) and trig.get("role") == "kpi-rotate" else "kpi-rotate-btn"

        if isinstance(file_path, list):
            file_path = file_path[0]
        d = get_df(file_path).copy()
        if pole and pole != "Tout" and "CAT1" in d.columns: d = d[d["CAT1"] == pole]
        if ent and ent != "Tout" and "PERIMETRE" in d.columns: d = d[d["PERIMETRE"] == ent]

        show_h = (n % 2 == 1)
        if "Sexe" not in d.columns or d.empty:
            return "N/A", ("d'hommes" if show_h else "de femmes"), spin_cls

        pct = 100 * d["Sexe"].eq("M" if show_h else "F").mean()
        lbl = "d'hommes" if show_h else "de femmes"
        return f"{pct:.1f} %".replace(".", ","), lbl, spin_cls

    @app.callback(
        Output({"role":"kpi-val","metric":"pct_part_time"}, "children"),
        Output({"role":"kpi-lbl","metric":"pct_part_time"}, "children"),
        Output({"role":"kpi-rotate","metric":"pct_part_time"}, "className"),
        Input({"role":"kpi-rotate","metric":"pct_part_time"}, "n_clicks"),
        Input({"role":"kpi","metric":"pct_part_time"}, "n_clicks"),
        State("file-dd", "value"),
        State("pole-dd", "value"),
        State("entite-dd", "value"),
        prevent_initial_call=False
    )
    def toggle_kpi_pct_part_time(btn_clicks, tile_clicks, file_path, pole, ent):
        n = (btn_clicks or 0) + (tile_clicks or 0)
        trig = ctx.triggered_id
        spin_cls = "kpi-rotate-btn is-spinning" if isinstance(trig, dict) and trig.get("role") == "kpi-rotate" else "kpi-rotate-btn"

        if isinstance(file_path, list):
            file_path = file_path[0]
        d = get_df(file_path).copy()
        if pole and pole != "Tout" and "CAT1" in d.columns: d = d[d["CAT1"] == pole]
        if ent and ent != "Tout" and "PERIMETRE" in d.columns: d = d[d["PERIMETRE"] == ent]

        show_full = (n % 2 == 1)
        if "TRANCHE_PCT_TRAV" not in d.columns or d.empty:
            return "N/A", ("à temps plein" if show_full else "à temps partiel"), spin_cls

        if show_full:
            pct = 100 * (d["TRANCHE_PCT_TRAV"] == "TEMPS PLEIN").mean()
            lbl = "à temps plein"
        else:
            pct = 100 * (d["TRANCHE_PCT_TRAV"] != "TEMPS PLEIN").mean()
            lbl = "à temps partiel"
        return f"{pct:.1f} %".replace(".", ","), lbl, spin_cls

    @app.callback(
        Output({"role":"kpi-val","metric":"pct_cadres_f"}, "children"),
        Output({"role":"kpi-lbl","metric":"pct_cadres_f"}, "children"),
        Output({"role":"kpi-rotate","metric":"pct_cadres_f"}, "className"),
        Input({"role":"kpi-rotate","metric":"pct_cadres_f"}, "n_clicks"),
        Input({"role":"kpi","metric":"pct_cadres_f"}, "n_clicks"),
        State("file-dd", "value"),
        State("pole-dd", "value"),
        State("entite-dd", "value"),
        prevent_initial_call=False
    )
    def toggle_kpi_pct_cadres_f(btn_clicks, tile_clicks, file_path, pole, ent):
        n = (btn_clicks or 0) + (tile_clicks or 0)
        trig = ctx.triggered_id
        spin_cls = "kpi-rotate-btn is-spinning" if isinstance(trig, dict) and trig.get("role") == "kpi-rotate" else "kpi-rotate-btn"

        if isinstance(file_path, list):
            file_path = file_path[0]
        d = get_df(file_path).copy()
        if pole and pole != "Tout" and "CAT1" in d.columns: d = d[d["CAT1"] == pole]
        if ent and ent != "Tout" and "PERIMETRE" in d.columns: d = d[d["PERIMETRE"] == ent]

        show_h = (n % 2 == 1)
        g = "M" if show_h else "F"

        d = _clean(d)
        if "STATUT" not in d.columns or "Sexe" not in d.columns:
            return "N/A", ("de cadres hommes" if show_h else "de cadres femmes"), spin_cls

        mask_cadre = d["STATUT"].eq("CADRE")
        sexe_cadres = d.loc[mask_cadre, "Sexe"]
        denom = sexe_cadres.isin(["F", "M"]).sum()
        lbl = "de cadres hommes" if show_h else "de cadres femmes"
        if denom == 0:
            return "N/A", lbl, spin_cls
        num = (sexe_cadres == g).sum()
        pct = 100 * num / denom
        return f"{pct:.1f} %".replace(".", ","), lbl, spin_cls

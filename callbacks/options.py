# callbacks/options.py
from __future__ import annotations

import os
import re
import datetime as dt
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
from dash import Input, Output, State, no_update
from dash.dependencies import MATCH, ALL
from dash.exceptions import PreventUpdate

from services.data_manager import get_df
from config.settings import DATE_REGEX
from services.schema_services import build_schema



DATE_PAT = re.compile(DATE_REGEX)


# ───────────────────────────── Dates & libellés fichiers (utilitaires) ─────────────────────────────
# Conservés au cas où ils seraient réutilisés ailleurs ; ils ne sont plus appelés ici.

def file_to_dt(path: str) -> Optional[dt.date]:
    """Renvoie la date (objet date) extraite d'un nom de fichier …_AAAAMMJJ.xlsx, ou None."""
    m = DATE_PAT.search(os.path.basename(path))
    if not m:
        return None
    return dt.datetime.strptime(m.group(1), "%Y%m%d").date()

def dt_short_fr(d: dt.date) -> str:
    """2025-06-30 → '06/2025'."""
    return f"{d.month:02d}/{d.year}"

def _label_for_index(file_list: List[str], i: int) -> str:
    """Libellé court pour index de fichier (MM/AAAA si dispo, sinon nom)."""
    try:
        fp = file_list[i]
    except Exception:
        return str(i)
    d = file_to_dt(fp)
    return dt_short_fr(d) if d else os.path.basename(fp)

def make_sparse_marks(file_list: List[str], k: int = 6) -> Dict[int, str]:
    """
    Réduit le nombre de marks pour un slider long (≤ k labels).
    Garde 0, n-1 et (k-2) positions espacées.
    """
    n = len(file_list)
    if n <= 0:
        return {}
    if n <= k:
        return {i: _label_for_index(file_list, i) for i in range(n)}
    idxs = sorted(set([0, n - 1] + [int(round(x)) for x in np.linspace(0, n - 1, k - 2)]))
    return {i: _label_for_index(file_list, i) for i in idxs}


# ───────────────────────────── Entités par pôle ─────────────────────────────

def _dd_entites(df: pd.DataFrame, pole_val: str) -> List[Dict[str, str]]:
    """Construit les options d'entités à partir du DataFrame courant et d’un pôle."""
    if "PERIMETRE" not in df.columns or "CAT1" not in df.columns:
        return [{"label": "Tout", "value": "Tout"}]
    if pole_val and pole_val != "Tout":
        df = df[df["CAT1"] == pole_val]
    entites = sorted(v for v in df["PERIMETRE"].dropna().unique())
    opts = [{"label": "Tout", "value": "Tout"}] + [{"label": e, "value": e} for e in entites]
    return opts


# ───────────────────────────── Axes numériques scatter/bubble ─────────────────────────────

def _ensure_derived_numeric_cols(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    if "ANCIENNETE" not in d.columns and "ENTREE_AN" in d.columns:
        an = pd.to_numeric(d["ENTREE_AN"], errors="coerce")
        d["ANCIENNETE"] = dt.date.today().year - an
    if "SALAIRE_ETP_NUM" not in d.columns and "Salaire Annuel ETP" in d.columns:
        d["SALAIRE_ETP_NUM"] = pd.to_numeric(
            d["Salaire Annuel ETP"].astype(str).str.replace(r"\s", "", regex=True).str.replace(",", "."),
            errors="coerce"
        )
    return d

def scatter_numeric_cols(df: pd.DataFrame,
                         allowed: Optional[List[str]] = None,
                         excluded: Optional[List[str]] = None,
                         min_ratio: float = 0.9) -> List[str]:
    """
    Colonnes NUMÉRIQUES autorisées pour X/Y/Taille.
    - allowed : liste blanche (si fournie depuis schema-store)
    - excluded : colonnes à exclure
    - min_ratio : tolérance de conversion numérique via to_numeric (≥ min_ratio non-NaN)
    """
    d = _ensure_derived_numeric_cols(df)
    excl = set(excluded or [])
    base = list(allowed) if allowed else list(d.columns)

    kept: List[str] = []
    for c in base:
        if c in excl:
            continue
        if c not in d.columns:
            continue
        s = d[c]
        if pd.api.types.is_numeric_dtype(s):
            kept.append(c)
        else:
            s_num = pd.to_numeric(s, errors="coerce")
            if s_num.notna().mean() >= min_ratio:
                kept.append(c)

    # Ordre sympa : prioriser ces colonnes si présentes
    priority = ["AGE", "ANCIENNETE", "SALAIRE_ETP_NUM", "AGE_ENTREE", "ENTREE_AN"]
    ordered = [c for c in priority if c in kept] + [c for c in kept if c not in priority]
    # dédoublonnage (au cas où)
    seen, out = set(), []
    for c in ordered:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out


# ───────────────────────────── Options de colonnes (SIMP / VIZ) ─────────────────────────────

def _labels_from_store(schema: Optional[dict]) -> Dict[str, str]:
    return (schema or {}).get("labels", {})

def _cats_from_store(schema: Optional[dict], key: str, fallback: Optional[List[str]] = None) -> List[str]:
    """
    Récupère une liste de catégories depuis schema-store.
    Clés possibles suggérées : 'CATEGORIES_SIMP', 'CATEGORIES_VIZ', etc.
    """
    if not isinstance(schema, dict):
        return fallback or []
    return list(schema.get(key, fallback or []))


# ───────────────────────────── Enregistrement des callbacks ─────────────────────────────

def register_callbacks(app):

    # 0) Construire le schéma (labels + listes de catégories) à chaque changement de fichier
    @app.callback(
        Output("schema-store", "data"),
        Input("file-dd", "value"),
        prevent_initial_call=False
    )
    def refresh_schema(file_path):
        if isinstance(file_path, list):
            file_path = file_path[0]
        df = get_df(file_path)
        return build_schema(df)

    # 1) Entités par pôle (et fichier courant)
    @app.callback(
        Output("entite-dd", "options"),
        Input("file-dd", "value"),
        Input("pole-dd", "value"),
        prevent_initial_call=False
    )
    def upd_entites(file_path, pole_val):
        if isinstance(file_path, list):
            file_path = file_path[0]
        df = get_df(file_path)
        return _dd_entites(df, pole_val or "Tout")
    # 1bis) Global tab: fill column options
    @app.callback(
        Output("global-data-dd", "options"),
        Input("schema-store", "data"),
        prevent_initial_call=False
    )
    def fill_global_cols(schema):
        schema = schema or {}
        labels = schema.get("labels", {})
        cols = schema.get("CATEGORIES_GLOBAL", [])
        opts = [{"label": "-- Aucun filtre --", "value": ""}]
        opts += [{"label": labels.get(c, c), "value": c} for c in cols]
        return opts

    # 1ter) Time tab: feed time-col dropdowns (1..5)
    @app.callback(
        Output({"t": "time-col", "idx": ALL}, "options"),
        Input("schema-store", "data"),
        prevent_initial_call=False
    )
    def fill_time_cols(schema):
        schema = schema or {}
        labels = schema.get("labels", {})
        cats = schema.get("CATEGORIES_CMP", [])
        opts = [{"label": labels.get(c, c), "value": c} for c in cats]
        return [opts] * 5

    # 2) Simp: désactiver dans chaque liste la valeur déjà choisie dans l’autre
    @app.callback(
        Output("simp-col2", "options"),
        Output("simp-col1", "options"),
        Input("simp-col1", "value"),
        Input("simp-col2", "value"),
        Input("schema-store", "data"),
        prevent_initial_call=False
    )
    def update_dropdown_options(col1, col2, schema):
        cat_lbl = _labels_from_store(schema)
        cats = _cats_from_store(schema, "CATEGORIES_SIMP", [])
        def make_opts(exclude):
            return [
                {
                    "label": cat_lbl.get(c, c),
                    "value": c,
                    "disabled": (c == exclude)
                }
                for c in cats
            ]
        return make_opts(col1), make_opts(col2)

    # 3) VIZ: désactiver les colonnes déjà choisies + exclure pour treemap
    @app.callback(
        Output({"t": "viz-col", "idx": ALL}, "options"),
        Input({"t": "viz-col", "idx": ALL}, "value"),
        Input("viz-type", "value"),
        Input("schema-store", "data"),
        prevent_initial_call=False
    )
    def disable_chosen_cols(chosen, gtype, schema):
        cat_lbl = _labels_from_store(schema)
        cats_viz = _cats_from_store(schema, "CATEGORIES_VIZ", [])
        treemap_excl = set(_cats_from_store(schema, "TREEMAP_EXCLUDED_COLS", []))

        chosen_set = {c for c in chosen if c}
        opts = []
        for _ in chosen:
            lst = []
            for c in cats_viz:
                if gtype == "treemap" and c in treemap_excl:
                    continue
                lst.append({
                    "label": cat_lbl.get(c, c),
                    "value": c,
                    "disabled": (c in chosen_set)
                })
            opts.append(lst)
        return opts

    # 4) VIZ: remplir la liste des valeurs disponibles pour la colonne choisie
    @app.callback(
        Output({"t": "viz-val", "idx": MATCH}, "options"),
        Input("file-dd", "value"),
        Input({"t": "viz-col", "idx": MATCH}, "value"),
        Input({"t": "viz-col", "idx": ALL}, "value"),
        Input({"t": "viz-val", "idx": ALL}, "value"),
        Input("pole-dd", "value"),
        Input("entite-dd", "value"),
        Input("viz-compare-mode", "value"),
        Input("viz-cmp-pole-dd", "value"),
        Input("viz-cmp-ent-dd", "value"),
        State({"t": "viz-val", "idx": MATCH}, "value"),
        State({"t": "viz-val", "idx": MATCH}, "id"),
        prevent_initial_call=True
    )
    def update_value_dd(file_path, col_this, all_cols, all_vals,
                        pole, ent, cmp_mode, cmp_pole, cmp_ent,
                        current_selection, this_id):
        if not col_this:
            return []
        if isinstance(file_path, list):
            file_path = file_path[0]

        # DF principal (périmètre sélectionné)
        d_main = get_df(file_path).copy()
        if pole and pole != "Tout":
            d_main = d_main[d_main.get("CAT1") == pole]
        if ent and ent != "Tout":
            d_main = d_main[d_main.get("PERIMETRE") == ent]

        # Appliquer les filtres précédents (index < idx courant)
        idx_this = this_id["idx"]  # 1..n
        for idx_loop, (c, v) in enumerate(zip(all_cols, all_vals), start=1):
            if idx_loop >= idx_this:
                break
            if c and v:
                d_main = d_main[d_main[c].isin(v)]

        # Si comparaison : construire d_cmp et unir pour les options
        if "ON" in (cmp_mode or []):
            d_cmp = get_df(file_path).copy()
            if cmp_pole and cmp_pole != "Tout":
                d_cmp = d_cmp[d_cmp.get("CAT1") == cmp_pole]
            if cmp_ent and cmp_ent != "Tout":
                d_cmp = d_cmp[d_cmp.get("PERIMETRE") == cmp_ent]
            for idx_loop, (c, v) in enumerate(zip(all_cols, all_vals), start=1):
                if idx_loop >= idx_this:
                    break
                if c and v:
                    d_cmp = d_cmp[d_cmp[c].isin(v)]
            d_opt = pd.concat([d_main, d_cmp], ignore_index=True)
        else:
            d_opt = d_main

        if col_this not in d_opt.columns:
            return []

        vc = d_opt[col_this].value_counts().sort_index()
        options = [{"label": f"{val} — {cnt}", "value": val} for val, cnt in vc.items() if cnt > 0]

        # Si la sélection courante est encore valide, on la garde
        if current_selection:
            valid = {opt["value"] for opt in options}
            if all(sel in valid for sel in current_selection):
                return options

        return options

    # 5) Axes numériques pour scatter/bubble
    @app.callback(
        Output("simp-x", "options"),
        Output("simp-x", "value"),
        Output("simp-y", "options"),
        Output("simp-y", "value"),
        Output("simp-size", "options"),
        Output("simp-size", "value"),
        Input("file-dd", "value"),
        State("simp-x", "value"),
        State("simp-y", "value"),
        State("simp-size", "value"),
        State("schema-store", "data"),
        prevent_initial_call=False
    )
    def fill_numeric_axes(file_path, x_cur, y_cur, size_cur, schema):
        if isinstance(file_path, list):
            file_path = file_path[0]
        d = get_df(file_path)

        # liste blanche + exclusions depuis schema-store si fournis
        allowed = _cats_from_store(schema, "SCATTER_ALLOWED_COLS", None)
        excluded = _cats_from_store(schema, "SCATTER_EXCLUDED_COLS", ["Matricule", "Date_de_Naissance", "Date_Affection_Unité", "Salaire Annuel", "Salaire Annuel ETP"])

        numeric_cols = scatter_numeric_cols(d, allowed=allowed, excluded=excluded)
        opts_xy = [{"label": schema.get("labels", {}).get(c, c) if schema else c, "value": c} for c in numeric_cols]

        # Taille: ajouter l’option de comptage
        opts_size = [{"label": "Effectifs (comptage)", "value": "__COUNT__"}] + opts_xy

        x_val = x_cur if x_cur in numeric_cols else None
        y_val = y_cur if y_cur in numeric_cols else None
        s_val = size_cur if (size_cur in numeric_cols or size_cur == "__COUNT__") else "__COUNT__"

        return opts_xy, x_val, opts_xy, y_val, opts_size, s_val

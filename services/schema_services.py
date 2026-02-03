# services/schema_service.py
from __future__ import annotations
import datetime as dt
import pandas as pd
from pandas.api.types import is_numeric_dtype
from typing import TypedDict, List, Dict, Any

from config.column_rules import (
    GLOBAL_HIDDEN_COLS, VIS_HIDDEN_COLS, ANALYS_HIDDEN_COLS,
    COMPA_HIDDEN_COLS, TREEMAP_EXCLUDED_COLS, SCATTER_EXCLUDED_COLS,
    cat_lbl
)

class Schema(TypedDict):
    all_cols: List[str]
    labels: Dict[str, str]
    # listes “dynamiques” en fonction du fichier
    CATEGORIES_GLOBAL: List[str]
    CATEGORIES_SIMP: List[str]
    CATEGORIES_VIZ: List[str]
    CATEGORIES_CMP: List[str]
    numeric_candidates: List[str]   # pour scatter/bubble
    # info de périmètre
    effectifs_cat1: Dict[str, int]
    cat1_to_perim: Dict[str, List[str]]

def _ensure_derived_numeric_cols(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    if "ANCIENNETE" not in d.columns and "ENTREE_AN" in d.columns:
        an = pd.to_numeric(d["ENTREE_AN"], errors="coerce")
        d["ANCIENNETE"] = dt.date.today().year - an
    if "SALAIRE_ETP_NUM" not in d.columns and "Salaire Annuel ETP" in d.columns:
        d["SALAIRE_ETP_NUM"] = pd.to_numeric(
            d["Salaire Annuel ETP"].astype(str).str.replace(r"\s","",regex=True).str.replace(",","."), errors="coerce"
        )
    return d

def _numeric_candidates(df: pd.DataFrame) -> List[str]:
    d = _ensure_derived_numeric_cols(df)
    num_cols = [c for c in d.columns if is_numeric_dtype(d[c])]
    # Priorité sympa
    priority = ["AGE", "ANCIENNETE", "SALAIRE_ETP_NUM", "AGE_ENTREE", "ENTREE_AN"]
    out = [c for c in priority if c in num_cols] + [c for c in num_cols if c not in priority]
    out = [c for c in out if c not in SCATTER_EXCLUDED_COLS]
    # dédoublonnage
    seen = set(); ordered=[]
    for c in out:
        if c not in seen:
            ordered.append(c); seen.add(c)
    return ordered

def build_schema(df_clean: pd.DataFrame) -> Schema:
    all_cols = list(df_clean.columns)

    effectifs_cat1 = df_clean["CAT1"].value_counts().sort_index().to_dict() if "CAT1" in df_clean else {}
    cat1_to_perim = {}
    if {"CAT1","PERIMETRE"}.issubset(df_clean.columns):
        cat1_to_perim = (
            df_clean.groupby("CAT1")["PERIMETRE"].apply(lambda x: sorted(set(x))).to_dict()
        )

    def _filter(cols, banned):
        return [c for c in cols if c not in banned and c in all_cols]

    # colonnes candidates “catégorielles” = tout sauf numériques strictes ? On garde simple :
    categories = [c for c in all_cols if c not in {"Matricule"}]

    CATEGORIES_GLOBAL = _filter(categories, GLOBAL_HIDDEN_COLS)
    CATEGORIES_SIMP   = _filter(categories, VIS_HIDDEN_COLS)
    CATEGORIES_VIZ    = _filter(categories, ANALYS_HIDDEN_COLS)
    CATEGORIES_CMP    = _filter(categories, COMPA_HIDDEN_COLS)

    schema: Schema = {
        "all_cols": all_cols,
        "labels": cat_lbl,
        "CATEGORIES_GLOBAL": CATEGORIES_GLOBAL,
        "CATEGORIES_SIMP":   CATEGORIES_SIMP,
        "CATEGORIES_VIZ":    CATEGORIES_VIZ,
        "CATEGORIES_CMP":    CATEGORIES_CMP,
        "numeric_candidates": _numeric_candidates(df_clean),
        "effectifs_cat1": effectifs_cat1,
        "cat1_to_perim": cat1_to_perim,
    }
    return schema
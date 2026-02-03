# ui/components/graphs.py
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
from dash import dcc
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objects import Bar
from plotly.subplots import make_subplots

from services.template_services import apply_theme_template


# ──────────────────────────────── Helpers génériques ────────────────────────────────

def sort_categories(series: pd.Series, mode: str) -> pd.Series:
    """
    Trie une Series selon 'DESC' | 'ASC' | 'ALPHA' (par index, insensible à la casse).
    """
    if mode == "ALPHA":
        return series.sort_index(key=lambda s: s.astype(str).str.lower())
    return series.sort_values(ascending=(mode == "ASC"))


def make_title(base: str,
               pole: str = "Tout",
               ent: str = "Tout",
               col: str | None = None,
               total: int | None = None,
               cat_lbl: Optional[Dict[str, str]] = None) -> str:
    """
    Construit un titre standardisé : <base> [– <libellé col>] [ | <pôle>] [ / <entité>] [ - N collaborateurs]
    """
    txt = base
    if col:
        txt += f" – {(cat_lbl or {}).get(col, col)}"
    if pole and pole != "Tout":
        txt += f" | {pole}"
    if ent and ent != "Tout":
        txt += f" / {ent}"
    if total is not None:
        total_str = f"{total:,}".replace(",", "\u202f")
        txt += f" - {total_str} collaborateurs"
    return txt


def add_labels(fig: go.Figure, mode: str = "count", legend_total: int | None = None) -> go.Figure:
    """
    Ajoute des étiquettes aux traces d'une figure.
      - mode 'count' => valeurs entières
      - sinon        => pourcentages entiers (%)
    Gère bar/pie/treemap/scatter (texte au-dessus ou à l'intérieur).
    """
    SEP = "\u202F"
    for tr in fig.data:
        # choisir la séquence de valeurs à étiqueter
        if tr.type == "pie" and mode != "count":
            # pour les pie en % natifs, on garde le rendu par défaut
            continue
        if hasattr(tr, "y") and tr.y is not None:
            vals = list(tr.y)
        elif hasattr(tr, "values") and tr.values is not None:
            vals = list(tr.values)
        else:
            vals = []

        # formatage
        if mode == "count":
            tr.text = [f"{(0 if v is None else v):,.0f}".replace(",", SEP) for v in vals]
        else:
            tr.text = [f"{(0 if v is None else v):,.0f}".replace(",", SEP) + " %" for v in vals]

        # position
        if tr.type == "pie":
            tr.textposition = "inside"; tr.textinfo = "text"
        elif tr.type == "bar":
            tr.textposition = "inside"; tr.cliponaxis = False
        elif tr.type == "scatter":
            tr.textposition = "top center"; tr.cliponaxis = False
        elif tr.type == "treemap":
            tr.textposition = "middle center"
            tr.textinfo = "label+value+percent entry"

    if legend_total is not None:
        fig.update_layout(legend_title_text=f"{legend_total:,}".replace(",", SEP) + " collaborateurs")
    fig.update_xaxes(tickangle=-45, automargin=True)
    return fig


def graph_wrap(fig: go.Figure,
               *,
               class_name: str = "card",
               style: Optional[Dict[str, str]] = None,
               config: Optional[Dict] = None) -> dcc.Graph:
    """
    Enveloppe un go.Figure dans un dcc.Graph uniformisé.
    """
    return dcc.Graph(
        figure=fig,
        className=class_name,
        style=style or {"width": "100%", "height": "100%"},
        config=config or {"responsive": True},
    )


# ──────────────────────────────── Fabriques de figures ────────────────────────────────

def fig_bar(df: pd.DataFrame,
            x: str,
            y: str = "Val",
            *,
            title: Optional[str] = None,
            mode: str = "count",
            theme: str = "dark",
            legend_title: Optional[str] = None,
            category_orders: Optional[Dict[str, Sequence[str]]] = None,
            barmode: str = "stack") -> go.Figure:
    """
    Barres (stack/group simples). `mode` gère le rendu des labels (count/%).
    """
    fig = px.bar(df, x=x, y=y, category_orders=category_orders)
    if title:
        fig.update_layout(title=title)
    if legend_title is not None:
        fig.update_layout(legend_title_text=legend_title)
    if barmode:
        fig.update_layout(barmode=barmode)
    fig = apply_theme_template(fig, theme)
    return add_labels(fig, mode)


def fig_pie(df: pd.DataFrame,
            names: str,
            values: str = "Val",
            *,
            title: Optional[str] = None,
            theme: str = "dark",
            hole: float = .4,
            legend_horizontal: bool = True) -> go.Figure:
    """
    Donut / camembert.
    """
    fig = px.pie(df, names=names, values=values, hole=hole, title=title)
    fig = apply_theme_template(fig, theme)
    if legend_horizontal:
        fig.update_layout(
            legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
            margin=dict(b=120)
        )
    return fig


def fig_treemap(df: pd.DataFrame,
                path: Sequence[str],
                values: str = "Val",
                *,
                title: Optional[str] = None,
                theme: str = "dark",
                show_rich_text: bool = True) -> go.Figure:
    """
    Treemap interactif (path = hiérarchie).
    """
    fig = px.treemap(df, path=path, values=values, title=title)
    fig = apply_theme_template(fig, theme)
    if show_rich_text and fig.data:
        fig.data[0].texttemplate = "%{label}<br>%{value:,}"
        fig.data[0].textinfo = "label+value+percent parent+percent root"
    return fig


def fig_scatter(df: pd.DataFrame,
                x: str,
                y: str,
                *,
                color: Optional[str] = None,
                size: Optional[str] = None,
                title: Optional[str] = None,
                theme: str = "dark",
                hover_data: Optional[Sequence[str]] = None) -> go.Figure:
    """
    Nuage de points (scatter) classique. Pas d’add_labels automatique (reste lisible avec markers).
    """
    fig = px.scatter(df, x=x, y=y, color=color, size=size, hover_data=hover_data, title=title)
    fig.update_layout(xaxis_title=x, yaxis_title=y, legend_title_text=color or "")
    fig = apply_theme_template(fig, theme)
    return fig


def fig_bubble(df: pd.DataFrame,
               x: str,
               y: str,
               size: str,
               *,
               title: Optional[str] = None,
               theme: str = "dark",
               hover_data: Optional[Sequence[str]] = None,
               size_max: int = 60) -> go.Figure:
    """
    Scatter en bulles (taille basée sur une colonne numérique).
    """
    fig = px.scatter(df, x=x, y=y, size=size, size_max=size_max, hover_data=hover_data, title=title)
    fig.update_layout(xaxis_title=x, yaxis_title=y, legend_title_text=size)
    fig = apply_theme_template(fig, theme)
    return fig


def _natural_key(txt: str):
    import re
    return [int(x) if x.isdigit() else x.lower()
            for x in re.split(r"(\d+)", str(txt))]


def fig_multi_pies(df: pd.DataFrame,
                   group_col: str,
                   slice_col: str,
                   *,
                   order: str = "DESC",
                   title_prefix: Optional[str] = None,
                   theme: str = "dark",
                   cat_lbl: Optional[Dict[str, str]] = None) -> go.Figure:
    """
    Une rangée de donuts (un par groupe). Légende unique.
    `order` gère l’ordre des sous-figures : 'DESC'|'ASC'|'ALPHA'
    """
    # 1) ordre des sous-figures
    if order == "ALPHA":
        groups = sorted(df[group_col].dropna().unique(), key=_natural_key)
    else:
        vc = df[group_col].value_counts(ascending=(order == "ASC"))
        groups = list(vc.index)

    n = max(len(groups), 1)
    fig = make_subplots(rows=1, cols=n, specs=[[{"type": "domain"}] * n],
                        subplot_titles=[str(g) for g in groups] if groups else None)

    # 2) liste maître des parts
    all_cats = sorted(df[slice_col].dropna().unique(), key=_natural_key)

    # 3) tracés
    if groups:
        for i, g in enumerate(groups, start=1):
            vc = df[df[group_col] == g][slice_col].value_counts()
            values = [vc.get(cat, 0) for cat in all_cats]
            fig.add_trace(
                go.Pie(labels=all_cats, values=values, hole=.4, sort=False, showlegend=(i == 1)),
                row=1, col=i
            )

    label = (cat_lbl or {}).get(slice_col, slice_col)
    title = f"{title_prefix or 'Répartition'} – {label}"

    fig.update_traces(textinfo="percent+label", texttemplate="%{percent:.0%}")
    fig.update_layout(
        title_text=title,
        margin=dict(t=40, b=200),
        legend_title_text=label,
        legend=dict(orientation="v", x=1.02, xanchor="left", y=0.5),
        height=460
    )
    for ann in fig.layout.annotations or []:
        ann.update(y=-0.1, textangle=45, font=dict(size=10), yanchor="top")

    fig = apply_theme_template(fig, theme)
    return fig


# ──────────────────────────────── Aides “haut niveau” ────────────────────────────────

def fig_from_counts(series: pd.Series,
                    *,
                    kind: str = "bar",
                    mode: str = "count",
                    order: str = "DESC",
                    theme: str = "dark",
                    title: Optional[str] = None,
                    x_label: Optional[str] = None,
                    cat_name: Optional[str] = None) -> go.Figure:
    """
    À partir d’une Series (index=catégories, values=effectifs/%), produit une figure.
    """
    s = sort_categories(series, order)
    df = s.reset_index()
    cat = cat_name or series.index.name or "Catégorie"
    df.columns = [cat, "Val"]

    if kind == "pie":
        fig = fig_pie(df, names=cat, values="Val", title=title, theme=theme)
        return fig

    if kind == "treemap":
        fig = fig_treemap(df, path=[cat], values="Val", title=title, theme=theme)
        return add_labels(fig, mode)

    # défaut : bar
    fig = fig_bar(df, x=cat, y="Val", title=title, mode=mode, theme=theme, legend_title=cat)
    if x_label:
        fig.update_xaxes(title=x_label)
    return fig


# ──────────────────────────────── Exemples de wrappers UI ────────────────────────────────

def graph_bar(df: pd.DataFrame, x: str, y: str = "Val", **kwargs) -> dcc.Graph:
    return graph_wrap(fig_bar(df, x, y, **kwargs))

def graph_pie(df: pd.DataFrame, names: str, values: str = "Val", **kwargs) -> dcc.Graph:
    return graph_wrap(fig_pie(df, names, values, **kwargs))

def graph_treemap(df: pd.DataFrame, path: Sequence[str], values: str = "Val", **kwargs) -> dcc.Graph:
    return graph_wrap(fig_treemap(df, path, values, **kwargs))

def graph_scatter(df: pd.DataFrame, x: str, y: str, **kwargs) -> dcc.Graph:
    return graph_wrap(fig_scatter(df, x, y, **kwargs))

def graph_bubble(df: pd.DataFrame, x: str, y: str, size: str, **kwargs) -> dcc.Graph:
    return graph_wrap(fig_bubble(df, x, y, size, **kwargs))

def graph_multi_pies(df: pd.DataFrame, group_col: str, slice_col: str, **kwargs) -> dcc.Graph:
    return graph_wrap(fig_multi_pies(df, group_col, slice_col, **kwargs))

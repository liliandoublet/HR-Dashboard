# ui/components/kpis.py
from __future__ import annotations

from typing import Iterable, List, Optional, Union, Dict, Any
from dash import html


THIN_NBSP = "\u202f"  # espace fine insécable


# ─────────────────────────── Formatage ───────────────────────────

def _fmt_number(value: Any) -> str:
    """
    Formate un nombre avec séparateur de milliers 'fine NBSP'.
    Laisse tel quel si non numérique.
    """
    if isinstance(value, (int, float)) and value == int(value):
        return f"{int(value):,}".replace(",", THIN_NBSP)
    if isinstance(value, (int, float)):
        return f"{value:,.1f}".replace(",", THIN_NBSP).replace(".", ",")
    return str(value)


# ─────────────────────────── Tuiles KPI ───────────────────────────

def kpi_tile_static(
    value: Any,
    label: str,
    css_class: str = "kpi-blue",
    *,
    value_suffix: str = "",
) -> html.Div:
    """
    Tuile KPI simple (non cliquable).
    Ex.: kpi_tile_static(1234, "Collaborateurs", "kpi-yellow")
    """
    display = _fmt_number(value) + (value_suffix or "")
    return html.Div(
        className=f"kpi-tile {css_class}",
        children=[
            html.Span(display, className="value"),
            html.Span(label, className="text-sub"),
        ],
    )


def kpi_tile_toggle(
    metric: str,
    value: Any,
    label: str,
    css_class: str = "kpi-blue",
    *,
    rotate_button: bool = True,
    value_suffix: str = "",
) -> html.Div:
    """
    Tuile KPI cliquable + bouton 'rotate' compatibles avec les callbacks:
      - container id     : {"role":"kpi","metric": metric}
      - rotate button id : {"role":"kpi-rotate","metric": metric}
      - value span id    : {"role":"kpi-val","metric": metric}
      - label span id    : {"role":"kpi-lbl","metric": metric}

    Ex.: kpi_tile_toggle("age", "35,4 ans", "Âge moyen", "kpi-yellow")
    """
    children = []
    if rotate_button:
        children.append(
            html.Button(
                id={"role": "kpi-rotate", "metric": metric},
                n_clicks=0,
                className="kpi-rotate-btn",
                title="Changer les KPI",
            )
        )

    display = _fmt_number(value) + (value_suffix or "")

    children.extend(
        [
            html.Span(display, id={"role": "kpi-val", "metric": metric}, className="value"),
            html.Span(label, id={"role": "kpi-lbl", "metric": metric}, className="text-sub"),
        ]
    )

    return html.Div(
        id={"role": "kpi", "metric": metric},
        className=f"kpi-tile kpi-click {css_class}",
        children=children,
    )


# ─────────────────────────── Grille KPI ───────────────────────────

def kpi_grid(tiles: Iterable[html.Div], *, class_name: str = "kpi-wrap") -> html.Div:
    """
    Conteneur de grille pour tuiles KPI (conserve ta classe .kpi-wrap).
    """
    return html.Div(children=list(tiles), className=class_name)


# ─────────────────────────── Raccourcis fréquents ───────────────────────────

def kpi_delta(percent: Optional[float], label: str, css_class: str) -> html.Div:
    """
    Tuile KPI pour variations (%) avec gestion du N/A.
    """
    display = "N/A" if percent is None else f"{percent:+.1f} %".replace(".", ",")
    return kpi_tile_static(display, label, css_class)


def kpi_pair_toggle(
    *,
    metric: str,
    value: Any,
    label: str,
    css_class: str,
    rotate: bool = True,
    suffix: str = "",
) -> html.Div:
    """
    Alias lisible pour créer rapidement une tuile toggle.
    """
    return kpi_tile_toggle(
        metric=metric,
        value=value,
        label=label,
        css_class=css_class,
        rotate_button=rotate,
        value_suffix=suffix,
    )

# services/template_services.py
from __future__ import annotations

import copy
from typing import Literal

import plotly.io as pio
from plotly.graph_objs import Figure

# Noms publics des templates
TEMPLATE_LIGHT_NAME = "neo_light"
TEMPLATE_DARK_NAME  = "neo_dark"

Theme = Literal["light", "dark"]


def _build_dark_template():
    """Construit un template sombre transparent basé sur 'plotly_dark'."""
    base = copy.deepcopy(pio.templates["plotly_dark"])

    # Arrière-plans transparents
    base.layout.paper_bgcolor = "rgba(0,0,0,0)"
    base.layout.plot_bgcolor  = "rgba(0,0,0,0)"

    # Police
    base.layout.font = dict(color="#e6e9f0", family="Inter")

    # Séparateurs : décimale ',' et espace fine pour milliers
    base.layout.separators = ",\u202F"

    # Palette (ta palette existante)
    base.layout.colorway = [
        "#ff007f", "#ab4aff", "#f66023", "#b83724", "#24e0ff", "#fed941"
    ]

    # Axes lisibles
    base.layout.xaxis = dict(color="#e6e9f0", gridcolor="rgba(230,233,240,0.15)")
    base.layout.yaxis = dict(color="#e6e9f0", gridcolor="rgba(230,233,240,0.15)")

    return base


def _build_light_template():
    """Construit un template clair transparent basé sur 'plotly_white'."""
    base = copy.deepcopy(pio.templates["plotly_white"])

    base.layout.paper_bgcolor = "rgba(0,0,0,0)"
    base.layout.plot_bgcolor  = "rgba(0,0,0,0)"

    base.layout.font = dict(color="#212529", family="Inter")

    # Séparateurs identiques (français)
    base.layout.separators = ",\u202F"

    # Palette claire
    base.layout.colorway = [
        "#4361ee", "#f72585", "#4895ef", "#4cc9f0", "#7209b7", "#3f37c9"
    ]

    # Axes
    base.layout.xaxis = dict(color="#212529")
    base.layout.yaxis = dict(color="#212529")

    return base


def register_templates(set_default: Theme | None = None) -> None:
    """
    Enregistre (ou ré-enregistre) les templates 'neo_light' et 'neo_dark'.
    Optionnellement, fixe le template par défaut de Plotly.

    Args:
        set_default: "light" | "dark" | None
    """
    pio.templates[TEMPLATE_DARK_NAME]  = _build_dark_template()
    pio.templates[TEMPLATE_LIGHT_NAME] = _build_light_template()

    if set_default == "dark":
        pio.templates.default = TEMPLATE_DARK_NAME
    elif set_default == "light":
        pio.templates.default = TEMPLATE_LIGHT_NAME


def get_template_name(theme: Theme) -> str:
    """Renvoie le nom du template à utiliser pour un thème donné."""
    return TEMPLATE_DARK_NAME if theme == "dark" else TEMPLATE_LIGHT_NAME


def apply_theme_template(fig: Figure, theme: Theme) -> Figure:
    """
    Applique le template Plotly correspondant au thème, et retourne la figure
    (pratique pour chaîner dans les callbacks).
    """
    fig.update_layout(template=get_template_name(theme))
    return fig


def set_default_template(theme: Theme) -> None:
    """Change le template Plotly par défaut globalement."""
    pio.templates.default = get_template_name(theme)

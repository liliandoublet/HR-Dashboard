# ui/components/filter.py
from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple, Union, Dict, Any
from dash import html, dcc


# ────────────────────────────── Primitives ──────────────────────────────

def dropdown(
    id: Union[str, dict],
    label: Optional[str] = None,
    *,
    options: Optional[Sequence[dict]] = None,
    value: Any = None,
    placeholder: Optional[str] = None,
    multi: bool = False,
    clearable: bool = True,
    class_name: str = "neo-dd",
    option_height: int = 40,
    max_height: int = 400,
) -> html.Div:
    """
    Args:
        id: id Dash (str ou dict).
        label: titre affiché au-dessus du composant (facultatif).
        options: liste d'options Dash [{"label": str, "value": Any, ...}, ...].
        value: valeur initiale (ou liste si multi=True).
        placeholder: texte d'aide quand rien n'est choisi.
        multi: sélection multiple.
        clearable: permet de vider la sélection.
        class_name: classe CSS pour le dcc.Dropdown.
        option_height: hauteur des options (px).
        max_height: hauteur max du menu déroulant (px).
    """
    children = []
    if label:
        children.append(html.Label(label, className="label-title"))
    children.append(
        dcc.Dropdown(
            id=id,
            options=options or [],
            value=value,
            placeholder=placeholder,
            multi=multi,
            clearable=clearable,
            className=class_name,
            optionHeight=option_height,
            maxHeight=max_height,
        )
    )
    return html.Div(children=children, className="")


def radio_items(
    id: Union[str, dict],
    label: Optional[str] = None,
    *,
    options: Sequence[dict],
    value: Any,
    flat: bool = False,
    class_name: str = "radio-group",
    label_block: bool = True,
) -> html.Div:
    """
    Fabrique un groupe de radio items avec style homogène.

    Args similaires à dropdown().
    """
    classes = class_name + (" radio-group--flat" if flat else "")
    children = []
    if label:
        children.append(html.Label(label, className="label-title"))
    children.append(
        dcc.RadioItems(
            id=id,
            options=options,
            value=value,
            className=classes,
            labelStyle={"display": "block"} if label_block else None,
        )
    )
    return html.Div(children=children, className="")


def checklist(
    id: Union[str, dict],
    label: Optional[str] = None,
    *,
    options: Sequence[dict],
    value: Optional[Sequence[Any]] = None,
    class_name: str = "kpi-checklist",
    input_margin_right: str = "6px",
    label_block: bool = True,
    help_text: Optional[str] = None,
) -> html.Div:
    """
    CheckList standardisée (utile pour sélecteurs KPI ou switchs).
    """
    children = []
    if label:
        children.append(html.Label(label, className="label-title"))

    children.append(
        dcc.Checklist(
            id=id,
            options=options,
            value=value or [],
            className=class_name,
            inputStyle={"margin-right": input_margin_right},
            labelStyle={"display": "block" if label_block else "inline-block"},
        )
    )
    if help_text:
        children.append(html.Small(help_text, className="text-sub"))
    return html.Div(children=children, className="filter-block")


def range_slider(
    id: Union[str, dict],
    label: Optional[str],
    *,
    min_v: int,
    max_v: int,
    value: List[int],
    marks: Optional[Dict[int, str]] = None,
    allow_cross: bool = False,
    tooltip_placement: str = "bottom",
    class_name_wrap: str = "",
) -> html.Div:
    """
    RangeSlider prêt à l’emploi (ex: sélection de période).
    """
    children = []
    if label:
        children.append(html.Label(label, className="label-title"))

    children.append(
        dcc.RangeSlider(
            id=id,
            min=min_v,
            max=max_v,
            step=1,
            value=value,
            marks=marks or {},
            allowCross=allow_cross,
            tooltip={"placement": tooltip_placement},
        )
    )
    return html.Div(children=children, className=class_name_wrap or "")


# ───────────────────────────── Composants métier ─────────────────────────────

def tri_block(id_prefix: str = "", *, default: str = "ALPHA", flat: bool = False) -> html.Div:
    """
    Bloc 'Tri' réutilisable (ALPHA/DESC/ASC).

    Exemples d'IDs générés:
      - f"{id_prefix}order-graph"
    """
    return radio_items(
        id=f"{id_prefix}order-graph",
        label=None if flat else "Filtrer les graphiques par ordre",
        options=[
            {"label": "Alphabétique / Chronologique ", "value": "ALPHA"},
            {"label": "Décroissant", "value": "DESC"},
            {"label": "Croissant", "value": "ASC"},
        ],
        value=default,
        flat=flat,
    )


def value_block(id_prefix: str = "", *, default: str = "count", flat: bool = True) -> html.Div:
    """
    Bloc 'Valeurs' (Nombre / % périmètre / % total).

    IDs:
      - section : f"{id_prefix}value-sec"
      - radios  : f"{id_prefix}value-mode"
    """
    classes = "radio-group" + (" radio-group--flat" if flat else "")
    return html.Div(
        id=f"{id_prefix}value-sec",
        children=[
            html.Label("Valeurs", className="label-title"),
            dcc.RadioItems(
                id=f"{id_prefix}value-mode",
                value=default,
                className=classes,
                options=[
                    {"label": "Nombre", "value": "count"},
                    {"label": "% périmètre", "value": "pct_scope"},
                    {"label": "% total", "value": "pct_total"},
                ],
                labelStyle={"display": "block"},
            ),
        ],
        className="",
    )


def viz_filter_block(idx: int, categories_options: Sequence[dict]) -> html.Div:
    """
    Bloc {Filtre n°idx} pour l’onglet 'Analyse complexe' (col + valeurs).
    IDs compatibles avec le pattern du projet:
      - Colonne : {"t":"viz-col","idx": idx}
      - Valeurs : {"t":"viz-val","idx": idx}
    """
    return html.Div(
        className="filter-block",
        children=[
            html.Label(f"Filtre n°{idx}", className="label-title"),
            dcc.Dropdown(
                id={"t": "viz-col", "idx": idx},
                options=categories_options,
                placeholder="Choisissez une catégorie",
                clearable=True,
                className="filter-dropdown",
                optionHeight=40,
                maxHeight=400,
            ),
            dcc.Dropdown(
                id={"t": "viz-val", "idx": idx},
                options=[],
                value=[],
                multi=True,
                placeholder="(Choisissez une ou plusieurs valeurs)",
                className="dropdown sub-dd",
                optionHeight=40,
                maxHeight=400,
            ),
        ],
    )


def two_dropdowns_group(
    title: str,
    start_id: Union[str, dict],
    end_id: Union[str, dict],
    *,
    start_label: str = "Début",
    end_label: str = "Fin",
    options: Optional[Sequence[dict]] = None,
    clearable: bool = False,
    class_name_wrap: str = "filter-block",
    grid_gap: str = "8px",
) -> html.Div:
    """
    Bloc générique (Titre + deux dropdowns), utile pour les sélecteurs Début/Fin.
    """
    return html.Div(
        className=class_name_wrap,
        children=[
            html.Label(title, className="label-title"),
            html.Div(
                id=f"{start_id}-end-wrap" if isinstance(start_id, str) else None,
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr 1fr",
                    "gap": grid_gap,
                    "marginTop": "8px",
                },
                children=[
                    html.Div([
                        html.Label(start_label, className="label-title"),
                        dcc.Dropdown(
                            id=start_id,
                            options=options or [],
                            value=None,
                            clearable=clearable,
                            className="neo-dd",
                            optionHeight=40,
                            maxHeight=400,
                        ),
                    ]),
                    html.Div([
                        html.Label(end_label, className="label-title"),
                        dcc.Dropdown(
                            id=end_id,
                            options=options or [],
                            value=None,
                            clearable=clearable,
                            className="neo-dd",
                            optionHeight=40,
                            maxHeight=400,
                        ),
                    ]),
                ],
            ),
        ],
    )


def simple_pair_filters(
    col1_id: str,
    col2_id: str,
    categories_options: Sequence[dict],
    *,
    labels: Tuple[str, str] = ("Filtre n°1", "Filtre n°2"),
) -> html.Div:
    """
    Bloc de deux filtres simples (col1 / col2) pour l’onglet 'Visualisation'.
    IDs attendus par le reste du projet: 'simp-col1' / 'simp-col2'.
    """
    return html.Div(
        children=[
            html.Div(
                id="simp-f1-wrap",
                className="",
                children=[
                    html.Label(labels[0], className="label-title"),
                    dcc.Dropdown(
                        id=col1_id,
                        options=categories_options,
                        value=[],
                        clearable=True,
                        placeholder="Choisissez une 1ʳᵉ catégorie",
                        className="radio-group",
                        optionHeight=40,
                        maxHeight=400,
                    ),
                ],
            ),
            html.Div(
                id="simp-f2-wrap",
                className="",
                children=[
                    html.Label(labels[1], className="label-title"),
                    dcc.Dropdown(
                        id=col2_id,
                        options=categories_options,
                        value=[],
                        clearable=True,
                        placeholder="Choisissez une 2ᵉ catégorie",
                        className="radio-group",
                        optionHeight=40,
                        maxHeight=400,
                    ),
                ],
            ),
        ],
        className="",
    )


def scatter_options_block(
    x_id: str = "simp-x",
    y_id: str = "simp-y",
    size_id: str = "simp-size",
) -> html.Div:
    """
    Bloc des options numériques pour Scatter / Bubble dans l’onglet 'Visualisation'.
    Garde les mêmes IDs que le code existant.
    """
    return html.Div(
        id="scatter-opts",
        className="filter-block hidden",
        children=[
            html.Label("Axe X (numérique)", className="label-title"),
            dcc.Dropdown(
                id=x_id,
                options=[],
                value=None,
                clearable=True,
                placeholder="Choisissez la variable X",
                className="neo-dd",
                optionHeight=40,
                maxHeight=400,
            ),
            html.Label("Axe Y (numérique)", className="label-title", style={"marginTop": ".6rem"}),
            dcc.Dropdown(
                id=y_id,
                options=[],
                value=None,
                clearable=True,
                placeholder="Choisissez la variable Y",
                className="neo-dd",
                optionHeight=40,
                maxHeight=400,
            ),
            html.Div(
                id="size-wrap",
                className="hidden",
                children=[
                    html.Label("Taille des bulles (numérique)", className="label_title", style={"marginTop": ".6rem"}),
                    dcc.Dropdown(
                        id=size_id,
                        options=[],
                        value=None,
                        clearable=True,
                        placeholder="Choisissez la variable taille",
                        className="neo-dd",
                        optionHeight=40,
                        maxHeight=400,
                    ),
                ],
            ),
            html.Small("Choisissez des colonnes numériques du fichier courant.", className="text-sub"),
        ],
    )


def combine_switch(id_: str = "simp-combine", label: str = "Fusionner en un seul graphique") -> html.Div:
    """Petit switch (checklist à une option) pour activer la combinaison."""
    return html.Div(
        id="simp-combine-wrap",
        className="",
        children=[
            dcc.Checklist(
                id=id_,
                options=[{"label": label, "value": "ON"}],
                value=[],
                style={"margin": "8px 0"},
            )
        ],
    )

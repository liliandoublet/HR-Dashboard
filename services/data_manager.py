# services/data_manager.py
from __future__ import annotations

import os
import re
import glob
import copy
import logging
import datetime as dt
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from cache_utils import memory, CACHE_DIR, TIMEOUT, clean_joblib_cache

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# ------------------------- Normalisation libellés -------------------------

STOPWORDS_FR = {
    "de", "des", "du", "la", "le", "les",
    "et", "à", "aux", "d", "l"
}

def normalize_label(txt: str) -> str:
    """
    04-POLE INFORMATIQUE  →  04-Pôle informatique
    ENTITE DES LOGISTIQUE →  Entité des logistiques
    Règles :
      • préfixe numérique (nn-) conservé
      • reste du texte en minuscules + capitale 1re lettre (hors mots outils)
      • ajoute un 's' après « des » si le mot suivant n’est pas déjà au pluriel
    """
    if pd.isna(txt):
        return txt

    txt = str(txt).strip()
    m = re.match(r"^(\d+\s*-\s*)(.*)", txt)     # extrait éventuel « nn- »
    prefix, label = m.groups() if m else ("", txt)

    words, out = label.lower().split(), []
    for i, w in enumerate(words):
        out.append(w.capitalize() if (i == 0 or w not in STOPWORDS_FR) else w)

    if len(out) >= 2 and out[-2] == "des" and not out[-1].endswith("s"):
        out[-1] += "s"

    return prefix + " ".join(out)

# ------------------------- Préparation DataFrame -------------------------

def prepare_dataset(df: pd.DataFrame) -> pd.DataFrame:

    logger.info("Début du nettoyage des données")
    d = df.copy()

    # 1) Normaliser les blancs sur TOUTES les colonnes objet
    obj_cols = d.select_dtypes(include=["object", "string"]).columns
    for col in obj_cols:
        d[col] = (
            d[col]
            .astype("string")
            .str.strip()
            .replace(r"^\s*$", np.nan, regex=True)
        )

    # 2) Suppression des doublons
    initial_count = len(d)
    if "Matricule" in d.columns:
        d = d.drop_duplicates(subset=["Matricule"], keep="first")
    duplicates_removed = initial_count - len(d)
    if duplicates_removed > 0:
        logger.info(f"Suppression de {duplicates_removed} doublons")

    logger.info("Nettoyage terminé")
    return d

# ------------------------- Chargement + enrichissement -------------------------

@memory.cache
def _load_and_prepare(path: str, _mtime: float) -> pd.DataFrame:

    logger.info(f"Chargement du fichier: {path}")
    try:
        # 1) Lecture brute
        df0 = pd.read_excel(path, sheet_name="COMPILE")

        # 2) Nettoyage standard
        df = prepare_dataset(df0)

        # 3) Normalisation des labels (si colonnes présentes)
        for col in ("CAT1", "PERIMETRE"):
            if col in df.columns:
                df[col] = df[col].apply(normalize_label)

        # 4) Colonnes attendues & avertissement
        required_cols = ["Matricule", "Salaire Annuel ETP", "Date_de_Naissance", "ENTREE_AN"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            logger.warning(f"Colonnes manquantes dans {path}: {missing}")

        # 5) SALAIRE_ETP_NUM (robuste aux espaces / virgules)
        if "Salaire Annuel ETP" in df.columns:
            df["SALAIRE_ETP_NUM"] = pd.to_numeric(
                df["Salaire Annuel ETP"].astype(str)
                  .str.replace(r"\s", "", regex=True)
                  .str.replace(",", ".", regex=False),
                errors="coerce"
            )
        else:
            df["SALAIRE_ETP_NUM"] = np.nan

        # 6) Tranches de salaire par NIVEAU
        grilles_salaire = {
            "TECHNICIEN 1": ([0, 24196.81, 33875.54, np.inf],
                             ["< 24 196 €", "24 196–33 876 €", "≥ 33 876 €"]),
            "TECHNICIEN 2": ([0, 24888.16, 37384.07, np.inf],
                             ["< 24 888 €", "24 888–37 384 €", "≥ 37 384 €"]),
            "TECHNICIEN 3": ([0, 27192.61, 42465.40, np.inf],
                             ["< 27 193 €", "27 193–42 465 €", "≥ 42 465 €"]),
            "TECHNICIEN 4": ([0, 29957.96, 47788.71, np.inf],
                             ["< 29 958 €", "29 958–47 789 €", "≥ 47 789 €"]),
            "TECHNICIEN 5": ([0, 33184.21, 55652.68, np.inf],
                             ["< 33 184 €", "33 184–55 653 €", "≥ 55 653 €"]),
            "CADRE 6":      ([0, 37491.23, 67509.11, np.inf],
                             ["< 37 491 €", "37 491–67 509 €", "≥ 67 509 €"]),
            "CADRE 7":      ([0, 41825.91, 80091.44, np.inf],
                             ["< 41 826 €", "41 826–80 091 €", "≥ 80 091 €"]),
            "CADRE A":      ([0, 50006.74, 97513.16, np.inf],
                             ["< 50 007 €", "50 007–97 513 €", "≥ 97 513 €"]),
            "CADRE B":      ([0, 54961.33, 110821.39, np.inf],
                             ["< 54 961 €", "54 961–110 821 €", "≥ 110 821 €"]),
            "CADRE C":      ([0, 65100.95, 126791.30, np.inf],
                             ["< 65 101 €", "65 101–126 791 €", "≥ 126 791 €"]),
            "CADRE D":      ([0, 77775.46, 148084.50, np.inf],
                             ["< 77 775 €", "77 775–148 085 €", "≥ 148 085 €"]),
        }

        def tranche_par_statut(row: pd.Series) -> str:
            statut = row.get("NIVEAU")
            sal = row.get("SALAIRE_ETP_NUM")
            if pd.isna(statut) or pd.isna(sal):
                return "NON DÉFINI"
            if statut in grilles_salaire:
                edges, labels = grilles_salaire[statut]
                try:
                    return str(pd.cut([sal], bins=edges, labels=labels, right=False)[0])
                except Exception:
                    return "ERREUR CALCUL"
            return "HORS GRILLE"

        if "NIVEAU" in df.columns:
            df["TRCH_SALAIRE_ETP"] = df.apply(tranche_par_statut, axis=1)
        else:
            df["TRCH_SALAIRE_ETP"] = "NON DÉFINI"

        # 7) Année de naissance, âge d'entrée & tranches
        an_ne = pd.to_datetime(df.get("Date_de_Naissance"), errors="coerce").dt.year
        entree_an = pd.to_numeric(df.get("ENTREE_AN"), errors="coerce")
        df["AN_NE"] = an_ne
        df["AGE_ENTREE"] = entree_an - an_ne

        bins = [0, 20, 25, 30, 35, 40, 45, 50, 55, 60, 100]
        labels = ["<20", "21-24", "25-29", "30-34", "35-39",
                  "40-44", "45-49", "50-54", "55-59", "+60"]
        df["TR_AGE_ENTREE"] = pd.cut(df["AGE_ENTREE"], bins=bins, labels=labels, right=False)

        logger.info(f"Fichier {path} préparé – {len(df)} lignes, {df.shape[1]} colonnes")
        return df

    except Exception as e:
        logger.error(f"Erreur lors du chargement de {path}: {e}")
        raise

def load_and_prepare(path: str) -> pd.DataFrame:

    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = 0.0
    return _load_and_prepare(path, mtime)

# ------------------------- DataManager -------------------------

class DataManager:

    def __init__(self, pattern: str = "data/data*.xlsx"):
        self.pattern = pattern
        self.file_list: List[str] = sorted(glob.glob(pattern))
        self._data_cache: Dict[str, pd.DataFrame] = {}
        self._default_file: Optional[str] = None
        self._is_initialized: bool = False

    def initialize(self) -> None:
        """
        Initialise le gestionnaire - charge uniquement le premier fichier.
        """
        if self._is_initialized:
            return

        self.file_list = sorted(glob.glob(self.pattern))
        if not self.file_list:
            logger.warning(f"Aucun fichier trouvé correspondant au pattern '{self.pattern}'")
            self._is_initialized = True
            return

        # Charge uniquement le premier fichier par défaut
        self._default_file = self.file_list[0]
        self._data_cache[self._default_file] = load_and_prepare(self._default_file)

        logger.info(f"Gestionnaire initialisé avec {len(self.file_list)} fichiers disponibles")
        logger.info(f"Fichier par défaut: {self._default_file}")
        self._is_initialized = True

    def get_data(self, file_path: Optional[str] = None) -> pd.DataFrame:
        """
        Retourne les données d'un fichier (chargement à la demande).
        """
        if not self._is_initialized:
            self.initialize()

        # Utilise le fichier par défaut si aucun spécifié
        if file_path is None:
            file_path = self._default_file

        if not file_path:
            # Aucun fichier disponible : renvoyer un DataFrame vide
            return pd.DataFrame()

        if file_path not in self._data_cache:
            logger.info(f"Chargement à la demande: {file_path}")
            self._data_cache[file_path] = load_and_prepare(file_path)

        return self._data_cache[file_path]

    def get_default_data(self) -> pd.DataFrame:
        """
        Retourne les données du fichier par défaut.
        """
        return self.get_data()

    def preload_all(self) -> None:
        """
        Précharge tous les fichiers (optionnel, pour améliorer les performances).
        """
        logger.info("Préchargement de tous les fichiers...")
        for file_path in self.file_list:
            if file_path not in self._data_cache:
                self._data_cache[file_path] = load_and_prepare(file_path)
        logger.info("Préchargement terminé")

    def get_file_list(self) -> List[str]:
        """
        Retourne la liste des fichiers disponibles.
        """
        return self.file_list

    def clear_cache(self) -> None:
        """
        Vide le cache des données (RAM + joblib + /tmp/joblib*).
        """
        self._data_cache.clear()
        memory.clear(warn=False)
        clean_joblib_cache(CACHE_DIR, also_tmp=True, verbose=True)
        logger.info("Cache vidé (joblib + /tmp)")

# ------------------------- API conviviale -------------------------

# Instance globale du gestionnaire
data_manager = DataManager()

def get_df(path: Optional[str] = None) -> pd.DataFrame:
    """
    Fonction de compatibilité - retourne un DataFrame prêt à l'emploi.
    """
    return data_manager.get_data(path)

def get_file_list() -> List[str]:
    return data_manager.get_file_list()

def get_default_file() -> Optional[str]:
    fl = data_manager.get_file_list()
    return fl[0] if fl else None

def warm_cache() -> None:
    """
    Force le pré-chargement joblib des fichiers détectés (utile au démarrage).
    """
    file_list = data_manager.get_file_list()
    for fp in file_list:
        load_and_prepare(fp)
    logger.info(f"✔️  {len(file_list)} fichiers pré-chargés (joblib)")

if __name__ == "__main__":

    data_manager.initialize()
    logger.info(f"Fichiers: {len(get_file_list())}")
    if get_default_file():
        df_test = get_df()
        logger.info(f"Default DF shape: {df_test.shape}")
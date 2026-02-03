# config/column_rules.py
GLOBAL_HIDDEN_COLS = {
    "Date_de_Naissance", "AGE", "EMPLOIS", "ENTREE_AN", "Salaire Annuel ETP",
    "Salaire Annuel", "FILIERE", "DOMAINE", "Date_Affection_Unité", "TRANCHE_PCT_TRAV",
}
VIS_HIDDEN_COLS = {
    "Date_de_Naissance", "Salaire Annuel ETP", "Salaire Annuel",
    "DOMAINE", "Date_Affection_Unité"
}
ANALYS_HIDDEN_COLS = {
    "Date_de_Naissance", "Salaire Annuel ETP", "Salaire Annuel", "DOMAINE"
}
TREEMAP_EXCLUDED_COLS = {
    "AGE_ENTREE", "AGE", "Salaire Annuel", "Salaire Annuel ETP",
    "Date_de_Naissance", "ENTREE_AN", "Date_Affection_Unité",
}
COMPA_HIDDEN_COLS = {
    "Date_de_Naissance", "Salaire Annuel ETP", "Salaire Annuel", "DOMAINE"
}
COMPA_CPLX_HIDDEN_COLS = {
    "Date_de_Naissance", "Salaire Annuel ETP", "Salaire Annuel", "DOMAINE"
}
SCATTER_EXCLUDED_COLS = {
    "Matricule", "Date_de_Naissance", "Date_Affection_Unité",
    "Salaire Annuel", "Salaire Annuel ETP"  # on utilise SALAIRE_ETP_NUM à la place
}

cat_lbl = {
    "AGE": "Age actuel", 
    "Type_de_contrat": "Type de contrat", 
    "EMPLOIS": "Emplois",
    "STATUT": "Cadre ou non cadre", 
    "Sexe": "Sexe", 
    "TRANCHE_AGE": "Tranche d'age",
    "ENTREE_AN": "Année d'entrée dans l'entreprise", 
    "ETU_NIV_MAX (Lib)": "Nombre d'année d'étude",
    "Date_de_Naissance": "NAISSANCE", 
    "RECRUT_EX": "Recrutement interne ou externe",
    "Salaire Annuel ETP": "Salaire Annuel EQ.TEMPS PLEIN", 
    "Salaire Annuel": "Salaire annuel réel",
    "Date_Affection_Unité": "Date de commencement du nouveau poste",
    "NIVEAU": "Statut administratif précis", 
    "FAM_EMP": "Famille d'emplois", 
    "DOMAINE": "Domaine d'emplois",
    "FILIERE": "Filère de métier", 
    "TRANCHE_PCT_TRAV": "Modalités de temps de travail", 
    "TR_ANC_GRP": "Tranche anciennetée dans le groupe", 
    "AGE_ENTREE": "Age d'entrée dans le groupe", 
    "TR_AGE_ENTREE": "Tranche d'age d'entrée dans le groupe",
    "TRCH_SALAIRE_ETP": "TRANCHE SALAIRE (ETP)", 
    "NAT_DISPO": "Situation particulière",
    "Périmètre": "Périmètre",
    "Libellé_service": "Information sur le service",
}
cat_lbl.setdefault("SALAIRE_ETP_NUM", "Salaire annuel ETP (num.)")
cat_lbl.setdefault("ANCIENNETE", "Ancienneté (années)")
cat_lbl.setdefault("AGE_ENTREE", "Âge d'entrée")
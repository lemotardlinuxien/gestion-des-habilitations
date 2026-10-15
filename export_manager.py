import os
import pandas as pd
from controle_manager import ControleManager
from mail_repository import recuperer_parametres_mail


def preparer_lignes_secteur(
        df,
        secteur,
        habilitations
):
    """
    Prépare les lignes d'export d'un secteur.

    Retourne uniquement les habilitations
    qui ne sont pas valides (🟢).
    """

    df_secteur = df[
        df["Secteur"]
        .astype(str)
        .str.upper()
        .str.strip()
        ==
        secteur.upper().strip()
    ]

    lignes = []

    param = recuperer_parametres_mail()
    delai_alerte = int(param["delai_alerte"])

    for _, row in df_secteur.iterrows():

        for hab in habilitations:

            date = row[hab]

            if pd.isna(date):
                continue

            etat = ControleManager.statut(
                date,
                delai_alerte
            )

            if "🟢" in etat:
                continue

            lignes.append({
                "Secteur": row["Secteur"],
                "Nom": row["Nom"],
                "Prénom": row["Prénom"],
                "Formation": hab,
                "Échéance": pd.to_datetime(
                    date
                ).strftime("%d/%m/%Y"),
                "Statut": etat
            })

    return lignes


def generer_export_secteur(
        lignes,
        dossier,
        secteur
):
    """
    Génère le fichier Excel d'un secteur.

    Retourne le chemin complet du fichier créé.
    """

    os.makedirs(
        dossier,
        exist_ok=True
    )

    fichier = os.path.join(
        dossier,
        f"exports_habilitations_{secteur}.xlsx"
    )

    pd.DataFrame(
        lignes
    ).to_excel(
        fichier,
        index=False
    )

    return fichier
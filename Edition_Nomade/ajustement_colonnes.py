from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font
from habilitation_manager import HabilitationManager


def colonnes_ajustees(fichier):

    wb = load_workbook(fichier)
    ws = wb.active

    largeurs = {
        "ID": 3,
        "Secteur": 20,
        "Nom": 20,
        "Prénom": 20
    }

    # Une seule lecture de la configuration pour tout le traitement Excel.
    habilitations = HabilitationManager.lister()

    for hab in habilitations:
        largeurs[hab] = 20

    for colonne in ws.columns:

        titre = colonne[0].value

        # Largeur de colonne
        if titre in largeurs:

            ws.column_dimensions[
                colonne[0].column_letter
            ].width = largeurs[titre]

        # Tous les titres en gras
        colonne[0].font = Font(
            bold=True
        )

        # Tous les titres de colonnes sont centrés verticalement et horizontalement.
        colonne[0].alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

    wb.save(fichier)
import os
import pandas as pd
from habilitation_manager import HabilitationManager
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4, landscape
from config import DOSSIER_PDF
from datetime import datetime
class PDFManager:

    @staticmethod
    def generer(df):

        aujourd_hui = pd.Timestamp.today()

        secteurs = sorted(
            df["Secteur"].dropna().unique()
        )

        # Les habilitations ne changent pas pendant la génération du PDF :
        # on les récupère une seule fois plutôt qu'à chaque secteur/salarié.
        habilitations = HabilitationManager.lister()

        for secteur in secteurs:

            pdf = os.path.join(
                DOSSIER_PDF,
                f"{secteur}.pdf"
            )

            document = SimpleDocTemplate(
                pdf,
                pagesize=landscape(A4)
            )

            elements = []

            styles = getSampleStyleSheet()

            titre = Paragraph(
                f"HABILITATIONS VALIDES<br/>{secteur}",
                styles["Title"]
            )

            date_export = Paragraph(
                f"Date d'édition : {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
                styles["Normal"]
            )

            elements.append(date_export)
            elements.append(titre)
            elements.append(Spacer(1, 15))

            data = [[
                "Nom",
                "Prénom",
                *habilitations
            ]]

            secteur_df = df[df["Secteur"] == secteur]

            for _, row in secteur_df.iterrows():

                ligne = [
                    row["Nom"],
                    row["Prénom"]
                ]

                valide = False

                for hab in habilitations:

                    date = row[hab]

                    if pd.isna(date):
                        ligne.append("")
                        continue

                    date = pd.to_datetime(date)

                    if date >= aujourd_hui:

                        ligne.append(date.strftime("%d/%m/%Y"))
                        valide = True

                    else:
                        ligne.append("")

                if valide:
                    data.append(ligne)

            table = Table(data)

            table.setStyle(
                TableStyle([
                    ("GRID", (0, 0), (-1, -1), 1, colors.black)
                ])
            )

            elements.append(table)

            document.build(elements)
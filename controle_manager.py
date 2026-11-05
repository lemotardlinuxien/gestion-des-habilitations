import pandas as pd
from datetime import timedelta
from mail_repository import recuperer_parametres_mail


class ControleManager:

    @staticmethod
    def statut(date, delai_alerte):

        aujourd_hui = pd.Timestamp.today().normalize()

        if pd.isna(date):
            return ""

        date = pd.to_datetime(date)

        if date < aujourd_hui:
            return "🔴 Expirée"

        limite = (
                aujourd_hui +
                timedelta(
                    days=delai_alerte
                )
        )

        if date <= limite:
            return (
                f"🟠 < {delai_alerte} jours"
            )

        return "🟢 Valide"

    @staticmethod
    def analyser_dataframe(df):

        resultats = []

        param = recuperer_parametres_mail()
        delai_alerte = int(param["delai_alerte"])

        habilitations = [
            colonne
            for colonne in df.columns
            if colonne not in {
                "ID",
                "Secteur",
                "Nom",
                "Prénom"
            }
        ]

        for _, row in df.iterrows():

            for hab in habilitations:

                date = row[hab]

                statut = ControleManager.statut(
                    date,
                    delai_alerte
                )

                if not statut:
                    continue

                resultats.append({
                    "Nom": row["Nom"],
                    "Prénom": row["Prénom"],
                    "Habilitation": hab,
                    "Échéance": date,
                    "Statut": statut
                })

        return resultats

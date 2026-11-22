import pandas as pd
from controle_manager import ControleManager
from database import lire_donnees
from mail_repository import recuperer_parametres_mail

class RechercheManager:

    def rechercher(
        self,
        nom="",
        prenom="",
        secteur="",
        habilitation="",
        statut=""
    ):
        """
        Effectue une recherche dans SQLite.

        Les critères Nom, Prénom et Secteur utilisent
        une recherche par début de texte, sans distinction
        majuscules / minuscules.

        Le filtre habilitation permet de rechercher
        selon la date de validité.
        """

        # =========================
        # SOURCE UNIQUE = SQLite
        # =========================

        df = lire_donnees()

        df = df.fillna("")

        # =========================
        # Normalisation des saisies
        # =========================

        nom = str(nom).strip().upper()
        prenom = str(prenom).strip().upper()
        secteur = str(secteur).strip().upper()

        # =========================
        # Filtre Nom
        # =========================

        if nom:
            df = df[
                df["Nom"]
                .astype(str)
                .str.upper()
                .str.startswith(nom)
            ]

        # =========================
        # Filtre Prénom
        # =========================

        if prenom:
            df = df[
                df["Prénom"]
                .astype(str)
                .str.upper()
                .str.startswith(prenom)
            ]

        # =========================
        # Filtre Secteur
        # =========================

        if secteur:
            df = df[
                df["Secteur"]
                .astype(str)
                .str.upper()
                .str.startswith(secteur)
            ]

        # =========================
        # Filtre habilitation
        # =========================

        if habilitation:

            dates = pd.to_datetime(
                df[habilitation],
                errors="coerce"
            )

            mask = dates.notna()

            df = df.loc[mask].copy()
            dates = dates.loc[mask]

            param = recuperer_parametres_mail()
            delai_alerte = int(param["delai_alerte"])

            if statut:

                statuts = dates.map(
                    lambda date: ControleManager.statut(
                        date,
                        delai_alerte
                    )
                ).astype("string")

                if statut == "Valide":

                    df = df[
                        statuts.str.contains(
                            "🟢",
                            na=False
                        )
                    ]

                elif statut.startswith("<"):

                    df = df[
                        statuts.str.contains(
                            "🟠",
                            na=False
                        )
                    ]

                elif statut == "Expirée":

                    df = df[
                        statuts.str.contains(
                            "🔴",
                            na=False
                        )
                    ]

        # =========================
        # Nettoyage final
        # =========================

        df = df.fillna("")

        return df
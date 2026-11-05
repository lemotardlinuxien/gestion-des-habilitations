import os
import shutil
import pandas as pd
from habilitation_manager import HabilitationManager
from datetime import datetime
from config import (
    FICHIER_EXCEL,
    DOSSIER_SAUVEGARDES,
    DB,
    COLONNES_TECHNIQUES
)
from ajustement_colonnes import colonnes_ajustees
from database import (sauvegarder_dataframe,
    lire_donnees)

from logger_manager import log_info
from validation import normaliser_texte_comparaison

class DataManager:

    def __init__(self):

        self.df = self.charger()

    def charger(self):
        try:
            df = lire_donnees()

            colonnes_fixes = COLONNES_TECHNIQUES.copy()

            habilitations = HabilitationManager.lister()

            # Garantit la présence des colonnes fixes
            for col in colonnes_fixes:
                if col not in df.columns:
                    df[col] = pd.NA

            # Garantit la présence des habilitations configurées
            for hab in habilitations:
                if hab not in df.columns:
                    df[hab] = pd.NaT

            # Conversion des dates des habilitations
            for hab in habilitations:
                if hab in df.columns:
                    df[hab] = pd.to_datetime(
                        df[hab],
                        errors="coerce",
                        format="mixed"
                    )

            # Organisation finale des colonnes
            colonnes_finales = colonnes_fixes + habilitations

            df = df.reindex(
                columns=colonnes_finales,
                fill_value=pd.NA
            )

            return df

        except FileNotFoundError:
            habilitations = HabilitationManager.lister()

            colonnes = [
                *COLONNES_TECHNIQUES,
                *habilitations
            ]

            df = pd.DataFrame(columns=colonnes)

            df.to_excel(
                FICHIER_EXCEL,
                index=False
            )

            return df

    def ajouter_colonne_habilitation(self, nom):
        """
        Ajoute une nouvelle colonne d'habilitation
        au DataFrame en mémoire.

        Les salariés existants ont une valeur vide.
        """

        if nom in self.df.columns:
            return

        self.df[nom] = pd.NaT

    def supprimer_salarie(self, id_):
        """
        Supprime un salarié du DataFrame en mémoire.

        La synchronisation avec SQLite et Excel est réalisée
        par sauvegarder().
        """

        if self.df.empty:
            return False

        masque = self.df["ID"].astype(str) != str(id_)

        if masque.all():
            return False

        self.df = (
            self.df.loc[masque]
            .reset_index(drop=True)
        )

        return True

    def ajouter_salarie(self, ligne):
        """
        Ajoute un salarié au DataFrame en mémoire.

        Parameters
        ----------
        ligne : dict
            Données du salarié à ajouter.

        Returns
        -------
        bool
            True si le salarié a été ajouté.
        """

        if not isinstance(ligne, dict):
            return False

        if not ligne:
            return False

        # Défense supplémentaire contre les doublons, même si l'ajout
        # est déclenché sans passer par l'interface graphique.
        colonnes_identite = {"Secteur", "Nom", "Prénom"}
        if colonnes_identite.issubset(ligne) and colonnes_identite.issubset(self.df.columns):
            if not self.df.empty:
                secteur = normaliser_texte_comparaison(ligne.get("Secteur", ""))
                nom = normaliser_texte_comparaison(ligne.get("Nom", ""))
                prenom = normaliser_texte_comparaison(ligne.get("Prénom", ""))
                doublon = (
                    self.df["Secteur"].fillna("").map(normaliser_texte_comparaison).eq(secteur)
                    & self.df["Nom"].fillna("").map(normaliser_texte_comparaison).eq(nom)
                    & self.df["Prénom"].fillna("").map(normaliser_texte_comparaison).eq(prenom)
                )
                if doublon.any():
                    return False

        # Garantit la présence des colonnes existantes
        for colonne in self.df.columns:
            if colonne not in ligne:
                ligne[colonne] = pd.NaT

        # Garantit les éventuelles nouvelles colonnes
        for colonne in ligne:
            if colonne not in self.df.columns:
                self.df[colonne] = pd.NaT

        nouvelle_ligne = pd.DataFrame(
            [ligne],
            columns=self.df.columns
        )

        self.df = pd.concat(
            [self.df, nouvelle_ligne],
            ignore_index=True
        )

        return True

    def modifier_salarie(self, id_, ligne):
        """
        Modifie un salarié dans le DataFrame en mémoire.

        Parameters
        ----------
        id_ : str
            Identifiant du salarié à modifier.

        ligne : dict
            Nouvelles données du salarié.

        Returns
        -------
        bool
            True si le salarié a été trouvé et modifié.
        """

        if self.df.empty:
            return False

        if not isinstance(ligne, dict):
            return False

        if "ID" not in self.df.columns:
            return False

        masque = (
            self.df["ID"]
            .astype(str)
            .eq(str(id_))
        )

        if not masque.any():
            return False

        index = self.df.index[masque][0]

        # Garantit les éventuelles nouvelles colonnes
        for colonne in ligne:

            if colonne not in self.df.columns:
                self.df[colonne] = pd.NaT

        # Mise à jour des valeurs
        for colonne, valeur in ligne.items():
            self.df.at[index, colonne] = valeur

        return True

    def sauvegarder_sqlite(self):
        """
        Sauvegarde les données du DataFrame dans SQLite.
        """
        sauvegarder_dataframe(self.df)

    def creer_sauvegardes(self):
        """
        Crée les sauvegardes Excel et SQLite
        et conserve uniquement les 2 plus récentes.
        """

        horodatage = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        # ==========================================
        # SAUVEGARDE EXCEL
        # ==========================================

        sauvegarde_excel = os.path.join(
            DOSSIER_SAUVEGARDES,
            f"habilitations_{horodatage}.xlsx"
        )

        shutil.copy2(
            FICHIER_EXCEL,
            sauvegarde_excel
        )

        # ==========================================
        # SAUVEGARDE SQLITE
        # ==========================================

        sauvegarde_db = os.path.join(
            DOSSIER_SAUVEGARDES,
            f"habilitations_{horodatage}.db"
        )

        if DB.exists():
            shutil.copy2(
                DB,
                sauvegarde_db
            )

        # ==========================================
        # ROTATION DES SAUVEGARDES EXCEL
        # ==========================================

        sauvegardes_excel = sorted(
            [
                os.path.join(
                    DOSSIER_SAUVEGARDES,
                    fichier
                )
                for fichier in os.listdir(
                DOSSIER_SAUVEGARDES
            )
                if fichier.endswith(".xlsx")
            ],
            key=os.path.getmtime,
            reverse=True
        )

        for fichier in sauvegardes_excel[2:]:
            os.remove(fichier)

        log_info(
            f"Sauvegarde de sécurité effectuée avant modification : "
            f"Excel={os.path.basename(sauvegarde_excel)}, "
            f"SQLite={os.path.basename(sauvegarde_db) if DB.exists() else 'non disponible'}"
        )

        # ==========================================
        # ROTATION DES SAUVEGARDES SQLITE
        # ==========================================

        sauvegardes_db = sorted(
            [
                os.path.join(
                    DOSSIER_SAUVEGARDES,
                    fichier
                )
                for fichier in os.listdir(
                DOSSIER_SAUVEGARDES
            )
                if fichier.endswith(".db")
            ],
            key=os.path.getmtime,
            reverse=True
        )

        for fichier in sauvegardes_db[2:]:
            os.remove(fichier)

    def sauvegarder_excel(self):
        """
        Sauvegarde les données du DataFrame dans Excel
        et ajuste automatiquement les colonnes.
        """
        self.df.to_excel(
            FICHIER_EXCEL,
            index=False
        )

        colonnes_ajustees(FICHIER_EXCEL)

    def sauvegarder(self):
        try:
            self.sauvegarder_sqlite()
            self.sauvegarder_excel()
            self.creer_sauvegardes()
            return True

        except Exception as erreur:
            log_info(
                f"Erreur lors de la sauvegarde : {erreur}"
            )
            return False
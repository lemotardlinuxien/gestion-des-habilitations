"""
ImportEngine
============

Moteur d'analyse et de préparation des imports Excel.

L'analyse est réalisée sans modification de SQLite.
Les opérations préparées sont appliquées uniquement
après validation explicite de l'utilisateur.
"""

import pandas as pd
from pathlib import Path
from database import normaliser_colonnes
from id_manager import generer_id
from logger_manager import (
    log_info,
    log_error,
    log_warning
)

from database import (
    lire_donnees,
    appliquer_operations,
)

import re

from habilitation_manager import HabilitationManager

from config import COLONNES_TECHNIQUES
from validation import normaliser_texte_comparaison

class ImportEngine:

    def __init__(self, fichier):

        self.fichier = fichier

        self.df_excel = None
        self.df_sql = None

        # Expressions régulières réutilisables

        self.regex_uuid = re.compile(
            r"^[0-9a-fA-F]{8}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{12}$"
        )

        self.regex_hab = re.compile(
            r"^HAB\d+$",
            re.IGNORECASE
        )

        self.rapport = {
            # ==========================================
            # Informations générales
            # ==========================================
            "nb_excel": 0,
            "nb_sqlite": 0,

            # ==========================================
            # Résultat de l'analyse
            # ==========================================
            "erreurs": [],
            "avertissements": [],

            # ==========================================
            # Nouvelles habilitations
            # ==========================================
            "nouvelles_habilitations": [],

            # ==========================================
            # Ordre des habilitations selon Excel
            # ==========================================
            "ordre_habilitations_excel": [],

            # ==========================================
            # Incohérences d'ID
            # ==========================================
            "incoherences_id": [],

            # ==========================================
            # Doublons
            # ==========================================
            "doublons_excel": [],
            "doublons_id": [],

            # ==========================================
            # Opérations préparées
            # ==========================================
            "ajoutes": 0,
            "modifies": 0,
            "doublons": [],
            "homonymes": [],
        }

        self.operations_import = []
        self.analyse_terminee = False

    # ======================================================
    # MOTEUR
    # ======================================================

    def executer(self, progression=None):
        """
        Analyse complète du fichier Excel.

        IMPORTANT :
            Cette fonction NE MODIFIE PAS SQLite.

        Elle :
            1. charge Excel et SQLite
            2. vérifie les en-têtes
            3. vérifie la structure
            4. normalise les données
            5. nettoie les lignes totalement vides
            6. vérifie les identifiants, doublons et dates
            7. prépare les opérations d'import

        Les opérations préparées sont stockées dans :

            self.operations_import

        L'application réelle en base sera effectuée
        ultérieurement, après validation de l'utilisateur.
        """

        def signaler_progression(etape, message):
            """Informe le dialogue à chaque étape réelle de l'analyse."""
            if progression is not None:
                progression(f"Étape {etape} / 7 — {message}")

        try:

            signaler_progression(1, "Lecture du fichier Excel...")

            # ======================================================
            # LOG
            # ======================================================

            log_info("Import Excel lancé")

            # ======================================================
            # 1. CHARGEMENT
            # ======================================================

            self.charger()
            signaler_progression(2, "Vérification des en-têtes...")

            # ======================================================
            # 2. VÉRIFICATION DES EN-TÊTES
            # ======================================================

            if not self.verifier_entetes_excel():
                return self.rapport

            # ======================================================
            # 3. VÉRIFICATION DE LA STRUCTURE
            # ======================================================

            signaler_progression(3, "Vérification de la structure...")
            self.verifier_colonnes()

            for avertissement in self.rapport["avertissements"]:
                log_warning(
                    f"Avertissement import : {avertissement}"
                )

            if self.rapport["erreurs"]:

                log_warning(
                    f"Import Excel refusé : "
                    f"{len(self.rapport['erreurs'])} erreur(s) détectée(s)"
                )

                for erreur in self.rapport["erreurs"]:
                    log_warning(
                        f"Détail erreur import : {erreur}"
                    )

                return self.rapport

            # ======================================================
            # 4. PRÉPARATION DU DATAFRAME
            # ======================================================

            signaler_progression(4, "Normalisation des données...")
            self.normaliser()

            # ======================================================
            # 5. NETTOYAGE
            # ======================================================

            signaler_progression(5, "Nettoyage des données...")
            self.nettoyer()

            # ======================================================
            # 6. VÉRIFICATION DU CONTENU
            # ======================================================

            signaler_progression(6, "Contrôle des identifiants, doublons et dates...")
            self.verifier_id()
            self.verifier_doublons()
            self.verifier_dates()

            if self.rapport["erreurs"]:

                log_warning(
                    f"Import Excel refusé : "
                    f"{len(self.rapport['erreurs'])} erreur(s) détectée(s)"
                )

                for erreur in self.rapport["erreurs"]:
                    log_warning(
                        f"Détail erreur import : {erreur}"
                    )

                return self.rapport

            # ======================================================
            # 7. PRÉPARATION DES OPÉRATIONS
            # ======================================================

            signaler_progression(7, "Préparation du résultat de l'import...")
            self._synchroniser_par_identite()

            for avertissement in self.rapport["avertissements"]:
                log_warning(
                    f"Avertissement import : {avertissement}"
                )

            log_info(
                f"Analyse Excel terminée : "
                f"{self.rapport['nb_excel']} lignes Excel / "
                f"{self.rapport['nb_sqlite']} salariés SQLite"
            )

            # ======================================================
            # 8. RETOUR DU RAPPORT
            # ======================================================

            self.analyse_terminee = True

            return self.rapport

        except Exception as erreur:

            log_error(
                f"Erreur lors de l'import Excel : "
                f"{type(erreur).__name__}"
            )

            raise

    # ======================================================
    # CHARGEMENT
    # ======================================================

    def _lire_excel(self):
        """
        Lit le fichier Excel.
        """

        self.df_excel = pd.read_excel(
            self.fichier
        )

        log_info(
            f"Fichier Excel chargé : {Path(self.fichier).name}"
        )

    def charger(self):
        """
        Charge le fichier Excel et la base SQLite.
        """

        self._lire_excel()

        self.df_sql = lire_donnees()

        self.rapport["nb_excel"] = len(
            self.df_excel
        )

        self.rapport["nb_sqlite"] = len(
            self.df_sql
        )

    # ======================================================
    # VALIDATION
    # ======================================================

    def _cle_identite(self, ligne):
        """
        Retourne la clé métier d'un salarié.

        L'identité métier est définie par :
            Nom + Prénom + Secteur
        """

        return (
            str(ligne["Nom"]).strip().upper(),
            str(ligne["Prénom"]).strip().upper(),
            str(ligne["Secteur"]).strip().upper()
        )

    def verifier_entetes_excel(self):
        """
        Vérifie que le fichier Excel possède de véritables
        en-têtes de colonnes avant toute modification de la DB.

        Les colonnes Nom et Prénom sont indispensables.

        Cette vérification est volontairement sans effet de bord :
        elle ne crée aucune habilitation et ne modifie pas SQLite.
        """

        df_test = self.df_excel.copy()

        # Normalisation uniquement pour identifier les en-têtes
        df_test = normaliser_colonnes(df_test)

        colonnes = {
            str(colonne).strip()
            for colonne in df_test.columns
        }

        indispensables = {
            "Secteur",
            "Nom",
            "Prénom"
        }

        manquantes = indispensables - colonnes

        if manquantes:
            self.rapport["erreurs"].append(
                "Import impossible.\n\n"
                "Le fichier Excel sélectionné ne contient pas "
                "les en-têtes de colonnes indispensables.\n\n"
                "Colonnes manquantes : "
                + ", ".join(sorted(manquantes))
                + "\n\n"
                  "Il est possible que le mauvais fichier ait été "
                  "sélectionné ou que ses en-têtes aient été modifiés.\n\n"
                  "Veuillez vérifier le fichier Excel puis relancer "
                  "l'import."
            )

            return False

        return True

    def verifier_colonnes(self):
        """
        Vérifie et adapte automatiquement la structure du fichier Excel.

        Les colonnes techniques sont reconnues sans tenir compte
        de la casse ni des accents.

        Exemple :
            ID
            Id
            id
            iD

        correspondent toutes à la colonne technique ID.

        Nom et Prénom sont indispensables.
        Les nouvelles colonnes métier peuvent devenir
        automatiquement de nouvelles habilitations.
        """

        # ==========================================
        # COLONNES EXCEL
        # ==========================================

        colonnes_excel = {
            str(colonne).strip().casefold()
            for colonne in self.df_excel.columns
        }

        # ==========================================
        # HABILITATIONS CONFIGURÉES
        # ==========================================

        habilitations = HabilitationManager.lister()

        # ==========================================
        # COLONNES TECHNIQUES
        # ==========================================

        colonnes_fixes = {
            str(colonne).strip().casefold()
            for colonne in COLONNES_TECHNIQUES
        }

        # ==========================================
        # COLONNES INDISPENSABLES
        # ==========================================

        colonnes_indispensables = {
            "secteur",
            "nom",
            "prénom"
        }

        colonnes_absentes = (
                colonnes_indispensables - colonnes_excel
        )

        if colonnes_absentes:

            noms_affichage = []

            for colonne in sorted(colonnes_absentes):

                if colonne == "nom":
                    noms_affichage.append("Nom")

                elif colonne == "prénom":
                    noms_affichage.append("Prénom")

                else:
                    noms_affichage.append(colonne)

            self.rapport["erreurs"].append(
                "Colonnes indispensables manquantes : "
                + ", ".join(noms_affichage)
            )

            return

        # ==========================================
        # COLONNES RECONNUES
        # ==========================================

        colonnes_habilitations = {
            str(habilitation).strip().casefold()
            for habilitation in habilitations
        }

        # ==========================================
        # COLONNES DÉTECTÉES MAIS NON IMPORTÉES
        # ==========================================

        colonnes_ignorees = {
            "matricule",
            "matricules",
            "hab",
            "habilitation",
            "habilitations",
        }

        colonnes_connues = (
                colonnes_fixes
                | colonnes_habilitations
                | colonnes_ignorees
        )

        # ==========================================
        # AVERTISSEMENT COLONNES IGNORÉES
        # ==========================================

        for cle_colonne in sorted(
                colonnes_excel & colonnes_ignorees
        ):
            nom = next(
                (
                    str(colonne).strip()
                    for colonne in self.df_excel.columns
                    if str(colonne).strip().casefold()
                       == cle_colonne
                ),
                cle_colonne
            )

            self.rapport["avertissements"].append(
                f"Colonne détectée mais non importée : "
                f"'{nom}'. "
                f"Son contenu sera ignoré."
            )

        # ==========================================
        # NOUVELLES COLONNES
        # ==========================================

        colonnes_nouvelles = (
                colonnes_excel - colonnes_connues
        )

        nouvelles_habilitations = []

        for cle_colonne in (
                str(colonne).strip().casefold()
                for colonne in self.df_excel.columns
                if str(colonne).strip().casefold() in colonnes_nouvelles
        ):

            # Retrouve le nom original de la colonne Excel
            nom = next(
                (
                    str(colonne).strip()
                    for colonne in self.df_excel.columns
                    if str(colonne).strip().casefold()
                       == cle_colonne
                ),
                cle_colonne
            )

            # --------------------------------------
            # Nom vide
            # --------------------------------------

            if not nom:
                continue

            # --------------------------------------
            # Protection contre les noms trop longs
            # --------------------------------------

            if len(nom) > 50:
                self.rapport["avertissements"].append(
                    f"Colonne ignorée : '{nom}' "
                    f"(nom trop long)."
                )

                continue

            # --------------------------------------
            # Protection colonnes techniques
            # --------------------------------------

            if cle_colonne in colonnes_fixes:
                continue

            if nom.startswith("_"):
                self.rapport["avertissements"].append(
                    f"Colonne ignorée : '{nom}' "
                    f"(colonne technique)."
                )

                continue

            # --------------------------------------
            # Nouvelle habilitation
            # --------------------------------------

            nouvelles_habilitations.append(nom)

        # ==========================================
        # RAPPORT DES NOUVELLES HABILITATIONS
        # ==========================================

        self.rapport["nouvelles_habilitations"] = (
            nouvelles_habilitations
        )

        # ==========================================
        # ORDRE DES HABILITATIONS SELON EXCEL
        # ==========================================

        ordre_habilitations_excel = []

        habilitations_par_cle = {
            str(habilitation).strip().casefold(): habilitation
            for habilitation in habilitations
        }

        nouvelles_par_cle = {
            str(habilitation).strip().casefold(): habilitation
            for habilitation in nouvelles_habilitations
        }

        for colonne in self.df_excel.columns:

            nom = str(colonne).strip()
            cle = nom.casefold()

            if cle in habilitations_par_cle:
                ordre_habilitations_excel.append(
                    habilitations_par_cle[cle]
                )

            elif cle in nouvelles_par_cle:
                ordre_habilitations_excel.append(
                    nouvelles_par_cle[cle]
                )

        self.rapport["ordre_habilitations_excel"] = (
            ordre_habilitations_excel
        )

        # ==========================================
        # DÉTECTION D'UN CHANGEMENT D'ORDRE
        # ==========================================

        ordre_actuel = list(habilitations)

        ordre_final = []

        # Habilitations présentes dans Excel
        for habilitation in ordre_habilitations_excel:

            if habilitation not in ordre_final:
                ordre_final.append(habilitation)

        # Habilitations existantes absentes de l'Excel
        # → elles restent à la fin
        for habilitation in ordre_actuel:

            if habilitation not in ordre_final:
                ordre_final.append(habilitation)

        if ordre_final != ordre_actuel:
            self.rapport["avertissements"].append(
                "⚠️ L'ordre des habilitations sera modifié "
                "selon l'ordre du fichier Excel."
            )

            self.rapport["avertissements"].append(
                "Ordre actuel : "
                + " → ".join(ordre_actuel)
            )

            self.rapport["avertissements"].append(
                "Nouvel ordre : "
                + " → ".join(ordre_final)
            )

        if nouvelles_habilitations:
            self.rapport["avertissements"].append(
                "Nouvelles habilitations détectées : "
                + ", ".join(nouvelles_habilitations)
                + ". Elles seront créées uniquement "
                  "après validation de l'import."
            )

    def verifier_id(self):
        """
        Vérifie :
        - que Secteur + Nom + Prénom sont présents sur chaque ligne ;
        - la validité des identifiants lorsqu'une colonne ID existe ;
        - les incohérences entre ID Excel et ID SQLite.
        """

        # ==========================================
        # Vérification de l'identité métier
        # Secteur + Nom + Prénom obligatoires
        # ==========================================

        for numero, (_, ligne) in enumerate(
                self.df_excel.iterrows(),
                start=2
        ):

            secteur = str(
                ligne.get("Secteur", "")
            ).strip()

            nom = str(
                ligne.get("Nom", "")
            ).strip()

            prenom = str(
                ligne.get("Prénom", "")
            ).strip()

            champs_manquants = []

            if not secteur:
                champs_manquants.append("Secteur")

            if not nom:
                champs_manquants.append("Nom")

            if not prenom:
                champs_manquants.append("Prénom")

            if champs_manquants:
                self.rapport["erreurs"].append(
                    f"Ligne {numero} : "
                    f"identité incomplète. "
                    f"Champ(s) manquant(s) : "
                    + ", ".join(champs_manquants)
                    + "."
                )

        # ==========================================
        # Fichier sans colonne ID
        # ==========================================

        if "ID" not in self.df_excel.columns:
            return

        # ==========================================
        # Vérification des identifiants
        # ==========================================

        for numero, identifiant in enumerate(
                self.df_excel["ID"],
                start=2
        ):

            identifiant = str(
                identifiant
            ).strip()

            # ==========================
            # ID vide
            # ==========================

            if identifiant == "":
                continue

            # ==========================
            # UUID
            # ==========================

            if self.regex_uuid.match(
                    identifiant
            ):
                continue

            # ==========================
            # Ancien identifiant HAB
            # ==========================

            if self.regex_hab.match(
                    identifiant
            ):
                continue

            # ==========================
            # Identifiant invalide
            # ==========================

            self.rapport["erreurs"].append(
                f"Ligne {numero} : "
                f"ID invalide ({identifiant})"
            )

        # ==========================================
        # Incohérence entre ID Excel et ID SQLite
        # ==========================================

        for numero, ligne in self.df_excel.iterrows():

            identifiant_excel = str(
                ligne.get("ID", "")
            ).strip()

            # Pas d'ID Excel → rien à comparer
            if not identifiant_excel:
                continue

            # Identité métier Excel
            cle_excel = self._cle_identite(ligne)

            # Recherche du salarié par identité métier
            correspondances = []

            for _, ligne_sql in self.df_sql.iterrows():

                if self._cle_identite(ligne_sql) == cle_excel:

                    id_sql = str(
                        ligne_sql.get("ID", "")
                    ).strip()

                    if id_sql:
                        correspondances.append(id_sql)

            # Une seule personne trouvée en DB
            if len(correspondances) == 1:

                id_sql = correspondances[0]

                # ID différent
                if identifiant_excel != id_sql:
                    incoherence = {
                        "ligne_excel": numero + 2,
                        "identite": {
                            "secteur": cle_excel[2],
                            "nom": cle_excel[0],
                            "prenom": cle_excel[1],
                        },
                        "id_excel": identifiant_excel,
                        "id_sqlite": id_sql,
                    }

                    self.rapport["incoherences_id"].append(
                        incoherence
                    )

                    self.rapport["avertissements"].append(
                        f"Ligne {numero + 2} : "
                        f"incohérence d'ID pour "
                        f"{cle_excel[2]} — "
                        f"{cle_excel[0]} {cle_excel[1]}."
                    )

    def verifier_doublons(self):
        """
        Détecte les doublons de salariés dans le fichier Excel.

        L'identité métier est :
            Secteur + Nom + Prénom

        Cette fonction analyse uniquement le fichier Excel.
        Elle ne modifie jamais SQLite.

        Les lignes concernées sont enregistrées dans le rapport
        afin que la préparation des opérations puisse les traiter
        avec prudence.
        """

        # ==================================================
        # 1. DOUBLONS D'ID
        # ==================================================

        if "ID" in self.df_excel.columns:

            ids = (
                self.df_excel["ID"]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            doublons_id = ids[
                (ids != "")
                & ids.duplicated(keep=False)
                ]

            if not doublons_id.empty:
                lignes = [
                    int(index) + 2
                    for index in doublons_id.index
                ]

                self.rapport["doublons_id"] = lignes

                self.rapport["avertissements"].append(
                    f"{len(lignes)} ligne(s) possèdent "
                    "le même identifiant ID dans le fichier Excel. "
                    "Ces lignes seront traitées avec prudence."
                )

        # ==================================================
        # 2. PRÉPARATION DE L'IDENTITÉ
        # ==================================================

        salaries = (
            self.df_excel[
                ["Secteur", "Nom", "Prénom"]
            ]
            .fillna("")
            .astype(str)
        )

        # Conserver les valeurs d'origine pour le rapport utilisateur.
        # La normalisation sans accents ne sert qu'à comparer les identités.
        salaries_comparaison = salaries.copy()
        for colonne in [
            "Secteur",
            "Nom",
            "Prénom"
        ]:
            salaries_comparaison[colonne] = salaries_comparaison[colonne].map(
                normaliser_texte_comparaison
            )

        # ==================================================
        # 3. VÉRIFICATION DE L'IDENTITÉ COMPLÈTE
        # ==================================================

        identite_complete = (
            (salaries_comparaison["Secteur"] != "")
            & (salaries_comparaison["Nom"] != "")
            & (salaries_comparaison["Prénom"] != "")
        )
        salaries = salaries.loc[identite_complete]
        salaries_comparaison = salaries_comparaison.loc[identite_complete]

        if salaries.empty:
            return

        # ==================================================
        # 4. RECHERCHE DES DOUBLONS
        # ==================================================

        doublons = salaries_comparaison.duplicated(
            subset=[
                "Secteur",
                "Nom",
                "Prénom"
            ],
            keep=False
        )

        if not doublons.any():
            return

        # ==================================================
        # 5. ENREGISTREMENT DES LIGNES CONCERNÉES
        # ==================================================

        indices_doublons = salaries.index[doublons]

        self.rapport["doublons_excel"] = [
            int(index) + 2
            for index in indices_doublons
        ]

        # ==================================================
        # 6. CONSTRUCTION DU RAPPORT
        # ==================================================

        salaries_doublons = salaries.loc[
            indices_doublons
        ]

        details = []

        for _, salarie in salaries_doublons.iterrows():
            secteur = salarie["Secteur"]
            nom = salarie["Nom"]
            prenom = salarie["Prénom"]

            details.append(
                f"- {secteur} — {nom} {prenom}"
            )

        # Suppression des doublons dans le message
        details = list(
            dict.fromkeys(details)
        )

        message = (
                "Doublon détecté dans le fichier Excel.\n\n"
                "L'identité utilisée pour la synchronisation est :\n"
                "Secteur + Nom + Prénom\n\n"
                "Salarié(s) concerné(s) :\n"
                + "\n".join(details)
                + "\n\n"
                  "Ces lignes sont signalées dans le rapport "
                  "et ne devront pas être traitées automatiquement "
                  "afin d'éviter une mauvaise attribution "
                  "des dates de formation."
        )

        self.rapport["avertissements"].append(
            message
        )

    def verifier_dates(self):
        """
        Vérifie les dates du fichier Excel.

        Les dates invalides sont vidées automatiquement
        puis signalées dans le rapport.
        """

        colonnes_dates = HabilitationManager.lister()

        for colonne in colonnes_dates:

            if colonne not in self.df_excel.columns:
                continue

            for index, valeur in self.df_excel[colonne].items():

                numero = index + 2

                if pd.isna(valeur):
                    continue

                if isinstance(valeur, pd.Timestamp):
                    continue

                valeur = str(valeur).strip()

                if valeur == "":
                    continue

                try:

                    # ==========================================
                    # Date commençant par une année : ISO
                    # ==========================================

                    if (
                            valeur[:4].isdigit()
                            and valeur[:4].startswith("20")
                    ):

                        pd.to_datetime(
                            valeur,
                            format="mixed",
                            dayfirst=False
                        )

                    # ==========================================
                    # Date française : JJ/MM/AAAA ou JJ-MM-AAAA
                    # ==========================================

                    else:

                        pd.to_datetime(
                            valeur,
                            format="mixed",
                            dayfirst=True
                        )

                except Exception:

                    # ==========================================
                    # Correction automatique
                    # ==========================================

                    self.df_excel.at[
                        index,
                        colonne
                    ] = ""

                    self.rapport["avertissements"].append(

                        f"Ligne {numero} - "
                        f"{colonne} : "
                        f"date invalide supprimée."

                    )

    # ======================================================
    # NORMALISATION
    # ======================================================

    def normaliser(self):
        """
        Prépare le DataFrame Excel sans perdre les nouvelles
        habilitations détectées lors de l'analyse.

        SQLite n'est jamais modifiée ici.
        """

        # ======================================================
        # NORMALISATION DES NOMS DE COLONNES
        # ======================================================

        self.df_excel = normaliser_colonnes(
            self.df_excel
        )

        # Suppression des doublons de colonnes éventuels
        self.df_excel = self.df_excel.loc[
            :,
            ~self.df_excel.columns.duplicated()
        ]

        # ======================================================
        # COLONNES ATTENDUES
        # ======================================================

        colonnes_fixes = COLONNES_TECHNIQUES.copy()

        habilitations_existantes = HabilitationManager.lister()

        nouvelles_habilitations = self.rapport.get(
            "nouvelles_habilitations",
            []
        )

        # ======================================================
        # ORDRE DES HABILITATIONS
        # ======================================================

        ordre_habilitations_excel = self.rapport.get(
            "ordre_habilitations_excel",
            []
        )

        # Habilitations existantes absentes du fichier Excel
        habilitations_absentes_excel = [
            habilitation
            for habilitation in habilitations_existantes
            if habilitation not in ordre_habilitations_excel
        ]

        # Colonnes finales :
        # 1. colonnes techniques
        # 2. habilitations présentes dans Excel, dans l'ordre Excel
        # 3. anciennes habilitations absentes du fichier, conservées à la fin

        ordre_habilitations_excel = self.rapport.get(
            "ordre_habilitations_excel",
            []
        )

        colonnes_finales = list(
            dict.fromkeys(
                colonnes_fixes
                + ordre_habilitations_excel
                + [
                    habilitation
                    for habilitation in habilitations_existantes
                    if habilitation not in ordre_habilitations_excel
                ]
            )
        )

        # ======================================================
        # AJOUT DES COLONNES MANQUANTES
        # ======================================================

        for colonne in colonnes_finales:

            if colonne not in self.df_excel.columns:
                self.df_excel[colonne] = ""

        # ======================================================
        # CONSERVATION DES COLONNES UTILES
        # ======================================================

        self.df_excel = self.df_excel.reindex(
            columns=colonnes_finales,
            fill_value=""
        )

        self.df_excel = self.df_excel.fillna("")

        # ======================================================
        # NORMALISATION DE L'IDENTITÉ
        # ======================================================

        self.df_excel["Nom"] = (
            self.df_excel["Nom"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        self.df_excel["Prénom"] = (
            self.df_excel["Prénom"]
            .astype(str)
            .str.strip()
            .str.title()
        )

        self.df_excel["Secteur"] = (
            self.df_excel["Secteur"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

    def nettoyer(self):
        """
        Supprime uniquement les lignes totalement vides du fichier Excel.

        Les identités incomplètes sont déjà détectées et bloquées
        par verifier_id().
        """

        self.df_excel = self.df_excel[
            ~(
                    self.df_excel["Secteur"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .eq("")
                    &
                    self.df_excel["Nom"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .eq("")
                    &
                    self.df_excel["Prénom"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .eq("")
            )
        ]

    def _synchroniser_par_identite(self):
        """
        Prépare les opérations d'import à partir de l'identité métier :

            Secteur + Nom + Prénom

        IMPORTANT :
            Cette fonction NE MODIFIE PAS SQLite.

        Elle prépare uniquement les opérations :

            - INSERT   : nouveau salarié
            - UPDATE   : salarié existant
            - DOUBLON  : ligne Excel en doublon
            - AMBIGU   : plusieurs correspondances possibles
        """

        # ==================================================
        # 1. CONSTRUIRE L'INDEX DES SALARIÉS SQLITE
        # ==================================================

        salaries_sql = {}

        for _, ligne_sql in self.df_sql.iterrows():

            cle = self._cle_identite(ligne_sql)

            if not all(cle):
                continue

            id_sql = str(
                ligne_sql.get("ID", "")
            ).strip()

            if not id_sql:
                continue

            salaries_sql.setdefault(
                cle,
                []
            ).append(id_sql)

        # ==================================================
        # 2. RÉCUPÉRER LES LIGNES EXCEL À EXCLURE
        # ==================================================

        doublons_excel = set(
            self.rapport.get(
                "doublons_excel",
                []
            )
        )

        doublons_id = set(
            self.rapport.get(
                "doublons_id",
                []
            )
        )

        incoherences_id = {
            incoherence["ligne_excel"]
            for incoherence in self.rapport.get(
                "incoherences_id",
                []
            )
        }

        # ==================================================
        # 3. PRÉPARATION DES OPÉRATIONS
        # ==================================================

        operations = []

        for numero, ligne in self.df_excel.iterrows():

            # Numéro réel de ligne Excel
            ligne_excel = numero + 2

            # --------------------------------------------------
            # DOUBLON DÉTECTÉ
            # --------------------------------------------------

            if (
                    ligne_excel in doublons_excel
                    or ligne_excel in doublons_id
            ):
                cle = self._cle_identite(ligne)

                operations.append({
                    "action": "DOUBLON",
                    "ligne_excel": ligne_excel,
                    "identite": {
                        "secteur": cle[2],
                        "nom": cle[0],
                        "prenom": cle[1],
                    },
                    "donnees": ligne.to_dict(),
                })

                continue

            # --------------------------------------------------
            # INCOHÉRENCE D'ID
            # --------------------------------------------------

            if ligne_excel in incoherences_id:
                continue

            # --------------------------------------------------
            # RECHERCHE PAR IDENTITÉ
            # --------------------------------------------------

            cle = self._cle_identite(ligne)

            correspondances = salaries_sql.get(
                cle,
                []
            )

            # --------------------------------------------------
            # SALARIÉ EXISTANT
            # --------------------------------------------------

            if len(correspondances) == 1:
                id_sql = correspondances[0]

                operations.append({
                    "action": "UPDATE",
                    "ligne_excel": ligne_excel,
                    "id": id_sql,
                    "donnees": ligne.to_dict(),
                })

                continue

            # --------------------------------------------------
            # HOMONYME / AMBIGU
            # --------------------------------------------------

            if len(correspondances) > 1:
                operations.append({
                    "action": "AMBIGU",
                    "ligne_excel": ligne_excel,
                    "identite": {
                        "secteur": cle[2],
                        "nom": cle[0],
                        "prenom": cle[1],
                    },
                    "correspondances": correspondances,
                    "donnees": ligne.to_dict(),
                })

                continue

            # --------------------------------------------------
            # NOUVEAU SALARIÉ
            # --------------------------------------------------

            nouvel_id = generer_id()

            operations.append({
                "action": "INSERT",
                "ligne_excel": ligne_excel,
                "id": nouvel_id,
                "donnees": {
                    **ligne.to_dict(),
                    "ID": nouvel_id,
                },
            })

        # ==================================================
        # 4. STOCKAGE DES OPÉRATIONS
        # ==================================================

        self.operations_import = operations

        # ==================================================
        # 5. SYNTHÈSE DU RAPPORT
        # ==================================================

        self.rapport["ajoutes"] = sum(
            1
            for op in operations
            if op["action"] == "INSERT"
        )

        self.rapport["modifies"] = sum(
            1
            for op in operations
            if op["action"] == "UPDATE"
        )

        self.rapport["doublons"] = [
            op
            for op in operations
            if op["action"] == "DOUBLON"
        ]

        self.rapport["homonymes"] = [
            op
            for op in operations
            if op["action"] == "AMBIGU"
        ]

    def appliquer_import(self):
        """
        Applique les opérations préparées par l'analyse.

        IMPORTANT :
            Cette méthode ne doit être appelée qu'après
            validation explicite de l'utilisateur.

        Les opérations DOUBLON et AMBIGU ne sont pas appliquées.
        Toutes les opérations sont exécutées dans une seule
        transaction SQLite.
        """

        if not self.analyse_terminee:
            raise RuntimeError(
                "Impossible d'appliquer l'import : "
                "l'analyse n'a pas été exécutée."
            )

        resultat = appliquer_operations(
            operations=self.operations_import,
            nouvelles_habilitations=self.rapport.get(
                "nouvelles_habilitations",
                []
            ),
            ordre_habilitations=self.rapport.get(
                "ordre_habilitations_excel",
                []
            ),
        )

        # Mise à jour du rapport avec le résultat réel
        self.rapport["ajoutes"] = resultat["ajoutes"]
        self.rapport["modifies"] = resultat["modifies"]

        log_info(
            f"Import Excel validé : "
            f"{resultat['ajoutes']} ajout(s), "
            f"{resultat['modifies']} modification(s)"
        )

        return resultat

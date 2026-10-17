from recherche_manager import RechercheManager
from message_manager import MessageManager
from session_manager import SessionManager
from utilisateur_manager import (
    UtilisateurManager,
    PROFILS)

from database import (
    initialiser_tables_systeme,
    initialiser_base_vide
)

from envoi_secteurs_manager import (
    envoyer_exports_secteurs as executer_envoi_secteurs
)
from habilitation_manager import HabilitationManager
from id_manager import generer_id

import os
import pandas as pd
from validation import normaliser_texte_comparaison
import tkinter as tk
from tkinter import simpledialog
import ttkbootstrap as ttk

from statistiques import calculer_alertes, obtenir_delai_alerte

from config import (
    VERSION,
    DOSSIER_EXPORTS
)

from mail_repository import (
    recuperer_parametres_mail,
    synchroniser_secteurs_mails,
    recuperer_mails_secteurs,
    sauvegarder_parametres_mail,
    enregistrer_mail_secteur,
    lire_historique_mails,
)

from validation import verifier_email

from data_manager import DataManager
from controle_manager import ControleManager
from pdf_manager import PDFManager

from statistiques import calculer_statistiques

from tkinter import (
    filedialog,
    messagebox)

from logger_manager import (log_info,
                            FICHIER_LOG,
                            log_warning)

from window_manager import WindowManager

from icon_manager import charger_icone

from dossier_manager import (
    creer_dossier_salarie,
    ouvrir_dossier_salarie,
    preparer_impression_document,
    renommer_document,
    supprimer_document,
    selectionner_document,
    copier_document,
    convertir_et_fusionner_documents,
    ouvrir_document
)

# ==========================================
# CONFIGURATION DES SCROLLBARS
# ==========================================

def creer_scrollbar(parent, orient, command):

    return tk.Scrollbar(
        parent,
        orient=orient,
        command=command,
        bg="#375a7f",
        troughcolor="#2b3e50",
        activebackground="#4e6a8a",
        highlightthickness=0,
        relief="flat"
    )

class GestionHabilitationsApp:

    def __init__(self, root):

        self.root = root

        # Initialise les tables système avant toute utilisation de la base

        initialiser_tables_systeme()

        # Initialise la table métier minimale si nécessaire

        initialiser_base_vide()

        self.root.minsize(970, 1020)

        try:
            self.root.state("zoomed")
        except:
            self.root.attributes("-zoomed", True)

        self.data = DataManager()

        self.recherche_manager = RechercheManager()

        # 1. UI (widgets d'abord)
        self.creer_bouton_parametres()
        self.creer_zone_recherche()
        self.creer_tableau_bord()
        self.creer_tableau()
        self.afficher_colonnes()

        if SessionManager.peut_modifier():
            self.creer_formulaire()

        self.creer_boutons()

        # 2. CHARGEMENT DONNÉES

        self.charger_tableau()

        # 3. ACTUALISATION AFFICHAGE

        self.maj_tableau_bord()

        # Fenêtre principale dans son état final
        # avant l'affichage éventuel des alertes.
        self.root.update_idletasks()

        try:
            self.root.state("zoomed")
        except:
            self.root.attributes("-zoomed", True)

        self.root.update_idletasks()

        # 4. ALERTES / LOGIQUE

        self.root.update()

        #self.verifier_alertes()

        # 5. GESTION DES FENETRES
        self.windows = WindowManager()

        self.messages = MessageManager(
            self.root,
            self.windows
        )

        self.root.title(f"Gestion des habilitations {VERSION}")

        # ==================================================
        # Gère le style des en-têtes du tableau
        # ==================================================
        style = ttk.Style()

        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 10, "bold")
        )

    def _ajuster_largeur_treeview(self):
        """
        Répartit la largeur disponible du Treeview
        entre les colonnes.
        """

        if not self.tree.winfo_exists():
            return

        colonnes = self.tree["columns"]

        if not colonnes:
            return

        largeur_tree = self.tree.winfo_width()

        if largeur_tree <= 1:
            return

        nombre_colonnes = len(colonnes)

        largeur = max(
            100,
            largeur_tree // nombre_colonnes
        )

        for colonne in colonnes:
            self.tree.column(
                colonne,
                width=largeur,
                minwidth=100,
                stretch=True
            )

    def charger_tableau(self):

        self.data.df = self.data.charger()

        # La configuration des mails doit refléter les secteurs auxquels
        # au moins un salarié est actuellement affilié.
        synchroniser_secteurs_mails()

        self.afficher_dataframe(
            self.data.df
        )

    def export_controles(self):

        HABILITATIONS = HabilitationManager.lister()

        lignes = []

        param = recuperer_parametres_mail()
        delai_alerte = int(param["delai_alerte"])

        for _, row in self.data.df.iterrows():

            for hab in HABILITATIONS:

                date = row[hab]

                if pd.isna(date):
                    continue

                statut = ControleManager.statut(
                    date,
                    delai_alerte
                )

                if "🟢" in statut:
                    continue

                lignes.append({
                    "Secteur": row["Secteur"],
                    "Nom": row["Nom"],
                    "Prénom": row["Prénom"],
                    "Formation": hab,
                    "Échéance": pd.to_datetime(date).strftime("%d/%m/%Y"),
                    "Statut": statut
                })

        if not lignes:
            self.messages.info(
                titre="Export",
                message="Aucune habilitation à exporter."
            )
            return

        df = pd.DataFrame(lignes)

        nom_fichier = os.path.join(
            DOSSIER_EXPORTS,
            "exports_habilitations_a_renouveler.xlsx",
        )

        df.to_excel(
            nom_fichier,
            index=False
        )

        from openpyxl import load_workbook
        from openpyxl.styles import Font, PatternFill

        wb = load_workbook(nom_fichier)
        ws = wb.active

        # Entêtes
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(
                "solid",
                fgColor="4472C4"
            )

        # Colonne Statut
        for row in ws.iter_rows(min_row=2):

            statut = str(row[5].value)

            if "🟢" in statut:

                row[5].fill = PatternFill(
                    "solid",
                    fgColor="C6EFCE"
                )

            elif "🟠" in statut:

                row[5].fill = PatternFill(
                    "solid",
                    fgColor="FFEB9C"
                )

            elif "🔴" in statut:

                row[5].fill = PatternFill(
                    "solid",
                    fgColor="FFC7CE"
                )

        # Largeur automatique
        for column in ws.columns:
            longueur = max(
                len(str(cell.value))
                if cell.value else 0
                for cell in column
            )

            ws.column_dimensions[
                column[0].column_letter
            ].width = longueur + 4

        wb.save(nom_fichier)

        wb.save(nom_fichier)

        log_info(
            f"Export Excel terminé : {nom_fichier}"
        )

        self.messages.info(
            titre="Export terminé",
            message=f"Fichier créé :\n{nom_fichier}"
        )

    def reinitialiser(self):

        # ==========================================
        # REMISE À ZÉRO DES CRITÈRES
        # ==========================================

        self.rech_nom.set("")
        self.rech_prenom.set("")
        self.rech_secteur.set("")
        self.rech_habilitation.set("")
        self.rech_statut.set("")

        # ==========================================
        # RÉAFFICHAGE DE TOUTES LES COLONNES
        # ==========================================

        self.afficher_colonnes()

        # ==========================================
        # RÉAFFICHAGE DE TOUS LES SALARIÉS
        # ==========================================

        self.afficher_dataframe(
            self.data.df
        )

    def afficher_tout(self):
        """
        Affiche tous les salariés possédant
        l'habilitation sélectionnée, quel que soit
        leur statut de validité.
        """

        # ==========================================
        # HABILITATION SÉLECTIONNÉE
        # ==========================================

        hab = self.rech_habilitation.get()

        # ==========================================
        # AUCUNE HABILITATION SÉLECTIONNÉE
        # ==========================================

        if not hab:
            self.afficher_colonnes()

            self.afficher_dataframe(
                self.data.df
            )

            return

        # ==========================================
        # COPIE DES DONNÉES
        # ==========================================

        df = self.data.df.copy()

        # ==========================================
        # SALARIÉS POSSÉDANT L'HABILITATION
        # ==========================================

        dates = pd.to_datetime(
            df[hab],
            errors="coerce"
        )

        df = df.loc[
            dates.notna()
        ].copy()

        # ==========================================
        # AFFICHAGE
        # ==========================================

        self.afficher_colonnes()

        self.afficher_dataframe(df)

    def afficher_graphiques(self):

        from loading_dialog import LoadingDialog
        from graphiques_manager import GraphiquesManager

        dialog = LoadingDialog(
            self.root,
            "Graphiques"
        )

        dialog.afficher()

        try:

            dialog.changer_message(
                "Étape 1 / 5\\n\\nPréparation des habilitations..."
            )

            plt_graph = GraphiquesManager.afficher_graphique(
                self.data.df,
                progression=dialog.changer_message,
            )

            dialog.fermer()

            plt_graph.show()

        finally:

            dialog.fermer()

    def importer_fichier(self):
        """
        Importe un fichier Excel.
        """

        if not SessionManager.peut_modifier():
            self.messages.warning(
                titre="Accès refusé",
                message="Vous n'avez pas les droits nécessaires pour importer un fichier Excel."
            )
            return

        # ==========================================
        # Choix du fichier
        # ==========================================

        fichier = filedialog.askopenfilename(
            filetypes=[("Excel", "*.xlsx")]
        )

        if not fichier:
            return

        # ==========================================
        # Fermeture de la fenêtre de travail
        # ==========================================

        self.windows.fermer()

        from loading_dialog import LoadingDialog
        from import_manager import ImportEngine

        # L'import Excel utilise une seule barre dès l'ouverture du dialogue.
        dialog = LoadingDialog(
            self.root,
            "Import Excel",
            progression_determinate=True,
            afficher_progression=False,
            details_import=True,
        )

        dialog.afficher()

        try:

            # ==========================================
            # Import avec progression dynamique
            # ==========================================

            dialog.changer_message("Préparation de l'import Excel...")

            moteur = ImportEngine(fichier)
            rapport = moteur.executer(
                progression=dialog.changer_message
            )

            # ==========================================
            # DOUBLONS DÉTECTÉS DANS LE FICHIER EXCEL
            # ==========================================

            doublons = rapport.get("doublons", [])

            if doublons:
                # Ferme la progression avant d'afficher l'avertissement modal.
                # Cela évite que la fenêtre de progression masque le message.
                dialog.fermer()

                # Regroupe les lignes Excel par identité afin de présenter
                # un message lisible, sans répéter le même salarié.
                doublons_par_identite = {}

                for doublon in doublons:
                    identite = doublon.get("identite", {})
                    secteur = str(identite.get("secteur", "")).strip()
                    nom = str(identite.get("nom", "")).strip()
                    prenom = str(identite.get("prenom", "")).strip()
                    cle = (secteur, nom, prenom)

                    doublons_par_identite.setdefault(
                        cle, []
                    ).append(doublon.get("ligne_excel"))

                details_doublons = []

                for (secteur, nom, prenom), lignes in doublons_par_identite.items():
                    lignes = sorted(
                        {ligne for ligne in lignes if ligne is not None}
                    )
                    lignes_texte = ", ".join(
                        str(ligne) for ligne in lignes
                    ) or "non précisée"

                    details_doublons.append(
                        f"• {secteur} — {nom} {prenom}\n"
                        f"  Lignes Excel : {lignes_texte}"
                    )

                self.messages.warning(
                    titre="⚠️ Doublons détectés dans le fichier Excel",
                    message=(
                        "Le même salarié apparaît plusieurs fois dans le fichier Excel.\n\n"
                        + "\n\n".join(details_doublons)
                        + "\n\nAucune de ces lignes en doublon ne sera importée. "
                          "La fiche déjà présente dans l'application ne sera pas modifiée par ces lignes.\n\n"
                          "Les autres lignes non concernées pourront être importées après confirmation."
                    )
                )

            # ==========================================
            # HOMONYMES DÉTECTÉS
            # ==========================================

            homonymes = rapport.get("homonymes", [])

            if homonymes:

                details = []

                for homonyme in homonymes:
                    details.append(
                        f"• {homonyme['secteur']} — "
                        f"{homonyme['nom']} {homonyme['prenom']}\n"
                        f"  IDs concernés : "
                        f"{', '.join(homonyme['ids'])}"
                    )

                self.messages.warning(
                    titre="⚠️ Homonymes détectés",
                    message=(
                            "Plusieurs salariés correspondent à la même "
                            "identité :\n\n"
                            "Secteur + Nom + Prénom\n\n"
                            + "\n\n".join(details)
                            + "\n\n"
                              "Aucune modification de formation n'a été "
                              "effectuée pour ces salariés afin d'éviter "
                              "une mauvaise attribution des dates."
                    )
                )

            # ==========================================
            # Vérification
            # ==========================================

            if rapport["erreurs"]:
                dialog.fermer()

                self.messages.error(
                    titre=("Import impossible"),
                    message=("\n".join(
                        rapport["erreurs"]
                    ))
                )

                return

            # ==========================================
            # CONFIRMATION DE L'IMPORT
            # ==========================================

            message_confirmation = (
                "Analyse de l'import terminée.\n\n"
                f"Ajouts prévus : {rapport.get('ajoutes', 0)}\n"
                f"Modifications prévues : {rapport.get('modifies', 0)}"
            )

            avertissements = rapport.get(
                "avertissements",
                []
            )

            # Les doublons Excel ont déjà fait l'objet d'une fenêtre dédiée.
            # On évite de répéter exactement le même avertissement dans la confirmation.
            avertissements = [
                avertissement
                for avertissement in avertissements
                if not avertissement.startswith(
                    "Doublon détecté dans le fichier Excel."
                )
            ]

            if avertissements:
                message_confirmation += (
                        "\n\nAvertissements :\n"
                        + "\n\n".join(avertissements)
                )

            message_confirmation += (
                "\n\n"
                "Voulez-vous valider cet import ?"
            )

            dialog.fermer()

            if not self.messages.confirm(
                    titre="Validation de l'import",
                    message=message_confirmation
            ):
                log_warning(
                    "Import Excel annulé par l'utilisateur"
                )
                return

            # ==========================================
            # APPLICATION DE L'IMPORT VALIDÉ
            # ==========================================

            try:
                rapport = moteur.appliquer_import()

            except Exception as erreur:
                self.messages.error(
                    titre="Erreur d'importation",
                    message=str(erreur)
                )
                return

            # ==========================================
            # Rafraîchissement GUI
            # ==========================================

            self.rafraichir_application()

            # ==========================================
            # Rapport utilisateur
            # ==========================================

            self.messages.resultat_import(rapport)


        except Exception as erreur:

            dialog.fermer()

            raise

    # ==================================================
    # RECHERCHE
    # ==================================================

    def creer_zone_recherche(self):

        cadre = ttk.Labelframe(
            self.root,
            text="Recherche",
            bootstyle="info"
        )

        cadre.pack(anchor="center")

        self.rech_nom = tk.StringVar()
        self.rech_prenom = tk.StringVar()
        self.rech_secteur = tk.StringVar()
        self.rech_habilitation = tk.StringVar()
        self.rech_statut = tk.StringVar()

        # =========================
        # Ligne 1
        # =========================

        ttk.Label(
            cadre,
            text="Nom",
            font=("Segoe UI", 10)
        ).grid(
            row=0,
            column=0,
            padx=5,
            pady=5,
            sticky="w"
        )

        entry_nom = ttk.Entry(
            cadre,
            textvariable=self.rech_nom,
            width=25,
            font=("Segoe UI", 10)
        )

        entry_nom.grid(
            row=0,
            column=1,
            padx=5,
            pady=5
        )

        entry_nom.bind(
            "<KeyRelease>",
            lambda e: self.rechercher()
        )

        ttk.Label(
            cadre,
            text="Prénom",
            font=("Segoe UI", 10)
        ).grid(
            row=0,
            column=2,
            padx=5,
            pady=5,
            sticky="w"
        )

        entry_prenom = ttk.Entry(
            cadre,
            textvariable=self.rech_prenom,
            width=25,
            font=("Segoe UI", 10)
        )

        entry_prenom.grid(
            row=0,
            column=3,
            padx=5,
            pady=5
        )

        entry_prenom.bind(
            "<KeyRelease>",
            lambda e: self.rechercher()
        )

        ttk.Label(
            cadre,
            text="Secteur",
            font=("Segoe UI", 10)
        ).grid(
            row=0,
            column=4,
            padx=5,
            pady=5,
            sticky="w"
        )

        entry_secteur = ttk.Entry(
            cadre,
            textvariable=self.rech_secteur,
            width=25,
            font=("Segoe UI", 10)
        )

        entry_secteur.grid(
            row=0,
            column=5,
            padx=5,
            pady=5
        )

        entry_secteur.bind(
            "<KeyRelease>",
            lambda e: self.rechercher()
        )

        self.icone_reinitialiser = charger_icone(
            "rotate-ccw", 12
        )

        ttk.Button(
            cadre,
            text="Réinitialiser",
            image=self.icone_reinitialiser,
            compound="left",
            command=self.reinitialiser,
            bootstyle="secondary"
        ).grid(
            row=0,
            column=7,
            padx=5
        )

        # =========================
        # Ligne 2
        # =========================

        ttk.Label(
            cadre,
            text="Statut",
            font=("Segoe UI", 10)
        ).grid(
            row=1,
            column=0,
            padx=5,
            pady=5,
            sticky="w"
        )

        combo_statut = ttk.Combobox(
            cadre,
            textvariable=self.rech_statut,
            state="readonly",
            width=22,
            font=("Segoe UI", 10)
        )

        # Paramètres de l'application
        param = recuperer_parametres_mail()

        delai_alerte = param["delai_alerte"]

        # Liste des statuts
        combo_statut["values"] = (
            "",
            "Valide",
            f"< {delai_alerte} jours",
            "Expirée"
        )

        combo_statut.grid(
            row=1,
            column=1,
            padx=5,
            pady=5
        )

        combo_statut.bind(
            "<<ComboboxSelected>>",
            lambda e: self.rechercher()
        )

        ttk.Label(
            cadre,
            text="Formation",
            font=("Segoe UI", 10)
        ).grid(
            row=1,
            column=2,
            padx=5,
            pady=5,
            sticky="w"
        )

        self.combo_hab = ttk.Combobox(
            cadre,
            textvariable=self.rech_habilitation,
            state="readonly",
            width=22,
            font=("Segoe UI", 10)
        )

        self.combo_hab["values"] = (
            "",
            *HabilitationManager.lister()
        )

        self.combo_hab.grid(
            row=1,
            column=3,
            padx=5,
            pady=5
        )

        self.combo_hab.bind(
            "<<ComboboxSelected>>",
            lambda e: self.rechercher()
        )

    # ==================================================
    # TABLEAU
    # ==================================================

    def creer_tableau(self):

        # ==========================================
        # Si un ancien tableau existe
        # ==========================================

        if hasattr(self, "cadre_tableau"):
            self.cadre_tableau.destroy()

        # ==========================================
        # Récupération des habilitations
        # ==========================================

        HABILITATIONS = HabilitationManager.lister()

        # ==========================================
        # Cadre principal
        # ==========================================

        self.cadre_tableau = ttk.Frame(
            self.root
        )

        self.cadre_tableau.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=(20, 5)
        )

        # ==========================================
        # Colonnes dynamiques
        # ==========================================

        colonnes_affichees = [
            "Secteur",
            "Nom",
            "Prénom",
            *HABILITATIONS
        ]

        # ==========================================
        # Treeview
        # ==========================================

        self.tree = ttk.Treeview(
            self.cadre_tableau,
            columns=colonnes_affichees,
            show="headings"
        )

        # ==========================================
        # Colonnes personnelles
        # ==========================================

        for colonne in (
                "Secteur",
                "Nom",
                "Prénom"
        ):
            self.tree.heading(
                colonne,
                text=colonne,
                anchor="w"
            )

            self.tree.column(
                colonne,
                width=150,
                anchor="w"
            )

        # ==========================================
        # Colonnes habilitations
        # ==========================================

        for hab in HABILITATIONS:
            self.tree.heading(
                hab,
                text=hab,
                anchor="center"
            )

            self.tree.column(
                hab,
                width=120,
                anchor="center"
            )

        # ==========================================
        # Scrollbar verticale
        # ==========================================

        scroll_y = creer_scrollbar(
            self.cadre_tableau,
            "vertical",
            self.tree.yview
        )

        # ==========================================
        # Scrollbar horizontale
        # ==========================================

        scroll_x = creer_scrollbar(
            self.cadre_tableau,
            "horizontal",
            self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        # ==========================================
        # Placement
        # ==========================================

        self.tree.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        scroll_y.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        scroll_x.grid(
            row=1,
            column=0,
            sticky="ew"
        )

        # ==========================================
        # Expansion du tableau
        # ==========================================

        self.cadre_tableau.grid_rowconfigure(
            0,
            weight=1
        )

        self.cadre_tableau.grid_columnconfigure(
            0,
            weight=1
        )

        # ==========================================
        # Double-clic sur un salarié
        # ==========================================

        if SessionManager.peut_modifier():
            self.tree.bind(
                "<Double-1>",
                self.charger_ligne
            )

    def actualiser_colonnes_tableau(self):

        # ==========================================
        # 1. Recréer uniquement le tableau dynamique
        # ==========================================

        self.creer_tableau()

        # ==========================================
        # 2. Réafficher les données
        # ==========================================

        self.afficher_dataframe(
            self.data.df
        )

        # ==========================================
        # 3. Replacer le tableau avant la Fiche salarié
        # ==========================================

        if hasattr(self, "cadre_formulaire"):
            self.cadre_tableau.pack(
                fill="both",
                expand=True,
                padx=5,
                pady=5,
                before=self.cadre_formulaire
            )

        # ==========================================
        # 4. Actualiser le tableau de bord
        # ==========================================

        self.maj_tableau_bord()

        # ==========================================
        # 5. Mise à jour graphique
        # ==========================================

        self.root.update_idletasks()

    # ==================================================
    # FORMULAIRE
    # ==================================================

    def creer_formulaire(self):

        # ==========================================
        # Supprimer l'ancienne Fiche salarié
        # ==========================================

        if hasattr(self, "cadre_formulaire"):
            self.cadre_formulaire.destroy()

        HABILITATIONS = HabilitationManager.lister()

        # ==========================================
        # Cadre principal
        # ==========================================

        self.cadre_formulaire = ttk.Labelframe(
            self.root,
            text="Fiche salarié",
            bootstyle="primary"
        )

        # ==========================================
        # Positionnement de la Fiche salarié
        # ==========================================

        if hasattr(self, "cadre_boutons"):

            self.cadre_formulaire.pack(
                anchor="center",
                padx=10,
                pady=10,
                before=self.cadre_boutons
            )

        else:

            self.cadre_formulaire.pack(
                anchor="center",
                padx=10,
                pady=10
            )

        # Hauteur fixe de la fiche
        self.cadre_formulaire.configure(
            height=320
        )

        self.cadre_formulaire.pack_propagate(False)

        # ==========================================
        # Variables
        # ==========================================

        self.champs = {}

        self.champs["Secteur"] = tk.StringVar()
        self.champs["Nom"] = tk.StringVar()
        self.champs["Prénom"] = tk.StringVar()

        self.dates = {}

        # ==========================================
        # Zone informations salarié
        # ==========================================

        cadre_infos = ttk.Frame(
            self.cadre_formulaire
        )

        cadre_infos.grid(
            row=0,
            column=0,
            padx=10,
            pady=10,
            sticky="n"
        )

        # ==========================================
        # Secteur
        # ==========================================

        ttk.Label(
            cadre_infos,
            text="Secteur",
            font=("Segoe UI", 10)
        ).grid(
            row=0,
            column=0,
            padx=5,
            pady=3,
            sticky="w"
        )

        self.secteur = ttk.Entry(
            cadre_infos,
            textvariable=self.champs["Secteur"],
            width=30,
            font=("Segoe UI", 10)
        )

        self.secteur.grid(
            row=0,
            column=1,
            padx=5,
            pady=3
        )

        # ==========================================
        # Nom
        # ==========================================

        ttk.Label(
            cadre_infos,
            text="Nom",
            font=("Segoe UI", 10)
        ).grid(
            row=1,
            column=0,
            padx=5,
            pady=3,
            sticky="w"
        )

        self.nom = ttk.Entry(
            cadre_infos,
            textvariable=self.champs["Nom"],
            width=30,
            font=("Segoe UI", 10)
        )

        self.nom.grid(
            row=1,
            column=1,
            padx=5,
            pady=3
        )

        # ==========================================
        # Prénom
        # ==========================================

        ttk.Label(
            cadre_infos,
            text="Prénom",
            font=("Segoe UI", 10)
        ).grid(
            row=2,
            column=0,
            padx=5,
            pady=3,
            sticky="w"
        )

        self.prenom = ttk.Entry(
            cadre_infos,
            textvariable=self.champs["Prénom"],
            width=30,
            font=("Segoe UI", 10)
        )

        self.prenom.grid(
            row=2,
            column=1,
            padx=5,
            pady=3
        )

        # ==========================================
        # Zone scrollable des habilitations
        # ==========================================

        cadre_scroll = ttk.Frame(
            self.cadre_formulaire
        )

        cadre_scroll.grid(
            row=0,
            column=1,
            padx=10,
            pady=5,
            sticky="ns"
        )

        # ==========================================
        # Canvas
        # ==========================================

        canvas = tk.Canvas(
            cadre_scroll,
            width=300,
            height=270,
            highlightthickness=0,
            bg=self.root.cget("bg")
        )

        canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        # ==========================================
        # Scrollbar verticale
        # ==========================================

        scrollbar = creer_scrollbar(
            cadre_scroll,
            "vertical",
            canvas.yview
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        canvas.configure(
            yscrollcommand=scrollbar.set
        )

        # ==========================================
        # Cadre interne du Canvas
        # ==========================================

        cadre_habilitations = ttk.Frame(
            canvas
        )

        canvas.create_window(
            (0, 0),
            window=cadre_habilitations,
            anchor="nw"
        )

        # ==========================================
        # Mise à jour zone scrollable
        # ==========================================

        def mettre_a_jour_scroll(event=None):

            canvas.configure(
                scrollregion=canvas.bbox("all")
            )

        cadre_habilitations.bind(
            "<Configure>",
            mettre_a_jour_scroll
        )

        # ==========================================
        # Habilitations dynamiques
        # ==========================================

        for i, hab in enumerate(HABILITATIONS):
            ttk.Label(
                cadre_habilitations,
                text=hab,
                font=("Segoe UI", 10)
            ).grid(
                row=i,
                column=0,
                padx=10,
                pady=3,
                sticky="w"
            )

            self.dates[hab] = ttk.Entry(
                cadre_habilitations,
                width=15,
                font=("Segoe UI", 10)
            )

            self.dates[hab].grid(
                row=i,
                column=1,
                padx=5,
                pady=3
            )

        # ==========================================
        # Défilement avec la molette
        # Linux + Windows
        # ==========================================

        def defiler_molette(event):

            widget = event.widget

            # Vérifie si le widget sous la souris
            # appartient à la zone des habilitations
            while widget is not None:

                if widget == cadre_habilitations:

                    # Linux : molette vers le haut
                    if event.num == 4:

                        canvas.yview_scroll(
                            -1,
                            "units"
                        )

                    # Linux : molette vers le bas
                    elif event.num == 5:

                        canvas.yview_scroll(
                            1,
                            "units"
                        )

                    # Windows
                    elif event.delta:

                        canvas.yview_scroll(
                            int(
                                -1 * (
                                        event.delta / 120
                                )
                            ),
                            "units"
                        )

                    return "break"

                try:

                    widget = widget.master

                except AttributeError:

                    break

        # ==========================================
        # Activation molette globale
        # ==========================================

        self.root.bind_all(
            "<MouseWheel>",
            defiler_molette
        )

        self.root.bind_all(
            "<Button-4>",
            defiler_molette
        )

        self.root.bind_all(
            "<Button-5>",
            defiler_molette
        )

        # ==========================================
        # Donner le focus et suivre le champ
        # ==========================================

        def focus_et_scroll(widget):

            # ==========================================
            # Donner le focus
            # ==========================================

            widget.focus_set()

            # Mise à jour des dimensions
            self.root.update_idletasks()

            # ==========================================
            # Si le widget n'est pas dans la zone
            # scrollable, aucun déplacement
            # ==========================================

            parent = widget.master

            est_habilitation = False

            while parent is not None:

                if parent == cadre_habilitations:
                    est_habilitation = True
                    break

                parent = parent.master

            if not est_habilitation:
                return

            # ==========================================
            # Position du widget dans le cadre
            # des habilitations
            # ==========================================

            widget_y = widget.winfo_y()

            # Hauteur du widget
            widget_hauteur = widget.winfo_height()

            # Hauteur visible du Canvas
            canvas_hauteur = canvas.winfo_height()

            # ==========================================
            # Position actuelle du scroll
            # ==========================================

            scroll_region = canvas.bbox("all")

            if not scroll_region:
                return

            hauteur_totale = (
                    scroll_region[3] -
                    scroll_region[1]
            )

            # ==========================================
            # Position actuelle visible
            # ==========================================

            position_actuelle = (
                    canvas.yview()[0] *
                    hauteur_totale
            )

            position_basse = (
                    position_actuelle +
                    canvas_hauteur
            )

            widget_bas = (
                    widget_y +
                    widget_hauteur
            )

            # ==========================================
            # Champ au-dessus de la zone visible
            # ==========================================

            if widget_y < position_actuelle:

                nouvelle_position = widget_y

                canvas.yview_moveto(
                    nouvelle_position /
                    hauteur_totale
                )

            # ==========================================
            # Champ en dessous de la zone visible
            # ==========================================

            elif widget_bas > position_basse:

                nouvelle_position = (
                        widget_bas -
                        canvas_hauteur
                )

                canvas.yview_moveto(
                    nouvelle_position /
                    hauteur_totale
                )

        # ==========================================
        # Navigation clavier
        # ==========================================

        widgets = [
            self.secteur,
            self.nom,
            self.prenom
        ]

        # Ajout dynamique des habilitations
        for hab in HABILITATIONS:
            widgets.append(
                self.dates[hab]
            )

        # ==========================================
        # Entrée + flèche bas
        # ==========================================

        for i in range(
                len(widgets) - 1
        ):
            widgets[i].bind(
                "<Return>",
                lambda e, w=widgets[i + 1]:
                focus_et_scroll(w)
            )

            widgets[i].bind(
                "<Down>",
                lambda e, w=widgets[i + 1]:
                focus_et_scroll(w)
            )

        # ==========================================
        # Flèche haut
        # ==========================================

        for i in range(
                1,
                len(widgets)
        ):
            widgets[i].bind(
                "<Up>",
                lambda e, w=widgets[i - 1]:
                focus_et_scroll(w)
            )

        # ==========================================
        # Dernier champ → Ajouter
        # ==========================================

        if widgets:
            widgets[-1].bind(
                "<Return>",
                lambda e: self.ajouter()
            )

        # ==========================================
        # Curseur initial
        # ==========================================

        self.secteur.focus_set()

        # ==========================================
        # Mise à jour finale du scroll
        # ==========================================

        self.root.update_idletasks()

        canvas.configure(
            scrollregion=canvas.bbox("all")
        )

    # ==================================================
    # BOUTONS
    # ==================================================

    def creer_boutons(self):

        # ==================================================
        # RECRÉATION DU CADRE
        # ==================================================

        if hasattr(self, "cadre_boutons"):
            self.cadre_boutons.destroy()

        self.cadre_boutons = ttk.Labelframe(
            self.root
        )

        self.cadre_boutons.pack(
            anchor="center"
        )

        cadre = self.cadre_boutons

        # ==================================================
        # DROITS MODIFICATION
        # ==================================================

        if SessionManager.peut_modifier():
            # ----------------------------------------------
            # Ajouter un salarié
            # ----------------------------------------------

            self.icone_ajouter = charger_icone(
                "circle-plus", 12
            )

            ttk.Button(
                cadre,
                text="Ajouter le salarié",
                image=self.icone_ajouter,
                compound="left",
                command=self.ajouter,
                bootstyle="success",
            ).pack(
                side="left"
            )

            # ----------------------------------------------
            # Ajouter un document
            # ----------------------------------------------

            self.icone_ajouter_document = charger_icone(
                "file-plus", 12
            )

            ttk.Button(
                cadre,
                text="Ajouter un document",
                image=self.icone_ajouter_document,
                compound="left",
                command=self.ajouter_document_salarie,
                bootstyle="secondary",
            ).pack(
                side="left"
            )

            # ----------------------------------------------
            # Modifier un salarié
            # ----------------------------------------------

            self.icone_modifier = charger_icone(
                "pencil", 12
            )

            ttk.Button(
                cadre,
                text="Modifier le salarié",
                image=self.icone_modifier,
                compound="left",
                command=self.modifier,
                bootstyle="warning",
            ).pack(
                side="left"
            )

            # ----------------------------------------------
            # Ouvrir le dossier
            # ----------------------------------------------

            self.icone_gerer_documents = charger_icone(
                "folder-open", 12
            )

            ttk.Button(
                cadre,
                text="Gérer les documents",
                image=self.icone_gerer_documents,
                compound="left",
                command=self.gerer_documents_salarie,
                bootstyle="secondary",
            ).pack(
                side="left"
            )

            # ----------------------------------------------
            # Supprimer un salarié
            # ----------------------------------------------

            self.icone_supprimer = charger_icone(
                "trash", 12
            )

            ttk.Button(
                cadre,
                text="Supprimer le salarié",
                image=self.icone_supprimer,
                compound="left",
                command=self.supprimer,
                bootstyle="danger",
            ).pack(
                side="left"
            )

            # ----------------------------------------------
            # Effacer le formulaire
            # ----------------------------------------------

            self.icone_effacer = charger_icone(
                "eraser", 12
            )

            ttk.Button(
                cadre,
                text="Effacer la fiche",
                image=self.icone_effacer,
                compound="left",
                command=self.effacer_formulaire,
                bootstyle="light",
            ).pack(
                side="left"
            )

        # ==================================================
        # DROITS CONSULTATION
        # ==================================================

        # ----------------------------------------------
        # Afficher tout
        # ----------------------------------------------

        self.icone_afficher_tout = charger_icone(
            "list", 12
        )

        ttk.Button(
            cadre,
            text="Afficher tout",
            image=self.icone_afficher_tout,
            compound="left",
            command=self.afficher_tout,
            bootstyle="dark",
        ).pack(
            side="left"
        )

        # ----------------------------------------------
        # Contrôle
        # ----------------------------------------------

        self.icone_controle = charger_icone(
            "eye", 12
        )

        ttk.Button(
            cadre,
            text="Contrôle",
            image=self.icone_controle,
            compound="left",
            command=self.controle,
            bootstyle="info",
        ).pack(
            side="left"
        )

        # ----------------------------------------------
        # PDF secteurs
        # ----------------------------------------------

        self.icone_pdf = charger_icone(
            "file-text", 12
        )

        ttk.Button(
            cadre,
            text="PDF secteurs",
            image=self.icone_pdf,
            compound="left",
            command=self.generer_pdf,
            bootstyle="dark",
        ).pack(
            side="left"
        )

        # ----------------------------------------------
        # Export contrôles
        # ----------------------------------------------

        self.icone_export_controles = charger_icone(
            "file-output", 12
        )

        ttk.Button(
            cadre,
            text="Export contrôles",
            image=self.icone_export_controles,
            compound="left",
            command=self.export_controles,
            bootstyle="secondary",
        ).pack(
            side="left"
        )

        # ----------------------------------------------
        # Graphiques
        # ----------------------------------------------

        self.icone_graphiques = charger_icone(
            "chart-no-axes-combined", 12
        )

        ttk.Button(
            cadre,
            text="Graphiques",
            image=self.icone_graphiques,
            compound="left",
            command=self.afficher_graphiques,
            bootstyle="light",
        ).pack(
            side="left"
        )

        # ==================================================
        # ENVOI DES ÉCHÉANCES
        # ==================================================

        if SessionManager.peut_modifier():
            self.icone_envoyer_secteurs = charger_icone(
                "send", 12
            )

            ttk.Button(
                cadre,
                text="Envoyer échéances secteurs",
                image=self.icone_envoyer_secteurs,
                compound="left",
                command=self.envoyer_exports_secteurs,
            ).pack(
                side="left",
                padx=3
            )

    def creer_bouton_parametres(self):

        if not SessionManager.est_administrateur():
            return

        cadre_param = ttk.Frame(self.root)

        cadre_param.pack(
            fill="x",
            padx=5,
            pady=5
        )

        self.icone_parametres = charger_icone(
            "settings", 20
        )

        ttk.Button(
            cadre_param,
            text="Paramètres",
            image=self.icone_parametres,
            compound="left",
            command=self.ouvrir_parametres,
            bootstyle="dark"
        ).pack(side="right")

    # ==================================================
    # TABLEAU DE BORD
    # ==================================================

    def creer_tableau_bord(self):

        cadre = ttk.Labelframe(
            self.root,
            text="Tableau de bord",
            bootstyle="success"
        )

        cadre.pack(anchor="center")

        self.icone_salaries = charger_icone(
            "users", 12
        )

        self.lbl_total = ttk.Label(
            cadre,
            text="Salariés : 0",
            image=self.icone_salaries,
            compound="left",
            font=("Segoe UI", 12)
        )

        self.lbl_total.pack(
            side="left",
            padx=20
        )

        self.icone_statut_valides = charger_icone("shield-check", 12)
        self.lbl_valides = ttk.Label(
            cadre,
            text="Valides : 0",
            image=self.icone_statut_valides,
            compound="left",
            font=("Segoe UI", 12)
        )

        self.lbl_valides.pack(
            side="left",
            padx=20
        )

        delai_alerte = obtenir_delai_alerte()

        self.icone_statut_echeance = charger_icone("clock-3", 12)
        self.lbl_45j = ttk.Label(
            cadre,
            text=f"< {delai_alerte} jours : 0",
            image=self.icone_statut_echeance,
            compound="left",
            font=("Segoe UI", 12)
        )

        self.lbl_45j.pack(
            side="left",
            padx=20
        )

        self.icone_statut_expirees = charger_icone("x", 12)
        self.lbl_expirees = ttk.Label(
            cadre,
            text="Expirées : 0",
            image=self.icone_statut_expirees,
            compound="left",
            font=("Segoe UI", 12)
        )

        self.lbl_expirees.pack(
            side="left",
            padx=20
        )

    # ==================================================
    # MISE A JOUR TABLEAU DE BORD
    # ==================================================

    def maj_tableau_bord(self):

        total = len(self.data.df)

        # Lire le délai une seule fois pour garantir la cohérence
        # entre les compteurs et le libellé affiché.
        delai_alerte = obtenir_delai_alerte()

        valides, echeance, expirees = calculer_statistiques(
            self.data.df,
            delai_alerte=delai_alerte,
        )

        self.lbl_total.config(
            text=f"Salariés : {total}"
        )

        self.lbl_valides.config(
            text=f"Valides : {valides}"
        )

        self.lbl_45j.config(
            text=f"< {delai_alerte} jours : {echeance}"
        )

        self.lbl_expirees.config(
            text=f"Expirées : {expirees}"
        )

    def afficher_colonnes(self):
        """
        Configure dynamiquement les colonnes du Treeview.

        - Secteur, Nom et Prénom sont alignés à gauche.
        - Les habilitations sont centrées.
        - Les colonnes utilisent automatiquement toute la largeur
          disponible lorsque celle-ci est suffisante.
        - Si le nombre de colonnes devient trop important,
          la scrollbar horizontale reste disponible.
        """

        # ==========================================
        # HABILITATIONS ACTUELLEMENT CONFIGURÉES
        # ==========================================

        HABILITATIONS = HabilitationManager.lister()

        # ==========================================
        # COLONNES COMPLÈTES
        # ==========================================

        colonnes = (
            "Secteur",
            "Nom",
            "Prénom",
            *HABILITATIONS
        )

        # ==========================================
        # DÉFINITION DES COLONNES
        # ==========================================

        self.tree["columns"] = colonnes

        # ==========================================
        # LARGEUR DISPONIBLE
        # ==========================================

        largeur_tree = self.tree.winfo_width()

        # Au premier affichage, la largeur peut encore
        # être inconnue. On demande donc à Tkinter de
        # terminer le calcul de la géométrie.

        if largeur_tree <= 1:
            self.root.update_idletasks()

            largeur_tree = self.tree.winfo_width()

        # ==========================================
        # LARGEUR MINIMALE
        # ==========================================

        largeur_minimale = 100

        # ==========================================
        # CALCUL AUTOMATIQUE
        # ==========================================

        nombre_colonnes = len(colonnes)

        if nombre_colonnes > 0 and largeur_tree > 1:

            largeur_calculee = max(
                largeur_minimale,
                largeur_tree // nombre_colonnes
            )

        else:

            largeur_calculee = 120

        # ==========================================
        # CONFIGURATION DES COLONNES
        # ==========================================

        for colonne in colonnes:

            # --------------------------------------
            # Alignement
            # --------------------------------------

            if colonne in (
                    "Secteur",
                    "Nom",
                    "Prénom"
            ):
                alignement = "w"
            else:
                alignement = "center"

            # --------------------------------------
            # En-tête
            # --------------------------------------

            self.tree.heading(
                colonne,
                text=colonne,
                anchor=alignement
            )

            # --------------------------------------
            # Colonne
            # --------------------------------------

            self.tree.column(
                colonne,
                width=largeur_calculee,
                minwidth=largeur_minimale,
                anchor=alignement,
                stretch=True
            )

        # ==========================================
        # FILTRE HABILITATION
        # ==========================================

        hab = self.rech_habilitation.get()

        if hab and hab in colonnes:

            self.tree["displaycolumns"] = (
                "Secteur",
                "Nom",
                "Prénom",
                hab
            )

        else:

            self.tree["displaycolumns"] = colonnes

        # ==========================================
        # NOUVEL AJUSTEMENT APRÈS AFFICHAGE
        # ==========================================

        self.root.after_idle(
            self._ajuster_largeur_treeview
        )

    # ==================================================
    # AFFICHAGE
    # ==================================================

    def afficher_dataframe(self, df):

        df = df.fillna("")

        colonnes = self.tree["columns"]

        df_original = df.copy()

        df = df.reindex(
            columns=colonnes,
            fill_value=""
        )

        # Tri alphabétique croissant par nom
        if "Nom" in df.columns:
            df = df.sort_values(
                by="Nom",
                key=lambda colonne: colonne.astype(str).str.casefold(),
                kind="stable",
                na_position="last",
            )

        self.tree.delete(
            *self.tree.get_children()
        )

        HABILITATIONS = HabilitationManager.lister()

        colonnes_dates = HABILITATIONS

        for i, row in df.iterrows():

            valeurs = []

            for col in colonnes:

                valeur = row[col]

                if (
                        col in colonnes_dates
                        and valeur not in ("", None)
                ):

                    date = pd.to_datetime(
                        valeur,
                        errors="coerce"
                    )

                    if pd.notna(date):
                        valeur = date.strftime("%d/%m/%Y")
                    else:
                        valeur = ""

                valeurs.append(valeur)

            iid = str(df_original.loc[i, "ID"])

            self.tree.insert(
                "",
                "end",
                iid=iid,
                values=tuple(valeurs)
            )

        self.root.update_idletasks()

    # ==================================================
    # CRUD
    # ==================================================

    def ajouter(self):

        if not SessionManager.peut_modifier():
            self.messages.warning(
                titre="Accès refusé",
                message="Vous n'avez pas les droits nécessaires pour ajouter un salarié."
            )
            return

        # Sécurité : ne jamais créer un nouveau salarié lorsqu'une fiche
        # est sélectionnée dans le tableau. Cela évite les doublons
        # lorsqu'un utilisateur charge une fiche pour ajouter une date.
        selection = self.tree.selection()
        if selection:
            self.messages.warning(
                titre="Salarié déjà sélectionné",
                message=(
                    "Un salarié est sélectionné.\n\n"
                    "Pour enregistrer une nouvelle date d'habilitation sur "
                    "cette fiche, utilisez « Modifier le salarié ».\n\n"
                    "Pour créer un nouveau salarié, cliquez d'abord sur "
                    "« Effacer » afin de désélectionner la fiche."
                )
            )
            return

        HABILITATIONS = HabilitationManager.lister()

        ligne = {}

        # Informations salarié
        secteur = self.champs["Secteur"].get().strip()
        nom = self.champs["Nom"].get().strip()
        prenom = self.champs["Prénom"].get().strip()

        # Vérification des informations obligatoires
        if not secteur or not nom or not prenom:
            self.messages.warning(
                titre="Informations incomplètes",
                message=(
                    "Veuillez renseigner le Secteur, "
                    "le Nom et le Prénom du salarié."
                )
            )

            return

        # Normalisation de saisie : les accents sont retirés avant la mise
        # en majuscules / en casse de titre pour éviter SÉCURITÉ ou ÉLODIE.
        # Cette règle concerne les nouvelles fiches créées manuellement.
        ligne["Secteur"] = normaliser_texte_comparaison(secteur).upper()
        ligne["Nom"] = normaliser_texte_comparaison(nom).upper()
        ligne["Prénom"] = normaliser_texte_comparaison(prenom).title()

        # Empêche la création d'un salarié déjà présent.
        # La clé métier est Secteur + Nom + Prénom, comme pour l'import Excel.
        df = self.data.df
        colonnes_identite = {"Secteur", "Nom", "Prénom"}
        if colonnes_identite.issubset(df.columns) and not df.empty:
            identite_existante = (
                df["Secteur"].fillna("").map(normaliser_texte_comparaison).eq(
                    normaliser_texte_comparaison(ligne["Secteur"])
                )
                & df["Nom"].fillna("").map(normaliser_texte_comparaison).eq(
                    normaliser_texte_comparaison(ligne["Nom"])
                )
                & df["Prénom"].fillna("").map(normaliser_texte_comparaison).eq(
                    normaliser_texte_comparaison(ligne["Prénom"])
                )
            )
            if identite_existante.any():
                self.messages.warning(
                    titre="Salarié déjà existant",
                    message=(
                        f"Le salarié {ligne['Nom']} {ligne['Prénom']} "
                        f"existe déjà dans le secteur {ligne['Secteur']}.\n\n"
                        "Aucun doublon n'a été créé. Sélectionnez sa fiche "
                        "pour la consulter ou la modifier."
                    )
                )
                return

        # ID unique
        ligne["ID"] = generer_id()

        # Habilitations
        for hab in HABILITATIONS:
            ligne[hab] = pd.to_datetime(
                self.dates[hab].get(),
                dayfirst=True,
                errors="coerce"
            )

        # Ajout au DataFrame via DataManager
        if not self.data.ajouter_salarie(ligne):
            self.messages.error(
                titre="Erreur d'ajout",
                message="Impossible d'ajouter le salarié."
            )
            return

        # Sauvegarde
        if not self.data.sauvegarder():
            self.messages.error(
                "Erreur",
                "Impossible de sauvegarder le salarié."
            )
            return

        creer_dossier_salarie(
            ligne["Nom"],
            ligne["Prénom"],
            ligne["ID"]
        )

        log_info(
            f"Ajout salarié : "
            f"{ligne['Nom']} {ligne['Prénom']} "
            f"- Secteur : {ligne['Secteur']}"
        )

        # Rafraîchissement affichage
        self.afficher_dataframe(
            self.data.df
        )

        # Mise à jour du tableau de bord
        self.maj_tableau_bord()

        # Nettoyage formulaire
        self.effacer_formulaire()

    def modifier(self):

        if not SessionManager.peut_modifier():
            self.messages.warning(
                titre="Accès refusé",
                message="Vous n'avez pas les droits nécessaires pour modifier un salarié."
            )
            return

        HABILITATIONS = HabilitationManager.lister()

        selection = self.tree.selection()

        if not selection:
            return

        # ID du salarié
        iid = selection[0]

        # Vérification de l'existence du salarié
        idx = self.data.df.index[
            self.data.df["ID"].astype(str) == str(iid)
            ]

        if len(idx) == 0:
            self.messages.error(
                titre="Erreur",
                message="Salarié introuvable."
            )
            return

        # ==========================
        # Construction de la ligne
        # ==========================

        ligne = {}

        ligne["Secteur"] = (
            self.champs["Secteur"]
            .get()
            .strip()
            .upper()
        )

        ligne["Nom"] = (
            self.champs["Nom"]
            .get()
            .strip()
            .upper()
        )

        ligne["Prénom"] = (
            self.champs["Prénom"]
            .get()
            .strip()
            .title()
        )

        # ==========================
        # Habilitations
        # ==========================

        for hab in HABILITATIONS:

            texte = (
                self.dates[hab]
                .get()
                .strip()
            )

            if texte == "":
                ligne[hab] = pd.NaT

            else:
                try:
                    ligne[hab] = pd.to_datetime(
                        texte,
                        format="%d/%m/%Y",
                        errors="raise"
                    )

                except Exception:
                    self.messages.error(
                        titre="Date invalide",
                        message=f"{hab} : {texte}"
                    )
                    return

        # ==========================
        # Modification via DataManager
        # ==========================

        if not self.data.modifier_salarie(
                iid,
                ligne
        ):
            self.messages.error(
                titre="Erreur de modification",
                message="Impossible de modifier le salarié."
            )
            return

        # ==========================
        # Sauvegarde
        # ==========================

        if not self.data.sauvegarder():
            self.messages.error(
                titre="Erreur de sauvegarde",
                message=(
                    "Les modifications ont été effectuées en mémoire, "
                    "mais la sauvegarde a échoué."
                )
            )
            return

        log_info(
            f"Modification salarié : "
            f"{ligne['Nom']} "
            f"{ligne['Prénom']} "
            f"- Secteur : "
            f"{ligne['Secteur']}"
        )

        # ==========================
        # Rafraîchissement
        # ==========================

        self.afficher_dataframe(
            self.data.df
        )

        self.maj_tableau_bord()

        self.effacer_formulaire()

    def supprimer(self):

        if not SessionManager.peut_modifier():
            self.messages.warning(
                titre="Accès refusé",
                message="Vous n'avez pas les droits nécessaires pour supprimer un salarié."
            )
            return

        selection = self.tree.selection()

        if not selection:
            return

        if not self.messages.confirm(
                titre="Confirmation",
                message="Supprimer ce salarié ?"
        ):
            return

        iid = selection[0]

        ligne = self.data.df[
            self.data.df["ID"] == iid
            ]

        if ligne.empty:
            return

        nom = ligne.iloc[0]["Nom"]
        prenom = ligne.iloc[0]["Prénom"]
        secteur = ligne.iloc[0]["Secteur"]

        # ==========================
        # Suppression du DataFrame
        # ==========================

        if not self.data.supprimer_salarie(iid):
            self.messages.error(
                "Suppression",
                "Impossible de supprimer le salarié."
            )
            return

        # ==========================
        # Sauvegarde
        # ==========================

        if not self.data.sauvegarder():
            self.messages.error(
                titre="Erreur de sauvegarde",
                message=(
                    "Le salarié a été supprimé en mémoire, "
                    "mais la sauvegarde a échoué."
                )
            )
            return

        log_info(
            f"Suppression salarié : "
            f"{nom} {prenom} "
            f"- Secteur : {secteur}"
        )

        # Rafraîchissement affichage
        self.afficher_dataframe(
            self.data.df
        )

        # Mise à jour du tableau de bord
        self.maj_tableau_bord()

    # ==================================================
    # UTILITAIRES
    # ==================================================

    def charger_ligne(self, event=None):

        HABILITATIONS = HabilitationManager.lister()

        # Récupère la sélection Treeview
        selection = self.tree.selection()

        if not selection:
            return

        iid = selection[0]

        # Récupère directement les valeurs affichées dans le tableau
        valeurs = self.tree.item(iid, "values")

        if not valeurs:
            return

        # -----------------------------------------
        # Champs principaux
        # -----------------------------------------

        self.champs["Secteur"].set(valeurs[0])
        self.champs["Nom"].set(valeurs[1])
        self.champs["Prénom"].set(valeurs[2])

        # -----------------------------------------
        # Habilitations (dates)
        # -----------------------------------------

        for i, hab in enumerate(HABILITATIONS, start=3):

            self.dates[hab].delete(0, tk.END)

            valeur = valeurs[i]

            # vide si None / vide
            if not valeur or valeur == "":
                continue

            # insertion directe (déjà formatée en affichage)
            self.dates[hab].insert(0, valeur)

    def effacer_formulaire(self):

        HABILITATIONS = HabilitationManager.lister()

        # Champs texte
        for champ in self.champs.values():
            champ.set("")

        # Dates habilitations
        for hab in HABILITATIONS:
            self.dates[hab].delete(0, tk.END)

        # Désélection du Treeview
        self.tree.selection_remove(
            self.tree.selection()
        )

        self.tree.focus("")

    def rechercher(self):

        self.afficher_colonnes()

        df = self.recherche_manager.rechercher(
            nom=self.rech_nom.get(),
            prenom=self.rech_prenom.get(),
            secteur=self.rech_secteur.get(),
            habilitation=self.rech_habilitation.get(),
            statut=self.rech_statut.get()
        )

        self.afficher_dataframe(df)

    # ==================================================
    # CONTROLE
    # ==================================================

    def controle(self):

        top = ttk.Toplevel(self.root)
        top.title("Contrôle des habilitations")
        top.geometry("1000x600")

        tree = ttk.Treeview(
            top,
            columns=(
                "Nom",
                "Prénom",
                "Habilitation",
                "Échéance",
                "Statut"
            ),
            show="headings"
        )

        # En-têtes
        for col in (
                "Nom",
                "Prénom",
                "Habilitation",
                "Échéance",
                "Statut"
        ):
            tree.heading(col, text=col)

        # Largeur des colonnes
        tree.column("Nom", width=150)
        tree.column("Prénom", width=150)
        tree.column("Habilitation", width=120)
        tree.column("Échéance", width=120, anchor="center")
        tree.column("Statut", width=180)

        # Couleurs des lignes
        tree.tag_configure(
            "valide",
            background="#C6EFCE",
            foreground="green",
            font=("Segoe UI", 9)
        )

        tree.tag_configure(
            "echeance",
            background="#FFEB9C",
            foreground="black",
            font=("Segoe UI", 10)
        )

        tree.tag_configure(
            "expire",
            background="#FFC7CE",
            foreground="red",
            font=("Segoe UI", 11, "bold")
        )

        # Analyse métier
        resultats = ControleManager.analyser_dataframe(
            self.data.df
        )

        # Affichage des résultats
        for resultat in resultats:

            statut = resultat["Statut"]

            if "🟢" in statut:
                tag = "valide"

            elif "🟠" in statut:
                tag = "echeance"

            elif "🔴" in statut:
                tag = "expire"

            else:
                tag = ""

            date = resultat["Échéance"]

            tree.insert(
                "",
                "end",
                values=(
                    resultat["Nom"],
                    resultat["Prénom"],
                    resultat["Habilitation"],
                    pd.to_datetime(
                        date
                    ).strftime("%d/%m/%Y"),
                    statut
                ),
                tags=(tag,)
            )

        tree.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

    # ==================================================
    # VERIFIER LES ALERTES
    # ==================================================

    def verifier_alertes(self):

        # Lire le délai une seule fois pour garantir la cohérence
        # entre le calcul des alertes et le texte affiché.
        delai_alerte = obtenir_delai_alerte()

        expirees, echeance = calculer_alertes(
            self.data.df,
            delai_alerte=delai_alerte,
        )

        # Rien à signaler
        if expirees == 0 and echeance == 0:
            return

        # Fenêtre d'alerte
        top = ttk.Toplevel(
            self.root
        )

        top.transient(
            self.root
        )

        top.grab_set()

        top.focus_force()

        top.title(
            "Alertes habilitations"
        )

        top.geometry(
            "550x220"
        )

        top.update_idletasks()

        largeur = top.winfo_width()
        hauteur = top.winfo_height()

        x = (top.winfo_screenwidth() - largeur) // 2
        y = (top.winfo_screenheight() - hauteur) // 2 - 150

        top.geometry(
            f"{largeur}x{hauteur}+{x}+{y}"
        )

        top.resizable(
            False,
            False
        )

        ttk.Label(
            top,
            text="Contrôle des habilitations",
            font=("Segoe UI", 14, "bold")
        ).pack(
            pady=10
        )

        if expirees:
            ttk.Label(
                top,
                text=(
                    f"🔴 {expirees} "
                    f"habilitation(s) expirée(s)"
                ),
                font=("Segoe UI", 12, "bold"),
                foreground="red"
            ).pack(
                pady=5
            )

        if echeance:
            ttk.Label(
                top,
                text=(
                    f"🟠 {echeance} habilitation(s) "
                    f"à renouveler sous "
                    f"{delai_alerte} jours"
                ),
                font=("Segoe UI", 12, "bold"),
                foreground="orange"
            ).pack(
                pady=5
            )

        self.icone_fermer = charger_icone("x", 12)

        ttk.Button(
            top,
            text="Fermer",
            image=self.icone_fermer,
            compound="left",
            command=top.destroy,
            bootstyle="danger"
        ).pack(
            pady=15
        )

    # ==================================================
    # PDF
    # ==================================================

    def generer_pdf(self):

        PDFManager.generer(
            self.data.df
        )

        log_info(
            "Export PDF terminé"
        )

        self.messages.info(
            titre="PDF",
            message="PDF générés."
        )

    def gestion_mails(self):

        # ==================================================
        # CONTRÔLE DES DROITS
        # ==================================================

        if not SessionManager.est_administrateur():
            self.messages.warning(
                titre="Accès refusé",
                message=(
                    "Vous devez être administrateur "
                    "pour gérer les adresses mail."
                )
            )
            return

        # ==================================================
        # CRÉATION DE LA FENÊTRE
        # ==================================================

        fenetre = ttk.Toplevel(
            self.root
        )

        self.windows.ouvrir(
            fenetre
        )

        fenetre.protocol(
            "WM_DELETE_WINDOW",
            self.windows.fermer
        )

        fenetre.title(
            "Gestion des mails"
        )

        fenetre.resizable(
            True,
            True
        )

        # ==================================================
        # SYNCHRONISATION DES SECTEURS
        # ==================================================

        synchroniser_secteurs_mails()

        # La synchronisation vient de retirer les secteurs sans salarié.
        # On affiche donc les seuls secteurs actuellement actifs.
        tous_les_mails = recuperer_mails_secteurs()

        secteurs_actuels = []
        if (
            hasattr(self, "data")
            and hasattr(self.data, "df")
            and self.data.df is not None
            and "Secteur" in self.data.df.columns
        ):
            secteurs_actuels = sorted({
                str(valeur).strip()
                for valeur in self.data.df["Secteur"].dropna()
                if str(valeur).strip()
            })

        mails = {
            secteur: tous_les_mails.get(secteur, "")
            for secteur in secteurs_actuels
        }

        self.entries_mails = {}

        nombre_secteurs = len(mails)

        # ==================================================
        # DIMENSIONS
        # ==================================================

        LARGEUR_FENETRE = 425

        HAUTEUR_LIGNE = 42

        HAUTEUR_MAX_ZONE = 250

        hauteur_contenu = (
                max(nombre_secteurs, 1)
                * HAUTEUR_LIGNE
        )

        hauteur_zone = min(
            hauteur_contenu,
            HAUTEUR_MAX_ZONE
        )

        # Titre + en-têtes + contenu + boutons
        hauteur_fenetre = (
                90
                + hauteur_zone
                + 75
        )

        hauteur_fenetre = max(
            350,
            min(
                hauteur_fenetre,
                500
            )
        )

        fenetre.geometry(
            f"{LARGEUR_FENETRE}x{hauteur_fenetre}"
        )

        fenetre.minsize(
            425,
            350
        )

        # ==================================================
        # CONFIGURATION DE LA GRILLE
        # ==================================================

        fenetre.columnconfigure(
            0,
            weight=1
        )

        fenetre.rowconfigure(
            1,
            weight=1
        )

        # ==================================================
        # TITRE
        # ==================================================

        cadre_titre = ttk.Frame(
            fenetre,
            padding=(12, 10, 12, 5)
        )

        cadre_titre.grid(
            row=0,
            column=0,
            sticky="ew"
        )

        self.icone_titre_mails = charger_icone("mail", 12)
        ttk.Label(
            cadre_titre,
            text="Gestion des mails",
            image=self.icone_titre_mails,
            compound="left",
            font=("Segoe UI", 14, "bold")
        ).pack(
            anchor="w"
        )

        ttk.Label(
            cadre_titre,
            text=(
                "Configurez l'adresse de réception "
                "des exports pour chaque secteur."
            ),
            font=("Segoe UI", 9)
        ).pack(
            anchor="w",
            pady=(3, 0)
        )

        # ==================================================
        # ZONE CENTRALE
        # ==================================================

        cadre_central = ttk.Frame(
            fenetre,
            padding=(12, 2, 12, 2)
        )

        cadre_central.grid(
            row=1,
            column=0,
            sticky="nsew"
        )

        cadre_central.columnconfigure(
            1,
            weight=1
        )

        cadre_central.rowconfigure(
            1,
            weight=1
        )

        # ==================================================
        # EN-TÊTES
        # ==================================================

        ttk.Label(
            cadre_central,
            text="Secteur",
            font=("Segoe UI", 9, "bold")
        ).grid(
            row=0,
            column=0,
            padx=(5, 12),
            pady=(3, 6),
            sticky="w"
        )

        ttk.Label(
            cadre_central,
            text="Adresse mail",
            font=("Segoe UI", 9, "bold")
        ).grid(
            row=0,
            column=1,
            padx=5,
            pady=(3, 6),
            sticky="w"
        )

        # ==================================================
        # ZONE SCROLLABLE
        # ==================================================

        cadre_scroll = ttk.Frame(
            cadre_central
        )

        cadre_scroll.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="nsew"
        )

        cadre_scroll.columnconfigure(
            0,
            weight=1
        )

        cadre_scroll.rowconfigure(
            0,
            weight=1
        )

        # ==================================================
        # CANVAS
        # ==================================================

        canvas = tk.Canvas(
            cadre_scroll,
            height=hauteur_zone,
            bg=self.root.cget("bg"),
            highlightthickness=0,
            borderwidth=0
        )

        scrollbar = ttk.Scrollbar(
            cadre_scroll,
            orient="vertical",
            command=canvas.yview
        )

        zone_lignes = ttk.Frame(
            canvas
        )

        zone_lignes.columnconfigure(
            1,
            weight=1
        )

        canvas_window = canvas.create_window(
            (0, 0),
            window=zone_lignes,
            anchor="nw"
        )

        canvas.configure(
            yscrollcommand=scrollbar.set
        )

        canvas.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        # ==================================================
        # ADAPTATION DE LA ZONE INTERNE
        # ==================================================

        def mettre_a_jour_scrollregion(event=None):

            canvas.configure(
                scrollregion=canvas.bbox("all")
            )

        zone_lignes.bind(
            "<Configure>",
            mettre_a_jour_scrollregion
        )

        def ajuster_largeur(event):

            canvas.itemconfigure(
                canvas_window,
                width=event.width
            )

        canvas.bind(
            "<Configure>",
            ajuster_largeur
        )

        # ==================================================
        # MOLETTE DE LA SOURIS
        # ==================================================

        def faire_defiler(event):

            # Windows / macOS
            if hasattr(event, "delta") and event.delta:
                canvas.yview_scroll(
                    int(-1 * (event.delta / 120)),
                    "units"
                )

            # Linux : molette vers le haut
            elif event.num == 4:
                canvas.yview_scroll(
                    -1,
                    "units"
                )

            # Linux : molette vers le bas
            elif event.num == 5:
                canvas.yview_scroll(
                    1,
                    "units"
                )

        # ==================================================
        # MOLETTE DE LA SOURIS
        # Compatible Linux + Windows
        # ==================================================

        fenetre.bind(
            "<MouseWheel>",
            faire_defiler
        )

        fenetre.bind(
            "<Button-4>",
            faire_defiler
        )

        fenetre.bind(
            "<Button-5>",
            faire_defiler
        )

        # ==================================================
        # LIGNES SECTEURS / ADRESSES
        # ==================================================

        for ligne, (secteur, email) in enumerate(
                mails.items()
        ):
            ttk.Label(
                zone_lignes,
                text=secteur,
                font=("Segoe UI", 9)
            ).grid(
                row=ligne,
                column=0,
                padx=(5, 12),
                pady=5,
                sticky="w"
            )

            entry = ttk.Entry(
                zone_lignes
            )

            entry.insert(
                0,
                email
            )

            entry.grid(
                row=ligne,
                column=1,
                padx=5,
                pady=5,
                sticky="ew"
            )

            self.entries_mails[
                secteur
            ] = entry

        # ==================================================
        # SCROLLBAR
        # ==================================================

        if hauteur_contenu > HAUTEUR_MAX_ZONE:
            scrollbar.grid(
                row=0,
                column=1,
                sticky="ns"
            )

        # ==================================================
        # BOUTONS
        # ==================================================

        cadre_boutons = ttk.Frame(
            fenetre,
            padding=(12, 8, 12, 12)
        )

        cadre_boutons.grid(
            row=2,
            column=0,
            sticky="ew"
        )

        cadre_boutons.columnconfigure(
            0,
            weight=1
        )

        # ==================================================
        # ENREGISTRER
        # ==================================================

        self.icone_enregistrer_mails = charger_icone(
            "save", 12
        )

        ttk.Button(
            cadre_boutons,
            text="Enregistrer",
            image=self.icone_enregistrer_mails,
            compound="left",
            command=self.sauvegarder_mails,
            bootstyle="success"
        ).grid(
            row=0,
            column=1,
            padx=4
        )

        # ==================================================
        # FERMER
        # ==================================================

        self.icone_fermer = charger_icone(
            "x", 12
        )

        ttk.Button(
            cadre_boutons,
            text="Fermer",
            image=self.icone_fermer,
            compound="left",
            command=self.windows.fermer,
            bootstyle="danger"
        ).grid(
            row=0,
            column=2,
            padx=4
        )

    def choisir_destinataire(self):
        """
        Affiche le choix du mode d'envoi des mails.

        Retourne :
            "tous" : envoi aux destinataires configurés par secteur
            "moi"  : envoi uniquement à l'utilisateur connecté
            None   : annulation
        """

        utilisateur = SessionManager.utilisateur()

        if not utilisateur:
            self.messages.warning(
                titre="Session",
                message="Aucun utilisateur connecté."
            )
            return None

        id_utilisateur = utilisateur.get("id")

        email = UtilisateurManager.recuperer_email(id_utilisateur)

        fenetre = tk.Toplevel(self.root)
        fenetre.title("Destinataires des mails")
        fenetre.resizable(False, False)
        fenetre.transient(self.root)
        fenetre.grab_set()

        resultat = {"choix": None}

        cadre = ttk.Frame(fenetre, padding=20)
        cadre.pack(fill="both", expand=True)

        ttk.Label(
            cadre,
            text="Choisissez les destinataires :",
            font=("TkDefaultFont", 11, "bold")
        ).pack(anchor="w", pady=(0, 15))

        choix = tk.StringVar(value="tous")

        ttk.Radiobutton(
            cadre,
            text="Tous les destinataires",
            variable=choix,
            value="tous"
        ).pack(anchor="w")

        ttk.Label(
            cadre,
            text="Envoi aux adresses configurées par secteur.",
        ).pack(anchor="w", padx=25, pady=(0, 12))

        radio_moi = ttk.Radiobutton(
            cadre,
            text="Moi uniquement",
            variable=choix,
            value="moi"
        )
        radio_moi.pack(anchor="w")

        if email:
            ttk.Label(
                cadre,
                text=email
            ).pack(anchor="w", padx=25, pady=(0, 15))
        else:
            ttk.Label(
                cadre,
                text="Aucune adresse e-mail n'est associée à votre compte."
            ).pack(anchor="w", padx=25, pady=(0, 15))

            radio_moi.configure(state="disabled")

        cadre_boutons = ttk.Frame(cadre)
        cadre_boutons.pack(fill="x", pady=(10, 0))

        def annuler():
            resultat["choix"] = None
            fenetre.destroy()

        def valider():
            resultat["choix"] = choix.get()
            fenetre.destroy()

        ttk.Button(
            cadre_boutons,
            text="Annuler",
            command=annuler,
            bootstyle="secondary"
        ).pack(side="left")

        ttk.Button(
            cadre_boutons,
            text="Envoyer",
            command=valider,
            bootstyle="success"
        ).pack(side="right")

        fenetre.protocol("WM_DELETE_WINDOW", annuler)

        self.root.wait_window(fenetre)

        return resultat["choix"]

    def envoyer_exports_secteurs(self):

        """
        Lance l'envoi des exports d'habilitations par secteur.
        """

        if not SessionManager.peut_modifier():
            self.messages.warning(
                titre="Accès refusé",
                message="Vous n'avez pas les droits nécessaires pour envoyer les échéances par secteur."
            )
            return

        choix_destinataire = self.choisir_destinataire()

        if choix_destinataire is None:
            return

        destinataire_personnel = None

        if choix_destinataire == "moi":

            utilisateur = SessionManager.utilisateur()

            if not utilisateur:
                self.messages.warning(
                    titre="Session",
                    message="Aucun utilisateur connecté."
                )
                return

            destinataire_personnel = (
                UtilisateurManager.recuperer_email(
                    utilisateur["id"]
                )
            )

            if not destinataire_personnel:
                self.messages.warning(
                    titre="Adresse e-mail",
                    message=(
                        "Aucune adresse e-mail n'est associée "
                        "à votre compte."
                    )
                )
                return

        HABILITATIONS = HabilitationManager.lister()

        from loading_dialog import LoadingDialog

        dialog = LoadingDialog(
            self.root,
            "Envoi des mails"
        )

        dialog.afficher()

        try:

            rapport = executer_envoi_secteurs(
                df=self.data.df,
                habilitations=HABILITATIONS,
                dossier_exports=DOSSIER_EXPORTS,
                progression=dialog.changer_message,
                destinataire_personnel=destinataire_personnel
            )

        finally:

            dialog.fermer()

        # ==========================================
        # RAPPORT FINAL
        # ==========================================

        nb_envois = rapport["nb_envois"]
        erreurs = rapport["erreurs"]

        if erreurs:

            self.messages.warning(
                titre="Envoi terminé",
                message=(
                        f"{nb_envois} mail(s) envoyé(s)\n\n"
                        f"Erreurs :\n\n"
                        + "\n".join(erreurs)
                )
            )

        else:

            self.messages.info(
                titre="Envoi terminé",
                message=(
                    f"{nb_envois} mail(s) envoyé(s)."
                )
            )

    def sauvegarder_mails(self):

        if not SessionManager.est_administrateur():
            messagebox.showerror(
                "Accès refusé",
                "Seul un administrateur peut modifier les adresses mail."
            )
            return

        modification = False
        suppression = False

        mails_existants = recuperer_mails_secteurs()

        for secteur, entry in self.entries_mails.items():

            email = entry.get().strip()
            ancien_email = mails_existants.get(secteur, "").strip()

            # ==========================================
            # SUPPRESSION D'UNE ADRESSE EXISTANTE
            # ==========================================

            if not email and ancien_email:
                suppression = True
                modification = True

                enregistrer_mail_secteur(
                    secteur,
                    email
                )

            # ==========================================
            # AJOUT OU MODIFICATION
            # ==========================================

            elif email and email != ancien_email:

                # Validation de l'adresse mail
                valide, message = verifier_email(email)

                if not valide:
                    messagebox.showerror(
                        "Adresse mail invalide",
                        f"Secteur : {secteur}\n\n{message}"
                    )
                    return

                modification = True

                enregistrer_mail_secteur(
                    secteur,
                    email
                )

        if suppression:
            messagebox.showinfo(
                "Adresses mail",
                "Adresse mail supprimée."
            )

        elif modification:
            messagebox.showinfo(
                "Adresses mail",
                "Adresse mail enregistrée."
            )

        else:
            messagebox.showinfo(
                "Adresses mail",
                "Aucune modification."
            )

    def historique_mails(self):

        fenetre = ttk.Toplevel(
            self.root
        )

        self.windows.ouvrir(
            fenetre
        )

        fenetre.protocol(
            "WM_DELETE_WINDOW",
            self.windows.fermer
        )

        fenetre.title(
            "Historique des envois"
        )

        fenetre.geometry(
            "1000x400"
        )

        tree = ttk.Treeview(
            fenetre,
            columns=(
                "Date",
                "Secteur",
                "Destinataire",
                "Nb",
                "Statut",
                "Erreur"
            ),
            show="headings"
        )

        tree.tag_configure(
            "envoye",
            background="#d4edda",
            foreground="darkgreen"
        )

        tree.tag_configure(
            "erreur",
            background="#f8d7da",
            foreground="darkred"
        )

        tree.column(
            "Date",
            anchor="center",
            width=95)

        tree.column(
            "Secteur",
            anchor="center",
            width=80)

        tree.column(
            "Destinataire",
            anchor="center",
            width=160)

        tree.column(
            "Nb",
            anchor="center",
            width=30)

        tree.column(
            "Statut",
            anchor="center",
            width=50)

        tree.column(
            "Erreur",
            anchor="center",
            width=240)

        tree.heading(
            "Date",
            text="Date",
            anchor="center"
        )

        tree.heading(
            "Secteur",
            text="Secteur"
        )

        tree.heading(
            "Destinataire",
            text="Destinataire"
        )

        tree.heading(
            "Nb",
            text="Nb hab.")
        tree.heading(
            "Statut",
            text="Statut")
        tree.heading(
            "Erreur",
            text="Erreur")

        tree.pack(
            fill="both",
            expand=True
        )

        df = lire_historique_mails()

        for _, row in df.iterrows():
            tag = (
                "envoye"
                if row["statut"] == "Envoyé"
                else "erreur"
            )

            tree.insert(
                "",
                "end",
                values=(
                    row["date_heure"],
                    row["secteur"],
                    row["destinataire"],
                    row["nombre_habilitations"],
                    row["statut"],
                    row["message_erreur"]
                ),
                tags=(tag,)
            )

        self.icone_fermer = charger_icone("x", 12)

        ttk.Button(
            fenetre,
            text="Fermer",
            image=self.icone_fermer,
            compound="left",
            command=self.windows.fermer,
            bootstyle="danger"
        ).pack(
            pady=10
        )

    def ouvrir_parametres(self):

        if not SessionManager.est_administrateur():
            self.messages.warning(
                titre="Accès refusé",
                message="Vous devez être administrateur pour accéder aux paramètres."
            )
            return

        fenetre = ttk.Toplevel(self.root)

        self.windows.ouvrir(fenetre)

        fenetre.title("Paramètres")
        fenetre.geometry("450x440")

        fenetre.transient(self.root)

        ttk.Label(
            fenetre,
            text="Paramètres",
            font=("Segoe UI", 14, "bold")
        ).pack(pady=10)

        self.icone_import_excel = charger_icone(
            "file-spreadsheet", 12
        )

        ttk.Button(
            fenetre,
            text="Importer Excel",
            image=self.icone_import_excel,
            compound="left",
            command=self.importer_fichier,
            bootstyle="success"
        ).pack(fill="x", padx=20, pady=5)

        self.icone_mails = charger_icone(
            "mail", 12
        )

        self.icone_gestion_habilitations = charger_icone(
            "shield-check", 12
        )

        ttk.Button(
            fenetre,
            text="Gestion des habilitations",
            image=self.icone_gestion_habilitations,
            compound="left",
            command=self.gestion_habilitations,
            bootstyle="info"
        ).pack(fill="x", padx=20, pady=5)

        self.icone_rapport_logs = charger_icone(
            "file-text", 12
        )

        self.icone_smtp = charger_icone(
            "key-round", 12
        )

        ttk.Button(
            fenetre,
            text="Paramètres SMTP",
            image=self.icone_smtp,
            compound="left",
            command=self.gestion_identifiants,
            bootstyle="warning"
        ).pack(
            fill="x",
            padx=20,
            pady=5
        )

        self.icone_mails = charger_icone(
            "mail", 12
        )

        ttk.Button(
            fenetre,
            text="Gestion des mails",
            image=self.icone_mails,
            compound="left",
            command=self.gestion_mails,
            bootstyle="secondary"
        ).pack(
            fill="x",
            padx=20,
            pady=5
        )

        self.icone_comptes_utilisateurs = charger_icone(
            "users", 12
        )

        ttk.Button(
            fenetre,
            text="Comptes utilisateurs",
            image=self.icone_comptes_utilisateurs,
            compound="left",
            command=self.gestion_utilisateurs,
            bootstyle="warning"
        ).pack(
            fill="x",
            padx=20,
            pady=5
        )

        self.icone_historique_envois = charger_icone(
            "clock-3", 12
        )

        ttk.Button(
            fenetre,
            text="Historique des envois",
            image=self.icone_historique_envois,
            compound="left",
            command=self.historique_mails,
            bootstyle="dark"
        ).pack(fill="x", padx=20, pady=5)

        self.icone_rapport_logs = charger_icone(
            "file-text", 12
        )

        ttk.Button(
            fenetre,
            text="Rapport des logs",
            image=self.icone_rapport_logs,
            compound="left",
            command=self.consulter_logs,
            bootstyle="secondary"
        ).pack(fill="x", padx=20, pady=5)

        ttk.Separator(
            fenetre,
            orient="horizontal"
        ).pack(fill="x", padx=20, pady=15)

        self.icone_fermer = charger_icone(
            "x", 12
        )

        ttk.Button(
            fenetre,
            text="Fermer",
            image=self.icone_fermer,
            compound="left",
            command=self.windows.fermer,
            bootstyle="danger"
        ).pack(
            pady=10
        )


    def historique_envois(self):

        self.messages.info(
            titre="Historique",
            message="Historique des envois à venir."
        )

    def ajouter_utilisateur(self):

        # ==========================================
        # Vérification des droits
        # ==========================================

        if not SessionManager.est_administrateur():
            self.messages.warning(
                titre="Accès refusé",
                message=(
                    "Vous devez être administrateur "
                    "pour créer un compte utilisateur."
                )
            )

            return

        # ==========================================
        # Fenêtre
        # ==========================================

        fenetre = ttk.Toplevel(self.root)

        self.windows.ouvrir(fenetre)

        fenetre.protocol(
            "WM_DELETE_WINDOW",
            self.windows.fermer
        )

        fenetre.title(
            "Ajouter un utilisateur"
        )

        fenetre.resizable(
            False,
            False
        )

        fenetre.transient(
            self.root
        )

        # ==========================================
        # Variables
        # ==========================================

        code_var = ttk.StringVar()
        nom_var = ttk.StringVar()
        prenom_var = ttk.StringVar()
        email_var = ttk.StringVar()
        profil_var = ttk.StringVar()

        mot_de_passe_var = ttk.StringVar()
        confirmation_var = ttk.StringVar()

        # ==========================================
        # Gestion de la taille et du centrage
        # ==========================================

        def ajuster_fenetre():

            fenetre.update_idletasks()

            largeur = 500

            if profil_var.get() == "Administrateur":
                hauteur = 540
            else:
                hauteur = 460

            x = (
                        fenetre.winfo_screenwidth() - largeur
                ) // 2

            y = (
                        fenetre.winfo_screenheight() - hauteur
                ) // 2

            fenetre.geometry(
                f"{largeur}x{hauteur}+{x}+{y}"
            )

        # ==========================================
        # Titre
        # ==========================================

        ttk.Label(
            fenetre,
            text="Ajouter un utilisateur",
            font=("Segoe UI", 14, "bold")
        ).pack(
            pady=15
        )

        # ==========================================
        # Cadre principal
        # ==========================================

        cadre = ttk.Frame(fenetre)

        cadre.pack(
            padx=30,
            pady=10,
            fill="x"
        )

        cadre.columnconfigure(
            1,
            weight=1
        )

        # ==========================================
        # Code
        # ==========================================

        ttk.Label(
            cadre,
            text="Code :"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=8
        )

        ttk.Entry(
            cadre,
            textvariable=code_var,
            width=30
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            pady=8
        )

        # ==========================================
        # Nom
        # ==========================================

        ttk.Label(
            cadre,
            text="Nom :"
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=8
        )

        ttk.Entry(
            cadre,
            textvariable=nom_var,
            width=30
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            pady=8
        )

        # ==========================================
        # Prénom
        # ==========================================

        ttk.Label(
            cadre,
            text="Prénom :"
        ).grid(
            row=2,
            column=0,
            sticky="w",
            pady=8
        )

        ttk.Entry(
            cadre,
            textvariable=prenom_var,
            width=30
        ).grid(
            row=2,
            column=1,
            sticky="ew",
            pady=8
        )

        # ==========================================
        # Adresse e-mail
        # ==========================================

        ttk.Label(
            cadre,
            text="Adresse e-mail :"
        ).grid(
            row=3,
            column=0,
            sticky="w",
            pady=8
        )

        ttk.Entry(
            cadre,
            textvariable=email_var,
            width=30
        ).grid(
            row=3,
            column=1,
            sticky="ew",
            pady=8
        )

        # ==========================================
        # Profil
        # ==========================================

        ttk.Label(
            cadre,
            text="Profil :"
        ).grid(
            row=4,
            column=0,
            sticky="w",
            pady=8
        )

        profil_combo = ttk.Combobox(
            cadre,
            textvariable=profil_var,
            values=PROFILS,
            state="readonly",
            width=28
        )

        profil_combo.grid(
            row=4,
            column=1,
            sticky="ew",
            pady=8
        )

        # ==========================================
        # Cadre mot de passe
        # ==========================================

        cadre_mot_de_passe = ttk.Frame(cadre)

        cadre_mot_de_passe.grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=10
        )

        cadre_mot_de_passe.columnconfigure(
            1,
            weight=1
        )

        # ==========================================
        # Mot de passe
        # ==========================================

        ttk.Label(
            cadre_mot_de_passe,
            text="Mot de passe :"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=8
        )

        entry_mot_de_passe = ttk.Entry(
            cadre_mot_de_passe,
            textvariable=mot_de_passe_var,
            show="*",
            width=30
        )

        entry_mot_de_passe.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=8
        )

        # ==========================================
        # Confirmation
        # ==========================================

        ttk.Label(
            cadre_mot_de_passe,
            text="Confirmation :"
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=8
        )

        entry_confirmation = ttk.Entry(
            cadre_mot_de_passe,
            textvariable=confirmation_var,
            show="*",
            width=30
        )

        entry_confirmation.grid(
            row=1,
            column=1,
            sticky="ew",
            pady=8
        )

        # Masqué par défaut
        cadre_mot_de_passe.grid_remove()

        # ==========================================
        # Gestion du changement de profil
        # ==========================================

        def gerer_profil(event=None):

            if profil_var.get() == "Administrateur":

                cadre_mot_de_passe.grid()

            else:

                cadre_mot_de_passe.grid_remove()

                mot_de_passe_var.set("")
                confirmation_var.set("")

            ajuster_fenetre()

        profil_combo.bind(
            "<<ComboboxSelected>>",
            gerer_profil
        )

        # ==========================================
        # Création du compte
        # ==========================================

        def enregistrer():

            code = code_var.get().strip()
            nom = nom_var.get().strip()
            prenom = prenom_var.get().strip()
            email = email_var.get().strip()
            profil = profil_var.get().strip()

            # --------------------------------------
            # Mot de passe
            # --------------------------------------

            mot_de_passe = (
                mot_de_passe_var.get()
                if profil == "Administrateur"
                else None
            )

            confirmation = (
                confirmation_var.get()
                if profil == "Administrateur"
                else None
            )

            # --------------------------------------
            # Vérification du mot de passe
            # --------------------------------------

            if profil == "Administrateur":

                if not mot_de_passe:
                    self.messages.warning(
                        titre="Création impossible",
                        message=(
                            "Le mot de passe est obligatoire "
                            "pour un administrateur."
                        )
                    )

                    entry_mot_de_passe.focus_set()

                    return

                if mot_de_passe != confirmation:
                    self.messages.warning(
                        titre="Création impossible",
                        message=(
                            "Les deux mots de passe "
                            "ne correspondent pas."
                        )
                    )

                    entry_confirmation.focus_set()

                    return

            # --------------------------------------
            # Création du compte
            # --------------------------------------

            try:

                UtilisateurManager.creer_utilisateur(
                    code=code,
                    nom=nom,
                    prenom=prenom,
                    profil=profil,
                    mot_de_passe=mot_de_passe,
                    email=email,
                )

            except ValueError as erreur:

                self.messages.warning(
                    titre="Création impossible",
                    message=str(erreur)
                )

                return

            except Exception as erreur:

                self.messages.error(
                    titre="Erreur",
                    message=(
                        "Une erreur est survenue "
                        "lors de la création du compte.\n\n"
                        f"Détail : {erreur}"
                    )
                )

                return

            # --------------------------------------
            # Succès
            # --------------------------------------

            self.messages.info(
                titre="Compte créé",
                message=(
                    f"Le compte « {code} » "
                    "a été créé avec succès."
                )
            )

            self.windows.fermer()

        # ==========================================
        # Boutons
        # ==========================================

        cadre_boutons = ttk.Frame(fenetre)

        cadre_boutons.pack(
            pady=20
        )

        # ------------------------------------------
        # Enregistrer
        # ------------------------------------------

        self.icone_enregistrer_utilisateur = charger_icone(
            "save", 12
        )

        ttk.Button(
            cadre_boutons,
            text="Enregistrer",
            image=self.icone_enregistrer_utilisateur,
            compound="left",
            command=enregistrer,
            bootstyle="success"
        ).pack(
            side="left",
            padx=5
        )

        # ------------------------------------------
        # Annuler
        # ------------------------------------------

        self.icone_fermer_ajout_utilisateur = charger_icone(
            "x", 12
        )

        ttk.Button(
            cadre_boutons,
            text="Annuler",
            image=self.icone_fermer_ajout_utilisateur,
            compound="left",
            command=self.windows.fermer,
            bootstyle="danger"
        ).pack(
            side="left",
            padx=5
        )

        # ==========================================
        # Taille initiale et centrage
        # ==========================================

        ajuster_fenetre()

        # ==========================================
        # Focus initial
        # ==========================================

        fenetre.focus_force()

        fenetre.after(
            100,
            fenetre.focus_force
        )

    def gestion_identifiants(self):

        if not SessionManager.est_administrateur():
            self.messages.warning(
                titre="Accès refusé",
                message="Vous devez être administrateur pour accéder aux paramètres SMTP."
            )
            return

        param = recuperer_parametres_mail()

        fenetre = ttk.Toplevel(self.root)

        self.windows.ouvrir(
            fenetre
        )

        fenetre.protocol(
            "WM_DELETE_WINDOW",
            self.windows.fermer
        )

        fenetre.title(
            "Comptes et mots de passe"
        )

        fenetre.geometry(
            "600x400"
        )

        # ==========================================
        # Adresse mail
        # ==========================================

        ttk.Label(
            fenetre,
            text="Adresse mail"
        ).grid(
            row=0,
            column=0,
            padx=10,
            pady=10,
            sticky="w"
        )

        entry_mail = ttk.Entry(
            fenetre,
            width=40
        )

        entry_mail.grid(
            row=0,
            column=1,
            padx=10,
            pady=10
        )

        entry_mail.insert(
            0,
            param["expediteur"]
        )

        # ==========================================
        # Mot de passe SMTP
        # ==========================================

        ttk.Label(
            fenetre,
            text="Mot de passe SMTP"
        ).grid(
            row=1,
            column=0,
            padx=10,
            pady=10,
            sticky="w"
        )

        entry_mdp = ttk.Entry(
            fenetre,
            width=40,
            show="*"
        )

        entry_mdp.grid(
            row=1,
            column=1,
            padx=10,
            pady=10
        )

        # IMPORTANT :
        # Le mot de passe n'est plus prérempli.
        # Il est stocké dans Keyring et non dans SQLite.

        ttk.Label(
            fenetre,
            text="Laissez vide pour conserver le mot de passe actuel."
        ).grid(
            row=1,
            column=1,
            padx=(0, 10),
            pady=(40, 0),
            sticky="w"
        )

        # ==========================================
        # Serveur SMTP
        # ==========================================

        ttk.Label(
            fenetre,
            text="Serveur SMTP"
        ).grid(
            row=2,
            column=0,
            padx=10,
            pady=10,
            sticky="w"
        )

        entry_smtp = ttk.Entry(
            fenetre,
            width=40
        )

        entry_smtp.grid(
            row=2,
            column=1,
            padx=10,
            pady=10
        )

        entry_smtp.insert(
            0,
            param["smtp_serveur"]
        )

        # ==========================================
        # Port SMTP
        # ==========================================

        ttk.Label(
            fenetre,
            text="Port SMTP"
        ).grid(
            row=3,
            column=0,
            padx=10,
            pady=10,
            sticky="w"
        )

        entry_port = ttk.Entry(
            fenetre,
            width=10
        )

        entry_port.grid(
            row=3,
            column=1,
            padx=10,
            pady=10,
            sticky="w"
        )

        entry_port.insert(
            0,
            str(param["smtp_port"])
        )

        # ==========================================
        # Délai d'alerte
        # ==========================================

        ttk.Label(
            fenetre,
            text="Délai d'alerte"
        ).grid(
            row=4,
            column=0,
            padx=10,
            pady=10,
            sticky="w"
        )

        entry_delai = ttk.Entry(
            fenetre,
            width=10
        )

        entry_delai.grid(
            row=4,
            column=1,
            padx=10,
            pady=10,
            sticky="w"
        )

        entry_delai.insert(
            0,
            str(param["delai_alerte"])
        )

        ttk.Label(
            fenetre,
            text="jours"
        ).grid(
            row=4,
            column=1,
            padx=(90, 0),
            pady=10,
            sticky="w"
        )

        # ==========================================
        # Enregistrer
        # ==========================================

        def enregistrer():

            if not SessionManager.est_administrateur():
                self.messages.warning(
                    titre="Accès refusé",
                    message="Vous devez être administrateur pour modifier les paramètres SMTP."
                )
                return

            mot_de_passe = entry_mdp.get()

            sauvegarder_parametres_mail(
                entry_mail.get(),
                mot_de_passe,
                entry_smtp.get(),
                int(entry_port.get()),
                int(entry_delai.get())
            )

            # Mise à jour immédiate du tableau de bord
            self.maj_tableau_bord()

            self.windows.fermer()

            self.messages.info(
                "Information",
                "Paramètres enregistrés."
            )

        self.icone_enregistrer_compte = charger_icone(
            "save", 12
        )

        ttk.Button(
            fenetre,
            text="Enregistrer",
            image=self.icone_enregistrer_compte,
            compound="left",
            command=enregistrer,
            bootstyle="success"
        ).grid(
            row=5,
            column=0,
            columnspan=2,
            pady=20
        )

        self.icone_fermer = charger_icone(
            "x", 12
        )

        ttk.Button(
            fenetre,
            text="Fermer",
            image=self.icone_fermer,
            compound="left",
            command=self.windows.fermer,
            bootstyle="danger"
        ).grid(
            row=6,
            column=0,
            columnspan=2
        )

    def rafraichir_application(self):
        """
        Recharge complètement les données de l'application
        et reconstruit les éléments dynamiques.
        """

        # ==========================================
        # Recharger les données depuis SQLite
        # ==========================================

        self.data.df = self.data.charger()

        # ==========================================
        # Actualiser les colonnes du Treeview
        # ==========================================

        self.afficher_colonnes()

        # ==========================================
        # Actualiser le filtre Formation
        # ==========================================

        self.combo_hab["values"] = (
            "",
            *HabilitationManager.lister()
        )

        # ==========================================
        # Recréer la fiche salarié
        # pour intégrer les nouvelles habilitations
        # ==========================================

        self.creer_formulaire()

        # ==========================================
        # Réafficher les données
        # ==========================================

        self.afficher_dataframe(
            self.data.df
        )

        # ==========================================
        # Mettre à jour le tableau de bord
        # ==========================================

        self.maj_tableau_bord()

    def gestion_habilitations(self):

        if not SessionManager.est_administrateur():
            self.messages.warning(
                titre="Accès refusé",
                message="Vous devez être administrateur pour gérer les habilitations."
            )
            return

        fenetre = ttk.Toplevel(self.root)

        self.windows.ouvrir(fenetre)

        fenetre.title("Gestion des habilitations")
        fenetre.geometry("900x500")
        fenetre.minsize(850, 460)

        fenetre.transient(self.root)

        # ==========================================
        # Titre
        # ==========================================

        ttk.Label(
            fenetre,
            text="Gestion des habilitations",
            font=("Segoe UI", 14, "bold")
        ).pack(
            pady=10
        )

        # ==========================================
        # Tableau
        # ==========================================

        cadre = ttk.Frame(
            fenetre
        )

        cadre.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=10
        )

        tree = ttk.Treeview(
            cadre,
            columns=(
                "ID",
                "Nom",
                "Ordre",
                "Active"
            ),
            show="headings"
        )

        tree.heading(
            "ID",
            text="ID"
        )

        tree.heading(
            "Nom",
            text="Habilitation"
        )

        tree.heading(
            "Ordre",
            text="Ordre"
        )

        tree.heading(
            "Active",
            text="Active"
        )

        tree.column(
            "ID",
            width=60,
            anchor="center"
        )

        tree.column(
            "Nom",
            width=250,
            anchor="w"
        )

        tree.column(
            "Ordre",
            width=100,
            anchor="center"
        )

        tree.column(
            "Active",
            width=100,
            anchor="center"
        )

        tree.pack(
            fill="both",
            expand=True
        )

        # ==========================================
        # Chargement des habilitations
        # ==========================================

        habilitations = (
            HabilitationManager
            .lister_avec_details()
        )

        for id_hab, nom, ordre, active in habilitations:
            tree.insert(
                "",
                "end",
                values=(
                    id_hab,
                    nom,
                    ordre,
                    "Oui" if active else "Non"
                )
            )

        # ==========================================
        # Zone d'ajout
        # ==========================================

        cadre_ajout = ttk.Frame(
            fenetre
        )

        cadre_ajout.pack(
            fill="x",
            padx=20,
            pady=10
        )

        ttk.Label(
            cadre_ajout,
            text="Nouvelle habilitation :"
        ).pack(
            side="left",
            padx=(0, 10)
        )

        entry_nom = ttk.Entry(
            cadre_ajout,
            width=30
        )

        entry_nom.pack(
            side="left",
            padx=(0, 10)
        )

        # ==========================================
        # Actualiser la liste
        # ==========================================

        def actualiser_liste():

            tree.delete(
                *tree.get_children()
            )

            habilitations = (
                HabilitationManager
                .lister_avec_details()
            )

            for id_hab, nom, ordre, active in habilitations:
                tree.insert(
                    "",
                    "end",
                    values=(
                        id_hab,
                        nom,
                        ordre,
                        "Oui" if active else "Non"
                    )
                )

        # ==========================================
        # Actualisation immédiate de la liste
        # ==========================================

        actualiser_liste()

        # ==========================================
        # Fonction Ajouter une habilitation
        # ==========================================

        def ajouter_habilitation():

            if not SessionManager.est_administrateur():
                self.messages.warning(
                    titre="Accès refusé",
                    message="Vous devez être administrateur pour ajouter une habilitation."
                )
                return

            # Harmonise la casse comme pour le champ « Prénom » et
            # supprime les espaces superflus. Si la saisie commence par un
            # « é » minuscule, il devient « E » sans accent. Les autres
            # accents et les vérifications existantes restent inchangés.
            nom_saisi = " ".join(entry_nom.get().split())
            nom = nom_saisi.title()
            if nom_saisi.startswith("é"):
                nom = "E" + nom[1:]

            # ==========================================
            # Vérification du nom
            # ==========================================

            if not nom:
                self.messages.warning(
                    "Attention",
                    "Veuillez saisir un nom d'habilitation."
                )

                entry_nom.focus_set()

                return

            # ==========================================
            # Ajout dans habilitations_config
            # ==========================================

            succes, message = (
                HabilitationManager.ajouter(
                    nom
                )
            )

            # ==========================================
            # Échec de l'ajout
            # ==========================================

            if not succes:
                self.messages.warning(
                    "Attention",
                    message
                )

                entry_nom.focus_set()

                return

            log_info(
                f"Habilitation créée : {nom}"
            )

            # ==========================================
            # Création de la colonne SQLite
            # ==========================================

            colonne_ok = (
                HabilitationManager
                .ajouter_colonne_habilitation(
                    nom
                )
            )

            # ==========================================
            # Échec de création de la colonne
            # ==========================================

            if not colonne_ok:
                self.messages.error(
                    "Erreur",
                    "L'habilitation a été ajoutée à la "
                    "configuration, mais la colonne SQLite "
                    "n'a pas pu être créée."
                )

                return

            # ==========================================
            # Ajout de la colonne dans le DataFrame
            # ==========================================

            self.data.ajouter_colonne_habilitation(
                nom
            )

            # ==========================================
            # Actualisation de la Fiche salarié
            # ==========================================

            self.creer_formulaire()

            # ==========================================
            # Mise à jour du Treeview principal
            # ==========================================

            self.actualiser_colonnes_tableau()

            # ==========================================
            # Effacement du champ
            # ==========================================

            entry_nom.delete(
                0,
                "end"
            )

            # ==========================================
            # Actualisation de la liste
            # ==========================================

            actualiser_liste()

            # ==========================================
            # Actualisation du filtre Formation
            # ==========================================

            self.combo_hab["values"] = (
                "",
                *HabilitationManager.lister()
            )

            # ==========================================
            # Récupération de la dernière ligne
            # ==========================================

            lignes = tree.get_children()

            if lignes:
                derniere_ligne = lignes[-1]

                # ==========================================
                # Rendre la nouvelle ligne visible
                # ==========================================

                tree.see(
                    derniere_ligne
                )

                # ==========================================
                # Sélectionner la nouvelle ligne
                # ==========================================

                tree.selection_set(
                    derniere_ligne
                )

                tree.focus(
                    derniere_ligne
                )

            # ==========================================
            # Message de confirmation
            # ==========================================

            self.messages.info(
                "Information",
                message
            )

            # ==========================================
            # Remettre le curseur dans le champ
            # ==========================================

            entry_nom.focus_set()

        # Les boutons d'action restent alignés sur la ligne
        # « Nouvelle habilitation ».

        # ==========================================
        # Bouton Ajouter
        # ==========================================

        self.icone_ajouter_habilitation = charger_icone(
            "circle-plus", 12
        )

        ttk.Button(
            cadre_ajout,
            text="Ajouter",
            image=self.icone_ajouter_habilitation,
            compound="left",
            command=ajouter_habilitation,
            bootstyle="success"
        ).pack(
            side="left"
        )

        # ==========================================
        # ==========================================
        # Fonction Modifier une habilitation
        # ==========================================

        def modifier_habilitation():

            if not SessionManager.est_administrateur():
                self.messages.warning(
                    titre="Accès refusé",
                    message="Vous devez être administrateur pour modifier une habilitation."
                )
                return

            selection = tree.selection()
            if not selection:
                self.messages.warning(
                    "Attention",
                    "Veuillez sélectionner une habilitation à modifier."
                )
                return

            valeurs = tree.item(selection[0], "values")
            id_hab = valeurs[0]
            ancien_nom = valeurs[1]

            nouveau_nom = simpledialog.askstring(
                "Modifier l'habilitation",
                "Nouveau nom de l'habilitation :",
                initialvalue=ancien_nom,
                parent=fenetre
            )
            if nouveau_nom is None:
                return

            # Harmonise la casse et les espaces sans supprimer les accents.
            # Exemple : « preparateur » devient « Preparateur », tandis que
            # « Préparateur » reste « Préparateur » lors du renommage.
            nouveau_nom = " ".join(nouveau_nom.split()).title()
            if not nouveau_nom:
                self.messages.warning(
                    "Attention",
                    "Le nom de l'habilitation ne peut pas être vide."
                )
                return

            succes, message = HabilitationManager.renommer(id_hab, nouveau_nom)
            if not succes:
                self.messages.warning("Modification impossible", message)
                return

            # Recharger depuis SQLite : les valeurs de la colonne renommée
            # restent intactes et le DataFrame récupère le nouveau nom.
            self.data.df = self.data.charger()
            self.creer_formulaire()
            self.actualiser_colonnes_tableau()

            habilitations_actives = HabilitationManager.lister()
            self.combo_hab["values"] = ("", *habilitations_actives)
            if hasattr(self, "rech_habilitation"):
                self.rech_habilitation.set("")

            actualiser_liste()
            for ligne in tree.get_children():
                valeurs_ligne = tree.item(ligne, "values")
                if str(valeurs_ligne[0]) == str(id_hab):
                    tree.selection_set(ligne)
                    tree.focus(ligne)
                    tree.see(ligne)
                    break

            log_info(f"Habilitation renommée : {ancien_nom} -> {nouveau_nom}")
            self.messages.info("Modification réussie", message)

        # Fonction Supprimer
        # ==========================================

        def supprimer_habilitation():

            if not SessionManager.est_administrateur():
                self.messages.warning(
                    titre="Accès refusé",
                    message="Vous devez être administrateur pour supprimer une habilitation."
                )
                return

            # ==========================================
            # Récupération de la sélection
            # ==========================================

            selection = tree.selection()

            if not selection:
                self.messages.warning(
                    "Attention",
                    "Veuillez sélectionner une habilitation."
                )

                return

            # ==========================================
            # Récupération de la ligne sélectionnée
            # ==========================================

            item = selection[0]

            valeurs = tree.item(
                item,
                "values"
            )

            id_hab = valeurs[0]
            nom = valeurs[1]

            # ==========================================
            # Confirmation avant suppression
            # ==========================================

            confirmation = self.messages.confirm(
                titre="Confirmation",
                message=(
                    f"Voulez-vous vraiment supprimer "
                    f"l'habilitation « {nom} » ?\n\n"
                    "Cette action supprimera également "
                    "sa colonne dans les données."
                )
            )

            if not confirmation:
                return

            # ==========================================
            # Suppression dans SQLite
            # ==========================================

            succes, message = (
                HabilitationManager.supprimer(
                    id_hab
                )
            )

            # ==========================================
            # Gestion d'une erreur
            # ==========================================

            if not succes:
                self.messages.warning(
                    "Attention",
                    message
                )

                return

            log_info(
                f"Habilitation supprimée : {nom}"
            )

            # ==========================================
            # Actualiser la liste de la fenêtre
            # Gestion des habilitations
            # ==========================================

            actualiser_liste()

            # ==========================================
            # Suppression immédiate de la colonne
            # dans le DataFrame mémoire
            # ==========================================

            if nom in self.data.df.columns:
                self.data.df.drop(
                    columns=[nom],
                    inplace=True
                )

            # ==========================================
            # Rechargement des données depuis SQLite
            #
            # Permet de garantir que le DataFrame mémoire
            # correspond exactement à la structure actuelle.
            # ==========================================

            self.data.df = self.data.charger()

            # ==========================================
            # Réinitialiser le filtre habilitation
            # ==========================================

            if hasattr(
                    self,
                    "rech_habilitation"
            ):
                self.rech_habilitation.set("")

            # ==========================================
            # Actualisation de la Fiche salarié
            #
            # Même stratégie que pour Ajouter.
            # ==========================================

            self.creer_formulaire()

            # ==========================================
            # Actualisation du tableau principal
            #
            # Utilise la méthode centralisée.
            # ==========================================

            self.actualiser_colonnes_tableau()

            # ==========================================
            # Confirmation
            # ==========================================

            self.messages.info(
                "Information",
                message
            )

        # ==========================================
        # Boutons Modifier et Supprimer sur la même ligne que le champ
        # ==========================================

        # ==========================================
        # Bouton Modifier
        # ==========================================

        self.icone_modifier_habilitation = charger_icone(
            "pencil", 12
        )

        ttk.Button(
            cadre_ajout,
            text="Modifier",
            image=self.icone_modifier_habilitation,
            compound="left",
            command=modifier_habilitation,
            bootstyle="warning"
        ).pack(
            side="left",
            padx=10
        )

        # Bouton Supprimer
        # ==========================================

        self.icone_supprimer_habilitation = charger_icone(
            "trash", 12
        )

        ttk.Button(
            cadre_ajout,
            text="Supprimer",
            image=self.icone_supprimer_habilitation,
            compound="left",
            command=supprimer_habilitation,
            bootstyle="danger"
        ).pack(
            side="left",
            padx=10
        )

        # ==========================================
        # Fermer
        # ==========================================

        self.icone_fermer = charger_icone(
            "x", 12
        )

        ttk.Button(
            fenetre,
            text="Fermer",
            image=self.icone_fermer,
            compound="left",
            command=self.windows.fermer,
            bootstyle="danger"
        ).pack(
            pady=10
        )

    def gestion_utilisateurs(self):

        if not SessionManager.est_administrateur():
            self.messages.warning(
                titre="Accès refusé",
                message="Vous devez être administrateur pour gérer les comptes utilisateurs."
            )
            return

        fenetre = ttk.Toplevel(self.root)

        self.windows.ouvrir(fenetre)

        fenetre.protocol(
            "WM_DELETE_WINDOW",
            self.windows.fermer
        )

        fenetre.title(
            "Gestion des comptes utilisateurs"
        )

        fenetre.geometry(
            "900x500"
        )

        fenetre.transient(self.root)

        # ==========================================
        # Titre
        # ==========================================

        ttk.Label(
            fenetre,
            text="Gestion des comptes utilisateurs",
            font=("Segoe UI", 14, "bold")
        ).pack(
            pady=10
        )

        # ==========================================
        # Filtre des utilisateurs
        # ==========================================

        cadre_filtre = ttk.Frame(fenetre)
        cadre_filtre.pack(
            fill="x",
            padx=20,
            pady=(0, 5)
        )

        ttk.Label(
            cadre_filtre,
            text="Afficher :"
        ).pack(
            side="left",
            padx=(0, 10)
        )

        filtre_var = ttk.StringVar(
            value="Actifs"
        )

        filtre = ttk.Combobox(
            cadre_filtre,
            textvariable=filtre_var,
            values=(
                "Actifs",
                "Archivés",
                "Tous"
            ),
            state="readonly",
            width=15
        )

        filtre.pack(
            side="left"
        )

        # ==========================================
        # Tableau
        # ==========================================

        cadre = ttk.Frame(
            fenetre
        )

        cadre.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=10
        )

        colonnes = (
            "Code",
            "Nom",
            "Prénom",
            "Profil",
            "Statut",
            "Date de création"
        )

        tree = ttk.Treeview(
            cadre,
            columns=colonnes,
            show="headings"
        )

        for colonne in colonnes:
            tree.heading(
                colonne,
                text=colonne
            )

        tree.column(
            "Code",
            width=120,
            anchor="center"
        )

        tree.column(
            "Nom",
            width=150,
            anchor="center"
        )

        tree.column(
            "Prénom",
            width=150,
            anchor="center"
        )

        tree.column(
            "Profil",
            width=150,
            anchor="center"
        )

        tree.column(
            "Statut",
            width=100,
            anchor="center"
        )

        tree.column(
            "Date de création",
            width=180,
            anchor="center"
        )

        scrollbar = ttk.Scrollbar(
            cadre,
            orient="vertical",
            command=tree.yview
        )

        tree.configure(
            yscrollcommand=scrollbar.set
        )

        tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        # ==========================================
        # Chargement des utilisateurs actifs
        # ==========================================

        utilisateurs = (
            UtilisateurManager
            .lister_utilisateurs()
        )

        for utilisateur in utilisateurs:
            (
                id_utilisateur,
                code,
                nom,
                prenom,
                profil,
                actif,
                date_creation
            ) = utilisateur

            tree.insert(
                "",
                "end",
                iid=str(id_utilisateur),
                values=(
                    code,
                    nom,
                    prenom,
                    profil,
                    "Actif" if actif else "Archivé",
                    date_creation
                )
            )

        # ==========================================
        # Actualisation de la liste
        # ==========================================

        def actualiser_liste():

            tree.delete(
                *tree.get_children()
            )

            choix = filtre_var.get()

            if choix == "Actifs":

                utilisateurs = (
                    UtilisateurManager
                    .lister_utilisateurs(
                        actifs_uniquement=True
                    )
                )

            elif choix == "Archivés":

                tous = (
                    UtilisateurManager
                    .lister_utilisateurs(
                        actifs_uniquement=False
                    )
                )

                utilisateurs = [
                    utilisateur
                    for utilisateur in tous
                    if not utilisateur[5]
                ]

            else:

                utilisateurs = (
                    UtilisateurManager
                    .lister_utilisateurs(
                        actifs_uniquement=False
                    )
                )

            for utilisateur in utilisateurs:
                (
                    id_utilisateur,
                    code,
                    nom,
                    prenom,
                    profil,
                    actif,
                    date_creation
                ) = utilisateur

                tree.insert(
                    "",
                    "end",
                    iid=str(id_utilisateur),
                    values=(
                        code,
                        nom,
                        prenom,
                        profil,
                        "Actif" if actif else "Archivé",
                        date_creation
                    )
                )

        filtre.bind(
            "<<ComboboxSelected>>",
            lambda event: actualiser_liste()
        )

        actualiser_liste()

        # ==========================================
        # Modifier un utilisateur
        # ==========================================

        def modifier_utilisateur():

            # Sécurité : accès administrateur uniquement
            if not SessionManager.est_administrateur():
                self.messages.warning(
                    titre="Accès refusé",
                    message=(
                        "Vous devez être administrateur "
                        "pour modifier un compte utilisateur."
                    )
                )
                return

            selection = tree.selection()

            if not selection:
                self.messages.warning(
                    titre="Aucun utilisateur sélectionné",
                    message=(
                        "Veuillez sélectionner un utilisateur "
                        "à modifier."
                    )
                )
                return

            item = selection[0]

            id_utilisateur = int(item)

            valeurs = tree.item(
                item,
                "values"
            )

            code = valeurs[0]
            nom = valeurs[1]
            prenom = valeurs[2]
            profil = valeurs[3]

            email = UtilisateurManager.recuperer_email(
                id_utilisateur
            )

            fenetre_modification = ttk.Toplevel(
                fenetre
            )

            fenetre_modification.title(
                "Modifier un utilisateur"
            )

            fenetre_modification.geometry(
                "500x650"
            )

            fenetre_modification.resizable(
                False,
                False
            )

            fenetre_modification.transient(
                fenetre
            )

            cadre = ttk.Frame(
                fenetre_modification,
                padding=20
            )
            cadre.pack(
                fill="both",
                expand=True
            )

            # ==========================================
            # Code
            # ==========================================

            ttk.Label(
                cadre,
                text="Code"
            ).pack(
                anchor="w",
                pady=(0, 5)
            )

            entree_code = ttk.Entry(
                cadre
            )
            entree_code.pack(
                fill="x",
                pady=(0, 15)
            )

            entree_code.insert(
                0,
                code
            )

            entree_code.configure(
                state="readonly"
            )

            # ==========================================
            # Nom
            # ==========================================

            ttk.Label(
                cadre,
                text="Nom"
            ).pack(
                anchor="w",
                pady=(0, 5)
            )

            entree_nom = ttk.Entry(
                cadre
            )
            entree_nom.pack(
                fill="x",
                pady=(0, 15)
            )

            entree_nom.insert(
                0,
                nom
            )

            # ==========================================
            # Prénom
            # ==========================================

            ttk.Label(
                cadre,
                text="Prénom"
            ).pack(
                anchor="w",
                pady=(0, 5)
            )

            entree_prenom = ttk.Entry(
                cadre
            )
            entree_prenom.pack(
                fill="x",
                pady=(0, 15)
            )

            entree_prenom.insert(
                0,
                prenom
            )

            # ==========================================
            # Adresse e-mail
            # ==========================================

            ttk.Label(
                cadre,
                text="Adresse e-mail"
            ).pack(
                anchor="w",
                pady=(0, 5)
            )

            entree_email = ttk.Entry(
                cadre
            )

            entree_email.pack(
                fill="x",
                pady=(0, 15)
            )

            entree_email.insert(
                0,
                email or ""
            )

            # ==========================================
            # Profil
            # ==========================================

            ttk.Label(
                cadre,
                text="Profil"
            ).pack(
                anchor="w",
                pady=(0, 5)
            )

            profil_var = ttk.StringVar(
                value=profil
            )

            combo_profil = ttk.Combobox(
                cadre,
                textvariable=profil_var,
                values=PROFILS,
                state="readonly"
            )
            combo_profil.pack(
                fill="x",
                pady=(0, 15)
            )

            # ==========================================
            # Cadre mot de passe
            # ==========================================

            cadre_mot_de_passe = ttk.Frame(
                cadre
            )

            # ==========================================
            # Nouveau mot de passe
            # ==========================================

            ttk.Label(
                cadre_mot_de_passe,
                text=(
                    "Nouveau mot de passe "
                    "(laisser vide pour conserver l'actuel)"
                )
            ).pack(
                anchor="w",
                pady=(0, 5)
            )

            entree_mot_de_passe = ttk.Entry(
                cadre_mot_de_passe,
                show="•"
            )
            entree_mot_de_passe.pack(
                fill="x",
                pady=(0, 15)
            )

            # ==========================================
            # Confirmation
            # ==========================================

            ttk.Label(
                cadre_mot_de_passe,
                text="Confirmation du nouveau mot de passe"
            ).pack(
                anchor="w",
                pady=(0, 5)
            )

            entree_confirmation = ttk.Entry(
                cadre_mot_de_passe,
                show="•"
            )
            entree_confirmation.pack(
                fill="x",
                pady=(0, 20)
            )

            # ==========================================
            # Boutons de la fenêtre de modification
            # ==========================================

            cadre_actions = ttk.Frame(
                cadre
            )
            cadre_actions.pack(
                pady=10
            )

            # ==========================================
            # Affichage du mot de passe selon le profil
            # ==========================================

            def actualiser_mot_de_passe(event=None):

                if profil_var.get() == "Administrateur":

                    cadre_mot_de_passe.pack(
                        fill="x",
                        before=cadre_actions
                    )

                else:

                    entree_mot_de_passe.delete(
                        0,
                        "end"
                    )

                    entree_confirmation.delete(
                        0,
                        "end"
                    )

                    cadre_mot_de_passe.pack_forget()

            # ==========================================
            # Enregistrer
            # ==========================================

            def enregistrer():

                nouveau_nom = entree_nom.get().strip()
                nouveau_prenom = entree_prenom.get().strip()
                nouveau_profil = profil_var.get()
                nouvel_email = entree_email.get().strip()

                nouveau_mot_de_passe = (
                    entree_mot_de_passe.get()
                )

                confirmation_mot_de_passe = (
                    entree_confirmation.get()
                )

                # --------------------------------------
                # Vérification du nom
                # --------------------------------------

                if not nouveau_nom:
                    self.messages.warning(
                        titre="Nom obligatoire",
                        message="Le nom est obligatoire.",
                        parent=fenetre_modification
                    )
                    return

                # --------------------------------------
                # Vérification du prénom
                # --------------------------------------

                if not nouveau_prenom:
                    self.messages.warning(
                        titre="Prénom obligatoire",
                        message="Le prénom est obligatoire.",
                        parent=fenetre_modification
                    )
                    return

                # --------------------------------------
                # Vérification du mot de passe
                # --------------------------------------

                if nouveau_profil == "Administrateur":

                    if nouveau_mot_de_passe:

                        if (
                                nouveau_mot_de_passe
                                != confirmation_mot_de_passe
                        ):
                            self.messages.warning(
                                titre="Mots de passe différents",
                                message=(
                                    "Le nouveau mot de passe "
                                    "et sa confirmation sont différents."
                                ),
                                parent=fenetre_modification
                            )
                            return

                    elif confirmation_mot_de_passe:

                        self.messages.warning(
                            titre="Mot de passe incomplet",
                            message=(
                                "Veuillez saisir le nouveau "
                                "mot de passe dans les deux champs."
                            ),
                            parent=fenetre_modification
                        )
                        return

                else:

                    nouveau_mot_de_passe = None

                # --------------------------------------
                # Modification en base
                # --------------------------------------

                try:

                    UtilisateurManager.modifier_utilisateur(
                        id_utilisateur=id_utilisateur,
                        nom=nouveau_nom,
                        prenom=nouveau_prenom,
                        profil=nouveau_profil,
                        nouveau_mot_de_passe=(
                            nouveau_mot_de_passe
                            if nouveau_mot_de_passe
                            else None
                        ),
                        email=nouvel_email,
                    )

                except ValueError as erreur:

                    self.messages.warning(
                        titre="Modification impossible",
                        message=str(erreur),
                        parent=fenetre_modification
                    )
                    return

                except Exception:

                    self.messages.error(
                        titre="Erreur",
                        message=(
                            "Une erreur est survenue "
                            "lors de la modification du compte."
                        ),
                        parent=fenetre_modification
                    )
                    return

                # --------------------------------------
                # Confirmation
                # --------------------------------------

                self.messages.info(
                    titre="Compte modifié",
                    message=(
                        f"Le compte « {code} » "
                        "a été modifié avec succès."
                    ),
                    parent=fenetre_modification
                )

                fenetre_modification.destroy()

                actualiser_liste()

            # ==========================================
            # Réaction au changement de profil
            # ==========================================

            combo_profil.bind(
                "<<ComboboxSelected>>",
                actualiser_mot_de_passe
            )

            # ==========================================
            # Affichage initial
            # ==========================================

            actualiser_mot_de_passe()

            # ==========================================
            # Boutons
            # ==========================================

            fenetre_modification.icone_enregistrer = charger_icone(
                "save", 12
            )

            fenetre_modification.icone_annuler = charger_icone(
                "x", 12
            )

            cadre_actions = ttk.Frame(
                cadre
            )
            cadre_actions.pack(
                pady=10
            )

            ttk.Button(
                cadre_actions,
                text="Enregistrer",
                image=fenetre_modification.icone_enregistrer,
                compound="left",
                command=enregistrer,
                bootstyle="success"
            ).pack(
                side="left",
                padx=5
            )

            ttk.Button(
                cadre_actions,
                text="Annuler",
                image=fenetre_modification.icone_annuler,
                compound="left",
                command=fenetre_modification.destroy,
                bootstyle="secondary"
            ).pack(
                side="left",
                padx=5
            )

            actualiser_mot_de_passe()

        # ==========================================
        # Fermer
        # ==========================================

        self.icone_fermer_utilisateurs = charger_icone(
            "x", 12
        )

        # ==========================================
        # Boutons
        # ==========================================

        cadre_boutons = ttk.Frame(fenetre)
        cadre_boutons.pack(pady=10)

        # ==========================================
        # Ajouter
        # ==========================================

        self.icone_ajouter_utilisateur = charger_icone(
            "circle-plus", 12
        )

        ttk.Button(
            cadre_boutons,
            text="Ajouter",
            image=self.icone_ajouter_utilisateur,
            compound="left",
            command=self.ajouter_utilisateur,
            bootstyle="success"
        ).pack(
            side="left",
            padx=5
        )

        # ==========================================
        # Modifier
        # ==========================================

        self.icone_modifier_utilisateur = charger_icone(
            "pencil", 12
        )

        ttk.Button(
            cadre_boutons,
            text="Modifier",
            image=self.icone_modifier_utilisateur,
            compound="left",
            command=modifier_utilisateur,
            bootstyle="primary"
        ).pack(
            side="left",
            padx=5
        )

        # ==========================================
        # Réactiver
        # ==========================================

        def demander_reactivation():

            selection = tree.selection()

            if not selection:
                self.messages.warning(
                    titre="Aucun utilisateur sélectionné",
                    message=(
                        "Veuillez sélectionner un utilisateur "
                        "archivé à réactiver."
                    )
                )
                return

            item = selection[0]

            id_utilisateur = int(item)

            valeurs = tree.item(
                item,
                "values"
            )

            code = valeurs[0]
            nom = valeurs[1]
            prenom = valeurs[2]
            profil = valeurs[3]
            statut = valeurs[4]

            # --------------------------------------
            # Vérification du statut
            # --------------------------------------

            if statut != "Archivé":
                self.messages.warning(
                    titre="Réactivation impossible",
                    message=(
                        f"Le compte « {code} » est déjà actif.\n\n"
                        "Seuls les comptes archivés peuvent être "
                        "réactivés."
                    )
                )
                return

            # --------------------------------------
            # Confirmation
            # --------------------------------------

            confirmation = self.messages.confirm(
                titre="Confirmation de réactivation",
                message=(
                    "Voulez-vous vraiment réactiver le compte :\n\n"
                    f"Code : {code}\n"
                    f"Nom : {nom}\n"
                    f"Prénom : {prenom}\n"
                    f"Profil : {profil}\n\n"
                    "Ce compte pourra à nouveau se connecter."
                )
            )

            if not confirmation:
                return

            # --------------------------------------
            # Réactivation
            # --------------------------------------

            try:

                UtilisateurManager.reactiver_utilisateur(
                    id_utilisateur
                )

            except ValueError as erreur:

                self.messages.warning(
                    titre="Réactivation impossible",
                    message=str(erreur)
                )
                return

            except Exception:

                self.messages.error(
                    titre="Erreur",
                    message=(
                        "Une erreur est survenue "
                        "lors de la réactivation du compte."
                    )
                )
                return

            # --------------------------------------
            # Confirmation
            # --------------------------------------

            self.messages.info(
                titre="Compte réactivé",
                message=(
                    f"Le compte « {code} » "
                    "a été réactivé avec succès."
                )
            )

            # --------------------------------------
            # Actualisation de la liste
            # --------------------------------------

            actualiser_liste()

        self.icone_reactiver_utilisateur = charger_icone(
            "rotate-ccw", 12
        )

        ttk.Button(
            cadre_boutons,
            text="Réactiver",
            image=self.icone_reactiver_utilisateur,
            compound="left",
            command=demander_reactivation,
            bootstyle="success"
        ).pack(
            side="left",
            padx=5
        )

        # ==========================================
        # Archiver
        # ==========================================

        def demander_archivage():

            selection = tree.selection()

            if not selection:
                self.messages.warning(
                    titre="Aucun utilisateur sélectionné",
                    message=(
                        "Veuillez sélectionner un utilisateur "
                        "à archiver."
                    )
                )
                return

            item = selection[0]

            id_utilisateur = int(item)

            valeurs = tree.item(
                item,
                "values"
            )

            code = valeurs[0]
            nom = valeurs[1]
            prenom = valeurs[2]
            profil = valeurs[3]
            statut = valeurs[4]

            # --------------------------------------
            # Protection du dernier administrateur
            # --------------------------------------

            if profil == "Administrateur":

                utilisateurs = (
                    UtilisateurManager.lister_utilisateurs()
                )

                nombre_admins_actifs = sum(
                    1
                    for utilisateur in utilisateurs
                    if utilisateur[4] == "Administrateur"
                )

                if nombre_admins_actifs <= 1:
                    self.messages.warning(
                        titre="Archivage impossible",
                        message=(
                            f"Le compte « {code} » "
                            "ne peut pas être archivé.\n\n"
                            "Il doit toujours rester au moins "
                            "un administrateur actif."
                        )
                    )
                    return

            # --------------------------------------
            # Compte déjà archivé
            # --------------------------------------

            if statut == "Archivé":
                self.messages.warning(
                    titre="Compte déjà archivé",
                    message=(
                        f"Le compte « {code} » est déjà archivé.\n\n"
                        "Aucune action n'est nécessaire."
                    )
                )
                return

            # --------------------------------------
            # Confirmation
            # --------------------------------------

            confirmation = self.messages.confirm(
                titre="Confirmation",
                message=(
                    "Voulez-vous vraiment archiver le compte :\n\n"
                    f"Code : {code}\n"
                    f"Nom : {nom}\n"
                    f"Prénom : {prenom}\n"
                    f"Profil : {profil}\n\n"
                    "Le compte ne pourra plus se connecter."
                )
            )

            if not confirmation:
                return

            # --------------------------------------
            # Archivage
            # --------------------------------------

            try:

                UtilisateurManager.archiver_utilisateur(
                    id_utilisateur
                )

            except ValueError as erreur:

                self.messages.warning(
                    titre="Archivage impossible",
                    message=str(erreur)
                )
                return

            except Exception:

                self.messages.error(
                    titre="Erreur",
                    message=(
                        "Une erreur est survenue "
                        "lors de l'archivage du compte."
                    )
                )
                return

            # --------------------------------------
            # Confirmation
            # --------------------------------------

            self.messages.info(
                titre="Compte archivé",
                message=(
                    f"Le compte « {code} » "
                    "a été archivé avec succès."
                )
            )

            actualiser_liste()

        self.icone_archiver_utilisateur = charger_icone(
            "archive", 12
        )

        ttk.Button(
            cadre_boutons,
            text="Archiver",
            image=self.icone_archiver_utilisateur,
            compound="left",
            command=demander_archivage,
            bootstyle="warning"
        ).pack(
            side="left",
            padx=5
        )

        # ==========================================
        # Fermer
        # ==========================================

        self.icone_fermer_utilisateurs = charger_icone(
            "x", 12
        )

        ttk.Button(
            cadre_boutons,
            text="Fermer",
            image=self.icone_fermer_utilisateurs,
            compound="left",
            command=self.windows.fermer,
            bootstyle="danger"
        ).pack(
            side="left",
            padx=5
        )

    def consulter_logs(self):

        if not SessionManager.est_administrateur():
            self.messages.warning(
                titre="Accès refusé",
                message="Vous devez être administrateur pour consulter les logs."
            )
            return

        fenetre = ttk.Toplevel(self.root)

        self.windows.ouvrir(fenetre)

        fenetre.title("Rapport des logs")
        fenetre.geometry("1250x600")

        fenetre.transient(self.root)

        ttk.Label(
            fenetre,
            text="Rapport des logs",
            font=("Segoe UI", 14, "bold")
        ).pack(pady=10)

        # ==========================================
        # ZONE DE TEXTE
        # ==========================================

        cadre = ttk.Frame(fenetre)
        cadre.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=10
        )

        texte = tk.Text(
            cadre,
            wrap="none",
            font=("Consolas", 10)
        )

        scrollbar_verticale = ttk.Scrollbar(
            cadre,
            orient="vertical",
            command=texte.yview
        )

        scrollbar_horizontale = ttk.Scrollbar(
            cadre,
            orient="horizontal",
            command=texte.xview
        )

        texte.configure(
            yscrollcommand=scrollbar_verticale.set,
            xscrollcommand=scrollbar_horizontale.set
        )

        texte.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        scrollbar_verticale.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        scrollbar_horizontale.grid(
            row=1,
            column=0,
            sticky="ew"
        )

        cadre.columnconfigure(0, weight=1)
        cadre.rowconfigure(0, weight=1)

        # ==========================================
        # LECTURE DU FICHIER LOG
        # ==========================================

        fichier_log = FICHIER_LOG

        if fichier_log.exists():

            try:

                contenu = fichier_log.read_text(
                    encoding="utf-8"
                )

                lignes = contenu.splitlines()

                lignes.reverse()

                texte.insert(
                    "1.0",
                    "\n".join(lignes)
                )

            except Exception as erreur:

                texte.insert(
                    "1.0",
                    f"Impossible de lire le fichier de logs :\n\n{erreur}"
                )

        else:

            texte.insert(
                "1.0",
                "Aucun fichier de logs disponible."
            )

        texte.configure(
            state="disabled"
        )

        # ==========================================
        # BOUTON FERMER
        # ==========================================

        self.icone_fermer_logs = charger_icone(
            "x", 12
        )

        ttk.Button(
            fenetre,
            text="Fermer",
            image=self.icone_fermer_logs,
            compound="left",
            command=fenetre.destroy,
            bootstyle="danger"
        ).pack(pady=10)

    def ajouter_document_salarie(self):
        """Fusionne des images/PDF et enregistre le résultat chez le salarié sélectionné."""

        selection = self.tree.selection()

        if not selection:
            self.messages.warning(
                "Ajouter un document",
                "Veuillez sélectionner un salarié."
            )
            return

        id_salarie = selection[0]
        ligne = self.data.df[
            self.data.df["ID"].astype(str) == str(id_salarie)
        ]

        if ligne.empty:
            self.messages.error(
                "Erreur",
                "Le salarié sélectionné est introuvable."
            )
            return

        salarie = ligne.iloc[0]

        try:
            chemin = convertir_et_fusionner_documents(
                nom=salarie["Nom"],
                prenom=salarie["Prénom"],
                id_salarie=salarie["ID"],
                parent=self.root,
            )
        except (FileNotFoundError, ValueError, RuntimeError, OSError) as erreur:
            self.messages.error(
                "Fusion PDF impossible",
                str(erreur)
            )
            return
        except Exception as erreur:
            # Dernière protection pour afficher une erreur compréhensible à l'utilisateur.
            log_warning(f"Échec de la fusion des documents : {erreur}")
            self.messages.error(
                "Fusion PDF impossible",
                f"Une erreur inattendue est survenue.\n\n{erreur}"
            )
            return

        # None signifie que l'utilisateur a annulé une étape.
        if chemin is None:
            return

        self.messages.info(
            "PDF ajouté",
            "Le PDF fusionné a été enregistré dans le dossier du salarié.\n\n"
            f"{chemin.name}"
        )

    def ouvrir_dossier_du_salarie(self):
        """Ouvre le dossier du salarié sélectionné."""

        selection = self.tree.selection()

        if not selection:
            self.messages.warning(
                "Ouvrir le dossier",
                "Veuillez sélectionner un salarié."
            )
            return

        id_salarie = selection[0]

        ligne = self.data.df[
            self.data.df["ID"].astype(str) == str(id_salarie)
            ]

        if ligne.empty:
            self.messages.error(
                "Erreur",
                "Le salarié sélectionné est introuvable."
            )
            return

        salarie = ligne.iloc[0]

        try:
            ouvrir_dossier_salarie(
                salarie["Nom"],
                salarie["Prénom"],
                salarie["ID"]
            )

        except OSError as erreur:
            self.messages.error(
                "Erreur",
                f"Impossible d'ouvrir le dossier.\n\n{erreur}"
            )

    def gerer_documents_salarie(self):
        """Ouvre la fenêtre de gestion des documents du salarié sélectionné."""

        selection = self.tree.selection()

        if not selection:
            self.messages.warning(
                "Documents du salarié",
                "Veuillez sélectionner un salarié."
            )
            return

        id_salarie = selection[0]

        ligne = self.data.df[
            self.data.df["ID"].astype(str) == str(id_salarie)
            ]

        if ligne.empty:
            self.messages.error(
                "Erreur",
                "Le salarié sélectionné est introuvable."
            )
            return

        salarie = ligne.iloc[0]

        nom = str(salarie["Nom"]).strip()
        prenom = str(salarie["Prénom"]).strip()
        id_salarie = str(salarie["ID"]).strip()

        # --------------------------------------------------
        # Fenêtre
        # --------------------------------------------------

        fenetre = ttk.Toplevel(self.root)

        fenetre.title(
            f"Documents — {nom} {prenom}"
        )

        fenetre.geometry("800x450")
        fenetre.minsize(700, 350)
        fenetre.transient(self.root)

        # --------------------------------------------------
        # Titre
        # --------------------------------------------------

        self.icone_titre_documents = charger_icone("folder-open", 12)
        ttk.Label(
            fenetre,
            text=f"Documents — {nom} {prenom}",
            image=self.icone_titre_documents,
            compound="left",
            font=("Segoe UI", 14, "bold")
        ).pack(
            pady=(15, 10)
        )

        # --------------------------------------------------
        # Zone liste
        # --------------------------------------------------

        cadre_liste = ttk.Frame(
            fenetre
        )

        cadre_liste.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=5
        )

        liste = tk.Listbox(
            cadre_liste,
            font=("Segoe UI", 10),
            activestyle="none"
        )

        scrollbar = ttk.Scrollbar(
            cadre_liste,
            orient="vertical",
            command=liste.yview
        )

        liste.configure(
            yscrollcommand=scrollbar.set
        )

        liste.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        # --------------------------------------------------
        # Chemins des documents
        # --------------------------------------------------

        chemins_documents = []

        def actualiser_liste():
            """Actualise la liste des documents du salarié."""

            from pathlib import Path
            from config import DOSSIER_SALARIES

            nom_dossier = (
                f"{nom}_{prenom}_{id_salarie[:8]}"
            )

            dossier = (
                    Path(DOSSIER_SALARIES)
                    / nom_dossier
            )

            dossier.mkdir(
                parents=True,
                exist_ok=True
            )

            fichiers = sorted(
                [
                    fichier
                    for fichier in dossier.iterdir()
                    if fichier.is_file()
                ],
                key=lambda fichier: fichier.name.lower()
            )

            chemins_documents.clear()
            chemins_documents.extend(fichiers)

            liste.delete(
                0,
                tk.END
            )

            for fichier in fichiers:
                liste.insert(
                    tk.END,
                    fichier.name
                )

        actualiser_liste()

        # --------------------------------------------------
        # Boutons
        # --------------------------------------------------

        def ajouter_document_selectionne():
            """Ajoute un document seul ou fusionne plusieurs images/PDF."""

            choix_fusion = messagebox.askyesnocancel(
                "Ajouter un document",
                (
                    "Souhaitez-vous convertir/fusionner plusieurs images ou PDF ?"
                    "Oui : sélectionner plusieurs fichiers et créer un PDF."
                    "Non : ajouter un seul document, quel que soit son format."
                ),
                parent=fenetre,
            )
            if choix_fusion is None:
                return

            if choix_fusion:
                try:
                    chemin = convertir_et_fusionner_documents(
                        nom=nom,
                        prenom=prenom,
                        id_salarie=id_salarie,
                        parent=fenetre,
                    )
                except (FileNotFoundError, ValueError, RuntimeError, OSError) as erreur:
                    self.messages.error(
                        "Fusion PDF impossible", str(erreur), parent=fenetre
                    )
                    return
                except Exception as erreur:
                    log_warning(f"Échec de la fusion des documents : {erreur}")
                    self.messages.error(
                        "Fusion PDF impossible",
                        f"Une erreur inattendue est survenue. {erreur}",
                        parent=fenetre,
                    )
                    return

                if chemin is None:
                    return
                actualiser_liste()
                self.messages.info(
                    "PDF ajouté",
                    f"Le PDF fusionné a été enregistré : {chemin.name}",
                    parent=fenetre,
                )
                return

            # Mode historique : ajout simple d'un fichier de n'importe quel format.
            fichier_source = selectionner_document()
            if fichier_source is None:
                return

            try:
                chemin = copier_document(
                    nom, prenom, id_salarie, fichier_source
                )
            except FileExistsError:
                confirmation = self.messages.confirm(
                    "Document déjà existant",
                    (
                        "Un document portant ce nom existe déjà."
                        f"{fichier_source.name}"
                        "Voulez-vous le remplacer ?"
                    ),
                    parent=fenetre,
                )
                if not confirmation:
                    return
                try:
                    chemin = copier_document(
                        nom, prenom, id_salarie, fichier_source, remplacer=True
                    )
                except (FileNotFoundError, OSError) as erreur:
                    self.messages.error(
                        "Erreur",
                        f"Impossible de remplacer le document. {erreur}",
                        parent=fenetre,
                    )
                    return
            except (FileNotFoundError, OSError) as erreur:
                self.messages.error(
                    "Erreur",
                    f"Impossible d'ajouter le document. {erreur}",
                    parent=fenetre,
                )
                return

            actualiser_liste()
            self.messages.info(
                "Document ajouté",
                f"Le document a été ajouté : {chemin.name}",
                parent=fenetre,
            )

        def visualiser_document_selectionne():
            """Ouvre le document choisi dans son application habituelle."""

            selection = liste.curselection()
            if not selection:
                self.messages.warning(
                    "Visualiser un document",
                    "Veuillez sélectionner un document dans la liste.",
                    parent=fenetre,
                )
                return

            index = selection[0]
            if index >= len(chemins_documents):
                self.messages.error(
                    "Erreur",
                    "Le document sélectionné est introuvable.",
                    parent=fenetre,
                )
                return

            chemin_document = chemins_documents[index]
            try:
                ouvrir_document(chemin_document)
            except (FileNotFoundError, OSError) as erreur:
                self.messages.error(
                    "Ouverture impossible",
                    f"Impossible d'ouvrir le document. {erreur}",
                    parent=fenetre,
                )

        def imprimer_document_selectionne():
            """Ouvre le document sélectionné pour impression."""

            selection = liste.curselection()

            if not selection:
                self.messages.warning(
                    "Imprimer un document",
                    "Veuillez sélectionner un document dans la liste.",
                    parent=fenetre,
                )
                return

            index = selection[0]

            if index >= len(chemins_documents):
                self.messages.error(
                    "Erreur",
                    "Le document sélectionné est introuvable.",
                    parent=fenetre,
                )
                return

            chemin_document = chemins_documents[index]

            try:
                preparer_impression_document(chemin_document)

            except (FileNotFoundError, OSError) as erreur:
                self.messages.error(
                    "Impression impossible",
                    f"Impossible d'ouvrir le document pour impression. {erreur}",
                    parent=fenetre,
                )
                return

        def renommer_document_selectionne():
            """Renomme le document sélectionné."""

            selection = liste.curselection()

            if not selection:
                self.messages.warning(
                    "Renommer",
                    "Veuillez sélectionner un document."
                )
                return

            index = selection[0]

            if index >= len(chemins_documents):
                self.messages.error(
                    "Erreur",
                    "Le document sélectionné est introuvable."
                )
                return

            chemin_document = chemins_documents[index]

            nouveau_nom = simpledialog.askstring(
                "Renommer le document",
                "Nouveau nom :",
                initialvalue=chemin_document.name,
                parent=fenetre
            )

            if nouveau_nom is None:
                return

            nouveau_nom = nouveau_nom.strip()

            if not nouveau_nom:
                self.messages.warning(
                    "Renommer",
                    "Le nouveau nom ne peut pas être vide."
                )
                return

            try:
                nouveau_chemin = renommer_document(
                    chemin_document,
                    nouveau_nom
                )

            except FileNotFoundError as erreur:
                self.messages.error(
                    "Erreur",
                    str(erreur)
                )
                return

            except FileExistsError as erreur:
                self.messages.error(
                    "Renommer",
                    str(erreur)
                )
                return

            except ValueError as erreur:
                self.messages.warning(
                    "Renommer",
                    str(erreur)
                )
                return

            except OSError as erreur:
                self.messages.error(
                    "Erreur",
                    f"Impossible de renommer le document. {erreur}"
                )
                return

            actualiser_liste()

            self.messages.info(
                "Document renommé",
                (
                    "Le document a été renommé : "
                    f"{nouveau_chemin.name}"
                )
            )

        def supprimer_document_selectionne():
            """Supprime le document sélectionné après confirmation."""

            selection = liste.curselection()

            if not selection:
                self.messages.warning(
                    "Supprimer",
                    "Veuillez sélectionner un document."
                )
                return

            index = selection[0]

            if index >= len(chemins_documents):
                self.messages.error(
                    "Erreur",
                    "Le document sélectionné est introuvable."
                )
                return

            chemin_document = chemins_documents[index]

            confirmation = self.messages.confirm(
                "Supprimer le document",
                (
                    "Voulez-vous vraiment supprimer ce document ? "
                    f"{chemin_document.name}"
                ),
                parent=fenetre
            )

            if not confirmation:
                return

            try:
                supprimer_document(
                    chemin_document
                )

            except FileNotFoundError as erreur:
                self.messages.error(
                    "Erreur",
                    str(erreur)
                )
                return

            except OSError as erreur:
                self.messages.error(
                    "Erreur",
                    f"Impossible de supprimer le document.{erreur}"
                )
                return

            actualiser_liste()

            self.messages.info(
                "Document supprimé",
                f"Le document a été supprimé : {chemin_document.name}"
            )

        cadre_boutons = ttk.Frame(
            fenetre
        )

        cadre_boutons.pack(
            pady=10
        )

        self.icone_doc_ajouter = charger_icone("file-plus", 12)
        ttk.Button(
            cadre_boutons,
            text="Ajouter",
            image=self.icone_doc_ajouter,
            compound="left",
            command=ajouter_document_selectionne,
            bootstyle="secondary"
        ).pack(
            side="left",
            padx=5
        )

        self.icone_doc_visualiser = charger_icone("eye", 12)
        ttk.Button(
            cadre_boutons,
            text="Visualiser",
            image=self.icone_doc_visualiser,
            compound="left",
            command=visualiser_document_selectionne,
            bootstyle="info"
        ).pack(
            side="left",
            padx=5
        )

        self.icone_doc_imprimer = charger_icone("printer", 12)
        ttk.Button(
            cadre_boutons,
            text="Imprimer",
            image=self.icone_doc_imprimer,
            compound="left",
            command=imprimer_document_selectionne,
            bootstyle="primary",
        ).pack(
            side="left",
            padx=5,
        )

        self.icone_doc_renommer = charger_icone("pencil", 12)
        ttk.Button(
            cadre_boutons,
            text="Renommer",
            image=self.icone_doc_renommer,
            compound="left",
            command=renommer_document_selectionne,
            bootstyle="warning"
        ).pack(
            side="left",
            padx=5
        )

        self.icone_doc_supprimer = charger_icone("trash", 12)
        ttk.Button(
            cadre_boutons,
            text="Supprimer",
            image=self.icone_doc_supprimer,
            compound="left",
            command=supprimer_document_selectionne,
            bootstyle="danger"
        ).pack(
            side="left",
            padx=5
        )

        self.icone_doc_actualiser = charger_icone("rotate-ccw", 12)
        ttk.Button(
            cadre_boutons,
            text="Actualiser",
            image=self.icone_doc_actualiser,
            compound="left",
            command=actualiser_liste,
            bootstyle="info"
        ).pack(
            side="left",
            padx=5
        )

        self.icone_fermer = charger_icone("x", 12)

        ttk.Button(
            cadre_boutons,
            text="Fermer",
            image=self.icone_fermer,
            compound="left",
            command=fenetre.destroy,
            bootstyle="secondary"
        ).pack(
            side="left",
            padx=5
        )

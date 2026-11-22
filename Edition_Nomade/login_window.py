import tkinter as tk
import ttkbootstrap as ttk
from tkinter import messagebox

from utilisateur_manager import UtilisateurManager
from session_manager import SessionManager
from logger_manager import log_info, log_warning

from recuperation_mot_de_passe import RecuperationMotDePasseWindow


class LoginWindow:
    """
    Interface d'authentification de l'application.

    Responsabilités :
        - demander le code utilisateur ;
        - déterminer le profil ;
        - demander le mot de passe uniquement pour Administrateur ;
        - authentifier l'utilisateur ;
        - ouvrir la session après authentification réussie.
    """

    def __init__(self, parent, callback_succes, callback_fermeture=None):

        self.parent = parent
        self.callback_succes = callback_succes
        self.callback_fermeture = callback_fermeture

        self.authentification_en_cours = False

        self.fenetre = parent

        self.fenetre.geometry("420x260")
        self.fenetre.minsize(420, 285)
        self.fenetre.resizable(False, False)

        self.fenetre.protocol(
            "WM_DELETE_WINDOW",
            self.fermer
        )

        self._creer_interface()

        self.fenetre.update_idletasks()

        largeur = self.fenetre.winfo_width()
        hauteur = self.fenetre.winfo_height()

        x = (self.fenetre.winfo_screenwidth() - largeur) // 2
        y = (self.fenetre.winfo_screenheight() - hauteur) // 2

        self.fenetre.geometry(
            f"{largeur}x{hauteur}+{x}+{y}"
        )

        self.code.focus_set()

    # ==========================================
    # INTERFACE
    # ==========================================

    def _creer_interface(self):

        self.cadre = ttk.Frame(
            self.fenetre,
            padding=30
        )

        self.cadre.pack(
            fill="both",
            expand=True
        )

        # Colonne extensible
        self.cadre.columnconfigure(
            0,
            weight=1
        )

        # ------------------------------------------
        # TITRE
        # ------------------------------------------

        ttk.Label(
            self.cadre,
            text="Connexion",
            font=("Segoe UI", 18, "bold")
        ).grid(
            row=0,
            column=0,
            pady=(0, 25)
        )

        # ------------------------------------------
        # CODE UTILISATEUR
        # ------------------------------------------

        ttk.Label(
            self.cadre,
            text="Code utilisateur",
            font=("Segoe UI", 10)
        ).grid(
            row=1,
            column=0,
            sticky="w"
        )

        self.code = ttk.Entry(
            self.cadre,
            width=35
        )

        self.code.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(6, 20)
        )

        # ------------------------------------------
        # MOT DE PASSE
        # ------------------------------------------

        self.cadre_mot_de_passe = ttk.Frame(
            self.cadre
        )

        self.cadre_mot_de_passe.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(0, 20)
        )

        self.cadre_mot_de_passe.columnconfigure(
            0,
            weight=1
        )

        self.label_mot_de_passe = ttk.Label(
            self.cadre_mot_de_passe,
            text="Mot de passe",
            font=("Segoe UI", 10)
        )

        self.label_mot_de_passe.grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.mot_de_passe = ttk.Entry(
            self.cadre_mot_de_passe,
            width=35,
            show="*"
        )

        self.mot_de_passe.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(6, 0)
        )

        # ------------------------------------------
        # BOUTON CONNEXION
        # ------------------------------------------

        self.bouton_connexion = ttk.Button(
            self.cadre,
            text="Connexion",
            command=self.authentifier,
            bootstyle="primary"
        )

        self.bouton_connexion.grid(
            row=4,
            column=0,
            sticky="ew",
            pady=(28, 0)
        )

        # ------------------------------------------
        # MOT DE PASSE OUBLIÉ
        # ------------------------------------------

        self.bouton_mot_de_passe_oublie = ttk.Button(
            self.cadre,
            text="Mot de passe oublié ?",
            command=self.mot_de_passe_oublie,
            bootstyle="link"
        )

        self.bouton_mot_de_passe_oublie.grid(
            row=5,
            column=0,
            pady=(12, 0)
        )

        # Mot de passe masqué au démarrage
        self.cadre_mot_de_passe.grid_remove()

        # ------------------------------------------
        # TOUCHE ENTRÉE
        # ------------------------------------------

        self.fenetre.bind(
            "<Return>",
            lambda event: self.authentifier()
        )

    # ==========================================
    # AFFICHAGE MOT DE PASSE
    # ==========================================

    def afficher_mot_de_passe(self):

        if not self.cadre_mot_de_passe.winfo_ismapped():
            self.cadre_mot_de_passe.grid()

            self.fenetre.geometry("420x360")

            self.fenetre.update_idletasks()

            largeur = self.fenetre.winfo_width()
            hauteur = self.fenetre.winfo_height()

            x = (
                        self.fenetre.winfo_screenwidth()
                        - largeur
                ) // 2

            y = (
                        self.fenetre.winfo_screenheight()
                        - hauteur
                ) // 2

            self.fenetre.geometry(
                f"{largeur}x{hauteur}+{x}+{y}"
            )

    # ==========================================
    # MOT DE PASSE OUBLIÉ
    # ==========================================

    def mot_de_passe_oublie(self):

        RecuperationMotDePasseWindow(
            self.fenetre
        )

    # ==========================================
    # AUTHENTIFICATION
    # ==========================================

    def authentifier(self):

        if self.authentification_en_cours:
            return

        code = self.code.get().strip()

        if not code:
            messagebox.showwarning(
                "Connexion",
                "Veuillez saisir votre code utilisateur.",
                parent=self.fenetre
            )

            self.code.focus_set()

            return

        # ------------------------------------------
        # Recherche du compte
        # ------------------------------------------

        utilisateur = UtilisateurManager.trouver_par_code(
            code
        )

        if utilisateur is None:
            log_warning(
                "Échec connexion : code utilisateur inconnu ou compte inactif"
            )

            messagebox.showerror(
                "Connexion refusée",
                "Code utilisateur incorrect ou compte inactif.",
                parent=self.fenetre
            )

            self.code.focus_set()

            return

        # ------------------------------------------
        # Administrateur
        # ------------------------------------------

        if utilisateur["profil"] == "Administrateur":

            # Premier passage :
            # affichage du mot de passe.

            if not self.cadre_mot_de_passe.winfo_ismapped():
                self.afficher_mot_de_passe()

                self.mot_de_passe.focus_set()

                return

            mot_de_passe = self.mot_de_passe.get()

            if not mot_de_passe:
                messagebox.showwarning(
                    "Connexion",
                    "Veuillez saisir votre mot de passe.",
                    parent=self.fenetre
                )

                self.mot_de_passe.focus_set()

                return

            # Vérification réelle du mot de passe.

            utilisateur = UtilisateurManager.authentifier(
                code,
                mot_de_passe
            )

            if utilisateur is None:
                log_warning(
                    f"Échec connexion : mot de passe incorrect - code {code}"
                )

                messagebox.showerror(
                    "Connexion refusée",
                    "Mot de passe incorrect.",
                    parent=self.fenetre
                )

                self.mot_de_passe.delete(
                    0,
                    tk.END
                )

                self.mot_de_passe.focus_set()

                return

        # ------------------------------------------
        # Consultation / Modification
        # ------------------------------------------
        #
        # Ces profils sont authentifiés par leur code.

        # ------------------------------------------
        # Ouverture de la session
        # ------------------------------------------

        SessionManager.ouvrir(
            utilisateur
        )

        log_info(
            f"Connexion réussie : {code} - profil {utilisateur['profil']}"
        )

        self.authentification_en_cours = True
        self.bouton_connexion.configure(state="disabled")

        # ------------------------------------------
        # Lancement de l'application
        # ------------------------------------------

        self.callback_succes(
            utilisateur
        )

    # ==========================================
    # FERMETURE
    # ==========================================

    def fermer(self):

        SessionManager.fermer()

        if self.callback_fermeture:

            self.callback_fermeture()

        else:

            self.parent.destroy()
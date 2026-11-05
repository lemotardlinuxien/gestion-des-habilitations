import ttkbootstrap as ttk
from tkinter import messagebox

from utilisateur_manager import UtilisateurManager

from mail_manager import (
    ouvrir_smtp,
    fermer_smtp,
    envoyer_mail,
)


class RecuperationMotDePasseWindow:
    """
    Fenêtre de récupération du mot de passe.

    Responsabilités actuelles :
        - demander le code utilisateur ;
        - rechercher le compte ;
        - vérifier que le compte est actif ;
        - vérifier que le profil est Administrateur.

    La génération du token, l'envoi de l'e-mail et la
    réinitialisation du mot de passe seront ajoutés
    dans les étapes suivantes.
    """

    def __init__(self, parent):

        self.parent = parent

        self.fenetre = ttk.Toplevel(parent)

        self.fenetre.title(
            "Récupération du mot de passe"
        )

        self.fenetre.geometry("420x500")
        self.fenetre.minsize(420, 515)
        self.fenetre.resizable(False, False)

        self.fenetre.transient(parent)
        self.fenetre.grab_set()

        self.fenetre.protocol(
            "WM_DELETE_WINDOW",
            self.fermer
        )

        self._creer_interface()

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

        self.cadre.columnconfigure(
            0,
            weight=1
        )

        # ------------------------------------------
        # TITRE
        # ------------------------------------------

        ttk.Label(
            self.cadre,
            text="Récupération du mot de passe",
            font=("Segoe UI", 16, "bold")
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
            pady=(6, 25)
        )

        # ------------------------------------------
        # TOKEN DE RÉCUPÉRATION
        # ------------------------------------------

        ttk.Label(
            self.cadre,
            text="Token reçu par e-mail",
            font=("Segoe UI", 10)
        ).grid(
            row=3,
            column=0,
            sticky="w"
        )

        self.token = ttk.Entry(
            self.cadre,
            width=35
        )

        self.token.grid(
            row=4,
            column=0,
            sticky="ew",
            pady=(6, 25)
        )

        # ------------------------------------------
        # NOUVEAU MOT DE PASSE
        # ------------------------------------------

        ttk.Label(
            self.cadre,
            text="Nouveau mot de passe",
            font=("Segoe UI", 10)
        ).grid(
            row=5,
            column=0,
            sticky="w"
        )

        self.nouveau_mot_de_passe = ttk.Entry(
            self.cadre,
            width=35,
            show="*"
        )

        self.nouveau_mot_de_passe.grid(
            row=6,
            column=0,
            sticky="ew",
            pady=(6, 15)
        )

        # ------------------------------------------
        # CONFIRMATION DU MOT DE PASSE
        # ------------------------------------------

        ttk.Label(
            self.cadre,
            text="Confirmer le mot de passe",
            font=("Segoe UI", 10)
        ).grid(
            row=7,
            column=0,
            sticky="w"
        )

        self.confirmation_mot_de_passe = ttk.Entry(
            self.cadre,
            width=35,
            show="*"
        )

        self.confirmation_mot_de_passe.grid(
            row=8,
            column=0,
            sticky="ew",
            pady=(6, 25)
        )

        # ------------------------------------------
        # BOUTON CONTINUER
        # ------------------------------------------

        self.bouton_continuer = ttk.Button(
            self.cadre,
            text="Continuer",
            command=self.verifier_code,
            bootstyle="primary"
        )

        self.bouton_continuer.grid(
            row=9,
            column=0,
            sticky="ew"
        )

        # ------------------------------------------
        # BOUTON ANNULER
        # ------------------------------------------

        self.bouton_annuler = ttk.Button(
            self.cadre,
            text="Annuler",
            command=self.fermer,
            bootstyle="secondary"
        )

        self.bouton_annuler.grid(
            row=10,
            column=0,
            sticky="ew",
            pady=(12, 0)
        )

        # ------------------------------------------
        # TOUCHE ENTRÉE
        # ------------------------------------------

        self.fenetre.bind(
            "<Return>",
            lambda event: self.verifier_code()
        )

        # ------------------------------------------
        # TOUCHE ÉCHAP
        # ------------------------------------------

        self.fenetre.bind(
            "<Escape>",
            lambda event: self.fermer()
        )

    # ==========================================
    # VALIDATION DU CODE
    # ==========================================

    def verifier_code(self):

        code = self.code.get().strip()

        # ------------------------------------------
        # Code obligatoire
        # ------------------------------------------

        if not code:

            messagebox.showwarning(
                "Récupération du mot de passe",
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

        # ------------------------------------------
        # Compte inconnu ou inactif
        # ------------------------------------------

        if utilisateur is None:

            messagebox.showerror(
                "Récupération du mot de passe",
                "Compte utilisateur introuvable ou inactif.",
                parent=self.fenetre
            )

            self.code.focus_set()

            return

        # ------------------------------------------
        # Vérification du profil
        # ------------------------------------------

        if utilisateur["profil"] != "Administrateur":

            messagebox.showerror(
                "Récupération du mot de passe",
                "La récupération du mot de passe "
                "est réservée aux administrateurs.",
                parent=self.fenetre
            )

            self.code.focus_set()

            return

        # ------------------------------------------
        # Récupération de l'adresse e-mail
        # ------------------------------------------

        email = UtilisateurManager.recuperer_email(
            utilisateur["id"]
        )

        if not email:
            messagebox.showwarning(
                "Récupération du mot de passe",
                "Aucune adresse e-mail n'est associée "
                "à ce compte administrateur.",
                parent=self.fenetre
            )

            return

        # ------------------------------------------
        # Gestion du token
        # ------------------------------------------

        # ==========================================
        # ÉTAPE 1 : génération et envoi du token
        # ==========================================

        if not self.token.get().strip():

            try:

                token = UtilisateurManager.creer_token_recuperation(
                    utilisateur["id"]
                )

                self.token_recuperation = token

                smtp = None

                try:

                    smtp = ouvrir_smtp()

                    sujet = "Récupération de votre mot de passe"

                    message = (
                        "Bonjour,\n\n"
                        "Une demande de récupération de mot de passe "
                        "a été effectuée pour votre compte administrateur.\n\n"
                        "Votre code de récupération est :\n\n"
                        f"{token}\n\n"
                        "Ce code est valable pendant 30 minutes.\n\n"
                        "Si vous n'êtes pas à l'origine de cette demande, "
                        "vous pouvez ignorer ce message.\n\n"
                        "Cordialement,\n"
                        "Gestion des habilitations"
                    )

                    envoyer_mail(
                        smtp=smtp,
                        destinataire=email,
                        sujet=sujet,
                        message=message,
                    )

                finally:

                    if smtp is not None:
                        fermer_smtp(smtp)

                messagebox.showinfo(
                    "Récupération du mot de passe",
                    "Un token de récupération a été envoyé "
                    "à votre adresse e-mail.",
                    parent=self.fenetre
                )

                self.token.focus_set()

                return

            except ValueError as e:

                messagebox.showerror(
                    "Récupération du mot de passe",
                    str(e),
                    parent=self.fenetre
                )

                return

        # ==========================================
        # ÉTAPE 2 : vérification du token
        # ==========================================

        token = self.token.get().strip()

        try:

            resultat = UtilisateurManager.verifier_token_recuperation(
                utilisateur["id"],
                token
            )

        except ValueError as e:

            messagebox.showerror(
                "Récupération du mot de passe",
                str(e),
                parent=self.fenetre
            )

            self.token.focus_set()

            return

        # ==========================================
        # ÉTAPE 3 : nouveau mot de passe
        # ==========================================

        nouveau_mot_de_passe = (
            self.nouveau_mot_de_passe.get()
        )

        confirmation_mot_de_passe = (
            self.confirmation_mot_de_passe.get()
        )

        if not nouveau_mot_de_passe:
            messagebox.showwarning(
                "Récupération du mot de passe",
                "Veuillez saisir un nouveau mot de passe.",
                parent=self.fenetre
            )

            self.nouveau_mot_de_passe.focus_set()

            return

        if not confirmation_mot_de_passe:
            messagebox.showwarning(
                "Récupération du mot de passe",
                "Veuillez confirmer le nouveau mot de passe.",
                parent=self.fenetre
            )

            self.confirmation_mot_de_passe.focus_set()

            return

        if nouveau_mot_de_passe != confirmation_mot_de_passe:
            messagebox.showerror(
                "Récupération du mot de passe",
                "Les deux mots de passe ne correspondent pas.",
                parent=self.fenetre
            )

            self.confirmation_mot_de_passe.focus_set()

            return

        # ==========================================
        # ÉTAPE 4 : réinitialisation
        # ==========================================

        try:

            UtilisateurManager.reinitialiser_mot_de_passe(
                utilisateur["id"],
                token,
                nouveau_mot_de_passe
            )

            messagebox.showinfo(
                "Récupération du mot de passe",
                "Votre mot de passe a été réinitialisé avec succès.",
                parent=self.fenetre
            )

            self.fermer()

        except ValueError as e:

            messagebox.showerror(
                "Récupération du mot de passe",
                str(e),
                parent=self.fenetre
            )

    # ==========================================
    # FERMETURE
    # ==========================================

    def fermer(self):

        try:
            self.fenetre.grab_release()
        except Exception:
            pass

        self.fenetre.destroy()
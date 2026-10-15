import ttkbootstrap as ttk
from tkinter import messagebox

from utilisateur_manager import UtilisateurManager


class PremierAdministrateurWindow:

    def __init__(self, parent, callback_succes, callback_fermeture):
        self.parent = parent
        self.callback_succes = callback_succes
        self.callback_fermeture = callback_fermeture

        self.fenetre = ttk.Toplevel(parent)
        self.fenetre.title("Création du premier administrateur")
        self.fenetre.geometry("500x500")
        self.fenetre.resizable(False, False)
        self.fenetre.transient(parent)
        self.fenetre.grab_set()

        self.creer_interface()

        self.fenetre.protocol(
            "WM_DELETE_WINDOW",
            self.fermer
        )

        self.centrer_fenetre()

        self.fenetre.deiconify()
        self.fenetre.lift()

        self.fenetre.attributes("-topmost", True)

        self.fenetre.after(
            100,
            lambda: self.fenetre.attributes("-topmost", False)
        )

        self.fenetre.focus_force()

    def creer_interface(self):

        ttk.Label(
            self.fenetre,
            text="Création du premier administrateur",
            font=("Segoe UI", 14, "bold")
        ).pack(pady=15)

        ttk.Label(
            self.fenetre,
            text=(
                "Aucun administrateur n'existe encore.\n"
                "Créez le premier compte administrateur."
            ),
            justify="center"
        ).pack(pady=(0, 15))

        cadre = ttk.Frame(self.fenetre)
        cadre.pack(
            padx=30,
            pady=10,
            fill="x"
        )

        self.code_var = ttk.StringVar()
        self.nom_var = ttk.StringVar()
        self.prenom_var = ttk.StringVar()
        self.mot_de_passe_var = ttk.StringVar()
        self.confirmation_var = ttk.StringVar()

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
            textvariable=self.code_var,
            width=30
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            pady=8
        )

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
            textvariable=self.nom_var,
            width=30
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            pady=8
        )

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
            textvariable=self.prenom_var,
            width=30
        ).grid(
            row=2,
            column=1,
            sticky="ew",
            pady=8
        )

        ttk.Label(
            cadre,
            text="Mot de passe :"
        ).grid(
            row=3,
            column=0,
            sticky="w",
            pady=8
        )

        ttk.Entry(
            cadre,
            textvariable=self.mot_de_passe_var,
            show="*",
            width=30
        ).grid(
            row=3,
            column=1,
            sticky="ew",
            pady=8
        )

        ttk.Label(
            cadre,
            text="Confirmation :"
        ).grid(
            row=4,
            column=0,
            sticky="w",
            pady=8
        )

        ttk.Entry(
            cadre,
            textvariable=self.confirmation_var,
            show="*",
            width=30
        ).grid(
            row=4,
            column=1,
            sticky="ew",
            pady=8
        )

        cadre_boutons = ttk.Frame(self.fenetre)
        cadre_boutons.pack(pady=20)

        ttk.Button(
            cadre_boutons,
            text="Créer le compte",
            command=self.enregistrer,
            bootstyle="success"
        ).pack(
            side="left",
            padx=5
        )

        ttk.Button(
            cadre_boutons,
            text="Annuler",
            command=self.fermer,
            bootstyle="danger"
        ).pack(
            side="left",
            padx=5
        )

    def enregistrer(self):

        code = self.code_var.get().strip()
        nom = self.nom_var.get().strip()
        prenom = self.prenom_var.get().strip()
        mot_de_passe = self.mot_de_passe_var.get()
        confirmation = self.confirmation_var.get()

        if not mot_de_passe:
            messagebox.showwarning(
                "Création impossible",
                "Le mot de passe est obligatoire.",
                parent=self.fenetre
            )
            return

        if mot_de_passe != confirmation:
            messagebox.showwarning(
                "Création impossible",
                "Les deux mots de passe ne correspondent pas.",
                parent=self.fenetre
            )
            return

        try:
            UtilisateurManager.creer_utilisateur(
                code=code,
                nom=nom,
                prenom=prenom,
                profil="Administrateur",
                mot_de_passe=mot_de_passe
            )

        except ValueError as erreur:
            messagebox.showwarning(
                "Création impossible",
                str(erreur),
                parent=self.fenetre
            )
            return

        except Exception:
            messagebox.showerror(
                "Erreur",
                (
                    "Une erreur est survenue "
                    "lors de la création du compte."
                ),
                parent=self.fenetre
            )
            return

        messagebox.showinfo(
            "Compte créé",
            (
                f"Le compte « {code} » "
                "a été créé avec succès."
            ),
            parent=self.fenetre
        )

        # --------------------------------------
        # Fermeture de la fenêtre
        # --------------------------------------

        self.fenetre.grab_release()
        self.fenetre.destroy()

        # --------------------------------------
        # Affichage de la connexion
        # --------------------------------------

        self.callback_succes()

    def fermer(self):

        if self.callback_fermeture:
            self.callback_fermeture()
        else:
            self.fenetre.destroy()

    def centrer_fenetre(self):

        largeur = 500
        hauteur = 500

        largeur_ecran = self.fenetre.winfo_screenwidth()
        hauteur_ecran = self.fenetre.winfo_screenheight()

        x = (largeur_ecran - largeur) // 2
        y = (hauteur_ecran - hauteur) // 2

        self.fenetre.geometry(
            f"{largeur}x{hauteur}+{x}+{y}"
        )
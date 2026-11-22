import ttkbootstrap as ttk
from tkinter import filedialog, messagebox
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

from config import DB
from utilisateur_manager import UtilisateurManager
from app_settings_manager import enregistrer_parametre


class PremierAdministrateurWindow:

    def __init__(self, parent, callback_succes, callback_fermeture, mode_recuperation=False):
        self.parent = parent
        self.callback_succes = callback_succes
        self.callback_fermeture = callback_fermeture
        self.mode_recuperation = mode_recuperation

        self.fenetre = ttk.Toplevel(parent)
        self.fenetre.title(
            "Restauration de la base de données"
            if self.mode_recuperation
            else "Création du premier administrateur"
        )
        self.fenetre.geometry("500x270" if self.mode_recuperation else "500x590")
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
            text=(
                "Restauration de la base de données"
                if self.mode_recuperation
                else "Création du premier administrateur"
            ),
            font=("Segoe UI", 14, "bold")
        ).pack(pady=15)

        ttk.Label(
            self.fenetre,
            text=(
                "La base de données locale est inutilisable.\n"
                "Importez une sauvegarde pour retrouver vos données."
                if self.mode_recuperation
                else "Aucun administrateur n'existe encore.\n"
                     "Créez le premier compte administrateur."
            ),
            justify="center"
        ).pack(pady=(0, 15))

        if not self.mode_recuperation:
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
            self.nom_entreprise_var = ttk.StringVar()

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

            ttk.Label(
                cadre,
                text="Entreprise / Organisation :"
            ).grid(
                row=5,
                column=0,
                sticky="w",
                pady=8
            )

            ttk.Entry(
                cadre,
                textvariable=self.nom_entreprise_var,
                width=30
            ).grid(
                row=5,
                column=1,
                sticky="ew",
                pady=8
            )

        cadre_boutons = ttk.Frame(self.fenetre)
        cadre_boutons.pack(pady=20)

        if not self.mode_recuperation:
            ttk.Button(
                cadre_boutons,
                text="Créer le compte",
                command=self.enregistrer,
                bootstyle="success"
            ).pack(side="left", padx=5)

        ttk.Button(
            cadre_boutons,
            text="Annuler",
            command=self.fermer,
            bootstyle="danger"
        ).pack(
            side="left",
            padx=5
        )

        ttk.Separator(self.fenetre, orient="horizontal").pack(
            fill="x", padx=45, pady=(5, 12)
        )

        ttk.Button(
            self.fenetre,
            text="Importer une base",
            command=self.selectionner_base,
            bootstyle="secondary-outline"
        ).pack(pady=(0, 10))

    def selectionner_base(self):
        """Sélectionne, vérifie et restaure une sauvegarde SQLite."""

        fichier = filedialog.askopenfilename(
            parent=self.fenetre,
            title="Sélectionner une sauvegarde de base de données",
            filetypes=[
                ("Bases SQLite", "*.db"),
                ("Tous les fichiers", "*.*"),
            ],
        )

        if not fichier:
            return

        fichier_source = Path(fichier).resolve()
        fichier_destination = Path(DB).resolve()

        confirmation = messagebox.askyesno(
            "Confirmer l'importation",
            "Vous allez importer une sauvegarde de la base de données.\n\n"
            "Cette opération est destinée à restaurer les données de l'application.\n\n"
            "Voulez-vous continuer ?",
            parent=self.fenetre,
        )

        if not confirmation:
            return

        fichier_temporaire = None

        try:
            # Vérification préalable de la sauvegarde, sans la modifier.
            # Important : le gestionnaire de contexte SQLite ne ferme pas
            # automatiquement la connexion à sa sortie. On la ferme donc
            # explicitement pour éviter tout verrouillage sous Windows.
            conn = sqlite3.connect(
                f"{fichier_source.as_uri()}?mode=ro",
                uri=True,
            )
            try:
                resultat = conn.execute("PRAGMA quick_check").fetchone()
                if not resultat or resultat[0] != "ok":
                    raise ValueError("La vérification d'intégrité SQLite a échoué.")

                tables = {
                    ligne[0]
                    for ligne in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }

                if "utilisateurs" not in tables:
                    raise ValueError(
                        "Cette sauvegarde ne contient pas la table des utilisateurs."
                    )

                colonnes = {
                    ligne[1]
                    for ligne in conn.execute(
                        "PRAGMA table_info(utilisateurs)"
                    ).fetchall()
                }

                colonnes_requises = {"code", "profil", "actif"}
                if not colonnes_requises.issubset(colonnes):
                    raise ValueError(
                        "La structure de la table des utilisateurs est incompatible."
                    )

                administrateurs = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM utilisateurs
                    WHERE LOWER(profil) = 'administrateur'
                      AND actif = 1
                    """
                ).fetchone()[0]

                if administrateurs == 0:
                    raise ValueError(
                        "La sauvegarde ne contient aucun administrateur actif."
                    )
            finally:
                conn.close()

            # Préparation d'une copie temporaire dans le même dossier que DB.
            fichier_destination.parent.mkdir(parents=True, exist_ok=True)
            descripteur, chemin_temporaire = tempfile.mkstemp(
                prefix="habilitation_import_",
                suffix=".db",
                dir=fichier_destination.parent,
            )
            os.close(descripteur)
            fichier_temporaire = Path(chemin_temporaire)
            shutil.copy2(fichier_source, fichier_temporaire)

            # Vérification de la copie avant le remplacement de la base active.
            # La connexion doit impérativement être fermée avant os.replace(),
            # car Windows interdit de renommer un fichier SQLite encore ouvert.
            conn = sqlite3.connect(
                f"{fichier_temporaire.as_uri()}?mode=ro",
                uri=True,
            )
            try:
                resultat = conn.execute("PRAGMA quick_check").fetchone()
                if not resultat or resultat[0] != "ok":
                    raise ValueError(
                        "La copie temporaire de la sauvegarde est invalide."
                    )
            finally:
                conn.close()

            # À ce stade, aucune connexion applicative n'est encore ouverte.
            # On retire d'éventuels fichiers WAL de la base vide initialisée au démarrage.
            for suffixe in ("-wal", "-shm"):
                fichier_annexe = Path(str(fichier_destination) + suffixe)
                if fichier_annexe.exists():
                    fichier_annexe.unlink()

            # Remplacement atomique : la base active n'est changée qu'après validation.
            os.replace(fichier_temporaire, fichier_destination)
            fichier_temporaire = None

        except (sqlite3.Error, OSError, ValueError) as erreur:
            messagebox.showerror(
                "Importation impossible",
                f"La sauvegarde n'a pas pu être importée.\n\n{erreur}",
                parent=self.fenetre,
            )
            return

        finally:
            if fichier_temporaire is not None:
                try:
                    fichier_temporaire.unlink(missing_ok=True)
                except OSError:
                    pass

        messagebox.showinfo(
            "Importation réussie",
            "La base de données a été restaurée.\n\n"
            "Vous allez maintenant être redirigé vers la connexion.",
            parent=self.fenetre,
        )

        self.fenetre.grab_release()
        self.fenetre.destroy()
        self.callback_succes()

    def enregistrer(self):

        if self.mode_recuperation:
            return

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

        try:
            enregistrer_parametre(
                "nom_entreprise",
                self.nom_entreprise_var.get()
            )
        except Exception as erreur:
            messagebox.showerror(
                "Paramétrage impossible",
                "Le compte a été créé, mais le nom de l'entreprise "
                "n'a pas pu être enregistré. Vous pourrez le renseigner "
                f"ultérieurement.\\n\\nDétail : {erreur}",
                parent=self.fenetre
            )

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
        hauteur = 590

        largeur_ecran = self.fenetre.winfo_screenwidth()
        hauteur_ecran = self.fenetre.winfo_screenheight()

        x = (largeur_ecran - largeur) // 2
        y = (hauteur_ecran - hauteur) // 2

        self.fenetre.geometry(
            f"{largeur}x{hauteur}+{x}+{y}"
        )
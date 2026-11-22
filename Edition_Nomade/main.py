import sqlite3
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk

# Charger la configuration nomade avant les modules qui utilisent les données.
try:
    import config
except OSError as erreur:
    fenetre_erreur = tk.Tk()
    fenetre_erreur.withdraw()
    messagebox.showerror(
        "Dossier de données inaccessible",
        "L'application ne peut pas accéder au dossier Donnees situé "
        "à côté de son exécutable.\\n\\n"
        "Vérifiez que le support est connecté et que vous disposez des "
        "droits de lecture et d'écriture.\\n\\n"
        f"Détail : {erreur}",
        parent=fenetre_erreur,
    )
    fenetre_erreur.destroy()
    raise SystemExit(1)

from config import (
    DB,
    FICHIER_MARQUEUR_INSTALLATION,
    marquer_installation_initialisee,
)
from database import initialiser_tables_systeme
from gui import GestionHabilitationsApp
from login_window import LoginWindow
from premier_administrateur_window import PremierAdministrateurWindow
from session_manager import SessionManager
from utilisateur_manager import UtilisateurManager
from logger_manager import log_info
from database_monitor import database_monitor
from backup_manager import (
    creer_sauvegarde_automatique,
    envoyer_sauvegarde_aux_administrateurs,
)


def lancer_application(utilisateur):
    """
    Lance l'application principale après authentification.
    """

    root.withdraw()

    for widget in root.winfo_children():
        widget.destroy()

    root.title("Gestion des habilitations")
    root.resizable(True, True)
    root.minsize(970, 1020)

    app = GestionHabilitationsApp(root)

    database_monitor.demarrer()

    root.protocol(
        "WM_DELETE_WINDOW",
        fermer_application
    )

    root.update_idletasks()

    try:
        root.state("zoomed")
    except:
        root.attributes("-zoomed", True)

    root.update_idletasks()

    root.deiconify()
    root.update()

    app.verifier_alertes()


def initialiser_application(dialog):
    """
    Initialise l'application principale après
    affichage de la fenêtre de chargement.
    """

    try:
        GestionHabilitationsApp(root)

        root.protocol(
            "WM_DELETE_WINDOW",
            fermer_application
        )

        root.update_idletasks()

        try:
            root.state("zoomed")
        except:
            root.attributes("-zoomed", True)

        root.update_idletasks()

    finally:
        dialog.fermer()


def fermer_application():
    """Ferme l'application et sauvegarde la base si nécessaire."""

    try:
        # Vérification uniquement si la surveillance est démarrée.
        if database_monitor.connexion is not None:

            if database_monitor.base_modifiee():

                log_info(
                    "Modification de la base détectée. "
                    "Création d'une sauvegarde automatique."
                )

                fichier_sauvegarde = creer_sauvegarde_automatique()

                envoyer_sauvegarde_aux_administrateurs(
                    fichier_sauvegarde
                )

            else:
                log_info(
                    "Aucune modification de la base. "
                    "Pas de sauvegarde automatique nécessaire."
                )

    except Exception as erreur:
        log_info(
            f"Erreur lors de la sauvegarde automatique : {erreur}"
        )

    finally:
        try:
            if SessionManager.est_connecte():
                log_info(
                    f"Déconnexion : {SessionManager.code()} - "
                    f"profil {SessionManager.profil()}"
                )
                SessionManager.fermer()

        finally:
            try:
                database_monitor.fermer()

            finally:
                root.destroy()



log_info("===== Démarrage de l'application =====")

root = ttk.Window(
    title="Connexion",
    themename="superhero"
)

# Icône de la fenêtre : PNG compatible Linux/Windows.
try:
    chemin_icone = Path(__file__).resolve().parent / "icons" / "app.png"
    if chemin_icone.exists():
        root._icone_application = tk.PhotoImage(file=str(chemin_icone))
        root.iconphoto(True, root._icone_application)
except Exception as erreur:
    # L'icône reste décorative : son absence ne bloque pas le démarrage.
    print(f"Icône de fenêtre indisponible : {erreur}")

# ==========================================
# CONTRÔLE ET INITIALISATION DE LA BASE SQLITE
# ==========================================

def base_sqlite_exploitable(chemin):
    """Vérifie en lecture seule que le fichier est une base SQLite intègre."""

    try:
        uri = f"{chemin.resolve().as_uri()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        try:
            resultat = conn.execute("PRAGMA quick_check").fetchone()
            if not resultat or resultat[0] != "ok":
                return False

            # Si la table utilisateurs existe, sa structure doit au moins
            # permettre le contrôle des comptes administrateurs.
            table = conn.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type = 'table' AND name = 'utilisateurs'"
            ).fetchone()

            if table:
                colonnes = {
                    ligne[1]
                    for ligne in conn.execute(
                        "PRAGMA table_info(utilisateurs)"
                    ).fetchall()
                }
                if not {"profil", "actif"}.issubset(colonnes):
                    return False

            return True
        finally:
            conn.close()

    except (sqlite3.Error, OSError, ValueError):
        return False


def afficher_connexion():
    """Applique les migrations après restauration, puis affiche la connexion."""
    try:
        initialiser_tables_systeme()
        marquer_installation_initialisee()
    except Exception as erreur:
        log_info(f"Erreur après restauration de la base : {erreur}")
        messagebox.showerror(
            "Initialisation impossible",
            "La sauvegarde a été importée, mais la base n'a pas pu être "
            "initialisée par cette version de l'application.\n\n"
            f"Détail : {erreur}",
            parent=root,
        )
        return

    root.deiconify()
    LoginWindow(
        root,
        callback_succes=lancer_application,
        callback_fermeture=fermer_application
    )


def afficher_creation_premier_administrateur(mode_recuperation=False):
    PremierAdministrateurWindow(
        root,
        callback_succes=afficher_connexion,
        callback_fermeture=fermer_application,
        mode_recuperation=mode_recuperation,
    )


base_existe = DB.exists()
installation_deja_initialisee = FICHIER_MARQUEUR_INSTALLATION.exists()
base_invalide = False

if installation_deja_initialisee and not base_existe:
    # Une installation déjà utilisée a perdu sa base : ne pas en créer une vide.
    base_invalide = True
    log_info(
        "Marqueur d'installation présent mais base locale absente. "
        "Démarrage en mode récupération."
    )

elif base_existe:
    if not base_sqlite_exploitable(DB):
        base_invalide = True
        log_info(
            "Base de données locale détectée mais invalide ou inaccessible. "
            "Aucune initialisation ne sera effectuée."
        )
    else:
        try:
            initialiser_tables_systeme()
            if not installation_deja_initialisee:
                marquer_installation_initialisee()
        except Exception as erreur:
            base_invalide = True
            log_info(f"Échec de l'initialisation de la base existante : {erreur}")

else:
    # Première utilisation : initialisation identique à la V55.
    try:
        initialiser_tables_systeme()
        marquer_installation_initialisee()
    except Exception as erreur:
        messagebox.showerror(
            "Initialisation impossible",
            "La base de données n'a pas pu être créée dans le dossier "
            "Donnees. Vérifiez les droits d'écriture du support.\\n\\n"
            f"Détail : {erreur}",
            parent=root,
        )
        root.destroy()
        raise SystemExit(1)

if base_invalide:
    messagebox.showwarning(
        "Base de données inutilisable",
        "La base de données locale est absente, inaccessible ou "
        "inutilisable.\\n\\n"
        "Vous pouvez restaurer vos données à partir d'une sauvegarde.",
        parent=root,
    )
    afficher_creation_premier_administrateur(mode_recuperation=True)

elif UtilisateurManager.administrateur_existe():
    LoginWindow(
        root,
        callback_succes=lancer_application,
        callback_fermeture=fermer_application
    )
else:
    afficher_creation_premier_administrateur()

root.mainloop()

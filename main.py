import ttkbootstrap as ttk
from database import initialiser_tables_systeme
from gui import GestionHabilitationsApp
from login_window import LoginWindow
from premier_administrateur_window import PremierAdministrateurWindow
from session_manager import SessionManager
from utilisateur_manager import UtilisateurManager
from logger_manager import log_info

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
    """Ferme complètement l'application."""

    if SessionManager.est_connecte():
        log_info(
            f"Déconnexion : {SessionManager.code()} - "
            f"profil {SessionManager.profil()}"
        )
        SessionManager.fermer()

    root.destroy()


log_info("===== Démarrage de l'application =====")

root = ttk.Window(
    title="Connexion",
    themename="superhero"
)

# ==========================================
# INITIALISATION DE LA STRUCTURE SQLITE
# ==========================================

initialiser_tables_systeme()

def afficher_connexion():
    root.deiconify()

    LoginWindow(
        root,
        callback_succes=lancer_application,
        callback_fermeture=fermer_application
    )

if UtilisateurManager.administrateur_existe():

    LoginWindow(
        root,
        callback_succes=lancer_application,
        callback_fermeture=fermer_application
    )

else:

    PremierAdministrateurWindow(
        root,
        callback_succes=afficher_connexion,
        callback_fermeture=fermer_application
    )

root.mainloop()

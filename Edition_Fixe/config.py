from pathlib import Path
import os
import sys

VERSION = "V57"
APP_NAME = "GestionHabilitations"

# ==================================================
# RESSOURCES DE L'APPLICATION
# ==================================================
# Les ressources (code, icônes...) peuvent être embarquées
# dans le dossier interne de PyInstaller. Elles ne servent
# pas à stocker les données modifiables de l'utilisateur.

if getattr(sys, "frozen", False):
    RESOURCE_DIR = Path(
        getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)
    )
else:
    RESOURCE_DIR = Path(__file__).resolve().parent

# Alias conservé pour compatibilité avec les modules existants.
BASE_DIR = RESOURCE_DIR


# ==================================================
# DOSSIER DE DONNÉES FIXE (NON NOMADE)
# ==================================================
def _determiner_dossier_donnees():
    """
    Retourne le dossier utilisateur permanent de l'application.

    Windows : %LOCALAPPDATA%/GestionHabilitations
    Linux   : $XDG_DATA_HOME/GestionHabilitations,
              ou ~/.local/share/GestionHabilitations
    macOS   : ~/Library/Application Support/GestionHabilitations
    """

    if sys.platform.startswith("win"):
        racine = os.environ.get("LOCALAPPDATA")
        if racine:
            return Path(racine) / APP_NAME
        return Path.home() / "AppData" / "Local" / APP_NAME

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME

    racine = os.environ.get("XDG_DATA_HOME")
    if racine:
        return Path(racine).expanduser() / APP_NAME

    return Path.home() / ".local" / "share" / APP_NAME


DATA_DIR = _determiner_dossier_donnees()

# Le marqueur accompagne les données, pas le programme.
# Il détecte une base disparue après une installation déjà utilisée.
FICHIER_MARQUEUR_INSTALLATION = DATA_DIR / ".installation_initialisee"

DOSSIERS_DONNEES = (
    DATA_DIR / "database",
    DATA_DIR / "sauvegardes",
    DATA_DIR / "pdf",
    DATA_DIR / "exports",
    DATA_DIR / "salariés",
    DATA_DIR / "logs",
    DATA_DIR / "graphiques",
)


def initialiser_repertoires_donnees():
    """
    Prépare les répertoires de données fixes.
    Ne déplace, ne supprime et ne remplace aucune donnée existante.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for dossier in DOSSIERS_DONNEES:
        dossier.mkdir(parents=True, exist_ok=True)


def marquer_installation_initialisee():
    """Marque l'installation après initialisation réussie de la base."""
    temporaire = FICHIER_MARQUEUR_INSTALLATION.with_name(
        FICHIER_MARQUEUR_INSTALLATION.name + ".tmp"
    )
    temporaire.write_text(
        f"{APP_NAME} - {VERSION}\n",
        encoding="utf-8"
    )
    temporaire.replace(FICHIER_MARQUEUR_INSTALLATION)


# Les dossiers sont préparés dès le démarrage.
# Une erreur remonte à main.py pour être affichée proprement.
initialiser_repertoires_donnees()

FICHIER_EXCEL = str(DATA_DIR / "habilitations.xlsx")
COLONNES_TECHNIQUES = ["ID", "Secteur", "Nom", "Prénom"]

DOSSIER_SAUVEGARDES = str(DATA_DIR / "sauvegardes")
DOSSIER_PDF = str(DATA_DIR / "pdf")
DOSSIER_EXPORTS = str(DATA_DIR / "exports")
DOSSIER_SALARIES = str(DATA_DIR / "salariés")
DOSSIER_LOGS = DATA_DIR / "logs"
DOSSIER_GRAPHIQUES = str(DATA_DIR / "graphiques")

DB = DATA_DIR / "database" / "habilitations.db"

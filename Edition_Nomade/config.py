from pathlib import Path
import sys

VERSION = "V58_Nomade"
APP_NAME = "GestionHabilitations"

# Ressources embarquées et dossier contenant l'exécutable.
if getattr(sys, "frozen", False):
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    APP_DIR = Path(sys.executable).resolve().parent
else:
    RESOURCE_DIR = Path(__file__).resolve().parent
    APP_DIR = RESOURCE_DIR

# Alias conservé pour compatibilité avec les modules existants.
BASE_DIR = RESOURCE_DIR

# En mode nomade, toutes les données résident à côté de l'application.
DATA_DIR = APP_DIR / "Donnees"
FICHIER_MARQUEUR_INSTALLATION = APP_DIR / ".installation_initialisee"

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
    """Crée l'arborescence nomade sans déplacer ni supprimer de données."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for dossier in DOSSIERS_DONNEES:
        dossier.mkdir(parents=True, exist_ok=True)


def marquer_installation_initialisee():
    """Marque l'installation après initialisation réussie de la base."""
    temporaire = FICHIER_MARQUEUR_INSTALLATION.with_name(
        FICHIER_MARQUEUR_INSTALLATION.name + ".tmp"
    )
    temporaire.write_text(f"{APP_NAME} - {VERSION}\\n", encoding="utf-8")
    temporaire.replace(FICHIER_MARQUEUR_INSTALLATION)


# Comme en V55, les dossiers sont prêts dès le démarrage.
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

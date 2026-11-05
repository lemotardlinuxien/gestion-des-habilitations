from pathlib import Path
import os
import shutil
import sys


# ==========================================
# VERSION APPLICATION
# ==========================================

VERSION = "V54"
APP_NAME = "GestionHabilitations"


# ==========================================
# RESSOURCES DE L'APPLICATION
# ==========================================

# En mode PyInstaller, les ressources embarquées (icônes, etc.) peuvent se
# trouver dans le répertoire temporaire _MEIPASS. Elles ne doivent jamais
# servir de répertoire de données persistantes.
if getattr(sys, "frozen", False):
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    APP_DIR = Path(sys.executable).resolve().parent
else:
    RESOURCE_DIR = Path(__file__).resolve().parent
    APP_DIR = RESOURCE_DIR

# Alias conservé pour compatibilité avec d'éventuels modules existants.
BASE_DIR = RESOURCE_DIR


# ==========================================
# RÉPERTOIRE DES DONNÉES PERSISTANTES
# ==========================================

def _repertoire_donnees_utilisateur():
    """Retourne un emplacement persistant et inscriptible selon le système."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / APP_NAME
        return Path.home() / "AppData" / "Local" / APP_NAME

    base = os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


DATA_DIR = _repertoire_donnees_utilisateur()


# ==========================================
# MIGRATION PRUDENTE DES ANCIENNES DONNÉES
# ==========================================

def _copier_si_absent(source: Path, destination: Path) -> None:
    """Copie les anciennes données uniquement si la destination n'existe pas.

    Les fichiers sources ne sont jamais supprimés ni remplacés.
    """
    if not source.exists() or destination.exists():
        return

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination)
        elif source.is_file():
            shutil.copy2(source, destination)
    except OSError:
        # Une migration qui échoue ne doit pas supprimer les données sources.
        # L'erreur pourra être diagnostiquée et la copie faite manuellement.
        return


def _migrer_anciennes_donnees() -> None:
    """Récupère les données de l'ancienne installation sans les déplacer.

    Les dossiers ne sont copiés que si leur équivalent dans DATA_DIR n'existe
    pas encore. Les originaux restent en place pour permettre un retour arrière.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    anciens_emplacements = []
    for emplacement in (APP_DIR, RESOURCE_DIR):
        emplacement = Path(emplacement).resolve()
        if emplacement != DATA_DIR.resolve() and emplacement not in anciens_emplacements:
            anciens_emplacements.append(emplacement)

    elements = (
        (Path("habilitations.xlsx"), Path("habilitations.xlsx")),
        (Path("database"), Path("database")),
        (Path("sauvegardes"), Path("sauvegardes")),
        (Path("pdf"), Path("pdf")),
        (Path("exports"), Path("exports")),
        (Path("salariés"), Path("salariés")),
        (Path("logs"), Path("logs")),
        (Path("graphiques"), Path("graphiques")),
    )

    for ancien_racine in anciens_emplacements:
        for ancien_rel, nouveau_rel in elements:
            _copier_si_absent(
                ancien_racine / ancien_rel,
                DATA_DIR / nouveau_rel,
            )


_migrer_anciennes_donnees()


# ==========================================
# FICHIERS ET DOSSIERS DE DONNÉES
# ==========================================

FICHIER_EXCEL = str(DATA_DIR / "habilitations.xlsx")

COLONNES_TECHNIQUES = [
    "ID",
    "Secteur",
    "Nom",
    "Prénom",
]

DOSSIER_SAUVEGARDES = str(DATA_DIR / "sauvegardes")
DOSSIER_PDF = str(DATA_DIR / "pdf")
DOSSIER_EXPORTS = str(DATA_DIR / "exports")
DOSSIER_SALARIES = str(DATA_DIR / "salariés")
DOSSIER_LOGS = DATA_DIR / "logs"
DOSSIER_GRAPHIQUES = str(DATA_DIR / "graphiques")

for dossier in (
    Path(DOSSIER_SAUVEGARDES),
    Path(DOSSIER_PDF),
    Path(DOSSIER_EXPORTS),
    Path(DOSSIER_SALARIES),
    DOSSIER_LOGS,
    Path(DOSSIER_GRAPHIQUES),
):
    dossier.mkdir(parents=True, exist_ok=True)


# ==========================================
# BASE DE DONNÉES SQLITE
# ==========================================

DB = DATA_DIR / "database" / "habilitations.db"
DB.parent.mkdir(parents=True, exist_ok=True)

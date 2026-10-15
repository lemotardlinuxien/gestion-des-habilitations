import logging
from pathlib import Path
from config import DOSSIER_LOGS

# Les journaux sont stockés avec les données utilisateur, pas à côté du code.
DOSSIER_LOGS = Path(DOSSIER_LOGS)
DOSSIER_LOGS.mkdir(parents=True, exist_ok=True)
FICHIER_LOG = DOSSIER_LOGS / "application.log"

logging.basicConfig(
    filename=FICHIER_LOG,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    encoding="utf-8",
)


def log_info(message):
    logging.info(message)


def log_warning(message):
    logging.warning(message)


def log_error(message):
    logging.error(message)


def log_critical(message):
    logging.critical(message)

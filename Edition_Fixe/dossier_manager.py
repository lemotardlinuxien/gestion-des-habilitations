from pathlib import Path
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

# Le glisser-déposer depuis l’Explorateur nécessite tkinterdnd2.
# L’application reste utilisable avec le sélecteur classique si le module manque.
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    DND_FILES = None
    TkinterDnD = None
from io import BytesIO

from config import DOSSIER_SALARIES

import os
import platform
import subprocess


def creer_dossier_salarie(
        nom,
        prenom,
        id_salarie
):
    """
    Crée le dossier individuel d'un salarié.

    Le dossier est identifié par :
    Nom + Prénom + ID salarié.
    """

    nom = str(nom).strip()
    prenom = str(prenom).strip()
    id_salarie = str(id_salarie).strip()

    nom_dossier = (
        f"{nom}_{prenom}_{id_salarie[:8]}"
    )

    chemin = Path(
        DOSSIER_SALARIES
    ) / nom_dossier

    chemin.mkdir(
        parents=True,
        exist_ok=True
    )

    return chemin

def selectionner_document():
    """Ouvre le sélecteur de fichiers."""

    fichier_source = filedialog.askopenfilename(
        title="Sélectionner un document"
    )

    if not fichier_source:
        return None

    return Path(fichier_source)



def selectionner_documents_ordonnes(parent=None):
    """Compatibilité : délègue la sélection à PDFManager."""
    from pdf_manager import PDFManager
    return PDFManager.selectionner_documents_ordonnes(parent=parent)



def copier_document(
        nom,
        prenom,
        id_salarie,
        fichier_source,
        remplacer=False
):
    """Copie un document dans le dossier individuel du salarié."""

    nom = str(nom).strip()
    prenom = str(prenom).strip()
    id_salarie = str(id_salarie).strip()

    fichier_source = Path(
        fichier_source
    )

    if not fichier_source.is_file():
        raise FileNotFoundError(
            "Le document source est introuvable."
        )

    nom_dossier = (
        f"{nom}_{prenom}_{id_salarie[:8]}"
    )

    dossier = (
        Path(DOSSIER_SALARIES)
        / nom_dossier
    )

    dossier.mkdir(
        parents=True,
        exist_ok=True
    )

    fichier_destination = (
        dossier / fichier_source.name
    )

    if fichier_destination.exists():

        if not remplacer:
            raise FileExistsError(
                "Un document portant déjà ce nom existe."
            )

        if (
            fichier_source.resolve()
            == fichier_destination.resolve()
        ):
            return fichier_destination

    shutil.copy2(
        fichier_source,
        fichier_destination
    )

    return fichier_destination


def convertir_et_fusionner_documents(nom, prenom, id_salarie, parent=None):
    """Compatibilité : délègue la création du PDF à PDFManager."""
    from pdf_manager import PDFManager
    return PDFManager.convertir_et_fusionner_documents(
        nom=nom, prenom=prenom, id_salarie=id_salarie, parent=parent
    )



def ouvrir_dossier_salarie(
        nom,
        prenom,
        id_salarie
):
    """
    Ouvre le dossier individuel du salarié
    dans l'explorateur de fichiers du système.

    Compatible Linux et Windows.
    """

    nom = str(nom).strip()
    prenom = str(prenom).strip()
    id_salarie = str(id_salarie).strip()

    nom_dossier = (
        f"{nom}_{prenom}_{id_salarie[:8]}"
    )

    dossier = (
        Path(DOSSIER_SALARIES)
        / nom_dossier
    )

    dossier.mkdir(
        parents=True,
        exist_ok=True
    )

    dossier = dossier.resolve()

    systeme = platform.system()

    if systeme == "Windows":

        os.startfile(dossier)

    elif systeme == "Linux":

        subprocess.Popen(
            ["xdg-open", str(dossier)]
        )

    else:

        raise OSError(
            f"Système d'exploitation non pris en charge : "
            f"{systeme}"
        )

    return dossier

def ouvrir_document(chemin_document):
    """Ouvre un document avec l'application par défaut du système."""
    chemin = Path(chemin_document).expanduser().resolve()
    if not chemin.is_file():
        raise FileNotFoundError(f"Document introuvable : {chemin}")

    systeme = platform.system()
    if systeme == "Windows":
        os.startfile(str(chemin))
    elif systeme == "Linux":
        subprocess.Popen(["xdg-open", str(chemin)])
    elif systeme == "Darwin":
        subprocess.Popen(["open", str(chemin)])
    else:
        raise OSError(f"Système d'exploitation non pris en charge : {systeme}")

    return chemin

def preparer_impression_document(chemin_document):
    """
    Ouvre le PDF dans Xreader avec sa barre d'outils visible.
    Les autres documents restent ouverts avec l'application par défaut.
    """
    chemin = Path(chemin_document).expanduser().resolve()

    if not chemin.is_file():
        raise FileNotFoundError(
            f"Document introuvable : {chemin}"
        )

    if platform.system() == "Linux" and chemin.suffix.lower() == ".pdf":
        subprocess.Popen(["xreader", str(chemin)])
    else:
        ouvrir_document(chemin)

    return chemin



def renommer_document(
        chemin_document,
        nouveau_nom
):
    """
    Renomme un document existant.

    Retourne le nouveau chemin du document.

    Lève une erreur si :
    - le fichier n'existe pas ;
    - le nouveau nom est vide ;
    - un fichier portant déjà ce nom existe.
    """

    chemin_document = Path(
        chemin_document
    )

    nouveau_nom = str(
        nouveau_nom
    ).strip()

    if not chemin_document.is_file():
        raise FileNotFoundError(
            "Le document à renommer est introuvable."
        )

    if not nouveau_nom:
        raise ValueError(
            "Le nouveau nom du document ne peut pas être vide."
        )

    nouveau_chemin = (
        chemin_document.parent
        / nouveau_nom
    )

    if nouveau_chemin == chemin_document:
        raise ValueError(
            "Le nouveau nom est identique au nom actuel."
        )

    if nouveau_chemin.exists():
        raise FileExistsError(
            "Un document portant déjà ce nom existe."
        )

    chemin_document.rename(
        nouveau_chemin
    )

    return nouveau_chemin

def supprimer_document(chemin_document):
    """
    Supprime un document existant.

    Retourne True si la suppression a réussi.

    Lève une erreur si :
    - le chemin ne correspond pas à un fichier ;
    - le document est introuvable.
    """

    chemin_document = Path(
        chemin_document
    )

    if not chemin_document.is_file():
        raise FileNotFoundError(
            "Le document à supprimer est introuvable."
        )

    chemin_document.unlink()

    return True
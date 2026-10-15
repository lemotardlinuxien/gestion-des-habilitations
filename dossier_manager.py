from pathlib import Path
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from io import BytesIO
from time import monotonic

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
    """
    Sélecteur de documents dont l'ordre est déterminé par les clics.

    Un clic ajoute ou retire un fichier de la sélection. Les dossiers
    s'ouvrent par double-clic. Retourne une liste de Path, ou None si annulé.
    """
    extensions = {".jpg", ".jpeg", ".png", ".pdf"}
    resultat = {"fichiers": None}
    selection = []
    dossier_initial = Path.home()

    fenetre = tk.Toplevel(parent) if parent is not None else tk.Tk()
    fenetre.title("Sélectionner les documents à fusionner")
    fenetre.geometry("760x540")
    fenetre.minsize(600, 400)
    if parent is not None:
        fenetre.transient(parent)
    fenetre.grab_set()

    dossier_courant = {"chemin": dossier_initial}
    historique_dossiers = []
    dernier_clic = {"index": None, "temps": 0.0}

    haut = ttk.Frame(fenetre, padding=10)
    haut.pack(fill="x")
    lbl_chemin = ttk.Label(haut, text="", anchor="w")
    lbl_chemin.pack(fill="x", pady=(0, 8))
    barre = ttk.Frame(haut)
    barre.pack(fill="x")
    bouton_retour = ttk.Button(barre, text="← Retour au dossier précédent")
    bouton_retour.pack(side="left")

    liste_frame = ttk.Frame(fenetre, padding=(10, 0, 10, 5))
    liste_frame.pack(fill="both", expand=True)
    liste = tk.Listbox(
        liste_frame, font=("TkDefaultFont", 10),
        activestyle="none", selectmode=tk.SINGLE, exportselection=False
    )
    scrollbar = ttk.Scrollbar(liste_frame, orient="vertical", command=liste.yview)
    liste.configure(yscrollcommand=scrollbar.set)
    liste.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    lbl_selection = ttk.Label(fenetre, text="Aucun fichier sélectionné", padding=(10, 4))
    lbl_selection.pack(fill="x")
    bas = ttk.Frame(fenetre, padding=10)
    bas.pack(fill="x")
    lignes = []

    def actualiser_compteur():
        if not selection:
            lbl_selection.configure(text="Aucun fichier sélectionné")
        else:
            noms = "  →  ".join(
                f"{i}. {p.name}" for i, p in enumerate(selection, 1)
            )
            lbl_selection.configure(
                text=f"{len(selection)} fichier(s), ordre choisi : {noms}"
            )
        bouton_ouvrir.configure(text=f"Ouvrir et continuer ({len(selection)})")

    def rafraichir():
        chemin = dossier_courant["chemin"]
        lbl_chemin.configure(text=f"Dossier : {chemin}")
        bouton_retour.configure(state="normal" if historique_dossiers else "disabled")
        liste.delete(0, tk.END)
        lignes.clear()
        try:
            elements = list(chemin.iterdir())
        except OSError as erreur:
            messagebox.showerror(
                "Accès au dossier impossible", str(erreur), parent=fenetre
            )
            return

        dossiers = sorted(
            (p for p in elements if p.is_dir()), key=lambda p: p.name.casefold()
        )
        fichiers = sorted(
            (p for p in elements if p.is_file() and p.suffix.lower() in extensions),
            key=lambda p: p.name.casefold()
        )
        for dossier in dossiers:
            lignes.append(("dossier", dossier))
            liste.insert(tk.END, f"[DOSSIER]  {dossier.name}/")
        for fichier in fichiers:
            lignes.append(("fichier", fichier))
            if fichier in selection:
                numero = selection.index(fichier) + 1
                marque = f"[{numero:02d}]"
            else:
                marque = "[ ]"
            liste.insert(tk.END, f"{marque}  {fichier.name}")
        actualiser_compteur()

    def clic_liste(event):
        index = liste.nearest(event.y)
        if not 0 <= index < len(lignes):
            return "break"
        type_ligne, chemin = lignes[index]
        if type_ligne == "dossier":
            return None

        maintenant = monotonic()
        # Empêche un double-clic rapide sur un fichier de le sélectionner puis retirer.
        if (dernier_clic["index"] == index
                and maintenant - dernier_clic["temps"] < 0.35):
            dernier_clic["index"] = None
            dernier_clic["temps"] = 0.0
            return "break"

        dernier_clic["index"] = index
        dernier_clic["temps"] = maintenant
        if chemin in selection:
            selection.remove(chemin)
        else:
            selection.append(chemin)
        rafraichir()
        return "break"

    def revenir_dossier_precedent():
        """Revient au dossier visité juste avant le dossier courant."""
        if not historique_dossiers:
            return
        dossier_courant["chemin"] = historique_dossiers.pop()
        dernier_clic["index"] = None
        dernier_clic["temps"] = 0.0
        rafraichir()

    def double_clic(event):
        index = liste.nearest(event.y)
        if 0 <= index < len(lignes):
            type_ligne, chemin = lignes[index]
            if type_ligne == "dossier":
                historique_dossiers.append(dossier_courant["chemin"])
                dossier_courant["chemin"] = chemin
                dernier_clic["index"] = None
                rafraichir()
        return "break"

    def valider():
        if not selection:
            messagebox.showwarning(
                "Aucun document sélectionné",
                "Cliquez sur un ou plusieurs fichiers avant de continuer.",
                parent=fenetre
            )
            return
        resultat["fichiers"] = list(selection)
        fenetre.destroy()

    def annuler():
        resultat["fichiers"] = None
        fenetre.destroy()

    # Le sélecteur démarre directement dans le dossier personnel de l'utilisateur.
    # La navigation reste possible par double-clic sur les dossiers affichés.
    bouton_retour.configure(command=revenir_dossier_precedent)
    liste.bind("<Button-1>", clic_liste)
    liste.bind("<Double-Button-1>", double_clic)

    bouton_ouvrir = ttk.Button(
        bas, text="Ouvrir et continuer (0)", command=valider
    )
    bouton_ouvrir.pack(side="right", padx=(5, 0))
    ttk.Button(bas, text="Annuler", command=annuler).pack(side="right")
    fenetre.protocol("WM_DELETE_WINDOW", annuler)
    rafraichir()
    fenetre.wait_window()
    return resultat["fichiers"]


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


def convertir_et_fusionner_documents(
        nom,
        prenom,
        id_salarie,
        parent=None
):
    """Fusionne des images et/ou PDF puis enregistre le résultat chez le salarié.

    Les fichiers sources restent inchangés. L'ordre des pages suit l'ordre
    des fichiers renvoyé par le sélecteur. Retourne le chemin final, ou None
    si l'utilisateur annule une étape.
    """
    try:
        from PIL import Image, ImageOps
        from pypdf import PdfReader, PdfWriter
    except ImportError as erreur:
        raise RuntimeError(
            "La fusion PDF nécessite les bibliothèques Pillow et pypdf. "
            "Installez-les avec : python -m pip install Pillow pypdf"
        ) from erreur

    fichiers = selectionner_documents_ordonnes(parent=parent)
    if not fichiers:
        return None

    # L'ordre des clics est conservé pour l'ordre des pages du PDF final.
    chemins = [Path(fichier) for fichier in fichiers]
    extensions_autorisees = {".jpg", ".jpeg", ".png", ".pdf"}
    non_supportes = [
        chemin.name for chemin in chemins
        if chemin.suffix.lower() not in extensions_autorisees
    ]
    if non_supportes:
        raise ValueError(
            "Format non pris en charge : " + ", ".join(non_supportes)
        )

    for chemin in chemins:
        if not chemin.is_file():
            raise FileNotFoundError(
                f"Le document source est introuvable : {chemin.name}"
            )

    nom = str(nom).strip()
    prenom = str(prenom).strip()
    id_salarie = str(id_salarie).strip()
    nom_dossier = f"{nom}_{prenom}_{id_salarie[:8]}"
    dossier = (Path(DOSSIER_SALARIES) / nom_dossier)
    dossier.mkdir(parents=True, exist_ok=True)

    nom_pdf = simpledialog.askstring(
        "Nom du PDF final",
        "Saisissez le nom du PDF à créer (sans extension) :",
        parent=parent,
    )
    if nom_pdf is None:
        return None

    nom_pdf = nom_pdf.strip()
    if not nom_pdf:
        raise ValueError("Le nom du PDF ne peut pas être vide.")

    # Empêche un nom de fichier de sortir du dossier du salarié.
    nom_pdf = Path(nom_pdf).name
    if nom_pdf in {".", ".."}:
        raise ValueError("Le nom du PDF est invalide.")
    if not nom_pdf.lower().endswith(".pdf"):
        nom_pdf += ".pdf"

    destination = dossier / nom_pdf
    if destination.exists():
        remplacer = messagebox.askyesno(
            "PDF déjà existant",
            f"Le fichier {nom_pdf} existe déjà dans le dossier du salarié.\n\n"
            "Voulez-vous le remplacer ?",
            parent=parent,
        )
        if not remplacer:
            return None

    writer = PdfWriter()
    try:
        for chemin in chemins:
            if chemin.suffix.lower() == ".pdf":
                # PdfReader détectera les PDF invalides ou protégés.
                reader = PdfReader(str(chemin), strict=False)
                if reader.is_encrypted:
                    try:
                        decrypte = reader.decrypt("")
                    except Exception:
                        decrypte = 0
                    if not decrypte:
                        raise ValueError(
                            f"Le PDF est protégé par mot de passe : {chemin.name}"
                        )
                for page in reader.pages:
                    writer.add_page(page)
            else:
                # Conversion en mémoire : aucun fichier intermédiaire à nettoyer.
                with Image.open(chemin) as image_source:
                    image = ImageOps.exif_transpose(image_source)
                    if image.mode in ("RGBA", "LA") or (
                        image.mode == "P" and "transparency" in image.info
                    ):
                        image = image.convert("RGBA")
                        fond = Image.new("RGB", image.size, "white")
                        fond.paste(image, mask=image.getchannel("A"))
                        image_pdf = fond
                    else:
                        image_pdf = image.convert("RGB")

                    tampon = BytesIO()
                    image_pdf.save(tampon, format="PDF", resolution=150.0)
                    tampon.seek(0)
                    reader_image = PdfReader(tampon)
                    for page in reader_image.pages:
                        writer.add_page(page)

        if len(writer.pages) == 0:
            raise ValueError("Les fichiers sélectionnés ne contiennent aucune page.")

        # Écriture temporaire dans le dossier cible, puis remplacement atomique.
        temporaire = dossier / f".{destination.stem}.fusion-temp.pdf"
        try:
            with temporaire.open("wb") as fichier_sortie:
                writer.write(fichier_sortie)
            temporaire.replace(destination)
        finally:
            if temporaire.exists():
                temporaire.unlink()
    except Exception:
        # Ne jamais laisser un PDF final partiel en cas d'échec.
        raise
    finally:
        writer.close()

    return destination


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
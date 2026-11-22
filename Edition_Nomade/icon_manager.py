from pathlib import Path

from PIL import Image, ImageTk


# ==========================================================
# DOSSIER CONTENANT LES ICÔNES PNG
# ==========================================================

DOSSIER_ICONES = (
    Path(__file__).resolve().parent / "icons"
)


# ==========================================================
# CHARGEMENT D'UNE ICÔNE
# ==========================================================

def charger_icone(nom, taille=12):
    """
    Charge une icône PNG et la convertit
    en image utilisable par Tkinter.

    Paramètres
    ----------
    nom : str
        Nom de l'icône sans extension.

    taille : int
        Taille souhaitée de l'icône en pixels.

    Retour
    ------
    ImageTk.PhotoImage
        Image utilisable par Tkinter.
    """

    chemin = DOSSIER_ICONES / f"{nom}.png"

    if not chemin.exists():
        # Les icônes sont décoratives : leur absence ne doit pas empêcher
        # le démarrage de l'application. Les boutons conservent leur libellé.
        return None

    image = Image.open(chemin)

    image = image.resize(
        (taille, taille),
        Image.Resampling.LANCZOS
    )

    return ImageTk.PhotoImage(image)
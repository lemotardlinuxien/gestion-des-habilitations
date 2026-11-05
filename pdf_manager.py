import os
import io
from io import BytesIO
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
try:
    from PIL import Image, ImageOps
    from pypdf import PdfReader, PdfWriter
except ImportError:
    Image = ImageOps = PdfReader = PdfWriter = None
import pandas as pd
from habilitation_manager import HabilitationManager
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4, landscape
from config import DOSSIER_PDF, DOSSIER_SALARIES
from datetime import datetime
from time import monotonic
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    DND_FILES = None
    TkinterDnD = None
class PDFManager:

    @staticmethod
    def _select_ordered_files(parent):
        extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".pdf"}
        result = {"files": None}
        selection = []
        dialog = tk.Toplevel(parent)
        dialog.title("Sélectionner les documents à fusionner")
        dialog.geometry("760x540")
        dialog.minsize(600, 400)
        dialog.transient(parent)
        dialog.grab_set()

        current_folder = {"path": Path.home()}
        folder_history = []
        last_click = {"index": None, "time": 0.0}

        top = ttk.Frame(dialog, padding=10)
        top.pack(fill="x")
        path_label = ttk.Label(top, text="", anchor="w")
        path_label.pack(fill="x", pady=(0, 8))
        toolbar = ttk.Frame(top)
        toolbar.pack(fill="x")
        back_button = ttk.Button(toolbar, text="← Retour au dossier précédent")
        back_button.pack(side="left")

        list_frame = ttk.Frame(dialog, padding=(10, 0, 10, 5))
        list_frame.pack(fill="both", expand=True)
        file_list = tk.Listbox(list_frame, font=("TkDefaultFont", 10),
                               activestyle="none", selectmode=tk.SINGLE,
                               exportselection=False)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=file_list.yview)
        file_list.configure(yscrollcommand=scrollbar.set)
        file_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        selection_label = ttk.Label(dialog, text="Aucun fichier sélectionné", padding=(10, 4))
        selection_label.pack(fill="x")
        bottom = ttk.Frame(dialog, padding=10)
        bottom.pack(fill="x")
        rows = []
        continue_button = ttk.Button(bottom, text="Ouvrir et continuer (0)")
        continue_button.pack(side="right", padx=(5, 0))
        ttk.Button(bottom, text="Annuler", command=lambda: cancel()).pack(side="right")

        def update_counter():
            if not selection:
                selection_label.configure(text="Aucun fichier sélectionné")
            else:
                names = "  →  ".join(f"{i}. {item.name}" for i, item in enumerate(selection, 1))
                selection_label.configure(text=f"{len(selection)} fichier(s), ordre choisi : {names}")
            continue_button.configure(text=f"Ouvrir et continuer ({len(selection)})")

        def refresh():
            folder = current_folder["path"]
            path_label.configure(text=f"Dossier : {folder}")
            back_button.configure(state="normal" if folder_history else "disabled")
            file_list.delete(0, tk.END)
            rows.clear()
            try:
                entries = list(folder.iterdir())
            except OSError as error:
                messagebox.showerror("Accès au dossier impossible", str(error), parent=dialog)
                return
            folders = sorted((item for item in entries if item.is_dir()), key=lambda item: item.name.casefold())
            files = sorted((item for item in entries if item.is_file() and item.suffix.lower() in extensions),
                           key=lambda item: item.name.casefold())
            for item in folders:
                rows.append(("folder", item))
                file_list.insert(tk.END, f"[DOSSIER]  {item.name}/")
            for item in files:
                rows.append(("file", item))
                marker = f"[{selection.index(item) + 1:02d}]" if item in selection else "[ ]"
                file_list.insert(tk.END, f"{marker}  {item.name}")
            update_counter()

        def on_click(event):
            index = file_list.nearest(event.y)
            if not 0 <= index < len(rows):
                return "break"
            row_type, path = rows[index]
            if row_type == "folder":
                return "break"
            now = monotonic()
            if last_click["index"] == index and now - last_click["time"] < 0.35:
                last_click["index"] = None
                last_click["time"] = 0.0
                return "break"
            last_click["index"] = index
            last_click["time"] = now
            if path in selection:
                selection.remove(path)
            else:
                selection.append(path)
            refresh()
            return "break"

        def go_back():
            if folder_history:
                current_folder["path"] = folder_history.pop()
                last_click["index"] = None
                last_click["time"] = 0.0
                refresh()

        def on_double_click(event):
            index = file_list.nearest(event.y)
            if 0 <= index < len(rows):
                row_type, path = rows[index]
                if row_type == "folder":
                    folder_history.append(current_folder["path"])
                    current_folder["path"] = path
                    last_click["index"] = None
                    refresh()
            return "break"

        def accept():
            if not selection:
                messagebox.showwarning("Aucun document sélectionné",
                                       "Clique sur un ou plusieurs fichiers avant de continuer.", parent=dialog)
                return
            result["files"] = list(selection)
            dialog.destroy()

        def cancel():
            result["files"] = None
            dialog.destroy()

        back_button.configure(command=go_back)
        file_list.bind("<Button-1>", on_click)
        file_list.bind("<Double-Button-1>", on_double_click)
        continue_button.configure(command=accept)
        dialog.protocol("WM_DELETE_WINDOW", cancel)
        refresh()
        parent.wait_window(dialog)
        return result["files"]

    @staticmethod
    def selectionner_documents_ordonnes(parent=None):
        """Sélectionne plusieurs fichiers et permet de réorganiser leur ordre.

        Le glisser-déposer dans la liste et les boutons Monter/Descendre
        déterminent l'ordre exact des pages du PDF final.
        Retourne une liste de Path, ou None si l'utilisateur annule.
        """
        extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".pdf"}
        result = {"files": None}
        files = []

        dnd_disponible = DND_FILES is not None and TkinterDnD is not None

        if parent is not None:
            # L'application possède déjà sa racine Tk (ttkbootstrap/Tkinter).
            # On charge tkdnd dans CET interpréteur, puis on crée une Toplevel Tk classique.
            # TkinterDnD.Toplevel n'existe pas dans tkinterdnd2 0.6.4.
            if dnd_disponible:
                try:
                    # Initialise tkdnd dans l'interpréteur Tcl/Tk déjà utilisé par
                    # l'application. Ne crée surtout pas de seconde racine Tk.
                    TkinterDnD._require(parent)

                    # Les widgets Tk classiques n'exposent pas eux-mêmes les
                    # méthodes DnD : on ajoute le mixin DnDWrapper à cette Toplevel.
                    class FenetreDnD(tk.Toplevel, TkinterDnD.DnDWrapper):
                        pass

                    fenetre = FenetreDnD(parent)
                except (tk.TclError, AttributeError) as erreur:
                    dnd_disponible = False
                    fenetre = tk.Toplevel(parent)
                    messagebox.showwarning(
                        "Glisser-déposer indisponible",
                        "L'extension tkdnd n'a pas pu être activée.\n\n"
                        f"Détail : {erreur}\n\n"
                        "Vous pourrez tout de même ajouter les fichiers avec le bouton dédié.",
                        parent=parent,
                    )
            else:
                fenetre = tk.Toplevel(parent)
        else:
            fenetre = TkinterDnD.Tk() if dnd_disponible else tk.Tk()
        fenetre.title("Documents à convertir et fusionner")
        fenetre.geometry("820x520")
        fenetre.minsize(650, 400)
        if parent is not None:
            fenetre.transient(parent)
        fenetre.grab_set()

        haut = ttk.Frame(fenetre, padding=12)
        haut.pack(fill="x")
        ttk.Label(
            haut,
            text="Ajoutez les fichiers, puis faites-les glisser pour définir l'ordre des pages.",
            wraplength=760,
        ).pack(anchor="w")

        actions = ttk.Frame(fenetre, padding=(12, 0, 12, 8))
        actions.pack(fill="x")
        table_frame = ttk.Frame(fenetre, padding=(12, 0, 12, 4))
        table_frame.pack(fill="both", expand=True)
        colonnes = ("ordre", "nom", "type", "taille")
        table = ttk.Treeview(table_frame, columns=colonnes, show="headings", selectmode="extended")
        table.heading("ordre", text="Ordre")
        table.heading("nom", text="Fichier")
        table.heading("type", text="Type")
        table.heading("taille", text="Taille")
        table.column("ordre", width=65, anchor="center", stretch=False)
        table.column("nom", width=450)
        table.column("type", width=80, anchor="center", stretch=False)
        table.column("taille", width=90, anchor="e", stretch=False)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=scrollbar.set)
        table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        statut = tk.StringVar(value="Aucun fichier sélectionné.")
        ttk.Label(fenetre, textvariable=statut, padding=(12, 5)).pack(fill="x")

        def rafraichir(selection_a_restaurer=None):
            table.delete(*table.get_children())
            for index, chemin in enumerate(files):
                try:
                    taille = chemin.stat().st_size
                    taille_txt = f"{taille / 1024:.0f} Ko" if taille < 1024 * 1024 else f"{taille / (1024 * 1024):.1f} Mo"
                except OSError:
                    taille_txt = "—"
                table.insert("", "end", iid=str(index), values=(index + 1, chemin.name, chemin.suffix[1:].upper(), taille_txt))
            if selection_a_restaurer:
                for index in selection_a_restaurer:
                    if 0 <= index < len(files):
                        table.selection_add(str(index))
            statut.set(f"{len(files)} fichier(s) — ordre de haut en bas.")

        def ajouter_chemins(chemins, source="sélecteur"):
            """Ajoute des chemins en respectant strictement leur ordre d'arrivée."""
            existants = {str(f.resolve()).casefold() for f in files}
            ajoutes = 0
            ignores = 0
            for valeur in chemins:
                chemin = Path(valeur)
                if chemin.suffix.lower() not in extensions or not chemin.is_file():
                    ignores += 1
                    continue
                try:
                    cle = str(chemin.resolve()).casefold()
                except OSError:
                    cle = str(chemin).casefold()
                if cle not in existants:
                    files.append(chemin)
                    existants.add(cle)
                    ajoutes += 1
            rafraichir([len(files) - 1] if ajoutes == 1 else None)
            if ajoutes:
                statut.set(f"{len(files)} fichier(s) — {ajoutes} ajouté(s) dans l'ordre du dépôt.")
            elif ignores:
                statut.set("Aucun nouveau fichier pris en charge n'a été ajouté.")

        def ajouter_fichiers():
            chemins = PDFManager._select_ordered_files(parent=fenetre)
            if chemins:
                ajouter_chemins(chemins, source="sélecteur personnalisé")

        def recevoir_depot(event):
            """Ajoute les fichiers déposés depuis l'Explorateur Windows/Linux."""
            try:
                # splitlist est nécessaire : les chemins peuvent contenir des espaces.
                chemins = fenetre.tk.splitlist(event.data)
            except (tk.TclError, TypeError):
                statut.set("Impossible de lire les fichiers déposés.")
                return "break"
            if chemins:
                ajouter_chemins(chemins, source="glisser-déposer")
                statut.set(
                    f"{len(files)} fichier(s) — dépôt ajouté dans l'ordre reçu. "
                    "Faites glisser les lignes pour modifier l'ordre."
                )
            return "break"

        def retirer_selection():
            indices = sorted((int(i) for i in table.selection()), reverse=True)
            for index in indices:
                files.pop(index)
            rafraichir()

        def vider_liste():
            if files and not messagebox.askyesno("Confirmation", "Retirer tous les fichiers de la liste ?", parent=fenetre):
                return
            files.clear()
            rafraichir()

        def deplacer(direction):
            indices = sorted(int(i) for i in table.selection())
            if not indices:
                return
            selection_fichiers = {files[i] for i in indices}
            indices_selectionnes = set(indices)
            if direction < 0:
                for i in indices:
                    if i > 0 and i - 1 not in indices_selectionnes:
                        files[i - 1], files[i] = files[i], files[i - 1]
            else:
                for i in reversed(indices):
                    if i < len(files) - 1 and i + 1 not in indices_selectionnes:
                        files[i + 1], files[i] = files[i], files[i + 1]
            nouveaux_indices = [i for i, fichier in enumerate(files) if fichier in selection_fichiers]
            rafraichir(nouveaux_indices)

        drag = {"iid": None}

        def debut_glisser(event):
            iid = table.identify_row(event.y)
            drag["iid"] = iid if iid else None

        def terminer_glisser(event):
            source = drag["iid"]
            drag["iid"] = None
            cible = table.identify_row(event.y)
            if not source or not cible or source == cible:
                return
            try:
                source_index, cible_index = int(source), int(cible)
            except ValueError:
                return
            fichier = files.pop(source_index)
            if source_index < cible_index:
                cible_index -= 1
            files.insert(cible_index, fichier)
            rafraichir([cible_index])
            statut.set("Ordre modifié par glisser-déposer.")

        def valider():
            if not files:
                messagebox.showwarning("Aucun fichier", "Ajoutez au moins une image ou un PDF.", parent=fenetre)
                return
            result["files"] = list(files)
            fenetre.destroy()

        def annuler():
            result["files"] = None
            fenetre.destroy()

        ttk.Button(actions, text="Ajouter des fichiers…", command=ajouter_fichiers).pack(side="left")
        ttk.Button(actions, text="Retirer", command=retirer_selection).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Tout effacer", command=vider_liste).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="↑ Monter", command=lambda: deplacer(-1)).pack(side="right", padx=(6, 0))
        ttk.Button(actions, text="↓ Descendre", command=lambda: deplacer(1)).pack(side="right")

        bas = ttk.Frame(fenetre, padding=12)
        bas.pack(fill="x")
        ttk.Button(bas, text="Annuler", command=annuler).pack(side="right", padx=(6, 0))
        ttk.Button(bas, text="Continuer", command=valider).pack(side="right")
        table.bind("<ButtonPress-1>", debut_glisser, add="+")
        table.bind("<ButtonRelease-1>", terminer_glisser, add="+")
        table.bind("<Delete>", lambda _event: retirer_selection())

        # Dépôt externe : enregistrer la Toplevel DnD, dont l'initialisation
        # est explicite via FenetreDnD. Cela évite de dépendre de méthodes DnD
        # non garanties sur un ttk.Treeview dans tous les environnements.
        if dnd_disponible and hasattr(fenetre, "drop_target_register"):
            try:
                fenetre.drop_target_register(DND_FILES)
                fenetre.dnd_bind("<<Drop>>", recevoir_depot)
                statut.set(
                    "Glissez les fichiers dans cette fenêtre, ou cliquez sur "
                    "« Ajouter des fichiers… »."
                )
            except (tk.TclError, AttributeError):
                statut.set(
                    "Glisser-déposer externe indisponible ; utilisez "
                    "« Ajouter des fichiers… »."
                )
        fenetre.protocol("WM_DELETE_WINDOW", annuler)
        parent.wait_window(fenetre) if parent is not None else fenetre.mainloop()
        return result["files"]

    @staticmethod
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

        fichiers = PDFManager.selectionner_documents_ordonnes(parent=parent)
        if not fichiers:
            return None

        # L'ordre de la liste est conservé pour l'ordre des pages du PDF final.
        # Il reflète l'ordre du dépôt initial, sauf si l'utilisateur le réorganise.
        chemins = [Path(fichier) for fichier in fichiers]
        extensions_autorisees = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".pdf"}
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
        tampons_images = []
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
                        # Les TIFF multipages et images animées sont convertis page par page.
                        nombre_images = getattr(image_source, "n_frames", 1)
                        for numero_image in range(nombre_images):
                            image_source.seek(numero_image)
                            image = ImageOps.exif_transpose(image_source.copy())
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
                            tampons_images.append(tampon)
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
            for tampon in tampons_images:
                tampon.close()

        return destination

    @staticmethod
    def generer(df):

        aujourd_hui = pd.Timestamp.today()

        secteurs = sorted(
            df["Secteur"].dropna().unique()
        )

        # Les habilitations ne changent pas pendant la génération du PDF :
        # on les récupère une seule fois plutôt qu'à chaque secteur/salarié.
        habilitations = HabilitationManager.lister()

        for secteur in secteurs:

            pdf = os.path.join(
                DOSSIER_PDF,
                f"{secteur}.pdf"
            )

            document = SimpleDocTemplate(
                pdf,
                pagesize=landscape(A4)
            )

            elements = []

            styles = getSampleStyleSheet()

            titre = Paragraph(
                f"HABILITATIONS VALIDES<br/>{secteur}",
                styles["Title"]
            )

            date_export = Paragraph(
                f"Date d'édition : {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
                styles["Normal"]
            )

            elements.append(date_export)
            elements.append(titre)
            elements.append(Spacer(1, 15))

            data = [[
                "Nom",
                "Prénom",
                *habilitations
            ]]

            secteur_df = df[df["Secteur"] == secteur]

            for _, row in secteur_df.iterrows():

                ligne = [
                    row["Nom"],
                    row["Prénom"]
                ]

                valide = False

                for hab in habilitations:

                    date = row[hab]

                    if pd.isna(date):
                        ligne.append("")
                        continue

                    date = pd.to_datetime(date)

                    if date >= aujourd_hui:

                        ligne.append(date.strftime("%d/%m/%Y"))
                        valide = True

                    else:
                        ligne.append("")

                if valide:
                    data.append(ligne)

            table = Table(data)

            table.setStyle(
                TableStyle([
                    ("GRID", (0, 0), (-1, -1), 1, colors.black)
                ])
            )

            elements.append(table)

            document.build(elements)
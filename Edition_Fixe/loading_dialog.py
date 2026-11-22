import ttkbootstrap as ttk
from tkinter import Toplevel, TclError
import re


class LoadingDialog:
    """Fenêtre de progression stable pendant les opérations longues."""

    def __init__(self, parent, titre="Veuillez patienter...", progression_determinate=False, afficher_progression=True, details_import=False):
        self.parent = parent
        self.titre = titre
        self.fenetre = None
        self.message = None
        self.progression = None
        self._texte_message = ""
        self._mode_progression = "determinate" if progression_determinate else "indeterminate"
        self._progression_determinate = progression_determinate
        self._afficher_progression = afficher_progression
        self._details_import = details_import
        self._etape_import = 0
        self._libelles_etapes = []

    def afficher(self):
        """Crée une fenêtre de progression avec une seule barre visible."""
        # Évite de construire deux fois le contenu si afficher() est rappelé.
        if self.fenetre is not None:
            try:
                if self.fenetre.winfo_exists():
                    return
            except TclError:
                pass
        self.fenetre = Toplevel(self.parent)
        self.fenetre.configure(background=self.parent.cget("background"))
        self.fenetre.title(self.titre)
        self.fenetre.resizable(False, False)
        self.fenetre.transient(self.parent)
        self.fenetre.grab_set()
        self.fenetre.attributes("-topmost", True)
        self.fenetre.protocol("WM_DELETE_WINDOW", self.fermer)

        cadre = ttk.Frame(self.fenetre, padding=(18, 16))
        cadre.pack(fill="both", expand=True)

        self._texte_message = "Chargement du fichier...\n\nVeuillez patienter"
        self.message = ttk.Label(
            cadre,
            text=self._texte_message,
            font=("Segoe UI", 13),
            anchor="center",
            justify="center",
            wraplength=400,
        )
        self.message.pack(fill="x", expand=False, padx=8, pady=(8, 12))

        # Pour Import Excel, afficher une liste d'étapes détaillées plutôt
        # qu'une barre : chaque ligne est actualisée dans ce dialogue unique.
        if self._details_import:
            separateur = ttk.Separator(cadre, orient="horizontal")
            separateur.pack(fill="x", padx=8, pady=(0, 10))

            titre_etapes = ttk.Label(
                cadre,
                text="DÉROULEMENT DE L’IMPORTATION",
                font=("Segoe UI", 9, "bold"),
                anchor="w",
            )
            titre_etapes.pack(fill="x", padx=8, pady=(0, 6))

            noms_etapes = [
                "Lecture du fichier Excel",
                "Vérification des en-têtes",
                "Vérification de la structure",
                "Normalisation des données",
                "Nettoyage des données",
                "Contrôle des identifiants, doublons et dates",
                "Préparation du résultat de l’import",
            ]
            for nom in noms_etapes:
                ligne = ttk.Frame(cadre)
                ligne.pack(fill="x", padx=8, pady=2)
                indicateur = ttk.Label(
                    ligne,
                    text="○",
                    width=3,
                    anchor="center",
                    font=("Segoe UI", 10, "bold"),
                )
                indicateur.pack(side="left")
                libelle = ttk.Label(
                    ligne,
                    text=nom,
                    anchor="w",
                    font=("Segoe UI", 9),
                )
                libelle.pack(side="left", fill="x", expand=True)
                statut = ttk.Label(
                    ligne,
                    text="À venir",
                    width=10,
                    anchor="e",
                    font=("Segoe UI", 8),
                )
                statut.pack(side="right")
                self._libelles_etapes.append((indicateur, libelle, statut))

            self._texte_message = "Préparation de l’importation…"
            self.message.configure(text=self._texte_message)

            note = ttk.Label(
                cadre,
                text="Veuillez patienter. Ne fermez pas l’application pendant le traitement.",
                font=("Segoe UI", 8),
                anchor="center",
                justify="center",
                wraplength=400,
            )
            note.pack(fill="x", padx=8, pady=(10, 0))

        # Les autres opérations conservent leur comportement habituel.
        if self._afficher_progression:
            mode_initial = "determinate" if self._progression_determinate else "indeterminate"
            self.progression = ttk.Progressbar(
                cadre,
                mode=mode_initial,
                length=300,
                maximum=7 if self._progression_determinate else 100,
                value=0,
            )
            self.progression.pack(fill="x", padx=12, pady=(0, 8))
            if not self._progression_determinate:
                self.progression.start(10)

        # Garde une seule barre si elle est activée.
        self._garder_une_seule_barre()
        self.fenetre.update_idletasks()
        self._centrer_fenetre(460, max(190, self.fenetre.winfo_reqheight()))
        self.fenetre.update_idletasks()

    def _garder_une_seule_barre(self):
        """Supprime les barres de progression supplémentaires dans ce dialogue."""
        if self.fenetre is None or self.progression is None:
            return
        try:
            if not self.fenetre.winfo_exists() or not self.progression.winfo_exists():
                return

            def parcourir(parent):
                for enfant in parent.winfo_children():
                    if isinstance(enfant, ttk.Progressbar):
                        if enfant is not self.progression:
                            try:
                                enfant.stop()
                            except TclError:
                                pass
                            enfant.destroy()
                    else:
                        parcourir(enfant)

            parcourir(self.fenetre)
        except TclError:
            pass

    def changer_message(self, texte):
        """Actualise le message sans redimensionnements successifs instables."""
        if self.fenetre is None or self.message is None:
            return

        try:
            if not self.fenetre.winfo_exists():
                return
            self._texte_message = str(texte)
            self.message.configure(text=self._texte_message)
            self._actualiser_etapes_import(self._texte_message)
            self._garder_une_seule_barre()

            # Pendant l'envoi des mails, utiliser une progression réelle
            # basée sur le compteur transmis par envoi_secteurs_manager.
            compteur = re.search(
                r"(?:Envoi|Étape)\s+(\d+)\s*/\s*(\d+)",
                self._texte_message,
                flags=re.IGNORECASE,
            )
            if compteur and self.progression is not None:
                numero = int(compteur.group(1))
                total = max(1, int(compteur.group(2)))
                if self._mode_progression != "determinate":
                    self.progression.stop()
                    self.progression.configure(
                        mode="determinate",
                        maximum=total,
                        value=0,
                    )
                    self._mode_progression = "determinate"
                else:
                    self.progression.configure(maximum=total)
                self.progression.configure(value=min(numero, total))
            elif (
                self.progression is not None
                and self._mode_progression != "indeterminate"
                and not self._progression_determinate
            ):
                self.progression.configure(mode="indeterminate", value=0)
                self.progression.start(10)
                self._mode_progression = "indeterminate"

            # Forcer le rafraîchissement visuel sans appeler update(), qui
            # pourrait réentrer dans les événements Tk pendant l'envoi.
            self.fenetre.update_idletasks()

            # Adapter la hauteur au texte (notamment au nom du secteur),
            # sans réduire la fenêtre sous la hauteur réellement requise.
            largeur = 460
            hauteur = max(210, self.fenetre.winfo_reqheight())
            hauteur = min(hauteur, max(210, self.fenetre.winfo_screenheight() - 80))
            self._centrer_fenetre(largeur, hauteur)
            self.fenetre.update_idletasks()
        except TclError:
            # Le dialogue peut avoir été fermé manuellement.
            pass

    def _actualiser_etapes_import(self, texte):
        """Actualise les statuts de la liste détaillée de l'import Excel."""
        if not self._details_import or not self._libelles_etapes:
            return

        correspondance = re.search(
            r"Étape\s+(\d+)\s*/\s*7\s*[—-]\s*(.*)",
            texte,
            flags=re.IGNORECASE,
        )
        if not correspondance:
            return

        try:
            numero = max(1, min(7, int(correspondance.group(1))))
        except (TypeError, ValueError):
            return

        self._etape_import = numero
        for index, (indicateur, libelle, statut) in enumerate(self._libelles_etapes, start=1):
            if index < numero:
                indicateur.configure(text="✓")
                statut.configure(text="Terminé")
                libelle.configure(font=("Segoe UI", 9))
            elif index == numero:
                indicateur.configure(text="●")
                statut.configure(text="En cours")
                libelle.configure(font=("Segoe UI", 9, "bold"))
            else:
                indicateur.configure(text="○")
                statut.configure(text="À venir")
                libelle.configure(font=("Segoe UI", 9))

    def _centrer_fenetre(self, largeur, hauteur):
        """Centre la fenêtre sur son parent et garde ses limites à l'écran."""
        if self.fenetre is None:
            return
        self.parent.update_idletasks()
        ecran_l = self.fenetre.winfo_screenwidth()
        ecran_h = self.fenetre.winfo_screenheight()
        largeur = min(largeur, ecran_l - 30)
        hauteur = min(hauteur, ecran_h - 60)
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - largeur) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - hauteur) // 2
        x = max(15, min(x, ecran_l - largeur - 15))
        y = max(15, min(y, ecran_h - hauteur - 30))
        self.fenetre.geometry(f"{largeur}x{hauteur}+{x}+{y}")

    def fermer(self):
        """Ferme proprement la fenêtre."""
        fenetre = self.fenetre
        progression = self.progression
        self.fenetre = None
        self.progression = None
        self.message = None

        if progression is not None:
            try:
                if progression.winfo_exists():
                    progression.stop()
            except TclError:
                pass

        if fenetre is not None:
            try:
                if fenetre.winfo_exists():
                    fenetre.grab_release()
                    fenetre.destroy()
            except TclError:
                pass

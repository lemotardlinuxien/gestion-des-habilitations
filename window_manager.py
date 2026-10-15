class WindowManager:
    """
    Gère les fenêtres secondaires de l'application.

    Une seule fenêtre de travail peut être ouverte
    à un instant donné.
    """

    def __init__(self):

        self.fenetre_active = None

    def ouvrir(self, fenetre):
        """
        Ouvre une nouvelle fenêtre.

        Si une autre fenêtre est déjà ouverte,
        elle est automatiquement fermée.
        """

        self.fermer()

        self.fenetre_active = fenetre

    def fermer(self):
        """
        Ferme la fenêtre actuellement ouverte.
        """

        if (
                self.fenetre_active
                and self.fenetre_active.winfo_exists()
        ):
            self.fenetre_active.destroy()

        self.fenetre_active = None

    def est_ouverte(self):
        """
        Indique si une fenêtre est actuellement ouverte.
        """

        return (
                self.fenetre_active is not None
                and self.fenetre_active.winfo_exists()
        )
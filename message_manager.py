from tkinter import messagebox


class MessageManager:

    def __init__(
        self,
        root,
        windows
    ):
        self.root = root
        self.windows = windows

    def _parent(self):
        """
        Retourne la fenêtre qui doit être parente
        du dialogue.

        Si une fenêtre secondaire est ouverte,
        le dialogue lui est rattaché.
        Sinon, il est rattaché à la fenêtre principale.
        """

        if self.windows.est_ouverte():
            return self.windows.fenetre_active

        return self.root

    def info(self, titre, message, parent=None):
        messagebox.showinfo(
            titre,
            message,
            parent=parent or self._parent()
        )

    def warning(self, titre, message, parent=None):
        messagebox.showwarning(
            titre,
            message,
            parent=parent or self._parent()
        )

    def error(self, titre, message, parent=None):
        messagebox.showerror(
            titre,
            message,
            parent=parent or self._parent()
        )

    def confirm(self, titre, message, parent=None):
        return messagebox.askyesno(
            titre,
            message,
            parent=parent or self._parent()
        )

    def resultat_import(
        self,
        rapport: dict
    ):
        message = (
            "Import terminé.\n\n"
            f"Ajoutés : {rapport.get('ajoutes', 0)}\n"
            f"Modifiés : {rapport.get('modifies', 0)}"
        )

        avertissements = rapport.get(
            "avertissements",
            []
        )

        if avertissements:
            message += (
                "\n\nAvertissements :\n"
                + "\n\n".join(avertissements)
            )

        self.warning(
            titre="Import",
            message=message
        )
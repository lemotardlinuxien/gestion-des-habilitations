
from database import get_connection


class DatabaseMonitor:
    """
    Surveille les modifications de la base SQLite
    effectuées par les autres connexions.
    """

    def __init__(self):
        self.connexion = None
        self.version_initiale = None

    def demarrer(self):
        """Ouvre la connexion de surveillance."""

        if self.connexion is not None:
            return

        connexion = get_connection()

        try:
            version = connexion.execute(
                "PRAGMA data_version"
            ).fetchone()[0]

            self.connexion = connexion
            self.version_initiale = version

        except Exception:
            connexion.close()
            raise

    def _lire_version(self):
        """Retourne la valeur PRAGMA data_version."""

        return self.connexion.execute(
            "PRAGMA data_version"
        ).fetchone()[0]

    def base_modifiee(self):
        """
        Indique si une autre connexion a validé
        une modification depuis le démarrage.
        """

        if self.connexion is None:
            raise RuntimeError(
                "La surveillance SQLite n'est pas démarrée."
            )

        version_actuelle = self._lire_version()

        return version_actuelle != self.version_initiale

    def fermer(self):
        """Ferme proprement la connexion."""

        if self.connexion is not None:
            self.connexion.close()
            self.connexion = None
            self.version_initiale = None

database_monitor = DatabaseMonitor()

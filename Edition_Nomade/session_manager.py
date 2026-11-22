# ==========================================
# SESSION UTILISATEUR
# ==========================================

class SessionManager:
    """
    Gère l'utilisateur connecté pendant toute
    la durée de l'application.

    Une seule session peut être active à la fois.
    """

    _utilisateur = None

    @classmethod
    def ouvrir(cls, utilisateur):
        """
        Ouvre une session avec l'utilisateur authentifié.
        """

        if not utilisateur:
            raise ValueError(
                "Impossible d'ouvrir une session "
                "sans utilisateur."
            )

        cls._utilisateur = dict(utilisateur)

    @classmethod
    def fermer(cls):
        """
        Ferme la session utilisateur.
        """

        cls._utilisateur = None

    @classmethod
    def est_connecte(cls):
        """
        Indique si un utilisateur est actuellement connecté.
        """

        return cls._utilisateur is not None

    @classmethod
    def utilisateur(cls):
        """
        Retourne les informations de l'utilisateur connecté.

        Retourne None si aucune session n'est ouverte.
        """

        if cls._utilisateur is None:
            return None

        return dict(cls._utilisateur)

    @classmethod
    def code(cls):
        """
        Retourne le code de l'utilisateur connecté.
        """

        if cls._utilisateur is None:
            return None

        return cls._utilisateur["code"]

    @classmethod
    def profil(cls):
        """
        Retourne le profil de l'utilisateur connecté.
        """

        if cls._utilisateur is None:
            return None

        return cls._utilisateur["profil"]

    @classmethod
    def est_administrateur(cls):
        """
        Indique si l'utilisateur connecté est Administrateur.
        """

        return cls.profil() == "Administrateur"

    @classmethod
    def peut_modifier(cls):
        """
        Indique si l'utilisateur peut effectuer
        des modifications métier.
        """

        return cls.profil() in {
            "Modification",
            "Administrateur",
        }

    @classmethod
    def peut_consulter(cls):
        """
        Indique si l'utilisateur peut consulter
        les données de l'application.
        """

        return cls.profil() in {
            "Consultation",
            "Modification",
            "Administrateur",
        }
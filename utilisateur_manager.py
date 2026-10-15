import secrets
import hashlib

from datetime import (
    datetime,
    timedelta)

from validation import verifier_email

from database import get_connection


# ==========================================
# PROFILS AUTORISÉS
# ==========================================

PROFILS = (
    "Consultation",
    "Modification",
    "Administrateur",
)


# ==========================================
# UTILISATEUR MANAGER
# ==========================================

class UtilisateurManager:
    """
    Gestion des utilisateurs de l'application.

    Responsabilités :
        - création des utilisateurs ;
        - vérification de l'unicité des codes ;
        - hachage des mots de passe Administrateur ;
        - gestion de l'état actif/inactif.
    """

    @staticmethod
    def _hachage_mot_de_passe(mot_de_passe):
        """
        Retourne un hash PBKDF2 sécurisé avec
        un sel aléatoire.

        Le résultat contient :
            - le sel ;
            - le nombre d'itérations ;
            - le hash.
        """

        sel = secrets.token_bytes(16)

        iterations = 600_000

        hash_mot_de_passe = hashlib.pbkdf2_hmac(
            "sha256",
            mot_de_passe.encode("utf-8"),
            sel,
            iterations,
        )

        return (
            f"pbkdf2_sha256${iterations}$"
            f"{sel.hex()}$"
            f"{hash_mot_de_passe.hex()}"
        )

    @staticmethod
    def _valider_mot_de_passe(mot_de_passe):
        """
        Vérifie qu'un mot de passe existe
        et ne contient pas uniquement des espaces.
        """

        if not mot_de_passe or not mot_de_passe.strip():
            raise ValueError(
                "Le mot de passe ne peut pas être vide."
            )

    @staticmethod
    def trouver_par_code(code):
        """
        Recherche un utilisateur actif à partir de son code.

        Cette méthode ne valide pas le mot de passe.
        Elle sert uniquement à déterminer le profil.
        """

        if not code:
            return None

        conn = get_connection()

        try:
            ligne = conn.execute(
                """
                SELECT
                    id,
                    code,
                    nom,
                    prenom,
                    profil,
                    actif,
                    date_creation
                FROM utilisateurs
                WHERE code = ?
                """,
                (code,)
            ).fetchone()

            if ligne is None:
                return None

            if not ligne[5]:
                return None

            return {
                "id": ligne[0],
                "code": ligne[1],
                "nom": ligne[2],
                "prenom": ligne[3],
                "profil": ligne[4],
                "actif": bool(ligne[5]),
                "date_creation": ligne[6],
            }

        finally:
            conn.close()

    @staticmethod
    def authentifier(code, mot_de_passe=None):
        """
        Authentifie un utilisateur.

        Règles :
            - Consultation / Modification : code uniquement ;
            - Administrateur : code + mot de passe ;
            - compte inactif : accès refusé ;
            - retourne les informations de l'utilisateur
              si l'authentification réussit.
        """

        code = str(code).strip()

        if not code:
            return None

        conn = get_connection()

        try:

            utilisateur = conn.execute(
                """
                SELECT
                    id,
                    code,
                    nom,
                    prenom,
                    profil,
                    mot_de_passe_hash,
                    actif,
                    date_creation
                FROM utilisateurs
                WHERE code = ?
                LIMIT 1
                """,
                (code,)
            ).fetchone()

        finally:
            conn.close()

        # ==========================================
        # UTILISATEUR INCONNU
        # ==========================================

        if utilisateur is None:
            return None

        (
            id_utilisateur,
            code_utilisateur,
            nom,
            prenom,
            profil,
            mot_de_passe_hash,
            actif,
            date_creation,
        ) = utilisateur

        # ==========================================
        # COMPTE INACTIF
        # ==========================================

        if not actif:
            return None

        # ==========================================
        # ADMINISTRATEUR
        # ==========================================

        if profil == "Administrateur":

            if not mot_de_passe:
                return None

            try:
                type_hash, iterations, sel_hex, hash_hex = (
                    mot_de_passe_hash.split("$")
                )

                if type_hash != "pbkdf2_sha256":
                    return None

                iterations = int(iterations)
                sel = bytes.fromhex(sel_hex)
                hash_attendu = bytes.fromhex(hash_hex)

            except (AttributeError, ValueError):
                return None

            hash_fourni = hashlib.pbkdf2_hmac(
                "sha256",
                mot_de_passe.encode("utf-8"),
                sel,
                iterations,
            )

            if not secrets.compare_digest(
                    hash_fourni,
                    hash_attendu
            ):
                return None

        # ==========================================
        # UTILISATEUR AUTHENTIFIÉ
        # ==========================================

        return {
            "id": id_utilisateur,
            "code": code_utilisateur,
            "nom": nom,
            "prenom": prenom,
            "profil": profil,
            "actif": bool(actif),
            "date_creation": date_creation,
        }

    @staticmethod
    def code_existe(code):
        """
        Vérifie si un code utilisateur existe déjà.

        Le code reste réservé même si le compte
        est ensuite archivé.
        """

        code = str(code).strip()

        if not code:
            return False

        conn = get_connection()

        try:
            resultat = conn.execute(
                """
                SELECT 1
                FROM utilisateurs
                WHERE code = ?
                LIMIT 1
                """,
                (code,)
            ).fetchone()

            return resultat is not None

        finally:
            conn.close()

    @staticmethod
    def recuperer_email(id_utilisateur):
        """
        Retourne l'adresse e-mail associée à un utilisateur.

        Retourne None si :
            - l'utilisateur n'existe pas ;
            - aucune adresse e-mail n'est enregistrée.
        """

        conn = get_connection()

        try:
            ligne = conn.execute(
                """
                SELECT email
                FROM utilisateurs
                WHERE id = ?
                """,
                (id_utilisateur,)
            ).fetchone()

            if ligne is None:
                return None

            return ligne[0]

        finally:
            conn.close()

    @staticmethod
    def creer_utilisateur(
            code,
            nom,
            prenom,
            profil,
            mot_de_passe=None,
            email=None,
    ):
        """
        Crée un utilisateur.

        Règles :
            - le code doit être unique ;
            - nom, prénom et profil sont obligatoires ;
            - le mot de passe est obligatoire uniquement
              pour un Administrateur ;
            - l'adresse e-mail est facultative ;
            - un utilisateur est actif à sa création.
        """

        # ==========================================
        # NORMALISATION
        # ==========================================

        code = str(code).strip()
        nom = str(nom).strip()
        prenom = str(prenom).strip()
        profil = str(profil).strip()

        email = (
            str(email).strip()
            if email is not None
            else ""
        )

        # ==========================================
        # VALIDATIONS
        # ==========================================

        if not code:
            raise ValueError(
                "Le code utilisateur est obligatoire."
            )

        if not nom:
            raise ValueError(
                "Le nom est obligatoire."
            )

        if not prenom:
            raise ValueError(
                "Le prénom est obligatoire."
            )

        if profil not in PROFILS:
            raise ValueError(
                "Le profil utilisateur est invalide."
            )

        # ==========================================
        # MOT DE PASSE
        # ==========================================

        mot_de_passe_hash = None

        if profil == "Administrateur":

            if not mot_de_passe:
                raise ValueError(
                    "Le mot de passe Administrateur "
                    "est obligatoire."
                )

            UtilisateurManager._valider_mot_de_passe(
                mot_de_passe
            )

            mot_de_passe_hash = (
                UtilisateurManager
                ._hachage_mot_de_passe(
                    mot_de_passe
                )
            )

        # ==========================================
        # VÉRIFICATION DU CODE
        # ==========================================

        if UtilisateurManager.code_existe(code):

            raise ValueError(
                "Ce code utilisateur existe déjà."
            )

        # ==========================================
        # DATE DE CRÉATION
        # ==========================================

        date_creation = datetime.now().isoformat(
            timespec="seconds"
        )

        # ==========================================
        # INSERTION
        # ==========================================

        conn = get_connection()

        try:

            conn.execute(
                """
                INSERT INTO utilisateurs
                (
                    code,
                    nom,
                    prenom,
                    profil,
                    email,
                    mot_de_passe_hash,
                    actif,
                    date_creation
                )
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    code,
                    nom,
                    prenom,
                    profil,
                    email or None,
                    mot_de_passe_hash,
                    date_creation,
                )
            )

            conn.commit()

        except Exception:

            conn.rollback()
            raise

        finally:

            conn.close()

    @staticmethod
    def enregistrer_email(id_utilisateur, email):
        """
        Enregistre ou modifie l'adresse e-mail
        associée à un utilisateur.

        Une adresse vide supprime l'association.
        """

        if email is None:
            email = ""

        email = str(email).strip()

        conn = get_connection()

        try:
            utilisateur = conn.execute(
                """
                SELECT id
                FROM utilisateurs
                WHERE id = ?
                """,
                (id_utilisateur,)
            ).fetchone()

            if utilisateur is None:
                raise ValueError(
                    "Utilisateur introuvable."
                )

            conn.execute(
                """
                UPDATE utilisateurs
                SET email = ?
                WHERE id = ?
                """,
                (
                    email or None,
                    id_utilisateur,
                )
            )

            conn.commit()

        finally:
            conn.close()

    @staticmethod
    def modifier_utilisateur(
            id_utilisateur,
            nom,
            prenom,
            profil,
            nouveau_mot_de_passe=None,
            email=None,
    ):
        """
        Modifie les informations d'un utilisateur.

        Le code utilisateur n'est jamais modifié.

        Pour un administrateur :
        - le mot de passe actuel est conservé si aucun
          nouveau mot de passe n'est fourni ;
        - le mot de passe est remplacé uniquement si
          un nouveau mot de passe est fourni.

        L'adresse e-mail est facultative.
        Une adresse vide supprime l'adresse existante.

        Le dernier administrateur actif ne peut pas
        être rétrogradé vers un autre profil.
        """

        if not nom or not nom.strip():
            raise ValueError(
                "Le nom est obligatoire."
            )

        if not prenom or not prenom.strip():
            raise ValueError(
                "Le prénom est obligatoire."
            )

        if profil not in PROFILS:
            raise ValueError(
                "Le profil sélectionné est invalide."
            )

        if nouveau_mot_de_passe is not None:
            UtilisateurManager._valider_mot_de_passe(
                nouveau_mot_de_passe
            )

        email = (
            str(email).strip()
            if email is not None
            else ""
        )

        if email:
            valide, message = verifier_email(email)

            if not valide:
                raise ValueError(message)

        conn = get_connection()

        try:
            utilisateur = conn.execute(
                """
                SELECT
                    id,
                    code,
                    nom,
                    prenom,
                    profil,
                    actif
                FROM utilisateurs
                WHERE id = ?
                """,
                (id_utilisateur,)
            ).fetchone()

            if utilisateur is None:
                raise ValueError(
                    "Utilisateur introuvable."
                )

            (
                id_user,
                code,
                ancien_nom,
                ancien_prenom,
                ancien_profil,
                actif,
            ) = utilisateur

            # ==========================================
            # PROTECTION DU DERNIER ADMINISTRATEUR ACTIF
            # ==========================================

            if (
                    actif
                    and ancien_profil == "Administrateur"
                    and profil != "Administrateur"
            ):
                nombre_admins = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM utilisateurs
                    WHERE profil = 'Administrateur'
                    AND actif = 1
                    """
                ).fetchone()[0]

                if nombre_admins <= 1:
                    raise ValueError(
                        "Impossible de modifier le profil de ce compte : "
                        "il doit toujours rester au moins "
                        "un administrateur actif."
                    )

            # ==========================================
            # AVEC NOUVEAU MOT DE PASSE
            # ==========================================

            if nouveau_mot_de_passe is not None:

                mot_de_passe_hash = (
                    UtilisateurManager._hachage_mot_de_passe(
                        nouveau_mot_de_passe
                    )
                )

                conn.execute(
                    """
                    UPDATE utilisateurs
                    SET
                        nom = ?,
                        prenom = ?,
                        profil = ?,
                        email = ?,
                        mot_de_passe_hash = ?
                    WHERE id = ?
                    """,
                    (
                        nom.strip(),
                        prenom.strip(),
                        profil,
                        email or None,
                        mot_de_passe_hash,
                        id_utilisateur,
                    )
                )

            # ==========================================
            # SANS NOUVEAU MOT DE PASSE
            # ==========================================

            else:

                conn.execute(
                    """
                    UPDATE utilisateurs
                    SET
                        nom = ?,
                        prenom = ?,
                        profil = ?,
                        email = ?
                    WHERE id = ?
                    """,
                    (
                        nom.strip(),
                        prenom.strip(),
                        profil,
                        email or None,
                        id_utilisateur,
                    )
                )

            conn.commit()

            return True

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    @staticmethod
    def archiver_utilisateur(id_utilisateur):
        """
        Archive un utilisateur sans supprimer son historique.

        Le dernier administrateur actif ne peut pas être archivé.
        """

        conn = get_connection()

        try:
            utilisateur = conn.execute(
                """
                SELECT
                    id,
                    code,
                    profil,
                    actif
                FROM utilisateurs
                WHERE id = ?
                """,
                (id_utilisateur,)
            ).fetchone()

            if utilisateur is None:
                raise ValueError(
                    "Utilisateur introuvable."
                )

            id_user, code, profil, actif = utilisateur

            if not actif:
                raise ValueError(
                    "Cet utilisateur est déjà archivé."
                )

            # ==========================================
            # Protection du dernier administrateur actif
            # ==========================================

            if profil == "Administrateur":

                nombre_admins = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM utilisateurs
                    WHERE profil = 'Administrateur'
                    AND actif = 1
                    """
                ).fetchone()[0]

                if nombre_admins <= 1:
                    raise ValueError(
                        "Impossible d'archiver ce compte : "
                        "il doit toujours rester au moins "
                        "un administrateur actif."
                    )

            # ==========================================
            # Archivage
            # ==========================================

            conn.execute(
                """
                UPDATE utilisateurs
                SET actif = 0
                WHERE id = ?
                """,
                (id_utilisateur,)
            )

            conn.commit()

            return True

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    @staticmethod
    def reactiver_utilisateur(id_utilisateur):
        """
        Réactive un utilisateur archivé.

        Le code utilisateur, le nom, le prénom,
        le profil et le mot de passe sont conservés.

        Un utilisateur déjà actif ne peut pas
        être réactivé.
        """

        conn = get_connection()

        try:

            utilisateur = conn.execute(
                """
                SELECT
                    id,
                    code,
                    actif
                FROM utilisateurs
                WHERE id = ?
                """,
                (id_utilisateur,)
            ).fetchone()

            # ==========================================
            # UTILISATEUR INTROUVABLE
            # ==========================================

            if utilisateur is None:
                raise ValueError(
                    "Utilisateur introuvable."
                )

            id_user, code, actif = utilisateur

            # ==========================================
            # UTILISATEUR DÉJÀ ACTIF
            # ==========================================

            if actif:
                raise ValueError(
                    "Cet utilisateur est déjà actif."
                )

            # ==========================================
            # RÉACTIVATION
            # ==========================================

            conn.execute(
                """
                UPDATE utilisateurs
                SET actif = 1
                WHERE id = ?
                """,
                (id_utilisateur,)
            )

            conn.commit()

            return True

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    @staticmethod
    def administrateur_existe():
        """
        Vérifie qu'au moins un Administrateur actif existe.
        """

        conn = get_connection()

        try:
            resultat = conn.execute(
                """
                SELECT 1
                FROM utilisateurs
                WHERE profil = 'Administrateur'
                  AND actif = 1
                LIMIT 1
                """
            ).fetchone()

            return resultat is not None

        finally:
            conn.close()

    @staticmethod
    def lister_utilisateurs(actifs_uniquement=True):
        """
        Retourne la liste des utilisateurs.

        Par défaut, seuls les utilisateurs actifs
        sont retournés.
        """

        conn = get_connection()

        try:

            if actifs_uniquement:

                lignes = conn.execute(
                    """
                    SELECT
                        id,
                        code,
                        nom,
                        prenom,
                        profil,
                        actif,
                        date_creation
                    FROM utilisateurs
                    WHERE actif = 1
                    ORDER BY nom, prenom
                    """
                ).fetchall()

            else:

                lignes = conn.execute(
                    """
                    SELECT
                        id,
                        code,
                        nom,
                        prenom,
                        profil,
                        actif,
                        date_creation
                    FROM utilisateurs
                    ORDER BY actif DESC, nom, prenom
                    """
                ).fetchall()

            return lignes

        finally:
            conn.close()

    @classmethod
    def creer_token_recuperation(cls, id_utilisateur):
        """
        Crée un token de récupération de mot de passe.

        Le token en clair n'est jamais enregistré en base.
        Seul son hash est conservé.

        Retourne :
            str : token en clair destiné à être transmis à l'utilisateur.
        """

        # Vérifier que l'utilisateur existe
        with get_connection() as conn:

            utilisateur = conn.execute(
                """
                SELECT id, profil, actif, email
                FROM utilisateurs
                WHERE id = ?
                """,
                (id_utilisateur,)
            ).fetchone()

        if utilisateur is None:
            raise ValueError("Utilisateur introuvable.")

        id_user, profil, actif, email = utilisateur

        # Vérifier que le compte est actif
        if not actif:
            raise ValueError("Le compte utilisateur est archivé.")

        # Vérifier qu'il s'agit bien d'un administrateur
        if profil != "Administrateur":
            raise ValueError(
                "La récupération du mot de passe est réservée aux administrateurs."
            )

        # Vérifier qu'une adresse e-mail existe
        if not email or not str(email).strip():
            raise ValueError(
                "Aucune adresse e-mail n'est associée à ce compte."
            )

        # Générer un token cryptographiquement sécurisé
        token = secrets.token_urlsafe(32)

        # Calculer son hash
        token_hash = hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

        # Dates de création et d'expiration
        date_creation = datetime.now()
        date_expiration = date_creation + timedelta(minutes=30)

        # Enregistrer uniquement le hash
        with get_connection() as conn:

            conn.execute(
                """
                INSERT INTO recuperations_mot_de_passe
                (
                    utilisateur_id,
                    token_hash,
                    date_creation,
                    date_expiration
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    id_user,
                    token_hash,
                    date_creation.isoformat(),
                    date_expiration.isoformat(),
                )
            )

            conn.commit()

        # Le token en clair n'existe qu'en mémoire
        # et sera transmis à l'étape d'envoi du mail.
        return token

    @classmethod
    def verifier_token_recuperation(cls, id_utilisateur, token):
        """
        Vérifie un token de récupération de mot de passe.

        Vérifie :
            - que le token est fourni ;
            - que l'utilisateur existe ;
            - que le token correspond ;
            - que le token n'est pas expiré ;
            - que le token n'a pas déjà été utilisé.

        Retourne :
            dict : informations sur la récupération si le token est valide.

        Lève :
            ValueError : si le token est invalide, expiré ou déjà utilisé.
        """

        if not token or not str(token).strip():
            raise ValueError(
                "Le token de récupération est obligatoire."
            )

        token = str(token).strip()

        # Calcul du hash du token reçu
        token_hash = hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

        with get_connection() as conn:

            recuperation = conn.execute(
                """
                SELECT
                    id,
                    utilisateur_id,
                    date_creation,
                    date_expiration,
                    date_utilisation
                FROM recuperations_mot_de_passe
                WHERE utilisateur_id = ?
                  AND token_hash = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    id_utilisateur,
                    token_hash,
                )
            ).fetchone()

        if recuperation is None:
            raise ValueError(
                "Token de récupération invalide."
            )

        (
            id_recuperation,
            utilisateur_id,
            date_creation,
            date_expiration,
            date_utilisation,
        ) = recuperation

        # Token déjà utilisé
        if date_utilisation is not None:
            raise ValueError(
                "Ce token de récupération a déjà été utilisé."
            )

        # Vérification de l'expiration
        try:
            expiration = datetime.fromisoformat(
                date_expiration
            )
        except (TypeError, ValueError):
            raise ValueError(
                "La date d'expiration du token est invalide."
            )

        if datetime.now() > expiration:
            raise ValueError(
                "Le token de récupération a expiré."
            )

        return {
            "id": id_recuperation,
            "utilisateur_id": utilisateur_id,
            "date_creation": date_creation,
            "date_expiration": date_expiration,
        }

    @classmethod
    def reinitialiser_mot_de_passe(
            cls,
            id_utilisateur,
            token,
            nouveau_mot_de_passe
    ):
        """
        Réinitialise le mot de passe d'un administrateur actif.

        La vérification et la consommation du token, ainsi que
        la modification du mot de passe, sont réalisées dans
        une même transaction SQLite.
        """

        cls._valider_mot_de_passe(nouveau_mot_de_passe)

        if not token or not str(token).strip():
            raise ValueError("Le token de récupération est obligatoire.")

        token = str(token).strip()
        token_hash = hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

        nouveau_hash = cls._hachage_mot_de_passe(
            nouveau_mot_de_passe
        )

        conn = get_connection()

        try:
            # Réserve l'accès en écriture avant de vérifier le token.
            conn.execute("BEGIN IMMEDIATE")

            utilisateur = conn.execute(
                """
                SELECT id, profil, actif
                FROM utilisateurs
                WHERE id = ?
                """,
                (id_utilisateur,)
            ).fetchone()

            if utilisateur is None:
                raise ValueError("Utilisateur introuvable.")

            _, profil, actif = utilisateur

            if not actif:
                raise ValueError("Le compte utilisateur est archivé.")

            if profil != "Administrateur":
                raise ValueError(
                    "La récupération du mot de passe "
                    "est réservée aux administrateurs."
                )

            recuperation = conn.execute(
                """
                SELECT id, date_expiration, date_utilisation
                FROM recuperations_mot_de_passe
                WHERE utilisateur_id = ?
                  AND token_hash = ?
                """,
                (id_utilisateur, token_hash)
            ).fetchone()

            if recuperation is None:
                raise ValueError("Token de récupération invalide.")

            id_recuperation, date_expiration, date_utilisation = recuperation

            if date_utilisation is not None:
                raise ValueError(
                    "Ce token de récupération a déjà été utilisé."
                )

            try:
                expiration = datetime.fromisoformat(date_expiration)
            except (TypeError, ValueError):
                raise ValueError(
                    "La date d'expiration du token est invalide."
                )

            maintenant = datetime.now()

            if maintenant > expiration:
                raise ValueError("Le token de récupération a expiré.")

            # Consommation conditionnelle : un seul appel peut réussir.
            curseur = conn.execute(
                """
                UPDATE recuperations_mot_de_passe
                SET date_utilisation = ?
                WHERE id = ?
                  AND utilisateur_id = ?
                  AND token_hash = ?
                  AND date_utilisation IS NULL
                  AND date_expiration > ?
                """,
                (
                    maintenant.isoformat(),
                    id_recuperation,
                    id_utilisateur,
                    token_hash,
                    maintenant.isoformat(),
                )
            )

            if curseur.rowcount != 1:
                raise ValueError(
                    "Token invalide, expiré ou déjà utilisé."
                )

            conn.execute(
                """
                UPDATE utilisateurs
                SET mot_de_passe_hash = ?
                WHERE id = ?
                """,
                (nouveau_hash, id_utilisateur)
            )

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

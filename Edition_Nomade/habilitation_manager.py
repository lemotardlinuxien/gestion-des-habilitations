import sqlite3

from config import DB


class HabilitationManager:
    """
    Gestion des habilitations configurables.
    """

    @staticmethod
    def lister():

        if not DB.exists():
            return []

        # Import local pour éviter une dépendance circulaire :
        # database.py importe également HabilitationManager.
        from database import get_connection

        conn = get_connection()

        try:

            cur = conn.cursor()

            cur.execute("""
                SELECT nom
                FROM habilitations_config
                WHERE active = 1
                ORDER BY ordre
            """)

            habilitations = [
                ligne[0]
                for ligne in cur.fetchall()
            ]

            return habilitations

        finally:
            conn.close()

    @staticmethod
    def lister_avec_details():
        # Import local pour éviter une dépendance circulaire avec database.py.
        from database import get_connection

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, nom, ordre, active
                FROM habilitations_config
                ORDER BY ordre
            """)
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def ajouter(nom):
        """
        Ajoute une nouvelle habilitation.

        L'ordre est automatiquement placé
        après la dernière habilitation.
        """

        nom = nom.strip()

        if not nom:
            return False, "Le nom de l'habilitation est vide."

        # Import local pour éviter une dépendance circulaire avec database.py.
        from database import get_connection

        conn = get_connection()
        cur = conn.cursor()

        try:

            # Vérifie les doublons comme pour les salariés : la comparaison
            # ignore la casse, les accents et les espaces superflus, sans
            # modifier le nom qui sera enregistré.
            from validation import normaliser_texte_comparaison

            cur.execute("SELECT nom FROM habilitations_config")
            noms_existants = [ligne[0] for ligne in cur.fetchall()]
            nom_compare = normaliser_texte_comparaison(nom)

            if any(
                normaliser_texte_comparaison(nom_existant) == nom_compare
                for nom_existant in noms_existants
            ):
                return False, (
                    f"L'habilitation « {nom} » existe déjà.\n\n"
                    "Aucun doublon n'a été créé. Vérifiez la liste des habilitations."
                )

            # Recherche du prochain ordre
            cur.execute("""
            SELECT COALESCE(MAX(ordre), 0) + 1
            FROM habilitations_config
            """)

            ordre = cur.fetchone()[0]

            # Ajout
            cur.execute("""
            INSERT INTO habilitations_config
            (
                nom,
                ordre,
                active
            )
            VALUES
            (
                ?, ?, 1
            )
            """, (
                nom,
                ordre
            ))

            conn.commit()

            return True, "Habilitation ajoutée."

        except sqlite3.Error as erreur:

            conn.rollback()

            return False, str(erreur)

        finally:

            conn.close()

    @staticmethod
    def ajouter_colonne_habilitation(nom):
        """
        Ajoute une colonne dans la table habilitations
        pour une nouvelle habilitation.
        """

        # Import local pour éviter une dépendance circulaire avec database.py.
        from database import get_connection

        conn = get_connection()
        cur = conn.cursor()

        try:

            # Vérifie si la colonne existe déjà
            cur.execute("""
                PRAGMA table_info(habilitations)
            """)

            colonnes = [
                ligne[1]
                for ligne in cur.fetchall()
            ]

            if nom in colonnes:
                return True

            # Ajout de la nouvelle colonne
            nom_sql = str(nom).replace('"', '""')
            cur.execute(
                f'ALTER TABLE habilitations ADD COLUMN "{nom_sql}" TEXT'
            )

            conn.commit()

            return True

        except sqlite3.Error:

            conn.rollback()

            return False

        finally:

            conn.close()

    @staticmethod

    @staticmethod
    def renommer(id_hab, nouveau_nom):
        """Renomme une habilitation et sa colonne SQLite sans perdre les valeurs."""
        nouveau_nom = str(nouveau_nom or "").strip()
        if not nouveau_nom:
            return False, "Le nom de l'habilitation est vide."

        # Import local pour éviter une dépendance circulaire avec database.py.
        from database import get_connection

        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT nom FROM habilitations_config WHERE id = ?", (id_hab,))
            resultat = cur.fetchone()
            if not resultat:
                return False, "Habilitation introuvable."

            ancien_nom = resultat[0]
            if ancien_nom == nouveau_nom:
                return True, "Aucune modification nécessaire."

            # Même règle de comparaison que lors de l'ajout : casse,
            # accents et espaces superflus sont ignorés pour détecter un doublon.
            from validation import normaliser_texte_comparaison

            cur.execute(
                "SELECT id, nom FROM habilitations_config WHERE id <> ?",
                (id_hab,)
            )
            autres_noms = [ligne[1] for ligne in cur.fetchall()]
            nom_compare = normaliser_texte_comparaison(nouveau_nom)
            if any(
                normaliser_texte_comparaison(nom_existant) == nom_compare
                for nom_existant in autres_noms
            ):
                return False, (
                    f"L'habilitation « {nouveau_nom} » existe déjà.\n\n"
                    "Choisissez un nom différent. Aucune modification n'a été effectuée."
                )

            cur.execute('PRAGMA table_info("habilitations")')
            colonnes = [ligne[1] for ligne in cur.fetchall()]
            colonnes_fold = {col.casefold(): col for col in colonnes}
            ancienne_colonne = colonnes_fold.get(ancien_nom.casefold())
            nouvelle_colonne = colonnes_fold.get(nouveau_nom.casefold())

            if nouvelle_colonne and (
                ancienne_colonne is None
                or nouvelle_colonne.casefold() != ancienne_colonne.casefold()
            ):
                return False, (
                    "Une colonne portant ce nom existe déjà dans les données. "
                    "Aucune modification n'a été effectuée."
                )

            def citer_identifiant(nom):
                return '"' + str(nom).replace('"', '""') + '"'

            if ancienne_colonne:
                if ancien_nom.casefold() == nouveau_nom.casefold() and ancien_nom != nouveau_nom:
                    temporaire = f"__renommage_habilitation_{id_hab}__"
                    suffixe = 1
                    while temporaire.casefold() in colonnes_fold:
                        temporaire = f"__renommage_habilitation_{id_hab}_{suffixe}__"
                        suffixe += 1
                    cur.execute(
                        f"ALTER TABLE habilitations RENAME COLUMN "
                        f"{citer_identifiant(ancienne_colonne)} TO {citer_identifiant(temporaire)}"
                    )
                    cur.execute(
                        f"ALTER TABLE habilitations RENAME COLUMN "
                        f"{citer_identifiant(temporaire)} TO {citer_identifiant(nouveau_nom)}"
                    )
                elif ancienne_colonne != nouveau_nom:
                    cur.execute(
                        f"ALTER TABLE habilitations RENAME COLUMN "
                        f"{citer_identifiant(ancienne_colonne)} TO {citer_identifiant(nouveau_nom)}"
                    )
            else:
                cur.execute(
                    f"ALTER TABLE habilitations ADD COLUMN {citer_identifiant(nouveau_nom)} TEXT"
                )

            cur.execute(
                "UPDATE habilitations_config SET nom = ? WHERE id = ?",
                (nouveau_nom, id_hab)
            )
            conn.commit()
            return True, (
                f"Habilitation renommée : « {ancien_nom} » → « {nouveau_nom} ». "
                "Les données existantes ont été conservées."
            )
        except sqlite3.Error as erreur:
            conn.rollback()
            return False, f"Renommage impossible : {erreur}"
        finally:
            conn.close()

    def supprimer(id_hab):
        # Import local pour éviter une dépendance circulaire avec database.py.
        from database import get_connection

        conn = get_connection()
        cur = conn.cursor()

        try:

            # ==========================================
            # Récupération du nom
            # ==========================================

            cur.execute(
                """
                SELECT nom
                FROM habilitations_config
                WHERE id = ?
                """,
                (id_hab,)
            )

            resultat = cur.fetchone()

            if not resultat:
                return (
                    False,
                    "Habilitation introuvable."
                )

            nom = resultat[0]

            # ==========================================
            # Suppression de la colonne SQLite
            # ==========================================

            cur.execute(
                """
                PRAGMA table_info(habilitations)
                """
            )

            colonnes = [
                ligne[1]
                for ligne in cur.fetchall()
            ]

            if nom in colonnes:

                nom_sql = nom.replace(
                    '"',
                    '""'
                )

                cur.execute(
                    f'''
                    ALTER TABLE habilitations
                    DROP COLUMN "{nom_sql}"
                    '''
                )

            # ==========================================
            # Suppression configuration
            # ==========================================

            cur.execute(
                """
                DELETE FROM habilitations_config
                WHERE id = ?
                """,
                (id_hab,)
            )

            # ==========================================
            # Validation
            # ==========================================

            conn.commit()

            # ==========================================
            # Vérification APRÈS COMMIT
            # ==========================================

            cur.execute(
                """
                SELECT id, nom, ordre, active
                FROM habilitations_config
                ORDER BY ordre
                """
            )

            cur.execute(
                """
                PRAGMA table_info(habilitations)
                """
            )

            return (
                True,
                f"Habilitation '{nom}' supprimée."
            )

        except sqlite3.Error as erreur:

            conn.rollback()

            return (
                False,
                str(erreur)
            )

        finally:

            conn.close()

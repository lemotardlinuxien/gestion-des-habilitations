import unicodedata
import sqlite3
import pandas as pd
from config import (
    DB,
    COLONNES_TECHNIQUES
)
from habilitation_manager import HabilitationManager

# ==========================================
# CONFIG
# ==========================================


def get_connection():
    """
    Retourne une connexion SQLite vers la base de données de l'application.

    Toute connexion SQLite doit passer par cette fonction afin de
    centraliser l'accès à la base.
    """
    DB.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    return sqlite3.connect(DB)

def initialiser_tables_systeme():
    """
    Initialise les tables SQLite indépendantes
    des données Excel.

    Ces tables doivent exister dès le démarrage
    de l'application, même si la base de données
    vient d'être créée.
    """

    conn = get_connection()

    try:
        cur = conn.cursor()

        # ==========================================
        # CONFIGURATION DES HABILITATIONS
        # ==========================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS habilitations_config
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL UNIQUE,
                ordre INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )
        """)

        # ==========================================
        # UTILISATEURS
        # ==========================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS utilisateurs
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                nom TEXT NOT NULL,
                prenom TEXT NOT NULL,
                profil TEXT NOT NULL,
                mot_de_passe_hash TEXT,
                email TEXT,
                actif INTEGER NOT NULL DEFAULT 1,
                date_creation TEXT NOT NULL
            )
        """)

        # ==========================================
        # MIGRATION : EMAIL UTILISATEUR
        # ==========================================

        colonnes_utilisateurs = {
            ligne[1]
            for ligne in cur.execute(
                "PRAGMA table_info(utilisateurs)"
            ).fetchall()
        }

        if "email" not in colonnes_utilisateurs:
            cur.execute(
                "ALTER TABLE utilisateurs ADD COLUMN email TEXT"
            )

        # ==========================================
        # RÉCUPÉRATION MOT DE PASSE
        # ==========================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS recuperations_mot_de_passe
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                utilisateur_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                date_creation TEXT NOT NULL,
                date_expiration TEXT NOT NULL,
                date_utilisation TEXT,
                FOREIGN KEY (utilisateur_id)
                    REFERENCES utilisateurs(id)
                    ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_recuperations_mdp_utilisateur
            ON recuperations_mot_de_passe(utilisateur_id)
        """)

        # ==========================================
        # MAILS PAR SECTEUR
        # ==========================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS mails_secteurs
            (
                secteur TEXT PRIMARY KEY,
                email TEXT
            )
        """)

        # ==========================================
        # PARAMÈTRES MAIL
        # ==========================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS parametres_mail
            (
                id INTEGER PRIMARY KEY,
                expediteur TEXT,
                smtp_serveur TEXT,
                smtp_port INTEGER,
                delai_alerte INTEGER DEFAULT 45
            )
        """)

        # ==========================================
        # MIGRATION DE L'ANCIENNE COLONNE MOT DE PASSE
        # ==========================================

        cur.execute("PRAGMA table_info(parametres_mail)")
        colonnes_parametres_mail = {
            ligne[1]
            for ligne in cur.fetchall()
        }

        if "mot_de_passe" in colonnes_parametres_mail:
            cur.execute("""
                CREATE TABLE parametres_mail_new
                (
                    id INTEGER PRIMARY KEY,
                    expediteur TEXT,
                    smtp_serveur TEXT,
                    smtp_port INTEGER,
                    delai_alerte INTEGER DEFAULT 45
                )
            """)

            cur.execute("""
                INSERT INTO parametres_mail_new
                (
                    id,
                    expediteur,
                    smtp_serveur,
                    smtp_port,
                    delai_alerte
                )
                SELECT
                    id,
                    expediteur,
                    smtp_serveur,
                    smtp_port,
                    delai_alerte
                FROM parametres_mail
            """)

            cur.execute("DROP TABLE parametres_mail")

            cur.execute("""
                ALTER TABLE parametres_mail_new
                RENAME TO parametres_mail
            """)

        cur.execute("""
            INSERT OR IGNORE INTO parametres_mail
            (
                id,
                expediteur,
                smtp_serveur,
                smtp_port,
                delai_alerte
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            1,
            "",
            "smtp.gmail.com",
            465,
            45
        ))

        # ==========================================
        # HISTORIQUE DES ENVOIS
        # ==========================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS historique_envois
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_envoi TEXT,
                secteur TEXT,
                destinataire TEXT,
                fichier TEXT
            )
        """)

        # ==========================================
        # HISTORIQUE DES MAILS
        # ==========================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS historique_mails
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_heure TEXT NOT NULL,
                secteur TEXT,
                destinataire TEXT,
                objet TEXT,
                nombre_habilitations INTEGER,
                statut TEXT,
                message_erreur TEXT
            )
        """)

        conn.commit()

    finally:
        conn.close()

def initialiser_base_vide():
    """
    Initialise une base SQLite vide.

    Cette fonction crée uniquement la structure minimale
    nécessaire à la gestion manuelle des salariés.

    Elle :
        - crée la table métier 'habilitations' si nécessaire ;
        - ne crée aucun salarié ;
        - ne crée aucune habilitation ;
        - ne supprime aucune donnée existante.
    """

    conn = get_connection()

    try:

        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS habilitations
            (
                "ID" TEXT PRIMARY KEY,
                "Secteur" TEXT,
                "Nom" TEXT,
                "Prénom" TEXT
            )
        """)

        conn.commit()

    finally:

        conn.close()

def _convertir_valeur_sqlite(valeur):
    """
    Convertit une valeur Python/pandas pour SQLite.

    Règles :
        - valeur vide / NaN → None
        - date / datetime → YYYY-MM-DD
        - autres valeurs → conservées si SQLite sait les gérer
        - valeurs inconnues → chaîne de caractères
    """

    if pd.isna(valeur):
        return None

    if hasattr(valeur, "strftime"):
        return valeur.strftime("%Y-%m-%d")

    if isinstance(
        valeur,
        (str, int, float, bytes)
    ):
        return valeur

    return str(valeur)


def normaliser_colonnes(df):
    """
    Normalise les noms de colonnes Excel.

    Les colonnes techniques de l'application sont reconnues
    indépendamment de la casse et des accents.

    Les habilitations sont récupérées dynamiquement depuis
    HabilitationManager.

    Une colonne inconnue est conservée telle quelle afin que
    ImportEngine puisse éventuellement la créer comme nouvelle
    habilitation.
    """

    df = df.copy()

    def cle_normalisee(nom):
        """
        Produit une clé comparable :
        - suppression des espaces autour
        - suppression des accents
        - comparaison insensible à la casse
        """

        texte = str(nom).strip()

        texte = unicodedata.normalize(
            "NFKD",
            texte
        )

        texte = "".join(
            caractere
            for caractere in texte
            if not unicodedata.combining(caractere)
        )

        return texte.casefold()

    # ==========================================
    # COLONNES TECHNIQUES
    # ==========================================

    colonnes_techniques = {
        cle_normalisee(colonne): colonne
        for colonne in COLONNES_TECHNIQUES
    }

    # ==========================================
    # HABILITATIONS CONFIGURÉES
    # ==========================================

    habilitations = HabilitationManager.lister()

    mapping_habilitations = {
        cle_normalisee(habilitation): habilitation
        for habilitation in habilitations
    }

    # ==========================================
    # NORMALISATION
    # ==========================================

    nouvelles_colonnes = []

    for colonne in df.columns:

        colonne_originale = str(colonne).strip()

        cle = cle_normalisee(
            colonne_originale
        )

        # ------------------------------
        # Colonne technique
        # ------------------------------

        if cle in colonnes_techniques:

            nouvelles_colonnes.append(
                colonnes_techniques[cle]
            )

            continue

        # ------------------------------
        # Habilitation configurée
        # ------------------------------

        if cle in mapping_habilitations:

            nouvelles_colonnes.append(
                mapping_habilitations[cle]
            )

            continue

        # ------------------------------
        # Nouvelle colonne
        # ------------------------------

        nouvelles_colonnes.append(
            colonne_originale
        )

    # ==========================================
    # GESTION DES DOUBLONS
    # ==========================================

    colonnes_finales = []
    compteurs = {}

    for colonne in nouvelles_colonnes:

        # Clé insensible à la casse
        cle = cle_normalisee(colonne)

        if cle not in compteurs:
            compteurs[cle] = 1
            colonnes_finales.append(colonne)

            continue

        compteur = compteurs[cle]
        nouvelle_colonne = f"{colonne}_{compteur}"

        cles_existantes = {
            cle_normalisee(c)
            for c in colonnes_finales
        }

        while cle_normalisee(nouvelle_colonne) in cles_existantes:
            compteur += 1
            nouvelle_colonne = f"{colonne}_{compteur}"

        compteurs[cle] = compteur + 1

        colonnes_finales.append(
            nouvelle_colonne
        )

    df.columns = colonnes_finales

    return df

# ==========================================
# LECTURE DONNEES
# ==========================================

def lire_donnees():
    """
    Lit les données de la base SQLite.

    Cette fonction est strictement en lecture :
    elle ne crée jamais la base si elle n'existe pas.
    """

    # ==========================================
    # Base inexistante
    # ==========================================

    if not DB.exists():
        return pd.DataFrame()

    # ==========================================
    # Lecture SQLite
    # ==========================================

    conn = get_connection()

    try:
        # ==========================================
        # Vérifier l'existence de la table métier
        # ==========================================

        table = conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'habilitations'
        """).fetchone()

        if table is None:
            return pd.DataFrame()

        # ==========================================
        # Lecture des données
        # ==========================================

        df = pd.read_sql_query(
            "SELECT * FROM habilitations",
            conn
        )

        return df

    finally:
        conn.close()


# ==========================================
# SAUVEGARDE DATAFRAME
# ==========================================

def sauvegarder_dataframe(df):
    """
    Sauvegarde le DataFrame dans SQLite.

    Les colonnes sauvegardées sont limitées aux colonnes
    techniques et aux habilitations actuellement actives.

    Les colonnes manquantes dans SQLite sont ajoutées
    automatiquement.

    La sauvegarde est transactionnelle :
    en cas d'erreur, aucune modification partielle
    n'est conservée.
    """

    if df is None:
        raise ValueError(
            "Le DataFrame à sauvegarder ne peut pas être None."
        )

    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            "La sauvegarde attend un pandas.DataFrame."
        )

    conn = get_connection()

    try:
        cur = conn.cursor()

        # ==========================================
        # HABILITATIONS ACTUELLEMENT ACTIVES
        # ==========================================

        habilitations = HabilitationManager.lister()

        # ==========================================
        # COLONNES AUTORISÉES
        # ==========================================

        colonnes_autorisees = [
            *COLONNES_TECHNIQUES,
            *habilitations
        ]

        # Évite d'éventuels doublons
        colonnes_autorisees = list(
            dict.fromkeys(colonnes_autorisees)
        )

        # ==========================================
        # NETTOYAGE DU DATAFRAME
        # ==========================================

        df_sauvegarde = df.reindex(
            columns=colonnes_autorisees
        ).copy()

        # ==========================================
        # VÉRIFICATION DE LA TABLE
        # ==========================================

        cur.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'habilitations'
        """)

        if cur.fetchone() is None:
            raise RuntimeError(
                "La table 'habilitations' n'existe pas."
            )

        # ==========================================
        # COLONNES ACTUELLES SQLITE
        # ==========================================

        cur.execute("""
            PRAGMA table_info(habilitations)
        """)

        colonnes_sqlite = {
            ligne[1]
            for ligne in cur.fetchall()
        }

        # ==========================================
        # AJOUT DES COLONNES MANQUANTES
        # ==========================================

        for colonne in colonnes_autorisees:

            if colonne not in colonnes_sqlite:

                nom_sql = colonne.replace(
                    '"',
                    '""'
                )

                cur.execute(
                    f'''
                    ALTER TABLE habilitations
                    ADD COLUMN "{nom_sql}" TEXT
                    '''
                )

        # ==========================================
        # SUPPRESSION DES ANCIENNES DONNÉES
        # ==========================================

        cur.execute(
            "DELETE FROM habilitations"
        )

        # ==========================================
        # ENREGISTREMENT DU DATAFRAME
        # ==========================================

        if not df_sauvegarde.empty:

            df_sauvegarde.to_sql(
                "habilitations",
                conn,
                if_exists="append",
                index=False
            )

        # ==========================================
        # VALIDATION DE LA TRANSACTION
        # ==========================================

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()



def appliquer_operations(
        operations,
        nouvelles_habilitations=None,
        ordre_habilitations=None
):
    """
    Applique les opérations d'import dans SQLite.

    Toutes les opérations sont exécutées dans UNE SEULE
    transaction SQLite.

    Si toutes les opérations réussissent :
        COMMIT

    Si une seule opération échoue :
        ROLLBACK

    Les opérations possibles sont :

        INSERT
        UPDATE

    Les opérations suivantes ne sont jamais appliquées :

        DOUBLON
        AMBIGU

    IMPORTANT :
        Cette fonction est appelée uniquement après validation
        explicite de l'import par l'utilisateur.
    """

    nouvelles_habilitations = (
        nouvelles_habilitations or []
    )

    ordre_habilitations = (
        ordre_habilitations or []
    )

    conn = get_connection()
    cur = conn.cursor()

    try:

        # ==================================================
        # 1. VÉRIFICATION DE LA STRUCTURE SQLITE
        # ==================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS habilitations_config
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL UNIQUE,
                ordre INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS habilitations
            (
                "ID" TEXT PRIMARY KEY,
                "Secteur" TEXT,
                "Nom" TEXT,
                "Prénom" TEXT
            )
        """)

        # ==================================================
        # 2. CRÉATION DES NOUVELLES HABILITATIONS
        # ==================================================

        for nom in nouvelles_habilitations:

            nom = str(nom).strip()

            if not nom:
                continue

            # ----------------------------------------------
            # Vérifier si l'habilitation existe déjà
            # ----------------------------------------------

            cur.execute("""
                SELECT id
                FROM habilitations_config
                WHERE LOWER(nom) = LOWER(?)
            """, (nom,))

            resultat = cur.fetchone()

            if resultat:
                continue

            # ----------------------------------------------
            # Déterminer l'ordre
            # ----------------------------------------------

            cur.execute("""
                SELECT COALESCE(MAX(ordre), 0) + 1
                FROM habilitations_config
            """)

            ordre = cur.fetchone()[0]

            # ----------------------------------------------
            # Ajouter dans la configuration
            # ----------------------------------------------

            cur.execute("""
                INSERT INTO habilitations_config
                (
                    nom,
                    ordre,
                    active
                )
                VALUES (?, ?, 1)
            """, (
                nom,
                ordre
            ))

            # ----------------------------------------------
            # Ajouter la colonne SQLite
            # ----------------------------------------------

            nom_sql = nom.replace(
                '"',
                '""'
            )

            cur.execute(
                f'''
                ALTER TABLE habilitations
                ADD COLUMN "{nom_sql}" TEXT
                '''
            )

        # ==================================================
        # 3. MISE À JOUR DE L'ORDRE DES HABILITATIONS
        # ==================================================

        if ordre_habilitations:

            # --------------------------------------------------
            # Habilitations actuellement actives en SQLite
            # --------------------------------------------------

            cur.execute("""
                SELECT nom
                FROM habilitations_config
                WHERE active = 1
                ORDER BY ordre
            """)

            habilitations_existantes = [
                ligne[0]
                for ligne in cur.fetchall()
            ]

            # --------------------------------------------------
            # Ordre final :
            # 1. habilitations présentes dans Excel
            # 2. habilitations existantes absentes d'Excel
            # --------------------------------------------------

            ordre_final = []

            for habilitation in ordre_habilitations:

                if habilitation not in ordre_final:
                    ordre_final.append(habilitation)

            for habilitation in habilitations_existantes:

                if habilitation not in ordre_final:
                    ordre_final.append(habilitation)

            # --------------------------------------------------
            # Application de l'ordre
            # --------------------------------------------------

            for position, habilitation in enumerate(
                ordre_final,
                start=1
            ):

                cur.execute("""
                    UPDATE habilitations_config
                    SET ordre = ?
                    WHERE LOWER(nom) = LOWER(?)
                      AND active = 1
                """, (
                    position,
                    str(habilitation).strip()
                ))

        # ==================================================
        # 4. RÉCUPÉRER LES HABILITATIONS ACTIVES
        # ==================================================

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

        # ==================================================
        # 4. VÉRIFICATION DU SCHÉMA
        # ==================================================

        cur.execute("""
            PRAGMA table_info(habilitations)
        """)

        colonnes_sqlite = {
            ligne[1]
            for ligne in cur.fetchall()
        }

        # Sécurité supplémentaire :
        # toutes les habilitations configurées doivent
        # posséder leur colonne SQLite.

        for colonne in habilitations:

            if colonne in colonnes_sqlite:
                continue

            nom_sql = colonne.replace(
                '"',
                '""'
            )

            cur.execute(
                f'''
                ALTER TABLE habilitations
                ADD COLUMN "{nom_sql}" TEXT
                '''
            )

        # ==================================================
        # 5. APPLICATION DES OPÉRATIONS
        # ==================================================

        nb_ajoutes = 0
        nb_modifies = 0

        for operation in operations:

            action = operation.get(
                "action"
            )

            # ----------------------------------------------
            # Les doublons et ambiguïtés sont volontairement
            # exclus de l'application automatique.
            # ----------------------------------------------

            if action in {
                "DOUBLON",
                "AMBIGU"
            }:
                continue

            donnees = operation.get(
                "donnees",
                {}
            )

            # ==================================================
            # INSERT
            # ==================================================

            if action == "INSERT":

                id_valeur = str(
                    operation.get(
                        "id",
                        donnees.get("ID", "")
                    )
                ).strip()

                if not id_valeur:
                    raise ValueError(
                        "Impossible d'insérer un salarié "
                        "sans ID."
                    )

                donnees = {
                    **donnees,
                    "ID": id_valeur
                }

                colonnes = [
                    *COLONNES_TECHNIQUES,
                    *habilitations
                ]

                valeurs = tuple(
                    _convertir_valeur_sqlite(
                        donnees.get(
                            colonne,
                            ""
                        )
                    )
                    for colonne in colonnes
                )

                colonnes_sql = ", ".join(
                    f'"{colonne.replace(chr(34), chr(34) * 2)}"'
                    for colonne in colonnes
                )

                placeholders = ", ".join(
                    "?"
                    for _ in colonnes
                )

                cur.execute(
                    f"""
                    INSERT INTO habilitations
                    (
                        {colonnes_sql}
                    )
                    VALUES
                    (
                        {placeholders}
                    )
                    """,
                    valeurs
                )

                nb_ajoutes += 1

                continue

            # ==================================================
            # UPDATE
            # ==================================================

            if action == "UPDATE":

                id_valeur = str(
                    operation.get(
                        "id",
                        ""
                    )
                ).strip()

                if not id_valeur:
                    raise ValueError(
                        "Impossible de mettre à jour "
                        "un salarié sans ID."
                    )

                modifications = []
                valeurs = []

                # ----------------------------------------------
                # Colonnes techniques + habilitations
                # ----------------------------------------------

                colonnes = [
                    "Secteur",
                    "Nom",
                    "Prénom",
                    *habilitations
                ]

                for colonne in colonnes:

                    valeur = donnees.get(
                        colonne,
                        ""
                    )

                    if pd.isna(valeur):
                        continue

                    if isinstance(
                            valeur,
                            str
                    ):
                        valeur = valeur.strip()

                        # Une cellule vide ne remplace
                        # jamais une donnée existante.
                        if valeur == "":
                            continue

                    valeur = _convertir_valeur_sqlite(
                        valeur
                    )

                    nom_sql = colonne.replace(
                        '"',
                        '""'
                    )

                    modifications.append(
                        f'"{nom_sql}"=?'
                    )

                    valeurs.append(
                        valeur
                    )

                # ----------------------------------------------
                # Rien à modifier
                # ----------------------------------------------

                if not modifications:
                    continue

                # ----------------------------------------------
                # UPDATE
                # ----------------------------------------------

                sql = f"""
                    UPDATE habilitations
                    SET {", ".join(modifications)}
                    WHERE ID=?
                """

                cur.execute(
                    sql,
                    tuple(valeurs) + (
                        id_valeur,
                    )
                )

                if cur.rowcount != 1:
                    raise RuntimeError(
                        "Le salarié à mettre à jour est introuvable "
                        f"dans SQLite (ID : {id_valeur})."
                    )

                nb_modifies += 1

                continue

            # ==================================================
            # ACTION INCONNUE
            # ==================================================

            raise ValueError(
                f"Action d'import inconnue : {action}"
            )

        # ==================================================
        # 6. VALIDATION DE LA TRANSACTION
        # ==================================================

        conn.commit()

        return {
            "ajoutes": nb_ajoutes,
            "modifies": nb_modifies,
        }

    except Exception:

        # ==================================================
        # ERREUR → ANNULATION COMPLÈTE
        # ==================================================

        conn.rollback()

        raise

    finally:

        conn.close()

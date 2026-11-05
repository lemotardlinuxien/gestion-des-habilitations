"""
Repository SQLite dédié à la gestion des mails.

Ce module regroupe uniquement les accès à la base de données
concernant :

- les adresses mails par secteur ;
- l'historique des envois ;
- les paramètres SMTP ;
- l'historique des mails ;
- le délai d'alerte.

Aucune logique graphique ou SMTP ne doit être placée ici.
"""

from datetime import datetime

import pandas as pd
import keyring

from database import get_connection

SERVICE_KEYRING = "gestion_habilitations_smtp"
COMPTE_KEYRING = "expediteur"


# ============================================================
# MAILS PAR SECTEUR
# ============================================================

def enregistrer_mail_secteur(secteur, email):
    """
    Enregistre, met à jour ou supprime l'adresse mail d'un secteur.
    """
    secteur = str(secteur).strip()
    email = str(email).strip()

    if not secteur:
        raise ValueError("Le secteur est obligatoire.")

    with get_connection() as conn:

        if not email:
            conn.execute(
                """
                DELETE FROM mails_secteurs
                WHERE secteur = ?
                """,
                (secteur,),
            )

        else:
            conn.execute(
                """
                INSERT INTO mails_secteurs (secteur, email)
                VALUES (?, ?)
                ON CONFLICT(secteur)
                DO UPDATE SET email = excluded.email
                """,
                (secteur, email),
            )

        conn.commit()


def recuperer_mails_secteurs():
    """
    Retourne les adresses mails associées aux secteurs.

    Retour :
        dict[str, str]
    """
    with get_connection() as conn:

        curseur = conn.execute(
            """
            SELECT secteur, email
            FROM mails_secteurs
            ORDER BY secteur
            """
        )

        return {
            ligne[0]: ligne[1]
            for ligne in curseur.fetchall()
        }

def synchroniser_secteurs_mails():
    """
    Synchronise mails_secteurs avec les secteurs réellement utilisés
    par au moins un salarié dans la table habilitations.

    - Ajoute les secteurs actifs sans adresse avec une adresse vide.
    - Conserve les adresses des secteurs toujours actifs.
    - Supprime les secteurs auxquels aucun salarié n'est affilié.
    - Compare les noms sans tenir compte de la casse, des accents
      ou des espaces superflus, puis adopte le libellé actuel du secteur.

    L'ensemble des changements est effectué dans une transaction.
    """
    from validation import normaliser_texte_comparaison

    with get_connection() as conn:
        secteurs_lignes = conn.execute(
            """
            SELECT DISTINCT TRIM(Secteur)
            FROM habilitations
            WHERE Secteur IS NOT NULL
              AND TRIM(Secteur) <> ''
            ORDER BY TRIM(Secteur)
            """
        ).fetchall()

        secteurs_actifs = {}
        for (secteur,) in secteurs_lignes:
            cle = normaliser_texte_comparaison(secteur)
            if cle and cle not in secteurs_actifs:
                secteurs_actifs[cle] = secteur

        lignes_existantes = conn.execute(
            "SELECT secteur, email FROM mails_secteurs ORDER BY secteur"
        ).fetchall()

        emails_existants = {}
        for secteur, email in lignes_existantes:
            cle = normaliser_texte_comparaison(secteur)
            if not cle:
                continue
            # Si plusieurs anciennes lignes ne diffèrent que par la casse,
            # les accents ou les espaces, préférer le libellé canonique.
            if cle not in emails_existants or secteur == secteurs_actifs.get(cle):
                emails_existants[cle] = email or ''

        # Reconstituer la table à partir des secteurs actifs uniquement.
        # Le DELETE et les INSERT sont atomiques dans cette transaction.
        conn.execute("DELETE FROM mails_secteurs")
        for cle, secteur in secteurs_actifs.items():
            conn.execute(
                "INSERT INTO mails_secteurs (secteur, email) VALUES (?, ?)",
                (secteur, emails_existants.get(cle, '')),
            )

        conn.commit()

# ============================================================
# HISTORIQUE DES ENVOIS
# ============================================================

def enregistrer_envoi(secteur, destinataire, fichier):
    """
    Enregistre un envoi de fichier dans l'historique.
    """
    date_envoi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO historique_envois
            (
                date_envoi,
                secteur,
                destinataire,
                fichier
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                date_envoi,
                secteur,
                destinataire,
                fichier,
            ),
        )

        conn.commit()


def lire_historique_envois():
    """
    Retourne l'historique des envois.

    Retour :
        liste de tuples
    """
    with get_connection() as conn:

        curseur = conn.execute(
            """
            SELECT
                id,
                date_envoi,
                secteur,
                destinataire,
                fichier
            FROM historique_envois
            ORDER BY id DESC
            """
        )

        return curseur.fetchall()


# ============================================================
# PARAMÈTRES MAIL
# ============================================================

def recuperer_parametres_mail():
    """
    Retourne les paramètres mail sous forme de dictionnaire.

    Les paramètres généraux sont récupérés depuis SQLite.

    Le mot de passe SMTP est récupéré depuis le gestionnaire
    sécurisé du système via keyring.

    La clé "mot_de_passe" est conservée dans le dictionnaire
    afin de rester compatible avec les modules existants.
    """

    with get_connection() as conn:

        curseur = conn.execute(
            """
            SELECT
                expediteur,
                smtp_serveur,
                smtp_port,
                delai_alerte
            FROM parametres_mail
            WHERE id = 1
            """
        )

        ligne = curseur.fetchone()

    if ligne is None:
        return None

    expediteur = ligne[0]

    mot_de_passe = keyring.get_password(
        SERVICE_KEYRING,
        COMPTE_KEYRING
    )

    return {
        "expediteur": expediteur,
        "mot_de_passe": mot_de_passe or "",
        "smtp_serveur": ligne[1],
        "smtp_port": ligne[2],
        "delai_alerte": ligne[3],
    }


def sauvegarder_parametres_mail(
    expediteur,
    mot_de_passe,
    smtp_serveur,
    smtp_port,
    delai_alerte=45,
):
    """
    Enregistre les paramètres de connexion mail.

    Les paramètres généraux sont enregistrés dans SQLite.

    Le mot de passe SMTP est enregistré dans le gestionnaire
    sécurisé du système via keyring.

    Si aucun nouveau mot de passe n'est fourni, le mot de passe
    actuellement présent dans Keyring est conservé.
    """

    expediteur = str(expediteur).strip()
    mot_de_passe = str(mot_de_passe)
    smtp_serveur = str(smtp_serveur).strip()

    try:
        smtp_port = int(smtp_port)
    except (TypeError, ValueError):
        raise ValueError("Le port SMTP doit être un nombre entier.")

    try:
        delai_alerte = int(delai_alerte)
    except (TypeError, ValueError):
        raise ValueError(
            "Le délai d'alerte doit être un nombre entier."
        )

    # ==========================================
    # MOT DE PASSE SMTP
    # ==========================================

    if mot_de_passe.strip():
        keyring.set_password(
            SERVICE_KEYRING,
            COMPTE_KEYRING,
            mot_de_passe
        )

    # ==========================================
    # PARAMÈTRES NON SENSIBLES
    # ==========================================

    with get_connection() as conn:

        conn.execute(
            """
            INSERT INTO parametres_mail
            (
                id,
                expediteur,
                smtp_serveur,
                smtp_port,
                delai_alerte
            )
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id)
            DO UPDATE SET
                expediteur = excluded.expediteur,
                smtp_serveur = excluded.smtp_serveur,
                smtp_port = excluded.smtp_port,
                delai_alerte = excluded.delai_alerte
            """,
            (
                expediteur,
                smtp_serveur,
                smtp_port,
                delai_alerte,
            ),
        )

        conn.commit()


def recuperer_jours_alerte():
    """
    Retourne le nombre de jours utilisé pour les alertes.

    Si aucun paramètre n'est enregistré, retourne 45.
    """

    parametres = recuperer_parametres_mail()

    if not parametres:
        return 45

    delai = parametres.get("delai_alerte")

    if delai is None:
        return 45

    try:
        return int(delai)

    except (TypeError, ValueError):
        return 45


# ============================================================
# HISTORIQUE DES MAILS
# ============================================================

def enregistrer_historique_mail(
    secteur,
    destinataire,
    objet,
    nombre_habilitations,
    statut,
    message_erreur=None,
):
    """
    Enregistre le résultat d'un envoi de mail.

    La date et l'heure sont générées automatiquement.
    """

    date_heure = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    with get_connection() as conn:

        conn.execute(
            """
            INSERT INTO historique_mails
            (
                date_heure,
                secteur,
                destinataire,
                objet,
                nombre_habilitations,
                statut,
                message_erreur
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date_heure,
                secteur,
                destinataire,
                objet,
                nombre_habilitations,
                statut,
                message_erreur,
            ),
        )

        conn.commit()


def lire_historique_mails():
    """
    Retourne l'historique des mails sous forme de DataFrame.

    Le format DataFrame est conservé afin de rester compatible
    avec l'interface graphique existante.
    """

    with get_connection() as conn:

        df = pd.read_sql_query(
            """
            SELECT
                id,
                date_heure,
                secteur,
                destinataire,
                objet,
                nombre_habilitations,
                statut,
                message_erreur
            FROM historique_mails
            ORDER BY id DESC
            """,
            conn,
        )

    return df


import sqlite3

from datetime import datetime
from pathlib import Path

from config import DB, DOSSIER_SAUVEGARDES
from logger_manager import log_info

from utilisateur_manager import UtilisateurManager

from mail_manager import (
    ouvrir_smtp,
    fermer_smtp,
    envoyer_mail,
)

from mail_repository import recuperer_parametres_mail


NOMBRE_SAUVEGARDES_AUTOMATIQUES = 2


def conserver_dernieres_sauvegardes(dossier):
    """
    Conserve uniquement les deux sauvegardes SQLite automatiques
    les plus récentes dans le dossier indiqué.

    Les fichiers sont classés à partir de leur horodatage dans le nom.
    Les erreurs de suppression sont journalisées sans invalider
    la sauvegarde qui vient d'être créée.
    """

    sauvegardes = sorted(
        Path(dossier).glob("habilitations_*.db"),
        key=lambda fichier: fichier.name,
        reverse=True,
    )

    for ancienne_sauvegarde in sauvegardes[NOMBRE_SAUVEGARDES_AUTOMATIQUES:]:
        try:
            ancienne_sauvegarde.unlink()

            log_info(
                "Ancienne sauvegarde automatique supprimée : "
                f"{ancienne_sauvegarde}"
            )

        except OSError as erreur:
            log_info(
                "Impossible de supprimer l'ancienne sauvegarde "
                f"{ancienne_sauvegarde} : {erreur}"
            )


def creer_sauvegarde_automatique():
    """
    Crée une sauvegarde cohérente de la base SQLite.

    La sauvegarde est conservée dans :
        sauvegardes/automatiques/

    Seules les deux sauvegardes automatiques les plus récentes
    sont conservées.

    Returns
    -------
    Path
        Chemin du fichier de sauvegarde créé.

    Raises
    ------
    FileNotFoundError
        Si la base SQLite n'existe pas.

    RuntimeError
        Si la sauvegarde ou sa vérification échoue.
    """

    # ==========================================
    # VÉRIFICATION DE LA BASE SOURCE
    # ==========================================

    if not DB.exists():
        raise FileNotFoundError(
            f"Base SQLite introuvable : {DB}"
        )

    # ==========================================
    # DOSSIER DE DESTINATION
    # ==========================================

    dossier = (
        Path(DOSSIER_SAUVEGARDES)
        / "automatiques"
    )

    dossier.mkdir(
        parents=True,
        exist_ok=True
    )

    # ==========================================
    # NOM DU FICHIER
    # ==========================================

    horodatage = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    fichier_sauvegarde = (
        dossier
        / f"habilitations_{horodatage}.db"
    )

    connexion_source = None
    connexion_destination = None
    sauvegarde_reussie = False

    try:

        # ==========================================
        # CONNEXIONS SQLITE
        # ==========================================

        connexion_source = sqlite3.connect(
            str(DB)
        )

        connexion_destination = sqlite3.connect(
            str(fichier_sauvegarde)
        )

        # ==========================================
        # SAUVEGARDE COHÉRENTE
        # ==========================================

        connexion_source.backup(
            connexion_destination
        )

        # ==========================================
        # VÉRIFICATION DE L'INTÉGRITÉ
        # ==========================================

        resultat = connexion_destination.execute(
            "PRAGMA quick_check"
        ).fetchone()

        if resultat is None or resultat[0] != "ok":
            raise RuntimeError(
                f"Vérification SQLite échouée : {resultat}"
            )

        sauvegarde_reussie = True

        log_info(
            "Sauvegarde automatique créée : "
            f"{fichier_sauvegarde}"
        )

        return fichier_sauvegarde

    except Exception as erreur:

        log_info(
            f"Erreur de sauvegarde automatique : {erreur}"
        )

        raise

    finally:

        # ==========================================
        # FERMETURE DES CONNEXIONS
        # ==========================================

        if connexion_destination is not None:
            connexion_destination.close()

        if connexion_source is not None:
            connexion_source.close()

        # ==========================================
        # NETTOYAGE EN CAS D'ÉCHEC
        # ==========================================

        if not sauvegarde_reussie:
            if fichier_sauvegarde.exists():
                fichier_sauvegarde.unlink()

        else:
            # La rotation intervient uniquement après une sauvegarde
            # créée et vérifiée avec succès.
            conserver_dernieres_sauvegardes(dossier)


def envoyer_sauvegarde_aux_administrateurs(fichier_sauvegarde):
    """
    Envoie la sauvegarde aux administrateurs actifs
    disposant d'une adresse e-mail.

    La sauvegarde locale est conservée en toutes circonstances.
    """

    import time

    smtp = None

    try:
        # ==========================================
        # DESTINATAIRES
        # ==========================================

        destinataires = (
            UtilisateurManager
            .lister_administrateurs_avec_email()
        )

        if not destinataires:
            log_info(
                "Sauvegarde conservée localement : "
                "aucun administrateur actif avec adresse e-mail."
            )
            return False

        # ==========================================
        # PARAMÈTRES MAIL
        # ==========================================

        parametres = recuperer_parametres_mail()

        if not parametres:
            log_info(
                "Envoi de la sauvegarde impossible : "
                "paramètres mail non configurés."
            )
            return False

        # ==========================================
        # CONNEXION SMTP
        # ==========================================

        debut = time.monotonic()

        log_info("Début de la connexion SMTP.")

        smtp = ouvrir_smtp(parametres)

        log_info(
            f"Connexion SMTP établie en "
            f"{time.monotonic() - debut:.2f} secondes."
        )

        # ==========================================
        # ENVOI AUX ADMINISTRATEURS
        # ==========================================

        envois_reussis = 0

        for destinataire in destinataires:
            try:
                envoyer_mail(
                    smtp=smtp,
                    destinataire=destinataire,
                    sujet="Sauvegarde automatique - Gestion des habilitations",
                    message=(
                        "Bonjour,\n\n"
                        "Vous trouverez en pièce jointe la sauvegarde "
                        "automatique de la base de données de "
                        "Gestion des habilitations.\n\n"
                        "Cordialement,\n"
                        "Gestion des habilitations"
                    ),
                    pieces_jointes=[str(fichier_sauvegarde)],
                    parametres=parametres,
                )

                envois_reussis += 1

            except Exception as erreur:
                log_info(
                    f"Échec d'envoi à {destinataire} : {erreur}"
                )

            log_info(
                f"Durée totale de l'opération SMTP : "
                f"{time.monotonic() - debut:.2f} secondes."
            )

        log_info(
            f"Sauvegarde envoyée à {envois_reussis} "
            f"administrateur(s) sur {len(destinataires)}."
        )

        return envois_reussis == len(destinataires)

    except Exception as erreur:

        log_info(
            "Échec de l'envoi de la sauvegarde : "
            f"{erreur}"
        )

        return False

    finally:

        if smtp is not None:

            try:
                fermer_smtp(smtp)

                log_info("Fermeture SMTP terminée.")

            except Exception as erreur:
                log_info(
                    f"Erreur fermeture SMTP : {erreur}"
                )

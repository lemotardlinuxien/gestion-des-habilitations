import os
import smtplib


from email.message import EmailMessage

from logger_manager import log_info

from mail_repository import recuperer_parametres_mail

import mimetypes


def ouvrir_smtp(parametres=None):
    """Ouvre une connexion SMTP selon le mode de sécurité configuré."""

    param = (
        parametres
        if parametres is not None
        else recuperer_parametres_mail()
    )

    mode = (param.get("smtp_securite") or "ssl").lower()
    serveur = param["smtp_serveur"]
    port = int(param["smtp_port"])

    if mode == "ssl":
        smtp = smtplib.SMTP_SSL(serveur, port, timeout=5)

    elif mode == "starttls":
        smtp = smtplib.SMTP(serveur, port, timeout=5)

        try:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
        except Exception:
            smtp.close()
            raise

    else:
        raise ValueError("Mode de sécurité SMTP non pris en charge.")

    try:
        smtp.login(param["expediteur"], param["mot_de_passe"])
        return smtp

    except Exception:
        smtp.close()
        raise


def fermer_smtp(smtp):
    """Ferme proprement la connexion SMTP."""

    try:
        smtp.quit()

    except (OSError, smtplib.SMTPException) as erreur:
        log_info(
            f"Fermeture SMTP interrompue : {erreur}"
        )

    finally:
        smtp.close()



def envoyer_mail(
        smtp,
        destinataire,
        sujet,
        message,
        pieces_jointes=None,
        parametres=None
):

    # Conserver le comportement historique pour les appels isolés,
    # tout en permettant aux envois groupés de réutiliser leurs paramètres.
    param = (
        parametres
        if parametres is not None
        else recuperer_parametres_mail()
    )

    mail = EmailMessage()

    mail["From"] = param["expediteur"]
    mail["To"] = destinataire
    mail["Subject"] = sujet

    mail.set_content(message)

    # ==========================================
    # PIÈCES JOINTES
    # ==========================================

    if pieces_jointes:

        for fichier in pieces_jointes:

            with open(fichier, "rb") as f:

                contenu = f.read()

            type_mime, encodage = mimetypes.guess_type(
                fichier
            )

            if type_mime is None:
                type_mime = "application/octet-stream"

            maintype, subtype = type_mime.split(
                "/",
                1
            )

            mail.add_attachment(
                contenu,
                maintype=maintype,
                subtype=subtype,
                filename=os.path.basename(fichier)
            )

    # ==========================================
    # ENVOI
    # ==========================================

    smtp.send_message(mail)

    log_info(
        f"Mail envoyé : sujet = {sujet}"
    )


def envoyer_mail_recuperation(email_destinataire, token):
    """
    Envoie le token de récupération du mot de passe.
    """

    smtp = None

    try:
        smtp = ouvrir_smtp()

        sujet = "Récupération de votre mot de passe"

        message = (
            "Bonjour,\n\n"
            "Une demande de récupération de mot de passe "
            "a été effectuée pour votre compte administrateur.\n\n"
            f"Votre code de récupération est :\n\n"
            f"{token}\n\n"
            "Ce code est valable pendant 30 minutes.\n\n"
            "Si vous n'êtes pas à l'origine de cette demande, "
            "vous pouvez ignorer ce message.\n\n"
            "Cordialement,\n"
            "Gestion des habilitations"
        )

        envoyer_mail(
            smtp=smtp,
            destinataire=email_destinataire,
            sujet=sujet,
            message=message,
            pieces_jointes=[]
        )

    finally:

        if smtp is not None:
            fermer_smtp(smtp)
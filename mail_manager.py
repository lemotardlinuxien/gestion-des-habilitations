import os
import smtplib


from email.message import EmailMessage

from logger_manager import log_info

from mail_repository import recuperer_parametres_mail


def ouvrir_smtp(parametres=None):

    # Les envois groupés peuvent fournir un instantané des paramètres
    # pour éviter de relire SQLite et le gestionnaire sécurisé.
    param = (
        parametres
        if parametres is not None
        else recuperer_parametres_mail()
    )

    smtp = smtplib.SMTP_SSL(
        param["smtp_serveur"],
        param["smtp_port"]
    )

    smtp.login(
        param["expediteur"],
        param["mot_de_passe"]
    )

    return smtp


def fermer_smtp(smtp):

    smtp.quit()


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

    if pieces_jointes:

        for fichier in pieces_jointes:

            with open(fichier, "rb") as f:

                mail.add_attachment(
                    f.read(),
                    maintype="application",
                    subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    filename=os.path.basename(fichier)
                )

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
import os
import time

from export_manager import (
    preparer_lignes_secteur,
    generer_export_secteur,
)

from mail_manager import (
    ouvrir_smtp,
    fermer_smtp,
    envoyer_mail,
)

from validation import verifier_email, normaliser_texte_comparaison

from mail_repository import (
    recuperer_mails_secteurs,
    enregistrer_historique_mail,
    enregistrer_envoi,
    recuperer_parametres_mail,
)


def envoyer_exports_secteurs(
        df,
        habilitations,
        dossier_exports,
        progression=None,
        destinataire_personnel=None
):
    """
    Prépare, génère et envoie les rapports d'habilitations
    par secteur.

    La fonction ne dépend pas de Tkinter.

    Paramètres
    ----------
    df :
        DataFrame contenant les salariés.

    habilitations :
        Liste des habilitations à contrôler.

    dossier_exports :
        Dossier dans lequel créer les fichiers Excel.

    progression :
        Fonction optionnelle appelée pour informer
        l'interface de la progression.

    Retour
    ------
    dict
        {
            "nb_envois": int,
            "erreurs": list[str]
        }
    """

    os.makedirs(
        dossier_exports,
        exist_ok=True
    )

    nb_envois = 0
    erreurs = []

    smtp = None

    def informer(message):
        """Transmet une information de progression si nécessaire."""

        if progression is not None:
            progression(message)

    # ==========================================
    # SECTEURS ACTUELS ET DESTINATAIRES
    # ==========================================

    # La base peut conserver les adresses d'anciens secteurs : elles ne
    # doivent pas déclencher d'envoi tant qu'aucun salarié n'appartient
    # à ces secteurs dans le DataFrame actuel.
    secteurs_actuels = {}
    if df is not None and not df.empty and "Secteur" in df.columns:
        for valeur in df["Secteur"].dropna():
            secteur = " ".join(str(valeur).split())
            cle = normaliser_texte_comparaison(secteur)
            if cle and cle not in secteurs_actuels:
                secteurs_actuels[cle] = secteur

    mails_enregistres = recuperer_mails_secteurs() or {}
    mails_normalises = {
        normaliser_texte_comparaison(secteur): (secteur, destinataire)
        for secteur, destinataire in mails_enregistres.items()
        if normaliser_texte_comparaison(secteur)
    }

    # La synchronisation maintient normalement la table à jour, mais on
    # vérifie tout de même les secteurs actifs afin de signaler les adresses
    # manquantes sans bloquer l'envoi des autres secteurs.
    mails = []
    for cle, secteur_actuel in sorted(
        secteurs_actuels.items(), key=lambda element: element[1].casefold()
    ):
        configuration = mails_normalises.get(cle)
        destinataire = configuration[1] if configuration else ""

        if destinataire is None or not str(destinataire).strip():
            message_absence = f"{secteur_actuel} : aucune adresse mail configurée"
            erreurs.append(message_absence)
            enregistrer_historique_mail(
                secteur=secteur_actuel,
                destinataire="",
                objet=f"Etat des habilitations - {secteur_actuel}",
                nombre_habilitations=0,
                statut="Ignoré",
                message_erreur="Aucune adresse mail configurée",
            )
            continue

        mails.append((secteur_actuel, str(destinataire).strip()))

    total = len(mails)

    # Aucun destinataire actif : signaler les adresses manquantes et ne pas
    # ouvrir de connexion SMTP.
    if total == 0:
        if erreurs:
            informer("Aucun envoi possible : des secteurs actifs n'ont pas d'adresse mail.")
        else:
            informer("Aucun secteur actif à traiter.")
        return {"nb_envois": 0, "erreurs": erreurs}

    try:

        # ==========================================
        # CONNEXION SMTP
        # ==========================================

        informer("Connexion au serveur SMTP...")

        parametres_mail = recuperer_parametres_mail()
        smtp = ouvrir_smtp(parametres=parametres_mail)

        informer("Préparation des envois...")

        # ==========================================
        # TRAITEMENT DES SECTEURS
        # ==========================================

        for numero, (secteur, destinataire) in enumerate(
                mails,
                start=1
        ):

            destinataire_envoi = (
                destinataire_personnel
                if destinataire_personnel
                else destinataire
            )

            informer(
                f"Envoi {numero} / {total}\n\n"
                f"Secteur : {secteur}"
            )

            # ==========================================
            # VALIDATION ADRESSE MAIL
            # ==========================================

            valide, message = verifier_email(
                destinataire_envoi
            )

            if not valide:

                enregistrer_historique_mail(
                    secteur=secteur,
                    destinataire=destinataire,
                    objet=(
                        f"Etat des habilitations - "
                        f"{secteur}"
                    ),
                    nombre_habilitations=0,
                    statut="Erreur",
                    message_erreur=message
                )

                erreurs.append(
                    f"{secteur} : {message}"
                )

                continue

            if not destinataire or not destinataire.strip():

                enregistrer_historique_mail(
                    secteur=secteur,
                    destinataire="",
                    objet=(
                        f"Etat des habilitations - "
                        f"{secteur}"
                    ),
                    nombre_habilitations=0,
                    statut="Erreur",
                    message_erreur=(
                        "Aucune adresse mail configurée"
                    )
                )

                erreurs.append(
                    f"{secteur} : "
                    f"aucune adresse mail configurée"
                )

                continue

            lignes = []

            try:

                # ==========================================
                # PRÉPARATION DU RAPPORT
                # ==========================================

                lignes = preparer_lignes_secteur(
                    df,
                    secteur,
                    habilitations
                )

                if not lignes:

                    continue

                # ==========================================
                # CRÉATION DU FICHIER EXCEL
                # ==========================================

                fichier = generer_export_secteur(
                    lignes,
                    dossier_exports,
                    secteur
                )

                # ==========================================
                # ENVOI DU MAIL
                # ==========================================

                envoyer_mail(
                    smtp=smtp,
                    destinataire=destinataire_envoi,
                    sujet=(
                        f"Etat des habilitations "
                        f"- {secteur}"
                    ),
                    message=(
                        f"Bonjour,\n\n"
                        f"Veuillez trouver ci-joint "
                        f"le rapport des habilitations "
                        f"du secteur {secteur}.\n\n"
                        f"Cordialement."
                    ),
                    pieces_jointes=[
                        fichier
                    ],
                    parametres=parametres_mail
                )

                # ==========================================
                # HISTORIQUE MAIL
                # ==========================================

                enregistrer_historique_mail(
                    secteur=secteur,
                    destinataire=destinataire_envoi,
                    objet=(
                        f"Etat des habilitations "
                        f"- {secteur}"
                    ),
                    nombre_habilitations=len(lignes),
                    statut="Envoyé",
                    message_erreur=""
                )

                # ==========================================
                # HISTORIQUE ENVOI
                # ==========================================

                enregistrer_envoi(
                    secteur=secteur,
                    destinataire=destinataire_envoi,
                    fichier=os.path.basename(
                        fichier
                    )
                )

                nb_envois += 1

                # ==========================================
                # DÉLAI ENTRE LES ENVOIS
                # ==========================================

                time.sleep(2)

            except Exception as erreur:

                import traceback

                traceback.print_exc()

                enregistrer_historique_mail(
                    secteur=secteur,
                    destinataire=destinataire,
                    objet=(
                        f"Etat des habilitations "
                        f"- {secteur}"
                    ),
                    nombre_habilitations=len(lignes),
                    statut="Erreur",
                    message_erreur=str(erreur)
                )

                erreurs.append(
                    f"{secteur} : {erreur}"
                )

    finally:

        if smtp is not None:
            fermer_smtp(smtp)

    return {
        "nb_envois": nb_envois,
        "erreurs": erreurs
    }
import unicodedata

import re


def verifier_email(email):
    """
    Vérifie la structure d'une adresse mail.

    Retourne :
        (True, "") si l'adresse est valide
        (False, "message") sinon
    """

    if email is None:
        return False, "Adresse mail absente"

    email = email.strip().lower()

    if email == "":
        return False, "Adresse mail absente"

    if " " in email:
        return False, "L'adresse contient un espace"

    if email.count("@") != 1:
        return False, "L'adresse doit contenir un seul @"

    partie_locale, domaine = email.split("@")

    if not partie_locale:
        return False, "La partie avant @ est absente"

    if not domaine:
        return False, "Le domaine est absent"

    if "." not in domaine:
        return False, "Le domaine doit contenir une extension"

    if domaine.startswith(".") or domaine.endswith("."):
        return False, "Le domaine est invalide"

    motif = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

    if re.fullmatch(motif, email) is None:
        return False, "Format d'adresse mail invalide"

    return True, ""

def normaliser_texte_comparaison(valeur):
    """Normalise un texte pour les comparaisons d'identité uniquement.

    Ignore la casse, les accents et les espaces superflus, sans modifier
    les valeurs originales enregistrées ou affichées par l'application.
    """
    if valeur is None:
        return ""

    texte = " ".join(str(valeur).split()).casefold()
    texte = unicodedata.normalize("NFKD", texte)
    return "".join(
        caractere
        for caractere in texte
        if not unicodedata.combining(caractere)
    )

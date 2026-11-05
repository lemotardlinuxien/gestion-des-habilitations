"""Calculs communs pour le tableau de bord, les graphiques et les alertes."""

import pandas as pd

from mail_repository import recuperer_parametres_mail
from habilitation_manager import HabilitationManager
from controle_manager import ControleManager


def obtenir_delai_alerte():
    """Retourne le délai configuré, avec 45 jours comme valeur de secours."""
    param = recuperer_parametres_mail()

    if not param:
        return 45

    try:
        return int(param.get("delai_alerte", 45))
    except (TypeError, ValueError):
        return 45


def _compter_statuts(dates, delai_alerte):
    """Compte les statuts en utilisant les règles communes de ControleManager."""
    valides = 0
    echeance = 0
    expirees = 0

    for date in dates:
        if pd.isna(date):
            continue

        statut = ControleManager.statut(date, delai_alerte)

        if "🔴" in statut:
            expirees += 1
        elif "🟠" in statut:
            echeance += 1
        elif "🟢" in statut:
            valides += 1

    return valides, echeance, expirees


def calculer_statistiques(df, delai_alerte=None):
    """Retourne les nombres d'habilitations valides, à échéance et expirées."""
    habilitations = HabilitationManager.lister()

    if delai_alerte is None:
        delai_alerte = obtenir_delai_alerte()

    if df is None or df.empty:
        return 0, 0, 0

    colonnes = [hab for hab in habilitations if hab in df.columns]
    if not colonnes:
        return 0, 0, 0

    dates = (date for colonne in colonnes for date in df[colonne])
    return _compter_statuts(dates, delai_alerte)


def calculer_statistiques_par_habilitation(df, habilitations=None):
    """Retourne trois listes de comptes, dans l'ordre des habilitations configurées.

    La liste peut être fournie par l'appelant pour éviter une lecture SQLite
    redondante lorsqu'elle a déjà été récupérée pour construire le graphique.
    """
    if habilitations is None:
        habilitations = HabilitationManager.lister()

    delai_alerte = obtenir_delai_alerte()

    valides = []
    echeance = []
    expirees = []

    for hab in habilitations:
        if df is None or df.empty or hab not in df.columns:
            nb_valides, nb_echeance, nb_expirees = 0, 0, 0
        else:
            nb_valides, nb_echeance, nb_expirees = _compter_statuts(
                df[hab], delai_alerte
            )

        valides.append(nb_valides)
        echeance.append(nb_echeance)
        expirees.append(nb_expirees)

    return valides, echeance, expirees


def calculer_alertes(df, delai_alerte=None):
    """Retourne le nombre d'habilitations expirées et arrivant à échéance."""
    _, echeance, expirees = calculer_statistiques(
        df,
        delai_alerte=delai_alerte,
    )
    return expirees, echeance

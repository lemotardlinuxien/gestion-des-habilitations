from database import get_connection


def obtenir_parametre(cle, valeur_defaut=""):
    """Retourne un paramètre général de l'application."""
    conn = get_connection()
    try:
        ligne = conn.execute(
            "SELECT valeur FROM parametres_application WHERE cle = ?",
            (cle,),
        ).fetchone()
        return ligne[0] if ligne else valeur_defaut
    finally:
        conn.close()


def enregistrer_parametre(cle, valeur):
    """Enregistre ou met à jour un paramètre général."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO parametres_application (cle, valeur)
            VALUES (?, ?)
            ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur
            """,
            (cle, str(valeur).strip()),
        )
        conn.commit()
    finally:
        conn.close()


def obtenir_nom_entreprise():
    return obtenir_parametre("nom_entreprise", "")

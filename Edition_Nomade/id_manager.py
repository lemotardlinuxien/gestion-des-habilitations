import uuid


def generer_id():
    return str(uuid.uuid4())


def id_valide(id_):
    return (
        id_ is not None
        and str(id_).strip() != ""
    )
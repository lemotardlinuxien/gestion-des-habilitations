import matplotlib.pyplot as plt
from statistiques import calculer_statistiques_par_habilitation, obtenir_delai_alerte
from habilitation_manager import HabilitationManager
from config import DOSSIER_GRAPHIQUES


class GraphiquesManager:

    @staticmethod
    def afficher_graphique(df, progression=None):

        def informer(etape, message):
            if progression is not None:
                progression(
                    f"Étape {etape} / 5 - {message}"
                )

        informer(1, "Préparation des habilitations...")
        HABILITATIONS = HabilitationManager.lister()

        informer(2, "Calcul des statistiques...")
        valides, recycler, perimees = (
            calculer_statistiques_par_habilitation(
                df,
                habilitations=HABILITATIONS,
            )
        )

        informer(3, "Création du graphique...")

        x = range(len(HABILITATIONS))
        largeur = 0.25

        fig, ax = plt.subplots(figsize=(12, 6))

        barres_valides = ax.bar(
            [i - largeur for i in x],
            valides,
            largeur,
            label="Valides",
            color="green"
        )

        delai_alerte = obtenir_delai_alerte()

        barres_recycler = ax.bar(
            x,
            recycler,
            largeur,
            label=f"À recycler < {delai_alerte} jours",
            color="orange"
        )

        barres_perimees = ax.bar(
            [i + largeur for i in x],
            perimees,
            largeur,
            label="Périmées",
            color="red"
        )

        for groupe in (
                barres_valides,
                barres_recycler,
                barres_perimees
        ):

            for barre in groupe:
                hauteur = barre.get_height()

                ax.text(
                    barre.get_x() + barre.get_width() / 2,
                    hauteur,
                    f"{int(hauteur)}",
                    ha="center",
                    va="bottom"
                )

        ax.set_title(
            "État des habilitations"
        )

        ax.set_xlabel(
            ""
        )

        ax.set_ylabel(
            "Nombre de personnes"
        )

        ax.set_yticks([])

        ax.set_xticks(
            list(x)
        )

        ax.set_xticklabels(
            HABILITATIONS
        )

        ax.legend()

        informer(4, "Mise en forme du graphique...")
        plt.tight_layout()

        informer(5, "Enregistrement du graphique...")
        # Sauvegarder le graphique dans le dossier de données utilisateur,
        # et non dans le répertoire courant de PyCharm.
        import os
        from datetime import datetime

        os.makedirs(
            DOSSIER_GRAPHIQUES,
            exist_ok=True
        )

        nom_fichier = os.path.join(
            DOSSIER_GRAPHIQUES,
            f"habilitations_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )

        plt.savefig(
            nom_fichier,
            dpi=300,
            bbox_inches="tight"
        )

        return plt

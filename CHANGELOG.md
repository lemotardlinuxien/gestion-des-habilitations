# Historique des versions

## V58 — Édition Nomade

- Version nomade de l’application Gestion des habilitations.
- Stockage des données dans le dossier `Donnees` placé à côté de l’exécutable.
- Socle fonctionnel commun à l’Édition Fixe V57.
- Rotation des sauvegardes SQLite : deux fichiers conservés au maximum dans chacun des dossiers de sauvegarde concernés.
- Préservation des mécanismes de vérification et de récupération de la base de données.

## V57 — Édition Fixe

- Version fixe de l’application Gestion des habilitations.
- Stockage des données dans le profil utilisateur du système.
- Gestion des salariés et de leurs habilitations, suivi des échéances, gestion documentaire, génération et fusion de PDF.
- Gestion des comptes utilisateurs, des accès, des courriels, des sauvegardes SQLite et de la récupération.
- Rotation des sauvegardes SQLite : deux fichiers conservés au maximum dans chacun des dossiers de sauvegarde concernés.

## Organisation des éditions

Les deux éditions partagent les modules applicatifs. Leur différence principale concerne l’emplacement des données et les paramètres de démarrage associés. Les sources sont conservées séparément afin de préserver les configurations propres à chaque édition.

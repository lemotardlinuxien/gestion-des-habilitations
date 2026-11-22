# Sécurité

## Signaler une vulnérabilité

Ne publiez pas de mot de passe, de donnée personnelle, de base SQLite réelle ou de document salarié dans une issue publique.

Pour signaler un problème de sécurité, contactez le mainteneur par un canal privé disponible depuis le profil GitHub du dépôt. Fournissez une description du problème, les étapes de reproduction et l'impact potentiel, sans joindre de données réelles lorsque des exemples fictifs suffisent.

## Données à ne jamais publier

Ne pas versionner :
- les bases SQLite de production ou de test contenant des données réelles ;
- les fichiers Excel de travail ;
- les sauvegardes ;
- les documents PDF et dossiers salariés ;
- les journaux contenant des informations personnelles ;
- les mots de passe, clés, jetons, fichiers `.env` ou paramètres privés.

Le fichier `.gitignore` couvre les principaux fichiers et dossiers locaux. Il ne remplace pas une vérification manuelle de `git status` avant chaque commit.

## Récupération

Ne jamais supprimer le marqueur d'installation ni contourner le mécanisme de récupération pour recréer une base vide lorsqu'une base existante est absente ou endommagée. Restaurer une sauvegarde vérifiée selon la procédure prévue par l'application.

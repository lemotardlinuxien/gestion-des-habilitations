# Audit prépublication — V53

**Date de mise à jour : 16 octobre 2026**

## 1. Identification du projet

- **Application :** Gestion des habilitations
- **Version :** V53
- **Branche Git :** `main`
- **État du dépôt :** fichiers indexés pour le premier commit ; aucun commit créé à ce stade.
- **Système de développement :** Linux Mint
- **Système de test complémentaire :** Windows 8
- **Licence choisie :** PolyForm Noncommercial License 1.0.0
- **Préparation à la publication publique :** en cours.

## 2. Vérifications et tests déjà réalisés

### 2.1. Préparation du dépôt

- Le dépôt Git de V53 est initialisé sur la branche `main`.
- Les fichiers du projet et les icônes nécessaires sont indexés.
- Le fichier `.gitignore` exclut notamment les environnements virtuels, les bases de données, les fichiers Excel métier, les PDF, les sauvegardes, les journaux et les fichiers de secrets.
- Les quatre fichiers `README.md`, `config.py`, `dossier_manager.py` et `gui.py` ont été réindexés après leurs dernières modifications.
- L'identité Git est configurée localement pour ce dépôt, avec une adresse GitHub `noreply`.
- Aucun commit ni aucune publication distante n'ont encore été effectués au moment de cette mise à jour.

### 2.2. Contrôles préliminaires des fichiers

- La liste des fichiers indexés a été examinée.
- Une recherche ciblée dans l'index n'a trouvé aucun fichier correspondant aux motifs utilisés pour identifier les bases SQLite, fichiers Excel, journaux, certificats et clés, ainsi que certains répertoires de données.
- Une recherche de termes liés aux mots de passe, aux courriels et aux secrets a identifié plusieurs fichiers Python et Markdown nécessitant une interprétation ciblée.

Ces résultats sont encourageants, mais ne constituent pas une garantie d'absence de secrets ou de données personnelles.

### 2.3. Gestion des documents

Les tests suivants ont été effectués et validés :

- Sous Linux Mint, ouverture correcte des documents PDF.
- Sous Linux Mint, ouverture correcte des photos.
- Sous Windows 8, ouverture correcte des documents PDF et des photos.
- Suppression du dialogue d'information devenu inutile après l'ouverture du document.
- Sous Linux Mint, les PDF sont ouverts avec Xreader sans imposer le plein écran, afin de conserver l'accès à la barre d'outils et à la commande d'impression.

Ces validations concernent uniquement les comportements effectivement testés. Elles ne constituent pas une validation complète de toutes les fonctionnalités de l'application.

## 3. État des vérifications restantes

### 3.1. Revue de sécurité

- Relire les modules d'authentification, de gestion des comptes et de récupération des mots de passe.
- Examiner les modules d'envoi de courriels et de stockage des secrets.
- Vérifier les chemins de stockage des données et les mécanismes de sauvegarde.
- Confirmer l'absence de données personnelles, de bases réelles, de documents salariés, d'identifiants confidentiels et de secrets dans les fichiers suivis par Git.
- Vérifier que les fichiers sensibles ne sont pas présents dans l'historique Git avant la publication.

### 3.2. Validation technique de V53

- Confirmer la cohérence de `VERSION = "V53"` dans `config.py`.
- Vérifier la cohérence du README, de la licence et des instructions d'installation.
- Recontrôler la syntaxe de tous les fichiers Python de V53.
- Vérifier les dépendances déclarées et leur installation dans un environnement propre.
- Vérifier la configuration du stockage des données et le comportement de `keyring` sous les systèmes pris en charge.

### 3.3. Tests fonctionnels

Les tests fonctionnels complets restent à finaliser ou à documenter, notamment pour :

- la création du premier compte administrateur et la connexion ;
- la gestion des utilisateurs et des droits d'accès ;
- la gestion des salariés et des habilitations ;
- les recherches, modifications et suppressions ;
- les imports et exports Excel ;
- les contrôles d'échéances et les statistiques ;
- la génération des PDF ;
- les sauvegardes et la restauration ;
- les envois de courriels ;
- la gestion des documents salariés ;
- la persistance des données après fermeture et redémarrage.

Les tests doivent être effectués avec des données fictives ou de test, sans exposer de données réelles de salariés.

### 3.4. Construction et publication

- Construire et tester séparément les livrables Linux et Windows prévus.
- Vérifier les icônes, les ressources, les chemins et la persistance dans les livrables.
- Relire le contenu exact de l'index Git avant le premier commit.
- Vérifier l'identité et les coordonnées de contact présentes dans les métadonnées publiques.
- Créer le premier commit après validation des contrôles nécessaires.
- Configurer le dépôt distant GitHub et vérifier les paramètres de visibilité avant toute publication publique.

## 4. Règles de sécurité pour la publication

Ne jamais publier :

- une base de données réelle ;
- un fichier Excel contenant des données personnelles ;
- un document salarié ou un export métier ;
- une sauvegarde ou un journal contenant des informations confidentielles ;
- un mot de passe, un jeton, une clé privée ou un secret de connexion.

Le fichier `.gitignore` constitue une protection supplémentaire, mais ne remplace pas l'examen des fichiers indexés et de l'historique Git.

## 5. État de publication

**V53 est en préparation pour une éventuelle publication sur GitHub.**

La gestion des documents a été testée sous Linux Mint et Windows 8. La préparation du dépôt Git et les contrôles préliminaires des fichiers sont engagés.

La revue de sécurité finale, la validation fonctionnelle complète, la vérification des livrables et la préparation du premier commit restent à finaliser.

Aucune publication publique ne doit être effectuée avant la fin des vérifications nécessaires.
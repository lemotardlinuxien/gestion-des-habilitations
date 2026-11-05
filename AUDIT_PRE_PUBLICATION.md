# Audit prépublication — V54

**Date de mise à jour : 5 novembre 2026**

## 1. Identification du projet

- **Application :** Gestion des habilitations
- **Version candidate :** V54
- **Branche de base dans l’archive examinée :** `main`
- **Commit de base :** `5262a2c` — préparation de V53 pour publication avec captures d’écran
- **Système de développement :** Linux Mint
- **Système de test complémentaire :** Windows 11
- **Licence choisie :** PolyForm Noncommercial License 1.0.0
- **État :** préparation de l’intégration V54 ; revue prépublication à poursuivre.

> Cet audit décrit les vérifications connues et les points à contrôler. Il ne vaut pas certification de sécurité ni validation fonctionnelle exhaustive.

## 2. Vérifications et tests rapportés

### 2.1. Gestion des documents V54

Selon les tests rapportés lors du développement :

- le sélecteur de fichiers permet de sélectionner les fichiers à assembler dans l’ordre souhaité ;
- le glisser-déposer a été testé sous Linux Mint ;
- sous Windows 11, le glisser-déposer a d’abord échoué parce que `tkinterdnd2` n’était pas installé dans l’environnement Python, puis a fonctionné après son installation ;
- l’utilisateur a confirmé les tests V54 comme réussis après installation de cette dépendance.

Ces résultats portent sur les comportements testés de la gestion des documents. Ils ne démontrent pas que toutes les fonctions de l’application ou tous les environnements sont validés.

### 2.2. Éléments du dépôt

- Le README présente les principales fonctions et comporte des captures d’écran dans `screenshots/`.
- Le `.gitignore` exclut notamment les environnements virtuels, bases de données, fichiers Excel métier, PDF, sauvegardes, journaux et fichiers locaux de secrets.
- `requirements-build.txt` inclut `requirements.txt` et PyInstaller.
- La dépendance `tkinterdnd2` doit être déclarée dans `requirements.txt` afin que l’installation des dépendances reproduise le test du glisser-déposer.

## 3. Vérifications restantes avant publication

### 3.1. Revue de sécurité et des données

- Examiner les modules d’authentification, de gestion des comptes et de récupération des mots de passe.
- Examiner l’envoi de courriels et le stockage des secrets.
- Vérifier les chemins de stockage des données et les sauvegardes.
- Confirmer qu’aucune donnée réelle de salarié, base métier, pièce justificative, identifiant confidentiel ou secret n’est incluse dans les fichiers qui seront publiés.
- Examiner l’historique Git afin de rechercher d’éventuels fichiers sensibles qui auraient été ajoutés puis supprimés.

Le `.gitignore` réduit le risque d’ajout accidentel mais ne nettoie pas l’historique et ne remplace pas cette vérification.

### 3.2. Validation technique

- Confirmer `VERSION = "V54"` dans `config.py`.
- Vérifier la cohérence du README, de la licence et des instructions d’installation.
- Contrôler la syntaxe des fichiers Python.
- Vérifier l’ensemble des dépendances, dont `tkinterdnd2`, dans un environnement propre.
- Contrôler la configuration de `keyring` et du stockage des données sur les systèmes cibles.

### 3.3. Tests fonctionnels à documenter

Les tests complets suivants restent à réaliser ou à consigner avec leur environnement et leur résultat :

- création du premier compte administrateur et connexion ;
- gestion des utilisateurs et des droits ;
- gestion des salariés et habilitations ;
- recherches, modifications et suppressions ;
- imports et exports Excel ;
- échéances et statistiques ;
- génération de PDF et graphiques ;
- sauvegarde et restauration ;
- envoi de courriels ;
- ajout, ouverture, fusion et suppression de documents ;
- persistance des données après fermeture et redémarrage.

Utiliser des données fictives ou de test.

### 3.4. Préparation GitHub

- Examiner le diff V53 → V54 et confirmer les fichiers qui doivent être inclus.
- Vérifier le contenu exact de l’index Git avant le commit.
- Exclure du dépôt les environnements virtuels, caches, bases et données métier, fichiers générés et secrets.
- Vérifier les métadonnées publiques et les coordonnées éventuelles.
- Vérifier le dépôt distant et les paramètres de visibilité avant tout push.
- Ne créer le commit et ne pousser V54 qu’après validation de la revue.

## 4. Règles de sécurité pour la publication

Ne jamais publier :

- une base de données réelle ;
- un fichier Excel contenant des données personnelles ;
- un document salarié ou un export métier ;
- une sauvegarde ou un journal confidentiel ;
- un mot de passe, jeton, clé privée ou secret de connexion.

## 5. État de publication

**V54 est en préparation pour intégration dans GitHub.** Les tests rapportés de la fonctionnalité de glisser-déposer sont concluants sous Linux Mint et Windows 11 après installation de `tkinterdnd2`. La revue finale des fichiers et de l’historique, les vérifications restantes et la validation du contenu exact du commit doivent précéder la publication.

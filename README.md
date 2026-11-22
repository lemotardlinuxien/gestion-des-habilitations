# Gestion des habilitations

Application de bureau Python destinée à la gestion des salariés et au suivi de leurs habilitations. Le dépôt propose deux éditions distinctes, construites sur un socle applicatif commun.

**Auteur :** Fabrice BONNAMY
**Licence :** PolyForm Noncommercial License 1.0.0 — voir [LICENSE](LICENSE).

## Choisir une édition

| Édition | Version | Emplacement des données | Sources |
|---|---|---|---|
| **Édition Fixe** | V57 | Profil utilisateur du système | [`Edition_Fixe/`](Edition_Fixe/) |
| **Édition Nomade** | V58 | Dossier `Donnees` à côté de l’exécutable | [`Edition_Nomade/`](Edition_Nomade/) |

### Édition Fixe — V57

Les données sont stockées indépendamment du dossier de l’application :
- Windows : `%LOCALAPPDATA%\GestionHabilitations`
- Linux : `$XDG_DATA_HOME/GestionHabilitations` si défini, sinon `~/.local/share/GestionHabilitations`
- macOS : `~/Library/Application Support/GestionHabilitations`

### Édition Nomade — V58

Les données sont stockées dans un dossier `Donnees` placé à côté de l’exécutable. L’application et ce dossier peuvent être déplacés ensemble, sous réserve que le support soit accessible en écriture.

## Fonctionnalités principales

- Gestion des salariés et de leurs habilitations.
- Suivi des échéances et alertes de validité.
- Recherche, tableau de bord, graphiques et statistiques.
- Gestion des documents associés aux salariés.
- Conversion et fusion de documents en PDF.
- Gestion des comptes utilisateurs et des accès.
- Paramétrage et envoi de courriels.
- Sauvegardes SQLite, vérification d’intégrité et mécanismes de récupération.

## Installation depuis les sources

Chaque édition possède ses propres fichiers `requirements.txt` et `requirements-build.txt`. Ouvrir le dossier de l’édition choisie, créer un environnement virtuel, installer les dépendances, puis lancer `main.py`.

```bash
python -m venv .venv
source .venv/bin/activate  # Linux
python -m pip install -r requirements.txt
python main.py
```

Sous Windows PowerShell, activer l’environnement avec `.venv\Scripts\Activate.ps1`. La compilation Windows doit être réalisée sous Windows avec les dépendances de `requirements-build.txt`.

## Sauvegardes et récupération

La rotation conserve au maximum deux fichiers SQLite dans chacun des emplacements de sauvegarde concernés. Cette limite s’applique séparément à chaque dossier, et non à l’ensemble des dossiers. Les sauvegardes automatiques sont vérifiées avant la rotation.

Ne pas supprimer le marqueur d’installation ni contourner le mécanisme de récupération lorsqu’une base existante est absente ou endommagée. Restaurer une sauvegarde vérifiée selon la procédure prévue par l’application. Il est recommandé de conserver également une copie indépendante des sauvegardes sur un autre support.

## Sécurité et données personnelles

Ne publiez jamais de base de données réelle, fichier Excel de travail, sauvegarde, document salarié, journal contenant des données personnelles, mot de passe ou secret. Consultez [SECURITY.md](SECURITY.md) et vérifiez le contenu de l’index Git avant chaque publication.

## Historique et contribution

- [CHANGELOG.md](CHANGELOG.md)
- [SECURITY.md](SECURITY.md)
- [LICENSE](LICENSE)

Les sources de chaque édition sont documentées dans leur dossier respectif.

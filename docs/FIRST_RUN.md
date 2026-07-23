# Premier lancement de PGA Shootout

Ce guide part de zéro. Il explique comment installer le projet, renseigner ses propres clubs et utiliser l'assistant interactif sans connaître son architecture interne.

## 1. Ce qu'est l'application

PGA Shootout est une application en ligne de commande écrite en **Python 3.11 ou plus récent**. Elle compare objectivement les statistiques et les capacités connues de plusieurs compositions de sac. Elle ne nécessite ni compilation manuelle, ni base de données, ni service en ligne.

Le projet ne choisit pas arbitrairement un « meilleur » sac : il montre les gains, les pertes, les compromis et les informations manquantes. Certaines capacités du jeu ne sont pas encore simulées ; elles sont signalées au lieu d'être devinées.

## 2. Logiciels à installer

Sous Windows, installer :

1. [Python](https://www.python.org/downloads/) 3.11 ou plus récent. Pendant l'installation, cocher **Add Python to PATH**.
2. [Git](https://git-scm.com/download/win), recommandé pour récupérer et mettre à jour le projet. Git n'est pas nécessaire si le projet est téléchargé en ZIP.
3. Un éditeur de texte capable de modifier du JSON, par exemple Visual Studio Code ou Notepad++.

Une connexion Internet est nécessaire lors de la récupération et de la première installation : Python télécharge les outils de construction déclarés par le projet. L'application installée et les données locales peuvent ensuite être utilisées hors ligne.

Vérifier Python dans PowerShell :

```powershell
py -3.11 --version
```

Une version `Python 3.11.x` ou supérieure doit s'afficher. Il n'existe aucune dépendance applicative externe à installer séparément : l'installation du projet s'en charge.

## 3. Récupérer le projet

### Avec Git, méthode recommandée

Dans PowerShell, choisir un dossier puis exécuter :

```powershell
git clone https://github.com/Pelic-commits/pga-shootout.git
cd pga-shootout
```

### Sans Git

Sur la page GitHub du projet, choisir **Code**, puis **Download ZIP**. Décompresser l'archive et ouvrir PowerShell dans le dossier `pga-shootout` obtenu.

Toutes les commandes de ce guide doivent être exécutées depuis ce dossier, celui qui contient `pyproject.toml`, `src`, `data` et `docs`.

## 4. Installer l'application

Créer un environnement Python isolé :

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
$env:PYTHONUTF8 = "1"
python -m pip install --upgrade pip
python -m pip install -e .
```

Le préfixe `(.venv)` apparaît normalement devant l'invite PowerShell. L'option `-e` installe le projet localement : les futures mises à jour du code sont immédiatement utilisées. Il n'y a rien à compiler.

Lors d'une prochaine session, il suffira de revenir dans le projet et de réactiver l'environnement :

```powershell
cd chemin\vers\pga-shootout
.\.venv\Scripts\Activate.ps1
$env:PYTHONUTF8 = "1"
```

`PYTHONUTF8` garantit l'affichage correct des accents et des flèches, y compris dans les anciennes consoles Windows.

Sous macOS ou Linux, utiliser Python 3.11 ou plus récent puis :

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## 5. Vérifier l'installation

Depuis la racine du projet, avec l'environnement actif :

```powershell
pga-shootout --help
pga-shootout user-validate
pga-shootout validate-data data/raw/pga_club_stats_extract_v2_2026-07-21.json data/normalized/clubs_official.json
python -m unittest discover -s tests
```

Les deux validations doivent réussir et les tests doivent se terminer par `OK`. Le catalogue officiel normalisé se trouve dans `data/normalized/clubs_official.json`; sa capture source immuable se trouve dans `data/raw/`.

Si `pga-shootout` n'est pas reconnu mais que l'installation a réussi, vérifier que `(.venv)` est visible, puis réexécuter `python -m pip install -e .`.

## 6. Où se trouvent les données

Le projet sépare strictement :

- `data/raw/` : capture officielle brute, à ne pas modifier ;
- `data/normalized/` : catalogue officiel exploitable par le moteur, à ne pas modifier pour saisir ses clubs ;
- `data/user/` : données personnelles du joueur.

Les cinq fichiers de `data/user/` sont :

- `account.json` : profil général ;
- `inventory.json` : clubs débloqués, niveaux et cartes ;
- `bags.json` : sacs enregistrés ;
- `preferences.json` : préférences factuelles, sans score automatique ;
- `observations.json` : observations personnelles.

Le chargeur attend ces cinq fichiers. Pour repartir d'un autre profil, conserver leur structure et remplacer les données. Avant toute modification :

```powershell
Copy-Item -Recurse data/user data/user.backup
```

Les fichiers sont du JSON : utiliser des guillemets doubles, ne pas laisser de virgule après le dernier élément et enregistrer en UTF-8.

## 7. Créer son premier inventaire

Ouvrir `data/user/inventory.json`. La liste `entries` contient un objet par club connu. Exemple pour Cyclotron au niveau 12 :

```json
{
  "club_id": "cyclotron",
  "display_name": "Cyclotron",
  "unlocked": true,
  "current_level": 12,
  "cards_owned": 46,
  "cards_required_for_next_upgrade": 50,
  "upgrade_available": false,
  "observed_at": "2026-07-23",
  "source": "manual_user_entry"
}
```

Règles importantes :

- `club_id` doit être l'identifiant exact du catalogue officiel ;
- `current_level` est un nombre entier, ou `null` si le niveau est inconnu ;
- `upgrade_available` doit être `true` exactement lorsque `cards_owned` est supérieur ou égal à `cards_required_for_next_upgrade` ;
- un club absent n'est pas considéré comme verrouillé lorsque `inventory_complete` vaut `false` ;
- conserver des identifiants uniques dans `entries`.

Pour trouver un identifiant, ouvrir `data/normalized/clubs_official.json` et rechercher le nom affiché du club. Ne jamais inventer l'identifiant à partir du nom.

Après chaque modification :

```powershell
pga-shootout user-validate
```

Cette commande signale notamment les identifiants inconnus, niveaux invalides et incohérences de cartes.

### Niveau réel ou niveau de scénario

Le mode **Réel** utilise exclusivement `current_level`. Pour analyser un remplacement, le niveau des cinq clubs du sac et celui du club entrant doivent tous être connus. Une valeur `null` provoque honnêtement l'exclusion du placement.

Le mode **Scénario** applique un même niveau hypothétique explicite aux clubs évalués. Il est utile pour explorer une idée, mais son résultat ne décrit pas l'inventaire réel.

## 8. Créer son premier sac

Ouvrir `data/user/bags.json` et ajouter un objet dans `bags` :

```json
{
  "id": "mon_premier_sac",
  "name": "Mon premier sac",
  "status": "user_observed",
  "club_ids": [
    "high_flight",
    "cyclotron",
    "ember",
    "maelstrom",
    "sunstorm"
  ],
  "notes": [
    "Composition saisie manuellement."
  ]
}
```

Un sac doit contenir **exactement cinq identifiants différents**, dans leur ordre réel. L'ordre compte : certaines capacités dépendent de la position ou de l'adjacence. La valeur de `status` doit être `user_observed`. Choisir un `id` court, unique, en minuscules et sans espace.

Tous les clubs du sac doivent exister dans le catalogue officiel. Ils ne sont pas obligés de figurer dans l'inventaire pour une analyse hypothétique, mais le mode Réel exigera leurs entrées et leurs niveaux.

Valider ensuite :

```powershell
pga-shootout user-validate
```

## 9. Lancer l'interface interactive

```powershell
pga-shootout recommend-interactive
```

L'assistant demande successivement :

1. le sac enregistré à analyser ;
2. le club débloqué à tester ;
3. le mode **Réel** ou **Scénario** ;
4. le niveau hypothétique si le mode Scénario est choisi.

Il teste les cinq positions possibles du club entrant. Aucun identifiant interne n'est à saisir dans ce parcours.

À la fin, l'assistant propose d'afficher l'Explain détaillé d'un placement. Répondre `1`, puis choisir son numéro, ou répondre `2` pour quitter.

## 10. Comprendre le résultat

Chaque placement appartient à l'une de ces catégories :

- **amélioration sans contrepartie** : au moins une métrique qualifiée progresse et aucune ne régresse ;
- **compromis** : certaines métriques progressent et d'autres régressent ;
- **neutre** : aucune métrique qualifiée ne change ;
- **exclu** : les données sont insuffisantes ou le candidat n'est pas qualifiable.

Les résultats distinguent Power, Control, Spin, Loft, Launch Angle, Wind Resistance et les autres métriques prises en charge. Il n'existe pas de score global caché : un compromis doit être choisi selon le besoin du joueur.

Les avertissements sont essentiels :

- une capacité non résolue signifie que son impact n'a pas été inclus ;
- un niveau manquant rend un résultat réel incomplet ou exclu ;
- un scénario est hypothétique ;
- un effet différé peut être reconnu sans être simulé comme une séquence complète de coups.

L'Explain détaille les statistiques de base, chaque capacité évaluée, ses entrées, ses contributions, les éléments ignorés et les valeurs finales.

## 11. Tutoriel 1 — « Je viens d'obtenir Cyclotron »

1. Ouvrir `data/user/inventory.json`.
2. Ajouter l'entrée Cyclotron présentée à la section 7, ou la compléter si elle existe déjà. Ne jamais créer deux entrées portant le même `club_id`. Utiliser le vrai niveau et le vrai nombre de cartes. Si le niveau n'est pas connu, utiliser `null` et prévoir une analyse en mode Scénario.
3. Enregistrer puis lancer `pga-shootout user-validate`.
4. Lancer `pga-shootout recommend-interactive`.
5. Choisir le sac à améliorer, par exemple **Sac de référence / par-3 Divebomb**.
6. Choisir **Cyclotron** dans la liste des clubs.
7. Choisir **Réel** uniquement si les six niveaux nécessaires sont renseignés. Sinon, choisir **Scénario**, puis saisir par exemple `12` en comprenant que tous les clubs seront évalués à ce niveau hypothétique.
8. Lire les cinq placements. Une amélioration sans contrepartie domine objectivement la référence sur les métriques qualifiées ; un compromis demande d'arbitrer les gains et pertes affichés.
9. Demander l'Explain du placement le plus intéressant afin de voir quelles capacités expliquent les différences.

Le moteur ne recommande pas automatiquement un achat ou une montée de niveau. Il expose ce que change la composition testée et les limites de la comparaison.

## 12. Tutoriel 2 — « Je viens d'améliorer un club »

Supposons que Cyclotron passe du niveau 12 au niveau 13.

1. Faire une copie de sauvegarde de `data/user/inventory.json` si l'on souhaite conserver l'ancien état.
2. Dans l'entrée `cyclotron`, remplacer `"current_level": 12` par `"current_level": 13`.
3. Mettre à jour `cards_owned`, `cards_required_for_next_upgrade`, `upgrade_available`, `observed_at` et `source` avec les nouvelles informations réelles.
4. Enregistrer puis lancer `pga-shootout user-validate`.
5. Lancer `pga-shootout recommend-interactive` et choisir le mode **Réel**.
6. Refaire l'analyse du même sac et du même club.
7. Comparer chaque métrique et consulter l'Explain. Les valeurs de niveau lues par les capacités y apparaissent.

L'application ne conserve pas encore automatiquement un historique avant/après. Pour une comparaison exacte avec l'ancien niveau, conserver la sortie précédente ou une copie de l'ancien fichier.

## 13. Tutoriel 3 — « Je souhaite comparer deux placements »

La méthode la plus simple est interactive :

1. Lancer `pga-shootout recommend-interactive`.
2. Choisir un sac et un club entrant.
3. Choisir Réel ou Scénario.
4. Repérer les deux numéros de placement à comparer dans le tableau des cinq résultats.
5. Comparer leurs gains, pertes, catégories et avertissements.
6. Ouvrir l'Explain du premier placement, puis relancer la commande pour ouvrir celui du second.

Pour reproduire précisément une analyse hypothétique en ligne de commande :

```powershell
pga-shootout recommend-placement par3_divebomb cyclotron --scenario-level 12 --partial
```

Cette commande affiche les cinq placements. Pour analyser un remplacement déterminé, par exemple la position 2 :

```powershell
pga-shootout recommend-replacement par3_divebomb jumpstart cyclotron --position 2 --scenario-level 12 --partial
```

Le mode `--partial` conserve les éléments calculables et liste le reste. Il ne faut pas interpréter l'absence d'une contribution non résolue comme un bonus nul.

## 14. Sauvegarder ses modifications

Enregistrer les fichiers JSON dans l'éditeur puis toujours exécuter :

```powershell
pga-shootout user-validate
```

Une copie locale simple peut être créée avec :

```powershell
Copy-Item -Recurse data/user data/user.backup
```

Avec Git, on peut conserver un historique local :

```powershell
git status
git add data/user
git commit -m "data: update my inventory and bags"
```

Ne pousser ces données vers GitHub que si l'on accepte qu'elles soient stockées sur le dépôt distant et visibles selon sa confidentialité.

Pour récupérer ultérieurement les mises à jour du projet, sauvegarder d'abord ses données utilisateur puis exécuter `git pull`. En cas de conflit dans `data/user/`, ne pas écraser aveuglément sa version.

## 15. Erreurs courantes

| Symptôme | Cause probable | Résolution |
|---|---|---|
| `py` ou `python` n'est pas reconnu | Python absent ou non ajouté au PATH | Installer Python 3.11+ et rouvrir PowerShell. |
| L'activation des scripts est interdite | Politique PowerShell restrictive | Exécuter `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, puis réactiver `.venv`. Ce réglage ne vaut que pour la session. |
| `pga-shootout` n'est pas reconnu | Environnement inactif ou projet non installé | Activer `.venv`, puis lancer `python -m pip install -e .`. |
| Un chemin de données est introuvable | Commande lancée hors de la racine du projet | Revenir dans le dossier contenant `pyproject.toml`. |
| `user-validate` signale un JSON invalide | Virgule finale, guillemets ou accolades incorrects | Corriger le fichier indiqué, idéalement avec un éditeur JSON. |
| Identifiant de club inconnu | `club_id` inventé ou mal orthographié | Copier l'identifiant exact depuis `clubs_official.json`. |
| Sac invalide | Il ne contient pas exactement cinq clubs uniques | Corriger `club_ids` et conserver l'ordre réel. |
| `upgrade_available` est incohérent | Le booléen ne correspond pas au nombre de cartes | Utiliser `true` si et seulement si les cartes possédées atteignent le seuil. |
| Tous les placements sont exclus en mode Réel | Au moins un niveau ou une entrée d'inventaire manque | Renseigner les vrais niveaux nécessaires ou utiliser explicitement le mode Scénario. |
| Une capacité apparaît non résolue | Règle non implémentée ou ambiguë | Conserver l'avertissement ; ne pas assimiler cette capacité à zéro. |
| Les accents s'affichent mal ou une erreur mentionne `UnicodeEncodeError` | Encodage de console non UTF-8 | Exécuter `$env:PYTHONUTF8 = "1"` dans la session avant de relancer l'application ; Windows Terminal est recommandé. |
| L'installation ne trouve pas `setuptools` | Connexion Internet absente ou filtrée | Vérifier la connexion et le pare-feu, puis relancer `python -m pip install -e .`. |

## 16. Étapes encore techniques et améliorations possibles

Le premier lancement fonctionne aujourd'hui, mais plusieurs manipulations restent peu accueillantes :

- les cinq fichiers utilisateur doivent être présents et modifiés à la main ; un assistant de création de profil réduirait les erreurs ;
- l'ajout d'un club demande de connaître le schéma JSON ; une commande guidée pourrait rechercher le club par son nom et valider ses cartes ;
- la création d'un sac demande cinq identifiants officiels ; un éditeur interactif de sac pourrait proposer seulement les clubs débloqués ;
- le lancement exige Python, un environnement virtuel et PowerShell ; un paquet autonome ou un raccourci de démarrage simplifierait l'installation ;
- aucune capture historique ne compare automatiquement un club avant et après amélioration ;
- l'Explain de deux placements doit être consulté en deux sessions interactives ; une vue côte à côte serait plus directe ;
- les données personnelles vivent dans le dépôt ; un dossier de profil externe éviterait de les inclure accidentellement dans un push Git.

Ces améliorations ne sont pas nécessaires au fonctionnement actuel et ne sont pas implémentées dans ce guide.

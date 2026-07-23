# Premier lancement de PGA Shootout

## Démarrage en quatre étapes

1. Installez **Python 3.11 ou une version plus récente** depuis [python.org](https://www.python.org/downloads/). Pendant l'installation, cochez **Add Python to PATH**.
2. Téléchargez le projet, décompressez-le si nécessaire, puis ouvrez son dossier.
3. Double-cliquez sur **`DEMARRER_PGA_SHOOTOUT.bat`**.
4. Suivez les menus en français.

C'est tout. Il n'est pas nécessaire de connaître Python, Git, PowerShell ou JSON. Le premier démarrage peut prendre quelques minutes et nécessite une connexion Internet. Les démarrages suivants sont plus rapides.

## Ce que prépare le lanceur

Le lanceur travaille uniquement dans le dossier du projet. Il :

- vérifie que Python 3.11 ou une version plus récente est disponible ;
- crée l'environnement isolé `.venv` s'il n'existe pas ;
- conserve sous le nom `.venv_incompatible` un ancien environnement utilisant une version trop vieille de Python ;
- installe localement le projet si nécessaire ;
- active l'affichage UTF-8 pour les accents et les flèches ;
- ouvre le menu principal ;
- garde la fenêtre ouverte si une erreur survient et affiche une explication simple.

L'application est écrite en Python. Il n'y a rien à compiler et aucune base de données à installer.

## Le menu principal

Après le double-clic, ce menu apparaît :

```text
PGA Shootout Assistant

Que souhaitez-vous faire ?

1 - Tester un nouveau club dans un sac
2 - Consulter ou modifier mes clubs
3 - Créer ou modifier un sac
4 - Vérifier mes données
5 - Tester un club en mode Scénario
6 - Quitter
```

Répondez toujours avec le numéro affiché. Une mauvaise saisie ne ferme pas l'application : le menu redemande simplement un choix valide.

## Tout premier lancement

Si les cinq fichiers personnels n'existent pas, l'application les crée avec une structure vide et valide. Elle ne remplace jamais silencieusement un fichier déjà présent.

Lorsque moins de cinq clubs sont enregistrés ou qu'aucun sac n'existe, l'assistant propose la première configuration :

1. rechercher et ajouter au moins cinq clubs possédés ;
2. saisir leur niveau et leurs cartes ;
3. nommer un premier sac ;
4. choisir ses clubs aux positions 1 à 5 ;
5. valider automatiquement les données ;
6. tester immédiatement un autre club si vous le souhaitez.

Vous pouvez reporter cette configuration et la reprendre plus tard avec les choix 2 et 3 du menu principal.

## Ajouter ou modifier un club

Choisissez **2 - Consulter ou modifier mes clubs**, puis **Ajouter ou modifier un club**.

L'assistant demande :

1. une partie du nom affiché dans le jeu ;
2. le club correspondant parmi les résultats officiels ;
3. son niveau actuel — appuyez directement sur Entrée s'il est inconnu ;
4. le nombre de cartes possédées ;
5. le nombre de cartes nécessaires à la prochaine amélioration.

L'identifiant interne est choisi automatiquement. Le statut « amélioration disponible » est calculé à partir des cartes : vous ne le saisissez jamais vous-même.

### Exemple — je viens d'obtenir Cyclotron

```text
Recherchez le club par son nom :
> Cyclotron

Club trouvé :
1 - Cyclotron
> 1

Niveau actuel (laissez vide s'il est inconnu) :
> 12

Nombre de cartes possédées :
> 46

Cartes nécessaires à la prochaine amélioration :
> 50

Cyclotron a été enregistré et les données ont été validées.
Amélioration non disponible.
```

Si Cyclotron était déjà enregistré, les nouvelles informations remplacent son ancienne entrée sans créer de doublon.

### Exemple — je viens d'améliorer Cyclotron

Refaites exactement le même parcours, recherchez Cyclotron, puis saisissez son nouveau niveau et ses nouveaux nombres de cartes. Une sauvegarde de l'état précédent est créée avant la modification.

### Corriger une erreur

Le même menu permet :

- d'afficher les clubs connus ;
- de marquer un club comme non possédé ;
- de supprimer une entrée ajoutée par erreur après confirmation.

## Créer ou modifier un sac

Choisissez **3 - Créer ou modifier un sac**.

Pour créer un sac :

1. donnez-lui un nom lisible ;
2. choisissez un club possédé pour la position 1 ;
3. recommencez pour les positions 2 à 5 ;
4. vérifiez l'ordre récapitulé.

Un club déjà choisi disparaît des choix suivants : les doublons sont donc impossibles. Il faut avoir enregistré au moins cinq clubs possédés.

### Exemple complet

```text
Nom du nouveau sac :
> Mon sac par 3

Position 1 — choisissez un club :
> High Flight

Position 2 — choisissez un club :
> Cyclotron

Position 3 — choisissez un club :
> Ember

Position 4 — choisissez un club :
> Maelstrom

Position 5 — choisissez un club :
> Sunstorm

Le sac « Mon sac par 3 » a été enregistré et validé.
```

Les menus permettent également de remplacer toute la composition d'un sac existant ou de supprimer un sac après confirmation.

## Tester un nouveau club

Choisissez **1 - Tester un nouveau club dans un sac**.

L'application demande :

1. le sac enregistré à analyser ;
2. le club possédé à tester ;
3. le mode **Réel** ou **Scénario** ;
4. le niveau hypothétique si le mode Scénario est choisi.

Elle évalue automatiquement les cinq placements possibles, puis revient au menu principal.

### Exemple — tester Cyclotron

```text
Choisissez un sac :
1 - Mon sac par 3
> 1

Choisissez un club à tester :
1 - Cyclotron
> 1

Choisissez le mode :
1 - Réel
2 - Scénario
> 2

Niveau de scénario :
> 12

Analyse...
```

Le choix **5 - Tester un club en mode Scénario** ouvre le même parcours, mais sélectionne directement le mode Scénario.

## Mode Réel ou mode Scénario

- **Réel** utilise les niveaux enregistrés dans votre inventaire. Les niveaux des cinq clubs du sac et du club testé doivent être connus.
- **Scénario** applique un niveau hypothétique commun. Il permet d'explorer une idée, mais ne représente pas nécessairement votre inventaire actuel.

Un niveau manquant en mode Réel exclut honnêtement le placement au lieu d'inventer une valeur.

## Comprendre les résultats

Chaque placement reçoit une description factuelle :

- **amélioration sans contrepartie** : au moins une métrique prise en charge progresse et aucune ne régresse ;
- **compromis** : certaines métriques progressent et d'autres régressent ;
- **neutre** : aucune métrique prise en charge ne change ;
- **exclu** : les informations disponibles ne permettent pas une comparaison correcte.

Les gains et pertes sont séparés par métrique : Power, Control, Spin, Loft, Launch Angle, Wind Resistance et les autres valeurs prises en charge. Aucun score global caché n'est calculé.

Prenez toujours en compte les avertissements :

- **information manquante** : un niveau réel n'est pas renseigné ;
- **capacité non encore prise en charge** : son influence n'est pas comptée comme zéro ;
- **niveau hypothétique** : le résultat appartient au mode Scénario ;
- **inventaire incomplet** : d'autres clubs peuvent exister sans être enregistrés ;
- **effet différé** : il est identifié, mais aucune partie complète n'est simulée.

Vous pouvez demander l'explication détaillée d'un placement. Elle montre les statistiques de départ, les capacités appliquées, les contributions et les valeurs finales.

## Vérifier ses données

Le choix **4 - Vérifier mes données** affiche simplement :

- le nombre de clubs enregistrés ;
- le nombre de sacs ;
- si les données sont valides ;
- si l'inventaire est déclaré complet ou partiel.

Chaque modification guidée déclenche également cette validation automatiquement. En cas d'erreur, l'ancienne version est restaurée.

## Sauvegardes et données personnelles

Les données personnelles restent dans `data/user/`. Avant chaque modification, l'application copie les cinq fichiers dans :

```text
data/user/backups/AAAAJJMM-HHMMSS-microsecondes/
```

Le catalogue officiel se trouve dans `data/normalized/` et la capture brute dans `data/raw/`. Les assistants ne les modifient jamais.

Si des données existantes sont invalides au démarrage, l'application explique le problème et demande une confirmation avant de repartir avec des fichiers vides. Les anciens fichiers sont sauvegardés auparavant.

## Problèmes courants

| Problème | Solution |
|---|---|
| Le message indique que Python manque | Installez Python 3.11+ depuis python.org, cochez **Add Python to PATH**, puis redémarrez le lanceur. |
| L'installation ne trouve pas `setuptools` | Vérifiez la connexion Internet et le pare-feu, puis relancez le fichier `.bat`. |
| L'ancien environnement Python est incompatible | Le lanceur le conserve dans `.venv_incompatible` et en crée normalement un nouveau. Fermez les programmes Python si le déplacement échoue. |
| Tous les placements sont exclus en mode Réel | Complétez les niveaux des six clubs concernés ou utilisez explicitement le mode Scénario. |
| Aucun club n'est proposé pour un sac | Ajoutez au moins cinq clubs et marquez-les comme possédés. |
| Une capacité est non prise en charge | Conservez l'avertissement : son effet n'est pas assimilé à zéro. |
| La fenêtre affiche une erreur | Lisez le message conservé à l'écran. Les données sont sauvegardées avant chaque modification. |

## Utilisation avancée — commandes techniques

Cette section n'est pas nécessaire pour l'utilisation normale.

Installation manuelle depuis PowerShell :

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
$env:PYTHONUTF8 = "1"
python -m pip install -e .
```

Ouvrir le menu principal sans le fichier `.bat` :

```powershell
pga-shootout assistant
```

Vérifier le projet et les données :

```powershell
pga-shootout user-validate
pga-shootout validate-data data/raw/pga_club_stats_extract_v2_2026-07-21.json data/normalized/clubs_official.json
python -m unittest discover -s tests
```

Les commandes historiques `recommend-interactive`, `recommend-placement`, `recommend-replacement`, `compare-bags` et `evaluate-bag` restent compatibles.

La modification manuelle des fichiers JSON reste possible pour le dépannage ou l'import en masse, mais elle n'est plus requise. Toujours conserver des guillemets doubles, enregistrer en UTF-8 et lancer `pga-shootout user-validate` après une modification manuelle.

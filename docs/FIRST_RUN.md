# Premier lancement de PGA Shootout

## Démarrage en quatre étapes

1. Installez **Python 3.11 ou une version plus récente** depuis [python.org](https://www.python.org/downloads/). Pendant l'installation, cochez **Add Python to PATH**.
2. Téléchargez le projet, décompressez-le si nécessaire, puis ouvrez son dossier.
3. Double-cliquez sur **`DEMARRER_PGA_SHOOTOUT.bat`**.
4. Suivez les menus en français.

C'est tout. Il n'est pas nécessaire de connaître Python, Git, PowerShell ou JSON. Le premier démarrage peut prendre quelques minutes et nécessite une connexion Internet. Les démarrages suivants sont plus rapides.

Pour ouvrir directement l'optimiseur graphique, utilisez ensuite
**`OPTIMISER_MES_SACS.bat`**.

## Ce que prépare le lanceur

Le lanceur travaille uniquement dans le dossier du projet. Il :

- vérifie que Python 3.11 ou une version plus récente est disponible ;
- crée l'environnement isolé `.venv` s'il n'existe pas ;
- conserve sous le nom `.venv_incompatible` un ancien environnement utilisant une version trop vieille de Python ;
- installe localement le projet si nécessaire ;
- active l'affichage UTF-8 pour les accents et les flèches ;
- ouvre le menu principal ;
- garde la fenêtre ouverte si une erreur survient et affiche une explication simple.

L'application est écrite en Python. Il n'y a rien à compiler ni aucun serveur de base de données à installer : Python fournit SQLite et l'application crée sa base locale automatiquement.

## Catalogue, inventaire et version des données

Le **catalogue** décrit les 88 clubs publiés par le jeu (statistiques, capacités,
marques, types et niveaux). Il est en lecture seule dans les menus. Votre
**inventaire** indique seulement les clubs que vous avez examinés, ceux que vous
possédez et les niveaux/cartes que vous connaissez. L'absence d'un club de votre
inventaire ne signifie donc jamais qu'il est verrouillé.

Au premier démarrage de cette version, les anciens JSON sont sauvegardés puis
migrés automatiquement vers `data/pga_shootout.sqlite`. Pour actualiser vos
clubs, utilisez directement l'éditeur visuel décrit ci-dessous.

## Mettre à jour mon inventaire — parcours normal

1. Double-cliquez sur **`GERER_MON_INVENTAIRE.bat`**.
2. Recherchez un club par son nom ou filtrez par marque, type, rareté, possession
   ou données incomplètes.
3. Cliquez sur la case **Possédé**, puis double-cliquez sur **Niveau** ou
   **Cartes possédées**. Ce sont les deux seules valeurs de progression à saisir ;
   une cellule vide signifie « inconnu ».
4. Modifiez autant de clubs que nécessaire, puis cliquez sur **Enregistrer toutes
   les modifications**.
5. Vérifiez le résumé global et confirmez une seule fois.

Le seuil suivant est calculé automatiquement à partir de la rareté et du niveau.
Les colonnes **Progression**, **Cartes restantes** et **Amélioration disponible**
se mettent à jour dès qu'un niveau ou un nombre de cartes est validé. À
l'ouverture d'une cellule, sa valeur est sélectionnée afin que la première frappe
la remplace. `Tab` passe à la cellule modifiable suivante ; `Entrée` valide puis
rend le focus au tableau sur la même ligne. Les filtres et la position de la liste
sont conservés. Si le niveau est inconnu,
l'éditeur conserve l'ancien seuil observé lorsqu'il existe ; sinon il affiche
« Inconnu ». Le coût d'un passage de niveau 12 vers Elite reste inconnu tant qu'il
n'est pas présent dans les données validées.

Les clubs suivent l'ordre du jeu : Corvid, Forester, Nautilus, Palo, Phoenix,
Ryusei, Stanchion, Willoughsby, Mythical ; puis Putter, Driver, Wood, Hybrid,
Iron et Wedge dans chaque marque. Les catégories futures inconnues apparaîtront
ensuite par ordre alphabétique.

L'éditeur affiche les 88 clubs officiels sur un écran unique. Une ligne jaune a
été modifiée sans être enregistrée ; une ligne rouge contient une erreur avec une
explication française dans la dernière colonne. Le bouton d'annulation restaure
instantanément toutes les valeurs chargées, sans toucher à la base.

### Exemple — Blacksmith

Recherchez `Blacksmith`, cochez **Possédé**, saisissez son niveau s'il est connu
et laissez Cartes possédées vide si vous ne les connaissez pas. La valeur
`0` saisie dans Cartes signifie réellement zéro et reste différente d'une cellule
vide. Vous pouvez ensuite rechercher d'autres clubs avant d'enregistrer.

La version et la provenance du catalogue apparaissent dans
`docs/DATA_DASHBOARD.md`. Le catalogue actuel est une vérification du 4 août 2026
de la source officielle annoncée au 14 juin 2026. Certaines futures demandes
d'optimisation restent impossibles lorsqu'elles exigent une portée réelle, la
géométrie d'un parcours ou une physique non validée. L'application doit alors le
dire, jamais inventer une conversion. Les exemples Power/Control/portée ne sont
pas des modes fermés : ils illustrent un contrat générique extensible.

## Le menu principal

Après le double-clic, ce menu apparaît :

```text
PGA Shootout Assistant

Que souhaitez-vous faire ?

1 - Gérer mon inventaire
2 - Gérer mes sacs
3 - Optimiser mes sacs
4 - Tester un club dans un sac
5 - Quitter
```

Répondez toujours avec le numéro affiché. Une mauvaise saisie ne ferme pas l'application : le menu redemande simplement un choix valide.

## Optimiser mes sacs — parcours normal

1. Double-cliquez sur **`OPTIMISER_MES_SACS.bat`**, ou choisissez
   **3 - Optimiser mes sacs** dans le menu principal.
2. Choisissez une stratégie par son nom, par exemple **Sac Par 3**.
3. Conservez le mode **Réel** pour utiliser vos niveaux enregistrés.
4. Choisissez 5, 10 ou 20 propositions, puis cliquez sur
   **Lancer l'analyse**.
5. Sélectionnez une proposition dans la liste de gauche.
6. Consultez à droite les onglets des étapes, les statistiques finales et
   **Pourquoi ces clubs ?**.
7. Utilisez **Exporter en JSON**, **Exporter en texte** ou
   **Copier le résumé du sac** si nécessaire.

Pendant le calcul, la barre animée et le message « Analyse en cours… » indiquent
que l'application travaille. La fenêtre reste utilisable et interdit un second
lancement simultané.

Les propositions ne sont pas présentées comme un meilleur sac absolu. La portée
réelle et la réussite du putt ne sont pas encore modélisées, et la recherche est
intelligemment réduite plutôt qu'exhaustive. L'encart jaune rappelle toujours
ces limites. Les statistiques `Power`, `Control` et `Spin` affichent la valeur de
base, la valeur finale et leur différence. Une statistique absente apparaît
`—`, jamais zéro. Les onglets utilisent les noms lisibles des étapes définis par
la stratégie ; un club peut donc avoir des valeurs différentes entre le départ,
l'approche et le putt.

Le mode **Scénario** applique uniquement le niveau hypothétique saisi. Il ne
modifie pas votre inventaire. Les options avancées permettent de réduire ou
d'augmenter la limite de sécurité du calcul ; elles peuvent normalement rester
fermées.

Le bouton **Gérer mon inventaire** ouvre l'éditeur visuel existant sans fermer
l'optimiseur.

## Tout premier lancement

Si des fichiers personnels historiques existent, l'application les sauvegarde et les migre dans SQLite sans les remplacer. Sur une installation neuve, l'assistant initialise des données personnelles valides. Il ne remplace jamais silencieusement une donnée existante.

Pour une première configuration, ouvrez d'abord l'éditeur visuel, indiquez au
moins cinq clubs possédés, enregistrez-les, puis utilisez **2 - Gérer mes sacs**.

## Créer ou modifier un sac

Choisissez **2 - Gérer mes sacs**.

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

## Sauvegardes et données personnelles

Les données personnelles normales sont dans `data/pga_shootout.sqlite`. Avant
chaque enregistrement global, l'application crée une sauvegarde complète dans :

```text
data/backups/pga_shootout-AAAAJJMM-HHMMSS-microsecondes.sqlite
```

Le catalogue officiel se trouve dans `data/normalized/` et la capture brute dans `data/raw/`. Les assistants ne les modifient jamais.

Toutes les lignes sont enregistrées dans une transaction unique : si une erreur
survient, aucune modification de la session n'est conservée. Les anciens JSON de
`data/user/` restent disponibles uniquement pour import, export ou dépannage.

## Problèmes courants

| Problème | Solution |
|---|---|
| Le message indique que Python manque | Installez Python 3.11+ depuis python.org, cochez **Add Python to PATH**, puis redémarrez le lanceur. |
| L'installation ne trouve pas `setuptools` | Vérifiez la connexion Internet et le pare-feu, puis relancez le fichier `.bat`. |
| L'ancien environnement Python est incompatible | Le lanceur le conserve dans `.venv_incompatible` et en crée normalement un nouveau. Fermez les programmes Python si le déplacement échoue. |
| Tous les placements sont exclus en mode Réel | Complétez les niveaux des six clubs concernés ou utilisez explicitement le mode Scénario. |
| Aucun club n'est proposé pour un sac | Ajoutez au moins cinq clubs et marquez-les comme possédés. |
| Une ligne devient rouge | Corrigez le champ indiqué dans la colonne Erreur ; les autres modifications restent en attente. |
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

L'ancien assistant textuel de gestion des clubs reste présent dans le code pour
compatibilité et dépannage, mais il n'est plus proposé dans le parcours normal.

Vérifier le projet et les données :

```powershell
pga-shootout user-validate
pga-shootout validate-data data/raw/pga_club_stats_extract_v2_2026-07-21.json data/normalized/clubs_official.json
python -m unittest discover -s tests
```

Les commandes historiques `optimize-strategy`, `recommend-interactive`, `recommend-placement`, `recommend-replacement`, `compare-bags` et `evaluate-bag` restent compatibles pour les usages avancés.

La modification manuelle des fichiers JSON reste possible pour le dépannage ou l'import en masse, mais elle n'est plus requise. Toujours conserver des guillemets doubles, enregistrer en UTF-8 et lancer `pga-shootout user-validate` après une modification manuelle.

# PGA Shootout

Moteur Python piloté par les données pour reproduire les calculs de **PGA TOUR Golf Shootout**. La priorité est la fidélité du simulateur ; l’optimisation des sacs viendra après sa validation.

## Démarrage utilisateur sous Windows

Installez Python 3.11 ou une version plus récente, puis double-cliquez sur **`DEMARRER_PGA_SHOOTOUT.bat`**. Le lanceur prépare l'application et ouvre les menus guidés en français. Voir [docs/FIRST_RUN.md](docs/FIRST_RUN.md).

## État

Le socle fournit des modèles immuables, un chargeur JSON, des conditions séparées des effets, un registre de mécanismes extensible, un moteur de règles minimal et un journal Explain détaillé. Aucune capacité propre à un club n’est codée en dur.

## Installation et tests

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -v
```

## Données

Placer le fichier officiel `pga_club_stats_extract_v2_2026-07-21.json` dans `data/raw/`. Les données brutes ne sont ni modifiées ni interprétées silencieusement par le chargeur.

Le catalogue des artefacts attendus, leurs invariants et les règles d'import sont décrits dans [DATA_MANIFEST.md](DATA_MANIFEST.md).

Valider la provenance et la structure des données importées :

```powershell
pga-shootout validate-data data/raw/pga_club_stats_extract_v2_2026-07-21.json data/normalized/clubs_official.json
```

## CLI

```powershell
pga-shootout inspect data/raw/pga_club_stats_extract_v2_2026-07-21.json
pga-shootout normalize
pga-shootout coverage
pga-shootout inventory-status
pga-shootout inventory-status --json
pga-shootout inventory-status --write-reports
pga-shootout evaluate-bag par3_divebomb --scenario-level 12 --partial
pga-shootout evaluate-bag par3_divebomb --scenario-level 12 --strict
pga-shootout compare-bags par3_divebomb par3_high_flight --scenario-level 12 --position 1 --partial
pga-shootout recommend-replacement par3_divebomb jumpstart cyclotron --scenario-level 12 --partial
pga-shootout recommend-placement par3_divebomb cyclotron --scenario-level 12 --partial
pga-shootout recommend-placement par3_divebomb cyclotron --scenario-level 12 --partial --json
pga-shootout recommend-interactive
pga-shootout assistant
```

`--scenario-level` applique explicitement un niveau hypothétique commun. L'ancien `--level` reste un alias temporaire. Pour les commandes de recommandation, l'absence de cette option active le mode réel : chaque niveau doit alors provenir de l'inventaire et toute valeur manquante exclut le candidat.

`normalize` régénère les artefacts structurels à partir de `clubs_official.json`. Il ne déduit aucune mécanique de jeu.

`coverage` compare ces artefacts au registre courant et régénère `docs/MECHANIC_COVERAGE.md`.

`inventory-status` recalcule l'état opérationnel des clubs possédés depuis le catalogue, le registre moteur et `data/user/`. La sortie humaine, la sortie JSON et les rapports `docs/INVENTORY_STATUS.md` / `docs/PROJECT_STATUS.md` partagent exactement le même audit.

Le mode `strict` échoue sur une mécanique inconnue. Le mode `partial` conserve le résultat calculable et signale explicitement chaque élément non évalué.

`compare-bags` compare la composition et le club occupant la même position dans deux sacs. Il affiche les statistiques de base, l'impact des capacités, les statistiques finales, les bonus gagnés ou perdus et les bonus non résolus, sans inventer de score global ni de poids de préférence.

`recommend-placement` teste les cinq emplacements du club entrant fourni, évalue chaque composition sur les cinq positions et présente les améliorations Pareto, compromis, placements neutres et exclusions. Il ne parcourt pas encore automatiquement l'inventaire.

`recommend-interactive` guide l'utilisateur par les noms lisibles des sacs et clubs, puis permet d'ouvrir l'Explain détaillé d'un placement. Voir [docs/INTERACTIVE_CLI.md](docs/INTERACTIVE_CLI.md).

Pour une installation complète depuis un ordinateur neuf, la création d'un inventaire et le premier essai guidé, voir [docs/FIRST_RUN.md](docs/FIRST_RUN.md).

## Données utilisateur

Les informations du joueur vivent exclusivement dans `data/user/` et ne modifient ni le catalogue officiel ni les règles du simulateur.

```powershell
pga-shootout user-validate
pga-shootout user-account
pga-shootout user-inventory
pga-shootout user-upgrades
pga-shootout user-bags
```

L'inventaire est explicitement partiel : un club absent reste de statut inconnu et n'est pas considéré comme verrouillé.

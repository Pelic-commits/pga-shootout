# PGA Shootout

Moteur Python piloté par les données pour reproduire les calculs de **PGA TOUR Golf Shootout**. La priorité est la fidélité du simulateur ; l’optimisation des sacs viendra après sa validation.

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
pga-shootout evaluate-bag par3_divebomb --level 12 --partial
pga-shootout evaluate-bag par3_divebomb --level 12 --strict
```

Le niveau est un niveau de scénario explicite, jamais déduit de l'inventaire utilisateur tant que les niveaux réels sont inconnus.

`normalize` régénère les artefacts structurels à partir de `clubs_official.json`. Il ne déduit aucune mécanique de jeu.

Le mode `strict` échoue sur une mécanique inconnue. Le mode `partial` conserve le résultat calculable et signale explicitement chaque élément non évalué.

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

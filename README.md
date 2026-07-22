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

## CLI

```powershell
pga-shootout inspect data/raw/pga_club_stats_extract_v2_2026-07-21.json
```

Le mode `strict` échoue sur une mécanique inconnue. Le mode `partial` conserve le résultat calculable et signale explicitement chaque élément non évalué.

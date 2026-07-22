# Data Manifest — PGA Shootout Solver

## Source brute prioritaire

`pga_club_stats_extract_v2_2026-07-21.json`

- source officielle Concrete Software ;
- 88 clubs ;
- 9 marques ;
- textes, tableaux, HTML et images ;
- fichier immuable après dépôt dans `data/raw/`.

## Couche normalisée déjà préparée

- `clubs_official.json`
- `ability_occurrences.json`
- `ability_labels.json`
- `mechanics_catalog.json`
- `semantic_map.json`
- `assets.json`
- `normalization_report.json`
- `ABILITY_AUDIT.md`

Organisation recommandée :

```text
data/
├── raw/
│   └── pga_club_stats_extract_v2_2026-07-21.json
└── normalized/
    ├── clubs_official.json
    ├── ability_occurrences.json
    ├── ability_labels.json
    ├── mechanics_catalog.json
    ├── semantic_map.json
    ├── assets.json
    └── normalization_report.json
```

Contrôles attendus :

- 88 clubs ;
- 9 marques ;
- 162 occurrences ;
- 125 intitulés uniques ;
- 1333 valeurs converties ;
- 0 valeur non reconnue ;
- 0 capacité non classée.

Règles :

- ne jamais modifier le brut ;
- conserver le texte officiel ;
- distinguer valeur officielle et interprétation ;
- conserver les incohérences ;
- enregistrer version de schéma et hash SHA-256.

## État au 22 juillet 2026

Aucun de ces artefacts n'est encore présent dans le dépôt. Des copies externes de `pga_club_stats_extract_v2_2026-07-21.json`, `clubs_official.json` et `ABILITY_AUDIT.md` ont été fournies, mais leur import doit faire l'objet d'un commit de données séparé.

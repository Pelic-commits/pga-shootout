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

Artefacts importés sans transformation :

| Fichier | SHA-256 |
|---|---|
| `data/raw/pga_club_stats_extract_v2_2026-07-21.json` | `449831121cada54114ac8175af38b99ab8bd6ecf15310600a1df9192ca703a14` |
| `data/normalized/clubs_official.json` | `76d298789030964a32cd4b047cba2598cc5b647b61a90b13ca962767f3417a85` |
| `docs/ABILITY_AUDIT.md` | `0e20a88a63536be87837b9f2dfee67e3ade1f9a0bc38f68a8deef5c6f7cd338a` |

Contrôles automatisés présents : lien SHA-256 entre le normalisé et le brut, compteurs de clubs et marques, unicité des identifiants, occurrences de capacités et valeurs converties.

Artefacts encore absents : `ability_occurrences.json`, `ability_labels.json`, `mechanics_catalog.json`, `semantic_map.json`, `assets.json` et `normalization_report.json`.

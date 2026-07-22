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

Artefacts structurels générés automatiquement depuis `clubs_official.json` :

| Fichier | SHA-256 |
|---|---|
| `ability_occurrences.json` | `884daf05d7ec2c02f12d5adbf305894007f8bf95097b3574a7c30df83bf9a512` |
| `ability_labels.json` | `065e69e564d34d8e2cdcf197219af5e8d1d143d362ffcfdc061b9517150adb5` |
| `mechanics_catalog.json` | `e69f8b9853d0ca0b5212e378f3b8fa703d918401f921b93b0da92b270c4a0f76` |
| `semantic_map.json` | `d57344fb7d62ff486800fa23ece6ef8b3bcd7fa9d061b03c1c0926ae13cd6ef7` |
| `normalization_report.json` | `0700c37302cc7b579d2392bbdfadc6e503b50767b760f55ba1c1535f4b46c5b9` |

Ces fichiers conservent 162 occurrences et 125 intitulés exacts. Les 125 groupes restent `uninterpreted`, avec `mechanic_id`, complexité et dépendances non renseignés. `assets.json` reste absent.

## Couche utilisateur

`data/user/` est indépendante des données officielles et contient `account.json`, `inventory.json`, `preferences.json`, `bags.json` et `observations.json`. Son inventaire est partiel (`inventory_complete: false`) et l'absence d'un identifiant ne signifie jamais que le club est verrouillé.

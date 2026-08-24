# Manifeste des données

## Catalogue officiel versionné

Source déclarée : [Concrete Software — PGA TOUR Golf Shootout Club Stats](https://concretesoftware.com/pga-tour-golf-shootout-club-stats/).

| Couche | Fichier | Rôle |
|---|---|---|
| brute | `data/raw/pga_club_stats_extract_v2_2026-07-21.json` | Capture immuable, HTML/images et données de source. |
| normalisée | `data/normalized/clubs_official.json` | Catalogue lu par le moteur. |
| structurelle | `ability_occurrences.json` | 162 occurrences, une par capacité de club. |
| structurelle | `ability_labels.json` | 125 identifiants d'intitulés. |
| structurelle | `mechanics_catalog.json` | Groupes structurels, sans interprétation implicite. |
| sémantique | `semantic_map.json` | Interprétations qualifiées séparées du catalogue. |
| contrôle | `normalization_report.json` | Compteurs, intégrité et limitations de source. |

Compteurs vérifiés dans les fichiers versionnés : **88 clubs**, **9 marques**, **162 occurrences**, **125 labels/groupes**, **1 333 valeurs de niveau converties**.

Le rapport de normalisation signale une limitation importante : le catalogue normalisé conserve labels et valeurs, mais ne contient pas les textes officiels complets pour les 162 occurrences. Les documents ne doivent donc pas prétendre que chaque texte est disponible dans cette couche.

## Invariants

- ne jamais modifier la capture brute ;
- conserver les identifiants et valeurs officielles ;
- séparer donnée officielle, interprétation et observation utilisateur ;
- ne pas effacer une contradiction ;
- conserver schéma, provenance et hash ;
- ne pas promouvoir un groupe structurel en règle de jeu sans qualification.

Le hash source déclaré par le catalogue normalisé est `76d298789030964a32cd4b047cba2598cc5b647b61a90b13ca962767f3417a85`.

## Données utilisateur

`data/pga_shootout.sqlite` est la source de vérité courante pour profil, inventaire, niveaux, cartes, sacs, références, notes, observations et rôles. `data/user/` conserve les anciens JSON pour import/export et diagnostic.

L'inventaire peut être incomplet : l'absence d'un club ne signifie pas qu'il est verrouillé. Les sauvegardes SQLite sont écrites dans `data/backups/` avant les modifications importantes.

## Données de stratégie

- `data/strategies/strategies.json` : quatre stratégies et variante de vent ;
- `data/strategies/metric_semantics.json` : statut objectif/contextuel/descriptif des métriques ;
- `data/strategies/optimization_policies.json` : politique produit versionnée.

## Régénération et validation

```powershell
pga-shootout validate-data data/raw/pga_club_stats_extract_v2_2026-07-21.json data/normalized/clubs_official.json
pga-shootout normalize
pga-shootout inventory-status --write-reports
python scripts/audit_remaining_capabilities.py
```

Voir [docs/DATA_FOUNDATION.md](docs/DATA_FOUNDATION.md) et [docs/CAPABILITY_AUDIT.md](docs/CAPABILITY_AUDIT.md).

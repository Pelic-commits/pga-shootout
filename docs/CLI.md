# Commandes en ligne

La GUI Windows est l'interface principale. La CLI reste utile pour le diagnostic, les exports, les audits reproductibles et les tests avancés.

Après installation locale :

```powershell
pga-shootout --help
```

## Utilisateur et sacs

| Commande | Rôle |
|---|---|
| `assistant` | Ouvre le menu guidé français. |
| `user-validate` | Valide les données utilisateur. |
| `user-account` | Affiche le profil. |
| `user-inventory` | Liste l'inventaire connu. |
| `user-upgrades` | Liste les améliorations disponibles. |
| `user-bags` | Liste les sacs enregistrés. |
| `evaluate-bag BAG --scenario-level N --partial` | Évalue un sac via le Rule Engine. |
| `compare-bags A B --scenario-level N --position 1 --partial` | Compare deux sacs sans score global. |

Les anciennes commandes utilisateur acceptent encore `--user-dir data/user` par défaut ; l'application graphique utilise SQLite. Indiquez `--user-dir data/pga_shootout.sqlite` pour viser explicitement la source actuelle lorsque l'option le permet.

## Recommandation explicite

| Commande | Rôle |
|---|---|
| `recommend-replacement BAG SORTANT ENTRANT --partial` | Analyse un remplacement fourni. |
| `recommend-placement BAG ENTRANT --partial` | Teste les cinq placements du club fourni. |
| `recommend-interactive` | Parcours textuel guidé par noms lisibles. |

`--scenario-level` applique un niveau hypothétique commun. Sans cette option, le mode réel exige les niveaux enregistrés.

## Stratégies et optimisation

```powershell
pga-shootout strategy-list
pga-shootout strategy-show par4_long
pga-shootout strategy-show par4_long --variant head_crosswind
pga-shootout optimize-strategy par3 --partial --limit 20
pga-shootout trace-composition par3 high_flight cyclotron ember maelstrom sunstorm
```

`optimize-strategy` accepte notamment clubs obligatoires, rôles, positions verrouillées, minimums, marques autorisées, référence, mode de recherche, profondeur 1/2 et politique `same_type`/`all_types`. Consultez son aide avant un usage avancé :

```powershell
pga-shootout optimize-strategy --help
```

## Données et audits

| Commande | Rôle |
|---|---|
| `inspect PATH` | Inspecte un JSON brut sans hypothèse de schéma. |
| `validate-data RAW NORMALIZED` | Vérifie provenance, structure et compteurs. |
| `data-init --preview` | Prévisualise l'initialisation/migration SQLite. |
| `catalog-diff` | Compare les versions retenues du catalogue. |
| `data-export --output-dir DIR` | Exporte SQLite en JSON diagnostique. |
| `data-dashboard` | Régénère le tableau de bord de données historique. |
| `normalize` | Régénère les artefacts structurels sans interprétation. |
| `coverage` | Régénère l'ancien rapport de couverture mécanique. |
| `user-gaps` / `reference-gaps` | Régénèrent les anciennes matrices de lacunes. |
| `inventory-status` | Produit l'audit opérationnel de l'inventaire actuel. |

Rapport de référence actuel :

```powershell
pga-shootout inventory-status --write-reports
python scripts/audit_remaining_capabilities.py
```

Les commandes de génération historiques restent supportées, mais leurs rapports sont des diagnostics datés et non une roadmap active.

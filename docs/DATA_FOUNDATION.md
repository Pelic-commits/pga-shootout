# Données, catalogue et SQLite

## Sources de vérité

1. `data/normalized/clubs_official.json` : catalogue versionné utilisé par le moteur ;
2. `data/pga_shootout.sqlite` : état utilisateur courant ;
3. `data/raw/pga_club_stats_extract_v2_2026-07-21.json` : capture brute conservée ;
4. `data/user/*.json` : format historique d'import/export et diagnostic.

Le catalogue contient 88 clubs, 9 marques et 162 occurrences de capacités. Sa provenance est la page [Concrete Software — PGA TOUR Golf Shootout Club Stats](https://concretesoftware.com/pga-tour-golf-shootout-club-stats/). Aucune requête réseau n'est nécessaire au fonctionnement courant.

## Catalogue versionné

La normalisation conserve niveaux, statistiques, labels, valeurs par niveau et provenance. Les artefacts `ability_occurrences.json`, `ability_labels.json`, `mechanics_catalog.json`, `semantic_map.json` et `normalization_report.json` permettent l'audit reproductible.

`normalize` ne déduit aucune mécanique. Les interprétations validées sont séparées dans la carte sémantique et exécutées par les registres du moteur.

## SQLite utilisateur

La base contient principalement :

- `user_profile` : profil ;
- `inventory_state` : complétude et provenance de l'inventaire ;
- `user_clubs` : possession, niveau, cartes et métadonnées ;
- `user_bags` / `user_bag_clubs` : sacs et positions ;
- `user_preferences` : préférences ;
- `user_observations` : observations factuelles ;
- `user_change_log` : journal des changements ;
- `migration_runs` : migrations JSON→SQLite.

Les références sont stockées dans les métadonnées extensibles des sacs : libellé, usage, stratégie, club principal, statut, notes, métriques observées et rôles utilisateur.

## Éditeur d'inventaire

`GERER_MON_INVENTAIRE.bat` ouvre l'éditeur Tkinter. Les seules entrées de progression sont Possédé, Niveau et Cartes possédées. Progression, cartes restantes, seuil suivant et amélioration disponible sont calculés depuis le catalogue.

La sauvegarde est transactionnelle : toutes les lignes réussissent ou aucune n'est conservée. Une copie SQLite est créée dans `data/backups/` avant l'écriture. Recherche, filtres, tri et navigation clavier sont disponibles.

## Fraîcheur

L'optimiseur relit SQLite avant chaque analyse. Un club, niveau ou sac enregistré par l'éditeur devient donc visible sans redémarrage de la GUI.

## Import, export et maintenance

```powershell
pga-shootout data-init --preview
pga-shootout data-export --output-dir export-diagnostic
pga-shootout inventory-status --write-reports
python scripts/audit_remaining_capabilities.py
```

`data-init --preview` n'écrit rien. Une migration réelle sauvegarde les JSON sources et consigne son résultat. Les tests destructifs utilisent des bases temporaires, jamais la base réelle.

Voir [../DATA_MANIFEST.md](../DATA_MANIFEST.md) et [CAPABILITY_AUDIT.md](CAPABILITY_AUDIT.md).

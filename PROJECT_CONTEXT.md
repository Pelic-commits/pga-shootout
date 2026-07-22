# PGA Shootout Solver — Contexte du projet

> **Mémoire durable du projet.** Lire ce fichier avant toute modification importante et le maintenir après toute décision structurante.

## 1. Mission et ordre de travail

Construire un moteur capable de reproduire fidèlement les calculs de **PGA TOUR Golf Shootout**, puis utiliser ce moteur validé pour analyser et optimiser des sacs.

Ordre impératif :

1. comprendre les règles ;
2. reproduire les calculs ;
3. expliquer chaque résultat ;
4. valider dans le jeu ;
5. optimiser seulement après validation.

Le cœur du projet est un simulateur explicable confronté à des observations réelles, pas un simple générateur de recommandations.

## 2. Principes non négociables

- **Simulation avant optimisation.** Aucune optimisation n'est fiable avant validation du moteur.
- **Données avant code spécifique.** Les noms de clubs peuvent apparaître dans les données, fixtures, régressions, documentation et interface, jamais comme déclencheurs de logique métier.
- **Aucune mécanique inventée.** Conserver les sources ambiguës, documenter l'ambiguïté, marquer la mécanique non validée et utiliser `partial` si nécessaire.
- **Explain obligatoire.** Montrer base, conditions, effets appliqués ou ignorés, avant, opération, après, éléments non évalués et résultat final.
- **Traçabilité.** Distinguer source officielle, donnée normalisée, hypothèse sémantique, observation en jeu, règle validée et règle inconnue.

Architecture attendue :

```python
condition_registry.evaluate(condition, context)
mechanics_registry.execute(effect, context)
```

Un branchement du type `if club.name == "Divebomb"` est interdit dans le moteur.

## 3. Sources et données connues

Page canonique : <https://concretesoftware.com/pga-tour-golf-shootout-club-stats/>

Capture documentaire primaire : `pga_club_stats_extract_v2_2026-07-21.json`.

- 88 clubs et 9 marques ;
- tableaux de niveau, textes et descriptions de capacités conservés ;
- HTML et références d'images conservés ;
- extraction du 21 juillet 2026 ;
- page indiquée comme mise à jour le 14 juin 2026.

Artefacts normalisés préparés en dehors du dépôt :

- `clubs_official.json` ;
- `ability_occurrences.json` ;
- `ability_labels.json` ;
- `mechanics_catalog.json` ;
- `semantic_map.json` ;
- `assets.json` ;
- `normalization_report.json` ;
- `ABILITY_AUDIT.md`.

Résultats annoncés de l'audit V2 : 88/88 clubs, 9 marques, 162 occurrences de capacités, 125 intitulés uniques, 156 variantes officielles uniques, 1333/1333 valeurs converties, aucune valeur non reconnue et aucune capacité non classée.

La couche officielle conserve le site. La couche sémantique est une interprétation à valider en jeu. Voir [DATA_MANIFEST.md](DATA_MANIFEST.md).

## 4. Architecture cible

```text
Data → Rule Engine → GameState → Explain Engine → EvaluationResult
```

Modules conceptuels : couche de données, modèles de domaine, registres de conditions et de mécanismes, Rule Engine, GameState, Explain Engine, EvaluationResult, CLI, puis futur Optimizer.

### Modèles fondamentaux

- `Club` : identifiant, nom, marque, type, rareté, niveau, statistiques, capacités, provenance.
- `Ability` : texte officiel, valeurs par niveau, interprétation, conditions, effets, validation et ambiguïtés.
- `Bag` : clubs ordonnés, positions, contraintes, références et scénario.
- `Condition` : ne modifie jamais l'état ; doit à terme expliquer correspondance, raison, observé et attendu.
- `Effect` : décrit une intention et délègue son exécution au registre.
- `GameState` : sac, club et position courants, terrain, vent, distance, coup précédent, historiques, bonus, effets différés, état du trou ou de partie, graine et journal.
- `EvaluationResult` : statistiques, événements Explain, avertissements, règles non supportées, hypothèses, provenance, erreurs et statut complet/partiel.

Les conditions et les effets restent strictement séparés. Un handler d'effet ne réimplémente pas sa condition. Un dictionnaire de fonctions enregistrées suffit ; aucun système de plugins complexe n'est requis à ce stade.

## 5. Ordre des calculs

L'ordre réel reste à valider. Le moteur doit rendre chaque phase explicite, éviter l'ordre accidentel et enregistrer la séquence exacte.

Phases candidates, non confirmées : base ; composition/positions ; bonus statiques du sac ; adjacence ; composition ; club courant ; contexte du coup ; coup précédent ; effets dynamiques ; hasard ; arrondis et contraintes finales.

Cette liste est une hypothèse architecturale, pas une règle du jeu.

## 6. Explain et modes d'évaluation

Un événement Explain cible à terme : identifiant séquentiel, phase, source, capacité, condition, cible, mécanique, statut (`applied`, `skipped`, `unsupported`, `error`), avant, opération, après, explication, provenance et confiance.

Conserver une forme structurée sérialisable et un rendu humain. Les tests portent prioritairement sur la structure.

- `strict` échoue si une mécanique requise manque ou si une ambiguïté interdit un résultat fiable.
- `partial` calcule le connu et signale capacités ignorées, mécaniques non supportées, champs manquants et impact potentiel. Un résultat partiel n'est jamais présenté comme exact.

## 7. Tests et validation en jeu

Pour chaque mécanique : numérique positif, condition non satisfaite, Explain, ciblage, limite et strict/partial si pertinent.

Pour les données : identifiants uniques, 88 clubs, 9 marques, niveaux cohérents, types numériques, texte et provenance conservés, valeurs reconnues et couverture des handlers.

Régression par sac : ordre exact, niveaux, contexte, valeurs observées, attendu, notes/captures et statut `observed`, `confirmed` ou `hypothesis`.

Boucle : calcul Explain → reproduction dans le jeu → comparaison → localisation du premier écart → correction → test de régression.

## 8. Scénarios de référence

Sac initial : Divebomb / Jumpstart / Steadfast / Ember / Sunstorm. Il combine chaîne, rareté, composition, type, position ou distance, mais les valeurs et l'ordre restent à valider.

Autres scénarios futurs, non démontrés comme optimums :

- par-3 High Flight : High Flight / Cyclotron / Ember / Maelstrom / Sunstorm ;
- contrôle quotidien ;
- par-3 long/vent ;
- deuxième coup/par 5 ;
- distance situationnelle.

## 9. Profil utilisateur séparé du simulateur

Préférences futures de l'optimiseur : free-to-play, aucune dépense réelle, cinq sacs, pas de balle spéciale connue, priorité au contrôle, à la prévisibilité et aux lignes sûres. Divebomb, High Flight, Maelstrom et Ember sont appréciés ; Outset est préféré à Conqueror ; Windstrike est jugé court, Skyfury peu prévisible et Lodestar faible dans certaines synergies ; le sand wedge PALO est apprécié.

Inventaire connu au 21 juillet 2026, à stocker hors catalogue officiel :

- Willoughsby : Homestead 438/500, Commonlaw 8/25, Kinship 15/50, Groundskeep 33/25, Sandsend 533/50, Steadfast 4/5 ;
- Ryusei : Jumpstart 19/100, Cyclotron 46/50, Neon Impulse 315/100, Color Theory 1/25 ;
- Corvid : High Flight 185/250, Cloudcatcher 2/25, Skyfury 2/25, Rook 714/100 ;
- PALO : Mirage 539/100, Lodestar 13/25, Green Demon 3/2 ;
- autres : Outset 59/50, Into the Breach 7/25, Conqueror 88/50.

La liste peut être incomplète. Progression connue : niveau joueur 35, objectif FedEx 50, palier maximal 5, hésitation sur le palier 6, Meteor prioritaire. Ces éléments concernent la stratégie de compte, jamais les règles du simulateur.

État implémenté au 22 juillet 2026 : `data/user/` contient cinq fichiers distincts pour le compte, l'inventaire partiel, les préférences sans poids inventés, les sacs observés et les observations personnelles. Les modèles et validateurs vivent dans `user_data.py`, sans dépendance au Rule Engine. Toute référence structurée utilise l'identifiant officiel ; une note ambiguë reste non résolue.

## 10. Catalogue sémantique préparatoire

Familles identifiées : `adjacency_scaling`, `trajectory`, `terrain_bonus`, `stat_modifier`, `terrain_interaction`, `wind`, `chain`, `position`, `ability_modification`, `shot_control`, `stateful_growth`, `random`, `adjacency`, `stat_copy`, `bag_position`, `composition_scaling`, `course_condition`, `previous_shot`, `composition_condition`, `transform`, `identity`.

Complexité estimée : 79 occurrences génériques, 54 paramétrées, 18 avec état et 11 spéciales.

Identifiants préparatoires, tous à vérifier avant handler :

```text
add_stat, add_stats, add_stats_next_shot,
adjacent_stat_bonus_with_filter_multiplier, aim_arrow_speed_multiplier,
bag_stat_and_trajectory_modifier, bag_stat_bonus_if_absent_types,
bag_stat_tradeoff_after_source, bounce_reduction,
brand_control_increase_on_hit, conditional_stat_bonus,
control_per_airtime, copy_adjacent_stat_percent,
copy_directional_stats_percent, copy_last_used_club_abilities,
counts_as_all_brands, destroy_random_club_and_steal_stats,
duplicate_ability_instances, fade_draw_multiplier,
first_hazard_or_tree_event_stat_growth, gem_ball_bonus_multiplier,
grant_source_base_stats_to_replacements, gravity_reduction,
groundspin_multiplier, hole_magnetism_radius, loft_angle_delta,
multi_stat_tradeoff, mutual_adjacent_stat_bonus,
named_ability_multiplier_on_course, named_ability_value_multiplier,
power_per_ground_roll_time, power_per_wind_speed,
pullback_power_tradeoff, random_stat_bonus,
replace_source_with_random_clubs, self_stat_bonus_if_absent_types,
self_stat_per_adjacent_filter, self_stats_increase_after_hit,
share_named_ability_with_adjacent, share_source_stats_percent,
shuffle_bag_positions, source_and_each_matching_adjacent_stat_bonus,
source_and_each_matching_club_stat_bonus,
source_and_type_stat_per_type_count,
speed_and_distance_modifier_over_terrain,
speed_reduction_over_terrain, stacking_gravity_reduction,
stat_per_adjacent_same_brand, tee_stat_bonus,
terrain_bonus_boost_after_perfect, terrain_bounce,
terrain_bounce_then_bag_bonus, terrain_penalty_resistance,
tree_passing, wind_resistance, wind_toward_hole
```

## 11. Incohérences officielles connues

Cas relevés : description +2 contre tableau +6/+7 ; texte 100 % contre tableau 85 % ; pieds contre mètres ; symbole `%` sans valeur ; intitulé figé à 50 % alors que les niveaux dépassent 50 % ; valeur Elite sans signe `+`.

Ne jamais corriger silencieusement : conserver les représentations, avertir et attendre une validation.

## 12. État réel audité au 22 juillet 2026

Le dépôt contient un socle Python minimal :

- modèles `Stats`, `Club`, `Ability`, `BagEntry`, `Bag`, `GameState`, `Condition`, `Effect`, `ExplainEntry`, `EvaluationResult` ;
- `ConditionRegistry` avec `always`, `state_equals` et `current_club_attribute_equals` ;
- `MechanismRegistry` avec les seuls handlers génériques `add_stat` et `add_all_stats` ;
- `RuleEngine` séquentiel, modes strict/partial et Explain élémentaire ;
- chargeur JSON brut sans hypothèse de schéma ;
- CLI pour les données officielles et les rapports utilisateur ;
- 23 tests `unittest`.

Conforme aujourd'hui : aucune logique de nom de club, séparation conditions/effets, registres extensibles, erreurs de mécanique inconnue, journal avant/modification/après et données brutes non interprétées.

Écarts restant à traiter :

- modèles incomplets au regard des champs cible (rareté, provenance, position, validation, avertissements) ;
- conditions booléennes sans raison structurée ni observé/attendu ;
- Explain sans identifiant, phase, cible, statut à quatre états, confiance ou provenance ;
- ordre séquentiel sans phases explicites ;
- capacités des clubs non chargées automatiquement dans l'évaluation ;
- aucune validation du schéma officiel ni test des compteurs annoncés ;
- tests réalisés avec `unittest` alors que la convention cible indique `pytest` ;
- capture brute, catalogue officiel et audit présents ; les autres artefacts sémantiques restent absents.

Git au 22 juillet 2026 : branche `main`, distant `origin` égal à `https://github.com/Pelic-commits/pga-shootout.git`, local et distant synchronisés au début de l'audit sur `cc8dc80`.

## 13. Organisation des données

```text
data/
├── raw/
│   └── pga_club_stats_extract_v2_2026-07-21.json
├── normalized/
│   ├── clubs_official.json
│   ├── ability_occurrences.json
│   ├── ability_labels.json
│   ├── mechanics_catalog.json
│   ├── semantic_map.json
│   ├── assets.json
│   └── normalization_report.json
├── user/
│   └── inventory.json
└── scenarios/
    └── reference_bags.json
```

Le brut est immuable. Chaque normalisation déclare version de schéma et hash SHA-256 de la source.

## 14. Roadmap et prochaine tâche

- Phase 0 — fondations : initialisée et auditée, encore incomplète.
- Phase 1 — données officielles : importer, vérifier les hashes et compteurs, exposer club+niveau et produire la couverture.
- Couche utilisateur — compte, inventaire partiel, préférences, sacs et observations : implémentée et validée.
- Phase 2 — mécaniques déterministes validées : statistiques, sac, rareté, marque, type, adjacence et composition.
- Phase 3 — sac de référence et validation de l'ordre.
- Phases 4 à 6 — environnement, historique, transformations et hasard.
- Phase 7 — optimiseur, seulement après validation.

La capture brute, `clubs_official.json` et `ABILITY_AUDIT.md` sont importés avec hashes et invariants testés. La couche utilisateur est séparée et son inventaire reste explicitement incomplet. Prochaine tâche recommandée : compléter les niveaux actuels et les clubs possédés manquants à partir d'une nouvelle observation utilisateur, puis exposer la consultation club+niveau sans exécuter les capacités sémantiques non validées.

## 15. Définition de terminé et règle de travail

Une mécanique est terminée seulement si la donnée officielle est conservée, l'interprétation documentée, le handler générique, les conditions séparées, Explain complet, les tests réussis, le comportement validé ou marqué non validé et aucun club codé en dur.

Avant une tâche importante : lire ce contexte, inspecter le code, annoncer un plan court, modifier, tester, résumer et mettre à jour la documentation. En cas de conflit, conserver toutes les sources et ouvrir une investigation.

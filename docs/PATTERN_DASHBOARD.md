# Pattern Dashboard

## Mesures

Le catalogue officiel contient 125 groupes, 162 occurrences et 88 clubs. Les pourcentages de pattern ci-dessous utilisent les occurrences du catalogue complet. Une famille candidate n'est pas comptée tant que son texte n'a pas permis de figer son pipeline sans ambiguïté.

| Pattern fonctionnel | Primitives utilisées | Familles couvertes | Familles restantes qualifiées | Occurrences couvertes | Couverture estimée |
|---|---|---|---|---:|---:|
| Bonus source proportionnel aux voisins correspondants | `SELECT_SELF`, `READ_LEVEL_VALUE`, `SELECT_ADJACENT`, `MATCH_BRAND` ou `MATCH_TYPE`, `COUNT`, `SCALE`, `ADD_STAT` | `brand_loyalty_x`, `brand_loyalty`, `driver_loyalty` | aucune | 22 | 13,58 % |
| Bonus direct aux cibles positionnelles | `SELECT_SELF`, `READ_LEVEL_VALUE`, `SELECT_ADJACENT`, `FOR_EACH`, `ADD_STAT` | `power_boost`, `control_boost`, `spin_boost`, `adjacent_power` | aucune | 5 | 3,09 % |
| Bonus direct aux cibles du sac | `SELECT_SELF`, `READ_LEVEL_VALUE`, `SELECT_ALL`, `FOR_EACH`, `ADD_STAT` | `bag_control`, `bag_spin_bonus` | aucune | 2 | 1,23 % |
| Bonus direct aux cibles d'une marque | `SELECT_SELF`, `READ_LEVEL_VALUE`, `SELECT_ALL`, `MATCH_BRAND`, `FOR_EACH`, `ADD_STAT` | `forester_power`, `phoenix_power`, `stanchion_power` | aucune | 3 | 1,85 % |
| Bonus par correspondance à la cible et à la source | `SELECT_SELF`, `READ_LEVEL_VALUE`, `SELECT_ALL` ou `SELECT_ADJACENT`, `MATCH_TYPE` ou `MATCH_BRAND`, `FOR_EACH`, `ADD_STAT` | `alloy`, `nautilus_boost` | aucune | 2 | 1,23 % |
| Bonus sous condition d'absence de types | `SELECT_SELF`, `READ_LEVEL_VALUE`, `SELECT_ALL`, `MATCH_TYPE`, `EXISTS`, `UNLESS`, `FOR_EACH`, `ADD_STAT` | `iron_wedge_exclusion`, `exclusion_zone` | aucune | 2 | 1,23 % |
| Compromis multi-statistiques du sac | `SELECT_SELF`, `READ_LEVEL_VALUE`, `SELECT_ALL`, `FOR_EACH`, `ADD_STAT` | `bag_recklessness` | aucune | 1 | 0,62 % |
| Bonus multi-statistiques du sac filtré par rareté | `SELECT_SELF`, `READ_LEVEL_VALUE`, `SELECT_ALL`, `MATCH_RARITY`, `FOR_EACH`, `ADD_STAT` | `bag_rarity_boost` | aucune | 1 | 0,62 % |
| Bonus adjacent avec multiplicateur de marque | `SELECT_SELF`, `READ_LEVEL_VALUE`, `SELECT_ADJACENT`, `FOR_EACH`, `MATCH_BRAND`, `ADD_STAT` | `fellowship` | aucune | 1 | 0,62 % |
| Modificateur statique ciblé | `SELECT_SELF`, `READ_LEVEL_VALUE`, `SELECT_SELF` ou `SELECT_ALL`, `FOR_EACH`, `ADD_MODIFIER` | `loft_angle_5`, `bag_loft_angle_10`, `bounce_reduction`, `sand_bounce`, `water_bounce` | aucune | 5 | 3,09 % |

## Priorisation orientée inventaire

| Rang | Pattern candidat | Clubs possédés concernés | Impact comparateur | Réutilisabilité | Difficulté / décision |
|---:|---|---:|---|---|---|
| 1 | Comptes de rebond par terrain | 1 (`mirage`) | élevée, deux mesures objectives | élevée | faible — implémenté |
| 2 | Réduction statique du rebond | 2 (`cyclotron`, `cloudcatcher`) ; Maelstrom apparaît dans un sac enregistré mais pas dans l'inventaire partiel | élevée, dont un sac de référence | élevée | partielle — Cloudcatcher implémenté ; Cyclotron et Maelstrom restent à qualifier séparément |
| 3 | Chaînes vers filtres de clubs | 3 (`conqueror`, `kinship`, `outset`) | élevée sur les statistiques | élevée | stateful — différé après la Phase 1 |
| 4 | Multiplicateur fade/draw | 1 (`lodestar`) | moyenne | moyenne | métrique de base absente |

Les comptes maximaux de Mirage sont explicites. Les réductions de rebond restent séparément bloquées : leur ROI brut ne justifie pas d'inventer leurs règles de cumul.

## Patterns paramétrés

`matching_targets_and_source_per_match` définit une fois le corps d'effet suivant : pour chaque cible filtrée, appliquer la valeur du niveau à la cible puis à la source. Les paramètres autorisés remplacent uniquement la sélection, ses entrées, le filtre, ses entrées et la statistique.

- `alloy` configure `SELECT_ALL` puis `MATCH_TYPE(hybrid)` ;
- `nautilus_boost` configure `SELECT_ADJACENT` puis `MATCH_BRAND(source)` ;
- le sous-programme `FOR_EACH(ADD_STAT(target), ADD_STAT(source))` n'est pas dupliqué.

Les groupes `smoke_x`, `steam_x` et `sparks_x` restent seulement des candidats. Leur formulation « while next to » ne permet pas encore de valider si le bonus de la source se cumule avec deux voisins ; `sparks_x` exige en outre des primitives absentes. Ils ne sont donc ni intégrés ni comptés.

`absent_types_stat_bonus` centralise la condition « aucun club des types configurés » et paramètre uniquement la sélection des cibles :

- `iron_wedge_exclusion` sélectionne uniquement la source ;
- `exclusion_zone` sélectionne tous les clubs sauf la source ;
- les deux familles utilisent le même filtre `MATCH_TYPE(in: iron, wedge)`, le même test `EXISTS` et la même branche `UNLESS`.

`bag_multi_stat_tradeoff` lit séparément chaque composante signée du niveau officiel. `bag_recklessness` configure les statistiques bonifiées (`power`, `spin`) et pénalisée (`control`) ; aucune perte n'est déduite par inversion du bonus.

`filtered_bag_multi_stat_bonus` sélectionne le sac, filtre les raretés configurées puis applique la valeur officielle aux statistiques configurées. `bag_rarity_boost` utilise les raretés `common` et `rare` et les trois statistiques, sans condition liée au nom de Steadfast.

`adjacent_stat_bonus_with_brand_multiplier` applique une première fois la valeur à chaque voisin, puis une seconde fois aux voisins partageant la marque de la source. `fellowship` obtient ainsi exactement le double pour Willoughsby sans multiplication ni branche métier.

`static_modifier_targets` conserve les propriétés déterministes qui ne sont pas des statistiques Power/Control/Spin. High Flight configure une cible source à `+5°`, Cloudcatcher tout le sac à `+10°`, sa propre réduction de rebond en pourcentage, et Mirage expose séparément ses nombres maximaux de rebonds sur sable et sur eau.

## Architecture Dashboard

| Indicateur | État |
|---|---:|
| Couverture technique | 24 / 125 groupes ; 44 / 162 occurrences |
| Couverture fonctionnelle | 5 / 8 fonctionnalités utilisateur de référence |
| Groupes couverts | 24 / 125 (19,20 %) |
| Occurrences couvertes | 44 / 162 (27,16 %) |
| Clubs couverts | 33 / 88 (37,50 %) |
| Primitives disponibles | 14 / 50 |
| Primitives encore manquantes | 36 / 50 |
| Familles qualifiées bloquées uniquement par une primitive absente | 0 |

Les 101 groupes restants sont non qualifiés. Attribuer un nombre exact de primitives manquantes avant validation sémantique produirait une fausse précision ; ils ne sont pas comptés comme « bloqués par une seule primitive ».

Précision fonctionnelle améliorée dans ce lot : Cloudcatcher expose désormais sa réduction de rebond comme mesure objective distincte. La couverture des capacités de l'inventaire passe de 20/35 à 21/35, soit de 57,14 % à 60,00 % (+2,86 points), et 8 clubs possédés sont entièrement simulés.

La préparation de l'optimiseur est suivie par la checklist objective `ready` / `partial` / `missing` détaillée dans `OPTIMIZER_API.md`.

## Couverture fonctionnelle

| Fonctionnalité utilisateur de référence | État |
|---|---|
| Charger et afficher les sacs sauvegardés | Supportée |
| Évaluer un sac à un niveau de scénario explicite | Supportée |
| Expliquer les effets appliqués et non résolus | Supportée |
| Comparer deux sacs par composition, position, statistiques, bonus gagnés/perdus et bonus non résolus | Supportée |
| Distinguer calcul complet et calcul partiel | Supportée |
| Classer automatiquement plusieurs sacs | Non supportée — pondérations non validées |
| Recommander le remplacement d'un club | Non supportée |
| Recommander l'ordre optimal des clubs | Non supportée |

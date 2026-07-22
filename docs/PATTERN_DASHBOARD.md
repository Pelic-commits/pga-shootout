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

## Pattern travaillé

`matching_targets_and_source_per_match` définit une fois le corps d'effet suivant : pour chaque cible filtrée, appliquer la valeur du niveau à la cible puis à la source. Les paramètres autorisés remplacent uniquement la sélection, ses entrées, le filtre, ses entrées et la statistique.

- `alloy` configure `SELECT_ALL` puis `MATCH_TYPE(hybrid)` ;
- `nautilus_boost` configure `SELECT_ADJACENT` puis `MATCH_BRAND(source)` ;
- le sous-programme `FOR_EACH(ADD_STAT(target), ADD_STAT(source))` n'est pas dupliqué.

Les groupes `smoke_x`, `steam_x` et `sparks_x` restent seulement des candidats. Leur formulation « while next to » ne permet pas encore de valider si le bonus de la source se cumule avec deux voisins ; `sparks_x` exige en outre des primitives absentes. Ils ne sont donc ni intégrés ni comptés.

## Architecture Dashboard

| Indicateur | État |
|---|---:|
| Groupes couverts | 14 / 125 (11,20 %) |
| Occurrences couvertes | 34 / 162 (20,99 %) |
| Clubs couverts | 30 / 88 (34,09 %) |
| Primitives disponibles | 10 / 50 |
| Primitives encore manquantes | 40 / 50 |
| Familles qualifiées bloquées uniquement par une primitive absente | 0 |

Les 111 groupes restants sont non qualifiés. Attribuer un nombre exact de primitives manquantes avant validation sémantique produirait une fausse précision ; ils ne sont pas comptés comme « bloqués par une seule primitive ».

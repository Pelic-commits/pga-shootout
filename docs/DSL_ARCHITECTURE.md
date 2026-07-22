# DSL Architecture

> Architecture déclarative proposée. Aucun élément de ce document n'est un handler, une mécanique validée ou une autorisation d'implémentation.

## Sous-ensemble implémenté

L'exécuteur couvre six compositions génériques qualifiées dans les données :

- marque : `SELECT_SELF → READ_LEVEL_VALUE → SELECT_ADJACENT → MATCH_BRAND → COUNT → SCALE → ADD_STAT` ;
- type : `SELECT_SELF → READ_LEVEL_VALUE → SELECT_ADJACENT → MATCH_TYPE → COUNT → SCALE → ADD_STAT` ;
- application à chaque cible adjacente : `SELECT_SELF → READ_LEVEL_VALUE → SELECT_ADJACENT → FOR_EACH(ADD_STAT)` ;
- application globale au sac : `SELECT_SELF → READ_LEVEL_VALUE → SELECT_ALL → FOR_EACH(ADD_STAT)` ;
- application globale filtrée par marque : `SELECT_SELF → READ_LEVEL_VALUE → SELECT_ALL → MATCH_BRAND → FOR_EACH(ADD_STAT)`.
- application par correspondance à la cible et à la source : `SELECT_SELF → READ_LEVEL_VALUE → SELECT_ALL|SELECT_ADJACENT → MATCH_TYPE|MATCH_BRAND → FOR_EACH(ADD_STAT(target), ADD_STAT(source))`.

Cette dernière composition est stockée une seule fois comme pattern paramétré dans `semantic_map.json`. Les familles ne déclarent que la sélection, le filtre et la statistique ; le chargeur matérialise le programme sans connaître leurs noms.

Le registre contient dix primitives : `SELECT_SELF`, `READ_LEVEL_VALUE`, `SELECT_ALL`, `SELECT_ADJACENT`, `MATCH_BRAND`, `MATCH_TYPE`, `COUNT`, `SCALE`, `FOR_EACH` et `ADD_STAT`. Le Rule Engine ne connaît ni le nom de la famille ni les noms des clubs : il reçoit le programme depuis `semantic_map.json`, le transmet à `dsl_pipeline` et ajoute une entrée Explain pour chaque nœud, y compris chaque sous-exécution ordonnée. Toutes les autres primitives de ce document restent des éléments d'architecture non implémentés.

## Principes

Le DSL décrit un graphe typé de primitives. Les primitives de lecture, sélection, filtrage, agrégation et calcul sont pures. Seules les familles Effets et Transformations peuvent produire un changement de `GameState`.

Règles invariantes :

- aucun nom de club ne déclenche de logique ;
- toutes les références entre étapes utilisent un identifiant de sortie explicite ;
- aucune lecture implicite du sac, de la source ou du niveau ;
- une collection de clubs reste ordonnée ;
- chaque primitive produit un événement Explain ;
- `strict` échoue sur une primitive, un type ou un champ inconnu ;
- `partial` conserve les sorties calculables et marque les nœuds dépendants comme non évalués ;
- toute opération aléatoire exige une source pseudo-aléatoire et une graine explicites ;
- les unités, arrondis, plafonds et phases ne sont jamais implicites.

## Types du DSL

| Type | Description |
|---|---|
| `Scalar` | Nombre avec unité facultative. |
| `Boolean` | Résultat vrai/faux avec justification Explain. |
| `String` | Identifiant ou valeur textuelle contrôlée. |
| `ClubRef` | Référence stable vers une instance de club dans un état. |
| `ClubSet` | Collection ordonnée de `ClubRef`. |
| `ValueSet` | Collection ordonnée de valeurs numériques. |
| `ContextRef` | Référence vers une donnée de contexte autorisée. |
| `EffectEvent` | Modification proposée avec source, cible, avant et après. |
| `StatePatch` | Ensemble atomique de modifications de l'état. |
| `ExplainNode` | Trace structurée d'une primitive et de ses entrées/sorties. |

## Forme canonique d'un nœud

```json
{
  "id": "unique_node_id",
  "op": "PRIMITIVE_NAME",
  "inputs": {
    "input_name": {"from": "another_node.output"}
  },
  "params": {},
  "output": "declared_output_name"
}
```

Une valeur littérale passe par `LITERAL`. Une donnée du jeu passe par une primitive de lecture. Les chaînes comme `$source.brand_id` ne constituent pas une syntaxe parallèle cachée.

## Famille 1 — Valeurs et contexte

| Primitive | Rôle | Entrées | Sortie | Paramètres | Dépendances | Exemple |
|---|---|---|---|---|---|---|
| `LITERAL` | Introduire une constante typée. | aucune | valeur | `value`, `type`, `unit` | aucune | Statistique `power`. |
| `READ_CONTEXT` | Lire un champ autorisé du contexte. | contexte | valeur | `path`, `required` | schéma `GameState` | Vent ou terrain courant. |
| `READ_ATTRIBUTE` | Lire un attribut d'une référence. | objet/référence | valeur | `attribute`, `required` | résolveur de références | Marque du club source. |
| `READ_LEVEL_VALUE` | Lire la valeur officielle d'une capacité au niveau évalué. | capacité, niveau | `Scalar` ou absence | `component`, `unit` | couche de données | Valeur `X` de Brand Loyalty. |
| `REFERENCE_OUTPUT` | Réutiliser explicitement une sortie antérieure. | identifiant de nœud | valeur typée | `output_name` | graphe d'exécution | Réutiliser `matching_count`. |

## Famille 2 — Sélection

| Primitive | Rôle | Entrées | Sortie | Paramètres | Dépendances | Exemple |
|---|---|---|---|---|---|---|
| `SELECT_SELF` | Sélectionner le club portant la capacité. | contexte d'effet | `ClubRef` | aucune | source structurée | Cible de Brand Loyalty. |
| `SELECT_CURRENT` | Sélectionner le club joué actuellement. | `GameState` | `ClubRef` | aucune | club courant | Bonus du coup courant. |
| `SELECT_ALL` | Sélectionner le sac ordonné. | sac | `ClubSet` | `include_source` | modèle `Bag` | Analyse de composition. |
| `SELECT_ADJACENT` | Sélectionner les voisins immédiats. | sac, origine | `ClubSet` | `directions`, `distance` | positions stables | Voisins de Brand Loyalty. |
| `SELECT_BY_POSITION` | Sélectionner une ou plusieurs positions. | sac | `ClubSet` | indices/plage | positions stables | Premier ou dernier club. |
| `SELECT_BEFORE` | Sélectionner les clubs avant une origine. | sac, origine | `ClubSet` | inclusivité | positions stables | Effet directionnel gauche. |
| `SELECT_AFTER` | Sélectionner les clubs après une origine. | sac, origine | `ClubSet` | inclusivité | positions stables | Effet directionnel droit. |
| `SELECT_HISTORY` | Sélectionner des événements ou clubs historiques. | historique | collection typée | `event_type`, fenêtre | historique structuré | Club du coup précédent. |

## Famille 3 — Filtres

Chaque filtre reçoit une collection et conserve son ordre. Il retourne les éléments correspondants ainsi qu'un résultat détaillé par candidat.

| Primitive | Rôle | Entrées | Sortie | Paramètres | Dépendances | Exemple |
|---|---|---|---|---|---|---|
| `MATCH_BRAND` | Filtrer par marque. | `ClubSet`, marque attendue | `ClubSet` | `operator` | modèle d'identité | Même marque que la source. |
| `MATCH_TYPE` | Filtrer par type. | `ClubSet`, type attendu | `ClubSet` | `operator` | taxonomie des types | Conserver les hybrides. |
| `MATCH_RARITY` | Filtrer par rareté. | `ClubSet`, rareté attendue | `ClubSet` | `operator` | taxonomie des raretés | Conserver les Epic. |
| `MATCH_IDENTITY` | Filtrer selon une identité calculée. | `ClubSet`, identité | `ClubSet` | règles de correspondance | registre d'identité validé | Club comptant comme une marque. |
| `MATCH_ATTRIBUTE` | Filtre générique de repli. | collection, attribut, attendu | collection | `path`, `operator` | type de l'objet | Terrain ou propriété booléenne. |

`MATCH_BRAND`, `MATCH_TYPE` et `MATCH_RARITY` sont des formes typées de `MATCH_ATTRIBUTE`. Elles rendent le DSL lisible mais doivent conserver la même sémantique de comparaison centrale.

## Famille 4 — Agrégation

| Primitive | Rôle | Entrées | Sortie | Paramètres | Dépendances | Exemple |
|---|---|---|---|---|---|---|
| `COUNT` | Compter les éléments. | collection | entier | aucune | aucune | Nombre de voisins correspondants. |
| `SUM` | Additionner des scalaires. | `ValueSet` | `Scalar` | unité attendue | compatibilité d'unités | Somme de statistiques. |
| `MIN` | Prendre le minimum. | `ValueSet` | `Scalar` | politique vide | compatibilité d'unités | Plus petite statistique. |
| `MAX` | Prendre le maximum. | `ValueSet` | `Scalar` | politique vide | compatibilité d'unités | Plus grande statistique. |
| `EXISTS` | Tester si une collection n'est pas vide. | collection | `Boolean` | aucune | aucune | Au moins un voisin valide. |
| `ANY` | Tester si un prédicat correspond au moins une fois. | résultats booléens | `Boolean` | aucune | résultats de filtre | Une condition satisfaite. |
| `ALL` | Tester si tous les résultats correspondent. | résultats booléens | `Boolean` | politique vide | résultats de filtre | Tous les clubs respectent un critère. |

## Famille 5 — Calcul

| Primitive | Rôle | Entrées | Sortie | Paramètres | Dépendances | Exemple |
|---|---|---|---|---|---|---|
| `ADD` | Additionner deux valeurs. | deux `Scalar` | `Scalar` | unité | compatibilité d'unités | Combiner deux bonus. |
| `SUBTRACT` | Soustraire une valeur. | deux `Scalar` | `Scalar` | unité | compatibilité d'unités | Compromis statistique. |
| `MULTIPLY` | Multiplier deux valeurs. | deux `Scalar` | `Scalar` | unité de sortie | règles d'unités | Multiplicateur générique. |
| `DIVIDE` | Diviser deux valeurs. | deux `Scalar` | `Scalar` | division par zéro | règles d'unités | Conversion validée. |
| `SCALE` | Multiplier un montant par un facteur nommé. | montant, facteur | `Scalar` | unité, sens du facteur | aucune | `X × matching_count`. |
| `CLAMP` | Borner une valeur. | valeur, minimum, maximum | `Scalar` | inclusivité | règle validée | Limite de statistique. |
| `ROUND` | Appliquer un arrondi explicite. | valeur | `Scalar` | mode, précision, phase | règle validée | Arrondi final du jeu. |

`SCALE` est une forme sémantique lisible de `MULTIPLY`. Elle conserve dans Explain les rôles `amount` et `factor`.

## Famille 6 — Contrôle

| Primitive | Rôle | Entrées | Sortie | Paramètres | Dépendances | Exemple |
|---|---|---|---|---|---|---|
| `SEQUENCE` | Ordonner explicitement des nœuds. | liste de nœuds | sorties ordonnées | phase | ordonnanceur | Calcul avant effet. |
| `WHEN` | Exécuter une branche si vrai. | `Boolean`, branche | sortie/absence | comportement faux | contrôle typé | Appliquer un bonus conditionnel. |
| `UNLESS` | Exécuter une branche si faux. | `Boolean`, branche | sortie/absence | comportement vrai | contrôle typé | Bonus en absence d'un type. |
| `FOR_EACH` | Exécuter un sous-graphe par élément. | collection, sous-graphe | collection de sorties | ordre, atomicité | exécuteur de graphe | Appliquer à chaque cible. |
| `RANDOM_CHOICE` | Choisir explicitement un élément. | collection, RNG | élément | distribution | graine, RNG validé | Sélection aléatoire reproductible. |

## Famille 7 — Effets statistiques et état

| Primitive | Rôle | Entrées | Sortie | Paramètres | Dépendances | Exemple |
|---|---|---|---|---|---|---|
| `ADD_STAT` | Ajouter un delta à une statistique. | cible, statistique, delta | `EffectEvent` | phase | cible résolue | Bonus de puissance. |
| `ADD_ALL_STATS` | Ajouter un delta aux statistiques déclarées. | cible, delta | `EffectEvent[]` | liste des stats | cible résolue | Bonus toutes statistiques. |
| `SET_STAT` | Fixer une statistique. | cible, statistique, valeur | `EffectEvent` | phase | cible résolue | Copie ou remplacement validé. |
| `MULTIPLY_STAT` | Multiplier une statistique. | cible, statistique, facteur | `EffectEvent` | unité, phase | cible résolue | Multiplicateur validé. |
| `ENABLE_FLAG` | Activer un état booléen. | cible/état, drapeau | `StatePatch` | durée | schéma d'état | Autoriser un comportement. |
| `DISABLE_FLAG` | Désactiver un état booléen. | cible/état, drapeau | `StatePatch` | durée | schéma d'état | Neutraliser un comportement. |
| `EMIT_EVENT` | Ajouter un événement métier explicite. | type, payload | événement | phase | schéma d'événements | Impact terrain observé. |
| `SCHEDULE_EFFECT` | Programmer un sous-graphe différé. | déclencheur, sous-graphe | `StatePatch` | durée, consommation | historique/ordonnanceur | Effet au prochain coup. |

## Famille 8 — Transformations du sac

| Primitive | Rôle | Entrées | Sortie | Paramètres | Dépendances | Exemple |
|---|---|---|---|---|---|---|
| `MOVE_CLUB` | Déplacer un club dans le sac. | sac, club, position | `StatePatch` | collision | positions | Changement de position. |
| `SHUFFLE_CLUBS` | Mélanger un ensemble sélectionné. | sac, sélection, RNG | `StatePatch` | distribution | graine, RNG | Mélange reproductible. |
| `REPLACE_CLUB` | Remplacer une instance. | sac, ancienne/nouvelle référence | `StatePatch` | conservation d'état | catalogue, identité | Transformation validée. |
| `REMOVE_CLUB` | Retirer une instance. | sac, référence | `StatePatch` | durée, restauration | contraintes du sac | Destruction temporaire. |
| `COPY_ABILITY` | Copier une capacité structurée. | source, cible, capacité | `StatePatch` | durée, empilement | modèle des capacités | Partage/copie validé. |

## Relations entre familles

```text
Valeurs et contexte ───────────────┐
                                  ↓
Sélection → Filtres → Agrégation → Calcul
    │          │          │          │
    └──────────┴──────────┴──────────┤
                                     ↓
                                  Contrôle
                                     ↓
                         Effets / Transformations
                                     ↓
                            GameState + Explain
```

Un pipeline peut s'arrêter avant les effets pour fournir une condition ou une valeur intermédiaire. Un effet ne peut pas effectuer secrètement une sélection, un filtre ou un calcul.

## Pipeline complet proposé — Brand Loyalty

```text
SELECT_SELF ───────────────────────────────────────────────┐
    │                                                      │
    ├─ READ_ATTRIBUTE(brand_id) ───────────────┐           │
    │                                          │           │
    └─ SELECT_ADJACENT                         │           │
           ↓                                   │           │
       MATCH_BRAND(expected = source.brand_id) │           │
           ↓                                   │           │
         COUNT                                 │           │
           ↓                                   │           │
READ_LEVEL_VALUE(X) ────────────────→ SCALE(amount=X, factor=count)
                                                   ↓       │
                                  ADD_STAT(target=self, stat=power)
```

```json
{
  "dsl_version": "1.0-proposal",
  "ability_group": "label:brand_loyalty_x",
  "validation_status": "proposed",
  "nodes": [
    {"id":"source","op":"SELECT_SELF","inputs":{},"params":{},"output":"club"},
    {"id":"brand","op":"READ_ATTRIBUTE","inputs":{"object":{"from":"source.club"}},"params":{"attribute":"brand_id"},"output":"value"},
    {"id":"neighbors","op":"SELECT_ADJACENT","inputs":{"origin":{"from":"source.club"}},"params":{"directions":["left","right"],"distance":1},"output":"clubs"},
    {"id":"matches","op":"MATCH_BRAND","inputs":{"clubs":{"from":"neighbors.clubs"},"expected":{"from":"brand.value"}},"params":{"operator":"equals"},"output":"clubs"},
    {"id":"count","op":"COUNT","inputs":{"items":{"from":"matches.clubs"}},"params":{},"output":"value"},
    {"id":"x","op":"READ_LEVEL_VALUE","inputs":{},"params":{"component":"primary","unit":"flat"},"output":"value"},
    {"id":"bonus","op":"SCALE","inputs":{"amount":{"from":"x.value"},"factor":{"from":"count.value"}},"params":{},"output":"value"},
    {"id":"apply","op":"ADD_STAT","inputs":{"target":{"from":"source.club"},"delta":{"from":"bonus.value"}},"params":{"stat":"power"},"output":"effect"}
  ]
}
```

## Autres pipelines illustratifs

### Mise à l'échelle par composition du sac

```text
SELECT_ALL → MATCH_TYPE → COUNT → SCALE → ADD_STAT
```

Même primitives de comptage et calcul que Brand Loyalty ; seule la portée de sélection change.

### Bonus conditionnel de contexte

```text
READ_CONTEXT → MATCH_ATTRIBUTE → EXISTS/WHEN → READ_LEVEL_VALUE → ADD_STAT
```

Le filtre porte sur le contexte et non sur des clubs. Seule la primitive terminale peut être commune avec Brand Loyalty.

### Effet différé

```text
READ_CONTEXT → MATCH_ATTRIBUTE → WHEN → SCHEDULE_EFFECT
                                      └→ ADD_STAT au déclenchement
```

### Transformation aléatoire reproductible

```text
SELECT_ALL → MATCH_ATTRIBUTE → RANDOM_CHOICE → REPLACE_CLUB
```

Ce pipeline exige une graine et ne préjuge d'aucune capacité officielle.

## Familles candidates au pipeline exact de Brand Loyalty

Le pipeline canonique est :

```text
SELECT_ADJACENT → MATCH_ATTRIBUTE → COUNT → SCALE → ADD_STAT
```

Les formes spécialisées `MATCH_BRAND` et `MATCH_TYPE` se normalisent vers `MATCH_ATTRIBUTE`. Sous réserve de qualification sémantique, les groupes suivants sont candidats à la même topologie exacte, avec seulement des paramètres différents :

- `brand_loyalty_x` et `brand_loyalty` ;
- `driver_loyalty` ;
- `combined_power` ;
- `combined_spin`.

`adjacent_power`, `nautilus_boost`, `alloy`, `tree_bonus` et `boundary_bonus` peuvent réutiliser certaines primitives, mais ne sont pas déclarés comme utilisant exactement ce pipeline sans analyse dédiée.

## Inventaire figé

Le DSL proposé contient **50 primitives** réparties en huit familles :

- Valeurs et contexte : 5 ;
- Sélection : 8 ;
- Filtres : 5 ;
- Agrégation : 7 ;
- Calcul : 7 ;
- Contrôle : 5 ;
- Effets statistiques et état : 8 ;
- Transformations du sac : 5.

Toute primitive future devra démontrer qu'elle ne peut pas être exprimée par composition de cet inventaire avant d'être ajoutée.

# Engine Primitives

> Proposition architecturale issue uniquement de l'analyse du groupe structurel `brand_loyalty_x`. Ce document ne valide aucune règle de jeu et n'autorise l'implémentation d'aucun handler.

> État actuel : cette proposition a depuis été précisée par `DSL_ARCHITECTURE.md`. Le registre générique comprend notamment `SELECT_SELF`, `READ_LEVEL_VALUE`, `SELECT_ADJACENT`, `SELECT_FARTHEST`, `MATCH_BRAND`, `COUNT`, `SCALE` et `ADD_STAT`.

## Objectif

Décomposer la proposition monolithique `self_stat_per_adjacent_filter` en opérations indépendantes et composables :

```text
ability context
  → SELECT_CLUBS
  → MATCH_CLUB_FILTER
  → COUNT_MATCHES
  → SCALE_VALUE
  → ADD_STAT
```

Pour `brand_loyalty_x`, le flux proposé serait : sélectionner les voisins immédiats, conserver ceux dont la marque correspond à celle de la source, les compter, multiplier la valeur `X` du niveau par ce nombre, puis ajouter le résultat à la puissance du club source.

## Primitives proposées

### 1. `SELECT_CLUBS`

Sélectionne des références de clubs sans appliquer de règle statistique.

Entrées :

- `bag` : sac ordonné ;
- `source_club_id` ou position source ;
- `scope` : `adjacent`, `whole_bag`, `before_source`, `after_source` ou autre portée validée ;
- `directions` : gauche, droite ou les deux ;
- politique d'inclusion de la source.

Sortie :

- collection ordonnée de références de clubs candidats.

Réutilisation candidate : capacités d'adjacence, de position, de composition du sac et effets directionnels. Les groupes `adjacent_power`, `combined_power`, `combined_spin`, `alloy`, `overdrive` et `overaim` semblent susceptibles de consommer une sélection de clubs, mais leur logique reste à qualifier.

### 2. `MATCH_CLUB_FILTER`

Évalue un filtre déclaratif sur chaque club candidat. Cette primitive ne compte rien et ne modifie aucune statistique.

Entrées :

- collection de clubs candidats ;
- un ou plusieurs prédicats ;
- valeurs littérales ou valeurs provenant du contexte/source.

Filtres prévus, sans présumer de leur comportement dans le jeu :

- marque ;
- type ;
- rareté ;
- identifiant stable ;
- position ;
- propriété d'identité ;
- composition générique `all` / `any` / `not`.

Sorties :

- collection des clubs correspondants ;
- pour chaque candidat, résultat structuré et raison du match ou du rejet.

Réutilisation candidate : Brand Loyalty, Driver Loyalty, bonus par marque/type/rareté, exclusions de composition et autres familles filtrant des clubs. Les interactions d'identité telles que « compte comme toutes les marques » devront être qualifiées séparément.

### 3. `COUNT_MATCHES`

Compte une collection déjà sélectionnée et filtrée.

Entrée :

- collection de références correspondantes.

Sortie :

- `matching_count` entier ;
- références comptées, conservées pour Explain.

Réutilisation candidate : bonus par voisin, bonus par nombre de clubs d'un type ou d'une marque, et conditions de présence/absence. `brand_loyalty_x` fournit au minimum 20 occurrences directes susceptibles d'utiliser cette primitive.

### 4. `SCALE_VALUE`

Produit une valeur numérique sans modifier l'état.

Entrées :

- `base_amount`, ici la valeur officielle `X` au niveau évalué ;
- `factor`, ici `matching_count` ;
- opération autorisée, initialement multiplication ;
- politique d'arrondi, uniquement lorsqu'elle sera validée.

Sortie :

- valeur calculée ;
- détail de l'opération pour Explain.

Réutilisation candidate : capacités « par club », « par voisin », « par unité de vent », « par seconde » ou autres effets proportionnels. Chaque unité et règle d'arrondi devra être validée avant utilisation.

### 5. `ADD_STAT`

Applique un delta numérique déjà calculé à une statistique d'une cible résolue.

Entrées :

- référence de la cible ;
- statistique ;
- delta ;
- source et provenance de l'effet.

Sorties :

- valeur avant ;
- delta appliqué ;
- valeur après ;
- événement Explain.

Réutilisation candidate : Brand Loyalty, Adjacent Power, Tree Bonus, Boundary Bonus et toute famille terminant par un bonus statistique. Cette affirmation concerne seulement la primitive terminale ; leurs conditions et sélecteurs ne sont pas considérés comme identiques.

## Contexte requis, mais non considéré comme une primitive

Le Rule Engine devra fournir un contexte d'effet structuré contenant au minimum la capacité source, le club source, sa position, son niveau et le sac ordonné. Sans ce contexte, `SELECT_CLUBS` et la résolution de la cible restent impossibles. Il s'agit d'une donnée d'exécution partagée, pas d'une règle de gameplay.

La lecture de la valeur officielle au niveau courant appartient à la couche de données. Elle alimente `base_amount` mais ne constitue pas une mécanique.

## Couverture actuelle du moteur

| Primitive | État actuel | Limite |
|---|---|---|
| `SELECT_CLUBS` | partiel | `Bag` est ordonné, mais aucune sélection relationnelle générique n'existe. |
| `MATCH_CLUB_FILTER` | partiel | Le registre de conditions sait comparer un attribut du club courant, pas filtrer une collection de clubs avec un résultat Explain structuré. |
| `COUNT_MATCHES` | absent | Aucun mécanisme générique de comptage. |
| `SCALE_VALUE` | absent | Aucun calcul intermédiaire générique exposé à Explain. |
| `ADD_STAT` | partiel | `add_stat` existe, mais sa cible est implicitement la statistique courante et non une référence de club résolue. |
| `ADD_ALL_STATS` | existant | Déjà enregistré, mais non requis par la proposition Brand Loyalty. |

## Nouvelles primitives à développer après validation

Ordre architectural proposé, sans autorisation d'implémentation :

1. contexte d'effet structuré avec source et positions ;
2. `SELECT_CLUBS` ;
3. `MATCH_CLUB_FILTER` ;
4. `COUNT_MATCHES` ;
5. `SCALE_VALUE` ;
6. généralisation prudente de `ADD_STAT` vers une cible résolue.

## Gain de réutilisation estimé

- **Gain direct minimal : élevé.** Les 20 occurrences de `brand_loyalty_x` partageraient exactement le même pipeline et ne différeraient que par la source, la marque dérivée et la valeur par niveau.
- **Gain transversal probable : élevé mais non quantifié.** Les groupes d'adjacence et de composition pourront potentiellement réutiliser `SELECT_CLUBS`, `MATCH_CLUB_FILTER` et `COUNT_MATCHES` après qualification.
- **Gain terminal très élevé.** `ADD_STAT` est susceptible d'être partagé par de nombreuses familles, notamment les bonus de terrain, de position et d'adjacence, sans rendre leurs conditions équivalentes.
- **Réduction de duplication attendue : forte.** Une capacité future devrait composer des primitives déclaratives plutôt qu'obtenir un handler monolithique par intitulé.

## Points de conception à valider avant implémentation

- définition exacte de chaque portée et de l'adjacence ;
- modèle d'identité et de marques multiples ;
- comportement lorsque la source est transformée ou déplacée ;
- distinction entre candidats, matches et cibles ;
- ordre des sélections, comptages et modifications ;
- règles de cumul, plafonnement et arrondi ;
- granularité des événements Explain pour chaque primitive ;
- comportement strict/partial lorsqu'une primitive de la chaîne manque.

# Rule Engine, DSL et Explain

## Principe

Le moteur applique uniquement des règles qualifiées depuis les données versionnées. Il ne contient aucune branche sur un nom de club. Une capacité officielle est reliée à un mécanisme générique ou à un pipeline DSL déclaré dans la carte sémantique.

```text
Club + niveau + position + contexte optionnel
                    ↓
             Ability / Effect
                    ↓ condition
      registre de mécanismes ou pipeline DSL
                    ↓
    Contribution + statistiques + Explain
```

## Conditions et contexte

Les conditions supportent l'application inconditionnelle, les valeurs catégorielles du `GameState`, la position du sac et les relations gauche/droite. Le contexte actif reste minimal : sac ordonné, club courant, étape éventuelle, terrain catégoriel lorsqu'il est fourni et effets différés en attente.

Une donnée absente est signalée. En mode `strict`, une mécanique ou un contexte indispensable inconnu bloque l'évaluation. En mode `partial`, les calculs connus continuent et l'élément manquant devient explicitement non résolu.

## Mécanismes et primitives

Le registre de mécanismes expose `add_stat`, `add_all_stats` et l'exécution d'un pipeline DSL. Le registre DSL actuel contient :

- valeurs : `READ_LEVEL_VALUE` ;
- sélections : `SELECT_SELF`, `SELECT_ALL`, `SELECT_ADJACENT`, `SELECT_FARTHEST` ;
- filtres : `MATCH_BRAND`, `MATCH_TYPE`, `MATCH_RARITY` ;
- agrégations/contrôle : `COUNT`, `EXISTS`, `FOR_EACH`, `UNLESS` ;
- calcul : `SCALE` ;
- effets : `ADD_STAT`, `ADD_MODIFIER`, `SCHEDULE_EFFECT`.

Ces primitives composent des effets personnels, d'adjacence, de marque, de type, de rareté, de position ou de sac entier sans dupliquer la logique métier.

## Positions, supports et ordre

Le sac est ordonné de 1 à 5. Les capacités peuvent sélectionner le club source, tous les clubs, les voisins immédiats ou une cible la plus éloignée lorsque celle-ci est unique. Les clubs support restent dans le sac et peuvent produire ou recevoir des contributions même s'ils ne sont actifs sur aucune étape.

Les relations gauche/droite et les effets positionnels sont calculés depuis l'ordre, jamais depuis un identifiant de club codé en dur.

## Chains et effets différés

`SCHEDULE_EFFECT` crée un effet planifié associé à une condition de club compatible. Lors des étapes suivantes, le moteur vérifie la condition, applique la contribution au premier déclenchement qualifié et consomme l'effet. Cette couche répond aux Chains supportées ; elle n'est pas un historique complet de partie.

Lorsque consommation, expiration ou interaction ne sont pas suffisamment qualifiées, l'effet reste partiel/non résolu au lieu d'être inventé.

## Métriques

Les statistiques de base sont Power, Control et Spin. Les contributions statiques qualifiées peuvent aussi exposer Loft, Launch Angle, Bounce Reduction, Groundspin, Wind Resistance et autres modificateurs officiels. Leur présence ne signifie pas qu'une direction physique bénéfique a été prouvée.

`data/strategies/metric_semantics.json` sépare métriques objectives, contextuelles et descriptives. `data/strategies/optimization_policies.json` décrit la politique produit, notamment Power comme objectif principal et Bounce Reduction comme compromis important pour certaines attaques du green.

## Explain

Chaque étape du DSL journalise ses entrées et sorties. Une contribution conserve sa source, sa capacité, sa condition, sa cible, la métrique, la valeur avant, la modification, la valeur après et son niveau de confiance/provenance lorsqu'il est disponible.

Le résultat distingue :

- effets appliqués ;
- effets ignorés parce que leur condition ne correspond pas ;
- capacités partielles ;
- capacités non résolues ;
- effets différés créés, déclenchés ou encore en attente.

## Politique de connaissance

Le texte officiel, les tables de niveaux et les observations validées peuvent justifier une règle. Une ressemblance de nom, une note utilisateur ou une supposition physique ne le peuvent pas. Shoreline Rush, Boundary Rush, Meteor, Perfect Shot, transformations, aléatoire et plusieurs effets terrain restent volontairement non résolus pour cette raison.

L'état détaillé est généré dans [CAPABILITY_AUDIT.md](CAPABILITY_AUDIT.md).

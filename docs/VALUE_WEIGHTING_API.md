# Value Weighting API

La couche de valeur utilisateur est strictement séparée du moteur. Le moteur et `compare-bags` produisent des mesures objectives ; aucun score global, sens de préférence ou classement n'est défini.

## Contrat neutre

- `MetricDefinition` identifie une mesure, sa catégorie et son unité.
- `ComparableMetric` conserve séparément base, contribution des capacités, valeur finale et différence droite moins gauche.
- `WeightingContext` peut recevoir un profil utilisateur, un type de parcours et un objectif.
- `MetricWeightProvider` est le point d'extension d'une future politique de pondération.
- `MetricWeightingRequest` transporte le contexte et les métriques sans calculer de somme ni de score.

Les métriques définies couvrent Power, Control, Spin, ajustement d'angle de lancement, réduction de rebond, nombre maximal de rebonds sur sable et nombre maximal de rebonds sur eau.

## Progression

La progression est suivie par la checklist objective de `OPTIMIZER_API.md`. Elle distingue les contrats disponibles des politiques produit encore absentes et ne produit aucun pourcentage.

L'absence volontaire de score global est une limite explicite du produit actuel : l'agrégation restera hors du moteur et ne sera ajoutée qu'après validation.

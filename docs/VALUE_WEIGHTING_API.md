# Value Weighting API

La couche de valeur utilisateur est strictement séparée du moteur. Le moteur et `compare-bags` produisent des mesures objectives ; aucun score global, sens de préférence ou classement n'est défini.

## Contrat neutre

- `MetricDefinition` identifie une mesure, sa catégorie et son unité.
- `ComparableMetric` conserve séparément base, contribution des capacités, valeur finale et différence droite moins gauche.
- `WeightingContext` peut recevoir un profil utilisateur, un type de parcours et un objectif.
- `MetricWeightProvider` est le point d'extension d'une future politique de pondération.
- `MetricWeightingRequest` transporte le contexte et les métriques sans calculer de somme ni de score.

Les métriques actuellement définies sont Power, Control, Spin, ajustement d'angle de lancement, nombre maximal de rebonds sur sable et nombre maximal de rebonds sur eau.

## Progression

L'API de pondération est prête à **70 % (7 critères sur 10)**.

| Critère | État |
|---|---|
| Mesures indépendantes et typées | prêt |
| Unités explicites | prêt |
| Base, contribution et valeur finale séparées | prêt |
| Différences gauche/droite séparées | prêt |
| Contributions rattachées à un club et une capacité | prêt |
| Contexte profil/parcours/objectif | prêt |
| Protocole de fournisseur de poids | prêt |
| Profil réel et préférences chiffrées de Pierre | manquant |
| Taxonomie validée des parcours et objectifs | manquante |
| Politiques de poids validées par cas d'usage | manquantes |

L'absence volontaire de score global n'est pas un manque : l'agrégation restera hors du moteur et ne sera ajoutée qu'après validation produit.

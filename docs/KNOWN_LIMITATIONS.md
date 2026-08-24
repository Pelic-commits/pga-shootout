# Limites connues

Ces limites sont volontaires ou correspondent à des connaissances insuffisantes. Elles ne doivent pas être présentées comme des bugs tant qu'une observation réelle ne démontre pas un comportement incorrect.

## Physique et portée

- aucune conversion validée de Power vers des yards ;
- aucune garantie qu'un club atteint réellement le green ou une distance donnée ;
- pas de simulation complète de trajectoire, loft, gravité, rebond, roule, eau, sable, arbres ou limites ;
- Wind Resistance est une métrique comparable, pas une simulation aérodynamique ;
- plusieurs effets de terrain et de trajectoire restent non résolus.

## Capacités

L'audit versionné recense 162 occurrences. Dans l'inventaire audité : 84 capacités sont simulées, 2 partielles et 60 non résolues hors partielles, soit 57,53 % des 146 occurrences possédées. Globalement, 86/162 occurrences sont couvertes (53,09 %).

La couverture restante est majoritairement bloquée par ambiguïté sémantique, conflit entre sources, physique/géométrie, historique complexe ou aléatoire/transformation. Une faible couverture n'est donc pas automatiquement une dette logicielle.

Exemples :

- **Shoreline Rush** et **Boundary Rush** : effets physiques non validés ;
- eau, sable et arbres : contexte et comportement physique incomplets ;
- **Meteor** : copie/provenance/récursion insuffisamment spécifiées ;
- **Perfect Shot** : déclenchement et historique nécessaires ;
- transformations et aléatoire : résultat ou distribution non qualifiés.

Un club concerné reste utilisable lorsque les calculs connus sont suffisants. Le résultat devient partiellement évalué et l'inconnue n'est jamais remplacée par zéro. Skyfury, Windstrike et Wave sont des exemples de cette politique.

## Stratégies et optimisation

- Par 4 long et Par 5 ont des séquences distinctes, mais peuvent produire des fronts calculables similaires faute de modèle de portée ;
- la variante de vent expose Wind Resistance sans prouver l'impact physique du vent ;
- la recherche globale et les paires de remplacements restent bornées ou structurellement réduites ;
- `MEILLEUR TROUVÉ` n'est pas un optimum démontré ;
- aucun score global ne départage arbitrairement des compromis ;
- les niveaux inconnus et capacités non résolues peuvent rendre une conclusion indéterminée.

## Écart High Flight historique

Pour High Flight niveau 8 / Cyclotron 8 / Ember 7 / Maelstrom 6 / Sunstorm 6, le moteur calcule `19/10/13`, tandis qu'une observation visuelle historique indique `19/10/14`. Le point de Spin supplémentaire n'est expliqué par aucune contribution qualifiée et n'est pas ajouté artificiellement.

Le cas courant distinct avec High Flight niveau 10 calcule `21/11/14`. Il ne résout pas l'écart historique.

Voir [REGRESSION_CASES.md](REGRESSION_CASES.md).

## Phase de produit

Le développement est gelé pendant l'utilisation réelle. Une limite ne devient prioritaire que si elle provoque une recommandation incompréhensible, un sac oublié, un workflow gênant, une information manquante, une capacité réellement bloquante ou une performance réellement gênante.

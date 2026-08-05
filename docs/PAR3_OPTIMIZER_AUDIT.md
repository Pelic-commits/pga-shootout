# Audit de pertinence de l’optimiseur Par 3

## Résultat reproduit avant correction

La commande `pga-shootout optimize-strategy par3 --partial --limit 5` conservait
les cinq compromis suivants sur l’inventaire réel du 5 août 2026.

| # | Club d’attaque | Type | P/C/S finales | Loft | WR | Bounce | Putter | P/C putter | Supports annoncés |
|---:|---|---|---|---:|---:|---:|---|---|---|
| 1 | High Flight | Hybrid | 12/8/5 | 15° | 75% | — | Homestead | 6/10 | Cyclotron, Cloudcatcher |
| 2 | Ironbark | Iron | 12/8/14 | — | — | — | Rising Flame | 11/9 | Steadfast |
| 3 | High Flight | Hybrid | 12/8/9 | 15° | 75% | 14% | Lowball | 5/11 | Cyclotron, Cloudcatcher |
| 4 | Homestead | Putter | 12/12/— | — | 15% | — | Rook | 11/6 | Steadfast, Jumpstart |
| 5 | Homestead | Putter | 6/10/— | 10° | — | 14% | Lowball | 5/11 | Cloudcatcher, Cyclotron |

Chaque composition ne testait que 8 ordres sur 120. Les objectifs
`all_comparable_metrics` incorporaient Power, Control, Spin et tous les
modificateurs produits pour les deux étapes. Homestead à 6 Power restait donc
non dominé grâce à Control, Loft ou Bounce Reduction. Pour la même raison,
Cyclotron pouvait être appelé support du putt grâce à Bounce Reduction et
Cloudcatcher grâce au Loft. Les calculs étaient techniquement fidèles au Rule
Engine, mais leur usage par l’optimiseur n’était pas fonctionnellement qualifié.

## Règles de pertinence corrigées

- attaque du green : Power, Control et Spin sont les objectifs déclarés ;
- putt : seuls Power et Control participent à la comparaison ;
- Loft est descriptif et n’est jamais maximisé automatiquement ;
- Wind Resistance exige un contexte de vent explicite ;
- Bounce Reduction exige un objectif explicite de réduction du roulement ;
- une métrique inconnue est descriptive ;
- une contribution descriptive reste exportée mais ne qualifie pas un support.

Ces règles proviennent de `metric_semantics.json` et des `metric_uses` de chaque
étape. Elles ne dépendent d’aucun identifiant de stratégie dans l’algorithme.

## Audit factuel des types après correction

La recherche corrigée a évalué 1 920 permutations, soit les 120 ordres complets
de 16 compositions. Le tableau décrit cet espace évalué ; il ne prétend pas
avoir épuisé les 5 596 617 600 candidats théoriques.

| Type | possédés | clubs actifs évalués | meilleure Power finale | meilleur Control à cette Power | meilleur Spin calculé | Loft observé |
|---|---:|---:|---:|---:|---:|---|
| Driver | 14 | 1 | 13 | 9 | 14 | inconnu |
| Hybrid | 9 | 2 | 19 | 10 | 15 | 5° |
| Iron | 14 | 2 | 16 | 9 | 9 | 10° |
| Wedge | 10 | 2 | 13 | 7 | 13 | inconnu |
| Wood | 13 | 1 | 12 | 8 | 7 | inconnu |

Le meilleur concurrent tous types observé est High Flight, Hybrid, à 19 Power,
10 Control et 13 Spin. Le meilleur Iron observé est Divebomb à 16/9/9. Cela
démontre qu’un non-Iron peut rester concurrent lorsque ses statistiques finales
et ses supports le justifient ; cela ne démontre aucune supériorité universelle
d’un type.

| Relation | Statut |
|---|---|
| Power, Control et Spin finaux sont calculables | donnée officielle explicite et Rule Engine |
| Wind Resistance et Bounce Reduction sont séparées | donnée officielle explicite |
| plus de Loft produit un meilleur arrêt | inconnue |
| Loft détermine une distance ou une hauteur | inconnue |
| Spin détermine une distance d’arrêt | inconnue |
| les Irons sont préférés par Pierre sur les Par 3 | observation personnelle du joueur |
| un type est universellement supérieur | non établi |

Une composition sensible à la position, l’adjacence, la distance ou aux effets
différés conserve ses 120 permutations. Une composition démontrée insensible à
l’ordre n’en évalue qu’une et enregistre la preuve d’équivalence. Les modes
`legacy_reduced` et `full_120` servent uniquement au diagnostic. La limite de
sécurité demeure visible : la recherche bornée ne garantit pas l’optimum global
sur l’inventaire entier.


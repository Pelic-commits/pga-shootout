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

### Audit ciblé Meteor / Flashpoint — 30 août 2026

Source utilisée exclusivement : catalogue normalisé local, `semantic_map.json` et
export officiel versionné capturé le 21 juillet 2026 (page datée du 14 juin 2026).
SHA-256 source : `449831121cada54114ac8175af38b99ab8bd6ecf15310600a1df9192ca703a14`.
Aucune réimportation, aucun changement de catalogue, de niveau ou de possession.

**Meteor** (`meteor`, Mythical / Mythical / Wedge) est déjà possédé au niveau 9.
Ses statistiques P/C/S officielles sont : 9 = 2/2/5 ; 10 = 2/2/6 ; 11 = 2/3/6 ;
12 et Elite = 3/3/6.

| Capacité | Texte officiel exact | Valeurs / activation | Qualification actuelle |
|---|---|---|---|
| Alien Relic (Left) | The club to the left of Meteor gains an extra instance of each of its abilities.  - Elite Level: Ability can wrap to the other side of the bag. | x2 aux niveaux 9–12 et Elite | Non résolue : instance copiée, niveau, provenance, ordre, interactions de copies/récursion à valider. |
| Alien Relic (Right) | The club to the right of Meteor gains an extra instance of each of its abilities.  - Elite Level: Ability can wrap to the other side of the bag. | x2 aux niveaux 10–12 et Elite | Même blocage ; inactive au niveau utilisateur 9. |
| Alien World | When you hit with Meteor, the ball bounces off of fairway. (Forever.) | ✔ aux niveaux 12 et Elite | Physique non qualifiée ; inactive au niveau utilisateur 9. |

Au niveau 9, **une** capacité native active est non résolue, pas trois. Les statistiques
de base et les effets entrants qualifiés sont calculables. L'audit avant modification
produisait déjà cinq candidats autour de Meteor, dont une attaque à 8/6/7 calculables.
L'absence perçue n'est donc pas un défaut de catalogue, de possession ou une exclusion
logicielle systématique. La copie inconnue n'améliore pas artificiellement son faible
profil calculable ; une recherche bornée sans club imposé ne garantit pas sa sélection.
Aucune capacité Meteor n'a été implémentée : les primitives actuelles ne lèvent pas
les ambiguïtés de copie ou de physique.

**Flashpoint** (`flashpoint`, Phoenix / Legendary / Driver) est déjà possédé au niveau 7.
Statistiques P/C/S : 7 = 5/8/5 ; 8 = 6/8/6 ; 9 = 7/9/6 ; 10 = 8/9/7 ;
11 = 9/10/7 ; 12 et Elite = 10/10/8.

| Capacité | Texte officiel exact | Valeurs | Qualification actuelle |
|---|---|---|---|
| Rocket Boosters | Gain 25% of the power of clubs to its left and right. | Niveaux 7→12 : +25, +26, +27, +28, +29, +30 % ; Elite +40 % | Non résolue : Power de base ou finale des voisins et ordre d'application non validés. Le 25 % du descriptif ne remplace pas la table de niveaux. |
| Boundary Rush | Shots from this club travel X% further and faster over water or out of bounds. | +50 % aux niveaux 7–12 et Elite | Physique/géométrie requises ; aucune conversion en Power. |

Flashpoint est admissible comme actif non-putter et comme support potentiel non résolu,
sans règle liée à son nom. Ses deux capacités natives restent non résolues ; ses stats
et synergies entrantes qualifiées sont calculées. Aucun niveau utilisateur ne manque
pour ces deux clubs. Les tests réels sont des smoke tests ; les tests de logique utilisent
des clubs synthétiques et le test « nouveau club par données seulement » est conservé.

### Stabilité : métriques du modèle, pas preuve physique

Landing/Wind exposent des axes de comparaison indépendants. Le moteur existant additionne
les contributions statiques ; ce lot ne valide ni ne modifie les règles réelles de cumul.
Une valeur telle que 132 % de Wind Resistance est une somme calculée, **pas** une preuve
d'immunité au vent ni un effet physique extrapolé au-delà de 100 %. Les cartes avertissent
lorsque plusieurs sources contribuent au même axe. Les effets absents d'un sac partiel
ne deviennent pas des zéros et les écarts correspondants sont indéterminés.

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

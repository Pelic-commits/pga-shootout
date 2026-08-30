# Guide de l'optimiseur de sacs

## Objectif

L'optimiseur recherche des sacs de cinq clubs dans l'inventaire enregistré, évalue chaque étape d'une stratégie et présente des gains, pertes et inconnues. Power est l'objectif principal par défaut ; aucun score global n'est inventé.

## Stratégies disponibles

| Stratégie | Séquence déclarée | Supports disponibles |
|---|---|---:|
| Par 3 | Atteindre le green → Putt | 3 |
| Par 4 court | Attaque directe du green → Putt | 3 |
| Par 4 long | Départ → Approche vers le green → Putt | 2 |
| Par 5 | Long départ → Longue approche → Putt | 2 |

Par 4 long et Par 5 possèdent des exigences conceptuelles distinctes, mais l'absence de modèle Power→distance peut produire des fronts calculables similaires. La variante **Vent contraire / latéral** existe pour Par 4 long et Par 5 et expose Wind Resistance séparément ; elle ne simule pas la physique du vent.

## Build From Scratch

Le workflow central construit un sac depuis cinq places vides. Son contrat accepte uniquement stratégie, inventaire et niveaux actuels, clubs obligatoires, objectifs, contraintes, marques et contexte explicitement demandé. Il ne peut pas recevoir de sac cible, sac de référence, composition voisine ou résultat précédent.

- choisissez un club principal puis, facultativement, d'autres clubs obligatoires ;
- laissez l'affectation aux étapes sur **Automatique** ;
- définissez éventuellement Control et Spin minimums ;
- choisissez éventuellement des marques autorisées ;
- utilisez **Options avancées**, fermé au démarrage, pour les rôles/positions, minimums des coups suivants, variante de contexte, scénario, nombre de résultats ou limite de recherche.

**Automatique** laisse le moteur chercher une affectation. **Support** interdit au club d'occuper une étape active. **Variable** conserve plusieurs interprétations possibles. Une position verrouillée fixe l'ordre physique et peut modifier les synergies gauche/droite.

## Politique des métriques

La configuration versionnée emploie actuellement :

- progression : Power, Control et Spin comme métriques objectives ;
- attaque du green : Power, Control et Spin ; Bounce Reduction devient un compromis important pour Driver/Wood/Hybrid ;
- putt : Power et Control ;
- profil d'atterrissage descriptif : Loft, Bounce Reduction, Groundspin, Spin, Control et Wind Resistance selon le contexte.

Cette politique traduit les besoins du joueur ; elle ne prouve aucune relation physique non validée.

### Axes séparés Atterrissage et Vent

Build From Scratch réserve les propositions dans cet ordre : puissance maximale trouvée,
**MEILLEUR ATTERRISSAGE**, **STABILITÉ AU VENT**, puis les paliers Control/Spin.
Un axe n'est proposé que si sa métrique est pertinente et calculable dans les candidats
explorés. Le nombre de résultats demandé reste une limite : avec un seul résultat,
seule la proposition Power est conservée.

- Atterrissage : meilleure Bounce Reduction calculable, puis Power, Control, Spin et
  putt pour départager. L'axe est activé par la politique fonction/type pour une attaque
  du green avec Driver/Wood/Hybrid. Il est également possible avec un contexte
  d'atterrissage explicite reconnu par le registre des métriques. Un Iron n'est pas
  automatiquement promu pour son rebond ; la progression conserve sa politique actuelle.
- Vent : même sélection sur Wind Resistance, **uniquement** si le contexte déclaré
  rend cette métrique objective. Dans la GUI : Par 4 long ou Par 5 → Options avancées
  → Vent contraire / latéral. Sans contexte, la résistance reste descriptive dans le
  détail et ne justifie pas, à elle seule, une place support.
- Il n'existe ni somme pondérée ni conversion en yards. La proposition de stabilité
  peut sacrifier beaucoup de Power : les écarts restent visibles, c'est au joueur de décider.
- Un même candidat gagnant plusieurs axes n'est affiché qu'une fois, avec plusieurs badges.

Les métriques secondaires pertinentes apparaissent dans la synthèse du coup actif,
pas dans toutes les tuiles. Les contributions correspondantes des supports sont
placées en tête de leur justification courte ; les autres restent dans le détail.
Les différences de pourcentage sont exprimées en **points de pourcentage**.
Une absence de modificateur vaut zéro seulement dans une évaluation complète ;
dans un sac partiel elle reste indéterminée. Les valeurs effectivement calculées restent
consultables, sans prétendre inclure les effets inconnus. Plusieurs sources additives
sont accompagnées d'un avertissement : leur cumul réel dans le jeu reste à valider.

Exemple contrôlé avec les niveaux réels audités (ce n'est pas une preuve d'optimum) :
High Flight / Jumpstart / Steadfast / Gearshift / Commonlaw donne une attaque à
**19/14/9**, sans bonus Bounce calculé. Remplacer Jumpstart par Cyclotron à la même
place donne **16/14/14** et **16 % Bounce Reduction** : **−3 Power, +5 Spin,
+16 points de Bounce Reduction**, sans changement du putt. Les deux évaluations sont
complètes pour les capacités prises en compte à ces niveaux.

Exemple de recherche bornée avec vent : High Flight / Cyclotron / Divebomb / Rook /
Commonlaw produit un départ à **13/11/11** et une somme de Wind Resistance de **132 %**,
contre **17/14/14 et 75 %** pour la proposition Power de cette recherche : **−4 Power,
−3 Control, −3 Spin, +57 points** de résistance calculée. Le cumul de plusieurs sources
est explicitement à valider en jeu ; il ne signifie pas une réduction physique de 132 %.

## Sacs de référence — outils secondaires

Une référence peut toujours servir aux anciens workflows d'amélioration ou de remplacement. Elle n'est ni lue par la génération Build From Scratch, ni injectée dans ses pools, son pruning ou son classement.

Les rôles sont dérivés des étapes de la stratégie, plus **Automatique**, **Support** et **Variable**. Ils appartiennent au sac de référence et ne changent pas le club ni le Rule Engine. **Utiliser les rôles de la référence** préremplit les sélections ; le joueur peut les modifier avant de lancer.

La comparaison est fonction à fonction : une mesure observée au départ n'est pas arbitrairement comparée à une approche.

## Remplacement ciblé

**Même type que le club actuel** est la politique par défaut. Elle filtre les clubs possédés admissibles sur le type officiel du club sortant. **Tous les types admissibles** élargit volontairement la recherche. Un club obligatoire incompatible provoque une explication plutôt qu'un changement silencieux de politique.

Les contraintes de type et de marques sont cumulatives.

La profondeur indique un maximum :

- jusqu'à 1 = profondeurs 0 et 1 ;
- jusqu'à 2 = profondeurs 0, 1 et 2.

Tous les résultats retenus à profondeur 1 sont injectés avant l'exploration structurellement réduite des paires. Chaque résultat exporte sa profondeur réelle.

## Marques autorisées

Toutes les marques sont autorisées par défaut. Une ou plusieurs marques peuvent être retenues. Les clubs obligatoires et candidats doivent respecter la restriction. Une référence interdite reste visible comme comparaison ; la meilleure solution conforme est alors **MEILLEUR SAC ADMISSIBLE**.

## Recherche et preuve

La recherche principale applique successivement admissibilité de l'inventaire, clubs imposés, fonctions actives possibles, supports potentiels issus des capacités, marques, contraintes, symétries d'ordre et évaluation du Rule Engine. Un contrôle local retire toute proposition dominée par un remplacement d'une place. Une place non obligatoire sans rôle actif, contribution calculable ou inconnue pertinente est rejetée. Aucun score de support n'est calculé.

- **MAXIMUM PROUVÉ** : espace pertinent exhaustif ou éliminations sûres ;
- **MEILLEUR TROUVÉ** : budget, réduction structurelle ou exploration incomplète.

La recherche jusqu'à deux remplacements ne peut pas perdre le meilleur résultat à un changement, mais cela ne rend pas toutes les paires exhaustives.

## Présentation des résultats

La zone principale affiche des cartes de sacs avec une catégorie issue du résultat existant (puissance, compromis Control/Spin, atterrissage, vent lorsque demandé) et un badge distinct si l'évaluation est partielle. La synthèse montre les coups actifs ; cinq colonnes homogènes montrent les clubs dans l'ordre physique. Les valeurs P/C/S proviennent de `final_stats`, sans recalcul ni substitution par les statistiques de base.

Le coup affiché est le premier coup actif du club, ou le premier coup évalué pour un support ; cette convention est toujours légendée. Un club actif sur plusieurs coups conserve tous ses détails dans Explain. `—` reste une valeur indisponible, jamais zéro. Les écarts numériques sont fournis par le moteur par rapport au résultat de puissance maximale, sans jugement arbitraire sur leur valeur utilisateur.

Dans les parcours secondaires accessibles par **Outils**, les catégories existantes restent :

- sac actuel ;
- améliorations sans perte calculable, affichées **Amélioration sans contrepartie observée** ;
- compromis ;
- compromis partiellement évalués ;
- meilleur sac admissible sous restriction.

Les propositions strictement inférieures sans avantage pertinent sont masquées. Une capacité inconnue pertinente empêche ce masquage automatique et reste signalée.

Le bouton **Détail technique ↗** ouvre une fenêtre séparée : résumé, étapes, raisons de sélection, capacités, contributions reçues/envoyées et effets différés. Elle reste fermée après chaque nouvelle recherche. Les exports JSON et texte complets sont disponibles dans **Outils**. Les courtes contributions des cartes sont des observations, pas un bilan contrefactuel du retrait du club.

## Clubs partiellement évalués

Un club comme Skyfury peut être imposé même si Boundary Rush reste non résolue. Le moteur optimise les contributions connues autour de lui, marque le résultat partiel et ne suppose jamais que l'inconnue vaut zéro. La même règle s'applique notamment à Windstrike ou Wave lorsque leurs capacités non résolues sont pertinentes.

Meteor et Flashpoint suivent exactement ce chemin générique : présence dans le catalogue,
possession et niveau connu dans SQLite suffisent à les rendre admissibles aux rôles
compatibles. Ils ne sont ni exclus à cause d'une capacité inconnue, ni favorisés par un
bonus supposé. Leur sélection automatique dépend des calculs connus et de la recherche
bornée ; les imposer permet d'explorer explicitement un sac autour d'eux.

### Supports amplificateurs

Le pool reconnaît maintenant les programmes `ABILITY_EFFECT_MULTIPLIER` et leur
relation d'adjacence. La recherche explore le voisin amplifié et son orientation,
sans sac sauvegardé ni préférence pour un nom de club. Le wrap explicite exige une
énumération positionnelle ; le niveau actuel sans wrap conserve les réductions
d'ordre sûres. La valeur du support est celle du contrefactuel existant : que perd
le sac lorsque cet amplificateur est retiré ?

La carte peut afficher, par exemple, **Alien Relic Left : texas tee de Blacksmith —
5 → 10 Power → Blacksmith**. Le détail technique et les exports conservent toutes
les transformations et contributions. Pour une capacité non qualifiée : **×2 [capacité]
de [voisin] · effet final non résolu**. Il ne s'agit jamais de doubler les stats finales.

Au niveau réel 9, Meteor amplifie seulement son voisin gauche. Son faible profil
propre ne l'élimine plus lorsqu'il apporte un bonus utile, mais ne garantit jamais
sa sélection. Exemple observé sans imposer Meteor : Blacksmith / Meteor / Commonlaw /
Sunstorm / Gearshift, attaque **23/11/7**, dont Texas Tee passe de +5 à +10. Le retrait
du support fait perdre 5 Power dans ce sac. Une proposition Atterrissage High Flight /
supports Bounce peut rester meilleure sur cet axe sans Meteor.

Les capacités de copie en cascade, pourcentages et modificateurs non qualifiés restent
partiels. Stormbringer/XLR8R et Alien World ne sont pas traités par ce lot.

## Inventaire dynamique et performances

SQLite est relu avant chaque analyse. La GUI exécute le calcul en arrière-plan. Le filtre même type réduit naturellement l'espace. Les recherches tous types ou à deux changements peuvent être plus longues ; la priorité est la cohérence des résultats.

Voir [ARCHITECTURE.md](ARCHITECTURE.md), [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) et [REGRESSION_CASES.md](REGRESSION_CASES.md).

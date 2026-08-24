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

## Optimiser autour de mes clubs

Le constructeur interactif est le workflow central.

- choisissez de un à cinq clubs obligatoires ;
- attribuez **Automatique**, une étape active, **Support** ou **Variable** ;
- verrouillez une position si l'ordre est imposé ;
- choisissez le club/étape principal dont Power structure les paliers ;
- définissez éventuellement Control et Spin minimums ;
- définissez Power/Control minimums du putt ou conservez le putter actuel ;
- choisissez une référence et des marques autorisées.

**Automatique** laisse le moteur chercher une affectation. **Support** interdit au club d'occuper une étape active. **Variable** conserve plusieurs interprétations possibles. Une position verrouillée fixe l'ordre physique et peut modifier les synergies gauche/droite.

## Politique des métriques

La configuration versionnée emploie actuellement :

- progression : Power, Control et Spin comme métriques objectives ;
- attaque du green : Power, Control et Spin ; Bounce Reduction devient un compromis important pour Driver/Wood/Hybrid ;
- putt : Power et Control ;
- profil d'atterrissage descriptif : Loft, Bounce Reduction, Groundspin, Spin, Control et Wind Resistance selon le contexte.

Cette politique traduit les besoins du joueur ; elle ne prouve aucune relation physique non validée.

## Sacs de référence

Une référence peut stocker libellé, usage, stratégie, club principal, stable/expérimental, notes, métriques observées et rôles par club. Elle est évaluée et comparée aux propositions si elle respecte les contraintes. Sinon elle reste témoin non admissible.

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

La recherche applique successivement admissibilité de l'inventaire, rôles, positions, types, marques, contraintes, ordre physique et évaluation du Rule Engine. Des caches de session évitent de recalculer les mêmes états sans masquer les changements d'inventaire.

- **MAXIMUM PROUVÉ** : espace pertinent exhaustif ou éliminations sûres ;
- **MEILLEUR TROUVÉ** : budget, réduction structurelle ou exploration incomplète.

La recherche jusqu'à deux remplacements ne peut pas perdre le meilleur résultat à un changement, mais cela ne rend pas toutes les paires exhaustives.

## Présentation des résultats

La zone principale sépare :

- sac actuel ;
- améliorations sans perte calculable, affichées **Amélioration sans contrepartie observée** ;
- compromis ;
- compromis partiellement évalués ;
- meilleur sac admissible sous restriction.

Les propositions strictement inférieures sans avantage pertinent sont masquées. Une capacité inconnue pertinente empêche ce masquage automatique et reste signalée.

Les onglets détaillent actifs, supports, statistiques finales, contributions reçues/envoyées, effets différés et Explain. Les exports texte/JSON conservent référence, rôles, profondeur, complétude, statuts, gains, pertes, inconnues, marques et raison d'affichage.

## Clubs partiellement évalués

Un club comme Skyfury peut être imposé même si Boundary Rush reste non résolue. Le moteur optimise les contributions connues autour de lui, marque le résultat partiel et ne suppose jamais que l'inconnue vaut zéro. La même règle s'applique notamment à Windstrike ou Wave lorsque leurs capacités non résolues sont pertinentes.

## Inventaire dynamique et performances

SQLite est relu avant chaque analyse. La GUI exécute le calcul en arrière-plan. Le filtre même type réduit naturellement l'espace. Les recherches tous types ou à deux changements peuvent être plus longues ; la priorité est la cohérence des résultats.

Voir [ARCHITECTURE.md](ARCHITECTURE.md), [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) et [REGRESSION_CASES.md](REGRESSION_CASES.md).

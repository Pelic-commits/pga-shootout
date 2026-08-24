> **HISTORIQUE — NE DÉCRIT PAS L'ÉTAT ACTUEL DU PROJET.** Consultez le [README principal](../../README.md) et l'[audit documentaire](../DOCUMENTATION_AUDIT.md).

# Recherche de compositions et contrôles de référence

## Constat High Flight

Le scénario historique validé contient, dans cet ordre : High Flight niveau 8,
Cyclotron niveau 8, Ember niveau 7, Maelstrom niveau 6 et Sunstorm niveau 6.
Ces niveaux sont désormais figés dans une base temporaire de test : ils ne sont
plus présentés comme l'état courant de SQLite.

Avec le catalogue normalisé, les règles validées et le contexte Par 3 actuels,
High Flight part de **12 Power / 8 Control / 5 Spin** et reçoit :

- Cyclotron : +4 Spin et 14 % de Bounce Reduction ;
- Ember : +5 Power ;
- Maelstrom : +2 Spin et 12 % de Bounce Reduction ;
- Sunstorm : +2 Power, +2 Control et +2 Spin ;
- ses propres effets descriptifs : +5° de Loft et 75 % de Wind Resistance.

Le résultat reproductible est donc **19 / 10 / 13**. Les 120 ordres de cette
composition ne produisent que `17/8/7`, `17/8/11`, `19/10/9` ou `19/10/13`.
Aucun ne produit 14 Spin. La valeur **19/10/14 est désormais visuellement
confirmée dans le jeu** pour ce sac exact. Le Rule Engine reste néanmoins à
19/10/13 : le point de Spin supplémentaire n'existe dans aucune contribution
officielle actuellement qualifiée et n'est pas ajouté artificiellement.

Au 24 août 2026, SQLite contient High Flight niveau 10, Cyclotron niveau 8,
Ember niveau 8, Maelstrom niveau 6 et Sunstorm niveau 6. Le même ordre produit
**21/11/14** avec ces niveaux actuels. Ce résultat ne résout pas l'ancien écart
13/14 : le scénario historique niveau 8 reste calculé à 13 Spin, tandis que le
niveau 10 possède une statistique de base différente.

## Références et garde-fou

Chaque sac enregistré compatible est injecté indépendamment de la présélection
globale avec `origin = reference_bag`, y compris dans le constructeur
interactif. Son ordre enregistré et toutes ses permutations structurellement
distinctes sont évalués. Les rôles actifs observés dans une référence compatible
servent aussi à approfondir prioritairement ce sous-espace sans coder le nom
d'un club.

Les meilleures solutions retenues enrichissent un cache de session. Une
recherche moins contrainte réutilise toute solution antérieure compatible. La
clé comprend la signature exacte de l'inventaire, la version du catalogue, la
stratégie, ses variantes, le scénario, le mode d'évaluation et le mode d'ordre ;
une donnée périmée ne peut donc pas être réinjectée.

Après évaluation, une proposition dominée sur toutes les métriques objectives
par une référence est retirée. Une proposition reste visible si elle apporte un
gain ailleurs, par exemple au putter : ce compromis est affiché métrique par
métrique, sans score global.

## Trois recherches

- `global` explore de nouvelles compositions avec une réduction déterministe.
  Elle reste partielle et bornée.
- `improve_bag` part d'un sac enregistré. À profondeur 1, chaque club peut être
  remplacé par chaque club possédé admissible et chaque composition sensible
  est réordonnée sur les 120 permutations. Cette passe est exhaustive.
- `around_club` conserve le club actif choisi et explore les remplacements de
  ses quatre supports. À profondeur 2, seules des paires possédant une relation
  structurelle démontrable sont admises ; la recherche est donc explicitement
  `structurally_reduced`.

Le `support_potential` est une relation, jamais un score. Il distingue les
relations directes, d'adjacence, de marque, de type, de rareté, de sac entier,
de Chain et les sémantiques encore non résolues. Les statistiques propres d'un
support ne suffisent pas à l'exclure.

## Diagnostic

```powershell
pga-shootout trace-composition par3 high_flight cyclotron ember maelstrom sunstorm
```

Cette commande indique l'étape exacte à laquelle une composition est conservée
ou éliminée. Les exports contiennent les volumes par étape, les origines, le
nombre de permutations, la profondeur et la complétude. Le diagnostic distingue
les équivalences d'ordre prouvées sûres, les contraintes de position, la
réduction heuristique du pool de supports et la limite de budget. Les solutions
réutilisées portent l'origine `known_candidate`.

## Audit des anomalies du constructeur interactif

La divergence High Flight 17 → 20 venait de l'ordonnancement en largeur : avec
High Flight seul, le budget offrait un premier jeu de supports à de nombreuses
affectations de putter, sans approfondir suffisamment l'affectation Ember. Une
fois Ember imposé, les mêmes 1 000 évaluations se concentraient sur ce seul
sous-espace et trouvaient 20. Le sous-espace actif issu du sac enregistré est
maintenant approfondi en plus de la passe large.

La divergence Divebomb 12/7/5 → 16/9/9 avait une cause plus directe : le sac
enregistré Divebomb / Jumpstart / Steadfast / Ember / Sunstorm était construit
par `reference_candidates`, mais n'était jamais fusionné dans la branche
`interactive_builder`. Il est désormais injecté avant toute réduction et ne
peut pas être supprimé par le budget.

Le contrôle 16/9/9 utilise désormais explicitement Divebomb niveau 8. Dans
l'inventaire SQLite actuel, Divebomb est niveau 10 et le même sac enregistré
produit **17/10/9**. Les deux résultats décrivent donc deux contextes distincts.

Une recherche interactive bornée annonce **MEILLEURE PUISSANCE TROUVÉE**. Le
statut **MAXIMUM PROUVÉ** est réservé aux espaces réellement exhaustifs.

La propriété de contrôle est la suivante : pour une stratégie, un contexte, un
objectif et des minimums identiques, si les clubs obligatoires de A sont inclus
dans ceux de B, toute solution B déjà observée est admissible dans A. Le meilleur
objectif connu de A doit donc être supérieur ou égal à celui de B. Les tests
appliquent cette monotonie à Power, aux minimums Control/Spin, au putt et aux
séquences de deux ou trois coups. Pour une recherche bornée, cette garantie porte
sur les références et solutions effectivement connues ; elle ne transforme pas
une exploration heuristique en preuve d'optimum absolu.

## Fraîcheur et Gearshift

L'inventaire SQLite est relu avant chaque clic sur « Lancer l'analyse ». Les
niveaux, nouveaux clubs et horodatage utilisés figurent dans le résultat ; un
redémarrage n'est pas nécessaire.

Au 8 août 2026, Gearshift est possédé au niveau 8 : Putter légendaire PALO,
13 Power, 5 Control et aucune statistique Spin officielle. Ses deux capacités
sont entièrement résolues : à gauche, `First Gear` donne à tout le sac +1
Control et 11 % de Bounce Reduction ; à droite, `Top Gear` donne à tout le sac
+1 Power et 60 % de Groundspin. Il n'a ni Chain ni effet non résolu au niveau
actuel. Il peut être actif comme putter ou support positionnel.

## Performance et portée de la preuve

Sur l'inventaire réel de 73 clubs évaluables, la recherche exhaustive d'un
remplacement parcourt quelques centaines de compositions et plusieurs dizaines
de milliers de permutations. Les mesures de ce lot sont environ 86 à 116
secondes selon le club fixé et le sac. La GUI reste réactive pendant le calcul,
mais cette durée dépasse la cible idéale de quelques secondes. La recherche
globale bornée à 2 000 candidats prend environ huit secondes sur la même machine.

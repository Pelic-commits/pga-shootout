# Recherche de compositions et contrôles de référence

## Constat High Flight

Le sac SQLite enregistré `par3_high_flight` contient, dans cet ordre : High
Flight niveau 8, Cyclotron niveau 8, Ember niveau 7, Maelstrom niveau 6 et
Sunstorm niveau 6.

Avec le catalogue normalisé, les règles validées et le contexte Par 3 actuels,
High Flight part de **12 Power / 8 Control / 5 Spin** et reçoit :

- Cyclotron : +4 Spin et 14 % de Bounce Reduction ;
- Ember : +5 Power ;
- Maelstrom : +2 Spin et 12 % de Bounce Reduction ;
- Sunstorm : +2 Power, +2 Control et +2 Spin ;
- ses propres effets descriptifs : +5° de Loft et 75 % de Wind Resistance.

Le résultat reproductible est donc **19 / 10 / 13**. Les 120 ordres de cette
composition ne produisent que `17/8/7`, `17/8/11`, `19/10/9` ou `19/10/13`.
Aucun ne produit 14 Spin. Le point annoncé dans `19/10/14` n'existe dans aucune
contribution validée de la base actuelle. Il s'agit d'un écart de donnée ou de
règle à valider dans le jeu, et non d'une composition que le générateur aurait
supprimée. Le moteur ne l'invente pas.

## Références et garde-fou

Chaque sac enregistré compatible est injecté indépendamment de la présélection
globale avec `origin = reference_bag`. Son ordre enregistré et, si nécessaire,
ses 120 permutations sont évalués. En recherche locale, la ligne `SAC ACTUEL`
désigne toujours l'ordre réellement sauvegardé.

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
nombre de permutations, la profondeur et la complétude. Les trois origines sont
`reference_bag`, `reference_neighborhood` et `global_search`.

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


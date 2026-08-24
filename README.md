# PGA TOUR Golf Shootout Bag Optimizer

Assistant local sous Windows pour évaluer, comparer et rechercher des sacs de cinq clubs à partir du catalogue versionné de **PGA TOUR Golf Shootout** et de l'inventaire réel du joueur.

L'application calcule des statistiques objectives, applique les capacités qualifiées par un Rule Engine piloté par les données, puis explique ses propositions métrique par métrique. Elle ne produit aucun score global opaque et ne prétend pas simuler la physique complète du jeu.

## Démarrer sous Windows

Prérequis : **Windows 10/11** et **Python 3.11 ou plus récent avec Tcl/Tk** installé depuis [python.org](https://www.python.org/downloads/).

- Double-cliquez sur **`OPTIMISER_MES_SACS.bat`** pour ouvrir directement l'optimiseur graphique.
- Double-cliquez sur **`GERER_MON_INVENTAIRE.bat`** pour modifier les clubs possédés, leurs niveaux et leurs cartes.
- **`DEMARRER_PGA_SHOOTOUT.bat`** ouvre l'assistant textuel historique, encore supporté pour gérer l'inventaire, les sacs et tester un club.

Le lanceur de l'optimiseur recherche un Python 3.11+ réellement compatible avec Tkinter, prépare l'environnement local `.venv`, vérifie Tk, SQLite, le registre de stratégies et l'inventaire, puis ouvre la fenêtre. Son diagnostic se trouve dans `logs/gui_preflight.txt`.

Le premier lancement peut installer le projet localement. Il n'y a rien à compiler et aucun serveur à installer : l'application est écrite en Python, utilise Tkinter et stocke les données utilisateur dans SQLite.

Guide détaillé : [Premier lancement](docs/FIRST_RUN.md).

## Workflow principal : optimiser autour de mes clubs

Dans l'optimiseur graphique :

1. choisissez une stratégie : Par 3, Par 4 court, Par 4 long ou Par 5 ;
2. sélectionnez de un à cinq clubs obligatoires ;
3. laissez leur rôle sur **Automatique**, ou choisissez une étape active, **Support** ou **Variable** ;
4. verrouillez une position seulement si l'ordre doit être conservé ;
5. choisissez éventuellement un sac de référence ;
6. conservez Power comme objectif principal, puis indiquez si nécessaire des minimums de Control et Spin et des contraintes de putt ;
7. limitez éventuellement les marques autorisées ;
8. lancez l'analyse et comparez les gains, pertes et inconnues.

Les clubs support peuvent être retenus pour leurs synergies même s'ils ne jouent pas un coup actif. L'inventaire SQLite est relu avant chaque analyse : un changement enregistré dans l'éditeur est disponible sans redémarrer l'optimiseur.

La politique de métriques est une configuration produit, pas une loi physique du jeu. Power est l'objectif principal par défaut. Control et Spin servent de contraintes ou d'objectifs ordonnés. Pour une attaque du green avec Driver, Wood ou Hybrid, Bounce Reduction peut constituer un compromis important. Le profil d'atterrissage affiche séparément Loft, Bounce Reduction, Groundspin, Spin, Control et Wind Resistance lorsque le contexte le rend pertinent.

## Sacs de référence et résultats

Un sac enregistré peut porter des métadonnées utilisateur : libellé, usage, stratégie, club principal, statut stable/expérimental, notes, métriques observées et rôles par club. Ces informations aident à interpréter et comparer le sac réellement joué ; elles ne modifient ni le catalogue ni le Rule Engine.

Les rôles disponibles sont **Automatique**, les étapes définies par la stratégie, **Support** et **Variable**. Un rôle appartient au sac : le même club peut avoir un autre rôle dans une autre référence. L'action **Utiliser les rôles de la référence** préremplit le constructeur sans lancer automatiquement l'analyse.

Terminologie des résultats :

- **SAC ACTUEL** : référence réelle du joueur ;
- **AMÉLIORATION SANS PERTE** : propriété affichée dans la GUI sous **Amélioration sans contrepartie observée** ; au moins un gain pertinent et aucune perte calculable ;
- **COMPROMIS** : gains et pertes explicites ;
- **COMPROMIS PARTIELLEMENT ÉVALUÉ** : une inconnue pertinente empêche une conclusion complète ;
- **MEILLEUR SAC ADMISSIBLE** : meilleure solution trouvée sous une restriction que la référence ne respecte pas ;
- **MEILLEUR TROUVÉ** : meilleure solution d'une recherche bornée ou réduite ;
- **MAXIMUM PROUVÉ** : maximum seulement lorsque l'espace pertinent a été évalué exhaustivement ou éliminé par des preuves sûres.

Une proposition strictement inférieure sans avantage pertinent est masquée dans la zone principale. Une capacité non résolue n'est jamais assimilée à zéro.

## Remplacer un club

Le mode **Remplacer un club de mon sac** propose deux politiques :

- **Même type que le club actuel** — choix par défaut ;
- **Tous les types admissibles** — changement de type explicite, sous réserve des rôles, de l'inventaire et des autres contraintes.

Un club obligatoire incompatible produit un conflit lisible ; l'application ne change jamais silencieusement la politique choisie.

La profondeur utilisateur signifie :

- **Jusqu'à 1 remplacement** : la référence et toutes les solutions à un changement ;
- **Jusqu'à 2 remplacements** : profondeurs 0, 1 et 2. Tous les résultats retenus à profondeur 1 sont inclus avant l'exploration des paires.

La passe à un remplacement est exhaustive lorsqu'elle est annoncée comme telle. Les paires restent structurellement réduites : l'ensemble jusqu'à deux changements porte donc **MEILLEUR TROUVÉ**, jamais **MAXIMUM PROUVÉ**.

## Marques autorisées

**Toutes les marques** est le réglage par défaut. Une ou plusieurs marques peuvent être sélectionnées. La contrainte se combine avec les clubs obligatoires, le remplacement ciblé et la politique de type. Aucun candidat non conforme n'est proposé.

Un sac de référence non conforme reste affiché comme témoin, mais n'est pas admissible. Le résultat pertinent devient alors **MEILLEUR SAC ADMISSIBLE**. Ce filtre générique est notamment utile pour les tournois ; il ne constitue pas un mode tournoi distinct.

## Ce que l'application sait faire

- charger les statistiques, niveaux, marques, types, raretés et capacités du catalogue ;
- gérer l'inventaire, les cartes, les sacs et les références dans SQLite avec sauvegardes ;
- évaluer les capacités déterministes qualifiées en modes strict ou partial ;
- appliquer les synergies de position, d'adjacence, de marque, de type, de rareté et de sac entier ;
- représenter les Chains comme effets différés simples entre étapes compatibles ;
- comparer Power, Control, Spin et les métriques statiques qualifiées ;
- rechercher des compositions et ordres de sacs sous contraintes ;
- conserver des clubs à capacités non résolues avec avertissement ;
- exporter les résultats en texte et JSON avec contributions, gains, pertes et inconnues.

## Ce que l'application ne prétend pas faire

- convertir Power en yards ou prouver qu'un coup atteint une distance donnée ;
- simuler complètement trajectoire, eau, sable, arbres, limites, rebonds ou vent ;
- inventer l'effet de Meteor, Perfect Shot, transformations ou capacités aléatoires ;
- donner une valeur arbitraire unique à un sac ;
- garantir un optimum absolu lorsque la recherche est annoncée comme bornée.

Voir [Limites connues](docs/KNOWN_LIMITATIONS.md) et [Audit des capacités](docs/CAPABILITY_AUDIT.md).

## Architecture et données

```text
Catalogue versionné + SQLite utilisateur
                    ↓
        Rule Engine piloté par le DSL
                    ↓
      Évaluation par étapes de stratégie
                    ↓
 Recherche / contraintes / références
                    ↓
          GUI + exports texte/JSON
```

Le catalogue normalisé `data/normalized/clubs_official.json` contient **88 clubs**, **9 marques** et **162 occurrences de capacités**. La capture brute immuable est conservée dans `data/raw/`. SQLite (`data/pga_shootout.sqlite`) est la source de vérité de l'état utilisateur.

Documentation : [Architecture](docs/ARCHITECTURE.md), [Rule Engine](docs/RULE_ENGINE.md), [Données](docs/DATA_FOUNDATION.md), [Manifeste](DATA_MANIFEST.md).

## Tests

État fonctionnel stable au commit `1fd1ce906ac25346ebc69e8a996277ff039bcb0f` : **530 tests réussis**, **168 sous-tests réussis**, **0 régression détectée**, avec validation réelle de la GUI Windows.

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
```

Les tests couvrent les capacités, le Rule Engine, les stratégies, les références, les remplacements, les marques, la GUI, les exports et les sacs réels de non-régression.

## Documentation détaillée

- [Premier lancement et dépannage](docs/FIRST_RUN.md)
- [Guide de l'optimiseur](docs/STRATEGY_OPTIMIZER.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Rule Engine et DSL](docs/RULE_ENGINE.md)
- [Commandes CLI](docs/CLI.md)
- [Données et SQLite](docs/DATA_FOUNDATION.md)
- [Stratégies](docs/STRATEGY_MODEL.md)
- [Audit détaillé des capacités](docs/CAPABILITY_AUDIT.md)
- [Limites connues](docs/KNOWN_LIMITATIONS.md)
- [Cas réels de régression](docs/REGRESSION_CASES.md)
- [Index et statut des documents](docs/DOCUMENTATION_AUDIT.md)

## Phase actuelle

Le développement fonctionnel est temporairement gelé pendant une période d'utilisation réelle. Les prochains changements devront provenir d'un problème observé par le joueur : recommandation incompréhensible, sac oublié, workflow gênant, information manquante, capacité réellement bloquante ou performance réellement gênante. Aucune roadmap spéculative n'est active.

# Architecture actuelle

Ce document décrit l'état stable du logiciel au commit fonctionnel `1fd1ce9`. Les spécifications préparatoires et anciennes roadmaps sont conservées dans [`archive/`](archive/README.md).

## Couches

```text
Capture officielle immuable
          ↓ normalisation sans interprétation
Catalogue versionné (clubs, niveaux, capacités)
          +
SQLite utilisateur (inventaire, sacs, références)
          ↓
Rule Engine + registres de conditions/mécanismes + DSL
          ↓
Évaluations de clubs, sacs et étapes de stratégie
          ↓
Recherche de compositions, contraintes et comparaison aux références
          ↓
GUI Windows, CLI, Explain, exports texte/JSON
```

### 1. Catalogue

`data/normalized/clubs_official.json` est la source versionnée utilisée par le moteur : 88 clubs, 9 marques et 162 occurrences de capacités. `data/raw/` conserve la capture d'origine. La normalisation structure les intitulés et valeurs sans déduire une règle de jeu.

### 2. SQLite utilisateur

`data/pga_shootout.sqlite` contient l'état du joueur. Les tables principales couvrent le profil, l'état de l'inventaire, les clubs, les sacs et leurs positions, les préférences, les observations, le journal de changements et les migrations. Les métadonnées extensibles restent dans les charges JSON des lignes, notamment les références et rôles utilisateur.

Le catalogue et l'état utilisateur sont séparés : modifier un niveau ou un rôle ne modifie jamais les données officielles. Une sauvegarde précède les écritures importantes.

### 3. Rule Engine

Le Rule Engine reçoit un `GameState`, évalue les conditions, puis délègue chaque effet au registre. Les programmes DSL décrivent les sélections, filtres, agrégations, calculs et contributions. Aucun nom de club n'est testé dans le moteur. Voir [RULE_ENGINE.md](RULE_ENGINE.md).

### 4. Strategy Registry

`data/strategies/strategies.json` définit les séquences de coups, fonctions attendues, rôles actifs, métriques et exigences. Les quatre stratégies sont Par 3, Par 4 court, Par 4 long et Par 5. La variante `head_crosswind` ajoute un contexte de vent contraire/latéral à Par 4 long et Par 5.

### 5. Évaluation

Une composition est évaluée dans son ordre physique. Pour chaque étape, le moteur choisit ou respecte l'affectation active, applique les capacités supportées et produit statistiques finales, contributions, effets différés, avertissements et Explain. Les états de faisabilité sont `satisfied`, `violated` ou `indeterminate`.

### 6. Recherche et optimisation

`BuildFromScratchRequest` est le contrat principal. Il représente un sac vide plus les clubs explicitement imposés et ne possède aucun champ de sac cible, référence ou graine. Le générateur construit des affectations actives et des pools de supports depuis les données du catalogue, puis compare des objectifs ordonnés sans score global.

Build From Scratch ne lit ni référence ni résultat connu. Il applique des réductions structurelles, un contrôle de domination locale à une place et rejette les places sans raison observable, sauf club obligatoire ou inconnue pertinente. Les références et résultats connus restent réservés aux anciens workflows locaux. Les recherches bornées restent annoncées comme telles.

### 7. Références utilisateur

Une référence est un sac réel accompagné de métadonnées : usage, stratégie, métriques observées, notes et rôles par club. Elle est un témoin de comparaison, pas une règle du moteur. Une référence interdite par les contraintes reste visible mais n'est pas candidate admissible.

### 8. Interfaces

La GUI Tkinter est l'interface principale. Elle relit SQLite avant chaque analyse et exécute la recherche hors du thread d'affichage. La CLI expose les mêmes couches pour diagnostic, automatisation et tests. Voir [CLI.md](CLI.md).

### 9. Exports

Les sorties texte et JSON exposent notamment composition, affectations, statistiques, contributions, capacités non résolues, référence, rôles, politique de type, profondeur, complétude, statuts, gains, pertes, inconnues, marques et raison d'affichage.

## Frontières stables

- le catalogue reste immuable pendant l'évaluation ;
- SQLite est la source de vérité utilisateur ;
- les stratégies et capacités sont pilotées par les données ;
- aucune préférence utilisateur ne modifie le Rule Engine ;
- une inconnue n'est jamais remplacée par zéro ;
- `MEILLEUR TROUVÉ` ne constitue pas une preuve d'optimalité.

# Audit fonctionnel du moteur

> État audité après le commit `05e9ffa`, à partir du catalogue officiel normalisé, du registre DSL, d'`inventory-status`, de `compare-bags` et des contrats de l'optimiseur. Ce document décrit des capacités observables ; il ne définit aucun nouveau calcul.

## 1. État actuel du moteur

Le moteur est un **évaluateur explicable de sacs**, utilisable pour comparer des mesures objectives dans un scénario de niveau et de position explicitement choisi. Il n'est pas encore un système autonome de recommandation ou de classement.

| Couche | État observable | Conclusion fonctionnelle |
|---|---|---|
| Données officielles | 88 clubs, statistiques par niveau et 162 occurrences de capacités normalisées | Base catalogue exploitable |
| Inventaire utilisateur | 20 clubs connus, inventaire explicitement incomplet, 0 niveau courant renseigné | Insuffisant pour une recommandation personnalisée réelle |
| Couverture de l'inventaire | 28 capacités sur 35, soit 80 % ; 14 clubs sur 20 entièrement simulés | Bonne couverture du comparateur statique |
| Couverture globale | 55 occurrences sur 162, 33 groupes sur 125, 37 clubs touchés sur 88 | Le moteur n'est pas encore général sur tout le catalogue |
| Évaluation | Modes strict et partial, statistiques finales, modificateurs, contributions et effets différés | Opérationnelle sur les règles qualifiées |
| Explain | Conditions, entrées, sorties, valeurs avant/après et éléments non résolus | Traçabilité suffisante pour auditer un résultat |
| Comparaison | Deux sacs sauvegardés, une position courante, différences par métrique, bonus gagnés/perdus et diagnostic factuel | Aide à la décision, sans désignation d'un vainqueur |
| Recommandation | Contrat d'évaluation de candidats disponible | Recherche, agrégation, normalisation, contraintes et classement incomplets ou absents |

La comparaison actuelle porte séparément sur Power, Control, Spin, angle de lancement, réduction de rebond, multiplicateur fade/draw, résistance au vent et nombres maximaux de rebonds sur sable ou eau. Les unités restent séparées : le moteur ne transforme pas, par exemple, 75 % de résistance au vent et 5 points de Power en une valeur commune.

Les deux sacs de référence restent des cas de non-régression, mais ne sont pas intégralement couverts : `par3_divebomb` est à 6/8 capacités (75 %) et `par3_high_flight` à 8/9 (88,89 %).

## 2. Capacités couvertes

### Occurrences possédées prises en compte

| Pattern ou mesure | Clubs de l'inventaire | Occurrences |
|---|---|---:|
| Brand Loyalty, bonus de Power par voisin de même marque | Homestead, Commonlaw, Kinship, Groundskeep, Sandsend, Steadfast, Cloudcatcher, Rook, Lodestar, Into the Breach, Conqueror | 11 |
| Chains, effet différé filtré par marque ou type | Kinship, Outset, Conqueror | 3 |
| Bonus de sac par rareté | Steadfast | 1 |
| Bonus de Control aux autres clubs | Commonlaw | 1 |
| Bonus au club de gauche : Power, Spin ou réduction de rebond | Jumpstart, Cyclotron | 3 |
| Angle de lancement, individuel ou portant sur le sac | High Flight, Cloudcatcher | 2 |
| Résistance au vent, individuelle ou portant sur le sac | High Flight, Rook | 2 |
| Réduction de rebond individuelle ou portant sur le sac | Cyclotron, Cloudcatcher | 2 |
| Rebonds sur sable et sur eau | Mirage | 2 |
| Multiplicateur Fade/Draw | Lodestar | 1 |
| Bag Recklessness, bonus Power/Spin et malus Control | Into the Breach | 1 |
| **Total** |  | **28** |

Ces effets sont pilotés par les données et le DSL. Les contributions restent attribuées à leur capacité source. Les capacités Chains peuvent planifier un effet, le conserver face à un club incompatible, l'appliquer au prochain club compatible puis le consommer.

### Clubs entièrement simulés par la couverture du moteur

Les 14 clubs possédés dont toutes les capacités officielles sont reconnues sont :

- Homestead ;
- Commonlaw ;
- Kinship ;
- Sandsend ;
- Steadfast ;
- Jumpstart ;
- Cyclotron ;
- High Flight ;
- Cloudcatcher ;
- Rook ;
- Mirage ;
- Lodestar ;
- Into the Breach ;
- Conqueror.

« Entièrement simulé » signifie ici que toutes les capacités du club disposent d'une représentation moteur. Cela ne signifie pas encore « comparable avec les valeurs réelles de Pierre » : les niveaux courants des 20 clubs sont inconnus.

## 3. Capacités manquantes

Les estimations ci-dessous évaluent leur effet sur le produit actuel. Aucune interprétation supplémentaire des textes officiels n'est introduite.

| Priorité produit | Club — capacité | État et difficulté | Physique avancée | Valeur pour le comparateur | Impact probable sur les recommandations |
|---:|---|---|---|---|---|
| 1 | Groundskeep — Fairway Affinity | `scenario_required` ; moyenne à élevée : terrain catégoriel, Tee Box à Elite et condition d'application | Non, si le bonus officiel est préalablement qualifié | Élevée dans un comparateur avec scénario tee/fairway ; nulle dans une comparaison strictement sans scénario | Élevé pour départager les sacs utilisant Groundskeep dans les contextes concernés ; complète ce club |
| 2 | Color Theory — Terrain Bonus | `scenario_required` ; moyenne à élevée : catégories Rough/Water/Tree/Sand et sens exact de chaque bonus à valider | Pas nécessairement ; le comportement des bonus doit néanmoins être qualifié | Élevée dans les scénarios de terrain, faible pour un classement statique général | Élevé pour Color Theory et réutilisable pour d'autres capacités de terrain, mais seulement si le scénario est connu |
| 3 | Color Theory — Perfect Shot / Terrain Bonus Boost | `history_required` ; élevée : coup précédent, condition Perfect et composition avec Terrain Bonus | Non pour la condition ; dépend du contrat validé de Terrain Bonus | Moyenne après Terrain Bonus, nulle avant | Moyen : complète Color Theory et affine une séquence précise, sans améliorer la majorité des comparaisons statiques |
| 4 | Outset — Tree Bonus | `ambiguous` ; élevée : nombre d'arbres à 25 pieds et formule « up to » inconnue | Non, mais géométrie/proximité et validation en jeu nécessaires | Moyenne dans un scénario arboré, nulle sans donnée de proximité | Moyen et très situationnel ; pourrait modifier Outset fortement, mais aucune recommandation fiable n'est possible avant mesure |
| 5 | Neon Impulse — Power Shot | `physics_required` ; très élevée : gain de portée et pénalité de timing non quantifiés | Oui | Faible dans le comparateur objectif actuel, car aucune métrique physique validée n'existe | Potentiellement élevé pour un objectif distance, mais impossible à chiffrer loyalement aujourd'hui |
| 6 | Green Demon — Emerald Rush 75% | `physics_required` ; très élevée : vitesse/distance au-dessus du fairway et ralentissement au-dessus du green | Oui, avec position et trajectoire | Faible dans le comparateur statique | Potentiellement élevé dans des trous adaptés, mais très dépendant du parcours et du coup |
| 7 | Skyfury — Boundary Rush 75% | `physics_required` ; très élevée : état au-dessus de l'eau/hors limites, vitesse et distance | Oui, avec position et trajectoire | Faible dans le comparateur statique | Situationnel et risqué ; peut être reporté sans dégrader sensiblement les recommandations statiques |

Les trois capacités de trajectoire peuvent être volontairement reportées : elles ne peuvent pas être converties honnêtement en Power, distance ou score sans mesures en jeu et sans moteur physique. Tree Bonus peut également être reporté tant que sa formule reste ambiguë. Leur absence doit cependant rester visible dans le diagnostic lorsqu'un sac contient le club concerné.

## 4. Cas d'usage déjà réalisables

| Question | Réponse actuelle du produit | Fiabilité et conditions |
|---|---|---|
| Comparer deux sacs proposés | Oui, métrique par métrique et pour une position sélectionnée | Fiable pour les capacités supportées, avec niveaux explicites ; le mode partial signale les omissions |
| Expliquer pourquoi deux sacs diffèrent | Oui | Contributions attribuées, bonus gagnés/perdus, effets planifiés et valeurs avant/après disponibles |
| Vérifier l'effet de l'ordre des clubs | Oui, manuellement en évaluant des compositions ordonnées | Fiable pour l'adjacence, les sélections positionnelles et les patterns de sac couverts |
| Évaluer un candidat construit par un autre outil | Oui via `RuleEngineBagEvaluator` | Tous les clubs et niveaux doivent être fournis ; une position courante doit être choisie |
| Identifier les clubs à comparaison incomplète | Oui via `inventory-status` et le diagnostic de comparaison | Classification factuelle par capacité et données nécessaires |
| Comparer des modificateurs non homogènes | Oui, séparément | Aucun ordre de préférence entre unités n'est inventé |

Le moteur peut donc soutenir une décision humaine : il peut montrer qu'un sac gagne du Control, perd du Power, ajoute de la résistance au vent et contient une capacité non résolue. Il ne doit pas transformer seul ces faits en verdict global.

## 5. Cas d'usage encore impossibles

### « Quel est le meilleur sac parmi plusieurs sacs proposés ? »

Pas de réponse automatique fiable. Le produit ne dispose ni d'agrégation sur les cinq positions, ni de normalisation entre unités, ni de pondérations validées, ni d'algorithme de classement. `compare-bags` ne compare que deux sacs à la fois et une position courante à la fois.

### « Quel club améliore le plus un sac existant ? »

Le moteur peut évaluer manuellement un remplacement donné, mais il ne génère pas les candidats de l'inventaire et ne parcourt pas toutes les positions. Il peut exposer les deltas objectifs, pas choisir automatiquement « le plus » sans objectif utilisateur explicite.

### « Quel remplacement apporte le plus de valeur ? »

Impossible actuellement. La notion de valeur n'est pas définie : Power, Control, Spin, comportement du rebond et résistance au vent ne sont ni normalisés ni pondérés. Les préférences utilisateur existent sous forme descriptive, avec des poids `null`.

### « Quels clubs sont actuellement impossibles à comparer correctement ? »

Par couverture de capacités, les clubs incomplets sont Groundskeep, Neon Impulse, Color Theory, Skyfury, Green Demon et Outset. En conditions réelles, les 20 clubs connus nécessitent encore leur niveau courant ; avant cette saisie, toute valeur par niveau est un scénario hypothétique. L'inventaire étant déclaré incomplet, le moteur ne peut pas garantir que le meilleur candidat possédé figure dans les données.

### Résultats nécessitant obligatoirement un avertissement

Un résultat doit être accompagné du diagnostic lorsque l'une des conditions suivantes est vraie :

- au moins une capacité est non simulée, ambiguë ou dépendante d'un scénario absent ;
- un niveau réel utilisateur est inconnu ou remplacé par un niveau hypothétique commun ;
- le sac contient un effet Chains planifié qui n'est pas résolu dans l'évaluation du coup courant ;
- des métriques d'unités différentes sont présentées sans politique de valeur ;
- la comparaison est utilisée comme verdict global alors qu'elle ne couvre qu'une position ;
- le candidat dépend de Power Shot, Boundary Rush, Emerald Rush ou Tree Bonus ;
- le mode partial a ignoré un élément indispensable ;
- l'inventaire incomplet est utilisé pour prétendre à une recommandation exhaustive.

## 6. Analyse des risques

| Risque | Conséquence utilisateur | Mesure de maîtrise actuelle |
|---|---|---|
| Niveaux courants inconnus | Statistiques et valeurs de capacités différentes de celles réellement disponibles | Le diagnostic liste chaque niveau inconnu ; le moteur accepte des scénarios explicites |
| Inventaire incomplet | Omission possible du meilleur candidat possédé | `inventory_complete: false` est conservé dans les données |
| Couverture partielle | Sous-évaluation d'un sac contenant une capacité non simulée | Modes strict/partial, éléments non résolus et `inventory-status` |
| Une seule position évaluée | Un « meilleur sac » apparent peut être moins bon sur les autres clubs | La position est affichée ; aucune agrégation globale n'est prétendue |
| Unités non normalisées | Addition arbitraire de mesures incompatibles | Chaque métrique et unité reste séparée ; aucun score global |
| Préférences non quantifiées | Impossible de traduire « précision » ou « sécurité » en classement reproductible | Contrat de pondération séparé, sans fournisseur validé |
| Effets de scénario et physiques | Résultats très dépendants du trou ou du coup | Capacités classées `scenario_required`, `history_required`, `physics_required` ou `ambiguous` |
| Politique minimale des Chains | La fidélité au jeu dépend encore de la validation exacte de l'expiration sur les coups incompatibles | Cycle planification/déclenchement/consommation visible dans Explain |

## 7. Feuille de route priorisée

### Priorité 0 — rendre les données utilisateur recommandables

Renseigner les niveaux réels des 20 clubs et compléter l'inventaire avant de présenter une recommandation personnalisée. Ce travail apporte plus de fidélité immédiate que toute nouvelle capacité isolée : les 28 capacités déjà supportées utilisent des valeurs par niveau qui sont actuellement inconnues.

### Priorité 1 — produire une recommandation transparente à partir du moteur existant

Construire, hors du Rule Engine :

1. la génération des remplacements autorisés par l'inventaire ;
2. l'évaluation systématique des cinq positions ;
3. une agrégation qui conserve les métriques séparées ;
4. un classement Pareto ou des profils de pondération explicitement configurés et validés ;
5. le rejet ou l'étiquetage automatique des candidats incomplets.

Ce lot débloque directement les questions « quel remplacement ? » et « quel sac parmi ces candidats ? » sans exiger 100 % du catalogue. Il doit conserver les contributions et avertissements existants.

### Priorité 2 — prochain lot de capacités : contexte de terrain minimal

Le prochain lot recommandé est **Fairway Affinity + Terrain Bonus**, uniquement après qualification exacte des textes officiels. Il introduit un contexte catégoriel réutilisable (`tee`, `fairway`, `rough`, `water`, `tree`, `sand`) sans géométrie ni physique complète, couvre deux occurrences possédées et rend Groundskeep entièrement simulé. Il prépare aussi la future composition de Perfect Shot avec Terrain Bonus.

Ce lot améliore les recommandations par scénario, mais pas un classement statique universel. Le contexte doit donc rester optionnel, absent par défaut et bloquant en strict seulement lorsque la capacité l'exige.

### Priorité 3 — historique minimal après le terrain

Qualifier puis implémenter Perfect Shot / Terrain Bonus Boost à partir d'un résultat catégoriel du coup précédent. Cette capacité ne doit pas précéder Terrain Bonus, dont elle modifie la valeur.

### Priorité 4 — campagnes expérimentales ciblées

Mesurer séparément Tree Bonus, puis Power Shot, Emerald Rush et Boundary Rush. Aucune implémentation ne doit commencer sans formule ou observation suffisante. Tree Bonus est prioritaire parmi ces validations parce qu'il n'exige pas de trajectoire complète et permettrait de compléter Outset.

### Capacités reportables

- Boundary Rush et Emerald Rush : report sans perte significative pour le comparateur statique ;
- Power Shot : report acceptable tant qu'aucune recommandation de distance physique n'est annoncée ;
- Tree Bonus : report obligatoire jusqu'à validation de la formule ;
- Perfect Shot / Terrain Bonus Boost : report logique jusqu'à disponibilité du contrat Terrain Bonus.

## Décision de maturité

Le moteur est **prêt comme comparateur explicable de métriques objectives**, sous réserve d'un niveau explicite et d'un diagnostic sans lacune bloquante. Il est **partiellement prêt comme assistant de recommandation** : il fournit les évaluations et les explications nécessaires, mais ne sait pas encore rechercher, agréger ou classer les solutions. Il n'est pas prêt à annoncer automatiquement « le meilleur sac » ou « le meilleur remplacement ».

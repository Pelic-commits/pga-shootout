# Modèle conceptuel des stratégies de jeu

> Contrat d'architecture uniquement. Ce document ne définit ni algorithme de recherche, ni score global, ni profil de parcours codé en dur. Le Rule Engine et le DSL restent inchangés.

## 1. Principe directeur

Une stratégie ne cherche pas à maximiser une statistique isolée. Elle décrit une **suite ordonnée de transitions de jeu souhaitées**. Chaque transition correspond à un coup ayant une fonction, un état de départ et un résultat attendu.

Les métriques objectives produites par le moteur servent ensuite à :

- vérifier les conditions mesurables de chaque coup ;
- comparer plusieurs façons de remplir la même fonction ;
- exposer les compromis lorsque plusieurs candidats restent admissibles ;
- signaler les conditions impossibles à vérifier avec les données actuelles.

Le nombre de coups, leurs fonctions et leur contexte sont des données de la stratégie. Aucun nom tel que `Par 3`, `Par 4`, `Long Drive` ou `Vent` ne déclenche de logique particulière.

## 2. Modèle abstrait commun

```text
StrategyDefinition
└── ShotSequence
    ├── ShotStep 1
    │   ├── ShotFunction
    │   ├── StepContext
    │   ├── OutcomeRequirement(s)
    │   └── LocalObjective(s)
    ├── ShotStep 2
    └── ...

BagCandidate + StrategyDefinition
└── StrategyAssignment
    ├── Active assignment(s) par coup
    ├── Support-only club(s)
    └── Hybrid club(s)

StrategyAssignment + évaluations du moteur
└── StrategyEvaluation
    ├── StepEvaluation(s)
    ├── AbilityContribution(s)
    ├── UnresolvedRequirement(s)
    └── Feasibility: satisfied | violated | indeterminate
```

Une stratégie est donc indépendante du sac. Une affectation relie ensuite un sac concret aux fonctions demandées. L'évaluation mesure cette affectation sans modifier la stratégie ni le résultat du Rule Engine.

## 3. Concepts métier

### 3.1 StrategyDefinition

Décrit l'intention complète et versionnée du joueur.

Informations nécessaires :

- identifiant stable et version du contrat ;
- provenance de la demande ;
- séquence de coups ;
- contraintes portant sur le sac ou les affectations ;
- politique de comparaison explicite, par exemple contraintes puis front de Pareto ;
- politique d'incertitude, notamment le traitement des exigences indéterminables.

Un libellé humain peut mentionner un type de trou, mais ce libellé n'a aucune sémantique moteur. Seuls les éléments structurés de la séquence en ont une.

### 3.2 ShotSequence

Suite ordonnée de `ShotStep`. L'ordre porte une sémantique réelle : le résultat attendu d'un coup fournit l'état de départ logique du suivant.

Informations nécessaires :

- étapes obligatoires, dans l'ordre ;
- état initial connu ou requis ;
- résultat terminal attendu ;
- cohérence attendue entre la sortie d'une étape et l'entrée de la suivante.

La première version peut rester linéaire. Des branches de récupération pourront être ajoutées ultérieurement sans changer le sens d'une séquence simple, mais elles ne sont pas nécessaires aux stratégies observées.

### 3.3 ShotStep

Un coup planifié, identifié par sa position dans la séquence et non par un type de trou.

Informations nécessaires :

- identifiant stable dans la stratégie ;
- fonction attendue ;
- contexte catégoriel ou mesuré connu avant le coup ;
- exigences de résultat ;
- objectifs locaux permettant de départager les affectations admissibles ;
- données indispensables à l'évaluation ;
- relation avec l'étape précédente et la suivante.

### 3.4 ShotFunction

Décrit **ce que le coup doit accomplir**, sans imposer un club ni traduire implicitement cette fonction en Power, Control ou Spin.

Exemples de fonctions génériques :

- `reach_target_zone` : terminer dans une zone cible ;
- `advance_toward_target` : produire une progression répondant à un seuil explicite ;
- `prepare_next_step` : obtenir un état de départ acceptable pour l'étape suivante ;
- `finish` : terminer le trou depuis l'état courant.

Une fonction contient :

- l'état ou la zone de départ ;
- le résultat ou la transition attendue ;
- les paramètres observables éventuels ;
- les données requises pour vérifier le résultat ;
- son statut de calculabilité avec le moteur actuel.

`reach_target_zone(green)` ne signifie jamais automatiquement `maximize(power)`. Tant qu'un modèle validé ne relie pas les données disponibles à l'atteinte du green, cette exigence reste `indeterminate`.

### 3.5 StepContext

Ensemble minimal de faits connus pour un coup. Il réutilise le principe de contexte facultatif de `GameState`.

Deux catégories doivent rester séparées :

- données permanentes : inventaire, niveaux, composition, ordre, identité et caractéristiques officielles des clubs ;
- contexte de l'étape : terrain de départ, distance cible si connue et validée, vent, numéro du coup, résultat précédent ou autre donnée explicitement justifiée.

Une donnée absente n'est jamais remplacée par zéro ou par une situation neutre. Elle rend seulement les exigences qui en dépendent indéterminables.

### 3.6 OutcomeRequirement

Prédicat factuel qu'une affectation doit satisfaire pour que le coup remplisse sa fonction.

Informations nécessaires :

- sujet observé, par exemple zone finale ou portée réelle ;
- opérateur ;
- valeur attendue ;
- unité ou vocabulaire catégoriel ;
- provenance ;
- données nécessaires ;
- caractère obligatoire ou simplement informatif.

Une exigence produit l'un des trois états suivants :

- `satisfied` : les données validées démontrent qu'elle est satisfaite ;
- `violated` : les données validées démontrent qu'elle ne l'est pas ;
- `indeterminate` : une donnée ou une mécanique indispensable manque.

Cette logique ternaire empêche de transformer une capacité inconnue ou une physique absente en valeur nulle.

### 3.7 LocalObjective

Critère de comparaison attaché à une étape précise et appliqué seulement après les exigences obligatoires.

Il réutilise les opérations neutres du contrat d'optimisation existant : ordre lexicographique, comparaison d'une métrique ou conservation d'un front de Pareto. Les métriques restent séparées et conservent leur unité.

Exemple : parmi les clubs démontrés capables de remplir une approche, conserver les compromis de Control et Spin. Cette formulation n'affirme pas qu'un point de Control vaut un point de Spin.

Un objectif peut aussi rester non évaluable si la métrique nécessaire n'est pas disponible. Il ne reçoit jamais de substitut arbitraire.

### 3.8 ClubRoleRequirement

Contraintes applicables au club qui remplira une fonction :

- club possédé et niveau connu ;
- éventuellement type, marque, rareté ou identité si l'utilisateur l'exige explicitement ;
- capacité à être évalué dans le contexte de l'étape ;
- possibilité ou interdiction de réutiliser le même club sur plusieurs étapes.

Le modèle ne suppose pas qu'une approche utilise forcément un Wedge ou qu'un départ utilise forcément un Driver. Une contrainte de type n'existe que si elle est déclarée. Un Iron peut donc naturellement concurrencer un Wedge pour la même fonction.

### 3.9 StrategyAssignment

Affectation concrète des clubs d'un sac aux étapes de la stratégie.

Elle contient :

- le sac ordonné et les niveaux ;
- le club actif choisi pour chaque étape ;
- les clubs non utilisés directement ;
- les contributions de chaque capacité vers chaque étape ;
- les effets différés reliant éventuellement deux étapes ;
- la classification de rôle dérivée pour chaque club.

L'affectation, et non la définition de stratégie, porte les identités des clubs.

## 4. Club actif et club support

Ces deux notions sont pertinentes à condition de les définir comme des **rôles relatifs à une affectation**.

### Club actif

Un club est actif s'il est explicitement utilisé pour exécuter au moins un `ShotStep`. Ses statistiques finales et les contributions qui le ciblent participent à l'évaluation de cette étape.

### Club support

Un club est support pour une étape lorsqu'il n'exécute pas cette étape mais que sa présence, sa position ou sa capacité produit une contribution pertinente pour son club actif, prépare un effet différé utile, ou satisfait une contrainte structurelle nécessaire.

La simple présence inutilisée dans le sac ne suffit pas à prouver un rôle support : il faut une contribution ou une dépendance attribuable.

### Rôle hybride

Un club est hybride lorsqu'il est actif sur au moins une étape et support d'au moins une autre étape, ou lorsqu'il soutient aussi sa propre utilisation par une capacité de sac attribuable.

### Règles importantes

- le rôle n'est jamais une propriété du catalogue ;
- un club peut changer de rôle entre deux stratégies ;
- un club support n'est pas automatiquement moins important qu'un club actif ;
- la valeur d'un support n'est pas un score propre : elle est exposée par ses contributions et par les exigences qu'elles aident à satisfaire ;
- retirer un support peut rendre une étape moins bonne, indéterminable ou inadmissible, ce que l'analyse contrefactuelle du futur optimiseur devra expliquer.

## 5. Évaluation d'une stratégie

### StepEvaluation

Pour chaque étape et chaque affectation candidate :

- club actif ;
- contexte réellement fourni ;
- statistiques de base et finales ;
- modificateurs objectifs ;
- contributions reçues, avec leur club source ;
- effets différés créés, consommés ou encore planifiés ;
- exigences satisfaites, violées ou indéterminables ;
- objectifs locaux effectivement comparables ;
- avertissements et références Explain.

### StrategyEvaluation

Agrège les états des étapes sans additionner leurs métriques.

Statut global :

- `satisfied` si toutes les étapes obligatoires sont satisfaites ;
- `violated` si au moins une étape obligatoire est démontrée impossible ;
- `indeterminate` si aucune étape n'est violée mais qu'au moins une exigence obligatoire ne peut pas être vérifiée.

Le résultat conserve la matrice `étape × métrique`, les compromis, les contributions et les incertitudes. Il ne produit aucun total Power/Control/Spin et aucun score synthétique.

## 6. Relation avec l'architecture existante

Le modèle de stratégie se place au-dessus de `OptimizationRequest` :

```text
StrategyDefinition
→ traduction en contraintes, objectifs locaux et scénarios ordonnés
→ OptimizationRequest
→ futur CandidateGenerator
→ BagEvaluator / Rule Engine existants
→ StepEvaluation
→ StrategyEvaluation
```

Évolutions conceptuelles nécessaires au contrat d'optimisation :

- remplacer la simple collection non ordonnée de scénarios par des étapes ordonnées identifiables ;
- permettre aux contraintes et objectifs de cibler une étape ;
- conserver l'affectation `step_id → active_club_id` ;
- conserver les contributions inter-étapes, notamment Chains ;
- distinguer faisabilité, comparaison locale et incertitude.

Ces évolutions appartiennent à la future couche d'optimisation. Elles ne nécessitent aucune modification du Rule Engine, du DSL ou des définitions de capacités.

## 7. Validation sur les quatre stratégies observées

| Séquence observée | Étapes génériques | Ce qui varie réellement |
|---|---|---|
| Deux coups avec attaque immédiate | `reach_target_zone(green)` → `finish(from=green)` | contexte initial, distance cible, contraintes et objectifs locaux |
| Trois coups avec approche | `advance_toward_target` → `reach_target_zone(green)` → `finish(from=green)` | contexte de chaque étape et seuils de transition |
| Deux coups avec attaque agressive | `reach_target_zone(green)` → `finish(from=green)` | exigences plus difficiles ou contexte différent, pas un autre pipeline |
| Trois coups avec longue approche | `advance_toward_target` → `reach_target_zone(green)` → `finish(from=green)` | portée requise pour l'approche et compromis locaux |

Les première et troisième stratégies partagent exactement la même structure. Les deuxième et quatrième aussi. Ce ne sont pas des profils distincts : seules les données des étapes diffèrent.

Le choix Iron contre Wedge est représenté par deux affectations candidates au même `ShotStep`. Si les deux satisfont l'exigence d'atteindre le green, leurs métriques et compromis locaux peuvent être comparés. Si la portée réelle n'est pas calculable, le moteur doit déclarer cette exigence indéterminable plutôt que choisir le club ayant le plus de Power.

## 8. Informations encore nécessaires avant l'optimiseur

Le contrat peut être défini dès maintenant, mais certaines stratégies ne sont pas encore entièrement calculables.

| Information | Usage | État actuel |
|---|---|---|
| inventaire, niveaux, sac et ordre | génération et évaluation des affectations | disponible, avec trois niveaux utilisateur inconnus |
| statistiques et contributions par capacité | comparaison locale des clubs actifs et supports | disponible pour les capacités couvertes |
| contexte catégoriel simple | conditions tee, fairway, rough, sand ou green | partiellement disponible |
| modèle validé de portée réelle | démontrer qu'un coup atteint une zone cible | manquant |
| distance ou exigence cible explicite | paramétrer `reach_target_zone` | à fournir par la stratégie ou une future source de parcours |
| modèle du putt ou critère validé de finition | démontrer le résultat `finish` | manquant |
| qualification des capacités non résolues | décider l'admissibilité sans faux zéro | suivie par `inventory-status` |
| contrat complet des effets inter-étapes | évaluer toutes les chaînes et capacités historiques | Chains simple disponible ; autres historiques reportés |

La conséquence est volontaire : le futur optimiseur pourra d'abord comparer les faits disponibles et identifier les affectations indéterminables, mais il ne devra pas prétendre garantir une séquence tant que ses exigences physiques ne sont pas vérifiables.

## 9. Frontière de la première implémentation future

La première implémentation pourra se limiter à :

- séquences linéaires ;
- une affectation active par étape ;
- rôles support et hybride dérivés des contributions ;
- contraintes ternaires ;
- objectifs locaux lexicographiques ou Pareto ;
- contexte facultatif explicite ;
- sortie détaillant faisabilité, compromis et incertitudes.

Sont différés : branches de récupération, probabilités de réussite, physique complète, base de parcours, apprentissage automatique, profils nommés et score global.

## 10. Registre et préréglages utilisateur

Le registre pratique est un catalogue JSON versionné, chargé par `StrategyRegistry`. Il contient des définitions et des variantes, sans branche conditionnelle liée à leurs identifiants.

Trois provenances sont prévues par le même champ `origin` :

- `bundled` pour la bibliothèque fournie avec le logiciel ;
- `user` pour une future stratégie personnalisée ;
- `generated` pour une future proposition automatique.

Le chargeur peut fusionner plusieurs catalogues respectant le même contrat. Les doublons, références inconnues, rôles incohérents et nombres de supports impossibles sont rejetés explicitement.

La première bibliothèque contient quatre préréglages :

- `par3` et `par4_short` utilisent `reach_target_zone → finish` ;
- `par4_long` et `par5` utilisent `advance_toward_target → reach_target_zone → finish` ;
- `par5` ajoute une exigence de longue approche, mais aucun type de club ;
- faute de distance demandée dans le mode actuel, `par3` et `par4_short` sont volontairement équivalents pour le calcul. Leur différence reste un libellé utilisateur jusqu'à ce qu'un futur contexte validé les distingue.

### Variantes

Une variante n'embarque aucune copie de `StrategyDefinition` ou de `ShotSequence`. Elle déclare seulement des patches ciblés par `step_id` :

- valeurs de contexte ajoutées ou remplacées ;
- données contextuelles requises ;
- exigences ajoutées ;
- objectifs locaux ajoutés.

La variante initiale `head_crosswind` s'applique à `par4_long` et `par5`. Elle ajoute le contexte catégoriel de vent et expose séparément la résistance au vent. Elle ne simule ni direction, ni trajectoire, ni portée.

### Consultation

```text
pga-shootout strategy-list
pga-shootout strategy-show par4_long
pga-shootout strategy-show par4_long --variant head_crosswind
pga-shootout strategy-show par3 --json
```

La consultation affiche la séquence, les rôles actifs, le nombre de supports disponibles, les variantes compatibles et toutes les données encore nécessaires à une évaluation complète.

## 11. Compatibilité contractuelle

| Composant | Relation avec le modèle de stratégie |
|---|---|
| `OptimizationRequest` | Chaque étape devient un scénario ordonné ; ses exigences deviennent des contraintes ciblées et ses objectifs restent locaux à cette étape. |
| Recommendation Engine | Continue à générer et comparer des sacs ; une future orchestration lui fournira les affectations actives et les étapes à évaluer. |
| Rule Engine | Inchangé ; il évalue toujours un club courant, un sac et un contexte explicite. |
| DSL | Inchangé ; aucune opération ne dépend d'un identifiant de stratégie. |
| Chains | L'ordre des étapes et l'identité du club actif sont conservés afin qu'un effet planifié puisse ultérieurement être transmis à l'étape suivante. Aucune nouvelle règle de consommation n'est inventée. |
| Incertitude | Les données exigées sont réunies par étape. Une exigence physique non calculable reste indéterminable et n'est jamais remplacée par zéro. |
| Explain | Les contributions existantes restent la preuve permettant de qualifier un club de support ou hybride et, plus tard, d'expliquer sa suppression. |

Cette couche compile les préréglages vers le contrat neutre existant. Elle ne construit pas encore de candidats, n'affecte pas les clubs aux rôles et ne décide pas quel sac est meilleur.

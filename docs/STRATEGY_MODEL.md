# Modèle de stratégies actuel

## Principe

Une stratégie est une séquence déclarative de fonctions de coups. Aucun identifiant `par3`, `par4` ou `par5` ne déclenche une branche métier dans le moteur.

```text
StrategyDefinition
└── ShotSequence
    ├── ShotStep
    │   ├── ShotFunction
    │   ├── contexte catégoriel optionnel
    │   ├── métriques utilisées
    │   └── exigences de résultat
    └── ...

BagCandidate + StrategyDefinition
└── StrategyAssignment
    ├── club actif par étape
    ├── clubs support
    └── clubs hybrides actif/support
```

## Concepts

- **StrategyDefinition** : identifiant, libellé, version, taille du sac, politique d'incertitude, séquence, rôles et familles de résultats.
- **ShotStep** : fonction attendue, rôle actif, contraintes de club, contexte, métriques, exigences et objectifs locaux.
- **ShotFunction** : progression, atteinte d'une zone cible ou finition.
- **StrategyAssignment** : affectation des clubs actifs et supports pour une composition donnée.
- **StepEvaluation** : statistiques et contributions calculées pour une étape.
- **StrategyEvaluation** : agrégation explicite des étapes, faisabilité, inconnues et Explain.

Un club actif est utilisé pour la fonction d'une étape. Un club support est présent pour ses synergies et n'occupe pas cette étape. Un même club peut être actif à une étape et supporter une autre.

## Stratégies versionnées

| Identifiant | Libellé | Séquence |
|---|---|---|
| `par3` | Sac Par 3 | Atteindre le green → Terminer depuis le green |
| `par4_short` | Sac Par 4 court | Attaque directe du green → Terminer depuis le green |
| `par4_long` | Sac Par 4 long | Départ → Approche vers le green → Putt |
| `par5` | Sac Par 5 | Long départ → Longue approche vers le green → Putt |

Par 3 et Par 4 court ont actuellement la même forme calculable à deux étapes. Par 4 long et Par 5 ont la même forme à trois étapes. Les libellés et exigences conceptuelles diffèrent, mais l'absence de modèle de distance peut produire des résultats identiques. Ce n'est pas une règle physique du jeu.

La variante `head_crosswind`, compatible avec Par 4 long et Par 5, ajoute un contexte de vent contraire/latéral et expose Wind Resistance séparément.

## Métriques et faisabilité

Les usages de métriques sont `objective`, `context_dependent` ou `descriptive`. Les exigences peuvent être :

- `satisfied` : vérifiables et respectées ;
- `violated` : vérifiables et non respectées ;
- `indeterminate` : donnée ou modèle manquant.

Une exigence de portée reste indéterminée sans modèle de carry et distance cible. L'optimiseur compare alors les faits disponibles sans prétendre garantir le coup.

## Rôles utilisateur

Les références peuvent remplacer l'affectation automatique du sac actuel par un rôle observé : étape, Support ou Variable. Cette donnée est locale au sac et sert à comparer fonction à fonction. Les candidats générés gardent leur propre affectation calculée.

## Séparation des responsabilités

- le registre définit la stratégie ;
- le Rule Engine calcule les capacités ;
- l'évaluateur applique une affectation à chaque étape ;
- la recherche génère et filtre des compositions ;
- la GUI recueille les préférences et restitue les résultats.

Voir [ARCHITECTURE.md](ARCHITECTURE.md) et [STRATEGY_OPTIMIZER.md](STRATEGY_OPTIMIZER.md).

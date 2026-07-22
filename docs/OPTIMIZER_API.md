# Optimizer API

L'optimiseur futur doit dépendre de `BagEvaluator`, pas du CLI ni des sacs sauvegardés. `RuleEngineBagEvaluator` adapte aujourd'hui ce contrat au Rule Engine sans effectuer de recherche, de classement ou de recommandation.

## Contrat

- `BagCandidate` décrit un identifiant, un ordre de clubs et le niveau réel de chaque club.
- `BagEvaluationRequest` choisit une position courante et le mode `strict` ou `partial`.
- `BagEvaluator.evaluate()` retourne un `ComparedBag` contenant l'évaluation complète.
- `ComparedBag` expose les statistiques de base et finales via `evaluation.result`, les modificateurs statiques, l'impact total des capacités, l'Explain, les éléments non résolus et une contribution structurée pour chaque capacité.
- `BagComparison` expose les différences finales, les différences d'impact des capacités et les statistiques ou modificateurs gagnés/perdus sous forme de mappings numériques.

## Préparation

L'API est prête à **80 % (8 critères sur 10)**.

| Capacité requise | État |
|---|---|
| Évaluer une composition générée non sauvegardée | prête |
| Préserver l'ordre du sac | prête |
| Utiliser un niveau propre à chaque club | prête |
| Choisir le club ou la position évaluée | prête |
| Lire statistiques de base, finales et impact total | prête |
| Lire les contributions par capacité | prête |
| Lire Explain, statut complet et bonus non résolus | prête |
| Lire les bonus gagnés et perdus d'une comparaison | prête |
| Construire l'espace de recherche depuis un inventaire complet et ses niveaux | bloquée par les données utilisateur |
| Classer les résultats avec un objectif et une politique d'agrégation validés | bloquée par les préférences produit |

Avant de calculer automatiquement le meilleur sac, il reste également à augmenter la couverture des capacités Phase 1. Le mode `partial` permet d'explorer avant 100 %, mais tout résultat devra alors conserver son niveau d'incomplétude.

La future valeur utilisateur consommera le contrat neutre décrit dans `VALUE_WEIGHTING_API.md`. Elle ne fait pas partie du Rule Engine.

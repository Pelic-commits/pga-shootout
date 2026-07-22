# Optimizer API

Le futur optimiseur dépend de `BagEvaluator`, jamais du CLI ni des sacs sauvegardés. `RuleEngineBagEvaluator` adapte ce contrat au Rule Engine sans effectuer de recherche, de classement ou de recommandation.

## Contrat

- `BagCandidate` décrit un identifiant, un ordre de clubs et le niveau réel de chaque club.
- `BagEvaluationRequest` choisit une position courante et le mode `strict` ou `partial`.
- `BagEvaluator.evaluate()` retourne un `ComparedBag` contenant l'évaluation complète.
- `ComparedBag` expose statistiques, modificateurs statiques, Explain, éléments non résolus et contributions identifiées par capacité.
- `BagComparison` expose les différences finales et les bonus gagnés ou perdus sous forme de mesures distinctes.

## Checklist objective

Cette checklist est exposée par `optimizer_readiness_checklist()` ; aucun pourcentage subjectif n'en est déduit.

| Capacité requise | État |
|---|---|
| Métriques séparées disponibles | `ready` |
| Contributions par capacité disponibles | `ready` |
| Normalisation disponible | `missing` |
| Pondérations configurables | `partial` |
| Profils d'objectif disponibles | `partial` |
| Agrégation multi-clubs disponible | `partial` |
| Classement disponible | `missing` |
| Contraintes d'inventaire disponibles | `partial` |

Avant de calculer automatiquement le meilleur sac, il reste à compléter les politiques produit et la couverture des capacités Phase 1. Le mode `partial` permet une exploration anticipée, mais conserve explicitement chaque résultat non résolu.

La future valeur utilisateur consommera le contrat neutre décrit dans `VALUE_WEIGHTING_API.md`. Elle ne fait pas partie du Rule Engine.

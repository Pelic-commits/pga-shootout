# Contrat générique des demandes d'optimisation

Ce contrat décrit une demande ; il n'implémente ni recherche exhaustive, ni
score global, ni compréhension du langage naturel. Toutes les provenances
(interface simple, modèle déclaré, texte traduit, requête avancée ou analyse de
parcours) produisent le même `OptimizationRequest`.

## Structure

- `provenance` : canal, référence traçable et version du catalogue ;
- `scope` : sélection générique d'inventaire, taille/ordre du sac et scénarios ;
- `constraints` : prédicats obligatoires avec opérateur, valeur, provenance et
  données requises ; une donnée indispensable absente rend la demande
  indéterminable au lieu de fabriquer une valeur ;
- `objectives` : opérations génériques ordonnées (`maximize`, `minimize`,
  `maximize_minimum`, `minimize_variance`, `pareto`) sur une métrique nommée ;
- `comparison_policy` : priorités lexicographiques ou conservation d'un front de
  compromis ;
- `uncertainty_policy` : signalement et exclusion seulement lorsqu'une donnée
  manquante conditionne l'admissibilité.

Les métriques ne sont jamais additionnées entre elles. Les égalités et compromis
restent explicites. Le Rule Engine ne connaît ni le langage naturel ni ce contrat.

## Huit traductions de contrôle

| Question | Contrat | Données nécessaires | État actuel |
|---|---|---|---|
| Privilégier la puissance | objectif `maximize(power)` | stats finales | calculable sur effets résolus |
| Privilégier le contrôle | objectif `maximize(control)` | stats finales | calculable sur effets résolus |
| Atteindre une portée, puis contrôle | contrainte `real_carry >= contexte`, objectif contrôle | modèle de portée validé | impossible aujourd'hui |
| Robuste fairway/rough | deux scénarios, `maximize_minimum(control)` | effets terrain qualifiés | partiel |
| Garder les compromis Power/Control | deux objectifs Pareto de même priorité | stats finales | calculable, recherche absente |
| Conserver un club et refuser l'inconnu | contraintes `contains` et unresolved=0, objectif spin | inventaire et qualification | exprimable |
| Par 3, limiter rebond puis spin | scénario catégoriel, objectifs ordonnés | rebond objectif qualifié | partiel |
| Régularité de portée sous trois vents | scénarios vent, `minimize_variance(real_carry)` | physique et vent validés | impossible aujourd'hui |

Ces huit cas utilisent strictement les mêmes champs et le même futur algorithme
générique de contraintes puis comparaison. Aucun champ ne porte le nom d'un
exemple ou d'un « mode » produit.

## Résultat attendu du futur moteur

Le résultat devra conserver : candidats admissibles/exclus, motifs, valeurs par
métrique et scénario, provenance, données absentes, objectifs effectivement
comparés, égalités et ensemble de compromis. Il ne devra annoncer un meilleur
sac que lorsque l'ordre déclaré et les données validées le permettent.

# Contexte du projet

## Objectif

Construire d’abord un simulateur fidèle des calculs de PGA TOUR Golf Shootout, puis seulement un moteur d’optimisation.

## Source de vérité

- Statistiques officielles : <https://concretesoftware.com/pga-tour-golf-shootout-club-stats/>
- Extraction validée attendue : `data/raw/pga_club_stats_extract_v2_2026-07-21.json`
- Contenu annoncé : 88 clubs, 9 marques, tables de niveaux, capacités, descriptions, HTML et images.

## Invariants d’architecture

Flux : Data → Rule Engine → GameState → Explain Engine → EvaluationResult.

- Aucun nom de club dans la logique du moteur.
- Conditions, effets et mécanismes d’exécution sont distincts.
- Les mécanismes sont résolus par un registre extensible.
- Chaque calcul produit une trace Explain vérifiable.
- Le mode strict refuse l’inconnu ; le mode partial le consigne.

## Référence future

Sac connu : Divebomb / Jumpstart / Steadfast / Ember / Sunstorm. Il ne constitue pas encore une spécification de règles et aucune capacité associée ne doit être inventée.

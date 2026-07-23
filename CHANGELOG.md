# Changelog

## Unreleased

- Implémentation déclarative de Bounce Reduction Boost et Fade/Draw x2 comme modificateurs objectifs compatibles avec Explain, compare-bags et inventory-status.
- Ajout de l'audit opérationnel `inventory-status`, de sa sortie JSON et des rapports générés sur la couverture réelle de l'inventaire et l'état du produit.
- Ajout d'un diagnostic factuel après `compare-bags` et du pattern Plasma Arc avec sélection de la cible la plus éloignée unique et garde explicite contre les égalités.
- Ajout de la matrice automatique des capacités des sacs de référence et de la réduction de rebond de Maelstrom filtrée par type de club.
- Ajout du rapport automatique des lacunes de l'inventaire, de la réduction de rebond de Cloudcatcher comme métrique objective et d'une checklist factuelle pour l'optimiseur.

- Ajout d'une API neutre de métriques et pondération, ainsi que des rebonds sable/eau de Mirage via le pattern de modificateurs statiques.
- Ajout des modificateurs statiques génériques et des angles de lancement de High Flight et Cloudcatcher dans le comparateur et l'API optimiseur.
- Ajout du contrat d'évaluation pour un futur optimiseur, des contributions structurées par capacité et du pattern Fellowship sans nouvelle primitive.
- Ajout du pattern déclaratif de bonus multi-statistiques filtré par rareté, de `MATCH_RARITY` et de golden tests produit sur les sacs par-3 de référence.
- Implémentation déclarative du premier pipeline DSL, avec les sept primitives requises par Brand Loyalty et une trace Explain par étape.

- Ajout d'un analyseur reproductible de couverture des groupes de capacités et de leur mapping vers les handlers.
- Ajout d'un pipeline reproductible de normalisation structurelle des 162 capacités officielles, sans interprétation de gameplay.
- Ajout d'une couche utilisateur séparée pour le compte, l'inventaire partiel, les préférences, les sacs et les observations.
- Ajout des modèles, validateurs et commandes CLI de consultation utilisateur.
- Ajout de tests de résolution, de non-inférence, d'ordre des sacs et d'améliorations disponibles.
- Import immuable de la capture officielle, du catalogue normalisé et de l'audit des capacités.
- Ajout d'une validation automatisée de la provenance, de la structure et des compteurs officiels.
- Fusion du contexte durable et ajout du manifeste des données.
- Documentation de l'architecture réelle, des écarts et de la prochaine étape d'import.
- Initialisation du projet Python.
- Ajout des modèles, du chargeur JSON et du GameState.
- Ajout des conditions, effets, registre de mécanismes et Rule Engine minimal.
- Ajout du journal Explain, des modes strict/partial, de la CLI et des tests unitaires.

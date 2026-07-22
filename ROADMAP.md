# Roadmap

## 1. Socle générique

- Modèles de domaine et état de jeu
- Chargeur de données brutes
- Conditions et effets déclaratifs
- Registre de mécanismes
- Rule Engine et journal Explain
- CLI et tests unitaires

Statut : initialisé et audité ; les phases Explain, la provenance et plusieurs champs de domaine restent à compléter.

## 2. Validation des données

- [x] Importer la capture brute, le catalogue officiel et l'audit dans un commit séparé
- [x] Vérifier leurs hashes SHA-256 et les compteurs disponibles du manifeste
- Importer les six artefacts sémantiques encore absents
- Mapper explicitement le schéma JSON officiel
- Documenter l’ordre d’application validé
- Ajouter les mécaniques déterministes confirmées
- Créer des fixtures issues des données officielles

## 2 bis. Données utilisateur

- [x] Séparer compte, inventaire, préférences, sacs et observations
- [x] Résoudre les références contre les identifiants officiels
- [x] Conserver l'inventaire partiel et les niveaux inconnus sans inférence
- [x] Fournir validation, rapports CLI et détection des améliorations
- Compléter progressivement les clubs et niveaux depuis des observations datées

## 3. Fidélité du simulateur

- Tests de régression par club et par sac
- Sac de référence après validation des capacités
- Chaînes, historique, terrain, vent, loft et rebond
- Modélisation contrôlée de l’aléatoire

## 4. Optimisation

- Fonction d’évaluation validée
- Recherche et comparaison de sacs
- Analyse de sensibilité et explications

# Changelog

## 2026-08-24 — Sacs réels comme références utilisateur

- Ajoute les métadonnées et notes de référence au profil utilisateur sans les injecter dans les règles du jeu.
- Compare chaque étape avant/après au sac réel, y compris lorsque des métriques observées ont été renseignées.
- Ajoute le remplacement ciblé d'un club, l'exploration facultative des supports et la sauvegarde confirmée des propositions.
- Corrige l'affectation des rôles d'un sac multi-étapes afin de réserver les clubs contraints aux étapes futures.

## 2026-08-24 — Audit exhaustif des capacités restantes

- Recalcule la couverture depuis l'inventaire SQLite actuel (80 clubs possédés) au lieu de reprendre les anciens totaux documentaires.
- Classe sans perte les 76 occurrences catalogue restantes dans les catégories A à H avec textes, niveaux, valeurs, primitives et provenance.
- Confirme qu'aucune capacité restante n'est actuellement qualifiée A ou B ; aucun handler hypothétique n'est ajouté.
- Rend les tests de suivi d'inventaire indépendants des futures modifications légitimes des niveaux et clubs possédés.
- Conserve High Flight 19/10/13 et Divebomb 16/9/9 sous forme de scénarios historiques à niveaux explicitement figés.

## 2026-08-24 — Fiabilité de la recherche contrainte

- Injecte les sacs enregistrés compatibles avant les réductions du constructeur interactif.
- Approfondit les affectations actives factuelles issues de ces sacs et réutilise les meilleures solutions compatibles pendant la session.
- Ajoute les diagnostics de réduction et distingue « meilleur trouvé » de « maximum prouvé ».
- Fige High Flight 19/10/13 et Divebomb 16/9/9 comme contrôles de non-régression, sans inventer le Spin 14 observé dans le jeu.

## Unreleased

- Ajout du constructeur interactif autour de plusieurs clubs avec rôles et positions facultatifs.
- Ajout des minimums factuels Control/Spin et Power/Control final du putt.
- Présentation de la Power maximale puis des compromis utiles à chaque palier réel de Power.
- Séparation déclarative de la préférence Progression/Attaque du green et Bounce Reduction hors du Rule Engine.
- Exposition des critères, plages observées, badges et deltas dans la GUI et les exports JSON/texte.
- Ajout des contraintes pratiques de sacs, de la détection fraîche de l’inventaire, de l’audit générique des nouveaux clubs et des comparaisons avant/après séparant attaque et atterrissage.
- Généralisation de la recherche autour d’un club et du test local d’un nouveau club, avec rôles actifs configurables et prise en charge des usages de support.
- Réduction exacte des permutations locales par signature structurelle, validée contre l’énumération historique complète.

- Qualification générique des bonus personnels de Power depuis le tee, contexte catégoriel strict/partial, audit SQLite d'éligibilité et cartographie détaillée des capacités possédées.
- Correction du tri des marques par comparaison normalisée, notamment pour le nom officiel `PALO`.
- Alignement de l'éditeur d'inventaire sur l'ordre des clubs du jeu, conservation du défilement et saisie clavier de type tableur.
- Calcul automatique de la progression des clubs dans l'éditeur visuel, avec cartes restantes, disponibilité d'amélioration et navigation clavier améliorée.
- Ajout de l'éditeur visuel Tkinter dédié à l'inventaire, de son lanceur Windows, de l'édition en lot transactionnelle et du menu principal simplifié.
- Ajout du catalogue SQLite immuable et versionné, du diff reproductible et de la vérification officielle du 4 août 2026.
- Migration sauvegardée du profil JSON vers SQLite, export diagnostique et adaptateur conservant les objets métier du moteur.
- Ajout de la synchronisation guidée en lot, du Data Dashboard et du contrat générique sérialisable des futures demandes d'optimisation.
- Ajout de Blacksmith à l'inventaire connu avec niveau et cartes explicitement inconnus.
- Ajout du lanceur Windows `DEMARRER_PGA_SHOOTOUT.bat`, du menu principal français et des assistants sauvegardés de gestion de l'inventaire et des sacs.
- Ajout d'un guide complet de premier lancement, de création des données utilisateur et d'utilisation interactive.
- Ajout de `recommend-interactive`, parcours guidé par noms lisibles avec catégories, avertissements et consultation de l'Explain d'un placement.
- Ajout de `recommend-placement`, de la matrice multi-position avec cache du sac de référence et de la séparation explicite entre niveaux réels et niveaux de scénario.
- Ajout du vertical slice `recommend-replacement` pour valider, évaluer, comparer, qualifier et expliquer un remplacement explicite sans score global.
- Ajout d'une couche minimale d'effets différés, de la primitive DSL `SCHEDULE_EFFECT` et du pattern générique Chains filtré par marque ou type de club.
- Ajout générique de Wind Resistance comme métrique objective, avec portées club et sac pilotées par le DSL existant.
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

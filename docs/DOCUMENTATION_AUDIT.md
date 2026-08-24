# Audit documentaire de la version stable

Audit réalisé le 24 août 2026 à partir du code, des données versionnées, des tests, puis des documents du plus récent au plus ancien. Aucun fichier fonctionnel, schéma SQLite ou donnée utilisateur n'a été modifié.

## Décisions

| Document audité | Rôle/état constaté | Décision |
|---|---|---|
| `README.md` | Porte d'entrée devenue partiellement historique | Refonte complète, état actuel |
| `CHANGELOG.md` | Historique chronologique utile | Conservé, entrée documentaire ajoutée |
| `DATA_MANIFEST.md` | Manifeste utile mais chemins/comptes partiellement obsolètes | Refonte et vérification |
| `PROJECT_CONTEXT.md` | Contexte initial et ancienne prochaine tâche | Archivé sous `PROJECT_CONTEXT_2026-07-22.md` |
| `ROADMAP.md` | Roadmap initiale achevée | Archivée sous `ROADMAP_2026-07-22.md` |
| `docs/ABILITY_AUDIT.md` | Audit de normalisation initial | Archivé ; remplacé fonctionnellement par `CAPABILITY_AUDIT.md` |
| `docs/CAPABILITY_AUDIT.md` | Audit exhaustif actuel des capacités | Conservé, introduction clarifiée |
| `docs/CATALOG_DIFF_2026-08-04.md` | Diff daté du catalogue | Archivé |
| `docs/COMPOSITION_SEARCH.md` | Audit High Flight/recherche/références | Fusionné dans `REGRESSION_CASES.md` et guides actuels, original archivé |
| `docs/DATA_DASHBOARD.md` | Tableau de bord daté et générable | Archivé ; `INVENTORY_STATUS.md` reste le diagnostic courant |
| `docs/DATA_FOUNDATION.md` | Données et migration | Refonte complète autour de SQLite courant |
| `docs/DSL_ARCHITECTURE.md` | DSL proposé avant implémentation | Archivé ; état réel dans `RULE_ENGINE.md` |
| `docs/ENGINE_PRIMITIVES.md` | Primitives proposées | Archivé ; registre réel dans `RULE_ENGINE.md` |
| `docs/ENGINE_READINESS.md` | Audit antérieur à l'optimiseur | Archivé |
| `docs/FIRST_RUN.md` | Premier lancement, utile mais partiellement obsolète | Refonte complète et vérifiée sur les launchers |
| `docs/GAMESTATE.md` | Contrat conceptuel antérieur | Archivé ; frontière active résumée dans `RULE_ENGINE.md` |
| `docs/INTERACTIVE_CLI.md` | Ancien parcours CLI principal | Archivé ; commandes actuelles dans `CLI.md` |
| `docs/INVENTORY_STATUS.md` | Rapport généré actuel de l'inventaire | Conservé, statut d'instantané clarifié |
| `docs/LANDING_VALIDATION.md` | Protocole expérimental encore unique et utile | Conservé |
| `docs/MECHANIC_COVERAGE.md` | Rapport structurel généré exigé par les tests, distinct de l'audit actuel | Conservé et marqué diagnostic historique ; ancienne copie archivée ; `CAPABILITY_AUDIT.md` reste la source actuelle |
| `docs/MULTI_STRATEGY_OPTIMIZER.md` | Rapport de validation daté | Fusionné dans stratégie/limites/régressions, original archivé |
| `docs/OPTIMIZATION_DATA_AUDIT.md` | Audit préparatoire | Archivé |
| `docs/OPTIMIZATION_REQUEST_CONTRACT.md` | Contrat préparatoire | Archivé ; architecture réelle documentée |
| `docs/OPTIMIZER_API.md` | Checklist préparatoire | Archivé |
| `docs/PAR3_OPTIMIZER_AUDIT.md` | Audit correctif daté | Fusionné dans les cas de régression, original archivé |
| `docs/PATTERN_DASHBOARD.md` | Dashboard de développement par patterns | Archivé |
| `docs/PRIMITIVE_ROADMAP.md` | Roadmap de primitives | Archivée |
| `docs/PROJECT_STATUS.md` | Rapport affirmant à tort que l'optimiseur était incomplet | Refonte complète, gel fonctionnel explicite |
| `docs/RECOMMENDATION_ENGINE.md` | Architecture/roadmap antérieure à l'implémentation | Archivé |
| `docs/REFERENCE_BAG_GAPS.md` | Matrice ancienne de sacs de référence | Archivée ; régressions courantes consolidées |
| `docs/STRATEGY_MODEL.md` | Modèle valide mêlé à des sections « futur optimiseur » achevées | Refonte sur le contrat réellement utilisé |
| `docs/STRATEGY_OPTIMIZER.md` | Guide le plus proche du produit actuel | Refonte complète avec stabilisation finale |
| `docs/USER_GAPS.md` | Rapport ancien limité à 21 clubs | Archivé |
| `docs/VALUE_WEIGHTING_API.md` | API préparatoire non utilisée par l'interface actuelle | Archivé |

## Datation apparente des documents audités

La date ci-dessous est celle du dernier commit ayant touché le document avant cet audit ; elle aide à distinguer fondations, spécifications et état produit.

| Date | Documents |
|---|---|
| 2026-07-22 | `DATA_MANIFEST.md`, `PROJECT_CONTEXT.md`, `ROADMAP.md`, `ABILITY_AUDIT.md`, `GAMESTATE.md`, `PRIMITIVE_ROADMAP.md` |
| 2026-07-23 | `DSL_ARCHITECTURE.md`, `ENGINE_PRIMITIVES.md`, `ENGINE_READINESS.md`, `INTERACTIVE_CLI.md`, `OPTIMIZER_API.md`, `PATTERN_DASHBOARD.md`, `RECOMMENDATION_ENGINE.md`, `REFERENCE_BAG_GAPS.md`, `USER_GAPS.md`, `VALUE_WEIGHTING_API.md` |
| 2026-08-04 | `CATALOG_DIFF_2026-08-04.md`, `DATA_DASHBOARD.md`, `DATA_FOUNDATION.md`, `OPTIMIZATION_DATA_AUDIT.md`, `OPTIMIZATION_REQUEST_CONTRACT.md` |
| 2026-08-05 | `LANDING_VALIDATION.md`, `MECHANIC_COVERAGE.md`, `PAR3_OPTIMIZER_AUDIT.md`, `STRATEGY_MODEL.md` |
| 2026-08-08 | `FIRST_RUN.md` |
| 2026-08-23 | `MULTI_STRATEGY_OPTIMIZER.md` |
| 2026-08-24 | `README.md`, `CHANGELOG.md`, `CAPABILITY_AUDIT.md`, `COMPOSITION_SEARCH.md`, `INVENTORY_STATUS.md`, `PROJECT_STATUS.md`, `STRATEGY_OPTIMIZER.md` |

## Documents actuels ajoutés

- `ARCHITECTURE.md` : couches et responsabilités actuelles ;
- `RULE_ENGINE.md` : registres, DSL, contexte, Chains, Explain et politique de connaissance ;
- `CLI.md` : inventaire vérifié des commandes supportées ;
- `KNOWN_LIMITATIONS.md` : point central des limites volontaires ;
- `REGRESSION_CASES.md` : valeurs utilisateur historiques et cas réels ;
- `DOCUMENTATION_AUDIT.md` : index, décisions et contradictions ;
- `archive/README.md` : frontière explicite des documents historiques.

## Contradictions résolues

| Contradiction | Source de vérité | Résolution documentaire |
|---|---|---|
| « L'optimisation viendra plus tard » | GUI, `StrategyOptimizer`, tests | README décrit l'optimiseur opérationnel. |
| Candidate generation/ranking annoncés incomplets | Code courant et validation Windows | `PROJECT_STATUS.md` réécrit. |
| Un launcher unique présenté comme parcours principal | Trois `.bat` réels | Rôle exact de chaque launcher documenté. |
| Tous les launchers supposés sélectionner Tk de la même manière | Scripts `.bat` et `windows_gui_launcher.ps1` | Sélection robuste attribuée uniquement au launcher optimiseur. |
| Données utilisateur JSON présentées comme source courante | `storage.py`, GUI, tests | SQLite devient explicitement la source de vérité. |
| Profondeur 2 assimilée à deux changements exacts | Code et tests de monotonie | Sémantique cumulative 0/1/2 documentée. |
| « meilleur » sans périmètre | Libellés GUI actuels | Terminologie actuelle uniformisée. |
| Référence toujours admissible | Filtrage actuel | Témoin non admissible et meilleur sac admissible documentés. |
| Club inconnu traité comme incomplet/exclu sans nuance | Modes partial et statuts actuels | Compromis partiellement évalué et inconnue non nulle documentés. |
| Par 4 long/Par 5 présentés comme physiquement distincts | Registre et absence de modèle de portée | Différence conceptuelle et limite calculable explicitées. |
| High Flight `19/10/13` et `19/10/14` mélangés | Fixture historique et observation | Écart historique conservé sans correction artificielle ; cas niveau 10 séparé. |
| 125 groupes décrits comme tous non interprétés | Carte/registre/audit plus récents | Ancien rapport archivé ; `CAPABILITY_AUDIT.md` devient la source détaillée. |
| Le générateur `inventory-status --write-reports` recréait un `PROJECT_STATUS` antérieur à l'optimiseur mature | Gabarit de génération actuel | Gabarit Markdown corrigé sans changer les calculs ; reproductibilité conservée par les tests. |

## Structure documentaire courante

### Démarrer et utiliser

- [`../README.md`](../README.md)
- [`FIRST_RUN.md`](FIRST_RUN.md)
- [`STRATEGY_OPTIMIZER.md`](STRATEGY_OPTIMIZER.md)

### Comprendre

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`RULE_ENGINE.md`](RULE_ENGINE.md)
- [`STRATEGY_MODEL.md`](STRATEGY_MODEL.md)
- [`DATA_FOUNDATION.md`](DATA_FOUNDATION.md)

### Capacités et limites

- [`CAPABILITY_AUDIT.md`](CAPABILITY_AUDIT.md)
- [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md)
- [`LANDING_VALIDATION.md`](LANDING_VALIDATION.md)

### Diagnostic et maintenance

- [`CLI.md`](CLI.md)
- [`INVENTORY_STATUS.md`](INVENTORY_STATUS.md)
- [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
- [`REGRESSION_CASES.md`](REGRESSION_CASES.md)

### Historique

- [`archive/`](archive/README.md)

## Documents supprimés

Aucun contenu documentaire n'a été supprimé. Les pages obsolètes ont été déplacées avec leur contenu intégral et un avertissement visible. Les informations encore utiles ont été fusionnées dans les documents actuels avant archivage.

## Future work — user-driven

Il n'existe plus de roadmap spéculative active. Les changements futurs devront répondre à une anomalie observée en utilisation réelle, une capacité réellement bloquante, un workflow ou une performance gênante, ou une information manquante constatée.

# Rule Engine, DSL et Explain

## Principe

Le moteur applique uniquement des règles qualifiées depuis les données versionnées. Il ne contient aucune branche sur un nom de club. Une capacité officielle est reliée à un mécanisme générique ou à un pipeline DSL déclaré dans la carte sémantique.

```text
Club + niveau + position + contexte optionnel
                    ↓
             Ability / Effect
                    ↓ condition
      registre de mécanismes ou pipeline DSL
                    ↓
    Contribution + statistiques + Explain
```

## Conditions et contexte

Les conditions supportent l'application inconditionnelle, les valeurs catégorielles du `GameState`, la position du sac et les relations gauche/droite. Le contexte actif reste minimal : sac ordonné, club courant, étape éventuelle, terrain catégoriel lorsqu'il est fourni et effets différés en attente.

Une donnée absente est signalée. En mode `strict`, une mécanique ou un contexte indispensable inconnu bloque l'évaluation. En mode `partial`, les calculs connus continuent et l'élément manquant devient explicitement non résolu.

## Mécanismes et primitives

Le registre de mécanismes expose `add_stat`, `add_all_stats` et l'exécution d'un pipeline DSL. Le registre DSL actuel contient :

- valeurs : `READ_LEVEL_VALUE` ;
- sélections : `SELECT_SELF`, `SELECT_ALL`, `SELECT_ADJACENT`, `SELECT_FARTHEST` ;
- filtres : `MATCH_BRAND`, `MATCH_TYPE`, `MATCH_RARITY` ;
- agrégations/contrôle : `COUNT`, `EXISTS`, `FOR_EACH`, `UNLESS` ;
- calcul : `SCALE` ;
- effets : `ADD_STAT`, `ADD_MODIFIER`, `SCHEDULE_EFFECT` ;
- transformations : `ABILITY_EFFECT_MULTIPLIER`.

Ces primitives composent des effets personnels, d'adjacence, de marque, de type, de rareté, de position ou de sac entier sans dupliquer la logique métier.

## Positions, supports et ordre

Le sac est ordonné de 1 à 5. Les capacités peuvent sélectionner le club source, tous les clubs, les voisins immédiats ou une cible la plus éloignée lorsque celle-ci est unique. Les clubs support restent dans le sac et peuvent produire ou recevoir des contributions même s'ils ne sont actifs sur aucune étape.

Les relations gauche/droite et les effets positionnels sont calculés depuis l'ordre, jamais depuis un identifiant de club codé en dur.

## Transformation générique des capacités

Une capacité déclarée avec la phase `ability_transform` est résolue avant les effets
natifs ordinaires du coup. Le DSL sélectionne son propriétaire, lit son multiplicateur
de niveau, sélectionne un voisin et produit une demande `AbilityAmplification`.
La demande contient source, cible relationnelle résolue, multiplicateur et provenance.
Les conditions d'activation restent celles de l'effet déclaratif.

Le moteur prépare une vue temporaire des effets natifs, sans modifier le catalogue,
le niveau du voisin ou ses conditions/cibles. Il multiplie la magnitude à l'entrée
du terminal additif, **pas** les statistiques finales, les paramètres d'une sélection,
le nombre de voisins ou tous les nombres d'un programme. Exemple : un propriétaire
B émet +3 Power vers A ; son amplificateur C transforme cette magnitude en +6 ;
le terminal habituel de B applique +6 à A. La Power de base de A n'est pas doublée.

### Qualification des formes actuelles

| Classe | Mécanismes / primitives | Traitement |
|---|---|---|
| A : multiplication sûre dans le modèle qualifié | `add_stat`, `add_all_stats`, `ADD_STAT` Power/Control/Spin | Magnitude additive × facteur, y compris une pénalité négative ; mêmes cibles, conditions, propriétaire et niveau. |
| B : règle déjà définie | `SELECT_SELF`, `SELECT_ALL`, `SELECT_ADJACENT`, `SELECT_FARTHEST`, `MATCH_BRAND`, `MATCH_TYPE`, `MATCH_RARITY` | Relations conservées ; aucune multiplication de position, distance ou filtre. |
| B : règle déjà définie | `READ_LEVEL_VALUE`, `COUNT`, `EXISTS`, `SCALE`, `FOR_EACH`, `UNLESS` | Programme original conservé ; seule sa sortie additive terminale est amplifiée. |
| B : règle déjà définie | `SCHEDULE_EFFECT` avec payload additif connu | Magnitude du payload amplifiée avant planification ; une seule réservation, consommation existante, provenance conservée au déclenchement. |
| C : non résolue | `ADD_MODIFIER` : Bounce, Wind Resistance, Groundspin, Loft, Gravity, multiplicateurs, etc. | Une valeur numérique n'établit pas la règle de cumul de deux instances. Effet natif conservé, amplification signalée non résolue. |
| C : non résolue | Primitive inconnue, programme mixte non qualifié, vent ajouté, physique, effet temporaire/non natif, transformation d'une transformation | Pas de magnitude inventée ; diagnostic explicite. |

Ces classes sont une qualification de formes de calcul, pas une liste de noms de clubs.
Une capacité composée de plusieurs effets est traitée effet par effet : un composant
additif peut être amplifié tandis qu'un autre reste non résolu. Un programme indivisible
mélangeant des terminaux non qualifiés reste conservativement non amplifié.

### Ordre, provenance et protections

1. Résoudre les effets différés déjà planifiés, sans réappliquer leur multiplicateur.
2. Résoudre les sélections des transformations du coup courant sur le sac natif.
3. Préparer une transformation par effet admissible, indépendamment de sa place dans la liste d'exécution.
4. Résoudre normalement les capacités natives et planifier les éventuels payloads amplifiés.

Une transformation ne peut ni modifier directement les stats ni planifier un coup.
Les transformations ne sont jamais relancées depuis leurs résultats : une seule passe
sur les instances natives. Auto-amplification, amplification d'une transformation et
plusieurs amplificateurs visant le même propriétaire sont non résolus ; ni ×3 ni ×4
ne sont supposés. Les effets temporaires ne sont pas assimilés à des capacités natives.
Le mode strict bloque un cas indispensable non qualifié ; partial conserve les effets
natifs et les amplifications sûres, avec leurs inconnues explicites.

`SELECT_ADJACENT` accepte un wrap explicite, désactivé par défaut et configuré par
les données de niveau. Une sélection vide ne produit aucun bonus ; un sac singleton
ne sélectionne pas sa propre source par wrap.

Explain sépare la transformation et la contribution. Le bonus amplifié reste attribué
à B ; C porte des faits d'amplification (voisin, capacité, valeur originale/amplifiée,
cible finale, statut). Ces faits ont une modification statistique vide pour éviter
tout double comptage. `AbilityContribution.amplifications` et les résultats par coup
exposent cette provenance aux comparaisons, exports et cartes. Le rôle support de C
est confirmé par le contrefactuel existant de retrait du club.

## Chains et effets différés

`SCHEDULE_EFFECT` crée un effet planifié associé à une condition de club compatible. Lors des étapes suivantes, le moteur vérifie la condition, applique la contribution au premier déclenchement qualifié et consomme l'effet. Cette couche répond aux Chains supportées ; elle n'est pas un historique complet de partie.

Lorsque consommation, expiration ou interaction ne sont pas suffisamment qualifiées, l'effet reste partiel/non résolu au lieu d'être inventé.

## Métriques

Les statistiques de base sont Power, Control et Spin. Les contributions statiques qualifiées peuvent aussi exposer Loft, Launch Angle, Bounce Reduction, Groundspin, Wind Resistance et autres modificateurs officiels. Leur présence ne signifie pas qu'une direction physique bénéfique a été prouvée.

`data/strategies/metric_semantics.json` sépare métriques objectives, contextuelles et descriptives. `data/strategies/optimization_policies.json` décrit la politique produit, notamment Power comme objectif principal et Bounce Reduction comme compromis important pour certaines attaques du green.

## Explain

Chaque étape du DSL journalise ses entrées et sorties. Une contribution conserve sa source, sa capacité, sa condition, sa cible, la métrique, la valeur avant, la modification, la valeur après et son niveau de confiance/provenance lorsqu'il est disponible.

Le résultat distingue :

- effets appliqués ;
- effets ignorés parce que leur condition ne correspond pas ;
- capacités partielles ;
- capacités non résolues ;
- effets différés créés, déclenchés ou encore en attente.

## Politique de connaissance

Le texte officiel, les tables de niveaux et les observations validées peuvent justifier une règle. Une ressemblance de nom, une note utilisateur ou une supposition physique ne le peuvent pas. Shoreline Rush, Boundary Rush, Alien World, Perfect Shot, transformations non qualifiées, aléatoire et plusieurs effets terrain restent non résolus. Alien Relic possède désormais un sous-ensemble additif qualifié, sans généralisation implicite à tous les effets numériques.

L'état détaillé est généré dans [CAPABILITY_AUDIT.md](CAPABILITY_AUDIT.md).

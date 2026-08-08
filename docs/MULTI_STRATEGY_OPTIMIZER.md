# Validation multi-stratégies de l’optimiseur

## Périmètre

Cette validation couvre les quatre stratégies existantes avec l’inventaire
SQLite observé le 8 août 2026 : Par 3, Par 4 court, Par 4 long et Par 5. Aucun
modèle de distance, score global, nouvelle capacité ou nouvelle stratégie n’a
été ajouté.

## Audit initial

Par 3 produisait déjà quatre familles explicites et des résultats exploitables.
Par 4 court, Par 4 long et Par 5 n’avaient aucune famille déclarée : le moteur
affichait simplement les cinq premiers éléments de son front global. Par 4 court
pouvait ainsi commencer par Homestead 9/12 plutôt que par les profils de Power
attendus. Par 4 long et Par 5 matérialisaient chacun 66 456 affectations actives
avant de ne générer que 18 compositions, ce qui coûtait environ 14 secondes de
génération.

Les séquences étaient néanmoins correctes : deux actifs distincts pour Par 3 et
Par 4 court ; trois actifs distincts pour Par 4 long et Par 5. Les métriques du
putt étaient déjà limitées à Power et Control. Loft, Bounce Reduction,
Groundspin et Wind Resistance y restaient descriptifs.

## Changements génériques

Lorsque la stratégie ne déclare pas ses propres familles, le moteur construit
des vues depuis les `ShotFunction` et les métriques objectives de chaque
`ShotStep` : Power maximale, paliers Power/Control, contrôle de l’attaque de
green, approche Iron, concurrent tous types, putter Power/Control et front de
toute la séquence. Aucun identifiant de stratégie n’est testé dans le moteur.

La réduction des affectations actives utilise désormais un préfixe diagonal
équitable, sans matérialiser le produit complet. Le nombre théorique et le
nombre effectivement considéré sont tous deux exportés. Les références
empiriques choisissent génériquement la première étape qui n’est pas une
finition lorsqu’aucun `reference_step_id` n’est déclaré.

Un cache d’évaluation limité à une exécution est ajouté. Il est recréé à chaque
optimisation avec le catalogue et l’inventaire relus ; il ne peut donc pas
masquer un nouveau club ou un changement de niveau.

## Résultats réels

### Par 3 — contrôle de non-régression

- Divebomb : 16 Power / 9 Control / 9 Spin ;
- High Flight enregistré : 19 / 10 / 13 ;
- l’observation 19 / 10 / 14 reste non expliquée et n’est pas inventée ;
- Gearshift est disponible au niveau 8 ;
- les 120 ordres sensibles restent évalués.

### Par 4 court

La famille Power maximale retient High Flight à 19/10/13 avec Ember au putt à
13/10. Divebomb reste visible à 16/9/9 avec Ember 15/17. Les familles de contrôle
font naturellement apparaître Homestead ou Cloudcatcher, et Gearshift comme
putter/support directionnel. Ces profils ne prouvent pas qu’un Par 4 est
atteignable en un coup.

### Par 4 long

Un profil de départ maximal utilise High Flight 19/10/13, Cyclotron en approche
11/7/12 et Ember au putt 13/10. Un autre ordre accepte un départ High Flight
17/8/11 pour porter Cyclotron à 13/9/14 sur l’approche. Le sac est donc comparé
comme une séquence complète : maximiser le premier coup n’est pas équivalent à
maximiser le deuxième.

### Par 5

Sans modèle de distance ni contexte distinctif validé, les fronts calculables
sont actuellement identiques à ceux de Par 4 long. Cette identité est une
limite honnête, pas une règle de jeu. La vue Iron montre Cloudcatcher 7/11/10 ;
la vue tous types conserve aussi High Flight 12/10/9, tandis que la famille de
Power maximale d’approche montre Cyclotron 13/9/14.

## Interactions multi-étapes

Les contributions restent attribuées par étape et par métrique. Dans le sac de
référence Divebomb, Steadfast soutient départ, approche et putt ; Sunstorm ne
soutient pas nécessairement les mêmes étapes. Divebomb et Jumpstart deviennent
hybrides : actifs sur leur propre coup et supports d’un autre actif. La Chain de
Divebomb traverse l’approche incompatible puis est consommée au putt compatible.

L’ordre peut modifier simultanément plusieurs étapes. Les exports donnent pour
chaque résultat les ordres évalués, les valeurs finales de chaque actif, les
contributions reçues/envoyées et les pertes contrefactuelles par support.

## Gearshift

Gearshift participe aux quatre stratégies sans branche particulière. À gauche
dans un exemple Par 5, il est putter 13/8 et donne +1 Control à High Flight et
Cyclotron. À droite comme deuxième putter-support, il donne +1 Power aux trois
actifs ; High Flight passe à 13/10/9 et Cyclotron à 12/9/10. Ces exemples sont
entièrement résolus, mais ne dominent pas nécessairement les meilleurs fronts.

## Instrumentation et performance

Avec une limite globale de 2 000 candidats :

| Stratégie | Compositions | Permutations évaluées | Génération | Moteur | Total approximatif |
|---|---:|---:|---:|---:|---:|
| Par 3 | 18 | 2 160 | 0,14 s | 7,40 s | 8,11 s |
| Par 4 court | 18 | 2 160 | 0,13 s | 7,25 s | 7,99 s |
| Par 4 long | 18 | 2 160 | 0,15 s | 11,59 s | 12,62 s |
| Par 5 | 18 | 2 160 | 0,20 s | 12,27 s | 13,35 s |

Les 512 affectations actives considérées sur 66 456 théoriques pour les
stratégies à trois étapes constituent une réduction déclarée. La recherche ne
garantit donc pas l’optimum absolu. Les recherches locales à un remplacement
restent exhaustives sur les compositions et les ordres de l’affectation active
retenue ; elles ne prétendent pas énumérer toutes les affectations de rôles.

## Limites restantes

- aucune conversion Power → distance ;
- Par 4 long et Par 5 non distinguables objectivement dans le contexte actuel ;
- affectations actives globales réduites à un préfixe équitable ;
- certaines capacités restent non résolues et sont signalées ;
- la recherche locale réelle sur trois étapes demeure plus coûteuse ;
- aucun classement global entre compromis n’est produit.


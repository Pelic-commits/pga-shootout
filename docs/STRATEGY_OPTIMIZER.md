# Optimiseur de sacs par stratégie

`optimize-strategy` est la première recherche automatique de sacs fondée sur une
`StrategyDefinition`. Le cas de validation actuel est `par3`, mais le générateur
ne contient aucune branche liée à cet identifiant : il lit la séquence, les
contraintes de clubs actifs, les objectifs locaux, les contextes et le nombre de
places de support dans le registre.

## Lancer une recherche

Mode réel, avec les clubs possédés et leurs niveaux SQLite :

```powershell
pga-shootout optimize-strategy par3 --partial --limit 20
```

Sortie structurée :

```powershell
pga-shootout optimize-strategy par3 --partial --limit 20 --json
```

Analyse explicitement hypothétique, au niveau 12 :

```powershell
pga-shootout optimize-strategy par3 --partial --scenario-level 12
```

Une variante compatible peut être ajoutée avec `--variant <id>`. `--strict`
écarte un candidat dès qu'une mécanique indispensable reste non résolue ; le
mode par défaut et `--partial` conservent les résultats calculables avec leurs
avertissements. `--max-evaluations` est une limite de sécurité explicite.

## Données et affectations

En mode réel, seuls les clubs marqués comme possédés et dotés d'un niveau connu
sont admissibles. Un niveau manquant exclut le club et apparaît avec sa raison.
Aucun niveau commun n'est inventé.

Chaque étape reçoit un club actif conforme aux `club_constraints` déclarées. Le
nom d'un rôle ne devient jamais implicitement un type de club. Le registre
déclare par exemple explicitement `type equals putter` pour les étapes de
finition qui l'exigent. `allow_active_club_reuse` décide si un même club physique
peut servir à plusieurs étapes.

Les autres places sont des candidates au support. Le rôle affiché est dérivé des
contributions effectivement observées :

- **actif** : utilisé pendant au moins une étape ;
- **support** : non actif, mais envoie une contribution utile ;
- **hybride** : actif et envoie aussi une contribution à un autre actif ;
- **neutre** : aucun effet différenciant observé.

Le retrait conceptuel de chaque support mesure séparément ce qui serait perdu ou
gagné. Cette analyse ne crée aucun score synthétique.

## Recherche et niveau de complétude

L'espace théorique contient les affectations actives, les compositions de
supports et les ordres possibles. Il est trop grand pour être parcouru en entier
sur l'inventaire réel. La première version applique donc une recherche
**partielle et réduite**, déclarée comme telle :

1. conservation de couches non dominées sur Power, Control et Spin pour les
   clubs actifs ;
2. plusieurs fenêtres génériques de supports susceptibles d'émettre un effet ou
   de correspondre aux attributs des actifs ;
3. inclusion des sacs enregistrés comme points de référence ;
4. échantillon déterministe d'ordres représentatifs ;
5. déduplication des résultats strictement équivalents.

L'instrumentation expose le nombre théorique, les candidats générés et évalués,
les permutations éliminées, les doublons de résultat, les durées et l'atteinte
éventuelle de la limite de sécurité. Cette méthode ne garantit pas l'optimum
global.

## Lire les résultats

Les statistiques **de base** proviennent du catalogue au niveau du joueur. Les
statistiques **finales** incluent les contributions résolues du sac et du
contexte de l'étape. Power, Control et Spin utilisent la forme :

```text
Power   : base → final (delta)
Control : base → final (delta)
Spin    : base → final (delta)
```

Une statistique officielle absente est affichée `—`, jamais zéro. Les autres
métriques objectives produites par le moteur sont conservées séparément.

Un même club peut avoir des valeurs finales différentes entre le tee et le green
ou avant/après un effet différé. Le JSON conserve donc la matrice complète
`club × étape × métrique`. Les Chains prises en charge sont transmises entre les
étapes dans leur ordre déclaré.

Les candidats sont comparés selon les objectifs locaux disponibles, métrique par
métrique. Plusieurs compromis peuvent être conservés. L'ordre technique stable
d'affichage n'est pas un score qualitatif et `aggregate_score` vaut toujours
`null`.

## Limites honnêtes

Le moteur ne possède actuellement ni modèle validé de portée, ni modèle validé
de réussite d'un putt. Il ne transforme pas Power en yards et ne prétend pas
qu'un sac atteindra le green. Les exigences correspondantes restent
`indeterminate`, tandis que les statistiques et contributions réellement
calculables restent comparables.


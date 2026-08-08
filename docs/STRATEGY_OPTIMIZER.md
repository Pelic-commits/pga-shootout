# Optimiseur de sacs par stratégie

`optimize-strategy` est la première recherche automatique de sacs fondée sur une
`StrategyDefinition`. Le cas de validation actuel est `par3`, mais le générateur
ne contient aucune branche liée à cet identifiant : il lit la séquence, les
contraintes de clubs actifs, les objectifs locaux, les contextes et le nombre de
places de support dans le registre.

Le parcours utilisateur normal ne demande aucune commande : double-cliquez sur
`OPTIMISER_MES_SACS.bat`. Les commandes ci-dessous restent disponibles pour les
usages avancés et le diagnostic.

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

`--reference-bag <id>` utilise facultativement la Power finale du club de départ
d’un sac enregistré comme minimum empirique. Ce seuil ne représente jamais une
distance garantie. `--order-mode structural_exact` est le mode normal ;
`full_120` et `legacy_reduced` sont réservés au diagnostic.

## Améliorer un sac existant

La fenêtre propose trois modes : chercher de nouveaux sacs, améliorer un sac
enregistré, ou optimiser autour d'un club possédé. En ligne de commande :

```powershell
pga-shootout optimize-strategy par3 --search-mode improve_bag --target-bag par3_high_flight --replacement-depth 1
pga-shootout optimize-strategy par3 --search-mode around_club --target-bag par3_divebomb --fixed-club divebomb --replacement-depth 1
```

La profondeur 1 est exhaustive sur les remplacements simples. La profondeur 2
est réduite aux paires liées par une synergie structurelle et l'indique dans les
résultats. Voir `COMPOSITION_SEARCH.md` pour le contrôle par les sacs enregistrés,
la commande `trace-composition` et l'audit High Flight/Gearshift.

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
4. toutes les permutations structurellement distinctes de chaque composition ;
5. déduplication des résultats strictement équivalents.

L'instrumentation expose le nombre théorique, les candidats générés et évalués,
les permutations éliminées, les doublons de résultat, les durées et l'atteinte
éventuelle de la limite de sécurité. Cette méthode ne garantit pas l'optimum
global.

Une permutation n’est supprimée que si toutes les capacités de la composition
sont démontrées insensibles à la position, l’adjacence, la distance et aux effets
différés. Sinon les 120 ordres sont évalués. Le résultat expose la preuve, le
nombre théorique, le nombre distinct et le nombre effectivement évalué.

## Familles Par 3 et profil d’atterrissage

Sans référence empirique, la stratégie Par 3 projette les mêmes candidats dans
quatre vues déclaratives : Iron le plus puissant, paliers Power/Control des
Irons, stabilité des Irons, et meilleur concurrent tous types. Ces vues dédiées
n’imposent pas les Irons : un Wood, Hybrid, Driver ou Wedge reste admissible dans
la vue tous types.

Le profil d’atterrissage affiche séparément Loft, Bounce Reduction, Groundspin,
Spin, Control et Wind Resistance. Il ne calcule aucun score. Loft décrit un angle
officiel mais aucune relation validée ne permet de conclure qu’une valeur plus
haute est meilleure. Bounce Reduction est activée seulement si une variante
demande explicitement de réduire le roulement ; Wind Resistance seulement dans
un contexte de vent. Les autres contributions restent visibles comme faits
descriptifs sans influencer le classement ou le rôle de support.

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

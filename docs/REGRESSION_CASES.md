# Cas réels de référence et de non-régression

Ces valeurs sont des observations utilisateur et des fixtures de test. Elles ne remplacent pas le catalogue officiel et ne constituent pas des vérités universelles sur le jeu.

## Par 3 Divebomb

Composition : Divebomb / Jumpstart / Steadfast / Ember / Sunstorm.

- Divebomb observé au niveau courant : `17 Power / 10 Control / 9 Spin` ;
- Ember observé : `11 Power / 16 Control` ;
- une variante calculée `13/6/5` ne doit jamais être présentée comme une amélioration de `17/10/9` ;
- si rien ne progresse sans perte, le sac reste **SAC ACTUEL — MEILLEUR RÉSULTAT CONNU**.

L'ancien contrôle `16/9/9` utilisait Divebomb niveau 8. Il ne doit pas être confondu avec l'état courant niveau 10.

## XLR8R

Composition de référence : XLR8R / Jumpstart / Divebomb / Sparky / Sunstorm. XLR8R observé : `15/8/10`.

Le remplacement ciblé en politique **Même type** ne considère que des Drivers admissibles. **Tous les types admissibles** élargit explicitement la recherche. Le meilleur résultat jusqu'à deux changements ne peut pas régresser par rapport à la profondeur 1 injectée.

## High Flight historique

Composition et niveaux historiques : High Flight 8 / Cyclotron 8 / Ember 7 / Maelstrom 6 / Sunstorm 6.

- moteur : `19/10/13` ;
- observation visuelle : `19/10/14` ;
- écart : `+1 Spin` non expliqué, non corrigé artificiellement.

Avec l'état plus récent High Flight 10 / Cyclotron 8 / Ember 8 / Maelstrom 6 / Sunstorm 6, le moteur produit `21/11/14`. Les deux cas restent distincts.

## Skyfury

Composition : Gearshift / Skyfury / Jumpstart / Maelstrom / Divebomb. Skyfury observé : `14/6/13`.

Boundary Rush reste non résolue. Skyfury peut être imposé, mais la proposition doit être marquée **partiellement évaluée**.

## Windstrike

Composition : Windstrike / Jumpstart / Steadfast / Ember / Sunstorm. Windstrike observé : `14/10/11`.

La note utilisateur « trop court pour l'usage recherché » reste une observation et n'influence pas le Rule Engine. Une proposition inférieure ne devient pas une amélioration.

## Sac confort multi-étapes

Composition : Homestead / Kinship / Steadfast / Cyclotron / Jumpstart.

Ce cas vérifie les rôles observés par sac, la comparaison départ/approche/putt fonction à fonction, Support, Variable et l'absence d'affectation ambiguë silencieuse. Les rôles sont saisis dans une copie de test ; aucun exemple documentaire ne préremplit les données réelles.

## Couverture de validation

Les tests permanents vérifient également marques autorisées, club obligatoire, putter, minimums Control/Spin, deux Putters, capacités non résolues, exports texte/JSON, sauvegardes, profondeur cumulative et distinction **MEILLEUR TROUVÉ** / **MAXIMUM PROUVÉ**.

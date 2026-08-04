# Fondation de données

## Catalogue officiel

La source vérifiée est la page officielle Concrete Software :
`https://concretesoftware.com/pga-tour-golf-shootout-club-stats/`.
Elle annonçait le 4 août 2026 une dernière mise à jour au 14 juin 2026 et
présentait 88 clubs. Les neuf marques et leurs nombres de clubs correspondent
exactement à la capture locale du 21 juillet 2026. La vérification du 4 août est
donc une nouvelle **version de vérification**, pas une fausse nouvelle extraction :
son contenu est volontairement identique et le diff est nul.

La base conserve les deux versions, leur source, leurs empreintes SHA-256, la
date de capture/vérification, le niveau de confiance et les limites de preuve.
Une recommandation peut ainsi citer son `catalog_version`.

Blacksmith est présent dans la source officielle : Mythical, Iron, rareté
Mythical, Elite, déblocage 6. Les niveaux disponibles sont 9, 10, 11, 12 et
Elite. Power vaut 10/11/12/13/13, Control 7/8/9/10/10 et Spin 5/6/7/8/8.
La capacité Texas Tee vaut +5/+6/+7/+8/+10 et son texte officiel est :
“Gains additional Power when hitting from the tee.”

Limite : cette vérification ne prouve pas qu'aucun contenu masqué ou non publié
n'existe au-delà des 88 clubs exposés par la page officielle.

## Stockage

`data/pga_shootout.sqlite` est la base locale normale (non versionnée par Git).
Elle sépare :

- les tables de catalogue immuables et versionnées ;
- le profil, les clubs examinés, les sacs et leur ordre ;
- un journal minimal des changements ;
- les traces de migration et les sauvegardes.

Le moteur ne lit pas SQLite : l'adaptateur de stockage reconstruit les mêmes
objets `UserDataBundle`, `InventoryEntry` et `SavedBag` qu'auparavant. Les JSON
restent importables et exportables pour transfert ou diagnostic.

## Migration et récupération

`pga-shootout data-init --preview` affiche les nombres et empreintes avant toute
écriture. `pga-shootout data-init` :

1. sauvegarde les cinq JSON historiques ;
2. importe le tout dans une transaction ;
3. compare les nombres d'entrées, sacs, positions et observations ;
4. annule la transaction si un contrôle échoue.

Une synchronisation guidée crée également une copie SQLite avant d'appliquer en
une transaction toutes les modifications confirmées. L'annulation ne touche pas
la base. `pga-shootout data-export --output-dir <dossier>` produit les cinq JSON
de diagnostic.

## Synchroniser mon inventaire

Lancer `DEMARRER_PGA_SHOOTOUT.bat`, choisir « Consulter ou modifier mes clubs »,
puis « Synchroniser mon inventaire ». La session permet recherche par nom,
filtres marque/type/rareté, clubs nouveaux, non examinés ou incomplets. Les
niveaux et cartes peuvent rester vides. Plusieurs clubs sont placés dans un
résumé avant une confirmation unique ; aucun identifiant technique n'est demandé.

## Maintenance

- Ajouter toute extraction à `data/raw/` sans remplacer l'ancienne.
- Ajouter une entrée à `data/catalog/versions.json` avec empreintes et limites.
- Initialiser la base puis exécuter `catalog-diff`.
- Examiner le rapport JSON et Markdown avant de déclarer une version courante.
- Ne jamais combler une donnée absente ou qualifier une mécanique par déduction.

# Premier lancement sous Windows

Ce guide permet d'utiliser l'application sans connaître Python, Git ou la structure du projet.

## 1. Installer le seul prérequis

Installez **Python 3.11 ou plus récent** depuis [python.org](https://www.python.org/downloads/). Conservez l'option **Tcl/Tk et IDLE**. L'ajout au `PATH` est utile pour l'assistant textuel et l'éditeur d'inventaire.

Il n'y a rien à compiler et aucun serveur de base de données à installer. Python fournit Tkinter et SQLite.

## 2. Récupérer le projet

Téléchargez ou clonez le dépôt, puis placez-le dans un dossier où vous avez le droit d'écrire. Ne déplacez pas séparément les fichiers `.bat` : ils utilisent les scripts et données du même dossier.

## 3. Ouvrir l'inventaire

Double-cliquez sur **`GERER_MON_INVENTAIRE.bat`**.

L'éditeur affiche les 88 clubs du catalogue. Les champs de progression éditables sont :

- **Possédé** ;
- **Niveau** ;
- **Cartes possédées**.

Le seuil du niveau suivant, la progression, les cartes restantes et **Amélioration disponible** sont calculés. Une cellule vide signifie « inconnu » ; `0` signifie réellement zéro.

Vous pouvez rechercher, filtrer et trier. `Tab` passe à la cellule modifiable suivante ; `Entrée` valide la cellule. Les filtres et la position de la liste sont conservés pendant la saisie.

Cliquez sur **Enregistrer toutes les modifications**. L'écriture est transactionnelle et une sauvegarde SQLite est créée avant la modification.

## 4. Ouvrir l'optimiseur

Double-cliquez sur **`OPTIMISER_MES_SACS.bat`**.

Ce lanceur :

1. cherche les installations Python locales ;
2. retient la première version 3.11+ qui sait réellement ouvrir et fermer une fenêtre Tk et fournit `pip`/`venv` ;
3. crée ou recrée uniquement `.venv` si nécessaire ;
4. installe le projet localement ;
5. vérifie en lecture seule Tkinter, SQLite, le registre de stratégies et l'inventaire ;
6. ouvre la GUI dans un processus Windows séparé.

Le diagnostic du préflight est écrit dans `logs/gui_preflight.txt`. La recréation de `.venv` ne supprime ni SQLite, ni sauvegarde, ni export.

## 5. Première recherche

1. Choisissez une stratégie.
2. Choisissez le **Club principal**.
3. Ajoutez éventuellement un ou plusieurs clubs obligatoires.
4. Conservez Power comme objectif principal et ajoutez si besoin des minimums Control/Spin.
5. Conservez **Toutes les marques**, ou sélectionnez les marques autorisées.
6. Cliquez sur **OPTIMISER MON SAC**.

Le calcul part d'un sac vide. Aucun sac enregistré n'est demandé ou utilisé. Pour une première recherche Par 3 autour de Blacksmith, trois actions suffisent : choisir Par 3, choisir Blacksmith, optimiser.

La fenêtre reste réactive pendant le calcul. L'inventaire est relu avant chaque lancement : après une modification enregistrée, il n'est pas nécessaire de redémarrer l'optimiseur.

## 6. Créer et utiliser un sac

L'assistant textuel historique reste disponible via **`DEMARRER_PGA_SHOOTOUT.bat`**. Choisissez **Gérer mes sacs**, donnez un nom, puis sélectionnez cinq clubs possédés dans leur ordre. Les doublons sont interdits.

Dans la GUI, un résultat peut également être sauvegardé comme sac. Un sac peut ensuite être marqué comme référence et recevoir : libellé, usage, stratégie, club principal, stabilité, notes, métriques observées et rôles par club.

Les rôles ne modifient pas les règles du jeu. Ils indiquent seulement comment ce sac précis est réellement joué.

## 7. Tester un remplacement

Dans la GUI, choisissez **Remplacer un club de mon sac**, sélectionnez le sac puis le club sortant.

- **Même type que le club actuel** est le réglage par défaut.
- **Tous les types admissibles** autorise explicitement un changement de type.
- **Jusqu'à 1 remplacement** examine la référence et les changements simples.
- **Jusqu'à 2 remplacements** inclut 0, 1 et 2 changements.

Les marques autorisées peuvent être combinées à ces contraintes.

## 8. Lire les résultats

- chaque fiche commence par les étapes actives puis présente les cinq clubs, leurs niveaux, types, rôles et statistiques finales ;
- la ligne `→` explique pourquoi chaque place est présente ;
- **Amélioration sans contrepartie observée** : gain pertinent sans perte calculable ;
- **COMPROMIS** : gains et pertes ;
- **COMPROMIS PARTIELLEMENT ÉVALUÉ** : une capacité ou métrique pertinente reste inconnue ;
- **MEILLEUR SAC ADMISSIBLE** : résultat sous une restriction que la référence ne respecte pas ;
- **MEILLEUR TROUVÉ** : recherche bornée ;
- **MAXIMUM PROUVÉ** : espace pertinent réellement exhaustif.

Power, Control, Spin et les métriques d'atterrissage sont séparées. L'application ne calcule aucun score global caché. Consultez l'Explain pour connaître chaque contribution.

## 9. Données et sauvegardes

- état utilisateur : `data/pga_shootout.sqlite` ;
- sauvegardes : `data/backups/` ;
- catalogue : `data/normalized/clubs_official.json` ;
- capture brute : `data/raw/` ;
- exports : emplacement choisi lors de l'export ;
- diagnostic de lancement : `logs/gui_preflight.txt`.

Les JSON de `data/user/` sont un format historique d'import/export. SQLite est la source de vérité courante.

## 10. Problèmes courants

| Symptôme | Action |
|---|---|
| « Aucun Python 3.11+… » | Réinstallez Python depuis python.org avec Tcl/Tk. |
| L'optimiseur ne s'ouvre pas | Consultez `logs/gui_preflight.txt`, puis relancez `OPTIMISER_MES_SACS.bat`. |
| Tkinter indisponible | Modifiez l'installation Python et ajoutez Tcl/Tk et IDLE. |
| Niveau réel manquant | Renseignez-le dans l'éditeur ou utilisez volontairement un niveau de scénario. |
| Club absent des résultats | Vérifiez Possédé, niveau, rôle, position, type de remplacement et marques. |
| Résultat partiel | Ouvrez les avertissements : la capacité inconnue n'a pas été comptée comme zéro. |
| Calcul long | Attendez la fin ; la GUI reste asynchrone. Réduisez les contraintes seulement si cela correspond à votre besoin. |
| Base verrouillée | Fermez l'autre fenêtre qui écrit dans SQLite, puis réessayez. |

L'ancien incident Tcl provoqué par un environnement Python incompatible n'est pas une procédure normale : le lanceur courant neutralise les variables Tcl/Tk héritées et sélectionne un interpréteur validé.

## 11. Vérifier l'installation techniquement

Facultatif :

```powershell
.venv\Scripts\python.exe -m pga_shootout.gui_preflight --json
.venv\Scripts\python.exe -m pytest -q
```

Guide fonctionnel : [STRATEGY_OPTIMIZER.md](STRATEGY_OPTIMIZER.md). Limites : [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).

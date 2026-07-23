# Interface interactive de recommandation

Lancer l'assistant depuis la racine du projet :

```powershell
pga-shootout recommend-interactive
```

L'interface demande successivement :

1. le sac enregistré à analyser ;
2. le club débloqué à tester, affiché par son nom ;
3. le mode de niveau ;
4. le niveau hypothétique lorsque le mode scénario est choisi.

Le mode **Réel** utilise uniquement les niveaux enregistrés dans l'inventaire. Un niveau absent exclut honnêtement le placement. Le mode **Scénario** demande un niveau explicite et marque les résultats comme hypothétiques.

Les cinq placements sont présentés comme amélioration sans contrepartie, compromis, neutre ou exclu. Chaque résultat conserve les gains, pertes et avertissements du Recommendation Engine, sans score global.

À la fin, répondre `1` pour ouvrir l'Explain d'un placement. L'assistant affiche alors le journal existant pour les cinq positions évaluées de cette composition.

Limites actuelles : le club entrant reste choisi explicitement, l'inventaire complet n'est pas parcouru automatiquement, les niveaux réels ne sont pas encore renseignés et aucune séquence de coups n'est simulée pour les effets différés.

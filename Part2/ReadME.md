# Section 2 — Adapter la boucle en fonction de l’état du système

---

# 1. Pourquoi adapter ?

Dans la Section 1, vous avez observé que :

- votre boucle vise 20 ms,
- mais la durée réelle varie,
- et les variations augmentent quand la charge CPU augmente.

Cela signifie que la stabilité temporelle dépend :

- de votre code,
- mais aussi de l’environnement d’exécution.

Dans un système embarqué réel, on ne subit pas passivement ces variations.

On adapte.

Exemples concrets :

- Un drone réduit le traitement vidéo si le processeur est trop chargé.
- Un robot ralentit un calcul secondaire pour préserver sa boucle de contrôle.
- Une passerelle industrielle désactive des services non critiques en cas de surcharge.

Dans tous ces cas :

> Le système observe son propre état et modifie son comportement.

C’est exactement ce que nous allons faire.

---

# 2. Problème posé

Dans la Section 1, le workload était fixe.

Cela signifie :

- la boucle consomme toujours la même quantité de CPU,
- quelle que soit la situation du système.

Mais si le CPU est déjà très chargé,
continuer à consommer autant peut :

- augmenter le jitter,
- provoquer plus de deadlines manquées.

Nous allons donc tester l’idée suivante :

> Si le système est très chargé, je réduis mon calcul.  
> Si le système est peu chargé, je peux en faire davantage.

---

# 3. Comprendre ce que signifie “charge CPU”

Avant d’adapter, il faut mesurer.

La bibliothèque `psutil` fournit une estimation de la charge CPU :

```python
import psutil
cpu_load = psutil.cpu_percent(interval=None)
```

Cette valeur :

- varie entre 0 et 100,
- représente l’occupation moyenne récente du CPU,
- dépend des autres processus actifs.

Important :

Cette mesure n’est pas parfaite. Elle donne une indication, pas une vérité exacte.

# Exercice 1 — Comprendre la mesure

Répondez :

1. Pourquoi la charge CPU peut-elle varier d’une seconde à l’autre ?
2. Cette valeur représente-t-elle uniquement votre programme ?
3. Pourquoi cette mesure dépend-elle aussi du scheduler ?

---

# 4. Ce que nous allons modifier : le workload

Dans votre boucle, le paramètre :

```bash
workload_ratio
```

contrôle la quantité de calcul interne.

Exemple :

- 0.2 → environ 20 % du budget de 20 ms est utilisé pour calculer
- 0.8 → environ 80 % du budget est utilisé

Plus le workload est élevé :

- plus la boucle est “lourde”
- plus elle risque de dépasser la période

---

# 5. Logique simple d’adaptation

Nous utilisons une règle volontairement simple :

- Si CPU > 70 % → réduire workload
- Si CPU < 40 % → augmenter workload
- Sinon → ne rien changer

Pourquoi ces valeurs ?

Elles sont arbitraires, mais permettent de voir un comportement.

---

# 6. Que signifie “réduire le workload” ?

Si la charge CPU est forte :

- le scheduler doit partager le processeur,
- votre boucle attend plus longtemps,
- le jitter augmente.

En réduisant le calcul interne :

- vous libérez du temps CPU,
- vous augmentez les chances de respecter la période.

Mais vous perdez en performance interne... C’est un compromis !

---

# 7. Expérience 1 — Adaptatif sans stress

Créez à partiru du fichier `rt_loop` un nouveau fichier qui exécutera la boucle adaptative indiquée ci-dessus. En théorie vous n'aurez que des modifications minimes à réaliser sur votre fichier de départ.

```python
python3 rt_loop_adaptive.py --out logs/rt_E_adaptive_nominal.csv
```

Observe :

- comment le workload évolue dans le temps,
- si la valeur reste stable ou fluctue.

# Exercice 2 — Interprétation progressive

1. Le workload reste-t-il constant ?
2. Pourquoi converge-t-il vers une valeur stable ?
3. Si le CPU est peu chargé, pourquoi le workload augmente-t-il ?

--- 

# 8. Expérience 2 — Adaptatif sous stress CPU

Nous allons maintenant reproduire exactement
le scénario qui posait problème dans la Section 1 :

- une boucle périodique de 20 ms
- une charge CPU concurrente

Mais cette fois, la boucle est adaptative.

---

## 8.1 Mise en place

Terminal 1 :

```bash
python3 stress_cpu.py
```
Terminal 2 :

```bash
python3 rt_loop_adaptive.py --out logs/rt_F_adaptive_stress.csv
```

Laissez tourner au moins 2 minutes.

---

# 9. Comment analyser correctement les résultats ?

Dans la Section 1, vous avez appris que :
- la moyenne seule ne suffit pas,
- le maximum observé est important,
- les événements rares sont critiques.

Nous allons maintenant appliquer la même rigueur.

---

## 9.1 Étape 1 — Comparer les moyennes

Comparez :

- jitter moyen (non adaptatif sous stress)
- jitter moyen (adaptatif sous stress)

Question :

Si la moyenne diminue légèrement, mais que le maximum reste élevé, le système est-il réellement plus stable ?

Expliquez.

---

## 9.2 Étape 2 — Examiner les valeurs extrêmes

Observez la valeur maximale du jitter.

Rappel : Le maximum correspond au pire cas observé.

Posez-vous ces questions :

- Ce maximum est-il plus faible qu’avant ?
- Apparaît-il fréquemment ou très rarement ?
- Un seul pic élevé est-il acceptable dans un système critique ?

Reliez votre réponse à la définition du hard real-time vue en Section 1.

---

## 9.3 Étape 3 — Observer l’évolution du workload

Tracez le `workload_ratio` au cours du temps.

Questions guidées :

1. Le workload diminue-t-il rapidement lorsque la charge CPU augmente ?
2. Remonte-t-il lorsque le stress disparaît ?
3. Oscille-t-il autour d’une valeur ?

Essayez d’interpréter ce comportement :

- Pourquoi ne reste-t-il pas constant ?
- Pourquoi ne converge-t-il pas exactement vers une seule valeur fixe ?

---

# 10. Comprendre ce qui se passe réellement

Quand le stress CPU est actif :

- Le scheduler partage le processeur.
- Votre boucle attend plus longtemps.
- La charge CPU mesurée augmente.
- Votre règle d’adaptation réduit le workload.

Réduire le workload signifie :

- Moins de calcul interne.
- Moins de temps CPU consommé.
- Plus de chances de respecter la période.

Mais cela signifie aussi :

- Moins de travail effectué à chaque itération.
- Donc moins de performance interne.
  
Vous venez d’observer un compromis fondamental :

> "Stabilité temporelle ↔ Capacité de calcul"

# 11. Peut-on dire que le système est devenu temps réel ?

C’est une question importante.

Même si :

- le jitter diminue,
- les deadlines manquées diminuent,

le système reste exécuté sous Linux standard.

Donc :

- Le scheduler reste non déterministe.
- Les interruptions matérielles restent présentes.
- Aucune borne maximale formelle n’est garantie.

L’adaptation améliore le comportement observé. Elle ne transforme pas l’OS en système hard real-time.

---

# 12. Discussion approfondie — Ce que vous devez expliquer

Dans votre rapport, vous devez argumenter précisément :

--- 

## 12.1 Sur l’efficacité de l’adaptation

- L’adaptation améliore-t-elle le comportement global ?
- Est-ce visible sur la moyenne ?
- Est-ce visible sur les pires cas ?

## 12.2 Sur le compromis introduit

- Quelle quantité de calcul a été sacrifiée ?
- La stabilité obtenue justifie-t-elle cette perte ?

## 12.3 Sur les limites structurelles

- Pourquoi l’adaptation ne peut-elle pas garantir une borne stricte ?
- Quel élément fondamental reste incontrôlable ?

---

# 13. Comparaison pédagogique avec un RTOS

Imaginons maintenant un système utilisant un OS temps réel strict. Dans un tel système :

- Les priorités sont fixes et absolues.
- La tâche critique peut interrompre toutes les autres.
- Le temps d’exécution maximal peut être analysé théoriquement.
- Une borne de latence peut être démontrée.

Sous Linux standard :

- Les priorités sont relatives.
- Le système vise l’équité globale.
- Les interruptions ne sont pas entièrement maîtrisées.
- Les délais extrêmes ne peuvent pas être bornés formellement.

# 14. Synthèse finale de la Section 2

Vous devez maintenant être capables d’expliquer clairement :

1. Pourquoi l’adaptation réduit le jitter.
2. Pourquoi elle réduit aussi la performance interne.
3. Pourquoi le système reste soft real-time.
4. Pourquoi une architecture temps réel repose d’abord sur l’OS.

Vous avez maintenant :

- observé la variabilité,
- tenté de la corriger,
- compris ses limites fondamentales.

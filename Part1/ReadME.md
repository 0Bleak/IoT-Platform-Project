# Section 1 — Comprendre le comportement temporel d’un système sous Linux

---

# 1. Introduction : qu’est-ce qu’un système temps réel ?

Dans de nombreux systèmes embarqués, certaines tâches doivent respecter
des contraintes temporelles strictes.

Exemples :

- Contrôle moteur d’un drone (toutes les 5 ms)
- Freinage assisté dans un véhicule
- Régulation industrielle
- Synchronisation réseau

Dans ces cas, la question n’est pas :

> “Le programme fonctionne-t-il ?”

Mais :

> “Fonctionne-t-il dans le temps imparti ?”

---

# 2. Définition : système temps réel

Un système temps réel est un système dans lequel :

> La validité d’un calcul dépend non seulement du résultat,
> mais aussi du moment où ce résultat est produit.

On distingue :

### Hard Real-Time
- Une deadline manquée = défaillance du système
- Garantie formelle requise
- Exemples : avionique, contrôle critique

### Soft Real-Time
- Une deadline manquée dégrade la qualité
- Pas de garantie stricte
- Exemples : streaming, supervision

---

# 3. Linux est-il un OS temps réel ?

Linux standard :

- utilise un ordonnanceur généraliste
- optimise débit global et équité
- ne garantit pas de latence maximale bornée

Il est donc :

> Un système généraliste non déterministe.

Cela signifie :

- Les délais peuvent varier
- Il n’y a pas de borne garantie sans configuration spécifique

Pour approfondir :

- https://wiki.linuxfoundation.org/realtime/start
- https://www.kernel.org/doc/html/latest/scheduler/index.html

---

# Exercice 1 — Compréhension conceptuelle

Répondez (quelques lignes) :

1. Quelle est la différence entre hard et soft real-time ?
2. Pourquoi Linux standard n’est-il pas hard real-time ?
3. Un système peut-il être rapide sans être temps réel ?

---

# 4. Objectif expérimental

Nous allons maintenant vérifier expérimentalement
le comportement temporel d’une boucle périodique sous Linux.

Hypothèse initiale :

> Si je demande une période de 20 ms,
> je n’obtiendrai pas exactement 20 ms à chaque itération.

Nous allons mesurer :

- la période réelle
- le jitter
- les deadlines manquées

---

# 5. Mise en œuvre expérimentale : observer le comportement réel

Dans cette partie, vous allez exécuter une boucle périodique déjà implémentée dans le fichier fourni :

- `rt_loop.py`

Votre objectif n’est pas seulement d’exécuter ce script, mais de comprendre :

- ce qu’il fait,
- comment il le fait,
- pourquoi il ne peut pas être parfaitement stable.

---

## 5.1 Organisation des fichiers

Vous disposez des fichiers suivants :

- `rt_loop.py` → boucle périodique + export CSV
- `stress_cpu.py` → générateur de charge CPU
- `analyze_rt.py` → analyse statistique des résultats

Créez un dossier de travail :

```bash
mkdir logs
mkdir figures
```

---

## 5.2 Lecture rapide du code

Avant d’exécuter quoi que ce soit; Ouvrez rt_loop.py et identifiez :

- Où est définie la période cible ?
- Où est mesuré le temps courant ?
- Où est calculé le jitter ?
- Comment est détectée une deadline manquée ?

Expliquez en quelques lignes :

1. Pourquoi utilise-t-on time.monotonic_ns() ?
2. Pourquoi ne pas utiliser time.time() ?

---

## 5.3 Exécution en fonctionnement nominal

Exécutez :

```bash
python3 rt_loop.py --period-ms 20 --duration-s 120 --epsilon-ms 2 --workload-ratio 0.2 --out logs/rt_A_nominal.csv
```

Paramètres :

- `period-ms` : période cible
- `duration-s` : durée d’exécution
- `epsilon-ms` : tolérance de deadline
- `workload-ratio` : part de la période occupée par du calcul

---

## 5.4 Ce que vous devez observer

Même sans stress externe :

- la période réelle varie
- le jitter n’est pas nul
- certaines itérations peuvent dépasser 20 ms

Question fondamentale :

> “Pourquoi existe-t-il du jitter alors qu’aucune charge supplémentaire n’est lancée ?“

Pour ça on peut considérer de nombreux points différents liés au fonctionnement de l'OS :  interruptions système, gestion mémoire, processus système, imprécision de sleep(), etc.

---

# Exercice 2 — Interprétation initiale

1. Comparez la moyenne et le maximum du jitter.
2. Pourquoi la moyenne seule est-elle insuffisante ?
3. Dans un système de contrôle moteur, lequel est le plus critique : moyenne ou maximum ?

---

# 6. Ajouter une perturbation contrôlée

Dans un système embarqué réel, votre tâche critique coexiste avec d’autres tâches.

Simulons cela ! 

---

## 6.1 Lancer une charge CPU

Dans un premier terminal :

```bash
python3 stress_cpu.py --seconds 130
```

Dans un second terminal :

```bash
python3 rt_loop.py --out logs/rt_B_cpu_stress.csv
```

---

## 6.2 Comprendre ce qui se passe

Le scheduler Linux doit maintenant :

- partager le CPU
- interrompre votre boucle
- arbitrer entre plusieurs processus

Le jitter augmente car :

- votre tâche attend plus longtemps
- le réveil n’est plus immédiat
- le système n’est pas déterministe

---

# Exercice 3 — Relier au scheduler

1. Qui décide quel processus s’exécute ?
2. Pourquoi votre programme ne peut-il pas “réserver” le CPU ?
3. Si vous doublez la puissance du processeur, le problème disparaît-il totalement ?

# 7. Modifier la priorité du processus

Sous Linux, chaque processus possède une priorité.

Testez :

```bash
nice -n -10 python3 rt_loop.py --out logs/rt_C_nice.csv
```

---

## 7.1 Que signifie cette commande ?

`nice` modifie la priorité relative. Une priorité plus élevée augmente les chances d’être planifié.

Mais cela ne :

- supprime pas les interruptions matérielles,
- ne garantit pas une latence maximale bornée.

---

# Exercice 4 — Analyse de la priorité

1. Comparez les résultats avec et sans nice.
2. La priorité améliore-t-elle le jitter moyen ?
3. Améliore-t-elle le jitter maximal ?
4. Peut-on garantir une borne ?
  

# 8. Affinité CPU : comprendre les cœurs

Un Raspberry Pi possède plusieurs cœurs. Sans configuration :

> “le système peut déplacer votre processus d’un cœur à l’autre.“

Testez :

```bash
taskset -c 2 python3 rt_loop.py --out logs/rt_D_affinity.csv
```

---

## 8.1 Pourquoi cela peut changer les résultats ?

Une migration entre cœurs peut :

- invalider le cache
- introduire une latence supplémentaire
- perturber le timing

Fixer l’affinité :

- réduit les migrations
- peut stabiliser certaines mesures

---

# Exercice 5 — Comprendre l’affinité

1. Pourquoi le cache CPU peut-il influencer le jitter ?
2. Est-ce toujours bénéfique de fixer l’affinité ?
3. Peut-on isoler complètement un cœur sous Linux standard ?

---

# 9. Analyse comparative obligatoire

Utilisez :

```bash
python3 analyze_rt.py logs/*.csv
```

Vous devez produire :

1. un tableau comparatif des 4 cas
2. au minimum deux graphiques : 1) jitter dans le temps ; 2) distribution du jitter

---

# 10. Discussion finale de la section

Vous devez conclure :

- Linux standard est-il hard real-time ?
- Peut-on garantir une période stricte ?
- Quelle manipulation améliore le plus la stabilité ?
- Quelle est la principale source de variabilité ?

---

# Ce que vous devez avoir compris à la fin de cette section :

- Une période demandée n’est pas une période garantie.
- La moyenne est insuffisante pour caractériser un système temps réel.
- Les événements rares sont critiques.
- Le scheduler est central dans la variabilité.
- Linux standard est adapté au soft real-time, pas au hard real-time.

# Bonus — Fréquence CPU et interférences : au-delà de nice et taskset

---

# 1. Où nous en sommes dans le projet

Vous avez déjà étudié :

- Une boucle périodique 20 ms.
- Le jitter et les deadlines manquées.
- L’effet de la charge CPU.
- L’effet de la priorité (`nice`).
- L’effet du placement CPU (`taskset`).

Ces manipulations agissaient sur :

> L’ordonnancement des processus.

Autrement dit :

- Qui passe en premier ?
- Sur quel cœur s’exécute le programme ?

Mais une dimension n’a pas encore été étudiée :

> À quelle vitesse le CPU fonctionne-t-il réellement ?
> Et combien d’interférences système persistent ?

Ce bonus change donc d’échelle.

---

# 2. Ce que nous avons déjà fait (et ce que nous ne faisons plus)

| Outil | Niveau | Action | Déjà étudié |
|--------|--------|--------|-------------|
| nice | Ordonnanceur | Priorité relative | Oui |
| taskset | Placement | Affinité CPU | Oui |
| DVFS | Matériel | Fréquence CPU | Non |
| Isolation (cset) | Interférences noyau | Réduction du bruit système | Non |

Important :

- `nice` ne change pas la vitesse du CPU.
- `taskset` ne garantit pas l’absence d’interruptions.
- Aucun des deux ne fixe la fréquence matérielle.

Nous allons maintenant travailler :

> au niveau du SoC et du comportement matériel.

---

# 3. Première dimension : la fréquence CPU (DVFS)

## 3.1 Pourquoi la fréquence varie ?

Linux ajuste dynamiquement la fréquence du CPU pour :

- économiser l’énergie,
- réduire la température,
- optimiser la consommation.

Ce mécanisme s’appelle :

DVFS — Dynamic Voltage and Frequency Scaling.

Conséquence :

> La vitesse d’exécution d’un même code peut varier.

Même si :

- la priorité est élevée,
- le cœur est dédié,

si la fréquence change,
le temps d’exécution change.

---

# 4. Expérience 1 — Observer le comportement actuel

Afficher :

```bash
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq
```

Questions :

1. La fréquence est-elle fixe ?
2. Change-t-elle lorsque la charge augmente ?
3. Le gouverneur actuel favorise-t-il performance ou économie ?

# 5. Expérience 2 — Forcer la fréquence

## Mode performance

```bash
sudo cpufreq-set -g performance
```

Relancer la boucle 20 ms.

Mesurer :

- jitter moyen
- jitter max
- miss_rate

## Mode powersave

```bash
sudo cpufreq-set -g powersave
```

Relancer et comparer : est ce que vous observez des différences ?

# 6. Analyse

Répondez :

- Pourquoi le mode performance peut réduire le jitter ?
- Pourquoi powersave peut amplifier les retards ?
- Pourquoi ce phénomène est-il différent de nice ?

# 7. Deuxième dimension : interférences système

Même si :

- la fréquence CPU est fixe,
- votre programme a une bonne priorité,
- il est placé sur un cœur spécifique,

il peut toujours être interrompu par :

- des interruptions matérielles (réseau, timer),
- des threads noyau,
- des services système,
- EdgeX ou Mosquitto.

Ces interruptions peuvent provoquer :

- un retard ponctuel,
- une itération de la boucle qui dure plus longtemps,
- une deadline manquée.

---

## 7.1 Comprendre le phénomène

Dans vos mesures de jitter, vous avez peut-être observé :

- un jitter moyen faible (ex : 0.3 ms),
- mais parfois un pic brutal (ex : 6 ms).

Ces pics ne sont pas la norme, mais ils existent.

On appelle cela :

> des retards exceptionnels.

Ce ne sont pas des erreurs constantes, mais des perturbations ponctuelles.

C’est souvent ce type de retard qui provoque les deadlines manquées.

---

## 7.2 Visualiser ce phénomène

Tracez l’évolution du jitter en fonction du temps.

Vous pouvez observer :

- une ligne relativement stable,
- et parfois un pic isolé.

Ces pics correspondent à des interférences système. L’objectif de l’isolation CPU est de :

> réduire la fréquence et l’amplitude de ces pics.

---

# 8. Expérience 3 — Isolation CPU

Installer :

```bash
sudo apt install cset
```

Créer un cœur protégé (ex : CPU 2) :

```bash
sudo cset shield --cpu 2 --kthread=on
```

Exécuter la boucle sur ce cœur :

```bash
sudo cset shield --exec -- python3 rt_loop_measure.py
```


## 8.1 Ce que vous devez observer

Comparez :

- jitter moyen
- jitter maximal
- nombre de deadlines manquées

Question importante :

1. Les pics extrêmes diminuent-ils ?
2. La variabilité globale est-elle plus stable ?

## 8.2 Interprétation

Même si la moyenne change peu, une réduction des pics importants peut fortement améliorer la stabilité globale.

Dans un système embarqué : ce sont souvent les retards exceptionnels qui posent problème, plus que la moyenne elle-même.


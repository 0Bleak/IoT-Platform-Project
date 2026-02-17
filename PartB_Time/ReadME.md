# Bonus — Le temps global dans votre architecture Edge

---

# 1. Pourquoi ce bonus arrive maintenant ?

Dans les premières parties du projet, vous avez étudié :

1. Le temps local (jitter, deadline, périodicité 20 ms).
2. L’adaptation locale (réduction de charge).
3. L’intégration EdgeX + MQTT + policy-controller.

À ce stade, votre système fonctionne.

Mais une hypothèse implicite n’a jamais été vérifiée :

> Les différentes machines partagent-elles la même référence temporelle ?

Or, votre système repose sur des timestamps :

- les métriques envoyées contiennent un temps,
- EdgeX stocke les événements avec un champ `origin`,
- le policy-controller prend des décisions basées sur ces événements.

Nous allons maintenant examiner le **temps global**.

---

# 2. Schéma global : où intervient le temps ?

              ┌──────────────────────┐
              │  Raspberry Device A  │
              │  Boucle 20 ms        │
              │  Horloge locale A    │
              └──────────┬───────────┘
                         │
                         │ MQTT (timestamp A)
                         ▼
              ┌──────────────────────┐
              │        EdgeX         │
              │  Core Data           │
              │  Stockage événements │
              └──────────┬───────────┘
                         ▲
                         │ MQTT (timestamp B)
                         │
              ┌──────────┴───────────┐
              │  Raspberry Device B  │
              │  Boucle 20 ms        │
              │  Horloge locale B    │
              └──────────────────────┘

Si horloge A ≠ horloge B :

- Les événements peuvent être ordonnés incorrectement.
- Les comparaisons temporelles peuvent être fausses.
- Une décision distribuée peut devenir incohérente.

Dans un système embarqué distribué, la cohérence temporelle est une hypothèse forte.

---

# 3. Comprendre le problème physique

## 3.1 Une horloge embarquée, c’est quoi ?

Chaque Raspberry Pi possède un quartz matériel.

Ce quartz oscille à une fréquence nominale (ex : 19,2 MHz).
Mais :

- la fréquence réelle varie légèrement,
- la température influence cette fréquence,
- deux quartz n’oscillent jamais exactement de la même façon.

Le système d’exploitation construit une horloge logicielle à partir de cette oscillation.

---

## 3.2 Dérive (drift)

Si deux machines démarrent à la même seconde :

- Après quelques minutes, elles ne seront plus parfaitement alignées.

Ordre de grandeur typique :

- 10 à 50 ppm (parts per million)
- ≈ 1 ms de dérive par minute (ordre de grandeur)

La dérive est lente, mais permanente.

---

## 3.3 Offset

L’offset est la différence instantanée entre deux horloges.

Exemple :

- Device A : 100.000 s
- Device B : 100.006 s  

Offset = 6 ms

Dans votre architecture, 6 ms d’écart peuvent modifier l’ordre apparent des événements.

---

# 4. Ce que fait NTP dans votre système actuel

Par défaut, vos Raspberry utilisent NTP.

NTP (Network Time Protocol) :

- synchronise l’horloge via réseau IP,
- estime délai aller-retour,
- corrige progressivement l’heure,
- précision typique : millisecondes.

Dans votre architecture Wi-Fi :

- NTP maintient une cohérence approximative.
- Mais la précision dépend du jitter réseau.

Question importante :

> Cette précision est-elle suffisante pour votre système ?

---

# 5. Pourquoi parler de PTP ?

On va chercher à présent à aller plus loin que la solution mise en place de façon standard dans ces environnements en s'intéressant à un autre protocole PTP (Precision Time Protocol) qui  est conçu pour :

- réseau local Ethernet,
- précision microseconde,
- synchronisation plus fine.

Il est utilisé en :

- industrie,
- télécommunications,
- systèmes embarqués distribués.

La question ici n’est pas :
> Est-ce plus précis ? Ce qui estune certitude....

Mais :

> Est-ce nécessaire dans votre architecture ?

---

# 6. Expérience guidée

Les fichiers suivants sont déjà fournis dans le dossier du projet :

- `server_time.py`
- `client_time.py`

Vous n’avez pas à les écrire. Votre travail est de comprendre ce qu’ils mesurent.

---

# Étape 1 — Observer l’état actuel

Sur chaque Raspberry :

```bash
timedatectl status
```

Vérifiez si NTP est actif. Afficher l’heure :

```bash
watch -n 1 date +%s.%N
```

Comparer visuellement les deux machines.

Questions :
- L’écart est-il visible ?
- Est-il stable ?

---

# Étape 2 — Mesure d’offset avec les scripts fournis

Lancer :

- `server_time.py` sur Machine A
- `client_time.py` sur Machine B

Le script calcule :

```bash
offset = t_local − t_remote
```

Ce que vous mesurez réellement :

> offset ≈ (horloge B − horloge A) + délai réseau

Sur Ethernet local, le délai réseau est très faible à l’échelle milliseconde.

Laisser tourner 2–3 minutes.

Pour avoir une meilleure visibilité des choses vous pouvez éventuellement tracer : offset en fonction du temps.

Ceci pourrait vous permettre d'analyser différents éléments :

- offset moyen
- stabilité
- variation maximale

Ok et derrière si on essaie d'appliquer cela à un vrai système ?

Si cet offset existait dans votre architecture Edge, quel serait l’impact ?

---

# Étape 3 — Désactiver NTP

Sur les deux machines :

```bash
sudo systemctl stop systemd-timesyncd
```

Relancer la mesure.

Observer :

- évolution progressive de l’offset,
- apparition éventuelle d’une dérive.

---

# Étape 4 — Ethernet + PTP

Relier les deux Raspberry en Ethernet direct. Configurer des adresses IP compatibles si nécessaire.

Installer :

```bash
sudo apt install linuxptp
```

Machine maître :

```bash
sudo ptp4l -i eth0 -m
```

Machine esclave :

```bash
sudo ptp4l -i eth0 -m
sudo phc2sys -s eth0 -c CLOCK_REALTIME -m
```

Observer :

- offset en microsecondes,
- convergence,
- stabilité.

Relancer ensuite la mesure avec `server_time.py / client_time.py.`

Comparer :

- dérive libre
- NTP
- PTP

---

# 7. Lien direct avec votre projet

Posez-vous les questions suivantes :

- Votre boucle locale 20 ms dépend-elle d’une synchronisation globale ?
- Le policy-controller compare-t-il des événements provenant de plusieurs devices ?*
- À partir de combien de millisecondes d’erreur l’ordre devient problématique ?
- Votre système actuel exploite-t-il réellement une précision microseconde ?

---

# 8. Message pédagogique clé

Dans la première partie du projet, vous avez étudié :

> Le temps local.

Dans cette partie, vous étudiez :

> La cohérence temporelle globale.

Un système embarqué distribué doit maîtriser :

- la stabilité locale (jitter),
- la latence réseau,
- la sécurité,
- la gestion CPU,
- et la synchronisation temporelle.

---

# 9. Discussion finale

- PTP est-il nécessaire dans votre architecture actuelle ?
- Dans quel type d’application deviendrait-il indispensable ?
- Est-il cohérent d’avoir une synchronisation microseconde si le reste du système (MQTT, EdgeX, Wi-Fi) est non déterministe ?

# 10. Conclusion

Vous venez de relier :

- matériel (quartz),
- système d’exploitation,
- réseau,
- middleware (EdgeX),
- architecture distribuée.

Ce que l'on a cherché à mettre en évidence est le fait que le temps n’est pas seulement une variable locale. C’est une variable d’architecture.

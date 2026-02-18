# Projet M2 – Systèmes Embarqués Edge et Contraintes Temporelles

On va sur les prochains jours chercher à mener de bout en bout un projet de mise en oeuvre d'une infrastructure IoT en s'intéressant notamment à comment mettre en oeuvre des noeuds embarqués susceptibles (ou non) de garantir des performances temps réel.

Les objectifs derrière vont donc être multiples : comprendre ce que l'on entend par temps réel, comprendre comment on "embarque" une application Edge, comprendre comment on sécurise une chaine de bout en bout et comprendre le rôle du noeud de contrôle sur les devices terminaux.

## 1. Pourquoi ce projet ?

Les systèmes embarqués modernes ne sont plus isolés. On les retrouve dans de nombreux contextes, qu'il s'aggise de :

- robots industriels,
- véhicules connectés,
- systèmes ferroviaires,
- passerelles industrielles (Industry 4.0),
- micro-data centers edge (e.g. destinés à des contextes IoT dans lesquels on va vouloir contrôler des capteurs météo ou autres).

Ces systèmes (en prenant individuellement chacun des noeuds évoqués ci-dessus) doivent simultanément :

1. Exécuter des fonctions locales contraintes temporellement, type gérer son déplacement dans l'espace pour un véhicule connecté ou contrôler l'état des voies pour un système ferroviaire  
2. Être supervisés à distance, qu'il s'agisse juste de visualiser leur état ou de les contrôler   
3. Communiquer via des protocoles standardisés, ce qui peut permettre de changer côté gestion le système utilisé tout en restant transparent pour les devices terminaux  
4. Respecter des contraintes énergétiques : que ce soit un véhicule ou un micro data center on a des contraintes énergétiques fortes  

Le problème fondamental est le suivant :

> Comment maintenir une exécution locale stable (contraintes temporelles)
> tout en intégrant une architecture IoT distribuée non déterministe (ie qui peut introduire des délais non prévus/non systématiques) ?

Dans ce projet on va chercher à analyser de tels scénarios...

Un exemple dans le ferroviaire ? https://chance5g.ch/fr/articles/voici-comment-la-5g-contribue-a-la-securite-du-transport-ferroviaire/ 

---

## 2. Architecture type des systèmes modernes

Dans l’industrie, une architecture courante ressemble à ceci :

Devices (nœuds embarqués) ---> Edge Gateway ---> Cloud (optionnel - pour les scénarios IoT et Industry décrits au dessus par exemple ce n'est pas nécessaire !)

Chaque **device** (noeud terminal type véhicule ou autre) :

- exécute une fonction locale critique
- collecte des métriques (charge, état système, etc.)
- publie des données vers une passerelle

La **gateway edge** :

- reçoit les données
- les organise
- applique des règles
- fournit une interface de supervision

Dans ce projet on va considérer le système suivant :

- 4 Raspberry Pi représenteront des devices embarqués
- 1 Raspberry Pi représentera la gateway edge

---

## 3. Mise en œuvre dans ce projet

Chaque device exécutera :

- une boucle locale périodique (≈ 20 ms)
- un mécanisme d’adaptation basé sur l’état système (charge CPU)
- une estimation énergétique simplifiée
- une publication périodique vers la gateway (≈ 200 ms)

La gateway :

- collectera les données
- les structurera
- permettra leur visualisation
- servira de plateforme de supervision

Le réseau utilisé sera le Wi-Fi afin d’introduire une variabilité réaliste.

---

## 4. Technologies utilisées et rôle de chacune

### Linux (Raspberry Pi)

- Système d’exploitation standard en embarqué moderne
- Non temps réel strict
- Permet d’étudier la variabilité d’exécution

Documentation :
- https://www.kernel.org/
- https://wiki.linuxfoundation.org/realtime/start

---

### MQTT

- Protocole léger de publication/abonnement
- Très utilisé en IoT industriel

Documentation :
- https://mqtt.org/
- https://www.hivemq.com/mqtt-essentials/

---

### EdgeX Foundry

EdgeX est une plateforme open-source de gestion de données pour systèmes edge.

Elle fournit :

- gestion de devices
- ingestion de données
- bus de messages interne
- règles et transformations
- interface web

Elle représente une **gateway industrielle réaliste**.

Documentation :
- https://www.edgexfoundry.org/
- https://docs.edgexfoundry.org/


---

## 5. Objectifs pédagogiques

Ce projet a pour objectif de permettre aux étudiants de :

### 1️⃣ Comprendre les limites du soft real-time sous Linux

- variabilité d’exécution
- jitter
- deadlines manquées
- impact des charges concurrentes

---

### 2️⃣ Comprendre la séparation contrôle local / supervision edge

- la boucle critique doit rester locale
- la plateforme edge est non déterministe
- le réseau introduit de la variabilité

---

### 3️⃣ Étudier les compromis systeme / performance

- stabiliser une boucle est possible ?
- quelles métriques sont réellement significatives ?

---

### 4️⃣ Comprendre l’impact d’une architecture IoT réelle

- sur la latence
- sur la variabilité
- sur la complexité système

---

## 6. Question centrale

À la fin du projet, vous devrez être capables de répondre à :

> Peut-on maintenir une boucle locale stable sous Linux ? Quelle différence entre soft real time et hard real time ? Pourquoi ces concepts ?
> Comment est ce qu'on intègre une plateforme Edge industrielle ?
> Quelles sont les limites fondamentales de cette architecture ?

---

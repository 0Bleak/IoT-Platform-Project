# Section Bonus 2 — KubeEdge : orchestration Edge « réaliste » autour d’EdgeX

---

## 1) Pourquoi ajouter KubeEdge maintenant ?

Jusqu’ici, votre système fonctionne sur une gateway unique :

- Mosquitto (transport MQTT)
- EdgeX (plateforme)
- des devices (Raspberry) qui publient des métriques et reçoivent une commande

C’est déjà une architecture Edge complète.  
Mais dans un contexte industriel (ou “smart factory”), on veut souvent :

- **déployer** et **mettre à jour** des services facilement (EdgeX, scripts, règles),
- **monitorer** l’état des nœuds,
- **orchestrer** des composants sur plusieurs gateways (pas une seule),
- isoler et versionner l’exécution (conteneurs / pods).

KubeEdge apporte une réponse “Kubernetes-compatible” :

> Garder un contrôle “cloud-like” (K8s) tout en exécutant au bord (edge).

Ce bonus n’est **pas** pour “faire du Kubernetes pour faire du Kubernetes”.

Il sert à comprendre ce que change une couche d’orchestration sur :
- le déploiement,
- la robustesse,
- et potentiellement les performances.

---

## 2) Ce qu’est KubeEdge (explication simple)

KubeEdge étend Kubernetes pour des nœuds edge potentiellement :

- intermittents,
- derrière du NAT,
- avec connectivité variable,
- moins puissants.

Architecture minimale :

- **CloudCore** (côté “cloud/contrôle”) : équivalent contrôle K8s + gestion edge
- **EdgeCore** (sur la gateway edge) : agent local qui exécute les workloads

Dans ce bonus :

- la gateway devient un nœud edge KubeEdge
- EdgeX et Mosquitto sont déployés “comme workloads” (au moins partiellement)

---

## 3) Objectifs pédagogiques du bonus

Vous devez être capables de répondre :

1. Qu’est-ce que KubeEdge apporte par rapport à “docker compose sur la gateway” ?
2. Qu’est-ce que KubeEdge complique ?
3. Est-ce que l’orchestration introduit une charge ou une variabilité mesurable ?
4. Quelle serait une architecture multi-gateway réaliste (même sans l’implémenter) ?

---

## 4) Organisation proposée (réaliste en TP)

### Option A (recommandée, faisable en 20h)
- **Gateway = Edge node KubeEdge**
- KubeEdge sert à déployer :
  - Mosquitto
  - un “service de règles” (petit pod Python qui lit EdgeX et envoie SetMode)
- EdgeX reste en docker compose (pour limiter la complexité), mais on observe l’intégration.

➡️ But : comprendre l’intérêt d’orchestrer *un sous-ensemble* utile sans tout casser.

### Option B (plus ambitieuse)
- Déployer EdgeX complet sur KubeEdge (plusieurs microservices).
➡️ Plus proche du “vrai monde”, mais risqué/long.

Dans ce TP, on privilégie **Option A**.

---

## 5) Mise en place (niveau guidé)

### 5.1 Rôles machines
- 1 machine “contrôle” (peut être un PC Linux ou un Raspberry plus puissant) : **CloudCore**
- 1 gateway Raspberry : **EdgeCore** + workloads
- Les devices restent inchangés (publient metrics / reçoivent cmd)

> Si vous n’avez pas de machine contrôle dédiée, l’enseignant fournit un CloudCore préinstallé.

---

### 5.2 Ce que vous allez déployer via KubeEdge

Deux workloads simples :

#### (1) Mosquitto en Pod
- un service stable
- facile à tester
- permet de discuter : “orchestration vs performance”

#### (2) “Policy Controller” en Pod
Un petit service qui :
- lit les derniers events EdgeX (API)
- décide `NORMAL` vs `DEGRADED`
- appelle Core Command (EdgeX) pour envoyer `SetMode`

> C’est une boucle de retour “supervision/orchestration” typique.

---

## 6) Déploiement Mosquitto (manifest minimal)

Fichier fourni : `mosquitto-deploy.yaml`

Objectif :
- 1 Deployment
- 1 Service NodePort
- port 1883 exposé sur la gateway

Commandes :

```bash
kubectl apply -f mosquitto-deploy.yaml
kubectl get pods -o wide
kubectl get svc
```

Test depuis un device :

```bash
mosquitto_pub -h IP_GATEWAY -p <NODEPORT> -t test/topic -m "hello"
```

# 7) Déploiement du “Policy Controller” (manifest + code)

Fichiers fournis :

- `policy_controller.py`
- `policy-controller-deploy.yaml`

Le service fait (toutes les 1 s) :

1. `GET` sur EdgeX Core Data (dernier event device1)
2. extraction miss_rate
3. décision :
  - si miss_rate > seuil → `DEGRADED`
  - sinon → `NORMAL`
4. `PUT` sur EdgeX Core Command SetMode



Commandes :

```bash
kubectl apply -f policy-controller-deploy.yaml
kubectl logs -f deploy/policy-controller
```

----

# 8) Expérience demandée

## Expérience 1 — “sans KubeEdge”

- Mosquitto en service systemd (gateway)
- policy controller lancé à la main (python)

Mesurer :
- CPU gateway
- latence réaction SetMode (approx)
- stabilité

# Expérience 2 — “avec KubeEdge”

- Mosquitto en pod
- policy controller en pod

Mesurer les mêmes éléments.

Questions :

1. Est-ce plus simple à déployer / relancer ?
2. Est-ce que l’overhead est visible ?
3. Quelle approche est préférable sur une gateway contrainte ?

----

# 9) Discussion critique 

Répondez :

1. Pourquoi KubeEdge a du sens au bord alors que Kubernetes “pur” est souvent trop lourd ?
2. Qu’est-ce que vous gagnez concrètement avec la mise en place de cette architecture ici ? Qu’est-ce que vous perdez (complexité, debugging, overhead) ?
3. Si vous aviez 3 gateways, comment répartiriez-vous EdgeX / Mosquitto / policy controller ?
4. Est-ce que l’orchestration peut perturber la stabilité temporelle des devices (indirectement) ?

----


# Section Bonus 1 — Sécurité de l’architecture Edge distribuée

---

# 1. Pourquoi parler de sécurité ici ?

Jusqu’à présent, vous avez étudié :

- la stabilité temporelle (Section 1),
- l’adaptation locale (Section 2),
- l’architecture distribuée (Section 3).

Mais votre système actuel présente une faiblesse majeure :

Il fonctionne.

Il n’est pas sécurisé.

Dans un contexte industriel, un système fonctionnel mais non sécurisé
est un système inacceptable.

Avant d’ajouter des mécanismes de protection,
il faut d’abord comprendre :

> Quelles sont les surfaces d’attaque de notre architecture ?

---

# 2. Cartographie des surfaces d’attaque

Reprenons la chaîne complète :

Device → MQTT → Mosquitto → device-mqtt → EdgeX → commande → device

Chaque élément introduit une surface d’exposition.

---

## 2.1 Broker MQTT

Problème actuel :

- MQTT fonctionne en clair.
- Aucun contrôle d’accès.
- Tout client sur le réseau peut publier.
- Tout client peut s’abonner.

Conséquences possibles :

- Injection de fausses métriques.
- Injection de fausses commandes.
- Saturation du broker (DoS simple).
- Observation passive des messages.

---

## 2.2 API EdgeX (Core Command)

Si EdgeX est en mode sans sécurité :

- Toute machine peut appeler l’API REST.
- Les commandes ne sont pas authentifiées.
- Aucun contrôle d’identité.

Cela signifie :

- Un attaquant peut piloter vos devices via curl.
- Il peut forcer un mode dégradé permanent.
- Il peut provoquer des oscillations.

---

## 2.3 Réseau Wi-Fi

Le Wi-Fi introduit :

- un canal partagé,
- une exposition radio,
- des risques d’écoute passive.

Sans chiffrement applicatif :

- Les données MQTT sont lisibles.
- Les commandes sont lisibles.
- Un attaquant peut rejouer un message.

---

# 3. Menaces concrètes à simuler

Avant d’ajouter des protections, vous devez comprendre le risque.

---

## Expérience 1 — Injection non autorisée

Depuis un autre Raspberry :

```bash
mosquitto_pub -h IP_GATEWAY -t "tp/device1/cmd" -m '{"Mode":"DEGRADED"}'
```

Si le device change de mode :

→ Le système est vulnérable.

---

# Expérience 2 — Saturation simple

Envoyer en boucle :

```bash
while true; do mosquitto_pub -h IP_GATEWAY -t "tp/device1/metrics" -m "spam"; done
```

Observer :

- Charge CPU de la gateway.
- Stabilité du broker.
- Impact sur device-mqtt.

Vous venez de simuler un déni de service trivial.

---

# 4. Sécurisation progressive (approche raisonnée)

Nous allons ajouter des protections par niveaux :

Niveau 1 — Authentification MQTT
Niveau 2 — Restriction d’accès API EdgeX
Niveau 3 — Chiffrement TLS
Niveau 4 — Réflexion sur la robustesse système

---

# 5. Niveau 1 — Authentification MQTT

Objectif :

> Empêcher qu’un client non autorisé publie sur le broker.

---

# 5.1 Configuration Mosquitto

Créer un fichier de mots de passe :

```bash
sudo mosquitto_passwd -c /etc/mosquitto/passwd deviceuser
```

Modifier `/etc/mosquitto/mosquitto.conf` :

```bash
allow_anonymous false
password_file /etc/mosquitto/passwd
```

Redémarrer :

```bash
sudo systemctl restart mosquitto
```

## 5.2 Adapter les devices

Dans le code Python :

```bash
client.username_pw_set("deviceuser", "motdepasse")
```

Test :

- Publication sans mot de passe → échec.
- Publication avec mot de passe → succès.

---

## 5.3 Ce que cela protège

Empêche un client anonyme d’injecter des messages.

Ne protège pas contre l’écoute passive.

Ne chiffre pas le trafic.

---

# 6. Niveau 2 — Restriction d’accès à l’API EdgeX

Objectif :

> Limiter qui peut appeler Core Command.

## 6.1 Restriction via firewall (solution simple)

Activer UFW :

```bash
sudo ufw allow from 192.168.1.0/24 to any port 59882
sudo ufw enable
```

Maintenant :

> Seules les machines du réseau local peuvent appeler Core Command.

## 6.2 Limites

Pas d’authentification utilisateur.

Pas de journalisation par identité.

Protection périmétrique seulement.

# 7. Niveau 3 — Chiffrement TLS (discussion)

Pour protéger : confidentialité, intégrité, authentification forte, ce qui constitue les bases de la plupart des systèmes de sécurité, il faudrait :

- activer MQTT over TLS,
- générer des certificats,
- configurer EdgeX en mode sécurisé.

Impact :

1.  Augmentation de la complexité.
2. Légère augmentation de latence.
3. Charge CPU supplémentaire (chiffrement).

Question à discuter :

> Dans un système soft real-time, quel est le compromis acceptable ?

# 8. Sécurité vs performance

Chaque mécanisme ajouté 
- augmente la charge CPU,
- augmente la latence,
- complexifie le débogage.

Vous devez analyser :

1. L’authentification MQTT augmente-t-elle le jitter ?
2. Le chiffrement TLS aurait-il un impact mesurable ?
3. La sécurité est-elle gratuite ?

# 9. Sécurité et architecture

Un point fondamental : La sécurité ne peut pas être ajoutée à la fin.

Elle doit être pensée dès la conception, c'est pour ça qu'aujourd'hui le terme de `Security by design` prend beaucoup de place :
- séparation des plans,
- limitation des dépendances,
- réduction des surfaces exposées,
- principe du moindre privilège.

Dans votre architecture :

1. La boucle critique reste locale.
2. Elle ne dépend pas du réseau.
3. Elle reste fonctionnelle même si EdgeX tombe.
4. C’est déjà une forme de robustesse.

# 10. Discussion finale

Expliquez :

- Quelle est la principale vulnérabilité de votre système initial ?
- Quelle protection apporte l’authentification MQTT ?
- Pourquoi le chiffrement n’est pas activé ici ?
- Comment concilier sécurité et contraintes temps réel ?
- Un système sécurisé peut-il être déterministe ?

# 11. Conclusion

Vous venez d’ajouter une dimension essentielle :
> Performance + Architecture + Sécurité

Un système embarqué industriel doit équilibrer :

- stabilité temporelle,
- capacité de calcul,
- supervision distribuée,
- robustesse face aux attaques.

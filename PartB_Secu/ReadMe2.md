# Bonus Sécurité — Intégrité applicative par signature HMAC

---

## 1) Pourquoi ajouter une signature HMAC alors qu’on a déjà un mot de passe MQTT ?

L’authentification Mosquitto (user/password) protège surtout :
- l’accès au broker (qui peut publier/s’abonner).

Mais elle ne garantit pas, à elle seule, que :
- les messages n’ont pas été modifiés en transit,
- les messages viennent bien d’un device précis (au niveau applicatif),
- les commandes n’ont pas été forgées par un autre client authentifié (si identifiants compromis).

Une signature HMAC apporte :
- **Intégrité** : détecter une modification du message.
- **Authenticité partagée** : seul quelqu’un avec la clé peut signer.

Hypothèse : device et gateway partagent un secret `K_device1`.

---

## 2) Rappel minimal : qu’est-ce qu’un HMAC ?

- HMAC = “Hash-based Message Authentication Code”
- Entrées : une clé secrète `K` + un message `m`
- Sortie : un tag `t = HMAC(K, m)`
- Vérification : on recalcule `t` et on compare.

Propriétés utiles :
- si le tag ne vérifie pas → message rejeté
- un attaquant sans la clé ne peut pas forger un tag valide

Référence (optionnel) :
- https://datatracker.ietf.org/doc/html/rfc2104

---

## 3) Où placer HMAC dans notre architecture ?

### 3.1 Remontée (metrics)
Device publie un JSON signé :
- payload + metadata (timestamp, nonce, device_id)
- signature HMAC calculée sur un “message canonique”

Gateway vérifie :
- signature
- fraîcheur (timestamp)
- anti-rejeu (nonce)

### 3.2 Retour (commande `SetMode`)
Optionnel (mais cohérent) :
- Gateway signe les commandes
- Device rejette toute commande non signée ou rejouée

> Dans votre projet, le retour “via EdgeX” passera toujours par MQTT in fine.
> Vous pouvez signer les messages qui sortent vers le topic `tp/device1/cmd`.

---

## 4) Définir une convention simple (très important)

Pour que tout le monde signe la même chose, on standardise :

### 4.1 Structure de message (metrics)
```json
{
  "device_id": "device1",
  "ts_ms": 1730000000000,
  "nonce": "b3f1a9c2",
  "data": {
    "jitter_ms": 1.2,
    "miss_rate": 0.01,
    "workload": 0.35
  },
  "hmac": "..."
}
```

---

### 4.2 Canonicalisation : comment produire la chaîne signée ?

On signe le JSON sans le champ `hmac`, en triant les clés.

En Python : `json.dumps(obj, separators=(",", ":"), sort_keys=True)`

Cela évite les erreurs “ça ne vérifie pas” dues à l’ordre des champs.

5) Clé partagée (TP)

Pour le TP, on utilise une clé simple stockée dans un fichier local :

Sur chaque device :

- `secrets/device1.key`

Sur la gateway (vérification) :

- `secrets/device1.key`

Dans la pratique, stocker une clé en clair est faible. En production, on utiliserait un coffre à secrets / TEE / secure element.

---

# 6) Code fourni — Signature côté device (metrics)

Fichier fourni : `hmac_sign.py` (utilisé par `device_loop_with_mqtt.py`)

Dans la boucle device (toutes les 200 ms) :
```python
key = load_key()
msg = make_metrics_message("device1", data_dict, key)
client.publish("tp/device1/metrics", json.dumps(msg))
```

---

# 7) Code fourni — Vérification côté gateway

Fichier fourni : `hmac_verify.py`

Dans un script de vérification (gateway) : 
- on s’abonne au topic tp/device1/metrics
- on parse JSON
- on vérifie HMAC + fraîcheur
- sinon on rejette

---

# 8) Anti-rejeu minimal (nonce)

Même avec HMAC, un attaquant peut rejouer un message capturé.

Contre-mesure simple :

- conserver les derniers nonce vus sur une fenêtre (ex. 1000 derniers)
- rejeter les nonces déjà vus

> Pour le TP : vous stockez en mémoire une structure set() de nonces, purgée régulièrement.

---

# 9) Expériences 

## Expérience 1 — Injection non signée

Publiez un message “au format metrics” mais sans hmac correct.
→ le gateway doit le rejeter.

## Expérience 2 — Altération d’un message

Prenez un vrai message signé, modifiez `workload` et republiez.
→ la vérification doit échouer.

## Expérience 3 — Rejeu

Rejouez exactement le même message (même nonce).
→ la vérification HMAC passe, mais la protection anti-rejeu doit le rejeter.

---

# 10) Discussion : ce que HMAC fait et ne fait pas

HMAC fait :
- détecter l’altération
- empêcher la forge sans clé
- ajouter une couche de confiance applicative

HMAC ne fait pas :

- chiffrer (confidentialité)
- empêcher l’écoute passive
- empêcher le DoS

Question finale :

- Dans quelle mesure HMAC améliore-t-il la robustesse du système ?
- Pourquoi le hard real-time reste impossible malgré ces protections ?

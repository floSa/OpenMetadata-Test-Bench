# Chapitre 02 — Installer et comprendre la stack

> **Objectifs** — Démarrer l'environnement complet, savoir ce que fait chaque
> conteneur, et savoir où regarder quand ça ne marche pas.
> **Durée** — 30 minutes, dont 10 de téléchargement au premier lancement.

---

## 1. Ce qu'on démarre

`./omlab up` lance sept conteneurs. Ce n'est pas une usine à gaz : chacun a
un rôle précis, et les connaître fait gagner un temps considérable au moment
du premier problème.

```mermaid
flowchart TD
  nav([Navigateur]) -->|":8585"| server["<b>openmetadata-server</b> :8585<br/>l'API REST + l'interface web"]
  migrate["<b>execute-migrate-all</b><br/>joue les migrations, puis sort"] -.->|avant le démarrage| pg
  server --> pg[("<b>postgresql</b> :5432<br/>la vérité (entités)")]
  server --> es[("<b>elasticsearch</b> :9200<br/>la recherche (l'index)")]
  server --> ing["<b>ingestion</b> :8080<br/>Airflow, exécute les workflows"]
  ing -->|interroge| play[("<b>omlab-postgres</b> :5433<br/>LE TERRAIN DE JEU<br/>schémas raw et analytics")]
  server -->|"alertes (ch. 12)"| hook["<b>omlab-webhook</b> :8010<br/>reçoit les alertes"]
```

### Les deux Postgres, et pourquoi on s'y perd

C'est la confusion numéro un du tutoriel, alors autant la lever tout de suite :

| | `openmetadata_postgresql` | `omlab_postgres` |
|---|---|---|
| Rôle | base **interne** d'OpenMetadata | base **à cataloguer** |
| Contient | les entités, les tests, l'historique | des clients, des commandes |
| Port hôte | 5432 | **5433** |
| Nom réseau | `postgresql` | `omlab-postgres` |
| On y touche | jamais | tout le temps |

Le second n'existe que dans ce tutoriel : dans la vraie vie, c'est votre
entrepôt.

### Postgres et Elasticsearch : deux sources, deux rôles

OpenMetadata écrit **deux fois** chaque entité : dans Postgres, qui fait foi,
et dans Elasticsearch, qui sert la recherche. Conséquence pratique que vous
rencontrerez : une entité créée par l'API apparaît immédiatement par son FQN,
mais peut mettre un instant à sortir dans la barre de recherche. Ce n'est pas
un bug, c'est de l'indexation asynchrone. Si les deux divergent durablement,
on réindexe (chapitre 16).

## 2. Prérequis

| | Minimum | Ce qu'on a vérifié ici |
|---|---|---|
| Docker | 20.10+ | 29.9.2 |
| Docker Compose | v2.1.1+ | v5.6.1 |
| RAM allouée à Docker | 6 Gio | 31 Gio |
| vCPU | 4 | 12 |
| Disque | ~15 Go | — |

**Sous Windows :** travaillez depuis un terminal **WSL**, avec le dépôt dans le
système de fichiers Linux (`~/Projets/...`), pas dans `/mnt/c` ni via
`\\wsl.localhost`. Les conteneurs montent des dossiers de ce dépôt ; depuis un
chemin Windows, les montages échouent ou deviennent extrêmement lents. Vérifiez
aussi que l'intégration WSL est active dans Docker Desktop
(*Settings → Resources → WSL Integration*).

## 3. Démarrage

```bash
cp .env.example .env
./omlab up
```

Au premier lancement, comptez environ **5 Go d'images** à télécharger. Le
script attend ensuite que le serveur réponde, et affiche les accès :

```
OpenMetadata répond : {"version":"2.0.7","revision":"744c523...","timestamp":...}

  UI OpenMetadata : http://localhost:8585          (admin@open-metadata.org / admin)
  Airflow         : http://localhost:8080          (admin / admin)
  Playground PG   : localhost:5433                 (omlab / omlab_pwd, base omlab)
  Webhook de test : http://localhost:8010/
```

Puis récupérez le jeton dont tous les TP ont besoin :

```bash
./omlab token
```

### Les deux jetons, et pourquoi ça compte

`./omlab token` va chercher le jeton de l'**`ingestion-bot`**, pas celui de
l'administrateur. La différence est de taille :

- le jeton de session d'un humain expire au bout d'une heure, et la 2.0 limite
  chaque compte à cinq sessions ouvertes (`AUTHENTICATION_MAX_ACTIVE_SESSIONS_PER_USER`) ;
- le jeton de l'`ingestion-bot` n'a pas de date d'expiration (`JWTTokenExpiry: Unlimited`),
  et se relit sans mot de passe humain.

Un script d'automatisation utilise toujours un bot. Un jeton humain dans une
tâche planifiée, c'est une panne à retardement. L'inverse se paie aussi : un jeton
sans expiration se protège comme un mot de passe.

> **Sécurité** — Le fichier `.env` contient ce jeton et n'est pas versionné
> (`.gitignore`). Les YAML de TP, eux, ne contiennent que des `${PLACEHOLDERS}` :
> `./omlab ingest` produit la version remplie dans `tmp/`, elle aussi ignorée
> par git. C'est le minimum syndical pour un dépôt qu'on partage.

## 4. Vérifier que tout va bien

```bash
./omlab status                     # 6 conteneurs actifs, leur état de santé
./omlab psql "SELECT count(*) FROM raw.orders"   # 3000
curl -s localhost:8585/api/v1/system/version
```

Le septième conteneur, `execute_migrate_all`, joue les migrations puis s'arrête :
son état `Exited (0)` est normal.

Sur la page d'accueil d'OpenMetadata, vous devez voir un catalogue vide :
c'est normal, aucune ingestion n'a encore tourné. C'est l'objet du chapitre 04.

## 5. Quand ça ne marche pas

| Symptôme | Cause la plus fréquente | Que faire |
|---|---|---|
| `port is already allocated` | 8585, 8586, 8080, 5432, 5433, 9200, 9300 ou 8010 déjà pris (5432 surtout, si un Postgres tourne sur la machine) | libérez le port ; seul le webhook se change dans `.env`, via `OMLAB_WEBHOOK_PORT` |
| Le serveur ne répond jamais | Elasticsearch a été tué faute de RAM | `./omlab logs elasticsearch` ; augmentez la mémoire Docker |
| `Le démon Docker ne répond pas` | Docker Desktop éteint, ou intégration WSL désactivée | démarrez Docker Desktop, activez l'intégration |
| Ingestion : `Connection refused` | vous avez écrit `localhost` dans un YAML | depuis un conteneur, c'est `omlab-postgres` et `openmetadata-server` |
| 401 sur l'API | jeton expiré ou absent | `./omlab token` |

Les logs, dans l'ordre où on les consulte :

```bash
./omlab logs openmetadata-server    # 90 % des problèmes sont ici
./omlab logs ingestion              # workflows et Airflow
./omlab logs elasticsearch          # si le serveur ne démarre pas
./omlab logs omlab-webhook          # chapitre 12
```

## 6. Repartir de zéro

```bash
./omlab down     # arrête, garde les données
./omlab nuke     # supprime tout, volumes compris — demande confirmation
```

`nuke` est utile plus souvent qu'on ne croit dans un contexte d'apprentissage :
on casse quelque chose, on repart propre en trois minutes. Le seed du
playground est rejoué automatiquement à la recréation du volume.

## Mode d'emploi : se repérer dans l'interface

**Se connecter.** Ouvrez http://localhost:8585, saisissez l'e-mail **(1)** et le
mot de passe **(2)**, soit `admin@open-metadata.org` et `admin`, puis cliquez sur
**Sign In (3)**.

![L'écran de connexion d'OpenMetadata](img/02-connexion.png)

**Trouver son chemin.** Tout part du menu de gauche. Quatre entrées reviendront
dans tout le cours :

- **Explore (1)** : la recherche et les fiches (chapitre 03) ;
- **Observability (2)** : qualité, incidents et alertes (chapitres 10 et 12) ;
- **Govern (3)** : glossaire et classifications (chapitres 07 et 08) ;
- **Settings (4)** : services, équipes, droits, applications.

Les entrées **Data Marketplace** et **Context Center** sont arrivées avec la 2.0 : le
[chapitre 17](17-tour-complet-2x.md) les parcourt.

![La page d'accueil et le menu de gauche](img/02-accueil.png)

**Les réglages.** **Settings** regroupe l'administration sous forme de tuiles.
Les chapitres suivants y renvoient par leur nom : *Services*, *Applications*,
*Notifications*, *Team & User Management*, *Access Control*.

![Les tuiles de la page Settings](img/02-reglages.png)

**Airflow.** http://localhost:8080 (`admin` / `admin`) affiche l'orchestrateur.
Il contient d'origine six DAG d'exemple, tous en pause. Les workflows déployés
depuis l'interface d'OpenMetadata s'y ajouteront.

![La liste des DAG dans Airflow](img/02-airflow.png)

---

## TP guidé

1. `cp .env.example .env && ./omlab up`
2. `./omlab token`
3. `./omlab status` — les six conteneurs doivent être `running`, dont quatre
   `healthy`.
4. Ouvrez http://localhost:8585 et connectez-vous.
5. Ouvrez http://localhost:8080 (Airflow) : seuls les six DAG d'exemple y
   figurent, en pause — les workflows déployés depuis l'UI s'y ajouteront.
6. `./omlab psql` puis `\dt raw.*` pour voir les tables du terrain de jeu.

**Vérifier :**

```bash
./omlab status
./omlab psql "SELECT count(*) AS clients FROM raw.customers"   # 500
```

## Exercices

1. Arrêtez Elasticsearch (`docker stop openmetadata_elasticsearch`) et essayez
   une recherche dans l'UI. Que se passe-t-il ? Et la navigation par FQN ?
   Redémarrez-le ensuite.
2. Dans `docker/docker-compose.playground.yml`, trouvez pourquoi le playground
   écoute sur 5433 et non 5432.
3. Regardez `docker/docker-compose.openmetadata.yml` : combien de variables
   d'environnement le serveur accepte-t-il ? Cherchez `AUTHENTICATION_PROVIDER`
   et devinez ce qu'il faudrait changer pour brancher un SSO.

## Pièges & FAQ

**« Faut-il installer `openmetadata-ingestion` sur ma machine ? »**
Non, et c'est délibéré. Le conteneur `ingestion` embarque déjà le paquet et
ses cent connecteurs. `./omlab ingest` et `./omlab py` exécutent tout dedans,
avec le dépôt monté sur `/omlab`. Vous évitez ainsi le casse-tête de
dépendances qu'est l'installation locale de tous les pilotes de bases.

**« Pourquoi mon YAML parle-t-il de `openmetadata-server` et pas de `localhost` ? »**
Parce qu'il est exécuté *dans* le conteneur d'ingestion. Pour lui, `localhost`
est lui-même. C'est l'erreur la plus fréquente des débutants sur ce produit.

## Pour aller plus loin

- [Déploiement Docker](https://docs.open-metadata.org/v2.0.x/quick-start/local-docker-deployment)
- [Déploiement Kubernetes](https://docs.open-metadata.org/v2.0.x/deployment/kubernetes)

---

**Chapitre précédent :** [01 — Panorama](01-panorama.md) ·
**Suivant :** [03 — Le catalogue au quotidien](03-catalogue-decouverte.md)

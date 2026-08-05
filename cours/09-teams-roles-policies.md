# Chapitre 09 — Équipes, rôles et politiques

> **Objectifs** — Comprendre le modèle d'autorisation, écrire une politique
> conditionnelle, et savoir où le système va vous surprendre.
> **Durée** — 45 minutes.

---

## 1. Le modèle en une phrase

> Une **règle** autorise ou interdit des **opérations** sur des **ressources**,
> sous **condition**. Un ensemble de règles forme une **politique**. Une
> politique s'attache à un **rôle**. Un rôle se donne à un **utilisateur** ou
> à une **équipe**.

```
Utilisateur ──membre──▶ Équipe ──rôle par défaut──▶ Rôle
     │                                                │
     └────────────── rôle direct ────────────────────▶│
                                                      │
                                                 Politique
                                                      │
                                            Règle : effet + opérations
                                                    + ressources + condition
```

Ce qui fait la puissance — et la difficulté — du système, c'est la
**condition** : une expression évaluée au moment de l'accès, sur l'entité
visée. Elle permet d'écrire « chacun peut modifier la description des tables
qu'il possède » sans nommer personne.

## 2. Les équipes

`teamType` définit la place dans la hiérarchie organisationnelle :

```
Organization  →  BusinessUnit  →  Division  →  Department  →  Group
```

**Seuls les `Group` peuvent avoir des utilisateurs pour membres directs.**
C'est l'erreur du premier essai : on crée une `Division`, on tente d'y ajouter
quelqu'un, et on ne comprend pas le refus. Les niveaux supérieurs ne
contiennent que d'autres équipes.

L'héritage descend : un rôle posé sur une `BusinessUnit` s'applique à tous les
groupes qu'elle contient.

## 3. Les politiques

Trois politiques existent d'origine, et il faut savoir ce qu'elles font avant
d'en ajouter :

| Politique | Contenu |
|---|---|
| `OrganizationPolicy` | tout le monde peut voir ; le propriétaire peut éditer |
| `DataConsumerPolicy` | lecture, commentaire, suivi |
| `DataStewardPolicy` | édition des descriptions, étiquettes, propriétaires |

### Les fonctions de condition

| Fonction | Vraie quand… |
|---|---|
| `isOwner()` | l'utilisateur (ou son équipe) possède l'entité |
| `noOwner()` | l'entité n'a pas de propriétaire |
| `matchAnyTag('PII.Sensitive')` | l'entité porte une de ces étiquettes |
| `matchAllTags(...)` | elle les porte toutes |
| `matchTeam()` | l'entité appartient à l'équipe de l'utilisateur |
| `inAnyTeam('data_platform')` | l'utilisateur est dans une de ces équipes |
| `hasAnyRole('Admin')` | il a un de ces rôles |
| `hasDomain()` / `noDomain()` | l'entité est (ou non) dans son domaine |
| `isBotUser()`, `isAdminUser()`, `isReviewer()` | — |

La liste exacte de votre instance : `GET /api/v1/policies/functions`.

### La règle qui prime sur toutes les autres

> **Un `deny` l'emporte toujours sur un `allow`**, quel que soit l'ordre des
> règles, quel que soit le rôle qui l'apporte.

Conséquence pratique : on n'écrit un `deny` que quand on veut un verrou
absolu. Pour tout le reste, on construit par `allow` successifs. Un `deny`
mal placé dans une politique héritée par toute l'organisation devient très
vite impossible à diagnostiquer.

## 4. Le TP

```bash
./omlab py tp/09-securite/teams_roles_policies.py
```

```
Équipe : data_platform (type Group)
  utilisateur : cmartin <camille.martin@omlab.internal>
  utilisateur : lbernard <louis.bernard@omlab.internal>

Politique : omlab_donnees_rh (2 règles)
  [ALLOW] autoriser_documentation      si isOwner()
  [DENY ] interdire_echantillons_rh    si matchAnyTag('PII.Sensitive')

Rôle : omlab_data_steward -> politiques ['omlab_donnees_rh']
  rôle attaché à l'équipe data_platform

raw.employees appartient désormais à l'équipe Data Platform
```

La politique dit exactement ceci : *les membres de Data Platform peuvent
documenter ce qu'ils possèdent, mais personne — eux compris — ne peut
consulter les échantillons des tables marquées PII.Sensitive.*

C'est la parade au problème soulevé au chapitre 08 : l'échantillon reste
stocké et exploitable, mais son accès est verrouillé par une règle plutôt que
par sa suppression.

### Le piège des noms d'opérations

```yaml
"operations": ["ViewSampleData", "ViewDataProfile"]
```

Ces noms sont vérifiés par le serveur, et une faute de frappe ne donne pas
« opération inconnue » mais un laconique :

```
HTTP 400 — {"code":400,"message":"Invalid request format"}
```

La liste exacte, par ressource :

```bash
curl -s -H "Authorization: Bearer $OM_TOKEN" \
  localhost:8585/api/v1/policies/resources | jq '.data[] | select(.name=="table")'
```

Pour `table` : `ViewAll`, `ViewBasic`, `ViewSampleData`, `ViewDataProfile`,
`ViewQueries`, `ViewTests`, `ViewUsage`, `EditAll`, `EditDescription`,
`EditTags`, `EditOwners`, `EditLineage`, `EditTier`, `Create`, `Delete`…

## 5. Les bots

Un **bot** est un utilisateur non humain, avec un jeton long et pas de mot de
passe. `ingestion-bot` existe d'origine — c'est lui qu'utilise
`./omlab token`.

Bonne pratique : **un bot par usage**, avec les droits minimaux. Un bot pour
l'ingestion, un pour votre script de documentation, un pour votre CI. Quand
un jeton fuite ou qu'un script part en vrille, on révoque un bot sans arrêter
le reste.

## 6. Domaines et produits de données

Une couche organisationnelle plus récente, orientée *data mesh* :

- un **domaine** regroupe des assets par périmètre métier (Ventes, RH) et peut
  porter ses propres politiques ;
- un **produit de données** est un sous-ensemble publié avec un propriétaire,
  une documentation et des engagements — la brique que consomment les autres
  équipes.

C'est utile à partir d'une certaine taille d'organisation. En dessous,
équipes + propriétaires suffisent, et ajouter des domaines ne fait
qu'ajouter de la cérémonie.

---

## TP guidé

```bash
./omlab py tp/09-securite/teams_roles_policies.py
```

1. **Settings → Teams** : ouvrez `data_platform`, vérifiez ses deux membres et
   son rôle par défaut.
2. **Settings → Roles → omlab_data_steward** : lisez la politique attachée.
3. **Settings → Policies → omlab_donnees_rh** : lisez les deux règles.
4. Ouvrez `raw.employees` : elle appartient maintenant à l'équipe.
5. Donnez un mot de passe à `cmartin` (Settings → Users), ouvrez une fenêtre
   privée, connectez-vous, et essayez d'afficher l'échantillon de
   `raw.employees`.

**Vérifier :**

```bash
./omlab check 09
```

```
Chapitre 09 — Équipes, rôles, politiques
  OK   l'équipe data_platform existe
  OK   l'utilisateur cmartin existe
  OK   la politique omlab_donnees_rh existe
  OK   la politique combine une règle deny et une allow
  OK   le rôle omlab_data_steward existe
```

## Exercices

1. Écrivez une politique qui interdit de supprimer toute table `Tier.Tier1`.
2. Écrivez-en une qui autorise l'édition des descriptions uniquement sur les
   tables **sans** propriétaire (`noOwner()`) — pour encourager l'adoption des
   tables orphelines.
3. Créez une `BusinessUnit` `Data`, mettez `data_platform` dedans, posez un
   rôle sur la BU et vérifiez qu'il descend.
4. Créez un bot `documentation-bot`, générez son jeton, et refaites tourner
   `tp/14-sdk/02_ecriture.py` avec. Regardez la colonne « modifié par ».

## Pièges & FAQ

**« J'ai donné un rôle et rien ne change. »**
Trois causes, par fréquence : un `deny` hérité bloque ailleurs ; le rôle est
posé sur une équipe non-`Group` ; l'utilisateur a une session ouverte —
qu'il se reconnecte.

**« Comment brancher notre SSO ? »**
`AUTHENTICATION_PROVIDER` dans le compose accepte `google`, `okta`, `auth0`,
`azure`, `custom-oidc`, `saml`, `ldap`. Le sujet est conséquent et n'apporte
rien à l'apprentissage du produit : ce tutoriel reste en `basic`. Voir la
[documentation](https://docs.open-metadata.org/v1.13.x/deployment/security).

**« Peut-on masquer complètement une table ? »**
Oui, avec un `deny` sur `ViewBasic` : l'entité disparaît de la recherche et
des listes pour les utilisateurs concernés.

## Pour aller plus loin

- [Rôles et politiques](https://docs.open-metadata.org/v1.13.x/how-to-guides/admin-guide/roles-policies)

---

**Précédent :** [08 — Classification](08-classification-pii.md) ·
**Suivant :** [10 — Qualité de données](10-data-quality.md)

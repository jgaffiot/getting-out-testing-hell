> 🤖 **Ce document est une traduction française du `README.md`, réalisée par une IA (Claude).**
> En cas de divergence, la version anglaise fait foi.

# Sortir de l'enfer des tests

Support d'atelier — *Getting out of the testing hell!*

---

## L'application

Une API REST de librairie construite avec FastAPI + PostgreSQL. Elle gère :

- **Livres** — catalogue CRUD avec niveaux de stock
- **Utilisateurs** — comptes basiques
- **Commandes** — passer une commande, payer avec un token de carte, recevoir un email de confirmation, annuler dans l'heure

<details>
<summary>Architecture actuelle (<code>app/</code>)</summary>

```
app/
├── main.py               # Application FastAPI, branche les 3 routeurs ensemble
├── config.py              # constantes de module, mi variables d'env / mi codées en dur
├── database.py             # engine, SessionLocal, Base, dépendance get_db()
├── models/                  # ORM SQLAlchemy : Book, User, Order, OrderItem
├── schemas/                  # Schémas Pydantic de requête/réponse
├── api/                        # Routeurs FastAPI : books, users, orders
├── services/
│   └── order_service.py        # OrderService : logique de passage et d'annulation de commande
└── clients/
    ├── payment_client.py        # PaymentClient - vrais appels HTTP (httpx) vers une fausse API de paiement
    └── email_client.py          # EmailClient - vrais appels SMTP (smtplib)
```

- Les routeurs `books` et `users` parlent directement à la base via la dépendance FastAPI
  `get_db()` — du CRUD léger, sans couche de service.
- Le routeur `orders` délègue à `OrderService`, mais construit un **nouveau `OrderService()`
  à chaque requête** au lieu d'en recevoir un via `Depends()`.
- `OrderService.__init__` construit lui-même son `PaymentClient()` et son `EmailClient()`, et
  `create_order()` / `cancel_order()` ouvrent chacun leur propre session `SessionLocal()`
  au lieu de réutiliser celle de la requête — aucun des trois collaborateurs (session de
  base de données, client de paiement, client d'email) n'est injectable.
- `PaymentClient.charge/refund` et `EmailClient.send` font de vrais appels sortants
  (`httpx.post` vers `PAYMENT_API_URL`, `smtplib.SMTP` vers `EMAIL_SMTP_HOST`) — il n'y a
  aucune couture pour un faux/stub, donc tester `OrderService` implique de toucher (ou de
  mocker) de vrais appels réseau.
- Le calcul du total et des promotions est écrit en ligne dans `create_order` (et dupliqué,
  de façon légèrement différente, dans `calculate_order_total`, par ailleurs inutilisée) —
  de l'arithmétique pure est mélangée à des lectures en base et à des I/O.
- L'heure est lue via `datetime.utcnow()` directement dans `create_order` / `cancel_order` —
  la fenêtre d'annulation d'1 heure ne peut pas être testée sans réellement attendre.
- `config.py` mélange des valeurs `os.environ.get(...)` et des constantes codées en dur
  (`PAYMENT_API_URL`, `EMAIL_FROM`), lues une seule fois à l'import.

</details>

## Installation

### Prérequis

- [uv](https://docs.astral.sh/uv/) (obligatoire)
- Docker ou Podman (recommandé, pour la base de données)

### Démarrer l'infrastructure

```bash
docker compose up -d
```

### Installer les dépendances et lancer l'application

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

La documentation de l'API est disponible sur <http://localhost:8000/docs>.

### Lancer les linters

```bash
uv run ruff format .
uv run ruff check .
uv run ty check .
```

Par défaut, un petit ensemble de règles Ruff est activé.

La solution passe Ruff avec presque toutes les règles :

```bash
uv run ruff check --select ALL --ignore EM,TRY003 solution/app
uv run ruff check --select ALL --ignore EM,TRY003,S,ANN,PLR2004 solution/tests
```

### Lancer les tests existants

```bash
uv sync --group test
uv run pytest tests/ -v
```

> **Attention :** la plupart des tests nécessitent une application **et** une base de données
> en cours d'exécution. Plusieurs échoueront ou seront ignorés silencieusement sans
> l'environnement adéquat.

### Lancer la solution

Nécessite un conteneur non-root : Podman, Docker rootless, ou appartenir au groupe « docker ».

> **Attention :** appartenir au groupe « docker » équivaut en pratique à être root, car
> n'importe quel membre du groupe docker peut monter la racine du système de fichiers ('/')
> dans un conteneur privilégié.

```bash
uv sync --group solution
uv run pytest tests/ -v
```

En cas de problème avec Podman, essayez :

```bash
# Activer le socket Podman rootless
systemctl --user enable --now podman.socket
# Pointer testcontainers dessus :
export DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock
```

et si les tests plantent avec une `docker.error`, essayez :

```bash
export TESTCONTAINERS_RYUK_DISABLED=true
export TESTCONTAINERS_HOST_OVERRIDE=localhost
```

## Déroulé de l'atelier

### Partie 1 : Diagnostic (analyse guidée, 45 minutes)

* Introduction et vérification de l'installation (10 minutes)
* Exploration du code et exécution des tests (15 minutes)
  1. **Culture qualité** — quels signaux voyez-vous dans le dépôt sur la place accordée aux tests ?
  2. **Architecture** — qu'est-ce qui rend le code difficile à tester ? Où sont les coutures ? Quels sont les
    services cœur, les services tiers, et le contrat entre eux ?
  3. **Tests existants** — listez tous les problèmes que vous trouvez dans `tests/`. Combien de tests testent réellement quelque chose ?
  4. **CI** — qu'est-ce qui ne va pas dans `.github/workflows/ci.yml` ?
* Diagnostic guidé, pourquoi les tests sont mauvais (20 minutes)

### Partie 2 : Stratégie (analyse guidée + travail en groupe, 40 minutes)

* Concepts et vocabulaire (5 minutes)
* Définir une stratégie de test (20 minutes)
* Discussion des compromis (5 minutes)
* Présentation des outils (10 minutes)

Pause de 10 minutes

### Partie 3 : Implémentation (code en autonomie, 75 minutes)

* Corriger les tests existants (20 minutes)
* Ajouter de nouveaux tests (25 minutes)
* Refactoring minimal (15 minutes)
* Mise en place de la CI (10 minutes)

### Conclusion (10 minutes)

* Revue du résultat final (8 minutes)
* Ressources (2 minutes)

---

## Indices

<details>
<summary>Problèmes dans les tests existants (spoilers)</summary>

- Les tests appellent un serveur HTTP en fonctionnement (`requests.get("http://localhost:8000/...")`) — non portable, dépendant de l'ordre
- État global mutable (`created_book_id = None`) — les tests doivent s'exécuter dans l'ordre alphabétique
- `setup_test_data()` est appelée plusieurs fois sans nettoyage — laisse des déchets dans la base
- Appels directs à `psycopg2` qui contournent l'API — teste la base, pas l'application
- `time.sleep(3700)` est commenté — le test passe toujours, il ne teste jamais l'échéance
- `return` silencieux en cas d'échec — les tests sont verts alors que la fonctionnalité est cassée
- Des mocks qui vérifient seulement le nombre d'appels, pas leur exactitude
- Aucun teardown nulle part

</details>

<details>
<summary>Problèmes dans le code de l'application (spoilers)</summary>

- `OrderService.__init__` crée directement `PaymentClient()` et `EmailClient()` — impossible d'injecter des fakes
- `OrderService` appelle lui-même `SessionLocal()` — impossible d'injecter une session de test
- `datetime.utcnow()` appelé en ligne — la logique dépendant du temps ne peut pas être testée sans `sleep`
- `calculate_order_total` interroge la base pour faire de l'arithmétique — logique pure enfouie dans de l'I/O
- Le routeur de l'API instancie `OrderService()` à chaque requête — aucun point d'injection

</details>

<details>
<summary>Refactoring minimal nécessaire</summary>

- Ajouter des paramètres au constructeur : `OrderService(db, payment, email, now=datetime.utcnow)`
- Extraire `compute_total(prices, promo_code)` en fonction pure
- Utiliser `Depends()` de FastAPI pour injecter `OrderService` dans le routeur

Voir `solution/order_service.py` pour le résultat.

</details>

---

## Solution de référence

`solution/` contient le service refactoré et les tests améliorés.
Voir `solution/README.md` pour une explication complète de ce qui a changé et pourquoi.

<details>
<summary>Choix de conception des tests (<code>solution/tests/</code>)</summary>

**Portée des fixtures** (`conftest.py`) — trois niveaux, choisis pour payer une seule fois
l'installation coûteuse tout en gardant les tests isolés les uns des autres :

- `pg_container` (portée **session**) — un seul conteneur PostgreSQL réel pour toute
  l'exécution des tests. Démarrer un conteneur par test dominerait le temps d'exécution.
- `db_engine` (portée **session**) — un seul engine SQLAlchemy sur ce conteneur, avec le
  schéma créé une fois via `Base.metadata.create_all()`.
- `db` (portée **fonction**, la valeur par défaut) — chaque test obtient sa propre connexion
  enveloppée dans une transaction annulée (rollback) au teardown. Les tests peuvent librement
  insérer/modifier des lignes sans nettoyer ni polluer le test suivant, sans avoir besoin
  d'un nouveau conteneur.

**Testcontainers** — `testcontainers[postgres]` lance un vrai `postgres:16` dans
Docker/Podman plutôt que SQLite ou une session mockée. L'application s'appuie sur des
comportements spécifiques à Postgres (`Numeric` pour l'argent, un `Enum` natif pour
`OrderStatus`) qu'une base en mémoire ou d'un autre moteur n'exercerait pas fidèlement.

**Des fakes plutôt que des mocks** (`fakes.py`) — `FakePaymentClient` et `FakeEmailClient`
sont de petites implémentations en mémoire fonctionnelles, pas des `unittest.mock.Mock` :

- `FakePaymentClient` enregistre de vrais objets `FakeCharge` dans `self.charges`, génère des
  identifiants de paiement incrémentaux, et peut être construit avec `fail_on_token=...` pour
  simuler une carte refusée — ainsi la logique de remboursement de `cancel_order`, par
  exemple, peut être vérifiée via `payment.charges[0].refunded is True` plutôt qu'avec un
  simple `refund.assert_called()`.
- `FakeEmailClient` enregistre des objets `SentEmail`, si bien que les tests vérifient le
  destinataire, le sujet et le corps réels plutôt que seulement « send a été appelé ».

C'est volontairement différent de `_check_connections` (voir `order_service.py`), qui est
patché avec un simple `unittest.mock.MagicMock` via la fixture autouse
`no_connection_check` — cette méthode est du bruit d'infrastructure (un sleep aléatoire sans
rapport avec la logique métier), il n'y a donc rien à faker ; elle est entièrement
neutralisée. Les fakes sont réservés aux collaborateurs (`payment`, `email`) dont le
comportement intéresse réellement les tests.

</details>

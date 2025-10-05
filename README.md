# Labo 04 – Optimization, Caching, Load Balancing, Test de charge, Observabilité

<img src="https://upload.wikimedia.org/wikipedia/commons/2/2a/Ets_quebec_logo.png" width="250">    
ÉTS - LOG430 - Architecture logicielle - Chargé de laboratoire: Gabriel C. Ullmann, Automne 2025.

## 🎯 Objectifs d'apprentissage
- Apprendre à configurer Prometheus
- Apprendre à effectuer les tests de charge avec [Locust](https://docs.locust.io/en/stable/what-is-locust.html)
- Comprendre les types d'optimisation possibles ainsi que les avantages et inconvénients de chacun
- Apprendre à implémenter le cache en mémoire avec Redis et l'équilibrage de charge (load balancing) avec [Nginx](https://nginx.org/en/docs/http/load_balancing.html)

## ⚙️ Setup

Dans ce laboratoire, on continuera à utiliser la même version du « store manager » développée au laboratoire 03, mais nous ferons quelques modifications. Le but n'est pas d'ajouter de nouvelles fonctionnalités, mais de mesurer et comparer la performance de lecture/écriture de l'application en utilisant MySQL et Redis. Après avoir mesuré et comparé, nous allons implémenter deux approches d'optimisation : caching et load balancing.

> ⚠️ **IMPORTANT** : Les documents ARC42 et ADR contenus dans ce dépôt sont identiques à ceux du laboratoire 03, car nous ne modifions pas l'architecture de l'application dans ce laboratoire.

> 📝 NOTE : À partir de ce laboratoire, nous vous encourageons à utiliser la bibliothèque `logging` plutôt que la commande `print`. Bien que `print` fonctionne bien pour le débogage, l'utilisation d'un logger est une bonne pratique de développement logiciel car il offre [plusieurs avantages lorsque notre application entre en production](https://www.geeksforgeeks.org/python/difference-between-logging-and-print-in-python/). Vous trouverez un exemple d'utilisation du `logging` et plus de détails dans `src/stocks/commands/write_stock.py`.

### 1. Créez un nouveau dépôt à partir du gabarit et clonez le dépôt
```bash
git clone https://github.com/[votredepot]/log430-a25-labo4
cd log430-a25-labo4
```

### 2. Créez un réseau Docker
Exécutez dans votre terminal :
```bash
docker network create labo04-network
```

### 3. Préparez l'environnement de développement
Suivez les mêmes étapes que dans le laboratoire dérnier.

### 4. Installez Postman
Suivez les mêmes étapes que dans le laboratoire dérnier. Importez la collection disponible dans `/docs/collections`.

### 5. Préparez l’environnement de déploiement et le pipeline CI/CD
Utilisez les mêmes approches qui ont été abordées lors des laboratoires dérniers.

## 🧪 Activités pratiques
Pendant le labo 02, nous avons implémenté le cache avec Redis. Pendant le labo 03, nous avons utilisé ce cache pour les endpoints des rapports. Dans ce labo, nous allons temporairement désactiver le Redis pour mesurer la différence entre les lectures directement de MySQL vs Redis. Pour faciliter les comparaisons, dans ce laboratoire les méthodes qui font la génération de rapport dans `queries/read_order.py` ont 2 versions : une pour MySQL, autre pour Redis.

### 1. Désactivez le cache Redis temporairement
Dans `queries/read_order.py`, remplacez l'appel à `get_highest_spending_users_redis` par `get_highest_spending_users_mysql`. Également, remplacez l'appel à `get_best_selling_products_redis` par `get_best_selling_products_mysql`.

### 2. Instrumentez Flask avec Prometheus
Dans `store_manager.py`, ajoutez un endpoint `/metrics`, qui permettra à Prometheus de lire l'état des variables que nous voulons observer dans l'application.
```python
@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}
```

N'oubliez pas d'ajouter également les `imports` suivants:
```python
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
```

### 3. Créez des Counters 
Également dans `store_manager.py`, ajoutez les objets [Counter](https://prometheus.io/docs/concepts/metric_types/#counter) pour compter le nombre de requêtes aux endpoints `/orders`, `/orders/reports/highest-spenders` et `/orders/reports/best-sellers`. N'oubliez pas d'appeler la méthode `inc()` pour incrémenter la valeur du compteur à chaque requête. Par exemple :

```python
counter_orders = Counter('orders', 'Total calls to /orders')
@app.post('/orders')
def post_orders():
    counter_orders.inc()
```

### 4. Observez les métriques dans Prometheus
Dans Postman, faites quelques requêtes à `POST /orders`. Ensuite, accédez à Prometheus sur `http://localhost:9090` et exécutez une requête (query) à `orders_total`. Vous devriez voir une valeur numérique associée à la variable. Faites la même chose pour les deux autres `Counters`. Par exemple, si vous avez nommé le compteur `highest_spenders`, exécutez une requête à `highest_spenders_total`. Cliquez sur `Graph` pour voir la représentation visuelle de chaque variable. Faites quelques requêtes de plus pour voir le changement des variables.

> 📝 **NOTE** : Prometheus ne met pas automatiquement à jour les variables dans l'interface Web lorsqu'elles changent dans le serveur. Vous devez cliquer sur `Query` ou recharger la page Web pour voir les valeurs mises à jour.

### 5. Lancez un test de charge avec Locust
Le script `locustfiles/locustfile.py` lorsqu'il est exécuté, effectuera plusieurs appels vers des endpoints (représentés par les méthodes `@task`), simulant ainsi des utilisateurs réels. Dans un premier temps, nous ne modifierons pas ce script, nous l'activerons simplement à partir de l'interface web à Locust.

Accédez à `http://localhost:8089` et appliquez les paramètres suivantes :
- Number of users (nombre d'utilisateurs) : 100
- Spawn rate (taux d'apparition des nouveaux utilisateurs) : 1 (par seconde)

Lancez le test et observez les statistiques et graphiques dans Locust (onglet `Charts`). En un peu moins de 2 minutes, vous devriez observer que votre application reçoit une charge de requêtes équivalente à 100 utilisateurs simultanés.

> 💡 **Question 1** : Quelle est la latence moyenne (50ème percentile) et le taux d'erreur observés avec 100 utilisateurs ? Illustrez votre réponse à l'aide des graphiques Locust (onglet `Charts`).

### 6. Écrivez un nouveau test de charge avec Locust
Dans le répertoire `locustfiles/experiments/locustfile_read_write.py`, complétez le script `locustfile_read_write.py` pour ajouter une commande en utilisant des valeurs aléatoires et une proportion d'exécution des méthodes `@task` à 66% lectures, 33% écritures (2/3, 1/3, 1/3). Plus d'informations sur la proportion d'exécution des appels de chaque méthode `@task` [dans la documentation officielle à Locust](https://docs.locust.io/en/stable/writing-a-locustfile.html#task-decorator).

Finalement, copiez le code modifié de `locustfiles/experiments/locustfile_read_write.py` à `locustfiles/locustfile.py`. 

Éxecutez :
```bash
docker compose down -v && docker compose up -d --build
```

Relancez le test Locust (avec les mêmes paramètres de la dernière activité). Si cela fonctionne, passez à l'activité 7.

### 7. Augmentez la charge
Augmentez progressivement le nombre d'utilisateurs jusqu'à ce que l'application échoue (timeouts, erreurs 500, etc.).

> 💡 **Question 2** : À partir de combien d'utilisateurs votre application cesse-t-elle de répondre correctement (avec MySQL) ? Illustrez votre réponse à l'aide des graphiques Locust.

### 8. Optimisez la lecture des données des articles
Nous pourrions obtenir une performance supérieure simplement en utilisant un cache en mémoire tel que Redis. Cependant, il est toujours raisonnable de vérifier si nous pouvons d'abord optimiser notre code existant. L'optimisation du code est généralement plus abordable et plus efficace que changer de base de données, serveur Web ou augmenter les ressources de calcul (RAM/CPU) sur un serveur on-premises ou en nuage.

Dans `orders/commands/write_order.py`, si nous regardons attentivement la fonction `add_order`, nous verrons qu'elle ne récupère pas les informations des articles de manière efficace. Si nous avions, par exemple, 100 articles dans notre commande, la fonction effectuerait 100 requêtes à la base de données pour chercher les informations sur les articles ([problème N+1](https://planetscale.com/blog/what-is-n-1-query-problem-and-how-to-solve-it)). À fur et a mesure que le nombre d'articles augmente dans la base, le temps de recherche augmente également.

```python
# ❌ Code non-optimisé
product_prices = {}
for product_id in product_ids:
    product = session.query(Product).filter(Product.id == product_id).all()
    product_prices[product_id] = product[0].price
```

Modifiez la méthode `add_order` de façon à collecter et récupérer tous les `product_ids` en une seule requête. Utilisez la fonction `in_` à SQLAlchemy.
```python
# ✅ Code optimisé
product_prices = {}
product_ids = [1, 2, 3] # Collectez les product_ids des OrderItems
products = session.query(Product).filter(Product.id.in_(product_ids)).all()
# Parcourez la liste, extrayez le prix de chaque article
```

> 📝 NOTE : Ceci n'est qu'un exemple trivial d'optimisation dans une seule méthode. Dans une application réelle, il faut parfois optimiser des algorithmes complèxes, des fonctions mathématiques, des structures de données, ou effectuer des ajustements dans la base de données, comme la [création d'index](https://www.w3schools.com/mysql/mysql_create_index.asp) ou la [normalisation](https://www.ibm.com/fr-fr/think/topics/database-normalization).

Éxecutez :
```bash
docker compose down -v && docker compose up -d --build
```

Relancez le test Locust (avec les mêmes paramètres de la dernière activité).

> 💡 **Question 3** : À partir de combien d'utilisateurs votre application cesse-t-elle de répondre correctement (avec MySQL + Optimisation) ? Illustrez votre réponse à l'aide des graphiques Locust.

### 9. Réactivez Redis
Étant donné que nous avons fait de notre mieux pour identifier les obstructions dans notre application (lectures de la base de données) et l'optimiser, nous pouvons désormais mettre en place un cache en memóire pour aller encore plus loin. Dans `queries/read_order.py`, remplacez l'appel à `get_highest_spending_users_mysql` par `get_highest_spending_users_redis`. Également, remplacez l'appel à `get_best_selling_products_mysql` par `get_best_selling_products_redis`.

### 10. Testez la charge encore une fois
Éxecutez :
```bash
docker compose down -v && docker compose up -d --build
```

Augmentez progressivement le nombre d'utilisateurs jusqu'à ce que l'application échoue (timeouts, erreurs 500, etc.). Regardez l'onglet `Failures` pour plus d'informations sur les erreurs.

> 💡 **Question 4** : À partir de combien d'utilisateurs votre application cesse-t-elle de répondre correctement (avec Redis) ? Quelle est la latence et le taux d'erreur observés ? Illustrez votre réponse à l'aide des graphiques Locust.

### 11. Testez l'équilibrage de charge (load balancing) avec Nginx
Pour tester le scénario suivant, utilisez le répertoire `load-balancer-config` :
- Copiez le texte dans `docker-compose-to-copy-paste.txt` et collez-le dans `docker-compose.yml`
- Créez un fichier `nginx.conf` dans le répertoire racine du projet.
- Copiez le texte dans `nginx-conf-to-copy-paste.txt` et collez-le dans un fichier `nginx.conf`
Observez les modifications apportées à `docker-compose.yml`. 

Éxecutez :
```bash
docker compose down -v && docker compose up -d --build
```

Ensuite, relancez le test Locust (avec les mêmes paramètres de la dernière activité)

> 💡 **Question 5** : À partir de combien d'utilisateurs votre application cesse-t-elle de répondre correctement (avec Redis + Nginx load balancing) ? Quelle est la latence moyenne (50ème percentile) et le taux d'erreur observés ? Illustrez votre réponse à l'aide des graphiques Locust.

> 💡 **Question 6** : Avez-vous constaté une amélioration des performances à mesure que nous avons mis en œuvre différentes approches d'optimisation ? Quelle a été la meilleure approche ? Justifiez votre réponse en vous référant aux réponses précédentes.

> 💡 **Question 7** : Dans le fichier `nginx.conf`, il existe un attribut qui configure l'équilibrage de charge. Quelle politique d'équilibrage de charge utilisons-nous actuellement ? Consultez la documentation officielle Nginx si vous avez des questions.

## 📦 Livrables

- Un fichier .zip contenant l'intégralité du code source du projet Labo 04.
- Un rapport en .pdf répondant aux questions présentées dans ce document. Il est obligatoire d'illustrer vos réponses avec du code ou des captures d'écran/terminal.
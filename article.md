# Sortir de l'enfer des tests

## Intro

La nécessité d'écrire des tests automatisés est maintenant bien établie chez les
développeurs. Il s'agit du seul moyen de tester systématiquement et complètement, pour
éviter les régressions ou tout simplement ne pas avancer à l'aveugle.

Mais une fois posé ce consensus, les ennuis commencent. Écrire les tests est considéré
comme une corvée, souvent repoussée à la fin du projet, et qui n'attire pas les
volontaires.
Ensuite les tests sont trop souvent lents, fragiles, longs à maintenir, pas évident à
lancer, incomplets... et on finit par s'habituer à des rapports de test
négatifs ("la CI est tout le temps rouge, mais c'est normal").
On appelle ça la normalisation de la déviance, et ça peut conduire à la catastrophe,
comme faire se crasher
[Challenger](https://fr.wikipedia.org/wiki/Accident_de_la_navette_spatiale_Challenger)
*et* [Columbia](https://fr.wikipedia.org/wiki/Accident_de_la_navette_spatiale_Columbia).

Bon d'accord quand les tests auto sont inutiles ou absents, plutôt qu'une navette c'est
une app qui se crashe, mais le processus est le même.

Alors, comment reprendre le contrôle de ses tests auto ?

## Se poser les bonnes questions

Plus que les tests eux-mêmes, l'objectif est d'assurer la qualité et la maitrise
du code, un code qu'on peut donc livrer et faire évoluer en confiance.
Les tests constituent un système logiciel, parallèle au projet principal,
dont l'objectif est d'en assurer la qualité :
fiabilité, répétabilité, maintenabilité, évolutivité.

Comme tout système logiciel, il demande du temps de développement et des compétences
chères à acquérir. Ainsi, la suite de test constitue un investissement pour le projet
principal, qui doit donc en retirer un bénéfice sur la qualité. Il est donc crucial
de définir ce qui est attendu des tests. Comme il est toujours possible d'ajouter des
tests, il faut aussi définir les moyens alloués aux tests, qui permettront d'arbitrer
plus tard entre ajouter des tests, ou ajouter des fonctionnalités.

Les tests automatisés, par opposition aux tests manuels, forment tout ou partie de
la suite de tests, et sont lancés automatiquement et systématiquement,
typiquement à chaque commit.
Ainsi, on s'assure contre la plupart des régressions, et cette information est apportée
rapidement au développeur.
Il s'agit donc d'une partie centrale du processus d'intégration continue (CI), au point
que "CI" désigne maintenant les pipelines de tests automatisés !

Certains tests restent le plus souvent manuels, par exemple
les tests utilisateurs (dont tests d'ergonomie, tests A/B...), les tests de charges,
les tests de performances, les tests de pénétration...

Les tests automatisés sont là pour apporter un certain niveau de confiance sur la
qualité du code, afin d'atteindre les objectifs de qualité du projet, dans les moyens
alloués. Jamais oubliés, ils préviennent les bugs et empêchent la qualité de dériver,
mais sont souvent limités par la difficulté à automatiser.

## Repartir de la base

Les tests font partie de la boite à outil pour atteindre l'objectif de qualité, mais ils
ne sont pas seuls. Plusieurs couches successives d'outils sont nécessaires
pour intercepter les différents problèmes de qualité.

La première couche est un formatteur de code, qui permet d'uniformiser le code. Les
avantages sont de faciliter la lecture du code (pour ceux qui lisent encore le code),
de diminuer la charge du développeur (pour ceux qui l'écrivent encore), et de nettoyer
les comparaisons de code de toutes les différences de caractères d'espacement,
ce qui diminue la taile des Pull Request / Merge Request.

La seconde couche est constituée de logiciels d'analyse, et en premier lieu des outils
d'analyse statique. Ces derniers n'exécutent pas le code (d'où le nom de "statique")
mais cherchent des mauvaises pratiques en suivant des règles simples de reconnaissance
de texte, comme des expressions régulières. Leur gros avantage est de détecter des bugs
très rapidement et sans risque (le code ne tourne pas) et sans condition (pas besoin
d'environnement de test ou autre).

On trouve aussi dans cette catégorie les compilateurs, surtout avec leurs warnings
activés, et les analyseurs de types (pour les codes interprétés), qui permettent
de s'assurer de la cohérence des types, toujours sans avoir exécuté une ligne du code.

Enfin, les analyseurs dynamiques vont étudier le code pendant son fonctionnement,
souvent au prix d'une perte en performances (mémoire et CPU), pour chercher des erreurs
logiques plus difficiles à détecter (typiquement les erreurs de mémoire).

La dernière couche est bien sûr d'automatiser tous les outils choisis, au plus près
du développeur. Déjà, un lanceur comme [`doit`](https://pydoit.org/) ou
[`just`](https://just.systems/man/en/introduction.html) permet de lancer tous les outils
de qualité choisis en une commande simple. Ensuite, nous pouvons tirer parti des hooks
de Git pour lancer automatiquement ces outils lors de certains commandes, et typiquement
lors du commit. Des utilitaires comme le fameux [`pre-commit`](https://pre-commit.com/)
ou le plus récent [`prek`](https://prek.j178.dev/) permettent de configurer facilement
les hooks de Git. Pour éviter de perdre le fil à attendre la fin de tests longs au
moment du commit, n'utiliser lors du pre-commit que des outils dont le temps d'exécution
est court (jusqu'à quelques secondes).

## Nettoyer les tests

Continuons par nettoyer les tests existants, car on peut bien sûr supprimer des tests.
D'abord, les tests non fiables doivent être désactivés ou supprimées, parce qu'ils
n'apportent pas l'information dont l'équipe a besoin : que le test passe ou pas, on n'en
sait pas plus sur la qualité du code testé. Ces tests pourront être réactivés une fois
stabilisés, ce qui suppose d'identifier la cause de l'instabilité. Le tirage de nombre
aléatoire, le déclenchement à partir de l'heure réelle, la (non-)synchronisation de code
exécuté en parallèle (multi threading, asynchrone...), la dépendance à des processus ou
des API externes sont les causes les plus probables.

Par exemple, ce test échoue de façon imprévisible, car il dépend de l'heure réelle :

```python
# Fragile : dépend de l'horloge système... et reste bloqué une heure !
def test_reporting_each_hour():
    manager = Manager()            # crée un rapport à chaque heure pile
    assert manager.report is None  # faux si le test est lancé à une heure pile
    time.sleep(3600)               # c'est long...
    assert manager.report is not None
```

La solution est d'injecter l'horloge pour la contrôler depuis le test, ce qui le rend
à la fois fiable et instantané :

```python
# Fiable : le temps est injecté, donc maîtrisé
def test_reporting_each_hour():
    clock = FakeClock(now=datetime(2025, 1, 1, 12, 1))
    manager = Manager(clock)           # refacto de Manager
    assert manager.report is None      # démarrage 1 minute après midi : pas de rapport
    clock.advance(timedelta(hours=1))  # on avance le temps sans attendre
    assert manager.report is not None  # nouveau rapport
```

Ensuite, les tests trop longs n'apportent pas l'information à temps aux développeurs.
Ils peuvent être supprimés, accélérés, ou séparés dans une seconde suite de
tests si vraiment le test est nécessaire et le temps d'exécution vraiment incompressible.
Cette seconde suite de tests sera toujours automatisée, mais pas lancée à chaque commit,
à une fréquence plus faible, comme une fois par jour (souvent la nuit),
ou seulement juste avant fusion sur la branche principale. L'important est que le
développeur n'ait pas besoin du résultat immédiat du test pour continuer à travailler,
mais que l'information apportée par cette suite de tests longs ne soit nécessaire
par exemple que pour une nouvelle version.

Enfin, il ne faut pas hésiter à élaguer la suite de tests : certains tests ne sont pas
pertinents, parce que trop vieux, trop spécifiques, trop couplés ou qui testent trop peu
de code.

## Rendre le code testable

Les problèmes de test les plus sérieux sont le plus souvent dus au code à tester :
trop couplé et pas assez observable, il oblige le test à mettre en place tout un
environnement, à lancer tout le code d'un coup, à jouer tout un scénario complexe pour
atteindre l'état initial dans lequel le test pourra enfin être lancé, et à passer par
des moyens détournés ou fragiles (analyse des logs...) pour savoir si le test a réussi.

La première chose est d'isoler au maximum les effets de bord, en particulier les
entrées/sorties, pour pouvoir tester le code spécifique au projet et la logique métier
indépendamment. Pour tous les projets qui ne sont pas de simples "passe-plats", un
maximum de code doit être testable sans préparation particulière, juste en l'exécutant.

Trions ensuite les effets de bord en 3 catégories : trous noirs, fontaine blanche, et
le reste. Un trou noir est en écriture seule, on ne peut qu'y jeter des données qui sont
immédiatemement perdues. On trouve dans cette catégorie les systèmes de log et de
télémétrie. Une fontaine blanche, l'inverse théorique d'un trou noir, est en lecture
seule et ne peut être qu'initialisée, une seule fois. On trouve dans cette catégorie
le système de configuration, qui réconcilie variables d'environnement, fichiers,
ligne de commande... et met le résultat à disposition du reste du code.

Trous noirs et fontaines blanches peuvent avoir une durée de vie équivalente à celle
du programme entier et une portée globale. Ce sont les seuls effets de bord qu'on peut
tolérer à travers toute la base de code. Bien identifiés, une mise en place commune à
tous les test permettra de les gérer une fois pour toute.

Tous les autres effets de bords doivent être isolés, et si possible injectés dans le
code métier propre à leur utilisation, plutôt que détenus par le code métier. En effet,
une dépendance injectée donne toute liberté au test pour déconnecter l'effet de bord
et isoler le code, alors qu'un couplage fort rend le test difficile, surtout avec
les langages statiques.

```c++
// Difficile à tester, instancie toujours une vraie connexion
class MyClassWithInternalConnection {
private:
    HttpClient http_client;
public:
    MyClassWithInternalConnection(host, port) { http_client = HttpClient(host, port); }
};
// Facile à tester, peut instancier un substitut comme une vraie connexion
class MyClassWithInvertedDependency {
private:
    AbstractHttpClient http_client;  // peut contenir la vraie connexion ou le substitut
public:
    MyClassWithInvertedDependency(http_client_) { http_client = http_client_; }
};
```

## Prendre en main son framework de test

Tous les principaux langages ont un ou plusieurs frameworks de test, qui apportent
leur lot de fonctionnalités en plus de faciliter l'écriture des tests, comme :

- lancement depuis un point unique
- organisation en suite de tests, suite de suites...
- gestion de l'environnement, de l'OS, des signaux
- fichiers et dossiers temporaires
- interception de l'entrée standard et des sorties standards
- rassemblement et structuration des résultats des tests
- setup/teardown : une paire de fonction spéciale pour respectivement créer et détruire
  l'état initial d'un test
- fixture : une fonction qui "fixe" l'état initial pour un test (généralisation du
  setup)
- assertions pour comparer des résultats à des valeurs attendues, ou vérifier un
  comportement attendu (exception, appel de fonction...)
- injection de substitut ou mock
- parallélisation, plugins...

Utiliser un framework de test apporte donc énormément, au prix du temps vite rentabilisé
de prise en main du framework.

L'injection de substitut mérite un point d'attention : il s'agit de remplacer
sélectivement du code difficile à tester (souvent avec un effet de bord) par du code
propre au test, en réimplémentant l'interface du code original.
Par exemple, un objet de connexion à une base de données peut être remplacé par un
objet ne faisant rien, en renvoyant immédiatement une valeur fixée.

Le substitut peut être développé spécifiquement pour émuler un comportement complexe
ou aléatoire, mais avec un retour instantané et répétable.
Il peut aussi être complètement vide, mais permettre de vérifier que l'interface a été
appelée, avec quels arguments...
Certains frameworks de langages dynamiques permettent même de créer des substituts sans
déclarer l'interface du tout, l'interface étant créée à la volée, pour juste débrancher
un effet de bord.
De nombreux plugins ou librairies proposent des substituts clés en main pour les cas
les plus courants : connexion, temps, aléatoire, base de données, logs...

En combinant ces fonctionnalités, un test reste court et lisible. La structure
given/when/then (« étant donné / quand / alors », ou encore arrange/act/assert)
sépare nettement la préparation, l'action testée et la vérification, ce qui en fait
une documentation exécutable :

```python
def test_alerte_envoyee_si_solde_negatif():
    # given : un compte à découvert et un service d'envoi de mail substitué
    mailer = FakeMailer()
    compte = Compte(solde=-50, mailer=mailer)

    # when : on déclenche la vérification du découvert
    compte.verifier_decouvert()

    # then : une alerte, et une seule, a été envoyée au titulaire
    assert mailer.envois == [("alerte_decouvert", compte.titulaire)]
```

Ici le substitut `FakeMailer` n'envoie aucun vrai mail : il se contente d'enregistrer
les appels, ce qui permet d'affirmer que l'alerte a bien été déclenchée, et une seule
fois, sans dépendre d'un serveur de messagerie.

## Accélérer les tests

De nombreuses pistes peuvent permettre d'accélérer les tests :

- modulariser le code et éventuellement le séparer en plusieurs librairies. Ainsi, il y
  a moins de code, d'entrées, de cas limites à tester, et chaque librairie est validée
  indépendamment.
- préparer les artefacts (libs, exécutables, images...) pour le test (et la compilation
  si nécessaire) pour qu'ils soient prêts à l'emploi et en cache. Utiliser une lib
  précompilée est plus rapide que la recompiler avec tout le projet. Si un test a besoin
  d'un conteneur, l'image doit être disponible en cache et prête à l'emploi dès que le
  conteneur est lancé (pas d'entrypoint qui finit la mise en place par exemple).
- profiler ses tests, pour d'abord avoir le temps par test, et ensuite savoir où les
  tests longs passent leur temps.
  Cette étape est essentielle pour ne pas avancer à l'aveugle.
- paralléliser les tests (mais les workers de CI peuvent n'avoir qu'un seul coeur)
- factoriser la mise en place et le nettoyage entre plusieurs tests
- éviter d'attendre pendant un test (`sleep(...)`), à la place réagir quand l'action est
  terminée. Il faut parfois modifier le code pour qu'il reporte son état (code de
  retour, log, variable interne...) ou permette au test de l'obtenir avec une nouvelle
  API.
- réduire la quantité de valeurs différentes testées, pour se concentrer sur les valeurs
  attendues et les cas limites.
- focaliser les tests sur une séquence claire given/when/then, en évitant d'enchainer
  trop d'actions
- optimiser le code dont le test est irréductiblement long. Parfois le problème vient du
  code.
- activer sélectivement certaines options qui ralentissent les tests, comme la mesure
  de la couverture ou la vérification de l'intégrité de la mémoire
- lancer sélectivement les tests selon le code modifié, facile quand le code est bien
  structuré et modulaire

Le remplacement d'une attente fixe par une attente conditionnelle illustre bien ce
gain : au lieu de dormir « assez longtemps » en espérant que l'action soit terminée
(lent, et fragile si la machine est chargée), on rend la main dès que la condition est
remplie.

```python
# Lent et fragile : on attend une durée arbitraire
start_job()
time.sleep(5)
assert result_file.exists()

# Rapide et fiable : on réagit dès que la condition est vraie
job = start_job()
wait_until(lambda: job.is_done(), timeout=5)   # sort dès que c'est prêt
assert result_file.exists()
```

## Compléter les tests

Une fois les tests existants remis en ordre de marche, il faut vérifier que la suite de
test atteint son objectif, et en particulier qu'il ne reste pas de gros trou dans la
couverture de test. Si ce n'est pas déjà fait, il faut ajouter la mesure de la
couverture à son framework. Attention, mesurer la couverture a tendance à ralentir les
tests, parfois beaucoup, et il faut alors prévoir une option pour l'activer
sélectivement.

La couverture de test doit déjà être à peu près homogène sur la base de code, et donc la
première chose à rechercher est une partie du code non testée (fichier complet, classe,
fonction...). Ensuite, la couverture doit permettre de vérifier que la logique métier
(sans effets de bord) est très bien testée, avec une couverture tendant vers 100%.
Enfin, la couverture doit être analysée par rapport aux objectifs et ressources : est-ce
que le code non testé peut l'être facilement ? Est-il réutilisé massivement dans toute
la base de code ? Est-il critique ? Est-ce de la logique métier ?

Une fois la couverture analysée, c'est le moment de revenir sur les tests des
entrées/sorties, dont la couverture de test n'est pas la métrique pertinente. Il est en
effet facile de les couvrir par des tests qui déconnectent tellement d'effets de bord
que le test n'apporte plus beaucoup de garantie. Il faut plutôt vérifier que les cas
normaux, limites et d'erreurs sont testés, vérifier que le lien avec le reste du système
soit réellement testé à un moment ou un autre (connexion à l'API, base de données...),
ou envisager un contrat de communication à valider (OpenAPI par exemple).

Il n'y a pas de chiffre précis de taux de couverture à atteindre, surtout qu'il est
relativement facile de biaiser ce chiffre en déclarant des lignes hors couverture ou en
abusant des substituts. De plus, les derniers pourcents sont bien plus difficiles à
atteindre que les premiers. Un chiffre de 80% est une bonne base de réflexion, les
projets de qualité étant au-dessus. Il est plus important de suivre la tendance : au fur
et à mesure que le projet évolue, la couverture ne doit pas reculer, mais monter (même
lentement) au fur et à mesure que des bugs sont corrigés et donc des tests ajoutés.
Ajouter à ses pipelines de test la vérification que la couverture ne recule pas
empêche en particulier d'ajouter des fonctionnalités sans leurs tests.

## Utiliser l'IA à bon escient

Pour toutes ces tâches, plutôt rébarbatives et vues comme une perte de temps par rapport
à l'avancée du projet, l'IA est un auxiliaire précieux. Il peut être très tentant de
déléguer tout le problème à l'IA (et les derniers modèles feront un bon travail).
Mais les tests sont aussi le système qui garantit le fonctionnement du code,
et qui permettent au développeur d'engager sa responsabilité sur le code livré.
Est-ce que le test généré teste vraiment les points importants ? Ou est-ce qu'il s'agit
juste d'un spaghetti de substituts qui ne teste en fait rien du tout ? Dans tous les cas
la responsabilité est sur les épaules du développeur.

Selon les développeurs et les projets, plusieurs stratégies sont possibles : générer
mais relire soigneusement, travailler par étape à partir des spécifications, écrire
manuellement les tests ou au moins les tests principaux, utiliser une IA vérificatrice
après la génération...

Par délà l'appropriation des tests générés par le développeur, l'IA est surtout une
opportunité en or d'aller plus loin dans les tests : test de performances et
optimisation, test d'interface, fuzz testing, mutation testing... Autant de stratégies
de test avancées qui deviennent accessibles à tous les projets.

## Conclusion

Une fois repris en main, les tests apportent la confiance indispensable pour avancer,
et deviennent un outil de développement qui permet de livrer vite et bien.
À ce moment, l'équipe a acquis toute une gamme de nouvelles compétences,
de la prise en main du framework à l'optimisation, de la refactorisation du code à
l'ajout des tests manquant, qui rendent l'écriture de nouveaux tests banale.
Devenu un outil du quotidien, le test peut être écrit d'abord, dans certains cas en
partant des spécifications, faisant d'une corvée repoussée en fin de projet une étape
préparatoire qui signalera la fin du développement et garantira la qualité.

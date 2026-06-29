# Sortir de l'enfer des tests

## Intro

La nécessité d'écrire des tests automatisés est maintenant bien établie chez les
développeurs. Il s'agit du seul moyen de tester systématiquement et complètement, pour
éviter les régressions ou tout simplement ne pas avancer à l'aveugle.

Mais une fois posé ce consensus, les ennuis commencent. Ecrire les tests est considéré
comme une corvée que personne ne veut faire, souvent repoussée à la fin du projet.
Ensuite les tests sont trop souvent lents, fragiles, longs à maintenir, pas évident à
lancer, incomplets... et on finit par s'habituer à des rapports de test
négatifs ("la CI est tout le temps rouge, mais c'est normal").
On appelle ça la normalisation de la déviance, et ça a finit par faire se crasher
[Columbia](https://fr.wikipedia.org/wiki/Accident_de_la_navette_spatiale_Columbia)).

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
la suite de tests, et peuvent être lancés automatiquement et systématiquement,
typiquement à chaque commit, c'est la fameuse CI.
Ainsi, on s'assure contre la plupart des régressions, et cette information est apportée
rapidement au développeur.

Les tests qui ne peuvent ou ne sont généralement pas automatisés comprennent par exemple
les tests utilisateurs (dont tests d'ergonomie, tests A/B...), les tests de charges,
les tests de performances, les tests de pénétration...

Une fois de plus, les tests automatisés sont là pour apporter un certain niveau de
confiance sur la qualité du code, afin d'atteindre les objectifs de qualité du projet,
dans les moyens alloués.

## Repartir de la base

Les tests font partie de la boite à outil pour atteindre l'objectif de qualité, mais ils
ne sont pas seuls. Nous allons donc déployer plusieurs couches successives d'outils
de qualité.

La première est un formatteur de code, qui permet d'uniformiser le code. Les avantages
sont de faciliter la lecture du code, qui en se présentant toujours sous la même forme
sera perçu plus facilement par le cerveau, de diminuer la charge du développeur,
qui n'a plus à aligner son code à la main, et de nettoyer les comparaisons de code de
toutes les différences de caractères d'espacement, ce qui facilite grandement les
revues de code.

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

La dernière couche est bien sûr d'automatiser tout les outils choisis, au plus près
du développeur. Déjà, un lanceur comme [`doit`](https://pydoit.org/) ou
[`just`](https://just.systems/man/en/introduction.html) permet de lancer tous les outils
de qualité choisis en une commande simple. Ensuite, nous pouvons tirer parti des hooks
de Git pour lancer automatiquement ces outils lors de certains commandes, et typiquement
lors du commit. Des utilitaires comme le fameux [`pre-commit`](https://pre-commit.com/)
ou le plus récent [`prek`](https://prek.j178.dev/) permettent de configurer facilement
les hooks de Git. Je conseille de n'utiliser lors du pre-commit que des outils dont le
temps d'exécution est court (jusqu'à quelques secondes), pour éviter de perdre le fil
à attendre la fin de tests longs au moment du commit.

## Nettoyer les tests

Continuons par nettoyer les tests existants, car on peut bien sûr supprimer des tests.
D'abord, les tests non fiables doivent être retirés, parce qu'ils n'apportent pas
l'information dont l'équipe a besoin : que le test passe ou pas, on n'en sait pas plus
sur la qualité du code testé. Eventuellement, une fois stabilisés, ces tests pourront
être réintégrés.

Ensuite, les tests trop longs n'apportent pas l'information à temps aux développeurs.
Ils peuvent être supprimés, accélérés, ou séparés dans une seconde suite de
tests si vraiment le test est nécessaire et le temps d'exécution vraiment incompressible.
Cette seconde suite de tests sera toujours automatisée, mais pas lancée à chaque commit,
à une fréquence plus faible, comme une fois par jour (souvent la nuit),
ou seulement juste avant fusion sur la branche principale. L'important est que le
développeur n'ait pas besoin du résultat immédiat du test pour continuer à travailler,
mais que l'information apporté par cette suite de tests longs ne soit nécessaire
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

La première chose est d'isoler au maximum les effets de bods, en particulier les
entrées/sorties, pour pouvoir tester le code spécifique au projet et la logique métier
indépendament. Pour tous les projets qui ne sont pas de simples "passe-plats", un
maximum de code doit être testable sans préparation particulière, juste en l'exécutant.

Trions ensuite les effets de bord en 3 catégories : trous noirs, fontaine blanche, et
le reste. Un trou noir est en écriture seul, on ne peut qu'y jeter des données qui sont
immédiatemement perdues. On trouve dans cette catégorie les systèmes de log et de
télémétrie. Une fontaine blanche, l'inverse théorique d'un trou noir, est en lecture
seule et ne peut être qu'initialisée, une seule fois. On trouve dans cette catégorie
le système de configuration, qui réconcilie variables d'environnement, fichiers, 
ligne de commande... et mets le résultat à disposition du reste du code.

Trous noirs et fontaines blanches peuvent avoir une durée de vie équivalente à celle
du programme entier et une portée globale. Ce sont les seuls effets de bord qu'on peut
tolérer à travers toute la base de code. Bien identifiés, une mise en place commune à
tous les test permettra de les gérer une fois pour toute.

Tous les autres effets de bords doivent être isolés, et si possible injectés dans le
code métier propre à leur utilisation, plutôt que détenu par le code métier. En effet,
une dépendance injectée donne toute liberté au test pour déconnecter l'effet de bord
et isoler le code, alors qu'un couplage fort rend le test difficile, surtout avec
les langages statiques.

```
# Difficile à tester
class MyClassWithInternalConnection
private:
    HttpClient http_client
public:
    Constructor(host, port) { http_client = HttpClient(host, port) }

# Facile à tester
class MyClassWithInjectedConnection
private:
    HttpClient http_client
public:
    Constructor(client) { http_client = client }
```

## Prendre en main son framework de test

Tous les principaux langages proposent un ou plusieurs framework de test, qui apportent
leur lot de fonctionnalités en plus de faciliter l'écriture des tests, comme :

- lancement depuis un point unique
- organisation en suite de tests, suite de suite...
- gestion de l'environnement, de l'OS
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

Utiliser un framework de test apporte donc énormément, au prix du temps de prise en 
main du framework.

L'injection de substitut mérite un point d'attention : il s'agit de remplacer
sélectivement du code avec un effet de bord par du code propre au test,
en réimplémentant l'interface du code original.
Par exemple, un object de connexion à une base de données peut être remplacé par un
objet ne faisant rien, on renvoyant immédiatement une valeur fixée.
Le substitut peut être développé spécifiquement pour émuler un comportement complexe,
mais avec un retour instantané et répétable. Il peut aussi être complétement vide,
mais permettre de vérifier que l'interface a été appelée, avec quels arguments...
Certains frameworks permettent même de créer des substituts sans déclarer l'interface
du tout, l'interface étant créée à la volée, pour juste débrancher un effet de bord.

## Accélérer les tests

De nombreuses pistes peuvent permettre d'accélérer les tests :

- modulariser le code et éventuellement le séparer en plusieurs libs. Ainsi, il y a
  moins de code, d'entrées, de cas limites à tester, et chaque lib est validée
  indépendament.
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
- lancer sélectivement les tests selon le code modifié, facile quand le code est bien
  structuré et modulaire

## Compléter les tests

## Utiliser l'IA à bon escient

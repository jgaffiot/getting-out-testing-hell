# Sortir de l'enfer des tests

## Intro

La nécessité d'écrire des tests automatisés est maintenant bien établie chez les
développeurs. Il s'agit du seul moyen de tester systématiquement et complètement, pour
éviter les régressions ou tout simplement ne pas avancer à l'aveugle.

Mais une fois posé ce consensus, les ennuis commencent. Ecrire les tests est considéré
comme une corvée que personne ne veut faire, et souvent repoussée à la fin du projet.
Ensuite les tests sont trop souvent lents, fragiles, longs à maintenir, pas évident à 
lancer, ne couvres pas tout... et on finit par s'habituer à des rapports de test
négatifs ("la CI est tout le temps rouge, mais c'est normal").
Normalisation de la déviance, tout ça, et la navette Columbia finit par se crasher
([true story](https://fr.wikipedia.org/wiki/Accident_de_la_navette_spatiale_Columbia)).

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

Les tests automatisés, par opposition aux tests manuels, constituent tout ou partie de
la suite de tests, et ont comme caractéristique de pouvoir être lancés automatiquement
et systématiquement par le système de gestion de code, typiquement à chaque commit 
pour une utilisation de GitHub ou GitLab. Ainsi, on s'assure contre la plupart des
régressions, et cette information est apportée rapidement au développeur.

Les tests qui ne peuvent ou ne sont généralement pas automatisés comprennent par exemple
les tests utilisateurs (dont tests d'ergonomie, tests A/B...), les tests de charges,
les tests de performances, les tests de pénétration...

Une fois de plus, les tests automatisés sont là pour apporter un certain niveau de
confiance sur la qualité du code, pour atteindre les objectifs de qualité du projet,
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

Commençons par nettoyer les tests existants, car on peut bien sûr supprimer des tests.
D'abord, les tests non fiables doivent être supprimés, parce qu'ils n'apportent pas 
l'information dont l'équipe a besoin : que le test passe ou pas, on n'en sait pas plus
sur la qualité du code testé. Eventuellement, une fois stabilisés, ces tests pourront
être réintégrés.

Ensuite, les tests trop longs n'apportent pas l'information à temps aux développeurs.
Ils doivent être soit supprimés, soit accélérés, soit séparés dans une seconde suite de
tests si vraiment le test est nécessaire et le temps d'exécution incompressible.
Et vraiment incompressible : il existe de multiples façon d'accélérer ses tests,
comme nous le verrons plus tard.
Cette seconde suite de tests sera toujours automatisée, mais pas lancée à chaque commit,
à une fréquence plus faible, comme une fois par jour (souvent la nuit),
ou seulement juste avant fusion sur la branche principale. L'important est que le
développeur n'ait pas besoin du résultat immédiat du test pour continuer à travailler,
mais que l'information apporté par cette suite de tests longs ne soit nécessaire
par exemple que pour une nouvelle version.

Enfin, il ne faut pas hésiter à élaguer la suite de tests : certains tests ne sont pas
pertinents, parce que trop vieux, trop spécifiques, trop couplés ou qui testent trop peu
de code.

## 

## Accélérer les tests



# Sortir de l'enfer des tests

## Intro

La nécessité d'écrire des tests automatisés est maintenant bien établie chez les
développeurs. Il s'agit du seul moyen de tester souvent et complètement, pour
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
chères à acquérir. La suite de test constitue donc un investissement pour le projet
principal, qui doit donc en retirer un bénéfice sur la qualité. Il est donc crucial
de définir (et encore mieux d'écrire) ce qui est attendu des tests. Comme il est
toujours possible d'ajouter des tests, il faut aussi définir a priori les moyens alloués
aux tests, qui permettront d'arbitrer plus tard entre ajouter des tests, ou ajouter
des fonctionnalités. 

Les tests automatisés, par opposition aux tests manuels, constituent tout ou partie de
la suite de tests, et ont comme caractéristique de pouvoir être lancés automatiquement
et systématiquement par le système de gestion de code, typiquement à chaque commit 
pour une utilisation de GitHub ou GitLab. Ainsi, on s'assure contre la plupart des
régressions, et cette information est apportée rapidement au développeur.

Les tests qui ne peuvent ou ne sont généralement pas automatisés comprennent par exemple
les tests utilisateurs (dont tests d'ergonomie ou d'expérience, tests A/B...), les
tests de charges, les tests de performances, les tests de pénétration...

Une fois de plus, les tests automatisés sont là pour apporter un certain niveau de
confiance sur la qualité du code, pour atteindre les objectifs de qualité du projet,
dans les moyens alloués.

## Repartir de la base

Les tests font partie de la boite à outil pour atteindre cet objectif, mais ils ne sont
pas seuls. Nous allons donc déployer plusieurs couches successives d'outils de qualité.

La première est un formatteur de code, qui permet d'uniformiser le code. Les avantages
sont de faciliter la lecture du code, qui en se présentant toujours sous la même forme
sera perçu plus facilement par le cerveau, et de diminuer la charge du développeur,
qui n'a plus à aligner son code à la main.

Ensuite, un ou des analyseur statique (ou linter) permet de capturer en masse des
mauvaises pratiques suivant des règles simples à diagnostiquer. Le compilateur avec tous
ses warnings ou un analyseur de type (pour les codes interprétés) permet ensuite de 
s'assurer de la cohérence d'ensemble, toujours sans avoir exécuté une ligne du code.

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



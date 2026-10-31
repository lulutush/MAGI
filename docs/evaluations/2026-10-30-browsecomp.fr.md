# Évaluation exploratoire BrowseComp — 30 octobre 2026

[English](2026-10-30-browsecomp.md) · [Données chiffrées](2026-10-30-browsecomp.data.json) · [Guide d'évaluation](../EVALUATION.md)

## Résultat et périmètre

**Gain observé en faveur de MAGI sur ce test : 3 réponses correctes sur 8 (37,5 %), contre 2 sur 8 (25,0 %) avec Hermes standard — une bonne réponse supplémentaire, soit +12,5 points de pourcentage.**

**Un gain est observé en faveur de MAGI sur ce test ; sa reproductibilité et sa généralisation restent à confirmer.** Le constat sur cet échantillon et la preuve d'une supériorité générale sont deux conclusions distinctes.

Il s'agit d'une petite étude appariée réellement exécutée sur **une installation particulière d'Hermes**, et non d'un benchmark du seul paquet MAGI public. Ce dépôt fournit une extraction portable de référence ; l'installation évaluée possède aussi ses propres skills complets, mémoires, récupération contextuelle et orchestration. Installer ce dépôt ne reproduit pas cet environnement.

| Condition notée | Réussites | Taux |
| --- | ---: | ---: |
| Hermes standard (`off`) | 2/8 | 25,0 % |
| Hermes + MAGI intégré (`on`) | 3/8 | 37,5 % |

**Résultats appariés :** MAGI réussit une question supplémentaire ; les deux conditions réussissent les mêmes deux autres questions et échouent toutes deux sur cinq questions. Aucune réussite n'est propre au témoin.

**Portée statistique :** avec huit questions et une seule discordance, le test exact de McNemar bilatéral donne **p = 1,0**. Cet échantillon ne suffit pas à établir un avantage reproductible au-delà de ce test. Cette incertitude n'annule pas le gain observé et ne prouve pas l'équivalence des conditions. Les intervalles de Wilson par condition figurent dans les données ; ils ne sont pas des intervalles de confiance de la différence appariée.

Ce n'est **ni un score sur tout BrowseComp ni une soumission à son classement officiel**. Un seul essai par condition et par question ne permet pas de caractériser la variabilité ou la fiabilité générale.

## Protocole fixé avant les essais notés

- Corpus officiel : 1 266 questions. Empreinte du téléchargement et révision de l'évaluateur disponibles ci-dessous et dans les données.
- Tirage : `random.Random(20261030).sample(range(1266), 10)` en Python. Les deux premières questions servent à la calibration, les huit suivantes au score. Les indices commencent à zéro dans les lignes de données CSV, hors en-tête.
- Calibration : `bc-1116`, `bc-0450`. Questions notées, dans l'ordre du tirage : `bc-1147`, `bc-0683`, `bc-0843`, `bc-0076`, `bc-1058`, `bc-1210`, `bc-0536`, `bc-0553`.
- Sélection, protocole et empreintes de l'implémentation figés localement avant l'inférence notée : **pas de préenregistrement public**. Aucune question notée remplacée en fonction de son résultat.
- Ordre alterné `off → on`, puis `on → off`. Deux paires de tâches peuvent tourner simultanément ; les conditions d'une même paire sont séquentielles. Alternance équilibrée, pas randomisation de l'ordre.
- Même moteur demandé : agent natif Hermes `AIAgent`, fournisseur `openai-codex`, identifiant modèle `gpt-6-astra`, raisonnement natif `low`, température native par défaut inchangée. La graine du tirage n'est pas une graine de génération du modèle.
- Chaque essai repart de copies fraîches des mêmes mémoires et du même catalogue initial de skills. Le témoin conserve les bonnes pratiques d'Hermes : ce n'est pas un assistant volontairement affaibli.

### Intervention réellement testée

Le témoin conserve honnêteté, contexte, skills et outils natifs, sans exécuter le workflow spécifique d'orchestration MAGI, de Vérité absolue et de gouvernance des artefacts.

Le bras MAGI charge les **textes intégraux** des trois skills `magi-orchestration`, `verite-absolue-mode` et `magi-struct-comp-governance`, et non quelques règles extraites. Le programme de test exécute les vraies commandes de routage et de récupération contextuelle avant la réponse, puis ajoute leurs résultats à l'entrée du modèle. Les outils natifs de mémoire, skills, sessions, délégation et terminal restent disponibles.

C'est une intervention groupée : **pas une ablation de texte à contexte effectivement identique**. Les réserves initiales de contexte sont les mêmes, mais MAGI en sélectionne et en expose automatiquement davantage. Ce test ne sépare pas l'effet des instructions, de la récupération et de la taille du prompt.

L'installation déclare `manual_command_and_skill_not_global_middleware`. « Intégré » signifie que ces composants sont disponibles et réellement invoqués dans la copie isolée, **pas qu'un middleware global est actif, que chaque fonction est utilisée spontanément, ou que toutes les dimensions de MAGI sont évaluées**.

### Outils, isolation et budgets

Les deux bras disposent des mêmes **25 outils natifs**. Recherche Web réelle via le fournisseur DDGS d'Hermes ; extraction HTTP et analyse des documents ; navigateur natif/Chrome disponible. Après l'incident de calibration, recherche et extraction tournent dans des sous-processus jetables. Les tests réels de recherche, d'extraction et de navigateur réussissent avant la phase notée. Aucun résultat de recherche fictif n'est substitué.

Des espaces de noms de montages et de processus masquent les corrigés, les autres essais et le profil actif ; les écritures restent dans les copies de test. Le réseau demeure accessible pour la recherche publique. **Ce n'est pas une certification générale contre un agent adversarial ni une preuve d'absence de contamination antérieure.** La recherche du benchmark ou de ses corrigés est interdite ; le contrôle des traces n'a trouvé aucune correspondance avec les motifs recherchés, ce qui reste une vérification bornée.

Budgets identiques par essai :

| Limite | Valeur |
| --- | ---: |
| Constructions de requêtes modèle instrumentées, enfants natifs compris si utilisés | 24 |
| Durée contrôlée avant la requête modèle suivante | 360 secondes |
| Seuil de sortie générée contrôlé avant la requête suivante | 12 000 tokens |
| Délai maximal du superviseur séparé | 430 secondes |
| Paires de tâches simultanées | 2 |

Une requête déjà engagée peut dépasser les seuils de durée ou de sortie ; les reprises HTTP ne sont pas toutes comptées individuellement par le compteur de construction. **Ce n'est donc pas un plafond dur de facturation.**

Modèle et effort sont contrôlés sur les requêtes sortantes ; les identifiants de modèles retournés sont enregistrés. L'effort n'est pas répété dans la réponse normalisée : `low` est vérifié à l'envoi, **pas indépendamment dans les poids du fournisseur**.

## Correction et résultats par question

Les réponses sont figées avant une correction séparée, sans historique ni outils, par `gpt-6-astra`/`low`. Le correcteur reçoit la référence et la grille d'équivalence sémantique officielle épinglée, sans étiquette de condition. **Correction en aveugle sur la condition, pas modèle d'une autre famille ni réplication externe indépendante** ; le style d'une réponse peut encore donner des indices.

Le défaut de parsing des groupes de capture de l'évaluateur épinglé a été corrigé : `group(1)` récupère `yes`/`no`, au lieu de comparer la correspondance complète `correct: yes` à `yes`. Des tests positifs et négatifs ont été exécutés. Les réponses créditées et les réponses rejetées non vides ont ensuite été relues face aux références : scores primaires inchangés. La correspondance textuelle stricte n'est qu'un diagnostic secondaire ; ses faux négatifs de Markdown ou d'espacement d'initiales ne déterminent pas le score.

| Question | Hermes standard | MAGI intégré |
| --- | --- | --- |
| `bc-1147` | Limite de ressources ; échec | Limite de ressources ; échec |
| `bc-0683` | Correct | Correct |
| `bc-0843` | Limite de ressources ; échec | Terminé ; incorrect |
| `bc-0076` | Correct | Correct |
| `bc-1058` | Terminé ; incorrect | Terminé ; incorrect |
| `bc-1210` | Limite de ressources ; échec | Limite de ressources ; échec |
| `bc-0536` | Limite de ressources ; échec | Correct |
| `bc-0553` | Terminé ; incorrect | Terminé ; incorrect |

« Terminé » décrit l'exécution, pas la justesse. Les arrêts à la limite comptent comme des échecs selon le budget annoncé ; ils ne sont pas retirés du résultat. L'unique réussite supplémentaire de MAGI (`bc-0536`) oppose donc une réponse correcte à un témoin arrêté par son budget, pas deux réponses finales contradictoires.

Description des échecs : quatre arrêts à la limite, une abstention `UNKNOWN` et une réponse partielle côté témoin ; deux arrêts, deux abstentions et une réponse partielle côté MAGI. Abstention, réponse incomplète et panne d'infrastructure sont distinctes. Aucun taux général d'hallucination n'est mesuré.

## Usage observé des composants

Pour les huit essais notés du bras MAGI :

- corps complets des trois skills présents dans les instructions ;
- **8** exécutions du routeur et **8** récupérations contextuelles ;
- export mémoire natif, registre de projets et Cognee interrogés chacun dans **8** essais ; Cognee utilise la copie figée CHUNKS/vectorielle, sans modèle génératif supplémentaire ;
- **6** contrôles des preuves et **6** créations d'artefacts provisoires, lorsqu'une réponse finale existe ;
- **0** appel natif à la délégation, à l'écriture mémoire ou à la recherche de sessions, malgré leur disponibilité.

**Le contrôle des preuves et la création d'artefacts interviennent après le gel de la réponse notée.** Ils documentent une gouvernance après réponse, mais ne peuvent expliquer une amélioration de cette réponse déjà figée. Le contrôle vérifie des déclarations de présence de preuves, pas l'exactitude face au corrigé. Ces opérations pilotées par le programme de test ne doivent pas être présentées comme des décisions spontanées de l'agent. Le bénéfice individuel de ces composants n'est pas testé.

Aucune invocation spécifique à MAGI n'est observée dans les traces du témoin contrôlées. Les états réinitialisés empêchent l'apprentissage entre questions : bénéfices à long terme de la mémoire, de la délégation et de l'auto-amélioration non mesurés.

## Durée et consommation

Phase notée des agents solveurs uniquement :

| Mesure | Hermes standard | MAGI intégré |
| --- | ---: | ---: |
| Temps médian supervisé par question | 361,8 s | 329,8 s |
| Constructions de requêtes modèle instrumentées | 121 | 139 |
| Appels d'outils demandés par le modèle | 254 | 279 |
| Tokens d'entrée, cache inclus | 3 971 323 | 6 802 479 |
| Sous-ensemble d'entrée en cache | 3 627 648 | 6 206 720 |
| Entrée hors cache | 343 675 | 595 759 |
| Tokens de sortie | 20 885 | 23 391 |
| Sous-ensemble de raisonnement dans la sortie | 9 892 | 10 163 |

Sur cet échantillon, MAGI consomme **73,3 % d'entrée hors cache supplémentaire** et **12,0 % de sortie supplémentaire**. Le cache est déjà inclus dans l'entrée, le raisonnement dans la sortie : aucun de ces sous-ensembles ne doit être ajouté une seconde fois.

Ces durées viennent du superviseur : elles incluent le démarrage du processus et les contrôles/artefacts après réponse lorsqu'ils sont atteints, mais excluent la correction séparée, la préparation, l'orchestration parente et la conversation. Réseau variable, caches, concurrence et arrêts aux limites rendent les médianes descriptives ; elles ne prouvent pas que MAGI est plus rapide. Le total d'appels d'outils demandés par le modèle exclut les commandes déterministes du programme de test avant/après réponse, même si leur durée entre dans celle mesurée par le superviseur.

### Calibration et autres consommations mesurées

Calibration valide : **1/2 dans chaque condition**, hors score final. Une première calibration a été interrompue après un crash natif du tas mémoire pendant une extraction concurrente. Recherche et extraction ont été déplacées dans des sous-processus jetables pour **les deux bras**, les tests réels rejoués, puis les mêmes questions de calibration réexécutées. Réparation d'infrastructure avant les questions notées, pas remplacement opportuniste.

| Phase des solveurs | Entrée, cache inclus | Sous-ensemble en cache | Sortie | Requêtes enregistrées / réponses normalisées |
| --- | ---: | ---: | ---: | ---: |
| Calibration interrompue (`calibration-v1`) | 2 166 876 | 1 953 408 | 7 038 | 49 / 48 |
| Calibration valide (`calibration-v2`) | 3 158 744 | 2 906 240 | 11 077 | 74 / 73 |
| Essais notés (`main-v1`) | 10 773 802 | 9 834 368 | 44 276 | 260 / 252 |

Correcteur séparé : calibration **2 074 tokens d'entrée / 141 de sortie** ; phase notée **6 721 d'entrée / 528 de sortie**. Aucun cache d'entrée enregistré pour le correcteur. La consommation enregistrée de l'essai interrompu reste visible.

Ces compteurs couvrent les réponses enregistrées. Appels sans retour ou en cours, reprises HTTP, préparation, orchestration et conversation ne sont pas intégralement mesurés. L'écart entre requêtes construites et réponses n'est pas à lui seul un nombre d'erreurs ou d'appels facturables. **Aucun coût monétaire ni total exhaustif du projet n'est annoncé.**

## Données publiques et limites de reproductibilité

Le [fichier de données](2026-10-30-browsecomp.data.json) contient graine et indices de sélection, paramètres du protocole, mesures agrégées et individuelles des deux phases, consommation enregistrée, compteurs de composants et empreintes des sources locales conservées. Une empreinte établit l'identité d'octets si la source est disponible, pas leur vérité, une validation externe ou un préenregistrement public.

Contrôles hors ligne, depuis la racine du dépôt :

```sh
python3 -m unittest discover -s tests -p 'test_benchmark_report.py' -v
```

Ils recalculent sélection, résultats appariés, intervalles, médianes et totaux de tokens enregistrés. **Ils n'appellent aucun modèle, ne rejouent pas BrowseComp et ne recorrigent pas indépendamment les réponses.**

Ne sont pas publiés : textes des questions et corrigés, réponses brutes, traces modèle/outils, mémoires personnelles, conversations, prompts et skills privés, identifiants, configuration propre au serveur, programme d'exécution privé et copie de récupération. C'est donc une **publication de résultats et de méthode expurgée, pas une livraison intégralement reproductible de bout en bout**. Les étiquettes de réussite et l'environnement complet ne sont pas reconstructibles indépendamment à partir de ce seul sous-ensemble.

Sources :

- [Corpus officiel BrowseComp](https://openaipublic.blob.core.windows.net/simple-evals/browse_comp_test_set.csv), SHA-256 du CSV téléchargé : `7b24471cd5b3eb2a46830a14802b5c029ea62f488ff75a0f88af7923d1454abf`.
- [Évaluateur officiel épinglé](https://github.com/openai/simple-evals/blob/652c89d0ca9df547706735883097e9537d40dc47/browsecomp_eval.py), révision `652c89d0ca9df547706735883097e9537d40dc47` ; SHA-256 téléchargé : `0bfb33cfdf5fa0e0d7da48068cc86c5a22acc755979be4a2b46f8a821cc44b74`.

## Conclusion

**Le résultat de ce test est favorable à MAGI : une question supplémentaire résolue, soit +12,5 points de bonnes réponses.** Il s'accompagne d'une consommation de tokens supérieure. Sa reproductibilité et sa généralisation restent à confirmer : huit questions et une seule discordance ne démontrent ni supériorité générale, ni équivalence, ni contribution propre d'un composant. L'évolution du Web et une possible exposition préalable du modèle au corpus public limitent encore l'interprétation.

Une étude plus solide nécessiterait un échantillon réservé plus large, des répétitions annoncées, un programme et des contextes non privés reproductibles, des ablations à contexte contrôlé et une correction indépendante. Ce sont des pistes futures, **pas des essais réalisés ni une promesse de résultat favorable**.

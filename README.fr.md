# MAGI

**Un protocole de fiabilité pour assistants IA : contexte, outils, preuves et rigueur adaptée.**

[English](README.md) · [Protocole](protocol/MAGI.md) · [Adaptateurs](docs/ADAPTERS.md)

**Version open source expérimentale sous Apache 2.0.** Aucun compte, secret, profil personnel ou historique de conversation n'est fourni.

## L'idée

MAGI organise le travail autour du modèle : quand répondre simplement, rappeler un contexte pertinent, consulter une source, utiliser un outil, vérifier un résultat, demander une précision ou déléguer. Le protocole complet inclut mémoire, état de projet, procédures, preuves, autorisations et gouvernance des artefacts — pas seulement du JSON.

Ce n'est ni un nouveau modèle, ni un système de permissions, ni une garantie de meilleures réponses. Les instructions orientent le modèle ; elles ne créent pas un verrou de sécurité. Le niveau de raisonnement natif du modèle reste indépendant de la rigueur MAGI.

## Essai immédiat

Python 3.10 ou supérieur, aucune dépendance d'exécution externe. Récupérer le dépôt :

```sh
git clone https://github.com/lulutush/MAGI.git
cd MAGI
```

Puis lancer :

```sh
python3 -m magi --version
python3 -m magi route "Vérifie l'état actuel du serveur" --pretty
python3 -m magi validate examples/artifact.json --pretty
python3 -m unittest discover -s tests -v
```

Le cœur Python ne fait aucun appel réseau ou modèle et ne lit pas vos mémoires, conversations ou identifiants. Ces commandes vérifient le code ; elles ne prouvent pas un gain de qualité des réponses d'une IA.

## Trois façons de l'utiliser

- **Hermes Agent :** skill autonome, chargé explicitement avec `/skill magi` après installation dans le profil choisi.
- **Claude Code :** fichier `CLAUDE.md` autonome pour un projet d'essai. Ne remplacez pas les instructions existantes ; fusionnez-les après lecture.
- **GPT / conversation :** instructions autonomes à copier. Ni outils ni mémoire persistante ne sont ajoutés par ce texte. Un GPT ne peut exécuter le cœur Python que si son environnement offre réellement cette capacité, et cette intégration n'est pas automatisée ici.

L'installateur prépare uniquement la destination explicitement choisie et affiche d'abord un aperçu :

```sh
TRIAL_PARENT="$(mktemp -d)"
python3 tools/install_adapter.py hermes --destination "$TRIAL_PARENT/magi"
python3 tools/install_adapter.py hermes --destination "$TRIAL_PARENT/magi" --apply
```

Le parent doit exister hors du dépôt et ne comporter aucun lien symbolique ; le dossier cible doit être absent. L’installateur sécurisé nécessite POSIX, contrairement au cœur Python qui n’en dépend pas. Sans `--apply`, seule une simulation est affichée.

## Confidentialité et limites

- Fichiers génériques écrits pour la diffusion, exemples fictifs, modèles vides.
- Aucun export d'installation, de base mémoire, d'historique Git antérieur ou de configuration privée.
- Aucune télémétrie réseau ni collecte automatique dans le cœur fourni.
- Les plateformes hôtes restent responsables de leur propre traitement des données.
- Le routeur EN/FR est heuristique : il peut manquer une formulation. Il ne décide jamais des permissions.
- Le contrôle de preuves vérifie des déclarations ; il n'authentifie pas la réalité des preuves.
- Aucun bénéfice universel n'est revendiqué ; protocole d'évaluation comparatif fourni.

## Licence et origine

**MAGI — projet initié et piloté par Lucas.**

Le code, le protocole et la documentation originaux sont distribués sous [Apache 2.0](LICENSE). Tout le monde peut les utiliser, les modifier et les redistribuer, y compris commercialement, dans le respect de cette licence et des mentions applicables. Cela ne donne pas de droit d’écriture sur le dépôt officiel. Voir [NOTICE](NOTICE), [la provenance](NOTICE.md) et [les métadonnées de citation facultative](CITATION.cff).

Les tests ont été exécutés localement. GitHub Actions n’est pas activé dans cette première distribution ; un [exemple de CI](docs/CI.md) est fourni. Voir [les vérifications et leurs limites](docs/VERIFICATION.md).

Le compte GitHub choisi, les commits et une signature éventuelle peuvent identifier le responsable : un contenu sans données privées ne rend pas automatiquement le compte anonyme.

Voir [le périmètre inclus/exclu](docs/SCOPE.md), [l’architecture](docs/ARCHITECTURE.md), [les profils d’artefacts](docs/ARTIFACT-PROFILES.md), [la confidentialité](docs/PRIVACY.md), [les évaluations](docs/EVALUATION.md) et [la liste de contrôle de publication](docs/PUBLICATION.md).

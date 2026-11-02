# Pour Codex : réparer WallpaperMaison sur ce PC

L'utilisateur veut que WallpaperMaison installe et synchronise correctement les fonds d'écran Linux et VS Code sur sa machine et dans ses sessions graphiques. Il a constaté que les icônes de l'extension VS Code sont présentes, mais que le fond ne change pas. Une ancienne installation a aussi empêché le lancement de `code` à cause d'un lanceur ou d'un alias pointant vers `~/.local/bin/code` absent ou incorrect.

Travaille directement sur ce PC et sur la copie réelle du projet. Ne considère pas le problème comme résolu tant que tu n'as pas vérifié le fonctionnement possible ici. Fais les corrections nécessaires, explique les éventuelles limites et indique à l'utilisateur comment tester. Respecte les modifications déjà présentes et ne supprime pas ses données, ses extensions ou sa configuration personnelle.

## 1. Trouver la copie du projet et sa version

Demande à l'utilisateur où se trouve le projet uniquement si tu ne peux pas le trouver. Emplacements possibles : `~/Wallpaper`, `~/reseau/Perso/Wallpaper` et `~/reseau/Perso/Bureau/Wallpaper`. Dans le projet, examine `git status`, la branche et les modifications avant toute mise à jour.

Des corrections peuvent avoir été préparées sur un autre ordinateur sans encore être publiées sur GitHub. Ne suppose donc pas qu'un `git pull` contient la dernière version. Si la version distante est disponible et qu'une mise à jour est possible sans écraser le travail local, récupère-la ; sinon, explique précisément ce qui manque. Ne fais ni `git reset --hard`, ni suppression de fichiers pour forcer la mise à jour.

## 2. Récupérer les indices

Si `debug.sh` existe, reproduis d'abord le problème dans la session graphique concernée, idéalement avec VS Code ouvert, puis lance depuis le dossier du projet :

```bash
bash debug.sh
```

Le chemin du rapport créé dans le dossier personnel s'affiche dans le terminal. Lis ce rapport localement. Il peut contenir des chemins personnels et des extraits de journaux : ne l'envoie à personne sans instruction explicite.

Le script examine notamment le type de session, les commandes disponibles, `bubblewrap`, le workbench détecté, les raccourcis, l'extension, l'état partagé, le serveur média, les montages des processus VS Code et les derniers journaux de WallpaperMaison. Si le script n'existe pas, collecte ces informations par des commandes de lecture et consulte `~/.cache/wallpapermaison/logs/`.

Examine aussi les erreurs visibles dans le terminal de lancement et dans les outils de développement de VS Code si l'environnement permet de les ouvrir. Cherche les erreurs de chargement du média, de CSP, de décodage vidéo et les échecs d'injection. Ne publie pas un diagnostic fondé uniquement sur la présence des icônes.

## 3. Vérifier et réparer le lancement de VS Code

- Identifie l'installation réelle de VS Code : paquet natif, installation portable, Flatpak ou autre, ainsi que l'exécutable effectivement lancé. Ne suppose pas que `/usr/bin/code`, `/usr/apps/VSCode-linux-x64` ou un chemin IUT existe.
- Vérifie `command -v code`, le fichier ou lien qu'il désigne, les raccourcis `.desktop` et tout ancien alias `code`. Répare les éléments cassés créés par WallpaperMaison, sans remplacer aveuglément un fichier personnel ou l'exécutable système.
- Examine `scripts/code-launcher.sh`, `scripts/setup.sh` et `scripts/run.sh`. Le lanceur prévu par la version corrigée s'appelle `wallpapermaison-code` et le raccourci est « Visual Studio Code (WallpaperMaison) ». Vérifie qu'il transmet les arguments et que VS Code démarre aussi lorsque l'injection échoue.
- Pour l'injection actuelle, vérifie que le bon `workbench.html` est détecté et que `bwrap --dev-bind / / true` fonctionne pour cet utilisateur. Vérifie le montage dans le processus VS Code réellement ouvert. Ferme et relance toutes les fenêtres VS Code quand c'est nécessaire pour tester un nouveau montage.
- Les installations Flatpak et les systèmes qui interdisent les espaces de noms utilisateur ne sont pas garanties par l'implémentation actuelle. Diagnostique le cas réel ; si tu adaptes le code, teste cette adaptation et explique ses limites. Ne prétends pas qu'une installation est prise en charge sans preuve.

## 4. Vérifier le fond et la synchronisation

Suis les données de bout en bout : sélection du fond dans WallpaperMaison, fichier `~/.config/wallpapermaison/current_wallpaper.json`, extension installée dans `~/.vscode/extensions/budicuy.live-wallpaper-99.0.0`, fichier `live_state.json`, média préparé, serveur HTTP local et workbench injecté.

Inspecte en particulier :

- `app/automation/vscode_sync.py`, `vscode_media.py` et `vscode_media_server.py` pour la publication de l'état, le chemin du média et le serveur local ;
- `scripts/patch_vscode_html.py` et `vscode-extension/out/extension.js` pour la réception et l'affichage des changements ;
- les permissions de lecture, les chemins avec espaces, les liens cassés et le dossier personnel de l'utilisateur courant ;
- les codecs et le résultat de lecture d'une image simple puis d'une vidéo. Une image qui fonctionne et une vidéo qui échoue orientent vers le décodage ou le transcodage ;
- la disponibilité du serveur local et les messages de la console VS Code. Ne désactive pas globalement les protections du système pour faire fonctionner le projet.

Teste deux fonds différents successivement afin de vérifier une mise à jour en direct, puis redémarre VS Code pour vérifier la persistance. Vérifie également le fond Linux avec le moteur réellement disponible pour le bureau et la session de cet utilisateur. Indique les tests graphiques que tu n'as pas pu effectuer.

## 5. Installation et sessions

Examine `scripts/install.sh`, `scripts/setup.sh`, `scripts/session-start.sh`, `scripts/run.sh` et `scripts/write_desktop_entries.py`. L'installation locale se lance depuis le dossier du projet avec :

```bash
bash scripts/install.sh
```

Vérifie les erreurs de dépendances, les chemins absolus dans les raccourcis et XDG Autostart, ainsi que la restauration au redémarrage. Si le dossier personnel est temporaire ou si le projet est sur NFS, vérifie ce qui persiste réellement sur cette machine : un fichier autostart perdu à chaque connexion ne peut pas être restauré tout seul. Si une intervention administrateur est nécessaire, explique-la ; ne promets pas une prise en charge universelle sans la vérifier.

Pour corriger le code, ajoute des tests ciblés sur les causes trouvées et exécute les tests pertinents. Évite d'écraser les configurations existantes, de supprimer des extensions tierces ou de masquer les erreurs. Termine en indiquant les fichiers modifiés, les commandes de mise à jour ou d'installation adaptées à cette machine et les résultats concrets des tests.

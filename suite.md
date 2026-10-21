# Suite — dépannage du fond d’écran VS Code

Dernière mise à jour : 28 septembre 2026, 18:14 (Europe/Paris)

## Résultat

Le fond vidéo est de nouveau visible dans VS Code et s’étend à la taille de la fenêtre (`object-fit: fill`). La cause qui le masquait était le fond opaque de la grille racine du workbench. Le correctif est enregistré dans le dépôt et dans le HTML overlay utilisé par le lanceur. VS Code a été fermé puis rouvert par `~/.local/bin/code` sans port de diagnostic ; cette fenêtre est actuellement ouverte.

## Cause confirmée

La vidéo décodait et avançait, mais un `.monaco-grid-view` racine, couvrant toute la fenêtre, la recouvrait avec un fond opaque (`rgb(28, 31, 33)`, puis `rgb(33, 33, 30)`). Le CSS précédent ne rendait transparent que les grids situés sous `.part.editor`. La grille racine est en dehors de cette branche du DOM.

J’ai ajouté à `scripts/patch_vscode_html.py` des règles transparentes pour `.monaco-workbench .monaco-grid-view`, ses `.monaco-grid-branch-node` et ses `.split-view-view`, après que la vidéo est prête. Dans la fenêtre de diagnostic, le fond calculé est devenu transparent et une capture réelle montre le wallpaper derrière l’écran d’accueil de VS Code.

## Modifications conservées

- `scripts/patch_vscode_html.py` : recherche du workbench réparée ; taille JSONC `fill` par défaut ; CSS transparent étendu à la grille racine ; remplacement vidéo en double tampon et attente de la première image décodée ; CSP idempotente ; génération atomique du dossier overlay `workbench.html` + `workbench.js`.
- `scripts/code-launcher.sh` : `bwrap` monte tout le dossier overlay plutôt que le seul HTML, pour que les remplacements atomiques restent visibles dans la sandbox.
- `~/.local/bin/code`, utilisé par le raccourci GNOME, est identique au script du dépôt.
- `vscode-extension/out/liveWallpaper/LiveWallpaper.js` attend la fin du patcher avant le rechargement ; la taille par défaut du manifeste est `fill`.
- Les changements du binaire et les autorisations CSP demandés par l’utilisateur sont conservés.

## Pourquoi les essais précédents échouaient

1. Le raccourci GNOME lançait `~/.local/bin/code`, qui pouvait être en retard sur le lanceur modifié dans le dépôt.
2. L’ancien montage `bwrap --ro-bind` ne couvrait qu’un fichier. Après remplacement atomique du HTML, le processus ouvert gardait l’ancien inode ; un simple rechargement ne renouvelait pas le montage.
3. Même avec le bon montage, la grille racine plein écran restait opaque. Le wallpaper était donc présent sous VS Code mais invisible, ce qui donnait l’impression qu’il disparaissait.
4. Un premier `Page.reload` de diagnostic a momentanément renvoyé une page sans vidéo, puis cette instance s’est fermée. Je n’ai pas pris ce résultat isolé pour une validation : une ouverture complète ultérieure a affiché la vidéo, puis a tenu pendant le suivi.

## Vérifications faites

- Capture de la fenêtre de diagnostic : wallpaper effectivement visible dans le workbench, couvrant l’espace de travail.
- Suivi d’environ 65 secondes, avec mesures toutes les 5 secondes : classe `wallpapermaison-live-ready` présente, vidéo `paused=false`, `readyState=4`, opacité `0.35`, `object-fit=fill`, grille racine transparente à chaque mesure. Les clips bouclent normalement ; pendant un changement, l’ancienne vidéo reste affichée jusqu’à ce que la suivante soit prête.
- Fermeture de la fenêtre de diagnostic, puis ouverture propre sans `--remote-debugging-port`. Le processus réel monte bien `.../.config/wallpapermaison/vscode/workbench` avec `bwrap`, le port de diagnostic n’est plus ouvert et le journal de la nouvelle session confirme l’activation de l’extension `budicuy.live-wallpaper`.
- Le serveur média local répond `200 OK` pour le média actif.
- `bash -n scripts/code-launcher.sh`
- `python3 -m py_compile scripts/patch_vscode_html.py`
- `node --check vscode-extension/out/liveWallpaper/LiveWallpaper.js`
- JSON de `vscode-extension/package.json` valide
- JavaScript injecté extrait du HTML généré : `node --check` valide
- `git diff --check`
- Lanceur installé identique au script du dépôt

GNOME a refusé la capture d’écran automatisée de la dernière ouverture normale (`Screenshot is not allowed`). La capture visuelle de preuve provient de la fenêtre réelle juste avant sa fermeture ; la réouverture normale utilise le même lanceur et le même overlay corrigé.

Le fichier `hello.txt`, déjà présent dans le dépôt, a été laissé intact.

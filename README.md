# WallpaperMaison 🌌
> **L'alternative moderne et haut de gamme à Wallpaper Engine pour Linux Fedora**

**WallpaperMaison** est une application desktop moderne, modulaire, performante et soignée, conçue pour gérer vos fonds d'écran sous Linux (Fedora 38/39/40/41+). Elle prend en charge les images haute résolution, les GIFs animés, les vidéos (MP4, WebM, MKV) avec accélération matérielle, les playlists automatiques, le multi-écrans, un pipeline de retouche d'image non destructif, des automatisations intelligentes et une intégration native au System Tray.

---

## ✨ Fonctionnalités Clés

* **Multimédia Complet :**
  * Images statiques : PNG, JPG, JPEG, WEBP, BMP, AVIF, TIFF.
  * Animations : GIF, WEBP animé.
  * Vidéos : MP4, WEBM, MKV, MOV, AVI, FLV (décodage GPU via VA-API / NVDEC).
* **Architecture Multi-Moteurs Adaptative :**
  * Détection automatique de l'environnement (GNOME, KDE Plasma, Sway, Hyprland).
  * Détection de la session d'affichage (**Wayland** ou **X11**).
  * Sélection transparente du meilleur moteur : `GNOME GSettings`, `KDE DBus plasmashell`, `mpvpaper`, `swww`, `feh`, `xwinwrap`.
* **Éditeur d'Image Non Destructif :**
  * Réglages en temps réel sur canvas : Luminosité, Contraste, Saturation, Exposition, Température, Teinte, Flou (Blur), Vignettage, Noir & Blanc, Sépia, Rotation, Miroir H/V.
  * Le fichier original n'est jamais altéré ; les rendus ajustés sont mis en cache intelligemment.
* **Gestion Multi-Moniteurs :**
  * Détection automatique des écrans, résolutions et fréquences de rafraîchissement (Hz).
  * Modes : Fond identique partout, fond distinct par écran, ou mode panoramique étendu (*Span*).
* **Playlists & Rotations Intelligentes :**
  * Création de playlists thématiques (Nature, Anime, Dark/Minimal, Gaming, Night).
  * Minuteur de rotation paramétrable (30s, 1m, 5m, 10m, 30m, 1h, ou personnalisé).
  * Modes : Ordre de playlist, aléatoire, aléatoire sans répétition (*shuffle pool*), favoris uniquement.
* **Automatisations & Déclencheurs Contextuels :**
  * Règles horaires (ex: 08:00 playlist Matin, 22:00 playlist Nuit).
  * Détection d'alimentation : bascule automatique sur fond statique lors du passage sur batterie, et reprise des vidéos sur secteur.
  * Détection des jeux et fenêtres plein écran : mise en pause automatique de la vidéo pour libérer 100% du GPU et CPU.
* **Profils de Performance :**
  * `Quality` : 60 FPS natif, décodage matériel permanent.
  * `Balanced` : 30 FPS, pause automatique en jeu ou sur batterie (recommandé).
  * `Performance` : 24 FPS, 1080p max, consommation minimale.
  * `Battery Saver` : fonds animés coupés, forçage statique.
* **Interface Soignée & Haute Fidélité :**
  * Réalisée avec PyWebView + HTML5 + CSS3 + Vanilla JavaScript.
  * Thème sombre obsidienne, glassmorphism léger avec flou d'arrière-plan, transitions fluides.
  * Aucun dégradé violet/cyan générique.
  * Bibliothèque avec modes Grille, Grille Compacte et Liste détaillée, recherche instantanée et filtres par tags.
* **System Tray & Raccourcis :**
  * Icône dans la barre de notification avec menu d'actions rapides (Suivant, Précédent, Pause/Reprendre, Favori, Choix du profil, Quitter).
  * Raccourci XDG `.desktop` et intégration native au lanceur d'applications Fedora.

---

## 🚀 Installation

### ⚡ Installation en une seule ligne (Recommandé)
Vous pouvez installer ou restaurer **WallpaperMaison** sur n'importe quelle machine (y compris un nouveau poste de travail à l'IUT) avec une seule commande à copier-coller :

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Shunikai972/Wallpaper/main/scripts/install.sh)"
```

Cette commande clone automatiquement le dépôt (ou le met à jour), configure l'environnement Python sans nécessiter les droits `root`/`sudo`, crée le lanceur GNOME et indexe vos fonds d'écran.

---

### 🖥️ Installation sur un nouveau PC (Poste IUT / Fedora Silverblue)

Sur un nouveau PC Linux où votre session locale vient d'être créée (ou réinitialisée), le projet et tous vos réglages sont déjà présents sur votre partage réseau persistant (`~/reseau/Perso`).

Pour configurer instantanément la machine sans droits `root` (création des wrappers de codecs H.264, configuration de l'autostart GNOME et systemd, liens persistants, et déploiement de l'extension VS Code), **exécutez simplement cette commande** :

```bash
~/reseau/Perso/Bureau/Wallpaper/scripts/setup.sh
```

Ou si vous êtes déjà positionné dans le dossier :
```bash
./scripts/setup.sh
```

**Ce que fait `setup.sh` de manière 100% automatique et idempotente :**
1. **Auto-détection de l'environnement** : identifie Fedora Silverblue, Wayland, GNOME et le partage persistant NFS.
2. **Configuration autonome des codecs vidéo** : si le système hôte ne dispose pas des codecs H.264/HEVC propriétaires ou de `mpv`, configure automatiquement l'environnement Flatpak `io.mpv.Mpv` et les wrappers `~/.local/bin/mpv` et `~/.local/bin/ffmpeg-full`.
3. **Environnement virtuel Python** : initialise `.venv` avec `--system-site-packages` pour accéder aux bindings natifs GTK/GObject sans compilation.
4. **Liens symboliques persistants** : raccorde `~/.config/wallpapermaison`, `~/.local/share/wallpapermaison` et `~/.cache/wallpapermaison` vers le partage NFS.
5. **Démarrage automatique (Autostart)** :
   - Installe le fichier XDG `~/.config/autostart/wallpapermaison.desktop` avec boucle de résolution de chemin portable.
   - Installe et active le service utilisateur systemd `~/.config/systemd/user/wallpapermaison.service` rattaché à `graphical-session.target`.
6. **Auto-guérison Shell (`~/.bashrc.d`)** : corrige le bug de condition Debian (`/etc/apt`) dans `~/.bashrc` et installe le script d'auto-restauration dans `~/.bashrc.d/wallpapermaison.sh`.
7. **Déploiement de l'extension VS Code** : synchronise le dossier de l'extension dans `~/.vscode/extensions/` et `/var/tmp/visual_extensions/`.
8. **Auto-test** : valide les imports Python, le moteur de colorimétrie et le lecteur MPV.

---

### 💾 Mode Persistant Réseau (Spécial IUT / NFS)
Si vous travaillez sur une machine où la session locale est réinitialisée à chaque redémarrage (ex: postes IUT avec stockage réseau `~/reseau/Perso`) :
* L'installateur détecte automatiquement le partage réseau et applique l'**installation persistante**.
* Vos fonds d'écran, base de données SQLite, miniatures en cache, playlists et configurations sont conservés de manière permanente dans `~/reseau/Perso/`.
* Vos données sont instantanément retrouvées sur **n'importe quel ordinateur** sans réinstallation !

Vous pouvez exécuter ou relancer l'installateur à tout moment :
```bash
./scripts/install.sh --persistent -y
```

---

## 🎮 Lancement de l'Application

### Depuis le terminal
```bash
./scripts/run.sh
```

### Options en ligne de commande
```bash
# Démarrer minimisé dans la barre des tâches
./scripts/run.sh --minimized

# Lancer en mode démon d'arrière-plan sans interface
./scripts/run.sh --daemon

# Scanner un dossier spécifique et l'importer en bibliothèque
./scripts/run.sh --scan ~/Pictures/Wallpapers

# Afficher la version
./scripts/run.sh --version
```

### Depuis le menu d'applications GNOME / KDE
Recherchez simplement **WallpaperMaison** dans votre lanceur d'applications ou via la touche `Super`.

---

## 📦 Architecture du Projet

Le projet adopte une séparation stricte des responsabilités, sans fichier monolithique :

```
wallpapermaison/
├── app/
│   ├── main.py                     # Point d'entrée principal PyWebView, CLI flags et cycle de vie
│   ├── core/
│   │   ├── config.py               # Gestionnaire de configuration XDG, chemins et profils
│   │   ├── events.py               # Bus d'événements pub/sub interne thread-safe
│   │   └── logger.py               # Journalisation rotative (fichier + buffer mémoire UI)
│   ├── storage/
│   │   ├── database.py             # SQLite avec migrations automatiques et CRUD complet
│   │   └── cache.py                # Gestion du cache miniatures et contrôle du quota disque
│   ├── system/
│   │   ├── detector.py             # Détection Fedora, Wayland/X11, GNOME/KDE, paquets DNF
│   │   ├── monitors.py             # Détection multi-écrans (xrandr, wlr-randr, sysfs)
│   │   ├── power.py                # Surveillance batterie / secteur (sysfs, upower)
│   │   ├── window_monitor.py       # Détection plein écran / jeux et verrouillage de session
│   │   ├── autostart.py            # Gestion XDG Autostart (.desktop)
│   │   └── tray.py                 # Intégration icône System Tray
│   ├── media/
│   │   ├── scanner.py              # Scanner asynchrone de dossiers avec dédoublonnage hash
│   │   ├── metadata.py             # Extraction métadonnées vidéo/image (ffprobe, Pillow)
│   │   └── thumbnail.py            # Générateur de miniatures haute performance (JPEG/WebP)
│   ├── image_processing/
│   │   ├── adjuster.py             # Pipeline non destructif (Pillow) : filtres, géométrie, cache
│   │   └── colorimetry.py          # Moteur colorimétrique avancé (WCAG AAA >= 7:1, CIE-Lab, LERP)
│   ├── wallpaper/
│   │   ├── base.py                 # Classe abstraite BaseWallpaperEngine
│   │   ├── manager.py              # Orchestrateur central et sélecteur de moteur
│   │   └── engines/
│   │       ├── gnome_engine.py     # Moteur GSettings pour GNOME
│   │       ├── kde_engine.py       # Moteur DBus Plasmashell pour KDE
│   │       ├── mpvpaper_engine.py  # Moteur vidéo fluide Wayland via mpvpaper
│   │       ├── gtk_video_engine.py # Moteur vidéo autonome Wayland haute fidélité
│   │       ├── video_bg_worker.py  # Démon vidéo isolé avec socket IPC par utilisateur
│   │       ├── swww_engine.py      # Moteur animé/transitions Wayland via swww
│   │       ├── xwinwrap_engine.py  # Moteur vidéo X11 via xwinwrap + mpv
│   │       ├── feh_engine.py       # Moteur statique X11 via feh
│   │       └── fallback_engine.py  # Moteur de secours sans crash avec diagnostics
│   ├── automation/
│   │   ├── scheduler.py            # Minuteur de rotation automatique et sélection
│   │   └── rules.py                # Moteur de règles contextuelles (heures, batterie, jeux)
│   └── api/
│       └── bridge.py               # Passerelle API Python ↔ JavaScript pour PyWebView
│
├── ui/                             # Interface graphique SPA
│   ├── index.html                  # Shell SPA moderne
│   ├── css/
│   │   ├── variables.css           # Tokens design (palette sombre noble, blur, rayons)
│   │   ├── base.css                # Reset, scrollbars custom, layout
│   │   ├── components.css          # Cartes, modales, toasts, context-menu, switches, sliders
│   │   └── pages.css               # Styles spécifiques Dashboard, Library, Preview, Editor, etc.
│   ├── js/
│   │   ├── api.js                  # Client API PyWebView avec mode simulation navigateur
│   │   ├── store.js                # Store d'état réactif centralisé
│   │   ├── router.js               # Routeur SPA fluide
│   │   ├── components/             # Toasts, modales, menu contextuel
│   │   └── pages/                  # Contrôleurs de chaque vue
│   └── assets/
│       └── logo.svg                # Logo vectoriel de l'application
│
├── vscode-extension/               # Extension VS Code Live Wallpaper avec synchronisation dynamique
│   ├── out/colors/                 # Moteur JS d'extraction colorimétrique et lissage temporel
│   ├── out/liveWallpaper/          # Intégration sûre sans écriture root et lecteur Webview
│   └── package.json                # Schéma complet des paramètres liveWallpaper.colors.*
│
├── scripts/
│   ├── setup.sh                    # Installation autonome & idempotente sans root pour nouveau PC
│   ├── install.sh                  # Installeur universel interactif / one-liner
│   ├── run.sh                      # Lanceur dynamique avec auto-guérison et attente session
│   └── autostart.desktop           # Définition XDG Autostart portable
├── tests/                          # Suite complète de tests unitaires (29/29 validés)
│   ├── test_storage.py             # Tests SQLite et migrations
│   ├── test_adjuster.py            # Tests traitement d'image non destructif
│   ├── test_colorimetry.py         # Tests conversions CIE-Lab, WCAG 2.1 et garantie de contraste
│   ├── test_autostart.py           # Tests XDG Autostart, systemd --user et persistance NFS
│   ├── test_scanner.py             # Tests scanner, metadata et miniatures
│   ├── test_wallpaper_manager.py   # Tests orchestrateur de moteurs
│   └── test_bridge.py              # Tests API Bridge PyWebView
├── requirements.txt                # Dépendances Python
└── wallpapermaison.desktop         # Entrée standard XDG Desktop
```

---

## 🖥️ Matrice de Compatibilité Fedora & Environnements

| Environnement | Session | Images Statiques | GIFs Animés | Vidéos (MP4 / WebM) |
|---|---|---|---|---|
| **Fedora GNOME** (Défaut) | **Wayland** | `GSettings` (Natif) | `Hanabi (Mutter)` / `swww` | `Hanabi (Mutter)` / `mpvpaper` |
| **Fedora KDE Plasma** | **Wayland** | `Plasma DBus` (Natif) | `mpvpaper` / `swww` | `mpvpaper` |
| **Fedora KDE Plasma** | **X11** | `Plasma DBus` (Natif) | `xwinwrap + mpv` | `xwinwrap + mpv` |
| **Sway / Hyprland** | **Wayland** | `swww` / `swaybg` | `swww` / `mpvpaper` | `mpvpaper` |
| **Sessions X11 légères** | **X11** | `feh` / `nitrogen` | `xwinwrap + mpv` | `xwinwrap + mpv` |

---

## 🎬 Fonctionnement des Fonds Vidéos sous Linux Wayland

Sur Fedora Wayland, les protocoles de sécurité interdisent l'injection arbitraire de fenêtres sur le bureau sans passer par les protocoles officiels des compositeurs. WallpaperMaison s'adapte automatiquement à votre gestionnaire :

1. **Le moteur GNOME Shell Hanabi (Natif Mutter / GStreamer) :**
   - Intégration directe dans le compositeur Mutter via une extension GNOME Shell dédiée (`gnome-extension/`).
   - Restitution ultra-fluide avec élimination totale des black frames via `seek(0)` continue.
   - Synchronisation bidirectionnelle instantanée avec VS Code et GSettings sans boucle de rétroaction.
   - Support complet des codecs H.264 grâce à la bibliothèque Cisco OpenH264 injectée de manière portable (`~/.local/lib/libopenh264.so.8`).
2. **Le moteur `mpvpaper` (Layer-Shell) :**
   - Utilise le protocole `wlr-layer-shell` sous Wayland pour projeter la vidéo directement sur le plan d'arrière-plan du compositeur.
   - S'appuie sur `mpv` et le moteur d'accélération matérielle de votre carte graphique (`--hwdec=auto`, compatible Intel QuickSync, AMD VA-API et NVIDIA NVDEC).
   - Consommation processeur quasi-nulle (< 1% CPU sur machine moderne).
3. **Mise en pause intelligente :**
   - Le composant `window_monitor` surveille l'activité de vos fenêtres. Dès qu'un jeu (Steam, Proton, Lutris, etc.) ou une application plein écran est détecté, un signal `SIGSTOP` est envoyé au lecteur vidéo pour libérer immédiatement les ressources GPU.
   - Dès la fermeture du jeu ou le retour sur le bureau, un signal `SIGCONT` reprend la lecture instantanément à la même image.

---

## 🛠️ Dépannage & Diagnostics

### Accéder à la page de diagnostic intégrée
Dans l'application, rendez-vous dans **Paramètres & Diag** ➜ onglet **Diagnostics Fedora**. L'application teste en direct chaque outil et vous fournit la commande DNF exacte avec un bouton de copie en un clic.

### Installer les codecs multimédias complets (RPM Fusion)
Pour lire tous les formats vidéos sous Fedora (notamment H.264 / H.265 / HEVC) :
```bash
sudo dnf install -y https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
sudo dnf install -y ffmpeg mpv mpvpaper
```

### Les vidéos ne s'affichent pas sous GNOME Wayland
Si vous utilisez la session GNOME Wayland par défaut de Fedora sans compositeur layer-shell :
- Installez `mpvpaper` via : `sudo dnf install mpvpaper`
- Sous GNOME Shell, assurez-vous que l'extension de support de fond d'écran animé ou layer-shell est active, ou sélectionnez le mode fenêtré dans les paramètres de WallpaperMaison.

### Réinitialiser la configuration ou le cache
- Configuration : `~/.config/wallpapermaison/config.json`
- Base de données : `~/.local/share/wallpapermaison/wallpapermaison.db`
- Cache : `~/.cache/wallpapermaison/` (peut être vidé directement depuis l'interface)

---

## 🎨 Extension VS Code : Live Wallpaper & Colorimétrie Dynamique

Le projet intègre une version améliorée, robuste et hautement paramétrable de l'extension VS Code `budicuy.live-wallpaper-1.0.9`.

### ✨ Fonctionnalités de l'extension
1. **Synchronisation automatique avec WallpaperMaison** :
   - Détecte en temps réel le fond d'écran actif (GSettings sous GNOME ou base SQLite `wallpapermaison.db`).
   - S'adapte instantanément lors des changements de playlist ou de fond d'écran sans redémarrage de l'éditeur.
2. **Pipeline d'extraction colorimétrique haute performance** :
   - Échantillonnage de trames vidéo/images via un flux `rawvideo` `ffmpeg` en mémoire sans écriture de fichiers temporaires.
   - Quantification 5-bits et clustering perceptuel dans l'espace **CIE-Lab** avec calcul de distance $\Delta E$ (CIE76).
3. **Garantie stricte de lisibilité (WCAG 2.1)** :
   - Calcul de la luminance relative normalisée ($L = 0.2126 R + 0.7152 G + 0.0722 B$).
   - Ajustement automatique de la clarté pour garantir un contraste **$\ge 7:1$ (Norme WCAG AAA)** pour l'éditeur de texte et **$\ge 4.5:1$ (Norme AA)** pour l'interface secondaire.
4. **Lissage temporel et anti-scintillement** :
   - Interpolation linéaire (LERP) sur les composantes de couleur pour des transitions visuelles fluides.
   - Filtre d'hystérésis perceptuel ($\Delta E < \text{threshold}$) éliminant tout scintillement ou à-coup lors des variations mineures de la vidéo.
5. **Intégration non-invasive sans droits root** :
   - Mise à jour instantanée des tokens et éléments d'interface via l'API officielle VS Code (`workbench.colorCustomizations` et `editor.tokenColorCustomizations`).
   - Lecteur vidéo Webview intégré (`WebviewPlayer`) accessible même lorsque le système de fichiers est en lecture seule (`EROFS`).

### ⌨️ Commandes VS Code
* `Live Wallpaper: Open Wallpaper Player View` : Ouvre la vue Webview intégrée pour prévisualiser la vidéo et synchroniser les couleurs.
* `Live Wallpaper: Extract & Apply Dynamic Colors Now` : Force une ré-extraction et synchronisation immédiate de la palette.
* `Live Wallpaper: Toggle Dynamic Colors` : Active ou désactive la colorimétrie dynamique à la volée.
* `Live Wallpaper: Clear Dynamic Theme Colors` : Réinitialise et nettoie toutes les surcharges de couleurs appliquées au thème.

### ⚙️ Paramètres configurables (`settings.json`)
```json
{
  "liveWallpaper.syncWithWallpaperMaison": true,
  "liveWallpaper.colors": {
    "enabled": true,
    "mode": "auto",
    "updateInterval": 2.5,
    "smoothing": 0.25,
    "changeThreshold": 4.0,
    "saturation": 1.0,
    "contrast": 7.0,
    "analysisResolution": "160x90",
    "debug": false
  }
}
```
* `mode` : Choix du profil colorimétrique (`auto`, `dominant`, `vibrant`, `ambient`, `muted`).
* `updateInterval` : Intervalle en secondes (ou millisecondes) entre chaque analyse de frame vidéo (défaut : `2.5` s).
* `smoothing` : Facteur de lissage temporel LERP ($\alpha \in [0.05, 1.0]$). Une valeur basse produit des transitions très douces.
* `changeThreshold` : Seuil minimal $\Delta E$ avant d'appliquer une nouvelle couleur (défaut : `4.0`, seuil d'imperceptibilité).
* `contrast` : Ratio de contraste minimal garanti (défaut : `7.0` pour WCAG AAA).
* `analysisResolution` : Résolution de la vignette d'analyse (`160x90`, `80x45`, `320x180`).

---

### 🔄 Rotation Automatique Multi-Postes (Interface VS Code & `.env`)

WallpaperMaison intègre un moteur de rotation automatique complet, accessible à la fois directement depuis le tableau de bord de la vue latérale VS Code (`Live Wallpaper` dans la barre d'activités) et configurable via votre fichier `.env`.

#### 🎨 Fonctionnalités de l'Interface VS Code
* **Switch d'activation animé** façon iOS avec voyant de statut en direct.
* **Compte à rebours dynamique** (`MM:SS`) indiquant exactement le temps restant avant le prochain changement.
* **Bouton d'action rapide `⏭️ Suivant`** pour changer immédiatement de fond d'écran sans attendre l'expiration du minuteur.
* **Sélecteur de dossier intuitif** avec boutons d'accès rapide (Dossier Téléchargements, Images, etc.) et détection en direct du nombre de médias disponibles (compteurs séparés pour vidéos et images).
* **Réglage du délai de rotation** :
  * Sélection par puces rapides : **1m**, **3m**, **5m**, **10m**, **15m**, **30m**, **60m**.
  * Molette numérique pour un intervalle personnalisé en minutes.
* **Mode d'ordonnancement** :
  * `🎲 Aléatoire` : Pioche aléatoire sans répétition immédiate.
  * `🔁 Dans l'ordre` : Rotation séquentielle alphabétique à travers le dossier.

#### 💾 Persistance Cross-Postes (Réseau Perso NFS)
Les réglages sont sauvegardés simultanément dans :
1. `~/.config/wallpapermaison/rotation_settings.json`
2. `~/reseau/Perso/.config/wallpapermaison/rotation_settings.json` *(accessible depuis n'importe quel poste)*
3. Le fichier `.env` à la racine du projet (`ROTATION_ENABLED`, `ROTATION_INTERVAL_MINUTES`, `ROTATION_FOLDER`, `ROTATION_ORDER`).

#### ⚡ Configuration alternative via `.env`
```env
ROTATION_ENABLED=true
ROTATION_INTERVAL_MINUTES=5
ROTATION_FOLDER=/var/home/E256190S/reseau/Perso/Téléchargements
ROTATION_ORDER=random
```

---

## ⚠️ Limites Connues & Solutions de Contournement

### 1. Système de fichiers en lecture seule (`EROFS: read-only file system`)
* **Problème rencontré** : Sur les systèmes immuables comme **Fedora Silverblue** ou les environnements d'entreprise/université où VS Code est déployé dans `/usr/apps/` ou via des overlays `sysext`, `/usr` est monté en lecture seule stricte (`ro`). L'extension originale tentait d'écrire dans `/usr/apps/VSCode-linux-x64/.../workbench.html`, ce qui déclenchait une erreur `EROFS: read-only file system` et une boucle de demandes de mot de passe `sudo`.
* **Solution apportée** :
  1. Détection gracieuse de la lecture seule : l'extension vérifie `fs.accessSync(..., W_OK)`. Si le fichier n'est pas modifiable, aucun message d'erreur intempestif n'est affiché et aucune tentative d'escalade `sudo` n'est lancée.
  2. Theming officiel et propre : la colorimétrie dynamique utilise exclusivement l'API native `workbench.colorCustomizations`, 100% compatible avec les installations immuables.
  3. Pour la visualisation du fond d'écran, l'extension fournit le panneau Webview dédié (`Live Wallpaper: Open Wallpaper Player View`), totalement fonctionnel en espace utilisateur.

### 2. Absence des codecs H.264 propriétaires dans le FFmpeg de base de Fedora
* **Problème rencontré** : L'image Fedora standard intègre un stub `noopenh264`, provoquant un code d'erreur 171 lors de la tentative de décodage de vidéos MP4 H.264 via `ffmpeg` système.
* **Solution apportée** :
  - Sans nécessiter de droits administrateur `root` ni `sudo dnf`, le script `setup.sh` déploie l'environnement Flatpak `io.mpv.Mpv` (issu de Flathub, contenant tous les codecs) et installe les wrappers `~/.local/bin/mpv` et `~/.local/bin/ffmpeg-full`.
  - Le module `FrameExtractor` de l'extension comme `media_tools.py` de WallpaperMaison détectent et utilisent automatiquement ce pipeline à codecs complets.

### 3. Session Wayland et droits d'accès
* **Problème rencontré** : Les sockets IPC Unix et fichiers de verrouillage placés dans `/tmp/` peuvent entrer en conflit d'UID sur des machines multi-utilisateurs.
* **Solution apportée** : Tous les verrous applicatifs et sockets de communication du démon vidéo (`video_bg_worker.py`) utilisent désormais `$XDG_RUNTIME_DIR` (ex: `/run/user/26590/`), garantissant une isolation stricte et sécurisée par utilisateur.

### 4. Conformité syntaxique ECMAScript sous GNOME GJS
* **Problème rencontré** : Sous GNOME Shell 45 à 50+, GJS utilise le moteur SpiderMonkey strict. L'usage de déclarations de fonction classiques (`function foo()`) à l'intérieur du corps de classes ES6 dans les extensions GNOME provoque un rejet immédiat (`SyntaxError: unexpected token: identifier`) bloquant le sous-processus renderer.
* **Solution apportée** : Portée modulaire standardisée pour les fonctions utilitaires exportées et méthodes de classe pures sans mots-clés parasites, assurant un chargement 100% robuste sur tout nouveau poste.

---

## 🧪 Exécution des Tests Automatisés

Le projet inclut une suite de tests unitaires couvrant l'ensemble des modules (y compris l'autostart, la colorimétrie WCAG, la persistance et le stockage) :
```bash
python -m unittest discover -s tests
```
*Résultat attendu : `Ran 35 tests ... OK`*

---

## 📜 Licence
Projet open-source développé sous licence MIT.

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

### 💾 Mode Persistant Réseau (Spécial IUT / NFS)
Si vous travaillez sur une machine où la session locale est réinitialisée à chaque redémarrage (ex: postes IUT Nantes avec stockage réseau `~/reseau/Perso`) :
* L'installateur détecte automatiquement le partage réseau et vous propose l'**installation persistante**.
* Vos fonds d'écran, base de données SQLite, miniatures en cache, playlists et configurations sont conservés de manière permanente dans `~/reseau/Perso/`.
* Vos données sont instantanément retrouvées sur **n'importe quel ordinateur** de l'IUT sans réinstallation !

Vous pouvez également forcer le mode en ligne de commande :
```bash
# Installation persistante réseau automatique
./scripts/install.sh --persistent -y

# Ou installation locale classique
./scripts/install.sh --local -y
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
│   │   └── adjuster.py             # Pipeline non destructif (Pillow) : filtres, géométrie, cache
│   ├── wallpaper/
│   │   ├── base.py                 # Classe abstraite BaseWallpaperEngine
│   │   ├── manager.py              # Orchestrateur central et sélecteur de moteur
│   │   └── engines/
│   │       ├── gnome_engine.py     # Moteur GSettings pour GNOME
│   │       ├── kde_engine.py       # Moteur DBus Plasmashell pour KDE
│   │       ├── mpvpaper_engine.py  # Moteur vidéo fluide Wayland via mpvpaper
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
├── scripts/
│   ├── install.sh                  # Script d'installation Fedora DNF + venv
│   └── run.sh                      # Script de lancement exécutable
├── tests/                          # Suite complète de tests unitaires (100% passing)
│   ├── test_storage.py             # Tests SQLite et migrations
│   ├── test_adjuster.py            # Tests traitement d'image non destructif
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
| **Fedora GNOME** (Défaut) | **Wayland** | `GSettings` (Natif) | `mpvpaper` / `swww` | `mpvpaper` |
| **Fedora KDE Plasma** | **Wayland** | `Plasma DBus` (Natif) | `mpvpaper` / `swww` | `mpvpaper` |
| **Fedora KDE Plasma** | **X11** | `Plasma DBus` (Natif) | `xwinwrap + mpv` | `xwinwrap + mpv` |
| **Sway / Hyprland** | **Wayland** | `swww` / `swaybg` | `swww` / `mpvpaper` | `mpvpaper` |
| **Sessions X11 légères** | **X11** | `feh` / `nitrogen` | `xwinwrap + mpv` | `xwinwrap + mpv` |

---

## 🎬 Fonctionnement des Fonds Vidéos sous Linux Wayland

Sur Fedora Wayland, les protocoles de sécurité interdisent l'injection arbitraire de fenêtres sur le bureau sans passer par les protocoles officiels des compositeurs.

1. **Le moteur `mpvpaper` :**
   - Utilise le protocole `wlr-layer-shell` sous Wayland pour projeter la vidéo directement sur le plan d'arrière-plan du compositeur.
   - S'appuie sur `mpv` et le moteur d'accélération matérielle de votre carte graphique (`--hwdec=auto`, compatible Intel QuickSync, AMD VA-API et NVIDIA NVDEC).
   - Consommation processeur quasi-nulle (< 1% CPU sur machine moderne).
2. **Mise en pause intelligente :**
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

## 🧪 Exécution des Tests Automatisés

Le projet inclut une suite de tests unitaires couvrant l'ensemble des modules :
```bash
python -m unittest discover -s tests
```
*Résultat attendu : `Ran 20 tests ... OK`*

---

## 📜 Licence
Projet open-source développé sous licence MIT.

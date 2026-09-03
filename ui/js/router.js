/**
 * Routeur SPA pour navigation fluide sans rechargement.
 */
class Router {
  constructor() {
    this.routes = {};
    this.currentView = 'dashboard';
    this.titleMap = {
      dashboard: "Vue d'ensemble",
      library: "Bibliothèque de Fonds d'Écran",
      preview: "Aperçu & Cadrage",
      editor: "Éditeur d'Image Non Destructif",
      playlists: "Playlists & Rotations",
      automations: "Règles & Automatisations",
      monitors: "Configuration Multi-Écrans",
      settings: "Paramètres & Diagnostics"
    };

    document.querySelectorAll('.nav-item').forEach((item) => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const target = item.getAttribute('data-view');
        if (target) this.navigate(target);
      });
    });
  }

  register(viewName, pageHandler) {
    this.routes[viewName] = pageHandler;
  }

  navigate(viewName, params = {}) {
    const panels = document.querySelectorAll('.view-panel');
    panels.forEach((p) => p.classList.remove('active'));

    const targetPanel = document.getElementById(`view-${viewName}`);
    if (targetPanel) {
      targetPanel.classList.add('active');
    }

    // Mise à jour de l'élément actif dans la sidebar
    document.querySelectorAll('.nav-item').forEach((item) => {
      if (item.getAttribute('data-view') === viewName) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });

    // Mise à jour du titre
    const titleEl = document.getElementById('topbar-page-title');
    if (titleEl && this.titleMap[viewName]) {
      titleEl.textContent = this.titleMap[viewName];
    }

    this.currentView = viewName;

    // Appel du cycle de vie onEnter
    if (this.routes[viewName] && typeof this.routes[viewName].onEnter === 'function') {
      this.routes[viewName].onEnter(params);
    }
  }
}

window.router = new Router();

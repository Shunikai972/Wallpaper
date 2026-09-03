/**
 * Contrôleur de la bibliothèque de fonds d'écran.
 */
class LibraryPage {
  constructor() {
    this.container = null;
  }

  init() {
    window.router.register('library', this);
    this.container = document.getElementById('library-wallpapers-container');

    // Écouteurs de filtres de type
    document.querySelectorAll('.filter-tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.filter-tab').forEach((t) => t.classList.remove('active'));
        tab.classList.add('active');
        const mediaType = tab.getAttribute('data-type');
        window.store.updateLibraryFilter({ mediaType });
        window.store.refreshWallpapers();
      });
    });

    // Écouteur de recherche instantanée avec debouncing
    const searchInput = document.getElementById('library-search-input');
    let debounceTimer = null;
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          window.store.updateLibraryFilter({ search: e.target.value });
          window.store.refreshWallpapers();
        }, 250);
      });
    }

    // Sélecteur de tri
    const sortSelect = document.getElementById('library-sort-select');
    if (sortSelect) {
      sortSelect.addEventListener('change', (e) => {
        window.store.updateLibraryFilter({ sortBy: e.target.value });
        window.store.refreshWallpapers();
      });
    }

    // Sélecteur de mode d'affichage (grid, compact, liste)
    document.querySelectorAll('.view-mode-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.view-mode-btn').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        const mode = btn.getAttribute('data-mode');
        this.setViewMode(mode);
      });
    });

    // Boutons d'import
    document.getElementById('library-import-files-btn')?.addEventListener('click', async () => {
      const res = await window.api.call('open_file_dialog');
      if (res && res.success && res.imported_count > 0) {
        window.toast.success(`${res.imported_count} fond(s) d'écran importé(s).`);
        window.store.refreshAll();
      }
    });

    document.getElementById('library-import-folder-btn')?.addEventListener('click', async () => {
      const res = await window.api.call('open_directory_dialog');
      if (res && res.success && res.folder) {
        window.toast.info(`Scan du dossier : ${res.folder}`);
        await window.api.call('start_scan', [res.folder], true);
      }
    });

    // Configuration du glisser-déposer sur toute la fenêtre
    this.setupDragAndDrop();

    // Abonnements au store
    window.store.subscribe('wallpapers', (items) => this.render(items));
    window.store.subscribe('tags', (tags) => this.renderTags(tags));
  }

  async onEnter() {
    await window.store.refreshWallpapers();
    await window.store.refreshStats();
  }

  setViewMode(mode) {
    if (!this.container) return;
    this.container.className = mode === 'compact'
      ? 'wallpaper-grid compact'
      : (mode === 'list' ? 'wallpaper-list' : 'wallpaper-grid');
    window.store.updateLibraryFilter({ viewMode: mode });
  }

  render(items) {
    if (!this.container) return;

    if (!items || items.length === 0) {
      this.container.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: var(--text-muted);">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom:12px; opacity:0.5;">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <circle cx="8.5" cy="8.5" r="1.5"></circle>
            <polyline points="21 15 16 10 5 21"></polyline>
          </svg>
          <div style="font-size: 16px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px;">Aucun fond d'écran trouvé</div>
          <div style="font-size: 13px;">Glissez-déposez des fichiers ici ou importez un dossier pour enrichir votre collection.</div>
        </div>
      `;
      return;
    }

    const cur = window.store.get('currentWallpaper');
    const viewMode = window.store.get('libraryFilter').viewMode;

    if (viewMode === 'list') {
      this.renderListView(items, cur);
    } else {
      this.renderGridView(items, cur);
    }
  }

  renderGridView(items, current) {
    this.container.innerHTML = '';
    const fragment = document.createDocumentFragment();

    items.forEach((wp) => {
      const card = document.createElement('div');
      card.className = `wallpaper-card ${current && current.id === wp.id ? 'active' : ''}`;

      const imgUrl = wp.thumbnail_path
        ? (wp.thumbnail_path.startsWith('http') ? wp.thumbnail_path : `file://${wp.thumbnail_path}`)
        : `file://${wp.file_path}`;

      const badgeClass = `badge-${wp.media_type}`;
      const sizeMb = (wp.file_size / (1024 * 1024)).toFixed(1);

      card.innerHTML = `
        <div class="card-media-wrapper">
          <img class="card-media-img" src="${imgUrl}" alt="${wp.file_name}" loading="lazy" onerror="this.src='https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=500&q=80'">
          <div class="card-overlay">
            <div class="card-top-badges">
              <span class="badge ${badgeClass}">${wp.media_type}</span>
              <button class="card-favorite-btn ${wp.is_favorite ? 'active' : ''}" title="Favori">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="${wp.is_favorite ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                </svg>
              </button>
            </div>
            <div class="card-quick-actions">
              <button class="btn btn-primary btn-apply" title="Appliquer">Appliquer</button>
              <button class="btn btn-secondary btn-preview" title="Aperçu">Aperçu</button>
            </div>
          </div>
        </div>
        <div class="card-info">
          <div class="card-title" title="${wp.file_name}">${wp.file_name}</div>
          <div class="card-meta">
            <span>${wp.width ? `${wp.width}x${wp.height}` : 'HD'}</span>
            <span>${sizeMb} MB</span>
          </div>
        </div>
      `;

      // Clic sur Appliquer
      card.querySelector('.btn-apply')?.addEventListener('click', async (e) => {
        e.stopPropagation();
        const res = await window.api.call('apply_wallpaper', wp.id);
        if (res && res.success) {
          window.toast.success(`Fond appliqué : ${wp.file_name}`);
          window.store.refreshCurrent();
          this.render(items);
        } else {
          window.toast.error("Échec de l'application.");
        }
      });

      // Clic sur Aperçu
      card.querySelector('.btn-preview')?.addEventListener('click', (e) => {
        e.stopPropagation();
        window.store.set('selectedWallpaper', wp);
        window.router.navigate('preview');
      });

      // Clic sur Favori
      card.querySelector('.card-favorite-btn')?.addEventListener('click', async (e) => {
        e.stopPropagation();
        const res = await window.api.call('toggle_favorite', wp.id);
        if (res && res.success) {
          wp.is_favorite = res.is_favorite ? 1 : 0;
          this.render(items);
        }
      });

      // Clic droit : Menu contextuel
      card.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        window.contextMenu.show(e.clientX, e.clientY, wp);
      });

      fragment.appendChild(card);
    });

    this.container.appendChild(fragment);
  }

  renderListView(items, current) {
    this.container.innerHTML = '';
    const fragment = document.createDocumentFragment();

    items.forEach((wp) => {
      const row = document.createElement('div');
      row.className = `wallpaper-card ${current && current.id === wp.id ? 'active' : ''}`;
      row.style.flexDirection = 'row';
      row.style.alignItems = 'center';
      row.style.padding = '10px 16px';
      row.style.gap = '16px';

      const imgUrl = wp.thumbnail_path
        ? (wp.thumbnail_path.startsWith('http') ? wp.thumbnail_path : `file://${wp.thumbnail_path}`)
        : `file://${wp.file_path}`;

      row.innerHTML = `
        <img src="${imgUrl}" style="width:72px; height:42px; object-fit:cover; border-radius:var(--radius-sm); flex-shrink:0;">
        <div style="flex:1; min-width:0;">
          <div style="font-weight:600; font-size:13.5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${wp.file_name}</div>
          <div style="font-size:11.5px; color:var(--text-muted); font-family:var(--font-mono);">${wp.media_type.toUpperCase()} • ${wp.width}x${wp.height} • ${(wp.file_size / (1024*1024)).toFixed(1)} MB</div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <button class="btn btn-secondary btn-preview">Aperçu</button>
          <button class="btn btn-primary btn-apply">Appliquer</button>
        </div>
      `;

      row.querySelector('.btn-apply')?.addEventListener('click', async () => {
        await window.api.call('apply_wallpaper', wp.id);
        window.store.refreshCurrent();
      });

      row.querySelector('.btn-preview')?.addEventListener('click', () => {
        window.store.set('selectedWallpaper', wp);
        window.router.navigate('preview');
      });

      row.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        window.contextMenu.show(e.clientX, e.clientY, wp);
      });

      fragment.appendChild(row);
    });

    this.container.appendChild(fragment);
  }

  renderTags(tags) {
    const row = document.getElementById('library-tags-row');
    if (!row) return;
    row.innerHTML = `<div class="tag-pill active" data-tag="">Tous les tags</div>`;
    tags.forEach((t) => {
      const pill = document.createElement('div');
      pill.className = 'tag-pill';
      pill.setAttribute('data-tag', t);
      pill.textContent = `#${t}`;
      pill.addEventListener('click', () => {
        document.querySelectorAll('.tag-pill').forEach((p) => p.classList.remove('active'));
        pill.classList.add('active');
        window.store.updateLibraryFilter({ tag: t });
        window.store.refreshWallpapers();
      });
      row.appendChild(pill);
    });
  }

  setupDragAndDrop() {
    const overlay = document.getElementById('global-dropzone');
    if (!overlay) return;

    window.addEventListener('dragover', (e) => {
      e.preventDefault();
      overlay.classList.add('active');
    });

    overlay.addEventListener('dragleave', () => {
      overlay.classList.remove('active');
    });

    overlay.addEventListener('drop', async (e) => {
      e.preventDefault();
      overlay.classList.remove('active');
      if (e.dataTransfer && e.dataTransfer.files) {
        let count = 0;
        for (const file of e.dataTransfer.files) {
          if (file.path) {
            const res = await window.api.call('import_single_file', file.path);
            if (res && res.success) count++;
          }
        }
        if (count > 0) {
          window.toast.success(`${count} média(s) importé(s) via glisser-déposer.`);
          window.store.refreshAll();
        }
      }
    });
  }
}

window.libraryPage = new LibraryPage();

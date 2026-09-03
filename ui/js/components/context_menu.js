/**
 * Menu contextuel moderne au clic droit pour les fonds d'écran.
 */
class ContextMenuManager {
  constructor() {
    this.el = document.getElementById('context-menu');
    this._activeWallpaper = null;

    document.addEventListener('click', () => this.hide());
    window.addEventListener('resize', () => this.hide());
  }

  show(x, y, wallpaper) {
    if (!this.el) return;
    this._activeWallpaper = wallpaper;

    this.el.innerHTML = `
      <div class="context-menu-item" data-action="apply">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
        <span>Appliquer comme fond</span>
      </div>
      <div class="context-menu-item" data-action="preview">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polygon points="10 8 16 12 10 16 10 8"></polygon></svg>
        <span>Aperçu & Cadrage</span>
      </div>
      <div class="context-menu-item" data-action="edit">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
        <span>Retoucher l'image</span>
      </div>
      <div class="context-menu-item" data-action="favorite">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="${wallpaper.is_favorite ? 'var(--accent-secondary)' : 'none'}" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
        <span>${wallpaper.is_favorite ? 'Retirer des favoris' : 'Marquer comme favori'}</span>
      </div>
      <div class="context-menu-separator"></div>
      <div class="context-menu-item" data-action="tags">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path><line x1="7" y1="7" x2="7.01" y2="7"></line></svg>
        <span>Gérer les tags...</span>
      </div>
      <div class="context-menu-item" data-action="details">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
        <span>Détails techniques</span>
      </div>
      <div class="context-menu-separator"></div>
      <div class="context-menu-item" data-action="delete" style="color: var(--accent-danger);">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-danger)" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
        <span>Retirer de la bibliothèque</span>
      </div>
    `;

    // Écouteurs d'actions
    this.el.querySelectorAll('.context-menu-item').forEach((item) => {
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        const action = item.getAttribute('data-action');
        this._handleAction(action);
        this.hide();
      });
    });

    // Ajustement de position pour ne pas déborder de l'écran
    const menuWidth = 200;
    const menuHeight = 260;
    const posX = x + menuWidth > window.innerWidth ? window.innerWidth - menuWidth - 10 : x;
    const posY = y + menuHeight > window.innerHeight ? window.innerHeight - menuHeight - 10 : y;

    this.el.style.left = `${posX}px`;
    this.el.style.top = `${posY}px`;
    this.el.style.display = 'block';
  }

  hide() {
    if (this.el) {
      this.el.style.display = 'none';
      this._activeWallpaper = null;
    }
  }

  async _handleAction(action) {
    const wp = this._activeWallpaper;
    if (!wp) return;

    if (action === 'apply') {
      const res = await window.api.call('apply_wallpaper', wp.id);
      if (res && res.success) {
        window.toast.success(`Fond d'écran appliqué : ${wp.file_name}`);
        window.store.refreshCurrent();
      } else {
        window.toast.error("Impossible d'appliquer le fond d'écran.");
      }
    } else if (action === 'preview') {
      window.store.set('selectedWallpaper', wp);
      window.router.navigate('preview');
    } else if (action === 'edit') {
      window.store.set('selectedWallpaper', wp);
      window.router.navigate('editor');
    } else if (action === 'favorite') {
      const res = await window.api.call('toggle_favorite', wp.id);
      if (res && res.success) {
        wp.is_favorite = res.is_favorite ? 1 : 0;
        window.store.refreshWallpapers();
        window.toast.info(res.is_favorite ? 'Ajouté aux favoris' : 'Retiré des favoris');
      }
    } else if (action === 'tags') {
      window.modal.open({
        title: `Modifier les tags : ${wp.file_name}`,
        contentHtml: `
          <div style="display:flex; flex-direction:column; gap:12px;">
            <p style="font-size:12px; color:var(--text-secondary);">Séparez les tags par des virgules (ex: anime, 4k, sombre, nature) :</p>
            <input type="text" id="tag-input-field" class="search-input" value="${wp.tags || ''}" style="width:100%;">
          </div>
        `,
        buttons: [
          { text: 'Annuler', className: 'btn-ghost' },
          {
            text: 'Enregistrer',
            className: 'btn-primary',
            onClick: async () => {
              const input = document.getElementById('tag-input-field');
              if (input) {
                await window.api.call('update_tags', wp.id, input.value.trim());
                window.store.refreshWallpapers();
                window.toast.success('Tags mis à jour.');
              }
            }
          }
        ]
      });
    } else if (action === 'details') {
      window.modal.open({
        title: wp.file_name,
        contentHtml: `
          <div style="display:flex; flex-direction:column; gap:10px; font-size:13px; font-family:var(--font-mono);">
            <div><strong>Format :</strong> ${wp.media_type.toUpperCase()}</div>
            <div><strong>Résolution :</strong> ${wp.width} x ${wp.height} px</div>
            <div><strong>Taille :</strong> ${(wp.file_size / (1024 * 1024)).toFixed(2)} MB</div>
            ${wp.duration ? `<div><strong>Durée :</strong> ${wp.duration} s</div>` : ''}
            ${wp.fps ? `<div><strong>Cadence :</strong> ${wp.fps} FPS</div>` : ''}
            <div><strong>Chemin :</strong> <span style="font-size:11px; word-break:break-all; color:var(--text-secondary);">${wp.file_path}</span></div>
          </div>
        `,
        buttons: [{ text: 'Fermer', className: 'btn-secondary' }]
      });
    } else if (action === 'delete') {
      const res = await window.api.call('delete_wallpaper', wp.id);
      if (res && res.success) {
        window.toast.info('Fond d\'écran retiré de la bibliothèque.');
        window.store.refreshAll();
      }
    }
  }
}

window.contextMenu = new ContextMenuManager();

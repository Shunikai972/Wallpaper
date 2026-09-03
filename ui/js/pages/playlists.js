/**
 * Contrôleur des Playlists et gestion de la rotation par playlist.
 */
class PlaylistsPage {
  constructor() {
    this.playlists = [];
    this.selectedPlaylist = null;
  }

  init() {
    window.router.register('playlists', this);

    // Bouton Créer une Playlist
    document.getElementById('create-playlist-btn')?.addEventListener('click', () => {
      window.modal.open({
        title: 'Nouvelle Playlist',
        contentHtml: `
          <div style="display:flex; flex-direction:column; gap:16px;">
            <div>
              <label style="font-size:12px; color:var(--text-secondary); display:block; margin-bottom:6px;">Nom de la playlist :</label>
              <input type="text" id="new-pl-name" class="search-input" placeholder="ex: Ambiance Soirée, Cyberpunk..." style="width:100%;">
            </div>
            <div>
              <label style="font-size:12px; color:var(--text-secondary); display:block; margin-bottom:6px;">Description :</label>
              <input type="text" id="new-pl-desc" class="search-input" placeholder="Courte description" style="width:100%;">
            </div>
            <div>
              <label style="font-size:12px; color:var(--text-secondary); display:block; margin-bottom:6px;">Intervalle de rotation (secondes) :</label>
              <select id="new-pl-interval" class="search-input" style="width:100%;">
                <option value="30">30 secondes</option>
                <option value="60">1 minute</option>
                <option value="300" selected>5 minutes</option>
                <option value="600">10 minutes</option>
                <option value="1800">30 minutes</option>
                <option value="3600">1 heure</option>
              </select>
            </div>
          </div>
        `,
        buttons: [
          { text: 'Annuler', className: 'btn-ghost' },
          {
            text: 'Créer la playlist',
            className: 'btn-primary',
            onClick: async () => {
              const nameInput = document.getElementById('new-pl-name');
              const descInput = document.getElementById('new-pl-desc');
              const intInput = document.getElementById('new-pl-interval');
              if (nameInput && nameInput.value.trim()) {
                const res = await window.api.call(
                  'create_playlist',
                  nameInput.value.trim(),
                  descInput ? descInput.value.trim() : '',
                  'folder',
                  intInput ? parseInt(intInput.value) : 300
                );
                if (res && res.success) {
                  window.toast.success(`Playlist "${nameInput.value}" créée.`);
                  await this.loadPlaylists();
                }
              }
            }
          }
        ]
      });
    });
  }

  async onEnter() {
    await this.loadPlaylists();
  }

  async loadPlaylists() {
    const res = await window.api.call('get_playlists');
    if (res && res.success) {
      this.playlists = res.data || [];
      this.render();
    }
  }

  render() {
    const container = document.getElementById('playlists-grid-container');
    if (!container) return;

    container.innerHTML = '';
    const fragment = document.createDocumentFragment();

    this.playlists.forEach((pl) => {
      const card = document.createElement('div');
      card.className = 'widget-card';
      card.style.cursor = 'pointer';

      const intervalMin = Math.round(pl.interval_seconds / 60);

      card.innerHTML = `
        <div class="widget-header">
          <div style="display:flex; align-items:center; gap:12px;">
            <div style="width:40px; height:40px; border-radius:var(--radius-md); background:rgba(163,190,140,0.15); display:flex; align-items:center; justify-content:center; color:var(--accent-primary);">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
            </div>
            <div>
              <div class="widget-title">${pl.name}</div>
              <div style="font-size:12px; color:var(--text-muted);">${pl.item_count || 0} fond(s) d'écran</div>
            </div>
          </div>
          <button class="btn btn-icon btn-delete-pl" title="Supprimer">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
          </button>
        </div>
        <p style="font-size:12.5px; color:var(--text-secondary); line-height:1.4;">${pl.description || 'Aucune description'}</p>
        <div style="display:flex; align-items:center; justify-content:space-between; margin-top:auto; pt:12px; border-top:1px solid var(--border-subtle); padding-top:12px;">
          <span style="font-size:11.5px; color:var(--text-muted); font-family:var(--font-mono);">Intervalle: ${intervalMin}m</span>
          <button class="btn btn-primary btn-play-pl" style="padding:6px 14px; font-size:12px;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
            <span>Lancer</span>
          </button>
        </div>
      `;

      // Clic sur Lancer
      card.querySelector('.btn-play-pl')?.addEventListener('click', async (e) => {
        e.stopPropagation();
        await window.api.call('update_config', 'auto_change.target_playlist_id', pl.id);
        await window.api.call('toggle_scheduler', true);
        await window.api.call('next_wallpaper');
        window.toast.success(`Playlist "${pl.name}" activée.`);
        window.store.refreshCurrent();
      });

      // Clic sur Supprimer
      card.querySelector('.btn-delete-pl')?.addEventListener('click', async (e) => {
        e.stopPropagation();
        await window.api.call('delete_playlist', pl.id);
        window.toast.info(`Playlist "${pl.name}" supprimée.`);
        await this.loadPlaylists();
      });

      fragment.appendChild(card);
    });

    container.appendChild(fragment);
  }
}

window.playlistsPage = new PlaylistsPage();

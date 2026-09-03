/**
 * Gestionnaire d'état réactif centralisé pour l'interface.
 */
class StateStore {
  constructor() {
    this.state = {
      wallpapers: [],
      currentWallpaper: null,
      selectedWallpaper: null,
      stats: { total: 0, images: 0, gifs: 0, videos: 0, favorites: 0 },
      tags: [],
      playlists: [],
      automations: [],
      monitors: [],
      systemInfo: null,
      config: null,
      cacheStats: null,
      activeProfile: 'Balanced',
      // Filtres bibliothèque
      libraryFilter: {
        mediaType: 'all',
        favoriteOnly: false,
        tag: '',
        search: '',
        sortBy: 'created_desc',
        viewMode: 'grid' // grid, compact, list
      },
      isScanning: false,
      isPlaying: true
    };
    this.listeners = new Map();
  }

  subscribe(key, callback) {
    if (!this.listeners.has(key)) {
      this.listeners.set(key, []);
    }
    this.listeners.get(key).push(callback);
    return () => {
      const arr = this.listeners.get(key) || [];
      const idx = arr.indexOf(callback);
      if (idx !== -1) arr.splice(idx, 1);
    };
  }

  set(key, value) {
    this.state[key] = value;
    if (this.listeners.has(key)) {
      this.listeners.get(key).forEach((cb) => cb(value));
    }
    if (this.listeners.has('*')) {
      this.listeners.get('*').forEach((cb) => cb(key, value));
    }
  }

  get(key, defaultValue = null) {
    return this.state[key] !== undefined ? this.state[key] : defaultValue;
  }

  updateLibraryFilter(partial) {
    const updated = { ...this.state.libraryFilter, ...partial };
    this.set('libraryFilter', updated);
  }

  async refreshWallpapers() {
    const f = this.state.libraryFilter;
    const res = await window.api.call(
      'get_wallpapers',
      f.search,
      f.mediaType,
      f.favoriteOnly,
      f.tag,
      f.sortBy,
      500,
      0
    );
    if (res && res.success) {
      this.set('wallpapers', res.data || []);
    }
  }

  async refreshCurrent() {
    const res = await window.api.call('get_current_wallpaper');
    if (res && res.success) {
      this.set('currentWallpaper', res.data);
    }
  }

  async refreshStats() {
    const res = await window.api.call('get_stats');
    if (res && res.success) {
      this.set('stats', res.data);
    }
    const tagsRes = await window.api.call('get_all_tags');
    if (tagsRes && tagsRes.success) {
      this.set('tags', tagsRes.data || []);
    }
  }

  async refreshAll() {
    await Promise.all([
      this.refreshWallpapers(),
      this.refreshCurrent(),
      this.refreshStats()
    ]);
  }
}

window.store = new StateStore();

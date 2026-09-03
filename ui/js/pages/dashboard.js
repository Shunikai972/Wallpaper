/**
 * Contrôleur de la vue Dashboard (Vue d'ensemble).
 */
class DashboardPage {
  constructor() {
    this.timerInterval = null;
  }

  init() {
    window.router.register('dashboard', this);

    // Écouteurs pour les boutons d'action rapide du hero
    document.getElementById('hero-next-btn')?.addEventListener('click', async () => {
      await window.api.call('next_wallpaper');
      await window.store.refreshCurrent();
    });

    document.getElementById('hero-prev-btn')?.addEventListener('click', async () => {
      await window.api.call('previous_wallpaper');
      await window.store.refreshCurrent();
    });

    document.getElementById('hero-pause-btn')?.addEventListener('click', async () => {
      const isPlaying = window.store.get('isPlaying', true);
      if (isPlaying) {
        await window.api.call('pause_wallpaper');
        window.store.set('isPlaying', false);
        document.getElementById('hero-pause-btn').innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
          <span>Reprendre</span>
        `;
      } else {
        await window.api.call('resume_wallpaper');
        window.store.set('isPlaying', true);
        document.getElementById('hero-pause-btn').innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>
          <span>Pause</span>
        `;
      }
    });

    document.getElementById('hero-fav-btn')?.addEventListener('click', async () => {
      const cur = window.store.get('currentWallpaper');
      if (cur && cur.id) {
        const res = await window.api.call('toggle_favorite', cur.id);
        if (res && res.success) {
          cur.is_favorite = res.is_favorite ? 1 : 0;
          this.updateHero(cur);
          window.toast.info(res.is_favorite ? 'Ajouté aux favoris' : 'Retiré des favoris');
        }
      }
    });

    window.store.subscribe('currentWallpaper', (wp) => this.updateHero(wp));
  }

  async onEnter() {
    await window.store.refreshCurrent();
    await window.store.refreshStats();
    this.updateStats();
    this.startCountdownTimer();
  }

  updateHero(wp) {
    const bgEl = document.getElementById('dashboard-hero-bg');
    const titleEl = document.getElementById('now-playing-name');
    const metaEl = document.getElementById('now-playing-meta-info');
    const favBtn = document.getElementById('hero-fav-btn');

    if (!wp) {
      if (titleEl) titleEl.textContent = 'Aucun fond d\'écran actif';
      if (metaEl) metaEl.textContent = 'Sélectionnez un fond dans la bibliothèque';
      return;
    }

    const imgUrl = wp.thumbnail_path
      ? (wp.thumbnail_path.startsWith('http') ? wp.thumbnail_path : `file://${wp.thumbnail_path}`)
      : (wp.file_path ? `file://${wp.file_path}` : '');

    if (bgEl && imgUrl) {
      bgEl.style.backgroundImage = `url('${imgUrl}')`;
    }

    if (titleEl) titleEl.textContent = wp.file_name;
    if (metaEl) {
      const res = `${wp.width || 1920}x${wp.height || 1080}`;
      const type = (wp.media_type || 'image').toUpperCase();
      const sizeMb = (wp.file_size / (1024 * 1024)).toFixed(1);
      metaEl.textContent = `${type} • ${res} • ${sizeMb} MB ${wp.fps ? `• ${wp.fps} FPS` : ''}`;
    }

    if (favBtn) {
      favBtn.style.color = wp.is_favorite ? 'var(--accent-secondary)' : 'var(--text-secondary)';
    }
  }

  updateStats() {
    const stats = window.store.get('stats', {});
    const countEl = document.getElementById('dashboard-stat-total');
    const favEl = document.getElementById('dashboard-stat-favs');
    const videoEl = document.getElementById('dashboard-stat-videos');

    if (countEl) countEl.textContent = stats.total || 0;
    if (favEl) favEl.textContent = stats.favorites || 0;
    if (videoEl) videoEl.textContent = (stats.videos || 0) + (stats.gifs || 0);
  }

  startCountdownTimer() {
    if (this.timerInterval) clearInterval(this.timerInterval);
    const updateCountdown = async () => {
      const res = await window.api.call('get_scheduler_status');
      const timerEl = document.getElementById('dashboard-countdown-text');
      if (timerEl && res && res.success) {
        if (res.is_running) {
          const m = Math.floor(res.time_remaining / 60);
          const s = res.time_remaining % 60;
          timerEl.textContent = `${m}:${s < 10 ? '0' : ''}${s}`;
        } else {
          timerEl.textContent = 'Désactivé';
        }
      }
    };
    updateCountdown();
    this.timerInterval = setInterval(updateCountdown, 2000);
  }
}

window.dashboardPage = new DashboardPage();

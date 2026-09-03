/**
 * Contrôleur de l'Aperçu & Cadrage avant application.
 */
class PreviewPage {
  constructor() {
    this.videoEl = null;
    this.imgEl = null;
    this.activeWallpaper = null;
    this.fitMode = 'contain'; // contain (fit), cover (fill/crop), 100% (stretch), center
  }

  init() {
    window.router.register('preview', this);
    this.videoEl = document.getElementById('preview-video-player');
    this.imgEl = document.getElementById('preview-image-display');

    // Boutons de mode de cadrage (Fill, Fit, Stretch, Center, Crop)
    document.querySelectorAll('.fit-mode-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.fit-mode-btn').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        const mode = btn.getAttribute('data-fit');
        this.setFitMode(mode);
      });
    });

    // Contrôles vidéo
    const playPauseBtn = document.getElementById('preview-play-pause-btn');
    const timeline = document.getElementById('preview-timeline');
    const volumeSlider = document.getElementById('preview-volume');

    playPauseBtn?.addEventListener('click', () => {
      if (this.videoEl.paused) {
        this.videoEl.play();
        playPauseBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>';
      } else {
        this.videoEl.pause();
        playPauseBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>';
      }
    });

    if (this.videoEl) {
      this.videoEl.addEventListener('timeupdate', () => {
        if (timeline && this.videoEl.duration) {
          timeline.value = (this.videoEl.currentTime / this.videoEl.duration) * 100;
        }
      });
    }

    timeline?.addEventListener('input', (e) => {
      if (this.videoEl && this.videoEl.duration) {
        this.videoEl.currentTime = (e.target.value / 100) * this.videoEl.duration;
      }
    });

    volumeSlider?.addEventListener('input', (e) => {
      if (this.videoEl) {
        this.videoEl.volume = e.target.value / 100;
      }
    });

    // Bouton Appliquer directement depuis la vue Preview
    document.getElementById('preview-apply-btn')?.addEventListener('click', async () => {
      if (this.activeWallpaper) {
        const res = await window.api.call('apply_wallpaper', this.activeWallpaper.id, 'all', { fit_mode: this.fitMode });
        if (res && res.success) {
          window.toast.success(`Fond d'écran appliqué : ${this.activeWallpaper.file_name}`);
          window.store.refreshCurrent();
        } else {
          window.toast.error("Échec de l'application.");
        }
      }
    });

    // Bouton Retoucher
    document.getElementById('preview-edit-btn')?.addEventListener('click', () => {
      if (this.activeWallpaper) {
        window.store.set('selectedWallpaper', this.activeWallpaper);
        window.router.navigate('editor');
      }
    });
  }

  onEnter() {
    const wp = window.store.get('selectedWallpaper') || window.store.get('currentWallpaper');
    this.loadWallpaper(wp);
  }

  loadWallpaper(wp) {
    if (!wp) return;
    this.activeWallpaper = wp;

    const fileUrl = wp.file_path ? `file://${wp.file_path}` : '';
    const isVideo = wp.media_type === 'video';
    const videoControls = document.getElementById('preview-video-controls-box');

    if (isVideo) {
      if (this.imgEl) this.imgEl.style.display = 'none';
      if (this.videoEl) {
        this.videoEl.style.display = 'block';
        this.videoEl.src = fileUrl;
        this.videoEl.play().catch(() => {});
      }
      if (videoControls) videoControls.style.display = 'flex';
    } else {
      if (this.videoEl) {
        this.videoEl.pause();
        this.videoEl.style.display = 'none';
      }
      if (this.imgEl) {
        this.imgEl.style.display = 'block';
        this.imgEl.src = fileUrl;
      }
      if (videoControls) videoControls.style.display = 'none';
    }

    // Mise à jour de l'inspecteur technique
    document.getElementById('preview-spec-name').textContent = wp.file_name;
    document.getElementById('preview-spec-type').textContent = wp.media_type.toUpperCase();
    document.getElementById('preview-spec-res').textContent = `${wp.width || 1920} x ${wp.height || 1080} px`;
    document.getElementById('preview-spec-size').textContent = `${(wp.file_size / (1024 * 1024)).toFixed(2)} MB`;
    document.getElementById('preview-spec-screen').textContent = `${window.screen.width} x ${window.screen.height} px`;
  }

  setFitMode(mode) {
    this.fitMode = mode;
    const target = this.activeWallpaper?.media_type === 'video' ? this.videoEl : this.imgEl;
    if (!target) return;

    if (mode === 'fill' || mode === 'crop') {
      target.style.objectFit = 'cover';
    } else if (mode === 'fit') {
      target.style.objectFit = 'contain';
    } else if (mode === 'stretch') {
      target.style.objectFit = 'fill';
    } else if (mode === 'center') {
      target.style.objectFit = 'none';
    }
  }
}

window.previewPage = new PreviewPage();

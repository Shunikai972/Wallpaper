/**
 * Contrôleur de l'Éditeur d'Image Non Destructif sur Canvas HTML5.
 */
class EditorPage {
  constructor() {
    this.canvas = null;
    this.ctx = null;
    this.sourceImg = new Image();
    this.activeWallpaper = null;

    // Valeurs par défaut des réglages
    this.defaultAdjustments = {
      brightness: 1.0,
      contrast: 1.0,
      saturation: 1.0,
      vibrance: 1.0,
      exposure: 0.0,
      temperature: 0.0,
      tint: 0.0,
      sharpness: 0.0,
      blur: 0.0,
      vignette: 0.0,
      black_and_white: false,
      sepia: false,
      rotate: 0,
      flip_h: false,
      flip_v: false
    };
    this.currentAdjustments = { ...this.defaultAdjustments };
  }

  init() {
    window.router.register('editor', this);
    this.canvas = document.getElementById('editor-canvas');
    if (this.canvas) this.ctx = this.canvas.getContext('2d');

    this.sourceImg.crossOrigin = 'anonymous';
    this.sourceImg.onload = () => this.renderCanvas();

    // Raccordement des sliders
    this.bindSlider('editor-brightness', 'brightness', (v) => `${Math.round(v * 100)}%`);
    this.bindSlider('editor-contrast', 'contrast', (v) => `${Math.round(v * 100)}%`);
    this.bindSlider('editor-saturation', 'saturation', (v) => `${Math.round(v * 100)}%`);
    this.bindSlider('editor-exposure', 'exposure', (v) => `${v > 0 ? '+' : ''}${v}`);
    this.bindSlider('editor-temperature', 'temperature', (v) => `${v > 0 ? '+' : ''}${Math.round(v * 100)}`);
    this.bindSlider('editor-tint', 'tint', (v) => `${v > 0 ? '+' : ''}${Math.round(v * 100)}`);
    this.bindSlider('editor-blur', 'blur', (v) => `${v}px`);
    this.bindSlider('editor-vignette', 'vignette', (v) => `${Math.round(v * 100)}%`);

    // Toggles Noir & Blanc et Sépia
    document.getElementById('editor-bw-toggle')?.addEventListener('change', (e) => {
      this.currentAdjustments.black_and_white = e.target.checked;
      if (e.target.checked) {
        this.currentAdjustments.sepia = false;
        const sepiaToggle = document.getElementById('editor-sepia-toggle');
        if (sepiaToggle) sepiaToggle.checked = false;
      }
      this.renderCanvas();
    });

    document.getElementById('editor-sepia-toggle')?.addEventListener('change', (e) => {
      this.currentAdjustments.sepia = e.target.checked;
      if (e.target.checked) {
        this.currentAdjustments.black_and_white = false;
        const bwToggle = document.getElementById('editor-bw-toggle');
        if (bwToggle) bwToggle.checked = false;
      }
      this.renderCanvas();
    });

    // Rotation et retournements
    document.getElementById('editor-rotate-cw')?.addEventListener('click', () => {
      this.currentAdjustments.rotate = (this.currentAdjustments.rotate + 90) % 360;
      this.renderCanvas();
    });

    document.getElementById('editor-rotate-ccw')?.addEventListener('click', () => {
      this.currentAdjustments.rotate = (this.currentAdjustments.rotate - 90 + 360) % 360;
      this.renderCanvas();
    });

    document.getElementById('editor-flip-h')?.addEventListener('click', () => {
      this.currentAdjustments.flip_h = !this.currentAdjustments.flip_h;
      this.renderCanvas();
    });

    document.getElementById('editor-flip-v')?.addEventListener('click', () => {
      this.currentAdjustments.flip_v = !this.currentAdjustments.flip_v;
      this.renderCanvas();
    });

    // Presets
    this.bindPresets();

    // Réinitialisation
    document.getElementById('editor-reset-btn')?.addEventListener('click', () => {
      this.resetControls();
    });

    // Sauvegarde non destructive
    document.getElementById('editor-save-btn')?.addEventListener('click', async () => {
      if (!this.activeWallpaper) return;
      const res = await window.api.call('save_adjustments', this.activeWallpaper.id, this.currentAdjustments);
      if (res && res.success) {
        window.toast.success('Réglages sauvegardés sans modifier le fichier original.');
      } else {
        window.toast.error('Erreur lors de la sauvegarde.');
      }
    });

    // Appliquer directement
    document.getElementById('editor-apply-btn')?.addEventListener('click', async () => {
      if (!this.activeWallpaper) return;
      await window.api.call('save_adjustments', this.activeWallpaper.id, this.currentAdjustments);
      const res = await window.api.call('apply_wallpaper', this.activeWallpaper.id);
      if (res && res.success) {
        window.toast.success(`Fond retouché appliqué : ${this.activeWallpaper.file_name}`);
        window.store.refreshCurrent();
      }
    });
  }

  bindSlider(id, key, formatFn) {
    const slider = document.getElementById(id);
    const label = document.getElementById(`${id}-val`);
    if (!slider) return;

    slider.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      this.currentAdjustments[key] = val;
      if (label) label.textContent = formatFn(val);
      this.renderCanvas();
    });
  }

  bindPresets() {
    const presets = {
      'preset-vibrant': { brightness: 1.05, contrast: 1.15, saturation: 1.3, temperature: 0.1, vignette: 0.15 },
      'preset-nordic': { brightness: 1.0, contrast: 1.1, saturation: 0.85, temperature: -0.25, tint: 0.05, vignette: 0.2 },
      'preset-cinema-bw': { brightness: 1.0, contrast: 1.3, black_and_white: true, vignette: 0.35 },
      'preset-vintage': { brightness: 0.95, contrast: 1.05, sepia: true, temperature: 0.2, vignette: 0.3 }
    };

    Object.entries(presets).forEach(([btnId, p]) => {
      document.getElementById(btnId)?.addEventListener('click', () => {
        this.currentAdjustments = { ...this.defaultAdjustments, ...p };
        this.syncControlsToState();
        this.renderCanvas();
        window.toast.info('Préréglage appliqué.');
      });
    });
  }

  syncControlsToState() {
    const adj = this.currentAdjustments;
    const setVal = (id, v) => {
      const el = document.getElementById(id);
      if (el) el.value = v;
      const lbl = document.getElementById(`${id}-val`);
      if (lbl) lbl.textContent = v;
    };

    setVal('editor-brightness', adj.brightness);
    setVal('editor-contrast', adj.contrast);
    setVal('editor-saturation', adj.saturation);
    setVal('editor-exposure', adj.exposure);
    setVal('editor-temperature', adj.temperature);
    setVal('editor-tint', adj.tint);
    setVal('editor-blur', adj.blur);
    setVal('editor-vignette', adj.vignette);

    const bw = document.getElementById('editor-bw-toggle');
    if (bw) bw.checked = adj.black_and_white;
    const sepia = document.getElementById('editor-sepia-toggle');
    if (sepia) sepia.checked = adj.sepia;
  }

  resetControls() {
    this.currentAdjustments = { ...this.defaultAdjustments };
    this.syncControlsToState();
    this.renderCanvas();
    window.toast.info('Réglages réinitialisés.');
  }

  async onEnter() {
    const wp = window.store.get('selectedWallpaper') || window.store.get('currentWallpaper');
    if (!wp) return;
    this.activeWallpaper = wp;

    // Chargement des ajustements existants depuis la base
    const res = await window.api.call('get_adjustments', wp.id);
    if (res && res.success && Object.keys(res.data).length > 0) {
      this.currentAdjustments = { ...this.defaultAdjustments, ...res.data };
    } else {
      this.currentAdjustments = { ...this.defaultAdjustments };
    }
    this.syncControlsToState();

    const imgUrl = wp.thumbnail_path
      ? (wp.thumbnail_path.startsWith('http') ? wp.thumbnail_path : `file://${wp.thumbnail_path}`)
      : `file://${wp.file_path}`;
    this.sourceImg.src = imgUrl;
  }

  renderCanvas() {
    if (!this.ctx || !this.sourceImg.complete || !this.sourceImg.naturalWidth) return;

    const w = this.sourceImg.naturalWidth;
    const h = this.sourceImg.naturalHeight;
    const rot = this.currentAdjustments.rotate;
    const isSideways = rot === 90 || rot === 270;

    this.canvas.width = isSideways ? h : w;
    this.canvas.height = isSideways ? w : h;

    this.ctx.save();
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Transformation de géométrie (rotate, flip)
    this.ctx.translate(this.canvas.width / 2, this.canvas.height / 2);
    this.ctx.rotate((rot * Math.PI) / 180);
    this.ctx.scale(
      this.currentAdjustments.flip_h ? -1 : 1,
      this.currentAdjustments.flip_v ? -1 : 1
    );

    // Filtres CSS Canvas (Luminosité, Contraste, Saturation, Blur, N&B, Sépia)
    let filterString = `brightness(${this.currentAdjustments.brightness * (1 + this.currentAdjustments.exposure)}) `;
    filterString += `contrast(${this.currentAdjustments.contrast}) `;
    if (this.currentAdjustments.black_and_white) {
      filterString += `grayscale(100%) `;
    } else if (this.currentAdjustments.sepia) {
      filterString += `sepia(85%) `;
    } else {
      filterString += `saturate(${this.currentAdjustments.saturation}) `;
    }
    if (this.currentAdjustments.blur > 0) {
      filterString += `blur(${this.currentAdjustments.blur}px) `;
    }
    this.ctx.filter = filterString;

    this.ctx.drawImage(this.sourceImg, -w / 2, -h / 2, w, h);
    this.ctx.restore();

    // Application du vignettage
    if (this.currentAdjustments.vignette > 0) {
      this.applyCanvasVignette(this.currentAdjustments.vignette);
    }
  }

  applyCanvasVignette(intensity) {
    const w = this.canvas.width;
    const h = this.canvas.height;
    const radius = Math.sqrt((w / 2) ** 2 + (h / 2) ** 2);
    const grad = this.ctx.createRadialGradient(w / 2, h / 2, radius * (1 - intensity * 0.7), w / 2, h / 2, radius);
    grad.addColorStop(0, 'rgba(0,0,0,0)');
    grad.addColorStop(1, `rgba(0,0,0,${Math.min(0.95, intensity * 0.9)})`);

    this.ctx.fillStyle = grad;
    this.ctx.fillRect(0, 0, w, h);
  }
}

window.editorPage = new EditorPage();

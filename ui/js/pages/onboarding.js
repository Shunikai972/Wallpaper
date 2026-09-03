/**
 * Assistant de premier lancement (Onboarding) en 7 étapes fluides.
 */
class OnboardingWizard {
  constructor() {
    this.currentStep = 1;
    this.totalSteps = 7;
    this.overlay = null;
  }

  init() {
    this.overlay = document.getElementById('onboarding-modal-overlay');

    // Vérification si onboarding déjà validé
    window.api.ready().then(async () => {
      const cfgRes = await window.api.call('get_config');
      if (cfgRes && cfgRes.success && !cfgRes.data?.onboarding_completed) {
        this.show();
      }
    });

    document.getElementById('onboarding-next-btn')?.addEventListener('click', () => {
      this.nextStep();
    });

    document.getElementById('onboarding-skip-btn')?.addEventListener('click', () => {
      this.finish();
    });
  }

  show() {
    if (this.overlay) {
      this.overlay.style.display = 'flex';
      this.renderStep();
    }
  }

  async nextStep() {
    if (this.currentStep < this.totalSteps) {
      this.currentStep++;
      await this.renderStep();
    } else {
      await this.finish();
    }
  }

  async finish() {
    await window.api.call('update_config', 'onboarding_completed', true);
    if (this.overlay) {
      this.overlay.style.display = 'none';
    }
    window.toast.success('Bienvenue sur WallpaperMaison !');
    window.store.refreshAll();
  }

  async renderStep() {
    const titleEl = document.getElementById('onboarding-step-title');
    const contentEl = document.getElementById('onboarding-step-content');
    const dotsContainer = document.getElementById('onboarding-step-dots');
    const nextBtn = document.getElementById('onboarding-next-btn');

    // Mise à jour des indicateurs de progression
    if (dotsContainer) {
      dotsContainer.innerHTML = '';
      for (let i = 1; i <= this.totalSteps; i++) {
        const dot = document.createElement('div');
        dot.className = `dot ${i === this.currentStep ? 'active' : ''}`;
        dotsContainer.appendChild(dot);
      }
    }

    if (this.currentStep === 1) {
      titleEl.textContent = 'Bienvenue sur WallpaperMaison';
      contentEl.innerHTML = `
        <div style="font-size:14px; color:var(--text-secondary); line-height:1.6;">
          L'alternative moderne et haut de gamme à Wallpaper Engine conçue pour <strong>Linux Fedora</strong>.<br>
          Images statiques, GIFs animés, vidéos 4K et transitions fluides pour votre bureau.
        </div>
      `;
      if (nextBtn) nextBtn.textContent = 'Commencer la configuration →';
    } else if (this.currentStep === 2) {
      titleEl.textContent = 'Analyse de votre Système Linux';
      contentEl.innerHTML = `
        <div style="display:flex; flex-direction:column; align-items:center; gap:16px;">
          <div class="pulse-dot" style="width:16px; height:16px;"></div>
          <div style="font-size:13px; color:var(--text-secondary);">Détection de l'environnement Fedora et du compositeur...</div>
        </div>
      `;
      setTimeout(async () => {
        const sys = await window.api.call('get_system_info');
        if (contentEl && sys && sys.success) {
          const d = sys.data;
          contentEl.innerHTML = `
            <div style="font-size:13.5px; text-align:left; background:var(--bg-surface-raised); padding:16px; border-radius:var(--radius-md);">
              <div>🔹 <strong>Distribution :</strong> ${d.distro?.pretty_name || 'Fedora'}</div>
              <div style="margin-top:6px;">🔹 <strong>Serveur d'affichage :</strong> ${d.session_type?.toUpperCase()} (Wayland actif)</div>
              <div style="margin-top:6px;">🔹 <strong>Bureau :</strong> ${d.desktop_env?.toUpperCase()}</div>
            </div>
          `;
        }
      }, 500);
      if (nextBtn) nextBtn.textContent = 'Suivant →';
    } else if (this.currentStep === 3) {
      titleEl.textContent = 'Détection des Écrans';
      const monRes = await window.api.call('get_monitors');
      const count = monRes?.data?.length || 1;
      contentEl.innerHTML = `
        <div style="font-size:13.5px; color:var(--text-secondary);">
          <strong>${count} écran(s)</strong> détecté(s). Prise en charge du multi-moniteurs et du mode panoramique étendu prête.
        </div>
      `;
    } else if (this.currentStep === 4) {
      titleEl.textContent = 'Moteurs de Fond d\'Écran';
      contentEl.innerHTML = `
        <div style="font-size:13.5px; color:var(--text-secondary); line-height:1.5;">
          Votre système utilise automatiquement <strong>GNOME GSettings</strong> pour les images et <strong>mpvpaper</strong> pour les vidéos et animations Wayland.
        </div>
      `;
    } else if (this.currentStep === 5) {
      titleEl.textContent = 'Dossier de Fonds d\'Écran';
      contentEl.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:12px; align-items:center;">
          <p style="font-size:13px; color:var(--text-secondary);">Votre dossier par défaut est configuré sur <code>~/Pictures/Wallpapers</code>.</p>
          <button class="btn btn-secondary" id="onboarding-pick-folder-btn">Choisir un autre dossier...</button>
        </div>
      `;
      document.getElementById('onboarding-pick-folder-btn')?.addEventListener('click', async () => {
        const res = await window.api.call('open_directory_dialog');
        if (res && res.success) {
          window.toast.success(`Dossier sélectionné: ${res.folder}`);
        }
      });
    } else if (this.currentStep === 6) {
      titleEl.textContent = 'Profil de Performance';
      contentEl.innerHTML = `
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
          <div class="profile-card-option active" style="padding:14px; background:var(--bg-surface-raised); border:1px solid var(--border-subtle); border-radius:var(--radius-md); text-align:left;">
            <div style="font-weight:600; color:var(--accent-primary);">Balanced (Recommandé)</div>
            <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">30 FPS, pause automatique en jeu ou sur batterie.</div>
          </div>
          <div class="profile-card-option" style="padding:14px; background:var(--bg-surface-raised); border:1px solid var(--border-subtle); border-radius:var(--radius-md); text-align:left;">
            <div style="font-weight:600;">Quality</div>
            <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">60 FPS natif, rendu haute fidélité permanent.</div>
          </div>
        </div>
      `;
    } else if (this.currentStep === 7) {
      titleEl.textContent = 'Vous êtes prêt !';
      contentEl.innerHTML = `
        <div style="font-size:14px; color:var(--text-secondary); line-height:1.6;">
          WallpaperMaison est configuré pour votre système Fedora.<br>
          Glissez vos vidéos et images dans la bibliothèque pour personnaliser votre bureau.
        </div>
      `;
      if (nextBtn) nextBtn.textContent = 'Accéder à l\'application';
    }
  }
}

window.onboardingWizard = new OnboardingWizard();

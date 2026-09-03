/**
 * Contrôleur de la gestion multi-écrans avec canevas visuel interactif.
 */
class MonitorsPage {
  constructor() {
    this.monitors = [];
    this.selectedMonitor = null;
    this.mode = 'clone'; // clone, individual, span
  }

  init() {
    window.router.register('monitors', this);

    // Modes multi-écrans
    document.querySelectorAll('.monitor-mode-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        document.querySelectorAll('.monitor-mode-btn').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        this.mode = btn.getAttribute('data-mode');
        await window.api.call('update_config', 'multi_monitor.mode', this.mode);
        window.toast.info(`Mode d'affichage : ${btn.textContent.trim()}`);
      });
    });

    document.getElementById('refresh-monitors-btn')?.addEventListener('click', async () => {
      await this.loadMonitors();
      window.toast.success('Détection des écrans mise à jour.');
    });
  }

  async onEnter() {
    await this.loadMonitors();
  }

  async loadMonitors() {
    const res = await window.api.call('get_monitors');
    if (res && res.success) {
      this.monitors = res.data || [];
      this.render();
    }
  }

  render() {
    const canvas = document.getElementById('monitors-visual-canvas');
    if (!canvas) return;

    canvas.innerHTML = '';
    const fragment = document.createDocumentFragment();

    this.monitors.forEach((m, idx) => {
      const box = document.createElement('div');
      box.className = `monitor-screen-box ${idx === 0 ? 'active' : ''}`;

      box.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
          <div>
            <div style="font-weight:700; font-size:15px; color:var(--text-primary);">${m.name || m.id}</div>
            <div style="font-size:12px; color:var(--text-muted); font-family:var(--font-mono);">${m.width} x ${m.height} px</div>
          </div>
          ${m.is_primary ? '<span class="badge" style="background:rgba(163,190,140,0.2); color:var(--accent-primary); border:1px solid var(--accent-primary);">Principal</span>' : ''}
        </div>
        <div style="text-align:center; padding:16px 0; color:var(--text-secondary); font-size:12px;">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom:6px; opacity:0.6;"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
          <div>${m.refresh_rate ? `${m.refresh_rate} Hz` : '60 Hz'}</div>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border-subtle); padding-top:10px;">
          <span style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono);">${m.connector || m.id}</span>
          <button class="btn btn-secondary btn-assign-wp" style="padding:4px 10px; font-size:11px;">Changer le fond</button>
        </div>
      `;

      box.querySelector('.btn-assign-wp')?.addEventListener('click', (e) => {
        e.stopPropagation();
        window.toast.info(`Sélectionnez un fond d'écran dans la bibliothèque pour ${m.name}.`);
        window.router.navigate('library');
      });

      box.addEventListener('click', () => {
        document.querySelectorAll('.monitor-screen-box').forEach((b) => b.classList.remove('active'));
        box.classList.add('active');
        this.selectedMonitor = m;
      });

      fragment.appendChild(box);
    });

    canvas.appendChild(fragment);
  }
}

window.monitorsPage = new MonitorsPage();

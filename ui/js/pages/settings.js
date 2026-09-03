/**
 * Contrôleur des Paramètres et Diagnostics système.
 */
class SettingsPage {
  constructor() {
    this.activeTab = 'general';
  }

  init() {
    window.router.register('settings', this);

    // Onglets des paramètres
    document.querySelectorAll('.settings-tab-btn').forEach((tab) => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.settings-tab-btn').forEach((t) => t.classList.remove('active'));
        tab.classList.add('active');
        this.activeTab = tab.getAttribute('data-tab');
        this.switchTab(this.activeTab);
      });
    });

    // Profils de performance
    document.querySelectorAll('.profile-card-option').forEach((card) => {
      card.addEventListener('click', async () => {
        document.querySelectorAll('.profile-card-option').forEach((c) => c.classList.remove('active'));
        card.classList.add('active');
        const profile = card.getAttribute('data-profile');
        const res = await window.api.call('set_performance_profile', profile);
        if (res && res.success) {
          window.store.setProfile(profile, res.settings);
          window.toast.success(`Profil activé : ${profile} (${res.settings ? res.settings.max_fps : 60} FPS)`);
        } else {
          window.toast.error("Erreur lors de l'application du profil.");
        }
      });
    });

    // Nettoyage du cache
    document.getElementById('clear-cache-btn')?.addEventListener('click', async () => {
      const res = await window.api.call('clear_cache', true, true);
      if (res && res.success) {
        window.toast.success(`Cache vidé. ${res.data.freed_mb} MB libérés.`);
        await this.loadCacheStats();
      }
    });

    // Lancement au démarrage
    document.getElementById('settings-autostart-toggle')?.addEventListener('change', async (e) => {
      await window.api.call('set_autostart', e.target.checked);
      window.toast.info(`Démarrage automatique ${e.target.checked ? 'activé' : 'désactivé'}.`);
    });

    // Minimiser dans le tray
    document.getElementById('settings-tray-toggle')?.addEventListener('change', async (e) => {
      await window.api.call('update_config', 'minimize_to_tray', e.target.checked);
    });

    // Rafraîchir les logs
    document.getElementById('refresh-logs-btn')?.addEventListener('click', () => {
      this.loadLogs();
    });
  }

  async onEnter() {
    await this.loadConfig();
    await this.loadDiagnostics();
    await this.loadCacheStats();
    await this.loadLogs();
  }

  switchTab(tab) {
    document.querySelectorAll('.settings-section-view').forEach((sec) => {
      sec.style.display = 'none';
    });
    const target = document.getElementById(`settings-sec-${tab}`);
    if (target) target.style.display = 'block';
  }

  async loadConfig() {
    const res = await window.api.call('get_config');
    if (res && res.success) {
      const cfg = res.data;
      const autostartToggle = document.getElementById('settings-autostart-toggle');
      if (autostartToggle) autostartToggle.checked = !!cfg.start_at_login;

      const trayToggle = document.getElementById('settings-tray-toggle');
      if (trayToggle) trayToggle.checked = !!cfg.minimize_to_tray;

      // Profil actif
      const activeProf = cfg.performance_profile || 'Balanced';
      window.store.setProfile(activeProf);
      document.querySelectorAll('.profile-card-option').forEach((c) => {
        if (c.getAttribute('data-profile') === activeProf) {
          c.classList.add('active');
        } else {
          c.classList.remove('active');
        }
      });
    }
  }

  async loadDiagnostics() {
    const res = await window.api.call('get_system_info');
    const tableBody = document.getElementById('diagnostics-table-body');
    if (!tableBody || !res || !res.success) return;

    const data = res.data;
    const distroEl = document.getElementById('diag-distro-name');
    const sessEl = document.getElementById('diag-session-type');
    const deEl = document.getElementById('diag-desktop-env');

    if (distroEl) distroEl.textContent = data.distro?.pretty_name || 'Fedora Linux';
    if (sessEl) sessEl.textContent = (data.session_type || 'wayland').toUpperCase();
    if (deEl) deEl.textContent = (data.desktop_env || 'gnome').toUpperCase();

    tableBody.innerHTML = '';
    const tools = data.tools || {};

    Object.entries(tools).forEach(([toolName, info]) => {
      const tr = document.createElement('tr');
      tr.style.borderBottom = '1px solid var(--border-subtle)';

      const statusBadge = info.installed
        ? '<span class="badge" style="background:rgba(163,190,140,0.15); color:var(--accent-primary);">Installé</span>'
        : '<span class="badge" style="background:rgba(208,135,112,0.15); color:var(--accent-warning);">Non détecté</span>';

      tr.innerHTML = `
        <td style="padding:12px 14px; font-weight:600; font-family:var(--font-mono);">${toolName}</td>
        <td style="padding:12px 14px; font-size:12.5px; color:var(--text-secondary);">${info.description}</td>
        <td style="padding:12px 14px;">${statusBadge}</td>
        <td style="padding:12px 14px;">
          ${!info.installed ? `
            <div class="code-snippet-box" style="padding:4px 8px; font-size:11px;">
              <span>${info.install_cmd}</span>
              <button class="btn btn-ghost" style="padding:2px 6px; font-size:10px;" onclick="navigator.clipboard.writeText('${info.install_cmd}'); window.toast.info('Commande copiée !');">Copier</button>
            </div>
          ` : '<span style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono);">' + (info.path || 'Prêt') + '</span>'}
        </td>
      `;
      tableBody.appendChild(tr);
    });
  }

  async loadCacheStats() {
    const res = await window.api.call('get_cache_stats');
    if (res && res.success) {
      const stats = res.data;
      const bar = document.getElementById('cache-progress-fill');
      const text = document.getElementById('cache-stats-text');
      if (bar) bar.style.width = `${stats.percentage}%`;
      if (text) text.textContent = `${stats.total_mb} MB utilisés sur ${stats.max_mb} MB (${stats.percentage}%)`;
    }
  }

  async loadLogs() {
    const res = await window.api.call('get_recent_logs', 60);
    const box = document.getElementById('system-logs-console');
    if (!box || !res || !res.success) return;

    box.innerHTML = '';
    const items = res.data || [];
    items.forEach((item) => {
      const line = document.createElement('div');
      line.style.fontFamily = 'var(--font-mono)';
      line.style.fontSize = '11.5px';
      line.style.lineHeight = '1.6';
      line.style.borderBottom = '1px solid rgba(255,255,255,0.03)';
      line.style.padding = '2px 0';

      const color = item.level === 'ERROR' ? 'var(--accent-danger)' : (item.level === 'WARNING' ? 'var(--accent-secondary)' : 'var(--text-secondary)');
      line.innerHTML = `<span style="color:${color};">[${item.level}]</span> <span style="color:var(--text-muted);">${item.module}:</span> ${item.message}`;
      box.appendChild(line);
    });
    box.scrollTop = box.scrollHeight;
  }
}

window.settingsPage = new SettingsPage();

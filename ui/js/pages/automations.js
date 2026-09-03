/**
 * Contrôleur des Règles et Automatisations contextuelles.
 */
class AutomationsPage {
  constructor() {
    this.automations = [];
  }

  init() {
    window.router.register('automations', this);

    document.getElementById('add-automation-btn')?.addEventListener('click', () => {
      window.modal.open({
        title: 'Nouvelle Automatisation',
        contentHtml: `
          <div style="display:flex; flex-direction:column; gap:14px;">
            <div>
              <label style="font-size:12px; color:var(--text-secondary); display:block; margin-bottom:6px;">Nom de la règle :</label>
              <input type="text" id="auto-name" class="search-input" placeholder="ex: Pause en jeu, Nuit 23:00" style="width:100%;">
            </div>
            <div>
              <label style="font-size:12px; color:var(--text-secondary); display:block; margin-bottom:6px;">Déclencheur (Trigger) :</label>
              <select id="auto-trigger-type" class="search-input" style="width:100%;">
                <option value="time">Horaire spécifique (ex: 08:00)</option>
                <option value="battery">Passage sur Batterie</option>
                <option value="ac_power">Branché sur Secteur</option>
                <option value="fullscreen">Lancement Jeu / Plein écran</option>
              </select>
            </div>
            <div id="auto-cond-wrapper">
              <label style="font-size:12px; color:var(--text-secondary); display:block; margin-bottom:6px;">Condition (ex: heure HH:MM) :</label>
              <input type="text" id="auto-cond" class="search-input" value="20:00" style="width:100%;">
            </div>
            <div>
              <label style="font-size:12px; color:var(--text-secondary); display:block; margin-bottom:6px;">Action à exécuter :</label>
              <select id="auto-action-type" class="search-input" style="width:100%;">
                <option value="set_profile">Changer le Profil de performance</option>
                <option value="set_playlist">Activer une Playlist</option>
                <option value="pause_video">Mettre en pause la vidéo</option>
                <option value="resume_video">Reprendre la vidéo</option>
              </select>
            </div>
            <div>
              <label style="font-size:12px; color:var(--text-secondary); display:block; margin-bottom:6px;">Cible de l'action :</label>
              <input type="text" id="auto-target" class="search-input" placeholder="ex: Battery Saver, Nature, etc." style="width:100%;">
            </div>
          </div>
        `,
        buttons: [
          { text: 'Annuler', className: 'btn-ghost' },
          {
            text: 'Créer la règle',
            className: 'btn-primary',
            onClick: async () => {
              const name = document.getElementById('auto-name')?.value.trim();
              const tType = document.getElementById('auto-trigger-type')?.value;
              const cond = document.getElementById('auto-cond')?.value.trim();
              const aType = document.getElementById('auto-action-type')?.value;
              const target = document.getElementById('auto-target')?.value.trim();

              if (name && tType && aType) {
                const res = await window.api.call('add_automation', name, tType, cond, aType, target, 1);
                if (res && res.success) {
                  window.toast.success(`Règle "${name}" ajoutée.`);
                  await this.loadAutomations();
                }
              }
            }
          }
        ]
      });
    });
  }

  async onEnter() {
    await this.loadAutomations();
  }

  async loadAutomations() {
    const res = await window.api.call('get_automations');
    if (res && res.success) {
      this.automations = res.data || [];
      this.render();
    }
  }

  render() {
    const container = document.getElementById('automations-list-container');
    if (!container) return;

    container.innerHTML = '';
    const fragment = document.createDocumentFragment();

    this.automations.forEach((auto) => {
      const card = document.createElement('div');
      card.className = 'settings-item';
      card.style.background = 'var(--bg-surface)';
      card.style.padding = '16px 20px';
      card.style.borderRadius = 'var(--radius-lg)';
      card.style.border = '1px solid var(--border-subtle)';
      card.style.marginBottom = '12px';

      card.innerHTML = `
        <div style="display:flex; align-items:center; gap:16px;">
          <div style="width:40px; height:40px; border-radius:var(--radius-md); background:rgba(136,192,208,0.12); display:flex; align-items:center; justify-content:center; color:var(--accent-info);">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
          </div>
          <div>
            <div style="font-weight:600; font-size:14px; margin-bottom:2px;">${auto.name}</div>
            <div style="font-size:12px; color:var(--text-muted); font-family:var(--font-mono);">
              Quand <strong>${auto.trigger_type}</strong> (${auto.trigger_condition}) ➜ Action: <strong>${auto.action_type}</strong> [${auto.action_target}]
            </div>
          </div>
        </div>
        <div style="display:flex; align-items:center; gap:16px;">
          <label class="switch-label">
            <input type="checkbox" class="auto-toggle-input" ${auto.is_enabled ? 'checked' : ''}>
            <div class="switch"></div>
          </label>
          <button class="btn btn-icon btn-del-auto" title="Supprimer">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
          </button>
        </div>
      `;

      card.querySelector('.auto-toggle-input')?.addEventListener('change', async (e) => {
        await window.api.call('toggle_automation', auto.id, e.target.checked);
        window.toast.info(`Règle ${e.target.checked ? 'activée' : 'désactivée'}.`);
      });

      card.querySelector('.btn-del-auto')?.addEventListener('click', async () => {
        await window.api.call('delete_automation', auto.id);
        window.toast.info(`Règle "${auto.name}" supprimée.`);
        await this.loadAutomations();
      });

      fragment.appendChild(card);
    });

    container.appendChild(fragment);
  }
}

window.automationsPage = new AutomationsPage();

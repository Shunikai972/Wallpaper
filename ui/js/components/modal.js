/**
 * Gestionnaire de modales animées.
 */
class ModalManager {
  constructor() {
    this.overlay = document.getElementById('global-modal-overlay');
    this.card = document.getElementById('global-modal-card');
    this.titleEl = document.getElementById('global-modal-title');
    this.bodyEl = document.getElementById('global-modal-body');
    this.footerEl = document.getElementById('global-modal-footer');

    if (this.overlay) {
      this.overlay.addEventListener('click', (e) => {
        if (e.target === this.overlay) {
          this.close();
        }
      });
    }
  }

  open({ title = '', contentHtml = '', buttons = [] }) {
    if (!this.overlay) return;
    this.titleEl.textContent = title;
    this.bodyEl.innerHTML = contentHtml;

    this.footerEl.innerHTML = '';
    buttons.forEach((btnConfig) => {
      const btn = document.createElement('button');
      btn.className = `btn ${btnConfig.className || 'btn-secondary'}`;
      btn.textContent = btnConfig.text;
      btn.addEventListener('click', async () => {
        if (btnConfig.onClick) {
          const res = await btnConfig.onClick();
          if (res !== false) this.close();
        } else {
          this.close();
        }
      });
      this.footerEl.appendChild(btn);
    });

    this.overlay.classList.add('open');
  }

  close() {
    if (this.overlay) {
      this.overlay.classList.remove('open');
    }
  }
}

window.modal = new ModalManager();

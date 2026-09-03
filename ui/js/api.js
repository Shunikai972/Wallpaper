/**
 * API Wrapper pour la communication PyWebView ↔ Frontend.
 * En mode navigateur autonome, fournit des données de simulation pour permettre le développement visuel.
 */
class ApiClient {
  constructor() {
    this.isPyWebView = false;
    this._readyPromise = new Promise((resolve) => {
      if (window.pywebview && window.pywebview.api) {
        this.isPyWebView = true;
        resolve();
      } else {
        window.addEventListener('pywebviewready', () => {
          this.isPyWebView = true;
          resolve();
        });
        // Timeout de fallback si exécuté dans un navigateur classique
        setTimeout(() => {
          if (!this.isPyWebView) {
            console.log('[ApiClient] Mode simulation Web actif (hors PyWebView).');
            resolve();
          }
        }, 300);
      }
    });
  }

  async ready() {
    return this._readyPromise;
  }

  async call(method, ...args) {
    await this.ready();
    if (this.isPyWebView && window.pywebview && window.pywebview.api && typeof window.pywebview.api[method] === 'function') {
      try {
        return await window.pywebview.api[method](...args);
      } catch (err) {
        console.error(`[ApiClient] Erreur d'appel API ${method}:`, err);
        return { success: false, error: err.message || String(err) };
      }
    }
    return this._mockCall(method, ...args);
  }

  // --- Mocks pour prévisualisation dans un navigateur standard ---
  _mockCall(method, ...args) {
    console.debug(`[MockApi] ${method}`, args);

    if (method === 'get_wallpapers') {
      return {
        success: true,
        data: [
          {
            id: 1,
            file_name: 'aurora_borealis_4k.mp4',
            file_path: '/home/user/Pictures/Wallpapers/aurora_borealis_4k.mp4',
            file_size: 45200100,
            media_type: 'video',
            width: 3840,
            height: 2160,
            duration: 24.5,
            fps: 60.0,
            thumbnail_path: 'https://images.unsplash.com/photo-1531366936337-7c912a4589a7?w=600&q=80',
            is_favorite: 1,
            tags: 'nature,night,4k',
            view_count: 14,
            created_at: new Date().toISOString()
          },
          {
            id: 2,
            file_name: 'cyberpunk_rain_city.gif',
            file_path: '/home/user/Pictures/Wallpapers/cyberpunk_rain_city.gif',
            file_size: 18450000,
            media_type: 'gif',
            width: 1920,
            height: 1080,
            duration: 8.0,
            fps: 30.0,
            thumbnail_path: 'https://images.unsplash.com/photo-1519501025264-65ba15a82390?w=600&q=80',
            is_favorite: 1,
            tags: 'city,cyber,rain',
            view_count: 32,
            created_at: new Date().toISOString()
          },
          {
            id: 3,
            file_name: 'minimal_sand_dunes.webp',
            file_path: '/home/user/Pictures/Wallpapers/minimal_sand_dunes.webp',
            file_size: 3400200,
            media_type: 'image',
            width: 5120,
            height: 2880,
            duration: 0,
            fps: 0,
            thumbnail_path: 'https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=600&q=80',
            is_favorite: 0,
            tags: 'minimal,desert,warm',
            view_count: 8,
            created_at: new Date().toISOString()
          },
          {
            id: 4,
            file_name: 'deep_space_nebula.jpg',
            file_path: '/home/user/Pictures/Wallpapers/deep_space_nebula.jpg',
            file_size: 6800100,
            media_type: 'image',
            width: 3840,
            height: 2160,
            duration: 0,
            fps: 0,
            thumbnail_path: 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=600&q=80',
            is_favorite: 0,
            tags: 'space,dark,stars',
            view_count: 5,
            created_at: new Date().toISOString()
          }
        ]
      };
    }

    if (method === 'get_current_wallpaper') {
      return {
        success: true,
        data: {
          id: 1,
          file_name: 'aurora_borealis_4k.mp4',
          file_path: '/home/user/Pictures/Wallpapers/aurora_borealis_4k.mp4',
          file_size: 45200100,
          media_type: 'video',
          width: 3840,
          height: 2160,
          duration: 24.5,
          fps: 60.0,
          thumbnail_path: 'https://images.unsplash.com/photo-1531366936337-7c912a4589a7?w=600&q=80',
          is_favorite: 1,
          tags: 'nature,night,4k'
        }
      };
    }

    if (method === 'get_stats') {
      return {
        success: true,
        data: { total: 4, images: 2, gifs: 1, videos: 1, favorites: 2, total_size_bytes: 73850400 }
      };
    }

    if (method === 'get_all_tags') {
      return { success: true, data: ['nature', 'night', '4k', 'city', 'cyber', 'rain', 'minimal', 'space'] };
    }

    if (method === 'get_monitors') {
      return {
        success: true,
        data: [
          { id: 'DP-1', name: 'DisplayPort-1 (LG UltraFine 4K)', width: 3840, height: 2160, refresh_rate: 144.0, is_primary: true },
          { id: 'HDMI-A-1', name: 'HDMI-1 (Dell Ultrasharp)', width: 2560, height: 1440, refresh_rate: 60.0, is_primary: false }
        ]
      };
    }

    if (method === 'get_system_info') {
      return {
        success: true,
        data: {
          distro: { pretty_name: 'Fedora Linux 40 (Workstation Edition)', is_fedora: true },
          session_type: 'wayland',
          desktop_env: 'gnome',
          recommended_engine: 'mpvpaper',
          tools: {
            gsettings: { installed: true, package_fedora: 'glib2', install_cmd: 'sudo dnf install glib2' },
            mpvpaper: { installed: true, package_fedora: 'mpvpaper', install_cmd: 'sudo dnf install mpvpaper' },
            swww: { installed: false, package_fedora: 'swww', install_cmd: 'cargo install swww ou via COPR' },
            mpv: { installed: true, package_fedora: 'mpv', install_cmd: 'sudo dnf install mpv' },
            ffmpeg: { installed: true, package_fedora: 'ffmpeg', install_cmd: 'sudo dnf install ffmpeg' }
          }
        }
      };
    }

    if (method === 'get_playlists') {
      return {
        success: true,
        data: [
          { id: 1, name: 'Nature & Paysages', icon: 'tree', interval_seconds: 300, is_random: 0, item_count: 12 },
          { id: 2, name: 'Cyber & Néons', icon: 'zap', interval_seconds: 600, is_random: 1, item_count: 8 },
          { id: 3, name: 'Dark Minimal', icon: 'moon', interval_seconds: 900, is_random: 1, item_count: 15 }
        ]
      };
    }

    if (method === 'get_automations') {
      return {
        success: true,
        data: [
          { id: 1, name: 'Matin 08:00', trigger_type: 'time', trigger_condition: '08:00', action_type: 'set_playlist', action_target: 'Nature & Paysages', is_enabled: 1 },
          { id: 2, name: 'Soir 22:00', trigger_type: 'time', trigger_condition: '22:00', action_type: 'set_playlist', action_target: 'Dark Minimal', is_enabled: 1 },
          { id: 3, name: 'Économie Batterie', trigger_type: 'battery', trigger_condition: 'on_battery', action_type: 'set_profile', action_target: 'Battery Saver', is_enabled: 1 }
        ]
      };
    }

    if (method === 'get_config') {
      return {
        success: true,
        data: {
          performance_profile: 'Balanced',
          auto_change: { enabled: true, interval_seconds: 300, mode: 'random_no_repeat' },
          preferred_engine: 'auto',
          start_at_login: false,
          minimize_to_tray: true,
          ui_blur: true,
          ui_animations: true
        }
      };
    }

    if (method === 'get_cache_stats') {
      return {
        success: true,
        data: { total_mb: 142.5, max_mb: 2048, percentage: 6.9, thumbnail_files: 84, processed_files: 6 }
      };
    }

    return { success: true };
  }
}

window.api = new ApiClient();

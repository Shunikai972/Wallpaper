#!/usr/bin/env python3
"""Worker d'arrière-plan vidéo pour WallpaperMaison.
Crée une fenêtre X11 de type DESKTOP intégrée au bureau et y embarque MPV.
Fonctionne sur GNOME (Wayland via Xwayland ou X11 direct) sans droits root.
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time

# Forcer le backend X11/Xwayland pour que GdkX11 et --wid fonctionnent sous Mutter/GNOME
os.environ["GDK_BACKEND"] = "x11"

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkX11", "3.0")
from gi.repository import Gtk, Gdk, GdkX11, GLib

class VideoBackgroundWorker:
    def __init__(self, video_path: str, fps: int = 30, hwdec: str = "auto", ipc_socket: str = "/tmp/wallpapermaison_mpv.sock") -> None:
        self.video_path = video_path
        self.fps = fps
        self.hwdec = hwdec
        self.ipc_socket = ipc_socket
        self.mpv_proc = None
        self.window = None

    def _get_mpv_command(self, xid: int) -> list:
        if shutil.which("mpv"):
            mpv_bin = ["mpv"]
        else:
            mpv_bin = ["flatpak", "run", "--filesystem=host", "--command=mpv", "io.github.celluloid_player.Celluloid"]

        cmd = mpv_bin + [
            f"--wid={xid}",
            "--no-border",
            "--no-audio",
            "--loop-file=inf",
            "--no-osc",
            "--no-osd-bar",
            "--input-default-bindings=no",
            "--input-cursor=no",
            "--input-vo-keyboard=no",
            f"--hwdec={self.hwdec}",
            f"--override-display-fps={self.fps}",
            f"--input-ipc-server={self.ipc_socket}",
            "--vo=gpu,gpu-next,x11",
            self.video_path
        ]
        return cmd

    def run(self) -> None:
        if os.path.exists(self.ipc_socket):
            try:
                os.remove(self.ipc_socket)
            except Exception:
                pass

        # Calcul des dimensions totales des écrans
        display = Gdk.Display.get_default()
        n_monitors = display.get_n_monitors() if display else 1
        min_x, min_y, max_x, max_y = 0, 0, 1920, 1080
        if display:
            for i in range(n_monitors):
                m = display.get_monitor(i)
                if m:
                    g = m.get_geometry()
                    min_x = min(min_x, g.x)
                    min_y = min(min_y, g.y)
                    max_x = max(max_x, g.x + g.width)
                    max_y = max(max_y, g.y + g.height)

        total_width = max(max_x - min_x, 1920)
        total_height = max(max_y - min_y, 1080)

        # Fenêtre placée au niveau DESKTOP (fond d'écran) en dessous de toutes les applications
        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.window.set_title("WallpaperMaison_Background")
        self.window.set_keep_below(True)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.set_accept_focus(False)
        self.window.set_can_focus(False)
        self.window.set_decorated(False)
        self.window.set_default_size(total_width, total_height)
        self.window.resize(total_width, total_height)
        self.window.move(min_x, min_y)
        self.window.realize()

        gdk_win = self.window.get_window()

        # Rendre la fenêtre complètement transparente aux clics souris (click-through)
        # Tous les clics (clic droit sur le bureau pour ouvrir le menu GNOME,
        # clics sur les raccourcis et icônes d'applications) traversent la fenêtre
        # sans jamais interrompre la vidéo ni voler le focus
        try:
            import cairo
            empty_region = cairo.Region()
            gdk_win.input_shape_combine_region(empty_region, 0, 0)
        except Exception:
            pass

        # Forcer la fenêtre tout en bas de la pile de fenêtres
        gdk_win.lower()
        self.window.show_all()
        gdk_win.lower()

        xid = gdk_win.get_xid()
        cmd = self._get_mpv_command(xid)
        self.mpv_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        signal.signal(signal.SIGTERM, self._on_signal_exit)
        signal.signal(signal.SIGINT, self._on_signal_exit)
        if hasattr(signal, "SIGUSR1"):
            signal.signal(signal.SIGUSR1, self._on_signal_pause)
        if hasattr(signal, "SIGUSR2"):
            signal.signal(signal.SIGUSR2, self._on_signal_resume)

        GLib.timeout_add(1000, self._check_mpv_alive)

        try:
            Gtk.main()
        finally:
            self._cleanup()

    def _check_mpv_alive(self) -> bool:
        if self.mpv_proc and self.mpv_proc.poll() is not None:
            Gtk.main_quit()
            return False
        return True

    def _on_signal_pause(self, signum, frame):
        if self.mpv_proc and self.mpv_proc.poll() is None:
            try:
                self.mpv_proc.send_signal(signal.SIGSTOP)
            except Exception:
                pass

    def _on_signal_resume(self, signum, frame):
        if self.mpv_proc and self.mpv_proc.poll() is None:
            try:
                self.mpv_proc.send_signal(signal.SIGCONT)
            except Exception:
                pass

    def _on_signal_exit(self, signum, frame):
        self._cleanup()
        Gtk.main_quit()
        sys.exit(0)

    def _cleanup(self) -> None:
        if self.mpv_proc:
            try:
                if self.mpv_proc.poll() is None:
                    self.mpv_proc.terminate()
                    self.mpv_proc.wait(timeout=1.0)
            except Exception:
                try:
                    self.mpv_proc.kill()
                except Exception:
                    pass
            self.mpv_proc = None

        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None

        if os.path.exists(self.ipc_socket):
            try:
                os.remove(self.ipc_socket)
            except Exception:
                pass

def main():
    parser = argparse.ArgumentParser(description="WallpaperMaison Background Video Worker")
    parser.add_argument("--video", required=True, help="Chemin du fichier vidéo")
    parser.add_argument("--fps", type=int, default=30, help="Nombre max d'images/seconde")
    parser.add_argument("--hwdec", default="auto", help="Accélération matérielle")
    parser.add_argument("--ipc", default="/tmp/wallpapermaison_mpv.sock", help="Chemin socket IPC")
    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"Fichier vidéo introuvable: {args.video}", file=sys.stderr)
        sys.exit(1)

    worker = VideoBackgroundWorker(args.video, fps=args.fps, hwdec=args.hwdec, ipc_socket=args.ipc)
    worker.run()

if __name__ == "__main__":
    main()

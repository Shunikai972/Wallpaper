#!/usr/bin/env bash
# Stable XDG Autostart entry point. Wait for the persistent workspace to mount
# and for the graphical session to publish its display variables.
set -u

LOG_DIR="${HOME}/.cache/wallpapermaison/logs"
mkdir -p "$LOG_DIR" 2>/dev/null || true
exec >>"${LOG_DIR}/session-start.log" 2>&1

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

read_manager_env() {
    command -v systemctl >/dev/null 2>&1 || return 0
    for env_key in WAYLAND_DISPLAY DISPLAY XDG_SESSION_ID XDG_SESSION_TYPE XDG_CURRENT_DESKTOP DBUS_SESSION_BUS_ADDRESS; do
        if [ -z "${!env_key:-}" ]; then
            env_value="$(systemctl --user show-environment 2>/dev/null | sed -n "s/^${env_key}=//p" | head -n 1 || true)"
            if [ -n "$env_value" ]; then
                export "${env_key}=${env_value}"
            fi
        fi
    done
}

find_workspace() {
    for candidate in \
        "${HOME}/reseau/Perso/Bureau/Wallpaper" \
        "${HOME}/reseau/Perso/Wallpaper" \
        "${HOME}/Bureau/Wallpaper" \
        "${HOME}/Wallpaper" \
        "/var/home/${USER:-$(id -un)}/reseau/Perso/Bureau/Wallpaper"; do
        if [ -x "${candidate}/scripts/run.sh" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

attempt=0
while :; do
    attempt=$((attempt + 1))
    read_manager_env
    workspace="$(find_workspace || true)"
    display_ready=false
    if [ -n "${WAYLAND_DISPLAY:-}" ] || [ -n "${DISPLAY:-}" ]; then
        display_ready=true
    fi

    if [ -n "$workspace" ] && [ "$display_ready" = true ]; then
        log "Démarrage de WallpaperMaison dans la session ${XDG_SESSION_ID:-${WAYLAND_DISPLAY:-${DISPLAY}}}: $workspace"
        has_daemon=false
        for argument in "$@"; do
            [ "$argument" = "--daemon" ] && has_daemon=true
        done
        if [ "$has_daemon" = true ]; then
            exec "${workspace}/scripts/run.sh" "$@"
        fi
        exec "${workspace}/scripts/run.sh" --daemon "$@"
    fi
    if [ "$attempt" -eq 1 ] || [ $((attempt % 30)) -eq 0 ]; then
        log "En attente du stockage et de la session graphique (tentative ${attempt})."
    fi
    sleep 2
done

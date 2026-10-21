#define _GNU_SOURCE
#include <stdio.h>
#include <stdarg.h>
#include <dlfcn.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdlib.h>

static int (*real_open)(const char *pathname, int flags, mode_t mode) = NULL;
static int (*real_open64)(const char *pathname, int flags, mode_t mode) = NULL;
static int (*real_openat)(int dirfd, const char *pathname, int flags, mode_t mode) = NULL;
static int (*real_openat64)(int dirfd, const char *pathname, int flags, mode_t mode) = NULL;

static const char *get_redirect_path(void) {
    static char path[512] = {0};
    if (path[0] == '\0') {
        const char *home = getenv("HOME");
        if (!home) {
            const char *user = getenv("USER");
            static char fallback_home[128];
            snprintf(fallback_home, sizeof(fallback_home), "/home/%s", user ? user : "user");
            home = fallback_home;
        }
        char cand[512];
        snprintf(cand, sizeof(cand), "%s/reseau/Perso/.config/wallpapermaison/vscode/workbench.html", home);
        if (access(cand, R_OK) == 0) {
            strncpy(path, cand, sizeof(path) - 1);
        } else {
            snprintf(path, sizeof(path), "%s/.config/wallpapermaison/vscode/workbench.html", home);
        }
    }
    return path;
}

static inline int is_target(const char *path) {
    if (!path) return 0;
    return (strstr(path, "workbench.html") != NULL && strstr(path, "wallpapermaison") == NULL);
}

int open(const char *pathname, int flags, ...) {
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list args; va_start(args, flags); mode = va_arg(args, mode_t); va_end(args);
    }
    if (!real_open) real_open = dlsym(RTLD_NEXT, "open");
    if (is_target(pathname)) {
        return real_open(get_redirect_path(), flags, mode);
    }
    return real_open(pathname, flags, mode);
}

int open64(const char *pathname, int flags, ...) {
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list args; va_start(args, flags); mode = va_arg(args, mode_t); va_end(args);
    }
    if (!real_open64) real_open64 = dlsym(RTLD_NEXT, "open64");
    if (is_target(pathname)) {
        return real_open64(get_redirect_path(), flags, mode);
    }
    return real_open64(pathname, flags, mode);
}

int openat(int dirfd, const char *pathname, int flags, ...) {
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list args; va_start(args, flags); mode = va_arg(args, mode_t); va_end(args);
    }
    if (!real_openat) real_openat = dlsym(RTLD_NEXT, "openat");
    if (is_target(pathname)) {
        return real_openat(AT_FDCWD, get_redirect_path(), flags, mode);
    }
    return real_openat(dirfd, pathname, flags, mode);
}

int openat64(int dirfd, const char *pathname, int flags, ...) {
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list args; va_start(args, flags); mode = va_arg(args, mode_t); va_end(args);
    }
    if (!real_openat64) real_openat64 = dlsym(RTLD_NEXT, "openat64");
    if (is_target(pathname)) {
        return real_openat64(AT_FDCWD, get_redirect_path(), flags, mode);
    }
    return real_openat64(dirfd, pathname, flags, mode);
}

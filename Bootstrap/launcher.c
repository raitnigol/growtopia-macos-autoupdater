/* Native macOS bootstrap. Built for arm64 and x86_64, with no shell evaluation. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>

extern int _NSGetExecutablePath(char *buffer, uint32_t *buffer_size);

static void attach_log(void) {
    const char *home = getenv("HOME");
    char log_directory[8192];
    char log_path[8192];
    if (home == NULL || home[0] != '/') return;
    int n = snprintf(log_directory, sizeof log_directory, "%s/Library/Logs", home);
    if (n < 0 || (size_t)n >= sizeof log_directory) return;
    (void)mkdir(log_directory, 0700);
    n = snprintf(log_path, sizeof log_path, "%s/Growtopia Launcher UI.log", log_directory);
    if (n < 0 || (size_t)n >= sizeof log_path) return;
    (void)freopen(log_path, "a", stderr);
}

int main(void) {
    attach_log();
    char executable[8192];
    uint32_t capacity = (uint32_t)sizeof executable;
    if (_NSGetExecutablePath(executable, &capacity) != 0) {
        fputs("Growtopia Launcher: executable path is too long.\n", stderr);
        return 1;
    }
    char *canonical = realpath(executable, NULL);
    if (canonical == NULL) {
        perror("Growtopia Launcher: cannot resolve executable path");
        return 1;
    }
    char *slash = strrchr(canonical, '/');
    if (slash == NULL) {
        fputs("Growtopia Launcher: executable has no parent directory.\n", stderr);
        free(canonical);
        return 1;
    }
    *slash = '\0';
    char resource_relative[8192];
    int n = snprintf(resource_relative, sizeof resource_relative, "%s/../Resources", canonical);
    free(canonical);
    if (n < 0 || (size_t)n >= sizeof resource_relative) {
        fputs("Growtopia Launcher: resources path is too long.\n", stderr);
        return 1;
    }
    char *resources = realpath(resource_relative, NULL);
    if (resources == NULL) {
        perror("Growtopia Launcher: cannot find bundled resources");
        return 1;
    }
    char script[8192];
    n = snprintf(script, sizeof script, "%s/ui.js", resources);
    if (n < 0 || (size_t)n >= sizeof script || access(script, R_OK) != 0) {
        fputs("Growtopia Launcher: bundled ui.js is missing or unreadable.\n", stderr);
        free(resources);
        return 1;
    }
    char *const arguments[] = {
        "/usr/bin/osascript", "-l", "JavaScript", script, resources, NULL
    };
    execv(arguments[0], arguments);
    perror("Growtopia Launcher: cannot start the macOS UI runtime");
    free(resources);
    return 1;
}

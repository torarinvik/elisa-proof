/* Test-only fault injection: never linked into production executables. */
#define _GNU_SOURCE
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>

static ssize_t injected_write(int fd, const void *data, size_t count) {
    const char *mode = getenv("ELISA_TEST_WRITE_MODE");
    if (fd == STDOUT_FILENO && mode) {
        if (!strcmp(mode, "zero")) return 0;
        if (!strcmp(mode, "error")) { errno = EIO; return -1; }
        if (!strcmp(mode, "partial") && count > 7) count = 7;
    }
    return syscall(SYS_write, fd, data, count);
}

#ifdef __APPLE__
__attribute__((used)) static struct {
    const void *replacement;
    const void *original;
} hook __attribute__((section("__DATA,__interpose"))) = {
    (const void *)injected_write, (const void *)write
};
#else
ssize_t write(int fd, const void *data, size_t count) {
    return injected_write(fd, data, count);
}
#endif

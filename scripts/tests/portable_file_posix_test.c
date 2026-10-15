#define _POSIX_C_SOURCE 200809L
#ifdef __APPLE__
#define _DARWIN_C_SOURCE 1
#endif
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>

int64_t proof_open_regular_readonly(const char *, uint64_t *);
int64_t proof_regular_file_stable(int64_t, const char *, const uint64_t *);

int main(void) {
    char directory[] = "/tmp/elisa-portable-reader-XXXXXX";
    assert(mkdtemp(directory) != NULL);
    char regular[512], fifo[512], changed[512], alias[512], target[512];
    assert(snprintf(regular, sizeof regular, "%s/empty", directory) > 0);
    assert(snprintf(fifo, sizeof fifo, "%s/fifo", directory) > 0);
    assert(snprintf(changed, sizeof changed, "%s/changed", directory) > 0);
    assert(snprintf(alias, sizeof alias, "%s/alias", directory) > 0);
    assert(snprintf(target, sizeof target, "%s/target", directory) > 0);

    int empty = open(regular, O_CREAT | O_EXCL | O_WRONLY, 0600);
    assert(empty >= 0 && close(empty) == 0);
    uint64_t snapshot[8] = {0};
    int64_t descriptor = proof_open_regular_readonly(regular, snapshot);
    assert(descriptor >= 0);
    assert(proof_regular_file_stable(descriptor, regular, snapshot) != 0);
    assert(close((int)descriptor) == 0);

    assert(mkfifo(fifo, 0600) == 0);
    alarm(3);
    assert(proof_open_regular_readonly(fifo, snapshot) < 0);
    alarm(0);
    assert(proof_open_regular_readonly("/dev/null", snapshot) < 0);

    int output = open(changed, O_CREAT | O_EXCL | O_WRONLY, 0600);
    assert(output >= 0 && write(output, "a", 1) == 1 && close(output) == 0);
    descriptor = proof_open_regular_readonly(changed, snapshot);
    assert(descriptor >= 0);
    output = open(changed, O_WRONLY | O_APPEND);
    assert(output >= 0 && write(output, "b", 1) == 1 && close(output) == 0);
    assert(proof_regular_file_stable(descriptor, changed, snapshot) == 0);
    assert(close((int)descriptor) == 0);

    descriptor = proof_open_regular_readonly(changed, snapshot);
    assert(descriptor >= 0);
    output = open(changed, O_WRONLY);
    assert(output >= 0 && pwrite(output, "z", 1, 0) == 1 && close(output) == 0);
    assert(proof_regular_file_stable(descriptor, changed, snapshot) == 0);
    assert(close((int)descriptor) == 0);

    output = open(target, O_CREAT | O_EXCL | O_WRONLY, 0600);
    assert(output >= 0 && write(output, "other", 5) == 5 && close(output) == 0);
    assert(symlink(changed, alias) == 0);
    descriptor = proof_open_regular_readonly(alias, snapshot);
    assert(descriptor >= 0);
    assert(unlink(alias) == 0 && symlink(target, alias) == 0);
    assert(proof_regular_file_stable(descriptor, alias, snapshot) == 0);
    assert(close((int)descriptor) == 0);

    assert(unlink(regular) == 0 && unlink(fifo) == 0 && unlink(changed) == 0);
    assert(unlink(alias) == 0 && unlink(target) == 0);
    assert(rmdir(directory) == 0);
    return 0;
}

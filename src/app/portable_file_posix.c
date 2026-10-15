#define _POSIX_C_SOURCE 200809L
#ifdef __APPLE__
#define _DARWIN_C_SOURCE 1
#endif

#include <errno.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/stat.h>
#include <unistd.h>

/* The stat layout and flag values are target-specific; keep them behind this C ABI. */
enum { PROOF_FILE_SNAPSHOT_WORDS = 8 };

static int proof_snapshot_stat(const struct stat *st, uint64_t *snapshot) {
    if (!S_ISREG(st->st_mode) || st->st_size < 0) return 0;
    snapshot[0] = (uint64_t)st->st_dev;
    snapshot[1] = (uint64_t)st->st_ino;
    snapshot[2] = (uint64_t)st->st_size;
#if defined(__APPLE__)
    snapshot[3] = (uint64_t)st->st_mtimespec.tv_sec;
    snapshot[4] = (uint64_t)st->st_mtimespec.tv_nsec;
    snapshot[5] = (uint64_t)st->st_ctimespec.tv_sec;
    snapshot[6] = (uint64_t)st->st_ctimespec.tv_nsec;
#else
    snapshot[3] = (uint64_t)st->st_mtim.tv_sec;
    snapshot[4] = (uint64_t)st->st_mtim.tv_nsec;
    snapshot[5] = (uint64_t)st->st_ctim.tv_sec;
    snapshot[6] = (uint64_t)st->st_ctim.tv_nsec;
#endif
    snapshot[7] = (uint64_t)(st->st_mode & S_IFMT);
    return 1;
}

static int proof_same_snapshot(const uint64_t *left, const uint64_t *right) {
    for (size_t i = 0; i < PROOF_FILE_SNAPSHOT_WORDS; ++i)
        if (left[i] != right[i]) return 0;
    return 1;
}

int64_t proof_open_regular_readonly(const char *path, uint64_t *snapshot) {
    if (path == NULL || snapshot == NULL) return -1;
    struct stat named_before;
    uint64_t named_before_snapshot[PROOF_FILE_SNAPSHOT_WORDS];
    if (stat(path, &named_before) != 0 ||
        !proof_snapshot_stat(&named_before, named_before_snapshot)) return -1;
    int flags = O_RDONLY | O_NONBLOCK;
#ifdef O_CLOEXEC
    flags |= O_CLOEXEC;
#endif
    int fd;
    do { fd = open(path, flags); } while (fd < 0 && errno == EINTR);
    if (fd < 0) return -1;

    struct stat opened;
    struct stat named;
    uint64_t opened_snapshot[PROOF_FILE_SNAPSHOT_WORDS];
    uint64_t named_snapshot[PROOF_FILE_SNAPSHOT_WORDS];
    int valid = fstat(fd, &opened) == 0 && proof_snapshot_stat(&opened, opened_snapshot) &&
                stat(path, &named) == 0 && proof_snapshot_stat(&named, named_snapshot) &&
                proof_same_snapshot(named_before_snapshot, opened_snapshot) &&
                opened_snapshot[0] == named_snapshot[0] && opened_snapshot[1] == named_snapshot[1];
    if (!valid) {
        (void)close(fd);
        return -1;
    }
    for (size_t i = 0; i < PROOF_FILE_SNAPSHOT_WORDS; ++i) snapshot[i] = opened_snapshot[i];
    return (int64_t)fd;
}

int64_t proof_regular_file_stable(int64_t descriptor, const char *path,
                                  const uint64_t *original_snapshot) {
    if (descriptor < 0 || path == NULL || original_snapshot == NULL) return 0;
    struct stat opened;
    struct stat named;
    uint64_t opened_snapshot[PROOF_FILE_SNAPSHOT_WORDS];
    uint64_t named_snapshot[PROOF_FILE_SNAPSHOT_WORDS];
    if (fstat((int)descriptor, &opened) != 0 || !proof_snapshot_stat(&opened, opened_snapshot) ||
        stat(path, &named) != 0 || !proof_snapshot_stat(&named, named_snapshot)) return 0;
    return proof_same_snapshot(original_snapshot, opened_snapshot) &&
           proof_same_snapshot(opened_snapshot, named_snapshot);
}

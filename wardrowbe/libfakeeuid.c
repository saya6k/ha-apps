#define _GNU_SOURCE
#include <sys/types.h>
#include <sys/stat.h>
#include <dlfcn.h>
#include <pwd.h>
#include <unistd.h>

/*
 * HA add-on containers lack CAP_SETUID/CAP_SETGID/CAP_DAC_OVERRIDE, so we
 * cannot drop to the postgres OS user at runtime. postgres and initdb refuse
 * to run as root (geteuid()==0) and look up the effective UID in /etc/passwd.
 * This shim, loaded via LD_PRELOAD, overrides geteuid/getuid to return 999,
 * getpwuid/getpwnam to satisfy the passwd lookup, and the stat family so the
 * data-directory ownership check (st_uid == geteuid()) also passes.
 * The process runs as actual root; files are root-owned.
 *
 * Loaded ONLY by postgres and initdb (see postgres/run and 00-init.sh).
 */

#define FAKE_UID ((uid_t)999)

uid_t geteuid(void) { return FAKE_UID; }
uid_t getuid(void)  { return FAKE_UID; }

static struct passwd _fake_pw;
static char _pw_name[]   = "postgres";
static char _pw_passwd[] = "x";
static char _pw_gecos[]  = "PostgreSQL Server";
static char _pw_dir[]    = "/var/lib/postgresql";
static char _pw_shell[]  = "/bin/sh";

struct passwd *getpwuid(uid_t uid) {
    (void)uid;
    _fake_pw.pw_name   = _pw_name;
    _fake_pw.pw_passwd = _pw_passwd;
    _fake_pw.pw_uid    = FAKE_UID;
    _fake_pw.pw_gid    = FAKE_UID;
    _fake_pw.pw_gecos  = _pw_gecos;
    _fake_pw.pw_dir    = _pw_dir;
    _fake_pw.pw_shell  = _pw_shell;
    return &_fake_pw;
}

struct passwd *getpwnam(const char *name) {
    /* Pass through to real /etc/passwd so s6-setuidgid can find the
     * real postgres UID (100) and switch to it properly. */
    static struct passwd *(*real)(const char *);
    if (!real) real = dlsym(RTLD_NEXT, "getpwnam");
    return real(name);
}

/* Allow s6-setuidgid to switch to the postgres OS user.
 * setgroups() requires CAP_SETGID which HA containers lack; make it a no-op
 * so s6-setuidgid can proceed to setgid()+setuid() (root can drop privs).
 * Linux-only: Alpine/musl is the only runtime target. */
#ifdef __linux__
int setgroups(size_t size, const gid_t *list) {
    (void)size; (void)list;
    return 0;
}
#endif

static void patch_uid(struct stat *b) { if (b) b->st_uid = FAKE_UID; }

int stat(const char *p, struct stat *b) {
    static int (*real)(const char *, struct stat *);
    if (!real) real = dlsym(RTLD_NEXT, "stat");
    int r = real(p, b); if (!r) patch_uid(b); return r;
}
int fstat(int fd, struct stat *b) {
    static int (*real)(int, struct stat *);
    if (!real) real = dlsym(RTLD_NEXT, "fstat");
    int r = real(fd, b); if (!r) patch_uid(b); return r;
}
int lstat(const char *p, struct stat *b) {
    static int (*real)(const char *, struct stat *);
    if (!real) real = dlsym(RTLD_NEXT, "lstat");
    int r = real(p, b); if (!r) patch_uid(b); return r;
}
int fstatat(int d, const char *p, struct stat *b, int flags) {
    static int (*real)(int, const char *, struct stat *, int);
    if (!real) real = dlsym(RTLD_NEXT, "fstatat");
    int r = real(d, p, b, flags); if (!r) patch_uid(b); return r;
}

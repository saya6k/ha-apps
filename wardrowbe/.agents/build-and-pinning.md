# Build pipeline & version pinning (rationale)

The *why* behind the Dockerfile stages and the upstream-patch decisions.

## Stages

1. **GitHub clone** (`alpine:3.20`) — `git clone --depth 1 --branch
   ${WARDROWBE_VERSION}` from `Anyesh/wardrowbe`. The cloned tree is the
   only path source enters the image. Bump the `ARG WARDROWBE_VERSION`
   default in the `Dockerfile` to upgrade.
2. **Frontend build** (`node:20-alpine`) — `npm ci` + `npm run build`.
   Two `sed` patches applied here, *not* committed upstream:
   - `lib/auth.ts`: dev login enabled when `DEV_LOGIN=true` regardless of
     `NODE_ENV` (lets us ship a built image but still toggle dev mode by
     env at runtime).
   - `next.config.js`: `compress: false` + `images.unoptimized: true`.
     Compression is nginx's job; Image Optimization can't run through
     HA ingress because `/_next/image` doesn't survive the path rewrite.
3. **Python wheels** (HA base image, *not* alpine — must match the final
   image's Python ABI). Builds wheels from `requirements.txt`, then the
   final image installs them with no compiler toolchain.
4. **Final image** (HA base) — runtime packages, wheels installed into
   `/opt/venv`, frontend `.next/standalone` + `static` + `public` copied
   into `/app/frontend`, rootfs copied over.

## Worker shim

`/app/backend/run_worker.py` (written in the Dockerfile, not committed)
tries `app.workers.worker:WorkerSettings` first, falls back to
`app.workers.tagging:WorkerSettings`. Upstream wardrowbe v1.2.2 moved the
class; the shim keeps the worker working across both versions so a
`WARDROWBE_VERSION` bump that re-shuffles modules doesn't break it.

## Pinning policy

- `Dockerfile` `ARG WARDROWBE_VERSION` — bump intentionally on each upstream
  release. (Was `build.yaml`'s `args:` before the Supervisor 2026.04
  build.yaml deprecation; base image + labels moved into the Dockerfile too.)
- Never `@latest` for the frontend or wardrowbe itself — reproducibility
  matters.

## chmod after `COPY rootfs /`

```Dockerfile
RUN chmod a+x /etc/cont-init.d/*.sh \
 && find /etc/s6-overlay/s6-rc.d -type f \( -name run -o -name finish \) -exec chmod a+x {} \; \
 && find /etc/s6-overlay/s6-rc.d -type f -name type -exec chmod 644 {} \;
```

`COPY rootfs /` strips exec bits on some host filesystems (macOS dev
boxes especially). Keep this block in sync when adding a new s6 service.

# Architecture non-goals (Don'ts rationale)

The *why* behind the alternatives recommended in AGENTS's "Don'ts" section.

## chmod outside the Dockerfile

The final image's `COPY rootfs /` strips exec bits when the host
filesystem doesn't preserve them — macOS dev boxes most often. So the
Dockerfile re-asserts them once with `find … -exec chmod a+x`. Adding a
new s6 service means adding a new `run`/`finish` script; if those don't
get exec bits, s6 silently skips the service at boot. Keeping all the
chmod logic in the Dockerfile means one place to audit, and CI sees the
state every build.

## `armv7`/`armhf`/`i386`

Upstream wardrowbe deps that don't have prebuilt wheels for those archs:

- `sharp` (frontend image preprocessing) — only musl/glibc x64 + arm64.
- `asyncpg` (backend) — same.
- `Next.js standalone` build with sharp — same.

A user could *try*, but the multi-hour wheel-build CI cycles and the
likelihood of a runtime ABI mismatch make this a poor default. If a real
user needs another arch, they pin the relevant deps to source-build
versions in a fork; we don't carry that burden upstream.

## `@latest` pinning

Two specific bites we've already taken:

- A floating `@playwright/mcp` pin in the sibling `ha-playwright` addon
  shipped a year-old broken MCP transport (logged in that repo's
  CHANGELOG). We learned: pin transport-layer libs especially hard.
- Upstream wardrowbe v1.2.2 moved `WorkerSettings` — a floating tag
  would have silently broken the worker between two patch releases. We
  pin `WARDROWBE_VERSION` in `build.yaml` for exactly this.

The bump procedure: change the pin, rebuild for one arch, run the smoke
tests in AGENTS's "Sanity checks before PR", land in a release entry
that names the new version.

## `/_next/image` through nginx

Next.js Image Optimization rewrites image URLs to `/_next/image?url=…`
and expects to handle the request itself with Sharp. Behind HA ingress
the path prefix mangling makes the rewrite produce 400s; behind a
reverse proxy on a real domain it works but adds latency for no gain
(the backend already serves the images sized correctly). So we patch
`next.config.js` at build time:

```js
images: { unoptimized: true }
```

This makes Next.js emit plain `<img>` tags pointing at the backend's
real image URLs. Nginx just passes those through. Don't reintroduce the
proxy — there's no scenario where it's a win.

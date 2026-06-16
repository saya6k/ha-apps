# Security Policy

## Reporting a vulnerability

**Do not open a public issue for a security vulnerability.** Use GitHub's
private vulnerability reporting:

→ Security tab → "Report a vulnerability"

If that channel isn't available (e.g. the repo isn't published yet),
contact the maintainer privately first.

Please include:

- Which add-on is affected (`livekit-wakeword`, `nemo-asr-cpp`, `nemotron-asr`,
  `supertonic`, `voiceprint`, `wardrowbe`, `zensical`).
- Affected version (shown in the HA Add-ons UI).
- A reproducer or proof of concept, ideally minimal.
- Impact assessment (what can an attacker do? what privileges are needed?).

You should expect a first response within ~7 days. We'll coordinate a fix
and a disclosure window before publishing details.

## Add-on-specific surface

These add-ons differ in how exposed they are:

- **`wardrowbe`** — exposes a FastAPI backend, Next.js frontend, Postgres,
  Redis, and nginx in one container. Auth modes (Dev / OIDC) are mutually
  exclusive under HA ingress; please describe which mode was active for
  any reported issue.
- **`supertonic`** — Wyoming TTS server on TCP/10209. Minimal surface;
  voice / language inputs are untrusted but mapped through a fixed
  enum.
- **`zensical`** — stateless renderer behind HA ingress, no auth on the
  served site by design; do not expose port 8099 to the host network.

## Out of scope

- Issues that require an attacker with `/config` write access — they
  could rewrite the HA configuration directly anyway.
- Upstream vulnerabilities in pinned third-party code — please report
  those to the upstream project (`anszom/rethink`, `Anyesh/wardrowbe`,
  `vra/supertonic-mnn`, etc.). We'll bump the pin once a fix is
  available.

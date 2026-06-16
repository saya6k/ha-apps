# Auth modes (rationale)

Dev login vs OIDC vs HA ingress — the part that surprises users.

## Precedence (computed in `00-init.sh`)

| `dev_login` | OIDC issuer + client set | Effective backend mode | Notes |
| :--------- | :---------------------- | :------------------ | :---- |
| `true`      | no                       | Dev login            | Any email/name accepted. |
| any         | yes                      | OIDC                 | OIDC auto-overrides `dev_login`. |
| `false`     | no                       | Forced Dev login + warning | Can't run "no auth, no OIDC". |

## OIDC vs HA ingress (mutually exclusive in practice)

OIDC does **not** work through HA ingress — ingress URLs contain dynamic
session tokens that can't be pre-registered as redirect URIs. So:

- HA ingress always uses dev login (safe because HA itself is gated).
- OIDC requires `external_url` pointing at a real reverse proxy domain.
- Both can coexist against the same wardrowbe data: ingress for in-HA
  use, external domain for mobile / desktop browsers.

## Secret persistence

`SECRET_KEY` (FastAPI JWT) and `NEXTAUTH_SECRET` (Next.js session
encryption) are auto-generated on first boot and persisted to
`/config/.secret_key` / `/config/.nextauth_secret`. Explicit addon-config
values take precedence; blank means "auto-generate + persist".

In dev mode, `SECRET_KEY` is forced to `"change-me-in-production"` (the
backend's `_is_dev_mode()` requires this exact value to grant
`/auth/sync` to anyone presenting an external_id).

## `_is_dev_mode()` exact condition (upstream)

From `backend/app/api/auth.py`:

```python
def _is_dev_mode() -> bool:
    return settings.debug and settings.secret_key == DEFAULT_SECRET_KEY
```

So the addon must set `DEBUG=true` *and* keep `SECRET_KEY` as the
upstream default for dev login to actually work. Our 00-init.sh handles
both when `dev_login=true`.

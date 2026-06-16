# Storage layout & backups (rationale)

This is the *why* behind the storage table in `AGENTS.md`. Not shipped.

## Mount table

| HA mount        | Container path                    | What lives here                              | In HA backup? |
| --------------- | --------------------------------- | -------------------------------------------- | ------------- |
| `addon_config`  | `/config/.secret_key`, `.nextauth_secret` | auto-generated secrets    | yes (tiny) |
| `addon_config`  | `/config/photos/`                 | clothing photos (private to this addon)      | yes (in addon snapshot) |
| `data`          | `/data/postgres/data/`            | PostgreSQL cluster                           | **excluded** via `backup_exclude` |
| `data`          | `/data/redis/`                    | Redis AOF/RDB                                | **excluded** via `backup_exclude` |
| `share`         | `/share/wardrowbe/backups/`       | daily `pg_dump` output (`backup` service)    | yes (HA-wide share snapshot) |

## Why PGDATA is under `/data/` (not `/config/`)

`backup_exclude` only applies to paths under `/data/`. Before 1.0.6 PGDATA
lived at `/config/postgres/data/` (addon_config mount) which is *always*
included in HA add-on snapshots — a few thousand clothing items would
balloon every snapshot. Moving PGDATA into `/data/` and excluding
`postgres/**` keeps snapshots small.

Don't move PGDATA back into `/config/`. The size guarantee depends on it.

## Why the `backup` s6 service exists

PGDATA being excluded from snapshots means there's no recovery path
without a dump. Upstream wardrowbe has no backup feature (confirmed by
searching `dump`/`export`/`archive`/`snapshot`/`download` across
`Anyesh/wardrowbe` — only Pydantic `model_dump` / JS exports / item
"archive" status). So the packaging layer ships a daily `pg_dump`:

- Writes `/share/wardrowbe/backups/wardrowbe-<ts>.sql.gz`.
- `/share/` *is* included in HA-wide snapshots, so the dumps go with
  every backup.
- Pruning honours `backup_retention_days` (0 = keep forever).
- Runs as a longrun s6 service: `BACKUP_ENABLED=false` → `sleep infinity`
  (service stays up but does nothing).

If you ever change the destination, keep it under `/share/` or `/media/`
so HA snapshots pick it up. `/data/` won't, because of `backup_exclude`.

## Why photos are at `/config/`, not `/media/`

`/media/` is the HA-wide media share — anything under it shows up in the
Media Browser to every HA user/integration. Personal clothing photos
have no business being broadcast like that. `/config/` (`addon_config`)
is per-addon and private.

## Why the dir name is `/config/photos/`, not `/config/wardrobe/`

`/config/` is already scoped per-addon by HA (it's `addon_config`). The
content under it is *photos*, not "the wardrobe app" — `/config/wardrobe/`
would re-state the addon name. We name by content, so the path reads
"this addon's photos." Brief dev iteration in 1.2.0 used `/config/wardrobe/`
before this was caught; the migration loop in `00-init.sh` handles that
source too.

**Trade-off:** `backup_exclude` only applies to `/data/`, so `/config/
photos/` *is* included in every HA add-on snapshot. A heavy wardrobe
inflates snapshot size. Acceptable because the privacy win matters more
than disk; users with very large wardrobes can manually relocate the
directory and update `STORAGE_PATH`.

We considered `/share/wardrowbe/photos/` (HA-wide share, but in its own
subdir). Rejected: still leaks to anything traversing `/share/`. We
want strict per-addon scoping.

## Migration history

- ≤ 1.0.5: PGDATA at `/config/postgres/data/`. Each snapshot included
  the full cluster.
- 1.0.6: `10-postgres-persist.sh` moves PGDATA to `/data/postgres/data/`.
  The migration code was simplified afterwards (we deleted the legacy
  branch once the user confirmed pre-deployment cleanup was acceptable).
- 1.2.0: photos move from `/media/wardrowbe/` → `/config/photos/`
  (or from `/data/wardrobe/` for pre-1.0 holdouts, or `/config/wardrobe/`
  for the brief in-1.2.0 dev iteration that used the addon-named subdir).
  Migration in `00-init.sh` is one-shot and intentionally minimal —
  it'll be dropped before official public release once everyone in the
  dev rotation is on 1.2.0+.

# rethink add-on — Documentation

## How it works

```
[ LG appliance ] ──(DNS hijack)──► [ ha-rethink add-on ] ──(MQTT)──► [ HA ]
```

The appliance still thinks it is talking to `common.lgthinq.com`. Your DNS
server returns the HA host IP, so the appliance connects to this add-on
instead. The add-on terminates the LG protocol locally and re-publishes the
state to MQTT, where HA's MQTT discovery picks it up as entities.

## Configuration options

| Option              | Type        | Default          | Notes                                                                                                     |
| ------------------- | ----------- | ---------------- | --------------------------------------------------------------------------------------------------------- |
| `hostname`          | string      | `rethink.lan`    | **Must be a real DNS A record** pointing to the HA host IP. Not a raw IP. Not an mDNS name. **Re-pair caveat — see below.** |
| `discovery_prefix`  | string      | `homeassistant`  | Matches your HA MQTT integration's discovery prefix.                                                      |
| `rethink_prefix`    | string      | `rethink`        | Topic prefix for rethink's own state topics.                                                              |
| `log_levels`        | list of str | see add-on UI    | Valid: `status`, `incoming`, `HTTPS`, `publish`, `MGMT`, `outgoing`, `debug`.                             |
| `https_port`        | port        | 4433             | ThinQ2 HTTPS listen port. **Re-pair caveat.**                                                             |
| `mqtts_port`        | port        | 8884             | ThinQ2 MQTTS listen port. **Re-pair caveat.**                                                             |
| `mqtt_port`         | port        | 1884             | ThinQ2 plain MQTT listen port. Safe to change anytime.                                                    |
| `thinq1_https_port` | port        | 46030            | ThinQ1 HTTPS listen port. Change requires updating iptables/NAT target only.                              |
| `thinq1_port`       | port        | 47878            | ThinQ1 protocol listen port. Same iptables/NAT caveat.                                                    |
| `management_port`   | port        | 44401            | Management UI port. **No authentication.** "OPEN WEB UI" button only works at 44401; access manually otherwise. |

MQTT host / port / user / password are pulled automatically from the Mosquitto
broker add-on via Supervisor — you don't set them here.

The add-on runs with `host_network: true`. The management UI on port 44401
has no auth — anyone on your LAN can control rethink. Block it at the
firewall or only run on a trusted segment.

## Changing ports or hostname after pairing

ThinQ2 devices store the rethink server URL in their firmware at pairing
time. Specifically, the device records `hostname` and `https_port` /
`mqtts_port` and keeps using them forever, regardless of what we configure
later. If you change any of those after a device is paired, the device
keeps trying the old URL and silently stops working.

If you must change them after pairing:

1. Stop the add-on.
2. Change the option(s).
3. Re-pair every affected ThinQ2 device using `rethink-setup` (procedure
   in the upstream wiki).

**Safe to change anytime** (no re-pairing needed):

| Option | Why safe |
| --- | --- |
| `mqtt_port` | Not embedded in device URLs |
| `thinq1_https_port`, `thinq1_port` | ThinQ1 devices connect via DNS hijack to fixed standard ports — only your iptables/NAT target needs updating |
| `management_port` | Does not affect devices at all — only the addon's "OPEN WEB UI" button breaks; access manually at `http://<HA-IP>:<port>` |
| `discovery_prefix`, `rethink_prefix` | Restart the add-on to re-publish MQTT discovery; HA entities re-appear under new prefix (old ones may need manual cleanup) |
| `log_levels` | No restart side-effects beyond log volume |

## DNS setup (Pi-hole / AdGuard Home)

Two records are needed. The first lets the appliance find rethink; the second
lets rethink resolve its own configured hostname.

### Pi-hole

1. **Add a local A record** under *Local DNS → DNS Records*:
   - Domain: `rethink.lan` (or whatever you set as `hostname`)
   - IP:     your HA host IP
2. **Add a CNAME (or A) rewrite** under *Local DNS → CNAME Records*:
   - Domain: `common.lgthinq.com`
   - Target: `rethink.lan`
3. **Apply the rewrite only to supported devices.** Use Pi-hole's
   *Group Management* — create a client group containing only the MAC addresses
   of rethink-supported appliances, and scope the rewrite to that group.
   **Do not apply it network-wide.** Unsupported devices must keep going to LG's
   real cloud, or your existing cloud-based LG integration will break.

### AdGuard Home

1. *Filters → DNS rewrites*:
   - `rethink.lan` → HA host IP
   - `common.lgthinq.com` → HA host IP
2. Scope by **Client settings** so only supported devices get the rewrite.

### Why per-client?

If you rewrite `common.lgthinq.com` network-wide, every LG device — including
ones rethink doesn't support — will hit this add-on instead of LG's cloud.
For unsupported devices the add-on has no handler, so they'll just stop
working. Keeping the rewrite scoped to supported MACs leaves the rest alone.

## Device pairing

This add-on does not handle initial Wi-Fi provisioning. You need to run
`rethink-setup` once per device from a separate Linux machine with Wi-Fi.
See the [upstream wiki][wiki] for the procedure.

After provisioning, the appliance will connect to the add-on automatically as
long as DNS is configured.

## Persistent state

Everything that needs to survive add-on restarts lives under `/data`:

- `/data/config.json`  — rendered each boot from add-on options + MQTT creds
- `/data/ca.key`       — TLS CA private key (generated on first run)
- `/data/ca.cert`      — TLS CA certificate
- `/data/state/`       — rethink's bridge / device state
- `/data/options.json` — Supervisor-managed add-on options (do not edit)

## Bridge mode

Bridge mode is an upstream feature that transparently proxies device traffic
to LG's cloud while rethink observes it. It is **not enabled or needed for
normal operation**.

Use it only when:
- You want to keep using the LG mobile app alongside HA for a *supported*
  device, OR
- You are reverse-engineering a new device's protocol and want to capture its
  cloud traffic to contribute back to rethink.

Enabling bridge mode requires logging into your LG account via the management
UI on port 44401 (OAuth flow). The refresh token is stored under `/data`.
Caveats:

- Adds a single point of failure: if the add-on stops, the device also loses
  cloud connectivity.
- Bridge mode does **not** make unsupported devices appear in HA. They will
  still be missing from MQTT — bridge mode only forwards their traffic so the
  LG app / cloud integration keeps working through the proxy.

For day-to-day use: leave it alone.

## Troubleshooting

- **Add-on logs say "MQTT service unavailable"** — install and start the
  Mosquitto broker add-on, then restart this add-on.
- **Device connects but no HA entity appears** — check `discovery_prefix`
  matches HA's MQTT integration, and that `rethink_prefix/...` topics are
  visible in MQTT Explorer.
- **Device never connects** — verify DNS rewrite from *that* device with
  `nslookup common.lgthinq.com` on a machine in the same client group, and
  confirm rethink is listening on the relevant ports.
- **TLS errors after rebuild** — `/data/ca.key` and `/data/ca.cert` are
  generated on first run. If you wiped `/data`, the device may have cached the
  old CA — power-cycle the appliance.

[wiki]: https://github.com/anszom/rethink/wiki

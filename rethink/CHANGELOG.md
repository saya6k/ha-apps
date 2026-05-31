# Changelog

## 0.1.0

- First release. Packages [anszom/rethink](https://github.com/anszom/rethink)
  commit `054407c` (2026-05-11) as a Home Assistant app.
- Publishes supported LG ThinQ devices to MQTT discovery so they appear as
  HA entities.
- Reads MQTT broker credentials from the Mosquitto broker add-on via the
  Supervisor service API (`services: mqtt:need`).
- Persists CA cert/key and rethink bridge state under `/data` so the
  appliance does not need to re-pair across rebuilds.
- Management UI exposed on port 44401 via `webui`. **No authentication** —
  restrict at the network layer.
- amd64 + aarch64 multi-arch build via
  [`hassio-addons/workflows`](https://github.com/hassio-addons/workflows).
- Translations: English, Korean.

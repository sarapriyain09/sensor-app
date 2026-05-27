# Local Dashboard (Fully Offline)

This option gives you a **fully offline** dashboard on the edge/laptop:

**sensor-app → local Mosquitto → Telegraf → InfluxDB → Grafana (local)**

No AWS required.

---

## What’s included in this repo

- Docker Compose services (in `docker-compose.yml`):
  - `mosquitto` (MQTT broker)
  - `sensor-app` (publisher/simulator)
  - `telegraf` (subscribes to `factory/+/telemetry` and writes to InfluxDB)
  - `influxdb` (stores telemetry)
  - `grafana` (dashboard UI)

- Telegraf config:
  - `docker/local-dashboard/telegraf/telegraf.conf`

- Grafana provisioning (auto datasource + auto dashboard import):
  - `docker/local-dashboard/grafana/provisioning/datasources/datasource.yaml`
  - `docker/local-dashboard/grafana/provisioning/dashboards/dashboards.yaml`
  - `docker/local-dashboard/grafana/dashboards/sensor-app-offline.json`

---

## Start it

From the repo root:

```powershell
docker compose up -d
```

### Optional: secure MQTT (username/password)

By default Mosquitto allows anonymous access (safe enough for laptop dev because we bind ports to `127.0.0.1`).

To require a username/password:

1) Create a Mosquitto password file (you will be prompted for the password):

```powershell
docker run --rm -it -v ${PWD}/docker/mosquitto:/mosquitto/config eclipse-mosquitto:2 \
  mosquitto_passwd -c /mosquitto/config/passwordfile sensor
```

Make it readable by the Mosquitto container user:

```powershell
docker run --rm -v ${PWD}/docker/mosquitto:/mosquitto/config alpine:3.20 \
  sh -c "chmod 644 /mosquitto/config/passwordfile"
```

Windows note:
- The secure profile mounts the whole `docker/mosquitto/` directory and runs Mosquitto with `mosquitto.secure.conf` to avoid Windows single-file bind-mount issues.

2) Set env vars for the publisher + telegraf:

```powershell
$env:MQTT_USERNAME = "sensor"
$env:MQTT_PASSWORD = "<the password you chose>"
```

3) Start using the secure override:

```powershell
docker compose -f docker-compose.yml -f docker-compose.secure.yml up -d
```

Notes:
- `docker/mosquitto/passwordfile` is ignored by git.
- This keeps MQTT traffic local; for full encryption you’d enable MQTT-over-TLS.

Open Grafana:

- http://localhost:3000

Login:
- user: `admin` (or `$env:GRAFANA_ADMIN_USER` if you set it)
- pass: `admin` (or `$env:GRAFANA_ADMIN_PASSWORD` if you set it)

Security note:
- `docker-compose.yml` binds ports to `127.0.0.1` (localhost-only) by default.
- If you change bindings to expose ports on your network, set a strong Grafana password and disable anonymous MQTT.

You should see a folder `sensor-app` with a dashboard named **sensor-app (offline local MQTT)**.

If the charts look empty, open the dashboard and change the `machine_id` dropdown (top of dashboard) to match your data (commonly `machine1`).

---

## Common issues

- Port conflict on 3000: stop other Grafana, or change the host port in `docker-compose.yml`.
- No data in Grafana:
  - check Telegraf logs: `docker logs telegraf --tail 200`
  - check sensor-app is publishing: `docker logs sensor-app --tail 200`
  - check MQTT is reachable: `docker logs mosquitto --tail 200`

---

## Notes on fields

Telegraf expects JSON like:
- `factory_id`, `machine_id` (tags)
- `temperature_c`, `vibration_mm_s`, `rpm`, `pressure_bar`, `state` (fields)

If your payload keys differ, tell me the exact JSON and I’ll align `telegraf.conf` + dashboard queries.

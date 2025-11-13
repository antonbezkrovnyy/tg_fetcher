# Observability — notes and how-to

This project integrates with a full observability stack (Grafana, Prometheus, Loki, Pushgateway) but the stack is not included directly inside this repository.

Important notes
- The observability stack for development and production is expected to be managed at the workspace level in the `infrastructure/` directory adjacent to this repository.
- The fetcher service (`telegram-fetcher`) connects to the observability services by service names on the `tg-infrastructure` Docker network (e.g. `tg-loki`, `tg-prometheus`, `tg-pushgateway`).

Quick start (development)

1. From the workspace root (where the `infrastructure/` directory lives) start the observability components. For example, if the infrastructure is a docker-compose project:

```powershell
# from workspace root
cd .\infrastructure
# then (example) bring observability up
# docker-compose up -d prometheus loki grafana pushgateway
```

2. Verify services are reachable on the expected ports (Grafana: 3000, Prometheus: 9090, Loki: 3100, Pushgateway: 9091). The fetcher `docker-compose.yml` refers to these by hostnames on the `tg-infrastructure` network.

3. Start the fetcher (from this repo):

```powershell
# from python-tg repo
docker-compose up -d telegram-fetcher
```

If you don't have the external infrastructure available and you want a minimal local-only run, see the `docker/` directory for local docker-compose examples, or run the fetcher locally with metrics disabled (set `ENABLE_METRICS=false` in `.env`).

Local override inside this repo (optional)

We provide a convenience docker-compose file that runs a minimal observability stack on the external network `tg-infrastructure` so the fetcher can discover it by service names:

- `docker-compose.observability.yml` (in the repo root)
- Helper scripts:
	- `scripts/observability_up.ps1` — ensures the `tg-infrastructure` network exists and brings the stack up
	- `scripts/observability_down.ps1` — stops the stack (optionally removing volumes)

Usage (Windows PowerShell):

```powershell
# From the python-tg repo root
./scripts/observability_up.ps1            # start (add -Recreate to force a fresh start)
# ... work with the app ...
./scripts/observability_down.ps1          # stop (add -RemoveVolumes to clear data)
```

Endpoints (defaults):

- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Loki: http://localhost:3100
- Pushgateway: http://localhost:9091

Notes:

- The compose file mounts configuration from the adjacent workspace `infrastructure/observability/config/*` paths. Keep the standard workspace layout to avoid path issues.
- The down script does not remove the external Docker network, because it may be shared by multiple services in this workspace.

Troubleshooting
- If logs indicate Loki cannot be reached, check the `LOKI_URL` environment variable in `.env` and ensure the observability containers are on the same Docker network as the fetcher.
- For local quick debugging, set `LOG_FORMAT=text` to see plain logs in the container console.

Helper scripts are already provided as described above. If you need a Bash variant for non-Windows hosts, tell us and we'll add it.

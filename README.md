# Kubernetes Health Monitor

A Flask-based website health monitoring service deployed on Kubernetes using Docker and Helm. It periodically checks configured URLs, exposes health endpoints and Prometheus metrics, and visualizes monitoring results in Grafana.

This project demonstrates containerization, Kubernetes deployments, Helm-based configuration, CI/CD, application health probes, autoscaling, and observability using Prometheus and Grafana.

## Features

- Periodic HTTP health checks for configurable websites, run by a background thread.
- REST endpoints for application health, readiness, and monitoring results.
- Prometheus-compatible metrics.
- Docker container running as a non-root user with Gunicorn (one worker, because of the background thread).
- Kubernetes Deployment with two application replicas.
- Kubernetes Service for stable internal networking.
- ConfigMap and Secret for application configuration.
- Liveness and readiness probes.
- Helm-based deployment, upgrade and rollback.
- GitHub Actions CI pipeline using a temporary Kind cluster.
- Horizontal Pod Autoscaler (2 to 5 replicas, 50% CPU target), load-tested on Kind.
- Prometheus scraping and Grafana dashboard visualization.

## Architecture

### Application and monitoring

```text
                         Monitored websites
                         example.com
                         github.com
                              |
                              v
                     +------------------+
                     | Flask Health     |
                     | Monitor          |
                     | Background checks|
                     +------------------+
                              |
                         /metrics
                              |
                              v
                     +------------------+
                     | Prometheus       |
                     | Scrapes metrics  |
                     +------------------+
                              |
                              v
                     +------------------+
                     | Grafana          |
                     | Dashboard        |
                     +------------------+
```

### Kubernetes deployment

```text
Local development
       |
       v
Docker image
       |
       v
Kind cluster
       |
       v
Helm release: health-monitor
       |
       +-- Deployment
       |     +-- Health Monitor Pod
       |     +-- Health Monitor Pod
       |
       +-- Service
       |
       +-- ConfigMap
       |
       +-- Secret
       |
       +-- Horizontal Pod Autoscaler (HPA)
```

Prometheus and Grafana run in the `monitoring` namespace. The Health Monitor runs in the `default` namespace.

### CI pipeline

```text
Git push to main
       |
       v
GitHub Actions
       |
       v
Build Docker image using Git commit SHA
       |
       v
Create temporary Kind cluster
       |
       v
Load image into cluster
       |
       v
Deploy with Helm
       |
       v
Wait for deployment readiness
```

The CI pipeline validates that the image builds and the Helm chart deploys successfully. It does not deploy to a persistent production cluster.

## Technology Stack

- **Language:** Python
- **Web framework:** Flask
- **WSGI server:** Gunicorn
- **HTTP client:** Requests
- **Containerization:** Docker
- **Orchestration:** Kubernetes with Kind
- **Package management:** Helm
- **CI/CD:** GitHub Actions
- **Metrics collection:** Prometheus
- **Visualization:** Grafana
- **Version control:** Git and GitHub

## Application Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /status` | Returns the latest results for monitored websites |
| `GET /healthz` | Liveness probe: is the application alive? |
| `GET /ready` | Readiness probe: has every target been checked at least once? Returns 503 until then |
| `GET /metrics` | Exposes Prometheus metrics in text exposition format |

### Prometheus metrics

The `/metrics` endpoint currently exposes these aggregate metrics:

| Metric | Meaning |
|---|---|
| `health_monitor_targets_total` | Number of configured monitoring targets |
| `health_monitor_targets_up` | Number of healthy targets |
| `health_monitor_targets_down` | Number of unhealthy targets that have been checked |

The `health_monitor_targets_down` metric represents monitored website failures. It is different from Prometheus's built-in `up` metric, which indicates whether Prometheus successfully scraped the application.

## Project Structure

```text
k8s-health-monitor/
├── app.py
├── Dockerfile
├── requirements.txt
├── prometheus-values.yaml
├── helm-chart/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── configmap.yaml
│       ├── secret.yaml
│       └── hpa.yaml
├── k8s/
├── .github/
│   └── workflows/
│       └── deploy.yml
└── README.md
```

- `app.py` — Flask application and background health checker.
- `Dockerfile` — builds the application image, installs dependencies, and runs Gunicorn as a non-root user.
- `requirements.txt` — pinned Python dependencies.
- `helm-chart/` — Helm chart for deploying the application (Deployment, Service, ConfigMap, Secret, HPA).
- `k8s/` — plain Kubernetes manifests retained as reference. Helm is the source of truth.
- `prometheus-values.yaml` — additional Prometheus scrape configuration.
- `.github/workflows/deploy.yml` — GitHub Actions CI pipeline.

## Configuration

The application requires the following environment variables and exits with code 1 if one is missing:

| Variable | Description |
|---|---|
| `MONITOR_TARGETS` | Comma-separated list of URLs to monitor |
| `CHECK_INTERVAL_SECONDS` | Time in seconds between health-check rounds |
| `API_TOKEN` | Application token configured through a Kubernetes Secret (never printed or logged) |

In Kubernetes, the monitoring targets and interval are supplied through a ConfigMap, while the API token is supplied through a Secret. The committed Secret holds only the placeholder `change-me`.

The current configuration monitors:

```text
https://example.com
https://github.com
```

Use placeholders for secrets in examples. Never commit real tokens or credentials.

## Getting Started

### Prerequisites

Install the following tools:

- Python
- Docker
- kubectl
- Kind
- Helm

### 1. Run locally

Clone the repository and enter the project directory:

```bash
git clone https://github.com/tvero1011/k8s-health-monitor.git
cd k8s-health-monitor
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configure the required environment variables:

```bash
export MONITOR_TARGETS="https://example.com,https://github.com"
export CHECK_INTERVAL_SECONDS=10
export API_TOKEN=change-me
```

Run the application:

```bash
python app.py
```

In another terminal, test the endpoints:

```bash
curl http://localhost:5000/healthz
curl http://localhost:5000/status
curl http://localhost:5000/ready
curl http://localhost:5000/metrics
```

`/ready` returns 503 for the first few seconds, until the first round of checks finishes.

### 2. Build and run with Docker

Build the image:

```bash
docker build -t health-monitor:latest .
```

Run the container:

```bash
docker run --rm -p 5000:5000 \
  -e MONITOR_TARGETS="https://example.com,https://github.com" \
  -e CHECK_INTERVAL_SECONDS=10 \
  -e API_TOKEN=change-me \
  health-monitor:latest
```

Test the application at `http://localhost:5000/status`.

### 3. Deploy to Kind using Helm

Create the local cluster:

```bash
kind create cluster --name health-cluster
```

Build and load the image:

```bash
docker build -t health-monitor:latest .
kind load docker-image health-monitor:latest --name health-cluster
```

Install the application:

```bash
helm upgrade --install health-monitor ./helm-chart
```

Verify the deployment:

```bash
kubectl get pods -n default
kubectl get services -n default
kubectl get endpoints health-monitor-service
helm list -A
```

Access the application through port-forwarding:

```bash
kubectl port-forward service/health-monitor-service 8080:80
```

Then test:

```bash
curl http://localhost:8080/status
curl http://localhost:8080/metrics
```

Keep the port-forwarding terminal open while testing. Port-forwarding sends all traffic to a single Pod, so it does not show load sharing between replicas.

After changing `app.py`, rebuild, reload and restart:

```bash
docker build -t health-monitor:latest .
kind load docker-image health-monitor:latest --name health-cluster
kubectl rollout restart deployment/health-monitor
```

### 4. Scale and roll back with Helm

Override the replica count:

```bash
helm upgrade health-monitor ./helm-chart --set replicaCount=4
```

> **Note:** once the HPA from step 5 exists, it controls the replica count. The chart still sets `replicas` from `replicaCount`, so this command and the HPA fight each other and the HPA resets the count within minutes. This is a known limitation (see below). Use this step before you add the HPA, or to demonstrate the conflict.

Inspect the release history:

```bash
helm history health-monitor
```

Roll back to a previous revision when appropriate:

```bash
helm rollback health-monitor 1
```

The revision number must exist in the release history. A rollback creates a new revision rather than erasing the old ones. Helm stores this history inside the cluster, so it is lost if the cluster is deleted.

### 5. Autoscaling (optional)

The HPA needs metrics-server and a CPU request on the Pods (set in the Helm chart). On Kind, metrics-server needs one patch because Kind nodes use self-signed certificates. This is for local learning only.

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl patch deployment metrics-server -n kube-system --type='json' \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
kubectl top nodes
kubectl get hpa
```

Metrics-server is cluster equipment, not part of the Helm release, so it must be installed again if the cluster is recreated.

To see it scale, generate load from inside the cluster and watch:

```bash
kubectl run load --image=busybox:1.36 --restart=Never -- /bin/sh -c \
  "while true; do wget -q -O- http://health-monitor-service/status; done"
kubectl get hpa -w
kubectl delete pod load
```

In testing, average CPU rose far above the 50% target and the Deployment scaled from 2 to 5 replicas. After the load stopped, it scaled back to 2 after roughly five minutes, because Kubernetes waits before removing Pods.

## Prometheus Setup

Prometheus is installed using the `prometheus-community/prometheus` Helm chart in the `monitoring` namespace.

The additional scrape configuration is stored in `prometheus-values.yaml`. It tells Prometheus to scrape the Health Monitor Service at:

```text
health-monitor-service.default.svc.cluster.local:80/metrics
```

To access the Prometheus interface locally:

```bash
kubectl port-forward -n monitoring service/prometheus-server 9090:80
```

Open `http://localhost:9090`.

Useful checks:

- Visit `/targets` to inspect the scrape target state.
- Query `health_monitor_targets_total`.
- Query `health_monitor_targets_up`.
- Query `health_monitor_targets_down`.

A target state of `UP` means Prometheus can scrape the application's metrics endpoint. It does not guarantee that every monitored website is healthy.

## Grafana Dashboard

Grafana is installed in the `monitoring` namespace and configured to use Prometheus as its data source.

Access Grafana:

```bash
kubectl port-forward -n monitoring service/grafana 3000:80
```

Open `http://localhost:3000` and sign in with the configured Grafana administrator credentials.

The `health monitor` dashboard contains two time series panels, each showing its metric over time:

- Healthy website count: `health_monitor_targets_up` (2 when both targets are up)
- Unhealthy website count: `health_monitor_targets_down` (0 when both targets are up)

The current dashboard reflects aggregate target counts, not a separate status panel for every URL.

**Note:** Grafana persistence is disabled in the current local installation. Dashboard changes may be lost if the Grafana Pod is replaced.

## CI/CD Pipeline

The GitHub Actions workflow runs on pushes to `main`.

It:

1. Checks out the repository.
2. Generates a short Git commit SHA for the image tag.
3. Builds the Docker image.
4. Creates a temporary Kind cluster.
5. Loads the image into the cluster.
6. Deploys the application using Helm and waits for it to become ready.

The workflow uses a unique commit-based image tag rather than relying on `latest` for CI deployments. The local Helm chart still defaults to the `latest` tag for convenience, and the CI workflow overrides that value with the commit SHA.

A successful workflow verifies the build and deployment process. It does not provide a public application URL or deploy to production.

## Lessons Learned

- **Running is not ready.** A failing readiness probe removes a Pod from the Service; a failing liveness probe restarts the container. `kubectl get endpoints` shows which Pods really receive traffic.
- **Keep config out of the image.** ConfigMaps hold settings, Secrets hold tokens (base64 is not encryption), and the app fails fast at startup if a setting is missing.
- **Gunicorn changes how the app starts.** It skips the `if __name__ == '__main__'` block, so the background thread starts at module level and only one worker is used.
- **Helm gives repeatable releases.** It tracks revisions and supports rollback. Images must be rebuilt and loaded into Kind after code changes, and CI tags them with the commit SHA.
- **The HPA needs a CPU request** on the Pods, otherwise it shows `<unknown>`.
- **Two different "up" signals.** A healthy Prometheus scrape means the monitor is reachable, not that the monitored websites are healthy. Prometheus collects, Grafana visualizes.

## Known Limitations

- **Local learning setup:** Kind only, images loaded locally (no registry), `latest` tag by default, metrics-server patched by hand, Grafana without persistence, and a placeholder Secret.
- **Replica conflict:** the Deployment sets `replicas` and the HPA also controls it, so every `helm upgrade` resets the count. Fix: omit `replicas` when the HPA is enabled.
- **Monitoring depth:** only aggregate metrics (no per-URL labels or alerts). The checker thread catches only request errors, so an unexpected error would stop it silently while `/healthz` still says OK. Each replica runs its own checker, so scaling multiplies outgoing checks.
- **Hardening gaps:** no memory request or resource limits, no Ingress, TLS or NetworkPolicy, no `.dockerignore`, and the `k8s/` folder can drift from the Helm chart.
- **CI gaps:** no `helm lint` and no unit tests. `ubuntu-latest` is moving to Ubuntu 26.04, so pin `ubuntu-24.04` if the run fails.

## Future Improvements

1. **Chart fixes:** omit `replicas` when the HPA is on, add memory requests and resource limits, and move the URLs into `values.yaml` with `values-dev.yaml` and `values-prod.yaml`.
2. **Reliability:** catch all errors in the checker loop, and make `/healthz` fail if the last successful check is too old.
3. **Observability:** per-target Prometheus metrics with labels, per-URL Grafana panels, alerting rules for unhealthy targets and failed scrapes, and persistent Grafana storage.
4. **CI quality:** add helm lint and unit tests, and remove the old k8s/ folder.
5. **Delivery:** publish images to a container registry, deploy to a managed Kubernetes cluster, and use a proper secrets manager.

## Author

[@tvero1011](https://github.com/tvero1011)

# k8s-health-monitor

A small Flask service that checks whether websites are up, and runs on Kubernetes.

It checks each target in the background every few seconds, then reports the results over HTTP. The project is packaged with Docker and Helm, and a GitHub Actions pipeline proves on every push that it deploys.

## What it does

- `GET /status` returns the latest result for each monitored website
- `GET /healthz` tells Kubernetes the app is alive (liveness)
- `GET /ready` tells Kubernetes the app has finished its first round of checks (readiness)
- `GET /metrics` returns counts of targets up and down

## Architecture

```text
 git push
    |
    v
GitHub Actions --> builds image --> throwaway kind cluster --> helm install --wait
                                                                  (proves the chart deploys)

Local: Docker image --> kind cluster --> Helm release
                                          |-- Deployment (2-5 Pods, scaled by HPA)
                                          |-- Service (stable address)
                                          |-- ConfigMap (targets, interval)
                                          `-- Secret (API_TOKEN)
```

- A background thread checks every target each `CHECK_INTERVAL_SECONDS`
- Liveness and readiness probes call `/healthz` and `/ready`
- An HPA scales on CPU (target 50%, 2 to 5 replicas)

## Tech stack

Python and Flask, Docker, Kubernetes (kind), Helm, GitHub Actions.

## Project structure

```text
app.py              the Flask app
Dockerfile          builds the image
requirements.txt    pinned dependencies
helm-chart/         Helm chart (Deployment, Service, ConfigMap, Secret, HPA)
k8s/                plain Kubernetes manifests (kept as reference)
.github/workflows/  CI pipeline
```

## Configuration

The app reads these environment variables and exits with code 1 if one is missing:

| Variable | Meaning |
|---|---|
| `MONITOR_TARGETS` | comma-separated list of URLs to check |
| `CHECK_INTERVAL_SECONDS` | seconds between check rounds |
| `API_TOKEN` | a private token (never printed or logged) |

In Kubernetes, the first two come from a ConfigMap and the third from a Secret.

## Run it

### 1. Locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MONITOR_TARGETS="https://example.com,https://github.com"
export CHECK_INTERVAL_SECONDS=10
export API_TOKEN=change-me
python app.py
curl http://localhost:5000/status
```

### 2. With Docker

```bash
docker build -t health-monitor:latest .
docker run --rm -p 5000:5000 \
  -e MONITOR_TARGETS="https://example.com,https://github.com" \
  -e CHECK_INTERVAL_SECONDS=10 \
  -e API_TOKEN=change-me \
  health-monitor:latest
```

### 3. On kind with Helm

```bash
kind create cluster --name health-cluster
docker build -t health-monitor:latest .
kind load docker-image health-monitor:latest --name health-cluster
helm install health-monitor ./helm-chart
kubectl port-forward service/health-monitor-service 8080:80
curl http://localhost:8080/status
```

Change the number of replicas without editing files:

```bash
helm upgrade health-monitor ./helm-chart --set replicaCount=4
helm rollback health-monitor 1
```

### 4. Autoscaling (optional)

The HPA needs metrics-server. On kind it needs one patch, because kind uses self-signed certificates. This is for local learning only.

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl patch deployment metrics-server -n kube-system --type='json' \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
kubectl get hpa
```

## CI pipeline

On every push to `main`, GitHub Actions builds the image, creates a throwaway kind cluster, loads the image, and runs `helm upgrade --install --wait`. It does not deploy to a real cluster. A green run proves the chart installs and the Pods become ready.

## Lessons learned

- A Pod can be `Running` but not `Ready`. A failing readiness probe removes it from the Service without restarting it.
- An image is a frozen copy of the code. After a change: build, load into kind, restart.
- Fail fast: a missing setting stops the app at startup, which is easier to debug than a silent wrong run.
- I broke the Helm chart on purpose, read the error in the Actions log, and fixed it.
- A Kubernetes Secret is base64, not encryption. Only a placeholder is committed to Git.
- The HPA needs a CPU request on the Pods. Without one it shows `<unknown>`.
- Helm keeps its revision history inside the cluster, which is what makes rollback possible.

## Known limitations

- The Flask development server is used. A production setup would use gunicorn with a single worker, because of the background thread.
- The container runs as root.
- The image uses the `latest` tag instead of versioned tags.
- `kind load` is used instead of a container registry.
- The Secret holds a placeholder. Real projects use a secret manager.

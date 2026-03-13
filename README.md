# FluxCD Kubernetes Integration for Home Assistant

A custom Home Assistant integration that monitors **FluxCD resources in Kubernetes** using **kubernetes-asyncio**. It exposes FluxCD resource status as Home Assistant sensor entities.

## Features

- **Async-first design** using `kubernetes-asyncio`
- **DataUpdateCoordinator** for efficient polling
- **Config flow** for easy UI-based setup
- Monitors **GitRepository**, **Kustomization**, **HelmRelease**, and **HelmRepository** resources
- Supports **in-cluster** and **kubeconfig** authentication
- **Namespace scoping** — monitor a single namespace or all namespaces
- **Label selector** filtering for targeted monitoring
- **Configurable scan interval**

## Monitored Resources

| Resource | API Group / Version | Purpose |
|---|---|---|
| GitRepository | `source.toolkit.fluxcd.io/v1` | Source sync status, last fetched commit |
| Kustomization | `kustomize.toolkit.fluxcd.io/v1` | Deployment reconcile status, last applied revision |
| HelmRelease | `helm.toolkit.fluxcd.io/v2` | Helm chart status, version |
| HelmRepository | `source.toolkit.fluxcd.io/v1` | Helm repo sync status |

## Sensor States

Each FluxCD resource is represented as a sensor entity with one of these states:

- `ready` — The resource is reconciled and healthy
- `not_ready` — The resource has a failing condition
- `unknown` — The resource status cannot be determined

## Entity Attributes

### Common Attributes (all resource types)

- `kind` — Resource type (GitRepository, Kustomization, etc.)
- `namespace` — Kubernetes namespace
- `resource_name` — Resource name
- `suspend` — Whether the resource is suspended
- `message` — Status message from the Ready condition
- `reason` — Reason from the Ready condition
- `last_reconcile_time` — Timestamp of the last reconciliation
- `observed_generation` — Last observed generation
- `conditions` — Full list of status conditions

### GitRepository Attributes

- `url` — Git repository URL
- `branch` / `tag` / `semver` / `commit` — Git reference details
- `artifact_revision` — Last fetched artifact revision
- `interval` — Sync interval

### Kustomization Attributes

- `path` — Kustomize path
- `prune` — Whether pruning is enabled
- `interval` — Reconciliation interval
- `last_applied_revision` — Last successfully applied revision
- `source_ref_kind` / `source_ref_name` — Source reference details

### HelmRelease Attributes

- `chart_name` / `chart_version` — Helm chart details
- `source_ref_kind` / `source_ref_name` — Chart source reference
- `interval` — Reconciliation interval
- `last_applied_revision` — Last applied chart revision
- `last_attempted_revision` — Last attempted chart revision

### HelmRepository Attributes

- `url` — Helm repository URL
- `repo_type` — Repository type
- `interval` — Sync interval
- `artifact_revision` — Last fetched artifact revision

## Installation

### HACS (Recommended)

1. Add this repository as a custom repository in HACS
2. Install the "FluxCD Kubernetes" integration
3. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/fluxcd_k8s` directory to your Home Assistant `custom_components` directory:
   ```bash
   cp -r custom_components/fluxcd_k8s /path/to/homeassistant/custom_components/
   ```
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services**
2. Click **+ ADD INTEGRATION**
3. Search for **FluxCD Kubernetes**
4. Configure the following:
   - **Access Mode**: Select `In-Cluster` if Home Assistant runs inside Kubernetes, or `Kubeconfig File` for external access
   - **Kubeconfig Path**: Path to your kubeconfig file (only needed for Kubeconfig mode; leave empty for the default `~/.kube/config`)
   - **Namespace**: Kubernetes namespace to monitor (leave empty for all namespaces)
   - **Scan Interval**: How often to poll FluxCD resources (in seconds, minimum 10, default 60)
   - **Label Selector**: Optional Kubernetes label selector to filter resources

## Kubernetes RBAC

The integration requires read-only access to FluxCD custom resources. Apply the included RBAC manifest:

```bash
kubectl apply -f rbac.yaml
```

This creates a `ClusterRole` with `get`, `list`, and `watch` permissions on:
- `gitrepositories` and `helmrepositories` (`source.toolkit.fluxcd.io`)
- `kustomizations` (`kustomize.toolkit.fluxcd.io`)
- `helmreleases` (`helm.toolkit.fluxcd.io`)

Edit the `ClusterRoleBinding` subject to match your Home Assistant service account.

## Project Structure

```
custom_components/fluxcd_k8s/
├── __init__.py        # Integration setup and teardown
├── manifest.json      # Integration metadata and requirements
├── const.py           # Constants and FluxCD CRD definitions
├── config_flow.py     # Configuration UI flow
├── coordinator.py     # DataUpdateCoordinator for polling
├── api.py             # Kubernetes API client using kubernetes-asyncio
├── models.py          # Data models and parsing helpers
├── sensor.py          # Sensor entity platform
├── strings.json       # UI strings
└── translations/
    └── en.json        # English translations
```

## How It Works

### Querying FluxCD Resources

The integration uses `kubernetes_asyncio.client.CustomObjectsApi` to explicitly fetch each FluxCD resource kind:

- **Namespaced queries**: `list_namespaced_custom_object(group, version, namespace, plural)`
- **Cluster-wide queries**: `list_cluster_custom_object(group, version, plural)`

### Status Normalization

FluxCD resources store status in `status.conditions` as a list of condition objects. The integration:

1. Parses all conditions from the resource status
2. Finds the `Ready` condition
3. Maps `status: "True"` → `ready`, `status: "False"` → `not_ready`, otherwise → `unknown`
4. Extracts kind-specific attributes from `.spec` and `.status`

### Polling

A single `DataUpdateCoordinator` polls all four resource kinds on the configured interval. Results are organized by kind for efficient entity lookup.

## Requirements

- Home Assistant 2024.1.0+
- Python 3.11+
- `kubernetes-asyncio` (installed automatically)
- Kubernetes cluster with FluxCD installed
- Appropriate RBAC permissions (see above)

## License

This project is provided as-is for monitoring FluxCD resources in Home Assistant.
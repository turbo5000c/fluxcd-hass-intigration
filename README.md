# FluxCD Kubernetes Integration for Home Assistant

A custom Home Assistant integration that monitors **FluxCD resources in Kubernetes** using **kubernetes-asyncio**. It exposes FluxCD resource status as Home Assistant sensor entities, grouped by **category** (Sources / Deployments) and **resource type**.

## Features

- **Async-first design** using `kubernetes-asyncio`
- **DataUpdateCoordinator** for efficient polling
- **Config flow** for easy UI-based setup
- **Category-based grouping** — resources are organized into *Sources* and *Deployments*
- Monitors **12 FluxCD resource types** across both categories
- Supports **in-cluster** and **kubeconfig** authentication
- **Namespace scoping** — monitor a single namespace or all namespaces
- **Label selector** filtering for targeted monitoring
- **Configurable scan interval**
- **Grouped and per-resource-type fetch functions** for flexible querying

## Resource Categories

### Sources

| Resource | API Group / Version | Purpose |
|---|---|---|
| ArtifactGenerator | `source.toolkit.fluxcd.io/v1beta2` | Generate artifacts from various inputs |
| Bucket | `source.toolkit.fluxcd.io/v1` | S3-compatible bucket source |
| ExternalArtifact | `source.toolkit.fluxcd.io/v1beta2` | External artifact reference |
| GitRepository | `source.toolkit.fluxcd.io/v1` | Source sync status, last fetched commit |
| HelmChart | `source.toolkit.fluxcd.io/v1` | Helm chart source tracking |
| HelmRepository | `source.toolkit.fluxcd.io/v1` | Helm repo sync status |
| OCIRepository | `source.toolkit.fluxcd.io/v1beta2` | OCI artifact source |
| ResourceSetInputProvider | `fluxcd.controlplane.io/v1` | Input provider for ResourceSets |

### Deployments

| Resource | API Group / Version | Purpose |
|---|---|---|
| FluxInstance | `fluxcd.controlplane.io/v1` | Flux operator instance status |
| HelmRelease | `helm.toolkit.fluxcd.io/v2` | Helm chart deployment status |
| Kustomization | `kustomize.toolkit.fluxcd.io/v1` | Deployment reconcile status, last applied revision |
| ResourceSet | `fluxcd.controlplane.io/v1` | Templated resource deployment |

## Sensor States

Each FluxCD resource is represented as a sensor entity with one of these states:

- `ready` — The resource is reconciled and healthy
- `not_ready` — The resource has a failing condition
- `unknown` — The resource status cannot be determined

## Entity Attributes

### Common Attributes (all resource types)

- `category` — Resource category (Sources, Deployments)
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

### HelmChart Attributes

- `chart` — Chart name
- `version` — Version constraint
- `source_ref_kind` / `source_ref_name` — Source reference
- `artifact_revision` — Fetched chart revision

### Bucket Attributes

- `bucket_name` — S3 bucket name
- `endpoint` — Bucket endpoint URL
- `provider` — Cloud provider (aws, gcp, generic)
- `region` — Bucket region
- `artifact_revision` — Fetched artifact revision

### OCIRepository Attributes

- `url` — OCI repository URL
- `tag` / `semver` / `digest` — OCI reference details
- `artifact_revision` — Fetched artifact revision

### FluxInstance Attributes

- `distribution_version` — Flux distribution version
- `distribution_registry` — Flux distribution registry
- `cluster_domain` — Cluster domain
- `last_applied_revision` / `last_attempted_revision` — Revision info

### ResourceSet Attributes

- `input_ref_kind` / `input_ref_name` — Input reference details
- `interval` — Reconciliation interval

### ArtifactGenerator Attributes

- `interval` — Generation interval
- `artifact_revision` — Generated artifact revision

### ExternalArtifact Attributes

- `url` — External artifact URL
- `interval` — Fetch interval
- `artifact_revision` — Fetched artifact revision

### ResourceSetInputProvider Attributes

- `resource_ref_kind` / `resource_ref_name` / `resource_ref_namespace` — Resource reference details

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
- `gitrepositories`, `helmrepositories`, `helmcharts`, `buckets`, `ocirepositories`, `artifactgenerators`, `externalartifacts` (`source.toolkit.fluxcd.io`)
- `kustomizations` (`kustomize.toolkit.fluxcd.io`)
- `helmreleases` (`helm.toolkit.fluxcd.io`)
- `fluxinstances`, `resourcesets`, `resourcesetinputproviders` (`fluxcd.controlplane.io`)

Edit the `ClusterRoleBinding` subject to match your Home Assistant service account.

## Project Structure

```
custom_components/fluxcd_k8s/
├── __init__.py        # Integration setup and teardown
├── manifest.json      # Integration metadata and requirements
├── const.py           # Constants, CRD definitions, and category groupings
├── config_flow.py     # Configuration UI flow
├── coordinator.py     # DataUpdateCoordinator for polling
├── api.py             # Kubernetes API client with grouped/per-type fetch functions
├── models.py          # Data models and kind-specific parsing helpers
├── sensor.py          # Sensor entity platform
├── strings.json       # UI strings
└── translations/
    └── en.json        # English translations
```

## How It Works

### Resource Grouping by Category

Resources are organized into two categories:

- **Sources** — Resources that define where configuration comes from (GitRepository, HelmRepository, HelmChart, Bucket, OCIRepository, ArtifactGenerator, ExternalArtifact, ResourceSetInputProvider)
- **Deployments** — Resources that apply configuration to the cluster (FluxInstance, HelmRelease, Kustomization, ResourceSet)

Each resource carries its `category` as metadata, which is exposed as a sensor attribute.

### Querying FluxCD Resources

The integration uses `kubernetes_asyncio.client.CustomObjectsApi` to explicitly fetch each FluxCD resource kind:

- **Namespaced queries**: `list_namespaced_custom_object(group, version, namespace, plural)`
- **Cluster-wide queries**: `list_cluster_custom_object(group, version, plural)`

**Grouped fetch functions:**
- `async_fetch_sources()` — Fetches all Source category resources
- `async_fetch_deployments()` — Fetches all Deployment category resources

**Per-resource-type fetch functions:**
- `async_fetch_gitrepositories()`, `async_fetch_helmrepositories()`, `async_fetch_helmcharts()`, `async_fetch_buckets()`, `async_fetch_ocirepositories()`, `async_fetch_artifactgenerators()`, `async_fetch_externalartifacts()`, `async_fetch_resourcesetinputproviders()`
- `async_fetch_kustomizations()`, `async_fetch_helmreleases()`, `async_fetch_fluxinstances()`, `async_fetch_resourcesets()`

### Entity Organization

Each FluxCD resource becomes a Home Assistant sensor entity. Entities are grouped by:

1. **Category** (Sources / Deployments)
2. **Resource type** (GitRepository, Kustomization, etc.)

Example entity names:
- `FluxCD GitRepository flux-system/my-repo` (Sources / GitRepository)
- `FluxCD Kustomization flux-system/my-app` (Deployments / Kustomization)
- `FluxCD FluxInstance flux-system/flux` (Deployments / FluxInstance)

### Status Normalization

FluxCD resources store status in `status.conditions` as a list of condition objects. The integration:

1. Parses all conditions from the resource status
2. Finds the `Ready` condition
3. Maps `status: "True"` → `ready`, `status: "False"` → `not_ready`, otherwise → `unknown`
4. Extracts kind-specific attributes from `.spec` and `.status`

### Polling

A single `DataUpdateCoordinator` polls all resource kinds on the configured interval. Results are organized by kind for efficient entity lookup.

## Requirements

- Home Assistant 2024.9.1+
- Python 3.11+
- `kubernetes-asyncio` (installed automatically)
- Kubernetes cluster with FluxCD installed
- Appropriate RBAC permissions (see above)

## License

This project is provided as-is for monitoring FluxCD resources in Home Assistant.
"""Constants for the FluxCD Kubernetes integration."""

from __future__ import annotations

# Domain name for this integration
DOMAIN = "fluxcd_k8s"

# Configuration keys
CONF_ACCESS_MODE = "access_mode"
CONF_KUBECONFIG_PATH = "kubeconfig_path"
CONF_NAMESPACE = "namespace"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_LABEL_SELECTOR = "label_selector"

# Access modes
ACCESS_MODE_IN_CLUSTER = "in_cluster"
ACCESS_MODE_KUBECONFIG = "kubeconfig"

# Default values
DEFAULT_NAME = "FluxCD Kubernetes"
DEFAULT_SCAN_INTERVAL = 60  # seconds
DEFAULT_NAMESPACE = ""  # empty means all namespaces

# FluxCD CRD definitions
# Each entry: (group, version, plural)
FLUX_GITREPOSITORY = {
    "group": "source.toolkit.fluxcd.io",
    "version": "v1",
    "plural": "gitrepositories",
    "kind": "GitRepository",
}

FLUX_KUSTOMIZATION = {
    "group": "kustomize.toolkit.fluxcd.io",
    "version": "v1",
    "plural": "kustomizations",
    "kind": "Kustomization",
}

FLUX_HELMRELEASE = {
    "group": "helm.toolkit.fluxcd.io",
    "version": "v2",
    "plural": "helmreleases",
    "kind": "HelmRelease",
}

FLUX_HELMREPOSITORY = {
    "group": "source.toolkit.fluxcd.io",
    "version": "v1",
    "plural": "helmrepositories",
    "kind": "HelmRepository",
}

FLUX_RESOURCES = [
    FLUX_GITREPOSITORY,
    FLUX_KUSTOMIZATION,
    FLUX_HELMRELEASE,
    FLUX_HELMREPOSITORY,
]

# Sensor states
STATE_READY = "ready"
STATE_NOT_READY = "not_ready"
STATE_UNKNOWN = "unknown"

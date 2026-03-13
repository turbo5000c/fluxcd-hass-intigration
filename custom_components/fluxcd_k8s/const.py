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

# Categories
CATEGORY_SOURCES = "Sources"
CATEGORY_DEPLOYMENTS = "Deployments"

# ---------------------------------------------------------------------------
# FluxCD CRD definitions
# Each entry: group, version, plural, kind, category
# ---------------------------------------------------------------------------

# Sources (source.toolkit.fluxcd.io)
FLUX_GITREPOSITORY = {
    "group": "source.toolkit.fluxcd.io",
    "version": "v1",
    "plural": "gitrepositories",
    "kind": "GitRepository",
    "category": CATEGORY_SOURCES,
}

FLUX_HELMREPOSITORY = {
    "group": "source.toolkit.fluxcd.io",
    "version": "v1",
    "plural": "helmrepositories",
    "kind": "HelmRepository",
    "category": CATEGORY_SOURCES,
}

FLUX_HELMCHART = {
    "group": "source.toolkit.fluxcd.io",
    "version": "v1",
    "plural": "helmcharts",
    "kind": "HelmChart",
    "category": CATEGORY_SOURCES,
}

FLUX_BUCKET = {
    "group": "source.toolkit.fluxcd.io",
    "version": "v1",
    "plural": "buckets",
    "kind": "Bucket",
    "category": CATEGORY_SOURCES,
}

FLUX_OCIREPOSITORY = {
    "group": "source.toolkit.fluxcd.io",
    "version": "v1beta2",
    "plural": "ocirepositories",
    "kind": "OCIRepository",
    "category": CATEGORY_SOURCES,
}

FLUX_ARTIFACTGENERATOR = {
    "group": "source.toolkit.fluxcd.io",
    "version": "v1beta2",
    "plural": "artifactgenerators",
    "kind": "ArtifactGenerator",
    "category": CATEGORY_SOURCES,
}

FLUX_EXTERNALARTIFACT = {
    "group": "source.toolkit.fluxcd.io",
    "version": "v1beta2",
    "plural": "externalartifacts",
    "kind": "ExternalArtifact",
    "category": CATEGORY_SOURCES,
}

FLUX_RESOURCESETINPUTPROVIDER = {
    "group": "fluxcd.controlplane.io",
    "version": "v1",
    "plural": "resourcesetinputproviders",
    "kind": "ResourceSetInputProvider",
    "category": CATEGORY_SOURCES,
}

# Deployments
FLUX_KUSTOMIZATION = {
    "group": "kustomize.toolkit.fluxcd.io",
    "version": "v1",
    "plural": "kustomizations",
    "kind": "Kustomization",
    "category": CATEGORY_DEPLOYMENTS,
}

FLUX_HELMRELEASE = {
    "group": "helm.toolkit.fluxcd.io",
    "version": "v2",
    "plural": "helmreleases",
    "kind": "HelmRelease",
    "category": CATEGORY_DEPLOYMENTS,
}

FLUX_FLUXINSTANCE = {
    "group": "fluxcd.controlplane.io",
    "version": "v1",
    "plural": "fluxinstances",
    "kind": "FluxInstance",
    "category": CATEGORY_DEPLOYMENTS,
}

FLUX_RESOURCESET = {
    "group": "fluxcd.controlplane.io",
    "version": "v1",
    "plural": "resourcesets",
    "kind": "ResourceSet",
    "category": CATEGORY_DEPLOYMENTS,
}

# Grouped lists
FLUX_SOURCES = [
    FLUX_ARTIFACTGENERATOR,
    FLUX_BUCKET,
    FLUX_EXTERNALARTIFACT,
    FLUX_GITREPOSITORY,
    FLUX_HELMCHART,
    FLUX_HELMREPOSITORY,
    FLUX_OCIREPOSITORY,
    FLUX_RESOURCESETINPUTPROVIDER,
]

FLUX_DEPLOYMENTS = [
    FLUX_FLUXINSTANCE,
    FLUX_HELMRELEASE,
    FLUX_KUSTOMIZATION,
    FLUX_RESOURCESET,
]

# All resources
FLUX_RESOURCES = FLUX_SOURCES + FLUX_DEPLOYMENTS

# Sensor states
STATE_READY = "ready"
STATE_NOT_READY = "not_ready"
STATE_UNKNOWN = "unknown"

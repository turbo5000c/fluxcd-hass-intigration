"""Data models for FluxCD Kubernetes resources."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .const import (
    STATE_NOT_READY,
    STATE_PROGRESSING,
    STATE_READY,
    STATE_SUSPENDED,
    STATE_UNKNOWN,
)


@dataclass
class FluxCondition:
    """Represents a single Flux status condition."""

    type: str
    status: str
    reason: str
    message: str
    last_transition_time: str


@dataclass
class FluxResource:
    """Base model for a FluxCD resource.

    Contains the common fields extracted from metadata, spec, and status
    of FluxCD custom resources.
    """

    kind: str
    name: str
    namespace: str
    category: str
    ready_status: str  # "ready", "not_ready", "progressing", "suspended", "unknown"
    message: str
    reason: str
    reconcile_time: str
    suspend: bool
    observed_generation: int | None
    conditions: list[FluxCondition] = field(default_factory=list)
    extra_attributes: dict[str, Any] = field(default_factory=dict)
    diagnostic_attributes: dict[str, Any] = field(default_factory=dict)


def parse_conditions(status: dict[str, Any]) -> list[FluxCondition]:
    """Parse the conditions list from a Flux resource status.

    Flux resources store conditions in status.conditions as a list of
    objects with type, status, reason, message, and lastTransitionTime.
    """
    conditions: list[FluxCondition] = []
    for cond in status.get("conditions", []):
        conditions.append(
            FluxCondition(
                type=cond.get("type", ""),
                status=cond.get("status", ""),
                reason=cond.get("reason", ""),
                message=cond.get("message", ""),
                last_transition_time=cond.get("lastTransitionTime", ""),
            )
        )
    return conditions


def get_ready_condition(
    conditions: list[FluxCondition],
) -> FluxCondition | None:
    """Find the 'Ready' condition from a list of Flux conditions."""
    for cond in conditions:
        if cond.type == "Ready":
            return cond
    return None


def determine_ready_status(conditions: list[FluxCondition]) -> str:
    """Determine the overall ready status from conditions.

    Returns 'ready', 'not_ready', 'progressing', or 'unknown'.
    A resource is considered progressing when it has a Reconciling
    condition with status 'True' and is not yet ready.
    """
    ready = get_ready_condition(conditions)
    if ready is not None and ready.status == "True":
        return STATE_READY

    # Check for an active Reconciling condition before reporting not_ready/unknown
    for cond in conditions:
        if cond.type == "Reconciling" and cond.status == "True":
            return STATE_PROGRESSING

    if ready is not None and ready.status == "False":
        return STATE_NOT_READY

    return STATE_UNKNOWN


def _get_condition_flag(conditions: list[FluxCondition], cond_type: str) -> bool:
    """Return True when a named condition has status 'True'."""
    for cond in conditions:
        if cond.type == cond_type:
            return cond.status == "True"
    return False


def _format_source_ref(kind: str, name: str, namespace: str = "") -> str:
    """Format a source reference as 'Kind/name' or 'Kind/namespace/name'."""
    if namespace:
        return f"{kind}/{namespace}/{name}"
    return f"{kind}/{name}"


def parse_flux_resource(
    raw: dict[str, Any], kind: str, category: str = ""
) -> FluxResource:
    """Parse a raw Kubernetes custom object into a FluxResource.

    Extracts common fields from metadata, spec, and status, then
    delegates to kind-specific parsers for extra attributes.
    """
    metadata = raw.get("metadata", {})
    spec = raw.get("spec", {})
    status = raw.get("status", {})

    conditions = parse_conditions(status)
    ready_status = determine_ready_status(conditions)
    ready_cond = get_ready_condition(conditions)

    # Suspended resources override the derived ready status
    if spec.get("suspend", False):
        ready_status = STATE_SUSPENDED

    resource = FluxResource(
        kind=kind,
        name=metadata.get("name", ""),
        namespace=metadata.get("namespace", ""),
        category=category,
        ready_status=ready_status,
        message=ready_cond.message if ready_cond else "",
        reason=ready_cond.reason if ready_cond else "",
        reconcile_time=ready_cond.last_transition_time if ready_cond else "",
        suspend=spec.get("suspend", False),
        observed_generation=status.get("observedGeneration"),
        conditions=conditions,
    )

    # Parse kind-specific primary and diagnostic attributes
    parser = _KIND_ATTR_PARSERS.get(kind)
    if parser is not None:
        primary, diagnostic = parser(spec, status)
        resource.extra_attributes = primary
        resource.diagnostic_attributes = diagnostic

    # Compute and store a human-readable summary
    summary = _compute_summary(resource)
    if summary:
        resource.extra_attributes["summary"] = summary

    return resource


def _compute_summary(resource: FluxResource) -> str:
    """Compute a short human-readable summary for the resource."""
    attrs = resource.extra_attributes
    kind = resource.kind
    name = resource.name

    if kind == "HelmChart":
        chart = attrs.get("chart", name)
        version = attrs.get("version", "")
        source = attrs.get("source", "")
        parts = [p for p in [chart, version] if p]
        base = " ".join(parts)
        return f"{base} from {source}" if source else base

    if kind == "HelmRelease":
        chart = attrs.get("chart_name", name)
        version = attrs.get("chart_version", "")
        source = attrs.get("source", "")
        parts = [p for p in [chart, version] if p]
        base = " ".join(parts)
        return f"{base} from {source}" if source else base

    if kind in ("GitRepository", "OCIRepository", "HelmRepository", "ExternalArtifact"):
        url = attrs.get("url", "")
        ref = (
            attrs.get("branch")
            or attrs.get("tag")
            or attrs.get("semver")
            or attrs.get("commit")
            or ""
        )
        base = f"{name} {ref}".strip() if ref else name
        return f"{base} from {url}" if url else base

    if kind == "Bucket":
        bucket = attrs.get("bucket_name", name)
        endpoint = attrs.get("endpoint", "")
        return f"{bucket} from {endpoint}" if endpoint else bucket

    if kind == "Kustomization":
        path = attrs.get("path", "")
        source = attrs.get("source", "")
        base = f"{name}{' ' + path if path else ''}"
        return f"{base} from {source}" if source else base

    if kind == "FluxInstance":
        version = attrs.get("distribution_version", "")
        return f"FluxCD {version}".strip() if version else "FluxCD"

    if kind in ("ResourceSet", "ResourceSetInputProvider"):
        source = attrs.get("source", "")
        return f"{name} from {source}" if source else name

    if kind == "ArtifactGenerator":
        return name

    return ""


# ---------------------------------------------------------------------------
# Kind-specific attribute parsers
# Each returns (primary_attrs, diagnostic_attrs).
# ---------------------------------------------------------------------------


def _parse_git_repository_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract GitRepository-specific attributes from spec and status."""
    artifact = status.get("artifact", {})
    ref = spec.get("ref", {})
    primary: dict[str, Any] = {
        "url": spec.get("url", ""),
        "branch": ref.get("branch", ""),
        "tag": ref.get("tag", ""),
        "semver": ref.get("semver", ""),
        "commit": ref.get("commit", ""),
    }
    diagnostic: dict[str, Any] = {
        "artifact_revision": artifact.get("revision", ""),
        "artifact_checksum": artifact.get("digest", ""),
        "interval": spec.get("interval", ""),
    }
    return primary, diagnostic


def _parse_kustomization_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract Kustomization-specific attributes from spec and status."""
    source_ref = spec.get("sourceRef", {})
    source_kind = source_ref.get("kind", "")
    source_name = source_ref.get("name", "")
    source_namespace = source_ref.get("namespace", "")
    primary: dict[str, Any] = {
        "path": spec.get("path", ""),
        "prune": spec.get("prune", False),
        "source": _format_source_ref(source_kind, source_name, source_namespace)
        if source_kind
        else "",
    }
    diagnostic: dict[str, Any] = {
        "interval": spec.get("interval", ""),
        "last_applied_revision": status.get("lastAppliedRevision", ""),
        "last_attempted_revision": status.get("lastAttemptedRevision", ""),
    }
    return primary, diagnostic


def _parse_helm_release_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract HelmRelease-specific attributes from spec and status."""
    chart_spec = spec.get("chart", {}).get("spec", {})
    source_ref = chart_spec.get("sourceRef", {})
    source_kind = source_ref.get("kind", "")
    source_name = source_ref.get("name", "")
    primary: dict[str, Any] = {
        "chart_name": chart_spec.get("chart", ""),
        "chart_version": chart_spec.get("version", ""),
        "source": _format_source_ref(source_kind, source_name) if source_kind else "",
    }
    diagnostic: dict[str, Any] = {
        "interval": spec.get("interval", ""),
        "last_applied_revision": status.get("lastAppliedRevision", ""),
        "last_attempted_revision": status.get("lastAttemptedRevision", ""),
        "last_release_revision": status.get("lastReleaseRevision"),
    }
    return primary, diagnostic


def _parse_helm_repository_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract HelmRepository-specific attributes from spec and status."""
    artifact = status.get("artifact", {})
    primary: dict[str, Any] = {
        "url": spec.get("url", ""),
        "repo_type": spec.get("type", "default"),
    }
    diagnostic: dict[str, Any] = {
        "interval": spec.get("interval", ""),
        "artifact_revision": artifact.get("revision", ""),
        "artifact_checksum": artifact.get("digest", ""),
    }
    return primary, diagnostic


def _parse_helm_chart_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract HelmChart-specific attributes from spec and status."""
    artifact = status.get("artifact", {})
    source_ref = spec.get("sourceRef", {})
    source_kind = source_ref.get("kind", "")
    source_name = source_ref.get("name", "")
    source_namespace = source_ref.get("namespace", "")
    primary: dict[str, Any] = {
        "chart": spec.get("chart", ""),
        "version": spec.get("version", ""),
        "source": _format_source_ref(source_kind, source_name, source_namespace)
        if source_kind
        else "",
    }
    diagnostic: dict[str, Any] = {
        "interval": spec.get("interval", ""),
        "artifact_revision": artifact.get("revision", ""),
        "artifact_checksum": artifact.get("digest", ""),
    }
    return primary, diagnostic


def _parse_bucket_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract Bucket-specific attributes from spec and status."""
    artifact = status.get("artifact", {})
    primary: dict[str, Any] = {
        "bucket_name": spec.get("bucketName", ""),
        "endpoint": spec.get("endpoint", ""),
        "provider": spec.get("provider", "generic"),
        "region": spec.get("region", ""),
        "prefix": spec.get("prefix", ""),
    }
    diagnostic: dict[str, Any] = {
        "interval": spec.get("interval", ""),
        "artifact_revision": artifact.get("revision", ""),
        "artifact_checksum": artifact.get("digest", ""),
    }
    return primary, diagnostic


def _parse_oci_repository_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract OCIRepository-specific attributes from spec and status."""
    artifact = status.get("artifact", {})
    ref = spec.get("ref", {})
    primary: dict[str, Any] = {
        "url": spec.get("url", ""),
        "tag": ref.get("tag", ""),
        "semver": ref.get("semver", ""),
        "digest": ref.get("digest", ""),
    }
    diagnostic: dict[str, Any] = {
        "interval": spec.get("interval", ""),
        "artifact_revision": artifact.get("revision", ""),
        "artifact_checksum": artifact.get("digest", ""),
    }
    return primary, diagnostic


def _parse_flux_instance_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract FluxInstance-specific attributes from spec and status."""
    distribution = spec.get("distribution", {})
    primary: dict[str, Any] = {
        "distribution_version": distribution.get("version", ""),
        "distribution_registry": distribution.get("registry", ""),
        "cluster_domain": spec.get("cluster", {}).get("domain", ""),
    }
    diagnostic: dict[str, Any] = {
        "last_applied_revision": status.get("lastAppliedRevision", ""),
        "last_attempted_revision": status.get("lastAttemptedRevision", ""),
    }
    return primary, diagnostic


def _parse_resource_set_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract ResourceSet-specific attributes from spec and status."""
    input_ref = spec.get("inputRef", {})
    input_kind = input_ref.get("kind", "")
    input_name = input_ref.get("name", "")
    primary: dict[str, Any] = {
        "source": _format_source_ref(input_kind, input_name) if input_kind else "",
    }
    diagnostic: dict[str, Any] = {
        "interval": spec.get("interval", ""),
    }
    return primary, diagnostic


def _parse_artifact_generator_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract ArtifactGenerator-specific attributes from spec and status."""
    artifact = status.get("artifact", {})
    primary: dict[str, Any] = {}
    diagnostic: dict[str, Any] = {
        "interval": spec.get("interval", ""),
        "artifact_revision": artifact.get("revision", ""),
        "artifact_checksum": artifact.get("digest", ""),
    }
    return primary, diagnostic


def _parse_external_artifact_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract ExternalArtifact-specific attributes from spec and status."""
    artifact = status.get("artifact", {})
    primary: dict[str, Any] = {
        "url": spec.get("url", ""),
    }
    diagnostic: dict[str, Any] = {
        "interval": spec.get("interval", ""),
        "artifact_revision": artifact.get("revision", ""),
        "artifact_checksum": artifact.get("digest", ""),
    }
    return primary, diagnostic


def _parse_resource_set_input_provider_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract ResourceSetInputProvider-specific attributes from spec and status."""
    resource_ref = spec.get("resourceRef", {})
    resource_kind = resource_ref.get("kind", "")
    resource_name = resource_ref.get("name", "")
    resource_namespace = resource_ref.get("namespace", "")
    primary: dict[str, Any] = {
        "source": _format_source_ref(
            resource_kind, resource_name, resource_namespace
        )
        if resource_kind
        else "",
    }
    diagnostic: dict[str, Any] = {}
    return primary, diagnostic


# Map resource kind to its attribute parser
_KIND_ATTR_PARSERS: dict[
    str,
    Callable[
        [dict[str, Any], dict[str, Any]],
        tuple[dict[str, Any], dict[str, Any]],
    ],
] = {
    "GitRepository": _parse_git_repository_attrs,
    "Kustomization": _parse_kustomization_attrs,
    "HelmRelease": _parse_helm_release_attrs,
    "HelmRepository": _parse_helm_repository_attrs,
    "HelmChart": _parse_helm_chart_attrs,
    "Bucket": _parse_bucket_attrs,
    "OCIRepository": _parse_oci_repository_attrs,
    "FluxInstance": _parse_flux_instance_attrs,
    "ResourceSet": _parse_resource_set_attrs,
    "ArtifactGenerator": _parse_artifact_generator_attrs,
    "ExternalArtifact": _parse_external_artifact_attrs,
    "ResourceSetInputProvider": _parse_resource_set_input_provider_attrs,
}

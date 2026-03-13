"""Data models for FluxCD Kubernetes resources."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import STATE_NOT_READY, STATE_READY, STATE_UNKNOWN


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
    ready_status: str  # "ready", "not_ready", "unknown"
    message: str
    reason: str
    last_reconcile_time: str
    suspend: bool
    observed_generation: int | None
    conditions: list[FluxCondition] = field(default_factory=list)
    extra_attributes: dict[str, Any] = field(default_factory=dict)


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

    Returns 'ready', 'not_ready', or 'unknown'.
    """
    ready = get_ready_condition(conditions)
    if ready is None:
        return STATE_UNKNOWN
    if ready.status == "True":
        return STATE_READY
    if ready.status == "False":
        return STATE_NOT_READY
    return STATE_UNKNOWN


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

    resource = FluxResource(
        kind=kind,
        name=metadata.get("name", ""),
        namespace=metadata.get("namespace", ""),
        category=category,
        ready_status=ready_status,
        message=ready_cond.message if ready_cond else "",
        reason=ready_cond.reason if ready_cond else "",
        last_reconcile_time=ready_cond.last_transition_time if ready_cond else "",
        suspend=spec.get("suspend", False),
        observed_generation=status.get("observedGeneration"),
        conditions=conditions,
    )

    # Parse kind-specific extra attributes
    parser = _KIND_ATTR_PARSERS.get(kind)
    if parser is not None:
        resource.extra_attributes = parser(spec, status)

    return resource


# ---------------------------------------------------------------------------
# Kind-specific attribute parsers
# ---------------------------------------------------------------------------


def _parse_git_repository_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> dict[str, Any]:
    """Extract GitRepository-specific attributes from spec and status."""
    artifact = status.get("artifact", {})
    ref = spec.get("ref", {})
    return {
        "url": spec.get("url", ""),
        "branch": ref.get("branch", ""),
        "tag": ref.get("tag", ""),
        "semver": ref.get("semver", ""),
        "commit": ref.get("commit", ""),
        "artifact_revision": artifact.get("revision", ""),
        "artifact_checksum": artifact.get("digest", ""),
        "interval": spec.get("interval", ""),
    }


def _parse_kustomization_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> dict[str, Any]:
    """Extract Kustomization-specific attributes from spec and status."""
    source_ref = spec.get("sourceRef", {})
    return {
        "path": spec.get("path", ""),
        "prune": spec.get("prune", False),
        "interval": spec.get("interval", ""),
        "last_applied_revision": status.get("lastAppliedRevision", ""),
        "last_attempted_revision": status.get("lastAttemptedRevision", ""),
        "source_ref_kind": source_ref.get("kind", ""),
        "source_ref_name": source_ref.get("name", ""),
        "source_ref_namespace": source_ref.get("namespace", ""),
    }


def _parse_helm_release_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> dict[str, Any]:
    """Extract HelmRelease-specific attributes from spec and status."""
    chart_spec = spec.get("chart", {}).get("spec", {})
    source_ref = chart_spec.get("sourceRef", {})
    return {
        "chart_name": chart_spec.get("chart", ""),
        "chart_version": chart_spec.get("version", ""),
        "source_ref_kind": source_ref.get("kind", ""),
        "source_ref_name": source_ref.get("name", ""),
        "interval": spec.get("interval", ""),
        "last_applied_revision": status.get("lastAppliedRevision", ""),
        "last_attempted_revision": status.get("lastAttemptedRevision", ""),
        "last_release_revision": status.get("lastReleaseRevision"),
    }


def _parse_helm_repository_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> dict[str, Any]:
    """Extract HelmRepository-specific attributes from spec and status."""
    artifact = status.get("artifact", {})
    return {
        "url": spec.get("url", ""),
        "repo_type": spec.get("type", "default"),
        "interval": spec.get("interval", ""),
        "artifact_revision": artifact.get("revision", ""),
        "artifact_checksum": artifact.get("digest", ""),
    }


def _parse_helm_chart_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> dict[str, Any]:
    """Extract HelmChart-specific attributes from spec and status."""
    artifact = status.get("artifact", {})
    source_ref = spec.get("sourceRef", {})
    return {
        "chart": spec.get("chart", ""),
        "version": spec.get("version", ""),
        "source_ref_kind": source_ref.get("kind", ""),
        "source_ref_name": source_ref.get("name", ""),
        "source_ref_namespace": source_ref.get("namespace", ""),
        "interval": spec.get("interval", ""),
        "artifact_revision": artifact.get("revision", ""),
        "artifact_checksum": artifact.get("digest", ""),
    }


def _parse_bucket_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> dict[str, Any]:
    """Extract Bucket-specific attributes from spec and status."""
    artifact = status.get("artifact", {})
    return {
        "bucket_name": spec.get("bucketName", ""),
        "endpoint": spec.get("endpoint", ""),
        "provider": spec.get("provider", "generic"),
        "region": spec.get("region", ""),
        "prefix": spec.get("prefix", ""),
        "interval": spec.get("interval", ""),
        "artifact_revision": artifact.get("revision", ""),
        "artifact_checksum": artifact.get("digest", ""),
    }


def _parse_oci_repository_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> dict[str, Any]:
    """Extract OCIRepository-specific attributes from spec and status."""
    artifact = status.get("artifact", {})
    ref = spec.get("ref", {})
    return {
        "url": spec.get("url", ""),
        "tag": ref.get("tag", ""),
        "semver": ref.get("semver", ""),
        "digest": ref.get("digest", ""),
        "interval": spec.get("interval", ""),
        "artifact_revision": artifact.get("revision", ""),
        "artifact_checksum": artifact.get("digest", ""),
    }


def _parse_flux_instance_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> dict[str, Any]:
    """Extract FluxInstance-specific attributes from spec and status."""
    distribution = spec.get("distribution", {})
    return {
        "distribution_version": distribution.get("version", ""),
        "distribution_registry": distribution.get("registry", ""),
        "cluster_domain": spec.get("cluster", {}).get("domain", ""),
        "last_applied_revision": status.get("lastAppliedRevision", ""),
        "last_attempted_revision": status.get("lastAttemptedRevision", ""),
    }


def _parse_resource_set_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> dict[str, Any]:
    """Extract ResourceSet-specific attributes from spec and status."""
    return {
        "input_ref_kind": spec.get("inputRef", {}).get("kind", ""),
        "input_ref_name": spec.get("inputRef", {}).get("name", ""),
        "interval": spec.get("interval", ""),
    }


def _parse_artifact_generator_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> dict[str, Any]:
    """Extract ArtifactGenerator-specific attributes from spec and status."""
    artifact = status.get("artifact", {})
    return {
        "interval": spec.get("interval", ""),
        "artifact_revision": artifact.get("revision", ""),
        "artifact_checksum": artifact.get("digest", ""),
    }


def _parse_external_artifact_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> dict[str, Any]:
    """Extract ExternalArtifact-specific attributes from spec and status."""
    artifact = status.get("artifact", {})
    return {
        "url": spec.get("url", ""),
        "interval": spec.get("interval", ""),
        "artifact_revision": artifact.get("revision", ""),
        "artifact_checksum": artifact.get("digest", ""),
    }


def _parse_resource_set_input_provider_attrs(
    spec: dict[str, Any], status: dict[str, Any]
) -> dict[str, Any]:
    """Extract ResourceSetInputProvider-specific attributes from spec and status."""
    return {
        "resource_ref_kind": spec.get("resourceRef", {}).get("kind", ""),
        "resource_ref_name": spec.get("resourceRef", {}).get("name", ""),
        "resource_ref_namespace": spec.get("resourceRef", {}).get("namespace", ""),
    }


# Map resource kind to its attribute parser
_KIND_ATTR_PARSERS: dict[
    str,
    Any,
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

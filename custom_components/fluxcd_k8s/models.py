"""Data models for FluxCD Kubernetes resources."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
        return "unknown"
    if ready.status == "True":
        return "ready"
    if ready.status == "False":
        return "not_ready"
    return "unknown"


def parse_flux_resource(raw: dict[str, Any], kind: str) -> FluxResource:
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
        ready_status=ready_status,
        message=ready_cond.message if ready_cond else "",
        reason=ready_cond.reason if ready_cond else "",
        last_reconcile_time=ready_cond.last_transition_time if ready_cond else "",
        suspend=spec.get("suspend", False),
        observed_generation=status.get("observedGeneration"),
        conditions=conditions,
    )

    # Parse kind-specific extra attributes
    if kind == "GitRepository":
        resource.extra_attributes = _parse_git_repository_attrs(spec, status)
    elif kind == "Kustomization":
        resource.extra_attributes = _parse_kustomization_attrs(spec, status)
    elif kind == "HelmRelease":
        resource.extra_attributes = _parse_helm_release_attrs(spec, status)
    elif kind == "HelmRepository":
        resource.extra_attributes = _parse_helm_repository_attrs(spec, status)

    return resource


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

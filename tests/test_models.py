"""Tests for FluxCD Kubernetes integration data models and parsing helpers."""

from __future__ import annotations

import pytest

from fluxcd_k8s_models import (
    FluxCondition,
    FluxResource,
    determine_ready_status,
    get_ready_condition,
    parse_conditions,
    parse_flux_resource,
)


# --- Fixtures ---

def _make_condition(
    cond_type: str = "Ready",
    status: str = "True",
    reason: str = "Succeeded",
    message: str = "All good",
    last_transition_time: str = "2024-01-01T00:00:00Z",
) -> dict:
    return {
        "type": cond_type,
        "status": status,
        "reason": reason,
        "message": message,
        "lastTransitionTime": last_transition_time,
    }


def _make_raw_resource(
    kind: str = "GitRepository",
    name: str = "test-repo",
    namespace: str = "flux-system",
    conditions: list[dict] | None = None,
    spec: dict | None = None,
    status_extra: dict | None = None,
) -> dict:
    status = {}
    if conditions is not None:
        status["conditions"] = conditions
    if status_extra:
        status.update(status_extra)
    return {
        "metadata": {"name": name, "namespace": namespace},
        "spec": spec or {},
        "status": status,
    }


# --- parse_conditions ---

class TestParseConditions:
    def test_empty_status(self):
        assert parse_conditions({}) == []

    def test_empty_conditions_list(self):
        assert parse_conditions({"conditions": []}) == []

    def test_single_condition(self):
        conds = parse_conditions({"conditions": [_make_condition()]})
        assert len(conds) == 1
        assert conds[0].type == "Ready"
        assert conds[0].status == "True"
        assert conds[0].reason == "Succeeded"
        assert conds[0].message == "All good"
        assert conds[0].last_transition_time == "2024-01-01T00:00:00Z"

    def test_multiple_conditions(self):
        conds = parse_conditions(
            {
                "conditions": [
                    _make_condition(cond_type="Ready", status="True"),
                    _make_condition(cond_type="Reconciling", status="False"),
                ]
            }
        )
        assert len(conds) == 2

    def test_missing_fields(self):
        """Conditions with missing fields should default to empty strings."""
        conds = parse_conditions({"conditions": [{"type": "Ready"}]})
        assert len(conds) == 1
        assert conds[0].status == ""
        assert conds[0].reason == ""
        assert conds[0].message == ""
        assert conds[0].last_transition_time == ""


# --- get_ready_condition ---

class TestGetReadyCondition:
    def test_found(self):
        conds = [
            FluxCondition("Reconciling", "False", "", "", ""),
            FluxCondition("Ready", "True", "OK", "msg", "ts"),
        ]
        ready = get_ready_condition(conds)
        assert ready is not None
        assert ready.status == "True"
        assert ready.reason == "OK"

    def test_not_found(self):
        conds = [FluxCondition("Reconciling", "False", "", "", "")]
        assert get_ready_condition(conds) is None

    def test_empty_list(self):
        assert get_ready_condition([]) is None


# --- determine_ready_status ---

class TestDetermineReadyStatus:
    def test_ready(self):
        conds = [FluxCondition("Ready", "True", "", "", "")]
        assert determine_ready_status(conds) == "ready"

    def test_not_ready(self):
        conds = [FluxCondition("Ready", "False", "", "", "")]
        assert determine_ready_status(conds) == "not_ready"

    def test_unknown_status_value(self):
        conds = [FluxCondition("Ready", "Unknown", "", "", "")]
        assert determine_ready_status(conds) == "unknown"

    def test_no_ready_condition(self):
        conds = [FluxCondition("Reconciling", "True", "", "", "")]
        assert determine_ready_status(conds) == "unknown"

    def test_empty_conditions(self):
        assert determine_ready_status([]) == "unknown"


# --- parse_flux_resource: GitRepository ---

class TestParseGitRepository:
    def test_basic_parsing(self):
        raw = _make_raw_resource(
            kind="GitRepository",
            name="my-repo",
            namespace="flux-system",
            conditions=[_make_condition(status="True", reason="Succeeded", message="stored artifact")],
            spec={
                "url": "https://github.com/example/repo",
                "ref": {"branch": "main"},
                "interval": "5m",
                "suspend": False,
            },
            status_extra={
                "observedGeneration": 3,
                "artifact": {
                    "revision": "main@sha1:abc123",
                    "digest": "sha256:def456",
                },
            },
        )
        resource = parse_flux_resource(raw, "GitRepository")
        assert resource.kind == "GitRepository"
        assert resource.name == "my-repo"
        assert resource.namespace == "flux-system"
        assert resource.ready_status == "ready"
        assert resource.message == "stored artifact"
        assert resource.suspend is False
        assert resource.observed_generation == 3
        assert resource.extra_attributes["url"] == "https://github.com/example/repo"
        assert resource.extra_attributes["branch"] == "main"
        assert resource.extra_attributes["artifact_revision"] == "main@sha1:abc123"
        assert resource.extra_attributes["artifact_checksum"] == "sha256:def456"
        assert resource.extra_attributes["interval"] == "5m"

    def test_suspended_resource(self):
        raw = _make_raw_resource(
            spec={"suspend": True},
            conditions=[_make_condition(status="True")],
        )
        resource = parse_flux_resource(raw, "GitRepository")
        assert resource.suspend is True

    def test_empty_status(self):
        raw = _make_raw_resource(conditions=[])
        resource = parse_flux_resource(raw, "GitRepository")
        assert resource.ready_status == "unknown"
        assert resource.message == ""
        assert resource.reason == ""


# --- parse_flux_resource: Kustomization ---

class TestParseKustomization:
    def test_basic_parsing(self):
        raw = _make_raw_resource(
            kind="Kustomization",
            name="my-kustomization",
            namespace="flux-system",
            conditions=[_make_condition(status="True")],
            spec={
                "path": "./clusters/production",
                "prune": True,
                "interval": "10m",
                "sourceRef": {
                    "kind": "GitRepository",
                    "name": "my-repo",
                    "namespace": "flux-system",
                },
            },
            status_extra={
                "observedGeneration": 5,
                "lastAppliedRevision": "main@sha1:abc123",
                "lastAttemptedRevision": "main@sha1:abc123",
            },
        )
        resource = parse_flux_resource(raw, "Kustomization")
        assert resource.kind == "Kustomization"
        assert resource.name == "my-kustomization"
        assert resource.extra_attributes["path"] == "./clusters/production"
        assert resource.extra_attributes["prune"] is True
        assert resource.extra_attributes["interval"] == "10m"
        assert resource.extra_attributes["last_applied_revision"] == "main@sha1:abc123"
        assert resource.extra_attributes["source_ref_kind"] == "GitRepository"
        assert resource.extra_attributes["source_ref_name"] == "my-repo"


# --- parse_flux_resource: HelmRelease ---

class TestParseHelmRelease:
    def test_basic_parsing(self):
        raw = _make_raw_resource(
            kind="HelmRelease",
            name="my-release",
            namespace="default",
            conditions=[_make_condition(status="True")],
            spec={
                "interval": "5m",
                "chart": {
                    "spec": {
                        "chart": "nginx",
                        "version": "1.0.0",
                        "sourceRef": {
                            "kind": "HelmRepository",
                            "name": "bitnami",
                        },
                    }
                },
            },
            status_extra={
                "observedGeneration": 2,
                "lastAppliedRevision": "1.0.0",
                "lastAttemptedRevision": "1.0.0",
                "lastReleaseRevision": 3,
            },
        )
        resource = parse_flux_resource(raw, "HelmRelease")
        assert resource.kind == "HelmRelease"
        assert resource.name == "my-release"
        assert resource.namespace == "default"
        assert resource.extra_attributes["chart_name"] == "nginx"
        assert resource.extra_attributes["chart_version"] == "1.0.0"
        assert resource.extra_attributes["source_ref_kind"] == "HelmRepository"
        assert resource.extra_attributes["source_ref_name"] == "bitnami"
        assert resource.extra_attributes["last_applied_revision"] == "1.0.0"
        assert resource.extra_attributes["last_release_revision"] == 3


# --- parse_flux_resource: HelmRepository ---

class TestParseHelmRepository:
    def test_basic_parsing(self):
        raw = _make_raw_resource(
            kind="HelmRepository",
            name="bitnami",
            namespace="flux-system",
            conditions=[_make_condition(status="True")],
            spec={
                "url": "https://charts.bitnami.com/bitnami",
                "type": "default",
                "interval": "1h",
            },
            status_extra={
                "observedGeneration": 1,
                "artifact": {
                    "revision": "sha256:abc123",
                    "digest": "sha256:def456",
                },
            },
        )
        resource = parse_flux_resource(raw, "HelmRepository")
        assert resource.kind == "HelmRepository"
        assert resource.extra_attributes["url"] == "https://charts.bitnami.com/bitnami"
        assert resource.extra_attributes["repo_type"] == "default"
        assert resource.extra_attributes["interval"] == "1h"
        assert resource.extra_attributes["artifact_revision"] == "sha256:abc123"


# --- Edge cases ---

class TestEdgeCases:
    def test_completely_empty_resource(self):
        """A resource with no metadata, spec, or status should not crash."""
        resource = parse_flux_resource({}, "GitRepository")
        assert resource.kind == "GitRepository"
        assert resource.name == ""
        assert resource.namespace == ""
        assert resource.ready_status == "unknown"
        assert resource.conditions == []

    def test_unknown_kind(self):
        """An unknown kind should still parse common fields."""
        raw = _make_raw_resource(
            name="something",
            namespace="default",
            conditions=[_make_condition(status="True")],
        )
        resource = parse_flux_resource(raw, "UnknownKind")
        assert resource.kind == "UnknownKind"
        assert resource.ready_status == "ready"
        assert resource.extra_attributes == {}

    def test_not_ready_with_message(self):
        """A not-ready resource should expose the failure message."""
        raw = _make_raw_resource(
            conditions=[
                _make_condition(
                    status="False",
                    reason="ArtifactFailed",
                    message="failed to fetch: timeout",
                )
            ]
        )
        resource = parse_flux_resource(raw, "GitRepository")
        assert resource.ready_status == "not_ready"
        assert resource.reason == "ArtifactFailed"
        assert resource.message == "failed to fetch: timeout"

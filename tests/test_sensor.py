"""Tests for FluxCD sensor helper functions.

Covers _build_unique_id and _build_device_info which are the core functions
responsible for ensuring each FluxCD entity/device is uniquely identified in
Home Assistant.
"""

from __future__ import annotations

# conftest.py loads sensor.py via stubs so we can import the pure helpers.
from fluxcd_k8s.const import DOMAIN
from fluxcd_k8s.models import parse_flux_resource
from fluxcd_k8s.sensor import _build_device_info, _build_unique_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_resource(kind: str, name: str, namespace: str = "default"):
    """Return a minimal FluxResource for the given kind/name/namespace."""
    raw = {
        "metadata": {"name": name, "namespace": namespace},
        "spec": {},
        "status": {},
    }
    return parse_flux_resource(raw, kind)


ENTRY_ID = "test_entry_abc123"


# ---------------------------------------------------------------------------
# _build_unique_id
# ---------------------------------------------------------------------------

class TestBuildUniqueId:
    def test_includes_domain_prefix(self):
        """unique_id must start with the integration DOMAIN."""
        resource = _make_resource("HelmRelease", "traefik", "traefik")
        uid = _build_unique_id(ENTRY_ID, resource)
        assert uid.startswith(f"{DOMAIN}_"), (
            f"unique_id '{uid}' should start with '{DOMAIN}_'"
        )

    def test_includes_entry_id(self):
        resource = _make_resource("HelmRelease", "traefik", "traefik")
        uid = _build_unique_id(ENTRY_ID, resource)
        assert ENTRY_ID in uid

    def test_includes_kind(self):
        resource = _make_resource("HelmRelease", "traefik", "traefik")
        uid = _build_unique_id(ENTRY_ID, resource)
        assert "HelmRelease" in uid

    def test_includes_namespace_and_name(self):
        resource = _make_resource("Kustomization", "my-app", "my-ns")
        uid = _build_unique_id(ENTRY_ID, resource)
        assert "my-app" in uid
        assert "my-ns" in uid

    def test_different_kinds_same_namespace_name_produce_different_ids(self):
        """Core requirement: same namespace/name under different kinds must
        never share a unique_id, otherwise HA would treat them as the same
        entity and silently drop one."""
        helm_release = _make_resource("HelmRelease", "traefik", "traefik")
        helm_repo = _make_resource("HelmRepository", "traefik", "traefik")

        uid_hr = _build_unique_id(ENTRY_ID, helm_release)
        uid_repo = _build_unique_id(ENTRY_ID, helm_repo)

        assert uid_hr != uid_repo, (
            "HelmRelease and HelmRepository with same name must have different unique_ids"
        )

    def test_different_namespaces_produce_different_ids(self):
        r1 = _make_resource("Kustomization", "app", "ns-a")
        r2 = _make_resource("Kustomization", "app", "ns-b")
        assert _build_unique_id(ENTRY_ID, r1) != _build_unique_id(ENTRY_ID, r2)

    def test_different_entry_ids_produce_different_ids(self):
        resource = _make_resource("GitRepository", "flux-system", "flux-system")
        uid1 = _build_unique_id("entry-1", resource)
        uid2 = _build_unique_id("entry-2", resource)
        assert uid1 != uid2


# ---------------------------------------------------------------------------
# _build_device_info
# ---------------------------------------------------------------------------

class TestBuildDeviceInfo:
    def test_device_name_includes_namespace_and_name(self):
        resource = _make_resource("HelmRelease", "traefik", "traefik")
        info = _build_device_info(ENTRY_ID, resource)
        assert "traefik/traefik" in info["name"]

    def test_device_name_includes_resource_kind(self):
        """Device name must contain the human-readable resource kind so that
        two resources sharing the same namespace/name but of different kinds
        appear as distinct devices in the HA UI."""
        resource = _make_resource("HelmRelease", "traefik", "traefik")
        info = _build_device_info(ENTRY_ID, resource)
        # The resource_type for HelmRelease is "Helm Releases"
        assert "Helm Releases" in info["name"], (
            f"Device name '{info['name']}' should include the resource type"
        )

    def test_different_kinds_same_namespace_name_produce_different_device_names(self):
        """Core requirement: same namespace/name under different kinds must
        yield distinct device *names* so the HA UI can tell them apart."""
        helm_release = _make_resource("HelmRelease", "traefik", "traefik")
        helm_repo = _make_resource("HelmRepository", "traefik", "traefik")

        name_hr = _build_device_info(ENTRY_ID, helm_release)["name"]
        name_repo = _build_device_info(ENTRY_ID, helm_repo)["name"]

        assert name_hr != name_repo, (
            "Devices for HelmRelease and HelmRepository with the same "
            "namespace/name must have different display names"
        )

    def test_device_identifiers_differ_for_different_kinds(self):
        """Device identifiers (used by HA internally) must differ when kinds
        differ, even if namespace and name are the same."""
        r1 = _make_resource("HelmRelease", "app", "ns")
        r2 = _make_resource("HelmRepository", "app", "ns")

        ids1 = _build_device_info(ENTRY_ID, r1)["identifiers"]
        ids2 = _build_device_info(ENTRY_ID, r2)["identifiers"]
        assert ids1 != ids2

    def test_manufacturer_is_fluxcd(self):
        resource = _make_resource("GitRepository", "repo", "flux-system")
        info = _build_device_info(ENTRY_ID, resource)
        assert info["manufacturer"] == "FluxCD"

    def test_model_matches_resource_type(self):
        resource = _make_resource("Kustomization", "app", "default")
        info = _build_device_info(ENTRY_ID, resource)
        assert info["model"] == "Kustomizations"

    def test_controller_component_label(self):
        """ControllerComponent devices should say 'Flux Controller'."""
        resource = _make_resource("ControllerComponent", "source-controller", "flux-system")
        info = _build_device_info(ENTRY_ID, resource)
        assert "Flux Controller" in info["name"]
        assert info["model"] == "Flux Controller"

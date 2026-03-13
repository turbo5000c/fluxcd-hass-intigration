"""Tests for FluxCD Kubernetes integration constants."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _import_directly(name: str, filepath: Path):
    spec = importlib.util.spec_from_file_location(name, filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_const_path = Path(__file__).parent.parent / "custom_components" / "fluxcd_k8s" / "const.py"
const = _import_directly("fluxcd_k8s_const", _const_path)


class TestFluxCRDDefinitions:
    """Verify that FluxCD CRD definitions use the correct API groups and versions."""

    def test_gitrepository_crd(self):
        assert const.FLUX_GITREPOSITORY["group"] == "source.toolkit.fluxcd.io"
        assert const.FLUX_GITREPOSITORY["version"] == "v1"
        assert const.FLUX_GITREPOSITORY["plural"] == "gitrepositories"
        assert const.FLUX_GITREPOSITORY["kind"] == "GitRepository"

    def test_kustomization_crd(self):
        assert const.FLUX_KUSTOMIZATION["group"] == "kustomize.toolkit.fluxcd.io"
        assert const.FLUX_KUSTOMIZATION["version"] == "v1"
        assert const.FLUX_KUSTOMIZATION["plural"] == "kustomizations"
        assert const.FLUX_KUSTOMIZATION["kind"] == "Kustomization"

    def test_helmrelease_crd(self):
        assert const.FLUX_HELMRELEASE["group"] == "helm.toolkit.fluxcd.io"
        assert const.FLUX_HELMRELEASE["version"] == "v2"
        assert const.FLUX_HELMRELEASE["plural"] == "helmreleases"
        assert const.FLUX_HELMRELEASE["kind"] == "HelmRelease"

    def test_helmrepository_crd(self):
        assert const.FLUX_HELMREPOSITORY["group"] == "source.toolkit.fluxcd.io"
        assert const.FLUX_HELMREPOSITORY["version"] == "v1"
        assert const.FLUX_HELMREPOSITORY["plural"] == "helmrepositories"
        assert const.FLUX_HELMREPOSITORY["kind"] == "HelmRepository"

    def test_all_resources_list(self):
        assert len(const.FLUX_RESOURCES) == 4
        kinds = [r["kind"] for r in const.FLUX_RESOURCES]
        assert "GitRepository" in kinds
        assert "Kustomization" in kinds
        assert "HelmRelease" in kinds
        assert "HelmRepository" in kinds

    def test_domain(self):
        assert const.DOMAIN == "fluxcd_k8s"

    def test_access_modes(self):
        assert const.ACCESS_MODE_IN_CLUSTER == "in_cluster"
        assert const.ACCESS_MODE_KUBECONFIG == "kubeconfig"

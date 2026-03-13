"""Pytest configuration for FluxCD Kubernetes integration tests."""

import importlib.util
import sys
import types
from pathlib import Path

# Set up a minimal fluxcd_k8s package so that models.py can use
# relative imports (e.g. from .const import ...) without triggering
# the real __init__.py which requires homeassistant.
_pkg_dir = Path(__file__).parent.parent / "custom_components" / "fluxcd_k8s"

_pkg = types.ModuleType("fluxcd_k8s")
_pkg.__path__ = [str(_pkg_dir)]
_pkg.__package__ = "fluxcd_k8s"
sys.modules["fluxcd_k8s"] = _pkg


def _load_submodule(name: str, filepath: Path):
    """Load a submodule of the fluxcd_k8s package by file path."""
    full_name = f"fluxcd_k8s.{name}"
    spec = importlib.util.spec_from_file_location(full_name, filepath)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "fluxcd_k8s"
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


# Load const.py first (no dependencies), then models.py (imports .const)
_load_submodule("const", _pkg_dir / "const.py")
_load_submodule("models", _pkg_dir / "models.py")

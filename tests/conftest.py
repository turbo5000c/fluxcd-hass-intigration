"""Pytest configuration for FluxCD Kubernetes integration tests."""

import importlib.util
import sys
from pathlib import Path


def _import_module_directly(name: str, filepath: Path):
    """Import a module directly from its file path, bypassing package __init__."""
    spec = importlib.util.spec_from_file_location(name, filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Import models.py directly so tests don't trigger __init__.py
# which requires homeassistant
_models_path = Path(__file__).parent.parent / "custom_components" / "fluxcd_k8s" / "models.py"
_import_module_directly("fluxcd_k8s_models", _models_path)

"""Kubernetes API client for FluxCD resources using kubernetes-asyncio."""

from __future__ import annotations

import logging
from typing import Any

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client import ApiClient, CustomObjectsApi

from .const import ACCESS_MODE_IN_CLUSTER, FLUX_RESOURCES
from .models import FluxResource, parse_flux_resource

_LOGGER = logging.getLogger(__name__)


class FluxKubernetesClient:
    """Async client for fetching FluxCD custom resources from Kubernetes.

    Supports both in-cluster and kubeconfig-based authentication.
    """

    def __init__(
        self,
        access_mode: str,
        kubeconfig_path: str = "",
        namespace: str = "",
        label_selector: str = "",
    ) -> None:
        """Initialize the FluxCD Kubernetes client.

        Args:
            access_mode: Either 'in_cluster' or 'kubeconfig'.
            kubeconfig_path: Path to kubeconfig file (required if access_mode is 'kubeconfig').
            namespace: Kubernetes namespace to scope queries. Empty string means all namespaces.
            label_selector: Optional Kubernetes label selector to filter resources.
        """
        self._access_mode = access_mode
        self._kubeconfig_path = kubeconfig_path
        self._namespace = namespace
        self._label_selector = label_selector
        self._api_client: ApiClient | None = None

    async def async_init(self) -> None:
        """Initialize the Kubernetes API client.

        Loads the appropriate configuration based on access_mode and
        creates the API client instance.
        """
        if self._access_mode == ACCESS_MODE_IN_CLUSTER:
            # load_incluster_config() configures the global default client
            # settings from the pod's service account credentials
            config.load_incluster_config()
            self._api_client = ApiClient()
        else:
            self._api_client = await config.new_client_from_config(
                config_file=self._kubeconfig_path or None
            )

    async def async_close(self) -> None:
        """Close the Kubernetes API client connection."""
        if self._api_client:
            await self._api_client.close()
            self._api_client = None

    async def async_test_connection(self) -> bool:
        """Test the connection to the Kubernetes cluster.

        Returns True if the cluster is reachable, False otherwise.
        """
        if not self._api_client:
            await self.async_init()
        try:
            version_api = client.VersionApi(self._api_client)
            await version_api.get_code()
            return True
        except Exception:
            _LOGGER.exception("Failed to connect to Kubernetes cluster")
            return False

    async def async_get_all_flux_resources(self) -> list[FluxResource]:
        """Fetch all FluxCD resources from the Kubernetes cluster.

        Iterates over each FluxCD resource kind (GitRepository, Kustomization,
        HelmRelease, HelmRepository) and fetches them using the CustomObjectsApi.

        Returns a list of parsed FluxResource objects.
        """
        if not self._api_client:
            await self.async_init()

        custom_api = CustomObjectsApi(self._api_client)
        all_resources: list[FluxResource] = []

        for flux_crd in FLUX_RESOURCES:
            try:
                resources = await self._async_list_flux_resource(
                    custom_api,
                    group=flux_crd["group"],
                    version=flux_crd["version"],
                    plural=flux_crd["plural"],
                    kind=flux_crd["kind"],
                )
                all_resources.extend(resources)
            except Exception:
                _LOGGER.warning(
                    "Failed to fetch %s resources, skipping",
                    flux_crd["kind"],
                    exc_info=True,
                )

        return all_resources

    async def _async_list_flux_resource(
        self,
        custom_api: CustomObjectsApi,
        group: str,
        version: str,
        plural: str,
        kind: str,
    ) -> list[FluxResource]:
        """Fetch a specific FluxCD resource kind from the cluster.

        Uses list_namespaced_custom_object if a namespace is specified,
        otherwise uses list_cluster_custom_object to query all namespaces.
        """
        kwargs: dict[str, Any] = {}
        if self._label_selector:
            kwargs["label_selector"] = self._label_selector

        if self._namespace:
            # Fetch resources from a specific namespace
            response = await custom_api.list_namespaced_custom_object(
                group=group,
                version=version,
                namespace=self._namespace,
                plural=plural,
                **kwargs,
            )
        else:
            # Fetch resources from all namespaces
            response = await custom_api.list_cluster_custom_object(
                group=group,
                version=version,
                plural=plural,
                **kwargs,
            )

        items: list[dict[str, Any]] = response.get("items", [])
        resources: list[FluxResource] = []
        for item in items:
            try:
                resources.append(parse_flux_resource(item, kind))
            except Exception:
                _LOGGER.warning(
                    "Failed to parse %s resource: %s",
                    kind,
                    item.get("metadata", {}).get("name", "unknown"),
                    exc_info=True,
                )

        _LOGGER.debug("Fetched %d %s resources", len(resources), kind)
        return resources

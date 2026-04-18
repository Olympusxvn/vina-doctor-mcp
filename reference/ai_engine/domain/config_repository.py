from __future__ import annotations

from typing import Protocol


class ConfigRepositoryProtocol(Protocol):
    """Domain port — persists and retrieves runtime configuration.

    Implementations live in the infrastructure layer.
    The application layer depends only on this abstraction.
    """

    def get_dashscope_key(self) -> str | None:
        """Return the persisted DashScope API key, or *None* if not set."""
        ...

    def set_dashscope_key(self, key: str) -> None:
        """Persist *key* as the new DashScope API key."""
        ...

    def get_dashscope_url(self) -> str | None:
        """Return the persisted DashScope base HTTP API URL, or *None* if not set."""
        ...

    def set_dashscope_url(self, url: str) -> None:
        """Persist *url* as the DashScope base HTTP API URL."""
        ...

    def get_model(self, task: str) -> str | None:
        """Return the persisted model ID for *task*, or *None* if not overridden."""
        ...

    def set_model(self, task: str, model_id: str) -> None:
        """Persist *model_id* as the runtime override for *task*."""
        ...

    def get_icd10_enrich_enabled(self) -> bool:
        """Return whether ICD-10 context enrichment is enabled."""
        ...

    def set_icd10_enrich_enabled(self, enabled: bool) -> None:
        """Persist the ICD-10 enrichment toggle."""
        ...

    def get_all_config(self) -> dict:
        """Return a dict of all persisted configuration values."""
        ...

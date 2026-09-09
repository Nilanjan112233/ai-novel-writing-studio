import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PromptRegistryService:
    """Configuration-driven registry resolving logical prompt names to template resources."""

    def __init__(self):
        self.config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "core",
            "prompts_config.json"
        )
        self.prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "resources",
            "prompts"
        )
        self._registry: Dict[str, Any] = {}
        self.load_registry()

    def load_registry(self) -> None:
        """Loads prompt registry mapping config file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._registry = json.load(f)
                logger.info(f"Loaded prompt registry from {self.config_path}")
            else:
                logger.warning(f"Prompt registry config file not found at {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load prompt registry: {e}")
            self._registry = {}

    def get_template_path(self, logical_name: str, version: str = None) -> str:
        """Resolves template file path for logical name and version."""
        prompt_data = self._registry.get(logical_name)
        if not prompt_data:
            raise ValueError(f"Logical prompt name '{logical_name}' not registered.")

        target_version = version or prompt_data.get("current_version", "v1")
        templates = prompt_data.get("templates") or {}
        filename = templates.get(target_version)
        if not filename:
            raise ValueError(f"Version '{target_version}' not registered for logical prompt '{logical_name}'")

        # Resolve path, handle local fallback if necessary
        path = os.path.join(self.prompts_dir, filename)
        if not os.path.exists(path):
            fallback_path = os.path.join("backend", "app", "resources", "prompts", filename)
            if os.path.exists(fallback_path):
                return fallback_path

        return path

    def get_prompt_version_tag(self, logical_name: str, version: str = None) -> str:
        """Returns the identifier tag for prompt version tracking (e.g. 'logical_name_v1')."""
        prompt_data = self._registry.get(logical_name)
        if not prompt_data:
            return f"{logical_name}_unknown"
        target_version = version or prompt_data.get("current_version", "v1")
        return f"{logical_name}_{target_version}"


prompt_registry = PromptRegistryService()

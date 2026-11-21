"""
BrandMind — Jinja2 Prompt Template Manager
Loads, compiles, and renders layered prompt templates for understanding and grounded generation.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import jinja2
import yaml


class PromptTemplateManager:
    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            self.templates_dir = Path(__file__).parent / "templates"

        if not self.templates_dir.exists():
            self.templates_dir.mkdir(parents=True, exist_ok=True)

        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.templates_dir)),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Renders a Jinja2 template with the supplied context dictionary."""
        template = self.env.get_template(template_name)
        return template.render(**context)

    @classmethod
    def load_brand_config(cls, brand_id: str = "rlvnt", config_dir: str = "config") -> Dict[str, Any]:
        """Loads a brand YAML configuration file."""
        cfg_file = Path(config_dir) / f"{brand_id}.yaml"
        if not cfg_file.exists():
            raise FileNotFoundError(f"Brand profile not found for '{brand_id}': {cfg_file}")

        with open(cfg_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

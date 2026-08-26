from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError, meta


class TemplateRenderError(ValueError):
    pass


class TemplateRenderer:
    def __init__(self, template_dir: Path):
        self.environment = Environment(
            loader=FileSystemLoader(template_dir),
            undefined=StrictUndefined,
            autoescape=False,
            keep_trailing_newline=True,
        )

    def required_variables(self, template_name: str) -> set[str]:
        try:
            source = self.environment.loader.get_source(self.environment, template_name)[0]
            parsed = self.environment.parse(source)
            return meta.find_undeclared_variables(parsed)
        except (OSError, TemplateError) as error:
            raise TemplateRenderError(f"Could not inspect template {template_name}: {error}") from error

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        try:
            return self.environment.get_template(template_name).render(**context)
        except TemplateError as error:
            raise TemplateRenderError(f"Could not render template {template_name}: {error}") from error

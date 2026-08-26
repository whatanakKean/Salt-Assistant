from pathlib import Path

import pytest

from salt_assistant.templating import TemplateRenderError, TemplateRenderer


def test_template_renders_inventory_data(tmp_path: Path):
    (tmp_path / "router.jinja").write_text("hostname {{ device.hostname }}\n", encoding="utf-8")
    renderer = TemplateRenderer(tmp_path)
    assert renderer.required_variables("router.jinja") == {"device"}
    assert renderer.render("router.jinja", {"device": {"hostname": "edge-1"}}) == "hostname edge-1\n"


def test_template_fails_on_missing_data(tmp_path: Path):
    (tmp_path / "router.jinja").write_text("hostname {{ device.hostname }}\n", encoding="utf-8")
    with pytest.raises(TemplateRenderError):
        TemplateRenderer(tmp_path).render("router.jinja", {"device": {}})
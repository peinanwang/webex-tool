"""Every template renders with its sample values (catches broken edits). Run: pytest"""

import pytest

from shared import templates

ALL = [t["name"] for t in templates.list_templates()]


def test_there_are_templates():
    assert "notify/assistant_post.md" in ALL and "prompts/assistant.md" in ALL


@pytest.mark.parametrize("name", ALL)
def test_template_renders_with_samples(name):
    assert name in templates.samples(), f"add sample values for {name} to templates/samples.yaml"
    assert templates.render(name, **templates.samples()[name]) or name == "chat/answer.md"


@pytest.mark.parametrize("name", ALL)
def test_template_has_a_header(name):
    info = templates.get_template_info(name)
    assert info["description"], f"{name} needs a {{# ... #}} header saying what it's for"


def test_misspelled_placeholder_gets_a_friendly_error():
    with pytest.raises(templates.TemplateProblem, match=r"Did you mean \{\{ sender \}\}"):
        templates.preview("notify/desktop_title.txt", "🔔 {{ sendr }}")


def test_broken_syntax_gets_a_friendly_error():
    with pytest.raises(templates.TemplateProblem, match="Line 1"):
        templates.preview("notify/desktop_title.txt", "{% if is_direct %}oops")


def test_sandbox_blocks_python_internals():
    with pytest.raises(templates.TemplateProblem):
        templates.preview("notify/desktop_title.txt", "{{ sender.__class__.__mro__ }}")


def test_only_files_inside_templates_are_editable():
    with pytest.raises(templates.TemplateProblem):
        templates.get_template_info("../.env")


def test_rules_list_reads_like_english():
    out = templates.render("chat/rules_list.md", **templates.samples()["chat/rules_list.md"])
    assert "messages from **bob@example.com** → 🔔 **High priority**" in out
    assert "_(paused)_" in out

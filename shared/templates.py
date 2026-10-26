"""Render every user-facing text from files in templates/ (Jinja2).

A template is text with placeholders: `🔔 **{{ sender }}** in {{ space }}`. Code passes the values;
the file decides the wording. Non-technical teammates edit the files (or use the UI's Templates tab).

- Files are re-read when they change (Jinja checks the modification time), so edits apply without
  a restart.
- StrictUndefined: a misspelled placeholder is an error instead of silently blank text.
- SandboxedEnvironment: templates can format text but can't reach into Python, which makes it safe
  to edit them from a web page.
- Each template starts with a {# ... #} header: what it's for, then "Placeholders:" lines like
  "sender: who wrote the message". samples.yaml has example values used by previews and tests.
"""

import difflib
import re
import shutil
from pathlib import Path

import yaml
from jinja2 import FileSystemLoader, StrictUndefined, TemplateSyntaxError, UndefinedError, select_autoescape
from jinja2.sandbox import SandboxedEnvironment

from shared.config import TEMPLATES_DIR

EDITABLE_SUFFIXES = (".md", ".txt", ".html")
DEFAULTS_DIR = TEMPLATES_DIR / "_defaults"   # first-save backups, for "Reset to default"

_env = SandboxedEnvironment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    undefined=StrictUndefined,
    autoescape=select_autoescape(["html"]),   # escape values in .html (the email); not in Markdown
    trim_blocks=True,                          # no blank line left behind by {% if %} / {% for %} lines
    lstrip_blocks=True,
    auto_reload=True,
)


class TemplateProblem(ValueError):
    """A template can't be rendered; the message is written for non-technical editors."""


def render(name: str, **values) -> str:
    """Render templates/<name> with the given values."""
    return _env.get_template(name).render(**values).strip()


# --- editor support (UI Templates tab, tests) ---

def _path(name: str) -> Path:
    path = (TEMPLATES_DIR / name).resolve()
    if TEMPLATES_DIR.resolve() not in path.parents or path.suffix not in EDITABLE_SUFFIXES \
            or DEFAULTS_DIR.resolve() in path.parents:
        raise TemplateProblem(f"{name} isn't an editable template.")
    return path


def list_templates() -> list[dict]:
    """Every editable template, with its description, grouped by folder (e.g. 'notify')."""
    items = []
    for path in sorted(TEMPLATES_DIR.rglob("*")):
        if path.suffix in EDITABLE_SUFFIXES and DEFAULTS_DIR not in path.parents and path.parent != TEMPLATES_DIR:
            name = path.relative_to(TEMPLATES_DIR).as_posix()
            info = parse_header(path.read_text(encoding="utf-8"))
            items.append({"name": name, "group": name.split("/")[0], "description": info["description"]})
    return items


def parse_header(text: str) -> dict:
    """Read the {# ... #} header: description lines, then 'Placeholders:' with 'name: meaning' lines."""
    match = re.match(r"\s*\{#(.*?)#\}", text, re.S)
    description, placeholders, in_placeholders = [], [], False
    for line in (match.group(1).splitlines() if match else []):
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("placeholders"):
            in_placeholders = True
        elif in_placeholders and ":" in line:
            key, meaning = line.split(":", 1)
            placeholders.append({"name": key.strip(), "meaning": meaning.strip()})
        elif not in_placeholders:
            description.append(line)
    return {"description": " ".join(description), "placeholders": placeholders}


def samples() -> dict:
    return yaml.safe_load((TEMPLATES_DIR / "samples.yaml").read_text(encoding="utf-8")) or {}


def get_template_info(name: str) -> dict:
    text = _path(name).read_text(encoding="utf-8")
    return {"name": name, "text": text, **parse_header(text), "sample": samples().get(name, {}),
            "has_default": (DEFAULTS_DIR / name).exists()}


def preview(name: str, text: str) -> str:
    """Render unsaved text with the sample values. Raises TemplateProblem with a friendly message."""
    values = samples().get(name, {})
    try:
        env = _env.overlay(autoescape=name.endswith(".html"))
        return env.from_string(text).render(**values).strip()
    except UndefinedError as exc:
        missing = re.search(r"'(\w+)' is undefined", str(exc))
        if missing:
            word = missing.group(1)
            known = sorted(values)
            hint = difflib.get_close_matches(word, known, n=1)
            tip = f" Did you mean {{{{ {hint[0]} }}}}?" if hint else ""
            raise TemplateProblem(f"{{{{ {word} }}}} isn't a known placeholder.{tip} "
                                  f"Available: {', '.join(known) or 'none'}.") from None
        raise TemplateProblem(f"Something in the template refers to a value that doesn't exist ({exc}).") from None
    except TemplateSyntaxError as exc:
        raise TemplateProblem(f"Line {exc.lineno}: {exc.message}. Check that every {{{{ has a matching }}}} "
                              "and every {% if %} / {% for %} has its {% endif %} / {% endfor %}.") from None
    except Exception as exc:  # anything else the template engine raises
        raise TemplateProblem(f"The template couldn't be rendered: {exc}") from None


def save(name: str, text: str) -> str:
    """Validate, back up the shipped version once, then write. Returns the preview."""
    path = _path(name)
    rendered = preview(name, text)
    backup = DEFAULTS_DIR / name
    if not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return rendered


def reset(name: str) -> str:
    """Restore the version from before the first save. Returns the restored text."""
    path, backup = _path(name), DEFAULTS_DIR / name
    if not backup.exists():
        raise TemplateProblem("This template hasn't been changed from the UI, so there's nothing to reset.")
    shutil.copy2(backup, path)
    return path.read_text(encoding="utf-8")

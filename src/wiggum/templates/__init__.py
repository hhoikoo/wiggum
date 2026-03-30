"""Template loading and rendering via importlib.resources."""

from importlib import resources
from string import Template

_TEMPLATES_PACKAGE = "wiggum.templates"


def load_template(name: str) -> str:
    """Load a template file from the templates package."""
    return (
        resources.files(_TEMPLATES_PACKAGE).joinpath(name).read_text(encoding="utf-8")
    )


def render_template(name: str, **variables: str) -> str:
    """Load a template and substitute $variable placeholders using safe_substitute."""
    raw = load_template(name)
    return Template(raw).safe_substitute(variables)

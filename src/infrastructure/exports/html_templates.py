from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_DIR = Path(__file__).with_name("templates")


@lru_cache(maxsize=1)
def get_html_template_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=select_autoescape(
            enabled_extensions=("html", "j2"),
            default_for_string=True,
        ),
    )


def render_html_template(template_name: str, context: dict[str, object]) -> str:
    return get_html_template_environment().get_template(template_name).render(**context)

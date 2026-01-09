# SPDX-FileCopyrightText: 2025 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
"""Template processing for ADT Seed.

Provides custom Jinja2 filters and functions for profile templates.
"""

import re
import unicodedata
from pathlib import Path
from typing import Any

import tomlkit
from jinja2 import Environment


def create_template_environment(project_dir: Path | None = None) -> Environment:
    """Create a Jinja2 environment with custom filters and globals.

    Args:
        project_dir: Project directory for path-relative operations

    Returns:
        Configured Jinja2 Environment
    """
    # autoescape=False is intentional: we're generating config files, not HTML
    env = Environment(
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,  # noqa: S701
    )

    # Add custom filters
    env.filters["to_toml"] = filter_to_toml
    env.filters["to_yaml"] = filter_to_yaml
    env.filters["slugify"] = filter_slugify
    env.filters["path_exists"] = filter_path_exists
    env.filters["snake_case"] = filter_snake_case
    env.filters["kebab_case"] = filter_kebab_case
    env.filters["pascal_case"] = filter_pascal_case
    env.filters["camel_case"] = filter_camel_case

    # Add custom global functions
    project_dir = project_dir or Path.cwd()
    env.globals["pyproject_get"] = create_pyproject_get(project_dir)
    env.globals["include_if"] = include_if
    env.globals["path_exists"] = create_path_exists_func(project_dir)

    return env


def render_template(
    content: str,
    context: dict[str, Any],
    project_dir: Path | None = None,
) -> str:
    """Render a Jinja2 template with custom filters and functions.

    Args:
        content: Template content
        context: Variable context for rendering
        project_dir: Project directory for path-relative operations

    Returns:
        Rendered content
    """
    env = create_template_environment(project_dir)
    template = env.from_string(content)
    return template.render(**context)


# =============================================================================
# Custom Filters
# =============================================================================


def filter_to_toml(value: Any, *, inline: bool = False) -> str:
    """Convert a Python value to TOML format.

    Args:
        value: Value to convert (dict, list, or scalar)
        inline: If True, use inline table/array format

    Returns:
        TOML-formatted string

    Examples:
        {{ {"key": "value"} | to_toml }}
        {{ ["a", "b", "c"] | to_toml }}
    """
    if isinstance(value, dict):
        return _toml_dict(value, inline)
    if isinstance(value, list):
        return _toml_list(value, inline)
    # Scalar value - use TOML encoding
    doc = tomlkit.document()
    doc["_"] = value
    result = tomlkit.dumps(doc)
    return result.split("=", 1)[1].strip()


def _toml_dict(value: dict, inline: bool) -> str:  # noqa: FBT001
    """Convert dict to TOML format."""
    if inline:
        doc = tomlkit.inline_table()
        for k, v in value.items():
            doc[k] = v
        return tomlkit.dumps({"_": doc}).split("=", 1)[1].strip()
    doc = tomlkit.document()
    for k, v in value.items():
        doc[k] = v
    return tomlkit.dumps(doc).strip()


def _toml_list(value: list, inline: bool) -> str:  # noqa: FBT001
    """Convert list to TOML format."""
    if inline:
        arr = tomlkit.array()
        arr.extend(value)
        return str(arr)
    doc = tomlkit.document()
    doc["_"] = value
    result = tomlkit.dumps(doc)
    return result.split("=", 1)[1].strip()


def filter_to_yaml(value: Any, *, default_flow_style: bool = False) -> str:
    """Convert a Python value to YAML format.

    Args:
        value: Value to convert
        default_flow_style: If True, use flow style (inline) for collections

    Returns:
        YAML-formatted string

    Examples:
        {{ {"key": "value"} | to_yaml }}
        {{ items | to_yaml }}
    """
    try:
        import yaml  # noqa: PLC0415

        result = yaml.dump(
            value,
            default_flow_style=default_flow_style,
            allow_unicode=True,
            sort_keys=False,
        )
        return result.strip()
    except ImportError:
        # Fallback: simple representation for common cases
        return _simple_yaml_dump(value)


def _simple_yaml_dump(value: Any, indent: int = 0) -> str:  # noqa: PLR0911
    """Simple YAML-like dump without PyYAML dependency."""
    prefix = "  " * indent

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return _yaml_string(value)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        return _yaml_dict(value, prefix, indent)
    if isinstance(value, list):
        return _yaml_list(value, prefix, indent)
    return str(value)


def _yaml_string(value: str) -> str:
    """Format string for YAML output."""
    if any(c in value for c in ":#{}[]&*!|>'\"%@`"):
        return f'"{value}"'
    return value


def _yaml_dict(value: dict, prefix: str, indent: int) -> str:
    """Format dict for YAML output."""
    if not value:
        return "{}"
    lines = []
    for k, v in value.items():
        if isinstance(v, (dict, list)) and v:
            lines.append(f"{prefix}{k}:")
            lines.append(_simple_yaml_dump(v, indent + 1))
        else:
            lines.append(f"{prefix}{k}: {_simple_yaml_dump(v)}")
    return "\n".join(lines)


def _yaml_list(value: list, prefix: str, indent: int) -> str:
    """Format list for YAML output."""
    if not value:
        return "[]"
    lines = []
    for item in value:
        if isinstance(item, dict) and item:
            lines.append(f"{prefix}-")
            lines.append(_simple_yaml_dump(item, indent + 1))
        else:
            lines.append(f"{prefix}- {_simple_yaml_dump(item)}")
    return "\n".join(lines)


def filter_slugify(value: str, separator: str = "-") -> str:
    """Convert a string to a URL-friendly slug.

    Args:
        value: String to slugify
        separator: Character to use as word separator (default: "-")

    Returns:
        Slugified string

    Examples:
        {{ "Hello World!" | slugify }}  -> "hello-world"
        {{ "Café Résumé" | slugify }}    -> "cafe-resume"
    """
    # Normalize unicode characters
    value = unicodedata.normalize("NFKD", str(value))
    # Remove non-ASCII characters
    value = value.encode("ascii", "ignore").decode("ascii")
    # Convert to lowercase
    value = value.lower()
    # Replace any non-alphanumeric characters with separator
    value = re.sub(r"[^a-z0-9]+", separator, value)
    # Remove leading/trailing separators
    value = value.strip(separator)
    # Collapse multiple separators
    value = re.sub(f"{re.escape(separator)}+", separator, value)
    return value


def filter_path_exists(path: str, base_dir: str | None = None) -> bool:
    """Check if a path exists.

    Args:
        path: Path to check (can be relative or absolute)
        base_dir: Base directory for relative paths (default: cwd)

    Returns:
        True if path exists, False otherwise

    Examples:
        {% if "pyproject.toml" | path_exists %}
    """
    p = Path(path)
    if not p.is_absolute() and base_dir:
        p = Path(base_dir) / p
    elif not p.is_absolute():
        p = Path.cwd() / p
    return p.exists()


def filter_snake_case(value: str) -> str:
    """Convert string to snake_case.

    Examples:
        {{ "HelloWorld" | snake_case }}  -> "hello_world"
        {{ "my-project" | snake_case }}  -> "my_project"
    """
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.replace("-", "_").lower()


def filter_kebab_case(value: str) -> str:
    """Convert string to kebab-case.

    Examples:
        {{ "HelloWorld" | kebab_case }}  -> "hello-world"
        {{ "my_project" | kebab_case }}  -> "my-project"
    """
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1-\2", value)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s1)
    return s2.replace("_", "-").lower()


def filter_pascal_case(value: str) -> str:
    """Convert string to PascalCase.

    Examples:
        {{ "hello_world" | pascal_case }}  -> "HelloWorld"
        {{ "my-project" | pascal_case }}   -> "MyProject"
    """
    parts = value.replace("-", "_").split("_")
    return "".join(word.capitalize() for word in parts)


def filter_camel_case(value: str) -> str:
    """Convert string to camelCase.

    Examples:
        {{ "hello_world" | camel_case }}  -> "helloWorld"
        {{ "my-project" | camel_case }}   -> "myProject"
    """
    pascal = filter_pascal_case(value)
    if pascal:
        return pascal[0].lower() + pascal[1:]
    return pascal


# =============================================================================
# Custom Global Functions
# =============================================================================


def create_pyproject_get(project_dir: Path):
    """Create a pyproject_get function bound to a project directory.

    Args:
        project_dir: Project directory containing pyproject.toml

    Returns:
        Function that retrieves values from pyproject.toml
    """

    def pyproject_get(key: str, default: Any = None) -> Any:
        """Get a value from pyproject.toml using dot notation.

        Args:
            key: Dot-separated key path (e.g., "project.name")
            default: Default value if key not found

        Returns:
            Value from pyproject.toml or default

        Examples:
            {{ pyproject_get("project.name") }}
            {{ pyproject_get("project.version", "0.0.0") }}
            {{ pyproject_get("tool.ruff.line-length", 88) }}
        """
        pyproject_path = project_dir / "pyproject.toml"
        if not pyproject_path.exists():
            return default

        try:
            content = pyproject_path.read_text()
            data = tomlkit.parse(content)

            # Navigate the key path
            parts = key.split(".")
            current = data
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return default

            return current  # noqa: TRY300
        except Exception:
            return default

    return pyproject_get


def include_if(condition: bool, content: str, else_content: str = "") -> str:  # noqa: FBT001
    """Conditionally include content.

    A cleaner alternative to {% if %} blocks for simple cases.

    Args:
        condition: Boolean condition
        content: Content to include if condition is True
        else_content: Content to include if condition is False

    Returns:
        content if condition is True, else_content otherwise

    Examples:
        {{ include_if(use_docker, "docker-compose.yml") }}
        {{ include_if(python_version >= "3.10", "match statement", "if/elif") }}
    """
    return content if condition else else_content


def create_path_exists_func(project_dir: Path):
    """Create a path_exists function bound to a project directory.

    Args:
        project_dir: Base directory for relative paths

    Returns:
        Function that checks if paths exist
    """

    def path_exists(path: str) -> bool:
        """Check if a path exists relative to project directory.

        Args:
            path: Path to check (relative to project dir or absolute)

        Returns:
            True if path exists

        Examples:
            {% if path_exists("src/mypackage") %}
            {% if path_exists("docker-compose.yml") %}
        """
        p = Path(path)
        if not p.is_absolute():
            p = project_dir / p
        return p.exists()

    return path_exists


# =============================================================================
# Conditional File Processing
# =============================================================================


def evaluate_condition(
    condition: str,
    context: dict[str, Any],
    project_dir: Path | None = None,
) -> bool:
    """Evaluate a condition expression for conditional file inclusion.

    Supports simple expressions like:
    - Variable truthiness: "use_docker"
    - Comparison: "python_version >= '3.10'"
    - Path existence: "path_exists('src')"
    - Logical operators: "use_docker and not use_kubernetes"

    Args:
        condition: Condition expression string
        context: Variable context
        project_dir: Project directory for path checks

    Returns:
        True if condition evaluates to True

    Examples:
        evaluate_condition("use_docker", {"use_docker": True})
        evaluate_condition("python_version >= '3.10'", {"python_version": "3.11"})
    """
    if not condition:
        return True

    project_dir = project_dir or Path.cwd()

    # Build evaluation context
    eval_context = {
        **context,
        "path_exists": create_path_exists_func(project_dir),
        "pyproject_get": create_pyproject_get(project_dir),
    }

    try:
        # Use safe evaluation (no builtins to prevent code injection)
        return bool(eval(condition, {"__builtins__": {}}, eval_context))  # noqa: S307
    except Exception:
        # If evaluation fails, default to True (include file)
        return True

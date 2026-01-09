# SPDX-FileCopyrightText: 2025 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

"""Unit tests for seed template module."""

import tempfile
from pathlib import Path

import pytest

from abilian_devtools.seed.template import (
    create_path_exists_func,
    create_pyproject_get,
    create_template_environment,
    evaluate_condition,
    filter_camel_case,
    filter_kebab_case,
    filter_pascal_case,
    filter_path_exists,
    filter_slugify,
    filter_snake_case,
    filter_to_toml,
    filter_to_yaml,
    include_if,
    render_template,
)

# =============================================================================
# Tests for filter_to_toml
# =============================================================================


@pytest.mark.unit
class TestFilterToToml:
    """Tests for the to_toml filter."""

    def test_converts_simple_dict(self):
        # Arrange
        data = {"key": "value"}

        # Act
        result = filter_to_toml(data)

        # Assert
        assert 'key = "value"' in result

    def test_converts_nested_dict(self):
        # Arrange
        data = {"section": {"key": "value"}}

        # Act
        result = filter_to_toml(data)

        # Assert
        assert "[section]" in result or "section" in result

    def test_converts_list(self):
        # Arrange
        data = ["a", "b", "c"]

        # Act
        result = filter_to_toml(data)

        # Assert
        assert '"a"' in result
        assert '"b"' in result
        assert '"c"' in result

    def test_converts_integer(self):
        # Arrange
        data = 42

        # Act
        result = filter_to_toml(data)

        # Assert
        assert "42" in result

    def test_converts_boolean(self):
        # Arrange
        data = True

        # Act
        result = filter_to_toml(data)

        # Assert
        assert "true" in result

    def test_inline_dict_format(self):
        # Arrange
        data = {"a": 1, "b": 2}

        # Act
        result = filter_to_toml(data, inline=True)

        # Assert
        assert "{" in result or "a = 1" in result


# =============================================================================
# Tests for filter_to_yaml
# =============================================================================


@pytest.mark.unit
class TestFilterToYaml:
    """Tests for the to_yaml filter."""

    def test_converts_simple_dict(self):
        # Arrange
        data = {"key": "value"}

        # Act
        result = filter_to_yaml(data)

        # Assert
        assert "key:" in result
        assert "value" in result

    def test_converts_list(self):
        # Arrange
        data = ["a", "b", "c"]

        # Act
        result = filter_to_yaml(data)

        # Assert
        assert "- a" in result or "a" in result

    def test_converts_nested_structure(self):
        # Arrange
        data = {"parent": {"child": "value"}}

        # Act
        result = filter_to_yaml(data)

        # Assert
        assert "parent" in result
        assert "child" in result

    def test_handles_none(self):
        # Arrange
        data = None

        # Act
        result = filter_to_yaml(data)

        # Assert
        assert "null" in result

    def test_handles_boolean(self):
        # Arrange
        data = {"enabled": True, "disabled": False}

        # Act
        result = filter_to_yaml(data)

        # Assert
        assert "true" in result
        assert "false" in result


# =============================================================================
# Tests for filter_slugify
# =============================================================================


@pytest.mark.unit
class TestFilterSlugify:
    """Tests for the slugify filter."""

    def test_converts_simple_string(self):
        # Arrange
        value = "Hello World"

        # Act
        result = filter_slugify(value)

        # Assert
        assert result == "hello-world"

    def test_removes_special_characters(self):
        # Arrange
        value = "Hello, World!"

        # Act
        result = filter_slugify(value)

        # Assert
        assert result == "hello-world"

    def test_handles_unicode(self):
        # Arrange
        value = "Café Résumé"

        # Act
        result = filter_slugify(value)

        # Assert
        assert result == "cafe-resume"

    def test_custom_separator(self):
        # Arrange
        value = "Hello World"

        # Act
        result = filter_slugify(value, separator="_")

        # Assert
        assert result == "hello_world"

    def test_collapses_multiple_separators(self):
        # Arrange
        value = "Hello   World"

        # Act
        result = filter_slugify(value)

        # Assert
        assert result == "hello-world"

    def test_strips_leading_trailing_separators(self):
        # Arrange
        value = "  Hello World  "

        # Act
        result = filter_slugify(value)

        # Assert
        assert result == "hello-world"


# =============================================================================
# Tests for filter_path_exists
# =============================================================================


@pytest.mark.unit
class TestFilterPathExists:
    """Tests for the path_exists filter."""

    def test_returns_true_for_existing_path(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")

            # Act
            result = filter_path_exists(str(test_file))

            # Assert
            assert result is True

    def test_returns_false_for_nonexistent_path(self):
        # Arrange
        path = "/nonexistent/path/to/file"

        # Act
        result = filter_path_exists(path)

        # Assert
        assert result is False

    def test_handles_relative_path_with_base_dir(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")

            # Act
            result = filter_path_exists("test.txt", base_dir=tmpdir)

            # Assert
            assert result is True


# =============================================================================
# Tests for case conversion filters
# =============================================================================


@pytest.mark.unit
class TestFilterSnakeCase:
    """Tests for the snake_case filter."""

    def test_converts_camel_case(self):
        # Arrange / Act / Assert
        assert filter_snake_case("helloWorld") == "hello_world"

    def test_converts_pascal_case(self):
        # Arrange / Act / Assert
        assert filter_snake_case("HelloWorld") == "hello_world"

    def test_converts_kebab_case(self):
        # Arrange / Act / Assert
        assert filter_snake_case("hello-world") == "hello_world"

    def test_handles_already_snake_case(self):
        # Arrange / Act / Assert
        assert filter_snake_case("hello_world") == "hello_world"


@pytest.mark.unit
class TestFilterKebabCase:
    """Tests for the kebab_case filter."""

    def test_converts_camel_case(self):
        # Arrange / Act / Assert
        assert filter_kebab_case("helloWorld") == "hello-world"

    def test_converts_pascal_case(self):
        # Arrange / Act / Assert
        assert filter_kebab_case("HelloWorld") == "hello-world"

    def test_converts_snake_case(self):
        # Arrange / Act / Assert
        assert filter_kebab_case("hello_world") == "hello-world"


@pytest.mark.unit
class TestFilterPascalCase:
    """Tests for the pascal_case filter."""

    def test_converts_snake_case(self):
        # Arrange / Act / Assert
        assert filter_pascal_case("hello_world") == "HelloWorld"

    def test_converts_kebab_case(self):
        # Arrange / Act / Assert
        assert filter_pascal_case("hello-world") == "HelloWorld"


@pytest.mark.unit
class TestFilterCamelCase:
    """Tests for the camel_case filter."""

    def test_converts_snake_case(self):
        # Arrange / Act / Assert
        assert filter_camel_case("hello_world") == "helloWorld"

    def test_converts_kebab_case(self):
        # Arrange / Act / Assert
        assert filter_camel_case("hello-world") == "helloWorld"

    def test_handles_empty_string(self):
        # Arrange / Act / Assert
        assert filter_camel_case("") == ""


# =============================================================================
# Tests for include_if function
# =============================================================================


@pytest.mark.unit
class TestIncludeIf:
    """Tests for the include_if function."""

    def test_returns_content_when_condition_true(self):
        # Arrange
        condition = True
        content = "included"

        # Act
        result = include_if(condition, content)

        # Assert
        assert result == "included"

    def test_returns_empty_when_condition_false(self):
        # Arrange
        condition = False
        content = "included"

        # Act
        result = include_if(condition, content)

        # Assert
        assert result == ""

    def test_returns_else_content_when_condition_false(self):
        # Arrange
        condition = False
        content = "yes"
        else_content = "no"

        # Act
        result = include_if(condition, content, else_content)

        # Assert
        assert result == "no"


# =============================================================================
# Tests for create_pyproject_get
# =============================================================================


@pytest.mark.unit
class TestCreatePyprojectGet:
    """Tests for the pyproject_get function factory."""

    def test_returns_value_from_pyproject(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            pyproject = project_dir / "pyproject.toml"
            pyproject.write_text('[project]\nname = "my-project"\nversion = "1.0.0"')
            pyproject_get = create_pyproject_get(project_dir)

            # Act
            result = pyproject_get("project.name")

            # Assert
            assert result == "my-project"

    def test_returns_nested_value(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            pyproject = project_dir / "pyproject.toml"
            pyproject.write_text("[tool.ruff]\nline-length = 100")
            pyproject_get = create_pyproject_get(project_dir)

            # Act
            result = pyproject_get("tool.ruff.line-length")

            # Assert
            assert result == 100

    def test_returns_default_when_key_not_found(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            pyproject = project_dir / "pyproject.toml"
            pyproject.write_text('[project]\nname = "test"')
            pyproject_get = create_pyproject_get(project_dir)

            # Act
            result = pyproject_get("nonexistent.key", "default")

            # Assert
            assert result == "default"

    def test_returns_default_when_file_missing(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            pyproject_get = create_pyproject_get(project_dir)

            # Act
            result = pyproject_get("project.name", "fallback")

            # Assert
            assert result == "fallback"


# =============================================================================
# Tests for create_path_exists_func
# =============================================================================


@pytest.mark.unit
class TestCreatePathExistsFunc:
    """Tests for the path_exists function factory."""

    def test_returns_true_for_existing_file(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            test_file = project_dir / "exists.txt"
            test_file.write_text("content")
            path_exists = create_path_exists_func(project_dir)

            # Act
            result = path_exists("exists.txt")

            # Assert
            assert result is True

    def test_returns_false_for_missing_file(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            path_exists = create_path_exists_func(project_dir)

            # Act
            result = path_exists("missing.txt")

            # Assert
            assert result is False

    def test_returns_true_for_existing_directory(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            test_dir = project_dir / "subdir"
            test_dir.mkdir()
            path_exists = create_path_exists_func(project_dir)

            # Act
            result = path_exists("subdir")

            # Assert
            assert result is True


# =============================================================================
# Tests for create_template_environment
# =============================================================================


@pytest.mark.unit
class TestCreateTemplateEnvironment:
    """Tests for the template environment factory."""

    def test_environment_has_custom_filters(self):
        # Arrange / Act
        env = create_template_environment()

        # Assert
        assert "to_toml" in env.filters
        assert "to_yaml" in env.filters
        assert "slugify" in env.filters
        assert "path_exists" in env.filters
        assert "snake_case" in env.filters
        assert "kebab_case" in env.filters
        assert "pascal_case" in env.filters
        assert "camel_case" in env.filters

    def test_environment_has_custom_globals(self):
        # Arrange / Act
        env = create_template_environment()

        # Assert
        assert "pyproject_get" in env.globals
        assert "include_if" in env.globals
        assert "path_exists" in env.globals

    def test_environment_preserves_trailing_newline(self):
        # Arrange
        env = create_template_environment()

        # Assert
        assert env.keep_trailing_newline is True


# =============================================================================
# Tests for render_template
# =============================================================================


@pytest.mark.unit
class TestRenderTemplate:
    """Tests for the render_template function."""

    def test_renders_simple_variable(self):
        # Arrange
        template = "Hello {{ name }}!"
        context = {"name": "World"}

        # Act
        result = render_template(template, context)

        # Assert
        assert result == "Hello World!"

    def test_renders_with_snake_case_filter(self):
        # Arrange
        template = "{{ name | snake_case }}"
        context = {"name": "HelloWorld"}

        # Act
        result = render_template(template, context)

        # Assert
        assert result == "hello_world"

    def test_renders_with_slugify_filter(self):
        # Arrange
        template = "{{ title | slugify }}"
        context = {"title": "Hello World!"}

        # Act
        result = render_template(template, context)

        # Assert
        assert result == "hello-world"

    def test_renders_with_to_toml_filter(self):
        # Arrange
        template = "{{ data | to_toml }}"
        context = {"data": {"key": "value"}}

        # Act
        result = render_template(template, context)

        # Assert
        assert 'key = "value"' in result

    def test_renders_with_include_if(self):
        # Arrange
        template = "{{ include_if(use_feature, 'enabled', 'disabled') }}"
        context = {"use_feature": True}

        # Act
        result = render_template(template, context)

        # Assert
        assert result == "enabled"

    def test_renders_with_pyproject_get(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            pyproject = project_dir / "pyproject.toml"
            pyproject.write_text('[project]\nname = "test-project"')
            template = "{{ pyproject_get('project.name', 'unknown') }}"
            context = {}

            # Act
            result = render_template(template, context, project_dir)

            # Assert
            assert result == "test-project"

    def test_renders_conditional_block(self):
        # Arrange
        template = """{% if use_docker %}
docker: enabled
{% endif %}"""
        context = {"use_docker": True}

        # Act
        result = render_template(template, context)

        # Assert
        assert "docker: enabled" in result


# =============================================================================
# Tests for evaluate_condition
# =============================================================================


@pytest.mark.unit
class TestEvaluateCondition:
    """Tests for the evaluate_condition function."""

    def test_evaluates_true_variable(self):
        # Arrange
        condition = "use_docker"
        context = {"use_docker": True}

        # Act
        result = evaluate_condition(condition, context)

        # Assert
        assert result is True

    def test_evaluates_false_variable(self):
        # Arrange
        condition = "use_docker"
        context = {"use_docker": False}

        # Act
        result = evaluate_condition(condition, context)

        # Assert
        assert result is False

    def test_evaluates_comparison(self):
        # Arrange
        condition = "python_version >= '3.10'"
        context = {"python_version": "3.11"}

        # Act
        result = evaluate_condition(condition, context)

        # Assert
        assert result is True

    def test_evaluates_not_operator(self):
        # Arrange
        condition = "not use_kubernetes"
        context = {"use_kubernetes": False}

        # Act
        result = evaluate_condition(condition, context)

        # Assert
        assert result is True

    def test_evaluates_and_operator(self):
        # Arrange
        condition = "use_docker and use_compose"
        context = {"use_docker": True, "use_compose": True}

        # Act
        result = evaluate_condition(condition, context)

        # Assert
        assert result is True

    def test_evaluates_path_exists(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            test_file = project_dir / "Dockerfile"
            test_file.write_text("FROM python:3.11")
            condition = "path_exists('Dockerfile')"
            context = {}

            # Act
            result = evaluate_condition(condition, context, project_dir)

            # Assert
            assert result is True

    def test_returns_true_for_empty_condition(self):
        # Arrange
        condition = ""
        context = {}

        # Act
        result = evaluate_condition(condition, context)

        # Assert
        assert result is True

    def test_returns_true_for_invalid_condition(self):
        # Arrange
        condition = "invalid syntax !!!"
        context = {}

        # Act
        result = evaluate_condition(condition, context)

        # Assert
        assert result is True  # Default to True on error

    def test_evaluates_equality(self):
        # Arrange
        condition = "env == 'production'"
        context = {"env": "production"}

        # Act
        result = evaluate_condition(condition, context)

        # Assert
        assert result is True

import logging
import os

import pytest

from nomad_plugin_tests import package_tester


@pytest.mark.parametrize(
    "package_name, pyproject_path, has_test_group",
    [
        ("nomad_gui", "infra/pyproject.toml", True),
        ("example_plugin", "pyproject.toml", False),
    ],
)
def test_install_package_dependencies_uses_expected_pyproject(
    monkeypatch, tmp_path, package_name, pyproject_path, has_test_group
):
    call = {}

    def run_command(command, **kwargs):
        call["command"] = command
        call["kwargs"] = kwargs
        return True

    monkeypatch.setattr(package_tester, "run_command", run_command)

    package_tester.install_package_dependencies(
        temp_dir=str(tmp_path),
        package_name=package_name,
        python_path="/venv/bin/python",
        package_logger=logging.getLogger(package_name),
    )

    expected_pyproject = os.path.join(str(tmp_path), pyproject_path)
    assert call["command"][4] == expected_pyproject
    assert (f"{expected_pyproject}:test" in call["command"]) is has_test_group
    assert ("pytest" in call["command"]) is has_test_group
    assert call["kwargs"]["cwd"] == str(tmp_path)

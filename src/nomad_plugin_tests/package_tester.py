import logging
import os
from typing import TYPE_CHECKING

from nomad_plugin_tests.config import TESTS_TO_RUN
from nomad_plugin_tests.errors import PackageTestError
from nomad_plugin_tests.process import run_command

if TYPE_CHECKING:
    from nomad_plugin_tests.parsing import PluginPackage


def create_virtual_environment(
    *, venv_path: str, package_logger: logging.Logger
) -> None:
    """Creates a virtual environment using `uv`.

    Args:
        venv_path: The path where the virtual environment should be created.
        package_logger: The logger to use for logging messages.
    """
    venv_command = [
        "uv",
        "venv",
        "-p",
        "3.12",
        "--seed",
        venv_path,
    ]
    if not run_command(venv_command, package_logger=package_logger):
        raise PackageTestError(f"Failed to create venv: {' '.join(venv_command)}")
    package_logger.info(f"Successfully created venv at '{venv_path}'.")


def install_distro_dependencies(
    *, python_path: str, package_logger: logging.Logger
) -> None:
    """Installs distribution-level dependencies from requirements.txt.

    Args:
        python_path: The path to the Python executable within the virtual environment.
        package_logger: The logger to use for logging messages.
    """
    requirements_file = os.path.join(os.getcwd(), "requirements.txt")
    install_command = [
        "uv",
        "pip",
        "install",
        "-r",
        requirements_file,
        "--reinstall",
        "--quiet",
        "-p",
        python_path,
    ]
    if not run_command(install_command, cwd=os.getcwd(), package_logger=package_logger):
        raise PackageTestError(
            f"Failed to install distro dependencies: {' '.join(install_command)}"
        )
    package_logger.info("Successfully installed distro dependencies.")


def install_package_dependencies(
    *, temp_dir: str, python_path: str, package_logger: logging.Logger
) -> None:
    """Installs development dependencies from pyproject.toml.

    Args:
        temp_dir: The temporary directory where the package source code is located.
        python_path: The path to the Python executable within the virtual environment.
        package_logger: The logger to use for logging messages.
    """
    requirements_file = os.path.join(os.getcwd(), "requirements.txt")
    install_command = [
        "uv",
        "pip",
        "install",
        "-r",
        f"{temp_dir}/pyproject.toml",
        "--all-extras",
        "-p",
        python_path,
        "-c",
        requirements_file,
    ]

    if not run_command(install_command, cwd=temp_dir, package_logger=package_logger):
        raise PackageTestError(
            f"Failed to install package dependencies: {' '.join(install_command)}"
        )
    package_logger.info("Successfully installed package dependencies.")


def run_pytest(
    *,
    temp_dir: str,
    package: "PluginPackage",
    python_path: str,
    package_logger: logging.Logger,
) -> None:
    """Runs pytest to execute tests within the package.

    Args:
        temp_dir: The temporary directory where the package source code is located.
        package: The PluginPackage object.
        python_path: The path to the Python executable within the virtual environment.
        package_logger: The logger to use for logging messages.
    """
    pytest_command = [python_path, "-m", "pytest", "-p", "no:warnings"]

    if test_folder := TESTS_TO_RUN.get(package.name):
        pytest_command.append(os.path.join(temp_dir, test_folder))
    else:
        pytest_command.append(temp_dir)

    if not run_command(pytest_command, cwd=temp_dir, package_logger=package_logger):
        raise PackageTestError(f"Tests failed: {' '.join(pytest_command)}")

import tomllib
import re
import os
import logging
from dataclasses import dataclass, field
from typing import TypedDict

from nomad_plugin_tests.process import create_requirements_file

logger = logging.getLogger(__name__)


@dataclass
class PluginPackage:
    name: str
    description: str | None = None
    version: str | None = None
    homepage: str | None = None
    documentation: str | None = None
    repository: str | None = None
    github_url: str | None = None
    commit_hash: str | None = None
    entry_points: list[str] = field(default_factory=list)


class LockGitInfo(TypedDict):
    commit: str
    url: str


def _parse_git_packages(
    toml_data: dict, lock_data: dict[str, LockGitInfo]
) -> dict[str, LockGitInfo]:
    """
    Parses git package information from TOML and lock data.

    Args:
        toml_data: A dictionary representing the parsed TOML data.
        lock_data: A dictionary containing lock data for packages.

    Returns:
        A dictionary where keys are package names and values are dictionaries
        containing 'commit' and 'url' information for git packages.
        Returns an empty dict if no git packages are found.

    Raises:
        KeyError: If the expected structure is not found in `toml_data` or `lock_data`.
        TypeError: If toml_data['project']['optional-dependencies']['plugins'] is not a list.
    """

    git_packages: dict[str, LockGitInfo] = {}

    try:
        plugins = toml_data["project"]["optional-dependencies"]["plugins"]
    except KeyError as e:
        # Re-raise with more context
        raise KeyError(f"Missing key in toml_data: {e}") from e

    for line in plugins:
        match = re.match(r"(\S+) @ git\+(\S+?)@(\S+)", line)
        if match:
            package_name = match.group(1).strip()
            url = match.group(2)
            commit_hash = match.group(3)

            # Prioritize lock data if available
            if package_name in lock_data:
                git_packages[package_name] = lock_data[package_name]
            else:
                git_packages[package_name] = {"commit": commit_hash, "url": url}

    return git_packages


def _parse_git_requirements() -> dict[str, LockGitInfo]:
    """
    Parses a requirements.txt file, extracting Git dependency information (package name, URL, commit hash).

    If the file doesn't exist, it attempts to create one using `create_requirements_file`.
    Returns a dictionary of package names to Git dependency details, or an empty dictionary on failure.
    """
    requirements_file = os.path.join(os.getcwd(), "requirements.txt")
    result: dict[str, LockGitInfo] = {}
    if not os.path.isfile(requirements_file):
        if not create_requirements_file(requirements_file):
            logger.error(
                "Failed to create requirements file; unable to parse git dependencies."
            )
            return result
    git_pattern = re.compile(
        r"(?P<name>[\w\-]+) @ git\+(?P<url>[^@]+)@(?P<hash>[a-f0-9]+)"
    )

    try:
        with open(requirements_file, "r") as f:
            for line in f:
                line = line.strip()
                match = git_pattern.search(line)
                if match:
                    package_name = match.group("name")
                    result[package_name] = {
                        "url": match.group("url"),
                        "commit": match.group("hash"),
                    }
    except FileNotFoundError:
        logger.error(f"Requirements file not found: {requirements_file}")
        return result
    except IOError as e:
        logger.error(f"Error reading requirements file: {e}")
        return result
    return result


def _load_and_parse_data() -> dict[str, LockGitInfo]:
    """
    Loads and parses pyproject.toml, lock data, and git packages.

    Returns:
        A tuple containing the parsed TOML data and git packages.

    Raises:
        FileNotFoundError: If 'pyproject.toml' is not found.
        tomllib.TOMLDecodeError: If there's an error decoding 'pyproject.toml'.
        Exception: If there's any other unexpected error.
    """
    try:
        with open(os.path.join(os.getcwd(), "pyproject.toml"), "rb") as file:
            toml_data = tomllib.load(file)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"pyproject.toml not found: {e}") from e
    except tomllib.TOMLDecodeError as e:
        raise tomllib.TOMLDecodeError(f"Error decoding pyproject.toml: {e}") from e
    except Exception as e:
        raise Exception(
            f"An unexpected error occurred while loading pyproject.toml: {e}"
        ) from e

    lock_data: dict[str, LockGitInfo] = _parse_git_requirements()
    git_packages: dict[str, LockGitInfo] = _parse_git_packages(toml_data, lock_data)

    return git_packages


def get_plugin_packages() -> dict[str, "PluginPackage"]:
    """
    Retrieves information about installed plugin packages, combining data from pyproject.toml, lock data, and package metadata.
    """
    from importlib.metadata import entry_points
    from nomad_plugin_tests.parsing import PluginPackage
    from nomad_plugin_tests.cli import get_git_url

    plugin_packages: dict[str, PluginPackage] = {}

    git_packages = _load_and_parse_data()

    plugin_entry_points = entry_points(group="nomad.plugin")

    for entry_point in plugin_entry_points:
        try:
            key = entry_point.value
            package_name = entry_point.value.split(".", 1)[0].split(":", 1)[0]
            package_metadata = entry_point.dist.metadata

            url_list: list[str] = package_metadata.get_all("Project-URL") or []
            url_dict: dict[str, str] = {}
            for url in url_list:
                try:
                    name, value = url.split(",", 1)
                    url_dict[name.lower()] = value.strip()
                except ValueError:
                    print(f"Warning: Invalid Project-URL format: {url}")

            if package_name not in plugin_packages:
                plugin_package = PluginPackage(
                    name=package_name,
                    description=package_metadata.get("Summary"),
                    version=entry_point.dist.version,
                    homepage=url_dict.get("homepage"),
                    documentation=url_dict.get("documentation"),
                    repository=url_dict.get("repository"),
                    entry_points=[key],
                )

                git_package_name = plugin_package.name.replace("_", "-")
                git_info = git_packages.get(git_package_name)

                if git_info:
                    plugin_package.github_url = git_info["url"]
                    plugin_package.commit_hash = git_info["commit"]
                else:
                    plugin_package.github_url = get_git_url(plugin_package)
                    plugin_package.commit_hash = None

                plugin_packages[package_name] = plugin_package
        except Exception as e:
            print(f"Error processing plugin {entry_point.name}: {e}")

    return plugin_packages

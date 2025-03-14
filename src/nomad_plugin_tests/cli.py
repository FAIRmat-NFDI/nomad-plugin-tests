import click
import sys
import logging
import multiprocessing
import os
import tempfile

from nomad_plugin_tests.config import TESTS_TO_RUN
from nomad_plugin_tests.parsing import get_plugin_packages, PluginPackage
from nomad_plugin_tests.process import run_command

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def is_valid_github_url(url: str | None) -> bool:
    """
    Checks if a given URL is a valid GitHub URL. Specifically, validates that
    it's not None and that it contains "github.com".
    """
    return url is not None and "github.com" in url


def get_git_url(package: "PluginPackage") -> str | None:
    """
    Prioritizes and constructs a GitHub URL from various package sources,
    ensuring it ends with ".git" for compatibility.

    Args:
        package: A dictionary (or similar structure) containing potential GitHub URL sources
                 (homepage, repository, github_url).

    Returns:
        A string containing the validated GitHub URL if found; otherwise, None.
        Returns None if all inputs are None or invalid.
    """

    github_url: str | None = None

    # Prioritize github_url (most direct indicator)
    if package.github_url:
        github_url = package.github_url
        if not github_url.endswith(".git"):
            github_url = f"{github_url}.git"
        if not is_valid_github_url(github_url):
            github_url = None

    # Then repository
    if (
        github_url is None
        and package.repository
        and is_valid_github_url(package.repository)
    ):
        github_url = package.repository

    # Finally homepage
    if (
        github_url is None
        and package.homepage
        and is_valid_github_url(package.homepage)
    ):
        github_url = package.homepage

    return github_url


def checkout_tag(repo_path: str, tag_name: str, package_logger) -> bool:
    """Fetches a specific tag from the remote repository."""
    checkout_command = [
        "git",
        "checkout",
        f"{tag_name}",
        "-b",
        f"{tag_name}-branch",
    ]
    if run_command(checkout_command, cwd=repo_path, package_logger=package_logger):
        package_logger.debug(f"Successfully fetched tag '{tag_name}'.")
        return True
    else:
        package_logger.error(f"Failed to fetch tag '{tag_name}'.")
        return False


def clone_and_checkout(package: "PluginPackage", temp_dir: str, package_logger) -> bool:
    """
    Clones a Git repository, fetches all branches, and checks out a specific commit hash or tag based on package configuration.
    Also initializes and updates Git submodules.

    Args:
        package: The PluginPackage object containing repository information.
        temp_dir: The directory to clone the repository into.

    Returns:
        True if the entire process was successful, False otherwise.
    """
    # 1. Clone the repository
    clone_command = ["git", "clone", "--depth", "1", package.github_url, temp_dir]
    if not run_command(clone_command, cwd=None, package_logger=package_logger):
        package_logger.error(f"Failed to clone repository for '{package.name}'.")
        return False

    # 2. Checkout commit hash or tag
    checkout_successful = False
    if package.commit_hash:
        fetch_command = ["git", "fetch", "origin", package.commit_hash]
        checkout_command = ["git", "checkout", package.commit_hash]
        if run_command(
            fetch_command, cwd=temp_dir, package_logger=package_logger
        ) and run_command(
            checkout_command, cwd=temp_dir, package_logger=package_logger
        ):
            package_logger.info(
                f"Checked out commit '{package.commit_hash}' successfully for '{package.name}'."
            )
            checkout_successful = True
        else:
            package_logger.error(
                f"Failed to check out commit '{package.commit_hash}' for '{package.name}'."
            )

    if (
        not package.commit_hash or not checkout_successful
    ):  # Handle tag checkout only if commit hash checkout failed (or if there was no commit hash)
        version_tag = (
            package.version
            if package.version is not None and ".dev" not in package.version
            else None
        )

        if version_tag:
            # Try with "v" prefix first
            tag_name_v = f"v{version_tag}"
            tag_name_no_v = version_tag
            fetch_command = ["git", "fetch", "origin", "--tags"]
            if run_command(fetch_command, cwd=temp_dir, package_logger=package_logger):
                if tag_name_v != "v0.0.0" and checkout_tag(
                    temp_dir, tag_name_v, package_logger
                ):
                    checkout_successful = True
                elif tag_name_no_v != "0.0.0" and checkout_tag(
                    temp_dir, tag_name_no_v, package_logger
                ):
                    checkout_successful = True
        elif package.version and ".dev" in package.version:
            package_logger.warning(
                f"Skipping checkout for dev version '{package.version}' for '{package.name}'."
            )
            checkout_successful = True  # Consider this successful to proceed, though no actual checkout happened

        else:
            package_logger.warning(
                f"No commit_hash or valid tag found for '{package.name}'. Skipping checkout."
            )
            checkout_successful = True  # Proceed, but no checkout happened.
    return checkout_successful


# --- Main CLI Logic ---
def clone_and_test_package(package: "PluginPackage"):
    package_name = package.name
    log_dir = f"logs/{package_name}"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "test_output.log")

    # --- Logger Redirection ---
    # Create a package-specific logger
    package_logger = logging.getLogger(package_name)
    package_logger.setLevel(logging.INFO)

    logging.getLogger().handlers.clear()

    # Create a handler to write log messages
    log_handler = logging.FileHandler(log_file_path)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    log_handler.setFormatter(formatter)
    package_logger.addHandler(log_handler)

    try:
        package_logger.info(f"Package info: {package}")
        if package.github_url is None:
            package_logger.warning(
                f"No GitHub URL provided for package '{package.name}', skipping."
            )
            return

        with tempfile.TemporaryDirectory() as temp_dir:
            if not clone_and_checkout(package, temp_dir, package_logger):
                return

            package_logger.info(f"Installing dev dependencies for '{package.name}'...")

            venv = os.path.join(temp_dir, "venv")
            venv_command = [
                "uv",
                "venv",
                "-p",
                "3.12",
                "--seed",
                venv,
            ]
            if not run_command(venv_command, package_logger=package_logger):
                package_logger.error(f"Failed to create venv for '{package.name}'")
                return

            package_logger.info(f"Successfully created venv for '{package.name}'.")

            python_path = os.path.join(venv, "bin", "python")

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
            if not run_command(
                install_command, cwd=os.getcwd(), package_logger=package_logger
            ):
                package_logger.error(
                    f"Failed to install distro dependencies for '{package.name}'"
                )
                return

            package_logger.info(
                f"Successfully installed distro dependencies for '{package.name}'."
            )

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
            if not run_command(
                install_command, cwd=temp_dir, package_logger=package_logger
            ):
                package_logger.error(
                    f"Failed to install dev dependencies for '{package.name}'"
                )
                return

            package_logger.info(
                f"Successfully installed dev dependencies for '{package.name}'."
            )

            package_logger.info(f"Running pytest for '{package.name}'")

            pytest_command = [python_path, "-m", "pytest", "-p", "no:warnings"]

            if test_folder := TESTS_TO_RUN.get(package.name):
                pytest_command.append(os.path.join(temp_dir, test_folder))
            else:
                pytest_command.append(temp_dir)

            if not run_command(
                pytest_command, cwd=temp_dir, package_logger=package_logger
            ):
                package_logger.error(f"Tests failed for '{package.name}'")
            else:
                package_logger.info(f"Tests passed for '{package.name}'.")
                return True

            return False
    finally:
        package_logger.removeHandler(log_handler)  # Prevent memory leaks
        log_handler.close()


def split_packages(
    packages_to_test: list["PluginPackage"], ci_node_total: int, ci_node_index: int
) -> list["PluginPackage"]:
    """
    Splits a list of packages into sublists based on CI node configuration.

    Args:
        packages_to_test: A list of PluginPackage objects to split.
        ci_node_total: The total number of CI nodes.
        ci_node_index: The index of the current CI node (1-based).

    Returns:
        A list of PluginPackage objects assigned to the current CI node.
    """
    packages_per_node = (len(packages_to_test) + ci_node_total - 1) // ci_node_total
    start_index = (ci_node_index - 1) * packages_per_node

    if ci_node_index == ci_node_total:
        return packages_to_test[start_index:]

    end_index = start_index + packages_per_node
    return packages_to_test[start_index:end_index]


def run_tests_parallel(packages_to_test: list["PluginPackage"]):
    passed_packages = []
    failed_packages = []
    os.makedirs("logs", exist_ok=True)

    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        results = pool.map(clone_and_test_package, packages_to_test)

    for i, package in enumerate(packages_to_test):
        package_name = package.name
        if results[i]:
            passed_packages.append(package_name)
        else:
            failed_packages.append(package_name)

    return passed_packages, failed_packages


def output_package_logs(packages_to_test: list["PluginPackage"]):
    """Outputs the contents of each package's log file to the stream."""
    for package in packages_to_test:
        package_name = package.name
        log_file_path = f"logs/{package_name}/test_output.log"
        try:
            with open(log_file_path, "r") as log_file:
                log_contents = log_file.read()
            print(f"\n--- Log Output for {package_name} ---\n{log_contents}")
        except FileNotFoundError:
            logger.error(
                f"Log file not found for package: {package_name} at {log_file_path}"
            )
        except Exception as e:
            logger.error(f"Error reading log file for package {package_name}: {e}")


@click.command()
@click.option(
    "--plugins-to-skip",
    envvar="PLUGIN_TESTS_PLUGINS_TO_SKIP",
    help="Comma-separated list of plugin names skip tests.",
)
@click.option(
    "--ci-node-total",
    type=int,
    envvar="PLUGIN_TESTS_CI_NODE_TOTAL",
    default=1,
    help="Total number of CI nodes.",
)
@click.option(
    "--ci-node-index",
    type=int,
    envvar="PLUGIN_TESTS_CI_NODE_INDEX",
    default=1,
    help="Index of the current CI node (1-based).",
)
def test_plugins(plugins_to_skip: str, ci_node_total: int, ci_node_index: int) -> None:
    """
    Tests a specified list of plugins using a CI-aware split.
    """

    plugin_packages = get_plugin_packages()
    plugins_to_skip_list = (
        [p.strip() for p in plugins_to_skip.split(",")] if plugins_to_skip else []
    )  # Split and strip whitespace
    packages_to_test = [
        package
        for name, package in plugin_packages.items()
        if name not in plugins_to_skip_list
    ]

    packages_to_test = split_packages(packages_to_test, ci_node_total, ci_node_index)
    if not packages_to_test:
        print("No plugins found to test based on the provided names.")
        sys.exit(0)

    passed_packages, failed_packages = run_tests_parallel(packages_to_test)

    output_package_logs(packages_to_test)

    if passed_packages:
        print(f"Tests passed for packages: {', '.join(passed_packages)}")
    else:
        print("No packages passed the tests.")

    if failed_packages:
        print(f"Tests failed for packages: {', '.join(failed_packages)}")
        sys.exit(1)
    else:
        print("No packages failed the tests.")


if __name__ == "__main__":
    test_plugins()

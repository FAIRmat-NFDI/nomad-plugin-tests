import click
import sys
import logging
import multiprocessing
import os
import tempfile

from nomad_plugin_tests import git
from nomad_plugin_tests.errors import PackageTestError
from nomad_plugin_tests.package_tester import (
    create_virtual_environment,
    install_distro_dependencies,
    install_package_dependencies,
    run_pytest,
)
from nomad_plugin_tests.parsing import get_plugin_packages, PluginPackage

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def setup_logger(
    package_name: str, log_dir: str
) -> tuple[logging.Logger, logging.FileHandler]:
    """Sets up a logger for a given package, directing output to a file.

    Args:
        package_name: The name of the package.
        log_dir: The directory where the log file should be stored.

    Returns:
        A tuple containing the logger and the log handler.
    """
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "test_output.log")

    logging.getLogger().handlers.clear()

    logger = logging.getLogger(package_name)
    logger.setLevel(logging.INFO)

    log_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

    return logger, log_handler


def clone_and_test_package(package: "PluginPackage") -> bool:
    package_name = package.name
    log_dir = f"logs/{package_name}"
    package_logger, log_handler = setup_logger(package_name, log_dir)
    if not package.github_url:
        package_logger.warning(
            f"No GitHub URL provided for package '{package_name}', skipping."
        )
        return False

    try:
        package_logger.info(f"Starting test for package: {package}")
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                if not git.clone_and_checkout(package, temp_dir, package_logger):
                    raise PackageTestError(
                        f"Failed to clone and checkout '{package_name}'"
                    )

                venv = os.path.join(temp_dir, "venv")
                create_virtual_environment(
                    venv_path=venv, package_logger=package_logger
                )
                python_path = os.path.join(venv, "bin", "python")

                install_distro_dependencies(
                    python_path=python_path, package_logger=package_logger
                )
                install_package_dependencies(
                    temp_dir=temp_dir,
                    python_path=python_path,
                    package_logger=package_logger,
                )

                run_pytest(
                    temp_dir=temp_dir,
                    package=package,
                    python_path=python_path,
                    package_logger=package_logger,
                )
                package_logger.info(f"Tests passed for '{package_name}'.")
                return True

            except PackageTestError as e:
                package_logger.error(f"Package test failed for '{package_name}': {e}")
                return False
            except Exception as e:
                package_logger.exception(
                    f"An unexpected error occurred during testing '{package_name}': {e}"
                )
                return False
    finally:
        package_logger.removeHandler(log_handler)
        log_handler.close()


def split_packages(
    packages_to_test: list[PluginPackage], ci_node_total: int, ci_node_index: int
) -> list[PluginPackage]:
    """
    Splits a list of packages into sublists based on CI node configuration, ensuring
    even distribution and no overlap between nodes.

    Args:
        packages_to_test: A list of PluginPackage objects to split.
        ci_node_total: The total number of CI nodes.
        ci_node_index: The index of the current CI node (1-based).

    Returns:
        A list of PluginPackage objects assigned to the current CI node.
    """
    if ci_node_total <= 0 or ci_node_index <= 0 or ci_node_index > ci_node_total:
        raise ValueError(
            "Invalid CI node configuration: ci_node_total and ci_node_index must be positive, and ci_node_index must be less than or equal to ci_node_total."
        )

    num_packages = len(packages_to_test)
    packages_per_node = num_packages // ci_node_total
    remainder = num_packages % ci_node_total

    start_index = (ci_node_index - 1) * packages_per_node + min(
        ci_node_index - 1, remainder
    )
    end_index = (
        start_index + packages_per_node + (1 if ci_node_index <= remainder else 0)
    )

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
        and package.package_name not in plugins_to_skip_list
    ]

    packages_to_test = split_packages(packages_to_test, ci_node_total, ci_node_index)
    if not packages_to_test:
        print("No plugins found to test based on the provided names.")
        sys.exit(0)

    passed_packages, failed_packages = run_tests_parallel(packages_to_test)

    output_package_logs(packages_to_test)

    if plugins_to_skip_list:
        print(f"Tests skipped for packages: {', '.join(plugins_to_skip_list)}")

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

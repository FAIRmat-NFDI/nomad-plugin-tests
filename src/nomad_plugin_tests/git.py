from typing import TYPE_CHECKING

from nomad_plugin_tests.process import run_command

if TYPE_CHECKING:
    from nomad_plugin_tests.parsing import PluginPackage


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

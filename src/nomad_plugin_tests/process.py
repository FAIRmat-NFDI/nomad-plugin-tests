import subprocess
import logging

logger = logging.getLogger(__name__)


def run_command(command, cwd=None, package_logger=None):
    """Run a command using subprocess."""
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
        command_logger = package_logger or logger

        if result.stdout:
            command_logger.info(result.stdout)
        if result is None or result.returncode != 0 or result.returncode == 5:
            # return code 5 is pytest exit code for no tests
            command_logger.error(
                f"Command '{' '.join(command)}' failed. Return code: {result.returncode if result else 'None'}, "
                f"stdout: {result.stdout if result else 'None'}, stderr: {result.stderr if result else 'None'}"
            )
            return False
        else:
            command_logger.info(f"Command '{' '.join(command)}' executed successfully.")
        return result
    except Exception as e:
        logger.error(f"Error running command {command}: {e}")
        return None


def create_requirements_file(requirements_file: str) -> bool:
    """Creates a requirements.txt file using `uv export`."""
    export_command = [
        "uv",
        "export",
        "--frozen",
        "--quiet",
        "--no-hashes",
        "--no-emit-project",
        "--extra",
        "plugins",
        "-o",
        requirements_file,
    ]
    import os

    if not run_command(export_command, cwd=os.getcwd()):
        logger.error("Failed to export distro dependencies")
        return False
    return True

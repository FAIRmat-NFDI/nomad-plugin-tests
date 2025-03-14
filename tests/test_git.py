from unittest.mock import MagicMock
from nomad_plugin_tests.git import checkout_tag, clone_and_checkout
from nomad_plugin_tests.parsing import PluginPackage


def test_clone_and_checkout_success_commit_hash(monkeypatch):
    package = PluginPackage(
        name="test_package",
        github_url="https://github.com/test/repo.git",
        commit_hash="12345",
    )
    temp_dir = "/tmp/test_dir"
    package_logger = MagicMock()

    mock_run_command = MagicMock(return_value=True)
    monkeypatch.setattr("nomad_plugin_tests.git.run_command", mock_run_command)

    result = clone_and_checkout(package, temp_dir, package_logger)

    assert result is True
    assert mock_run_command.call_count == 3  # clone, fetch, checkout
    mock_run_command.assert_any_call(
        ["git", "clone", "--depth", "1", "https://github.com/test/repo.git", temp_dir],
        cwd=None,
        package_logger=package_logger,
    )
    mock_run_command.assert_any_call(
        ["git", "fetch", "origin", "12345"], cwd=temp_dir, package_logger=package_logger
    )
    mock_run_command.assert_any_call(
        ["git", "checkout", "12345"], cwd=temp_dir, package_logger=package_logger
    )


def test_clone_and_checkout_fail_clone(monkeypatch):
    package = PluginPackage(
        name="test_package",
        github_url="https://github.com/test/repo.git",
        commit_hash="12345",
    )
    temp_dir = "/tmp/test_dir"
    package_logger = MagicMock()

    mock_run_command = MagicMock()
    mock_run_command.side_effect = [False, True, True]
    monkeypatch.setattr("nomad_plugin_tests.git.run_command", mock_run_command)

    result = clone_and_checkout(package, temp_dir, package_logger)

    assert result is False
    assert mock_run_command.call_count == 1  # Only clone is attempted
    mock_run_command.assert_called_once_with(
        ["git", "clone", "--depth", "1", "https://github.com/test/repo.git", temp_dir],
        cwd=None,
        package_logger=package_logger,
    )
    package_logger.error.assert_called_once()  # Check if the error was logged.


def test_clone_and_checkout_success_tag(monkeypatch):
    package = PluginPackage(
        name="test_package",
        github_url="https://github.com/test/repo.git",
        version="1.2.3",
    )
    temp_dir = "/tmp/test_dir"
    package_logger = MagicMock()

    mock_run_command = MagicMock()
    mock_run_command.side_effect = [True, True, True]
    monkeypatch.setattr("nomad_plugin_tests.git.run_command", mock_run_command)

    mock_checkout_tag = MagicMock(return_value=True)
    monkeypatch.setattr("nomad_plugin_tests.git.checkout_tag", mock_checkout_tag)

    result = clone_and_checkout(package, temp_dir, package_logger)

    assert result is True
    assert mock_run_command.call_count == 2  # clone, fetch tags
    mock_run_command.assert_any_call(
        ["git", "clone", "--depth", "1", "https://github.com/test/repo.git", temp_dir],
        cwd=None,
        package_logger=package_logger,
    )

    mock_checkout_tag.assert_called_once()


def test_clone_and_checkout_no_commit_or_tag(monkeypatch):
    package = PluginPackage(
        name="test_package", github_url="https://github.com/test/repo.git"
    )
    temp_dir = "/tmp/test_dir"
    package_logger = MagicMock()

    mock_run_command = MagicMock(return_value=True)
    monkeypatch.setattr("nomad_plugin_tests.git.run_command", mock_run_command)

    result = clone_and_checkout(package, temp_dir, package_logger)

    assert result is True
    assert mock_run_command.call_count == 1  # Only clone is called
    package_logger.warning.assert_called()  # Warning should be raised because no checkout happened.


def test_checkout_tag_success(monkeypatch):
    repo_path = "/tmp/test_repo"
    tag_name = "v1.0.0"
    package_logger = MagicMock()

    mock_run_command = MagicMock(return_value=True)
    monkeypatch.setattr("nomad_plugin_tests.git.run_command", mock_run_command)

    result = checkout_tag(repo_path, tag_name, package_logger)

    assert result is True
    mock_run_command.assert_called_once_with(
        [
            "git",
            "checkout",
            "v1.0.0",
            "-b",
            "v1.0.0-branch",
        ],
        cwd=repo_path,
        package_logger=package_logger,
    )
    package_logger.debug.assert_called_once()


def test_checkout_tag_failure(monkeypatch):
    repo_path = "/tmp/test_repo"
    tag_name = "v1.0.0"
    package_logger = MagicMock()

    mock_run_command = MagicMock(return_value=False)
    monkeypatch.setattr("nomad_plugin_tests.git.run_command", mock_run_command)

    result = checkout_tag(repo_path, tag_name, package_logger)

    assert result is False
    mock_run_command.assert_called_once_with(
        [
            "git",
            "checkout",
            "v1.0.0",
            "-b",
            "v1.0.0-branch",
        ],
        cwd=repo_path,
        package_logger=package_logger,
    )
    package_logger.error.assert_called_once()


def test_clone_and_checkout_dev_version(monkeypatch):
    package = PluginPackage(
        name="test_package",
        github_url="https://github.com/test/repo.git",
        version="1.2.3.dev1",
    )
    temp_dir = "/tmp/test_dir"
    package_logger = MagicMock()

    mock_run_command = MagicMock(return_value=True)
    monkeypatch.setattr("nomad_plugin_tests.git.run_command", mock_run_command)

    result = clone_and_checkout(package, temp_dir, package_logger)

    assert result is True
    assert mock_run_command.call_count == 1  # Only clone
    package_logger.warning.assert_called()  # warning should be called.

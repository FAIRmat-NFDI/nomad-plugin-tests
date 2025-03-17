# NOMAD Plugin Tests

A command-line tool for unit testing NOAMD plugin packages, particularly designed for continuous integration (CI) environments.

## Features

- Automated cloning of plugin repositories from GitHub.
- Dependency installation within isolated virtual environments using `uv`.
- Execution of pytest tests within the isolated environment.
- CI-aware splitting of plugin tests across multiple nodes.
- Support for skipping specific plugins during testing.
- Detailed logging of test results and errors.

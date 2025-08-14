import pytest

from nomad_plugin_tests.cli import split_packages
from nomad_plugin_tests.parsing import PluginPackage


@pytest.mark.parametrize(
    "packages, ci_node_total, ci_node_index, expected_result",
    [
        (
            [PluginPackage(f"Package {i}") for i in range(6)],
            3,
            1,
            [PluginPackage("Package 0"), PluginPackage("Package 1")],
        ),
        (
            [PluginPackage(f"Package {i}") for i in range(6)],
            3,
            2,
            [PluginPackage("Package 2"), PluginPackage("Package 3")],
        ),
        (
            [PluginPackage(f"Package {i}") for i in range(6)],
            3,
            3,
            [PluginPackage("Package 4"), PluginPackage("Package 5")],
        ),
        (
            [PluginPackage(f"Package {i}") for i in range(7)],
            3,
            1,
            [
                PluginPackage("Package 0"),
                PluginPackage("Package 1"),
                PluginPackage("Package 2"),
            ],
        ),
        (
            [PluginPackage(f"Package {i}") for i in range(7)],
            3,
            2,
            [PluginPackage("Package 3"), PluginPackage("Package 4")],
        ),
        (
            [PluginPackage(f"Package {i}") for i in range(7)],
            3,
            3,
            [PluginPackage("Package 5"), PluginPackage("Package 6")],
        ),
        (
            [PluginPackage(f"Package {i}") for i in range(2)],
            4,
            1,
            [PluginPackage("Package 0")],
        ),
        (
            [PluginPackage(f"Package {i}") for i in range(2)],
            4,
            2,
            [PluginPackage("Package 1")],
        ),
        (
            [PluginPackage(f"Package {i}") for i in range(2)],
            4,
            3,
            [],
        ),
        (
            [PluginPackage(f"Package {i}") for i in range(2)],
            4,
            4,
            [],
        ),
        (
            [PluginPackage(f"Package {i}") for i in range(5)],
            1,
            1,
            [
                PluginPackage("Package 0"),
                PluginPackage("Package 1"),
                PluginPackage("Package 2"),
                PluginPackage("Package 3"),
                PluginPackage("Package 4"),
            ],
        ),
        (
            [],
            3,
            1,
            [],
        ),
        (
            [],
            3,
            2,
            [],
        ),
        (
            [],
            3,
            3,
            [],
        ),
    ],
)
def test_split_packages(
    packages: list[PluginPackage],
    ci_node_total: int,
    ci_node_index: int,
    expected_result: list[PluginPackage],
):
    result = split_packages(packages, ci_node_total, ci_node_index)
    assert result == expected_result

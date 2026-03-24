from dataclasses import dataclass, field


TESTS_TO_RUN: dict[str, str | list[str]] = {
    "pynxtools": "tests/nomad",
    "pynxtools_apm": ["tests/nomad", "tests/test_nomad_examples.py"],
    "pynxtools_ellips": ["tests/nomad", "tests/test_nomad_examples.py"],
    "pynxtools_em": ["tests/nomad", "tests/test_nomad_examples.py"],
    "pynxtools_mpes": ["tests/nomad", "tests/test_nomad_examples.py"],
    "pynxtools_stm": ["tests/nomad", "tests/test_nomad_examples.py"],
    "pynxtools_spm": ["tests/nomad", "tests/test_nomad_examples.py"],
    "pynxtools_xps": ["tests/nomad", "tests/test_nomad_examples.py"],
    "electronicparsers": "tests",
}


@dataclass(frozen=True)
class Config:
    python_version: str
    plugin_tests: dict[str, str | list[str]] = field(default_factory=lambda: dict(TESTS_TO_RUN))

from dataclasses import dataclass


TESTS_TO_RUN = {
    "pynxtools": "tests/nomad",
    "pynxtools_apm": "tests/nomad",
    "pynxtools_ellips": "tests/nomad",
    "pynxtools_em": "tests/nomad",
    "pynxtools_mpes": "tests/nomad",
    "pynxtools_stm": "tests/nomad",
    "pynxtools_spm": "tests/nomad",
    "pynxtools_xps": "tests/nomad",
    "electronicparsers": "tests",
}


@dataclass(frozen=True)
class Config:
    python_version: str

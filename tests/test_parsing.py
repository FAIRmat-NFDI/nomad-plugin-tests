import pytest

from nomad_plugin_tests.parsing import _extract_dependency_name


@pytest.mark.parametrize(
    "input_string, expected_name",
    [
        # Basic Cases
        ("requests", "requests"),
        ("django-crispy-forms", "django-crispy-forms"),
        ("google_auth_oauthlib", "google_auth_oauthlib"),
        ("zope.interface", "zope.interface"),
        # Version Specifiers
        ("requests>=2.0", "requests"),
        ("django==4.0.1", "django"),
        ("numpy~=1.21.0", "numpy"),
        ("python-dateutil!=2.8.0", "python-dateutil"),
        ("package<1.0", "package"),
        ("multiple>=1.0,<2.0", "multiple"),
        # Comments
        ("flask # web framework", "flask"),
        ("  starlette   # ASGI framework ", "starlette"),
        ("# completely commented out line", ""),
        # Markers
        ("pywin32 ; sys_platform == 'win32'", "pywin32"),
        ("twisted[tls];python_version < '3.8'", "twisted[tls]"),
        (
            " urllib3 ; python_version >= '3' and os_name == 'posix' # comment ",
            "urllib3",
        ),
        # Extras Specifiers (Note: only removes '; extra == ...' marker)
        ("requests[security]", "requests[security]"),
        ("celery[redis, SQS]", "celery[redis, SQS]"),
        ("requests ; extra == 'security'", "requests"),
        ("celery[redis]; extra == 'redis_support'", "celery[redis]"),
        # Git URLs
        ("my-package @ git+https://github.com/org/repo.git@main", "my-package"),
        (
            "another-package @ git+ssh://git@github.com/org/repo2.git@develop",
            "another-package",
        ),
        ("package-with-hyphen @ git+https://....", "package-with-hyphen"),
        (" my_pkg @ git+https://... ", "my_pkg"),
        # Combinations
        ("pandas>=1.3.0 # data analysis", "pandas"),
        ("click == 8.0.0 ; python_version >= '3.7'", "click"),
        ("  rich >= 10.0 ; sys_platform != 'win32' # Needs TTY ", "rich"),
        (
            "complex-pkg>=1.0 @ git+https://github.com/org/complex.git@v1.2.3 ; python_version > '3.8' # latest",
            "complex-pkg",
        ),
        ("another @ git+https://... # with comment", "another"),
        (
            " package [ extra ] @ git+https://... ; marker == 'value' # comment ",
            "package [ extra ]",
        ),
        # Edge Cases
        ("", ""),
        ("    ", ""),
        (";", ""),
        ("#", ""),
        ("@ git+https://...", ""),
        # Whitespace Handling
        ("  whitespace_test == 1.0  ", "whitespace_test"),
        ("git_pkg @ git+https://... ", "git_pkg"),
    ],
)
def test_extract_dependency_name(input_string, expected_name):
    assert _extract_dependency_name(input_string) == expected_name

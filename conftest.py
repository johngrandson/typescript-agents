"""Keep disposable Git fixtures isolated when pytest runs inside a Git hook.

Git exports repository/index/object/config variables to hooks. A subprocess with
another cwd still inherits those bindings. Tests that need Git configuration set
it explicitly after this process-level isolation, including the installer tests.
"""

import os


def pytest_configure(config):
    inherited = {
        key: value for key, value in os.environ.items() if key.startswith("GIT_")
    }
    config._typescript_inherited_git_environment = inherited
    for key in inherited:
        os.environ.pop(key, None)
    os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
    os.environ["GIT_CONFIG_NOSYSTEM"] = "1"


def pytest_unconfigure(config):
    # Another plugin can fail before this plugin captures the environment.
    inherited = getattr(config, "_typescript_inherited_git_environment", None)
    if inherited is None:
        return
    # Preserve callers that use pytest.main() in the same Python process.
    for key in list(os.environ):
        if key.startswith("GIT_"):
            os.environ.pop(key)
    os.environ.update(inherited)

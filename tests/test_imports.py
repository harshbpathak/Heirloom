"""Tests for import extraction and resolution (spec F3 step 1)."""

from core.analysis.imports_parser import (
    extract_import_specs,
    resolve_imports,
    resolve_js_import,
    resolve_py_import,
)

REPO_FILES = {
    "src/app.py",
    "src/utils.py",
    "src/auth/__init__.py",
    "src/auth/session.py",
    "web/index.ts",
    "web/helpers.ts",
    "web/components/Button.tsx",
    "web/components/index.ts",
}


def test_extract_python_specs():
    text = "import os\nfrom src import utils\nfrom .auth import session\nimport a, b\n"
    specs = extract_import_specs(text, "python")
    assert "src" in specs and ".auth" in specs and "a" in specs and "b" in specs


def test_extract_js_specs():
    text = (
        "import x from './helpers';\nimport { a } from \"./components\";\n"
        "const y = require('./utils');\nimport('./lazy');\nimport 'side-effect';\n"
    )
    specs = extract_import_specs(text, "typescript")
    assert (
        "./helpers" in specs
        and "./components" in specs
        and "./utils" in specs
        and "./lazy" in specs
    )


def test_vue_script_block_only():
    text = "<template><div/></template>\n<script>\nimport x from './helpers'\n</script>\n"
    assert extract_import_specs(text, "vue") == ["./helpers"]


def test_resolve_js_relative_with_extension_guess():
    assert resolve_js_import("web/index.ts", "./helpers", REPO_FILES) == "web/helpers.ts"


def test_resolve_js_index_file():
    assert (
        resolve_js_import("web/index.ts", "./components", REPO_FILES) == "web/components/index.ts"
    )


def test_resolve_js_external_ignored():
    assert resolve_js_import("web/index.ts", "react", REPO_FILES) is None


def test_resolve_py_absolute_module():
    assert resolve_py_import("src/app.py", "src.utils", REPO_FILES) == "src/utils.py"


def test_resolve_py_package_init():
    assert resolve_py_import("src/app.py", "src.auth", REPO_FILES) == "src/auth/__init__.py"


def test_resolve_py_symbol_import_falls_back_to_module():
    # "from src.utils import fmt" produces module "src.utils"
    assert resolve_py_import("src/app.py", "src.utils.fmt", REPO_FILES) == "src/utils.py"


def test_resolve_py_relative():
    assert resolve_py_import("src/auth/session.py", "..utils", REPO_FILES) == "src/utils.py"


def test_resolve_py_external_ignored():
    assert resolve_py_import("src/app.py", "os.path", REPO_FILES) is None


def test_resolve_imports_never_self():
    text = "import { x } from './index';"
    assert resolve_imports("web/index.ts", "typescript", text, REPO_FILES) == set()

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "agents" / "pdf_reader"
ALLOWED = {"pdfplumber", "pypdfium2", "PIL", "yaml", "dotenv"}


def test_package_imports_only_allowed_modules():
    for path in sorted(PKG.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    continue
                names = [] if node.module is None else [node.module]
            else:
                continue
            for name in names:
                first = name.split(".")[0]
                assert (
                    first in sys.stdlib_module_names
                    or first in ALLOWED
                    or name.startswith("agents.pdf_reader")
                ), (path.name, name)


def test_no_bank_samples_in_tests():
    folder = Path(__file__).resolve().parent
    banned = "pdf-" + "samples"
    assert not list(folder.rglob("*.pdf"))
    for path in folder.rglob("*.py"):
        assert banned not in path.read_text(encoding="utf-8")

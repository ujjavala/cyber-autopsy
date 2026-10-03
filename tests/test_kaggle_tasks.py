"""Guards on the generated Kaggle task files.

The files in ``kaggle/build/`` are generated, self-contained and pushed to
Kaggle. Two things can go wrong silently: they can drift out of sync with
``data/``, and they can leak gold labels into the prompt. Both are checked
here.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "kaggle" / "build"
BUILD_SCRIPT = ROOT / "scripts" / "build_kaggle_tasks.py"

BUILT = sorted(BUILD_DIR.glob("case_*.py"))


def _load(path: Path):
    """Import a generated task without executing its trailing `.run(...)`."""
    source = path.read_text(encoding="utf-8")
    lines = [
        ln for ln in source.splitlines() if not ln.strip().endswith(".run(kbench.llm)")
    ]
    import types

    module = types.ModuleType(f"built_{path.stem}")
    sys.modules[module.__name__] = module
    try:
        exec(  # noqa: S102
            compile("\n".join(lines), str(path), "exec", dont_inherit=True),
            module.__dict__,
        )
    finally:
        sys.modules.pop(module.__name__, None)
    return module


def test_tasks_have_been_built():
    assert BUILT, "run scripts/build_kaggle_tasks.py"


def test_generated_files_are_in_sync_with_data(tmp_path):
    """Regenerating must produce byte-identical files.

    If this fails, someone edited a generated file by hand or changed data/
    without rebuilding. Either way the pushed benchmark no longer matches the
    dataset it claims to represent.
    """
    before = {p.name: p.read_text(encoding="utf-8") for p in BUILT}
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(BUILD_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    after = {p.name: p.read_text(encoding="utf-8") for p in sorted(BUILD_DIR.glob("case_*.py"))}
    assert before == after, "generated tasks are stale; run scripts/build_kaggle_tasks.py"


@pytest.mark.parametrize("path", BUILT, ids=lambda p: p.stem)
def test_prompt_contains_no_gold_identifiers(path: Path):
    module = _load(path)
    prompt = module.build_user_prompt()
    for node in module.GOLD["nodes"]:
        assert node["id"] not in prompt, f"gold node id {node['id']} leaked into prompt"


@pytest.mark.parametrize("path", BUILT, ids=lambda p: p.stem)
def test_prompt_contains_no_gold_status_block(path: Path):
    module = _load(path)
    prompt = module.build_user_prompt()
    assert json.dumps(module.GOLD) not in prompt
    assert "supports_nodes" not in prompt
    assert "supports_edges" not in prompt
    assert "claim_status" not in prompt


@pytest.mark.parametrize("path", BUILT, ids=lambda p: p.stem)
def test_evidence_fields_are_stripped(path: Path):
    module = _load(path)
    allowed = {
        "evidence_id",
        "timestamp",
        "timestamp_precision",
        "type",
        "content",
        "evidence_strength",
    }
    for item in module.EVIDENCE:
        assert set(item) <= allowed, f"unexpected field exposed: {set(item) - allowed}"


@pytest.mark.parametrize("path", BUILT, ids=lambda p: p.stem)
def test_every_gold_node_cites_available_evidence(path: Path):
    module = _load(path)
    available = module.VALID_EVIDENCE_IDS
    for node in module.GOLD["nodes"]:
        for eid in node["evidence_ids"]:
            assert eid in available, (
                f"{path.stem}: gold node {node['id']} cites {eid}, which the "
                "model is never shown"
            )


@pytest.mark.parametrize("path", BUILT, ids=lambda p: p.stem)
def test_task_is_self_contained(path: Path):
    """No project imports. A pushed task runs with kaggle_benchmarks only.

    Comments may reference the project; code may not import it.
    """
    source = path.read_text(encoding="utf-8")
    imports = set(re.findall(r"^\s*(?:import|from)\s+([\w.]+)", source, re.MULTILINE))
    roots = {i.split(".")[0] for i in imports}
    allowed = {"json", "re", "dataclasses", "kaggle_benchmarks"}
    assert roots <= allowed, f"disallowed imports: {roots - allowed}"


@pytest.mark.parametrize("path", BUILT, ids=lambda p: p.stem)
def test_embedded_scoring_is_verbatim(path: Path):
    """The inlined scoring must be the same text as kaggle/tasks/_scoring.py."""
    scoring = (ROOT / "kaggle" / "tasks" / "_scoring.py").read_text(encoding="utf-8")
    body = scoring[scoring.index("MATCH_THRESHOLD = 0.25") :].rstrip()
    assert body in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", BUILT, ids=lambda p: p.stem)
def test_task_declares_comparability_and_leakage(path: Path):
    source = path.read_text(encoding="utf-8")
    assert "**Comparability.**" in source
    assert "**Leakage.**" in source
    assert "**Scope.**" in source
    assert "direct_comparison" not in source


def test_scoring_module_is_importable_standalone():
    """_scoring.py must not depend on anything in this project."""
    spec = importlib.util.spec_from_file_location(
        "standalone_scoring", ROOT / "kaggle" / "tasks" / "_scoring.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.score_prediction({}, {"nodes": [], "edges": []}, set())["egrs"] == 0.0

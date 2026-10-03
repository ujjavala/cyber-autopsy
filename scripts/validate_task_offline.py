"""Run a generated Kaggle task offline against a stubbed model.

This exercises the whole task file — prompt assembly, response parsing, scoring
and the returned score — without spending a model call or needing live Kaggle
credentials. It is the fastest way to catch a broken generated task before a
push.

Three stub behaviours are available:

    perfect    answers with the gold graph, should score ~100
    lazy       answers with nothing, should score 0
    inventive  answers with fabricated steps, should be heavily penalised

Usage:
    python scripts/validate_task_offline.py kaggle/build/case_001.py
    python scripts/validate_task_offline.py kaggle/build/case_001.py lazy
    python scripts/validate_task_offline.py            # all built tasks, all stubs
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "kaggle" / "build"

import kaggle_benchmarks as kbench  # noqa: E402

STUBS = ("perfect", "lazy", "inventive")


class StubLLM:
    """Minimal stand-in for an LLMChat.

    The package ships no mock, and subclassing the real LLMChat drags in
    provider configuration. The task only ever calls ``prompt``, so that is
    all this provides. The gold graph is injected by the harness, not read
    from the prompt, because the point is to exercise the task plumbing, not
    to simulate a model.
    """

    def __init__(self, behaviour: str, gold: dict, schema_types: dict):
        self.behaviour = behaviour
        self.gold = gold
        self.schema_types = schema_types
        self.calls = 0
        self.last_message = ""

    def prompt(self, message, schema=str, **_kwargs):
        self.calls += 1
        self.last_message = message
        event_cls = self.schema_types["event"]
        rel_cls = self.schema_types["relationship"]

        if self.behaviour == "lazy":
            return schema()

        if self.behaviour == "inventive":
            return schema(
                events=[
                    event_cls(
                        event_id=f"P{i}",
                        description=f"Invented step number {i} with no basis",
                        status="confirmed",
                        evidence_ids=["E-999"],
                    )
                    for i in range(5)
                ],
                relationships=[],
                unknown_steps=[],
                unsupported_steps=[],
            )

        # perfect
        node_to_event = {}
        events = []
        for index, node in enumerate(self.gold["nodes"], start=1):
            event_id = f"P{index}"
            node_to_event[node["id"]] = event_id
            events.append(
                event_cls(
                    event_id=event_id,
                    description=node["label"],
                    status=(
                        "unknown" if node["status"] == "contradicted" else node["status"]
                    ),
                    evidence_ids=list(node["evidence_ids"]),
                )
            )
        relationships = [
            rel_cls(
                source_event_id=node_to_event[edge["source"]],
                target_event_id=node_to_event[edge["target"]],
                relationship="precedes",
            )
            for edge in self.gold["edges"]
        ]
        return schema(
            events=events,
            relationships=relationships,
            unknown_steps=[],
            unsupported_steps=[],
        )


def run_task_file(path: Path, behaviour: str) -> float:
    source = path.read_text(encoding="utf-8")

    # The generated file ends with `<task>.run(kbench.llm)`. Strip that line so
    # the harness controls invocation and can supply the stub.
    lines = [ln for ln in source.splitlines() if not ln.strip().endswith(".run(kbench.llm)")]

    # `@dataclass` resolves `sys.modules[cls.__module__]`, so the task must be
    # executed inside a real module object rather than a bare dict.
    module_name = f"kaggle_task_{path.stem}"
    module = types.ModuleType(module_name)
    sys.modules[module_name] = module
    try:
        # dont_inherit matters: this harness uses `from __future__ import
        # annotations`, and without it the task's `-> float` would be compiled
        # to the string "float", which kbench.task cannot resolve.
        code = compile(
            "\n".join(lines), str(path), "exec", dont_inherit=True
        )
        exec(code, module.__dict__)  # noqa: S102
        namespace = module.__dict__

        task = next(
            value
            for key, value in namespace.items()
            if hasattr(value, "run") and key.startswith("case_")
        )
        stub = StubLLM(
            behaviour,
            namespace["GOLD"],
            {
                "event": namespace["ReconstructedEvent"],
                "relationship": namespace["ReconstructedRelationship"],
            },
        )
        run = task.run(stub)
    finally:
        sys.modules.pop(module_name, None)

    score = run.result if hasattr(run, "result") else run
    if stub.calls != 1:
        raise AssertionError(f"{path.name}: expected one model call, got {stub.calls}")
    return score


def main() -> int:
    args = sys.argv[1:]
    if args:
        paths = [Path(args[0])]
        behaviours = [args[1]] if len(args) > 1 else list(STUBS)
    else:
        paths = sorted(BUILD_DIR.glob("case_*.py"))
        behaviours = list(STUBS)

    if not paths:
        print("no built task files; run scripts/build_kaggle_tasks.py first")
        return 1

    failures = 0
    for path in paths:
        for behaviour in behaviours:
            score = run_task_file(path, behaviour)
            value = float(score) if score is not None else float("nan")
            ok = {
                "perfect": value > 0.9,
                "lazy": value == 0.0,
                "inventive": value < 0.1,
            }[behaviour]
            flag = "ok  " if ok else "FAIL"
            print(f"{flag} {path.name:<16} {behaviour:<10} score={value:.4f}")
            if not ok:
                failures += 1

    if failures:
        print(f"\n{failures} unexpected score(s)")
        return 1
    print("\nAll generated tasks behave as expected offline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""T-0010 / AC-40 Colab comparison. The same file runs on cantus v0.6.0 and on the ticket build.

Protocol: the ticket's "Stage-8 protocol (Colab, AC-40)". Nothing here reads a legacy attribute
of an event, so the recording itself emits no cantus warning on either build.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import warnings
from pathlib import Path

QUERIES = [
    "What is 3 + 4?",
    "What is 12 times 7?",
    "Add 15 and 27, then multiply the result by 2.",
    "What is 9 + 10?",
    "Multiply 6 by 8.",
]
MAX_ITERATIONS = 12
PROBE_PROMPT = 'Reply with exactly this JSON and nothing else: {"probe": "ok"}'
W13_MARK = 'the action key "skill_name"'


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_info() -> dict:
    import importlib.metadata as md

    import cantus

    dist = md.distribution("cantus-agent")
    return {
        "cantus_version": dist.version,
        "cantus_file": cantus.__file__,
        "direct_url": dist.read_text("direct_url.json"),
        "has_tool": hasattr(cantus, "tool"),
        "python": sys.version,
        "platform": platform.platform(),
        "pid": os.getpid(),
    }


def env_info() -> dict:
    import importlib.metadata as md

    info: dict = {}
    for name in ("torch", "transformers", "bitsandbytes", "accelerate", "huggingface_hub",
                 "tokenizers", "safetensors", "pydantic"):
        try:
            info[name] = md.version(name)
        except md.PackageNotFoundError:
            info[name] = None
    try:
        import torch

        info["torch_cuda"] = torch.version.cuda
        info["cuda_available"] = torch.cuda.is_available()
        info["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    except Exception as exc:  # no torch in a local dry run
        info["torch_error"] = f"{type(exc).__name__}: {exc}"
    try:
        info["nvidia_smi"] = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()
    except Exception as exc:
        info["nvidia_smi"] = f"unavailable: {type(exc).__name__}"
    return info


def mirror_fingerprint(model_dir: str, hash_weights: bool = True) -> dict:
    """Identify the weights: the Hub commit recorded by the download, else file hashes."""
    root = Path(model_dir)
    out: dict = {"dir": str(root), "commit_hashes": [], "files": {}}
    for meta in sorted(root.glob(".cache/huggingface/download/**/*.metadata")):
        lines = meta.read_text().splitlines()
        if lines:
            out["commit_hashes"].append(lines[0].strip())
    out["commit_hashes"] = sorted(set(out["commit_hashes"]))
    for path in sorted(p for p in root.iterdir() if p.is_file()):
        heavy = path.suffix in {".safetensors", ".bin"}
        if heavy and not hash_weights:
            out["files"][path.name] = {"size": path.stat().st_size}
            continue
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 22), b""):
                digest.update(chunk)
        out["files"][path.name] = {"size": path.stat().st_size, "sha256": digest.hexdigest()}
    return out


def load_model(root: str):
    """The public 4-bit loader; in Colab it mounts Drive first. No Hub fallback."""
    from cantus.model.loader import mount_drive_and_load

    handle = mount_drive_and_load("E2B", allow_hub_fallback=False, drive_root=root)
    config = handle.model.generation_config
    config.do_sample = False
    config.temperature = None
    config.top_p = None
    config.top_k = None
    assert handle.model.generation_config.do_sample is False
    print("generation_config:", handle.model.generation_config)
    print("warnings.filters after load:")
    for entry in warnings.filters:
        print("  ", entry)
    return handle


class Recorder:
    """Proxy around the model handle: appends every turn to a JSONL file."""

    def __init__(self, handle, path: Path, build: str) -> None:
        self.handle = handle
        self.path = path
        self.build = build
        self.query_index = -1
        self.turn = 0

    def start_query(self, index: int) -> None:
        self.query_index = index
        self.turn = 0

    def generate(self, prompt: str, **kwargs) -> str:
        started = time.time()
        output = self.handle.generate(prompt, **kwargs)
        tokenizer = getattr(self.handle, "tokenizer", None)
        row = {
            "build": self.build,
            "query_index": self.query_index,
            "turn": self.turn,
            "seconds": round(time.time() - started, 3),
            "prompt_chars": len(prompt),
            "output_tokens": len(tokenizer(output)["input_ids"]) if tokenizer else None,
            "prompt": prompt,
            "output": output,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.turn += 1
        return output


def make_tools():
    """The two tools, with the same source on both builds; only the decorator differs."""
    import cantus

    decorator = cantus.tool if hasattr(cantus, "tool") else cantus.skill

    @decorator
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    @decorator
    def multiply(a: int, b: int) -> int:
        """Multiply two integers."""
        return a * b

    return [add, multiply]


def make_agent(model, tools):
    import cantus

    if hasattr(cantus, "tool"):
        return cantus.Agent(model, tools=tools)
    return cantus.Agent(model)  # v0.6.0: the decorator registered the tools globally


def _plain(value):
    try:
        json.dumps(value)
        return value
    except TypeError:
        return repr(value)


def describe_event(event) -> dict:
    fields = {k: _plain(v) for k, v in vars(event).items() if k != "partial_state"}
    return {"type": type(event).__name__, **fields}


def run_query(model: Recorder, tools, index: int, query: str) -> dict:
    model.start_query(index)
    agent = make_agent(model, tools)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        state = agent.run(query, max_iterations=MAX_ITERATIONS)
    events = [describe_event(e) for e in state.stream]
    parse_errors = [
        e for e in events
        if e["type"] == "ValidationErrorObservation" and e.get("validator_name") == "action_parse"
    ]
    error_types: dict = {}
    for e in parse_errors:
        first = str(e.get("feedback", "")).splitlines()[0] if e.get("feedback") else "?"
        error_types[first] = error_types.get(first, 0) + 1
    calls = [
        {"name": e.get("tool_name", e.get("skill_name")), "args": e.get("args")}
        for e in events
        if e["type"] in ("CallToolAction", "CallSkillAction")
    ]
    finals = [e.get("answer") for e in events if e["type"] == "FinalAnswerAction"]
    return {
        "query_index": index,
        "query": query,
        "turns": model.turn,
        "parse_errors": len(parse_errors),
        "error_types": error_types,
        "other_validation_errors": sum(
            1 for e in events
            if e["type"] == "ValidationErrorObservation" and e.get("validator_name") != "action_parse"
        ),
        "tool_calls": calls,
        "tool_errors": sum(1 for e in events if e["type"] == "ToolErrorObservation"),
        "w13": sum(1 for w in caught if W13_MARK in str(w.message)),
        "warning_categories": sorted({w.category.__name__ for w in caught}),
        "final_answer": finals[-1] if finals else None,
        "ended_in_max_iterations": bool(events) and events[-1]["type"] == "MaxIterationsObservation",
        "events": events,
    }


def probe(handle, label: str, out_dir: Path) -> dict:
    """Noise probe: one fixed prompt, generated twice; unrelated to cantus's prompt assembly."""
    outputs = [handle.generate(PROBE_PROMPT) for _ in range(2)]
    result = {
        "label": label,
        "sha256": [_sha256(o.encode("utf-8")) for o in outputs],
        "outputs": outputs,
        "same_within_run": outputs[0] == outputs[1],
    }
    (out_dir / f"probe-{label}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
    return result


def run(build: str, root: str, out_dir: str, handle=None, hash_weights: bool = True) -> dict:
    """Run the five queries on the installed cantus and write the records under ``out_dir``."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    info = {"build": build, "build_info": build_info(), "env": env_info()}
    print(json.dumps(info, indent=1))
    if handle is None:
        handle = load_model(root)
        fingerprint = out / "model-fingerprint.json"
        if not fingerprint.exists():
            started = time.time()
            data = mirror_fingerprint(str(Path(root) / "gemma-4-E2B-it-4bit"), hash_weights)
            fingerprint.write_text(json.dumps(data, indent=1))
            print(f"model fingerprint written ({time.time() - started:.0f}s)")
    info["probe"] = probe(handle, build, out)
    jsonl = out / f"turns-{build}.jsonl"
    if jsonl.exists():
        jsonl.unlink()
    recorder = Recorder(handle, jsonl, build)
    tools = make_tools()
    results = [run_query(recorder, tools, i, q) for i, q in enumerate(QUERIES)]
    info["queries"] = results
    info["total_parse_errors"] = sum(r["parse_errors"] for r in results)
    info["total_w13"] = sum(r["w13"] for r in results)
    (out / f"summary-{build}.json").write_text(json.dumps(info, ensure_ascii=False, indent=1))
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True)
    (out / f"pip-freeze-{build}.txt").write_text(freeze.stdout)
    print(f"\n== {build}: per query ==")
    for r in results:
        print(
            f"[{r['query_index']}] {r['query']!r}: parse_errors={r['parse_errors']} {r['error_types']} "
            f"calls={[(c['name'], c['args']) for c in r['tool_calls']]} w13={r['w13']} "
            f"final={r['final_answer']!r} max_iter={r['ended_in_max_iterations']}"
        )
    print(f"TOTAL parse errors ({build}): {info['total_parse_errors']}; W13: {info['total_w13']}")
    return info


def compare(out_dir: str, baseline: str = "v0.6.0", candidate: str = "ticket") -> None:
    out = Path(out_dir)
    a = json.loads((out / f"summary-{baseline}.json").read_text())
    b = json.loads((out / f"summary-{candidate}.json").read_text())
    print(f"{'query':<48} {baseline:>8} {candidate:>8}")
    for ra, rb in zip(a["queries"], b["queries"]):
        print(f"{ra['query']:<48} {ra['parse_errors']:>8} {rb['parse_errors']:>8}")
    print(f"{'TOTAL action_parse errors':<48} {a['total_parse_errors']:>8} {b['total_parse_errors']:>8}")
    ceiling = MAX_ITERATIONS * len(QUERIES)
    print(f"ceiling per build: {ceiling}")
    print("probe within run:", a["probe"]["same_within_run"], b["probe"]["same_within_run"])
    print("probe across builds identical:", a["probe"]["sha256"] == b["probe"]["sha256"])
    fa = set((out / f"pip-freeze-{baseline}.txt").read_text().splitlines())
    fb = set((out / f"pip-freeze-{candidate}.txt").read_text().splitlines())
    print("pip freeze differences:", sorted(fa ^ fb))
    print("pids:", a["build_info"]["pid"], b["build_info"]["pid"])
    print("builds:", a["build_info"]["has_tool"], b["build_info"]["has_tool"], b["build_info"]["direct_url"])
    holds = b["total_parse_errors"] <= a["total_parse_errors"]
    print("AC-40 count criterion (candidate <= baseline):", holds)


class StubHandle:
    """Local dry run only: scripted outputs, no tokenizer, no GPU."""

    tokenizer = None

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str, **kwargs) -> str:
        if prompt == PROBE_PROMPT:
            return '{"probe": "ok"}'
        self.calls += 1
        script = [
            '{"thought": "t", "action": {"tool_name": "add", "args": {"a": 3, "b": 4}}}',
            '{"thought": "t", "action": {"skill_name": "add", "args": {"a": 3, "b": 4}}}',
            "not json at all",
            '{"thought": "t", "action": {"skill_name": "nope", "args": {}}}',
            '{"thought": "cut", "action": {"tool_name": "add", "args": {"a": 3',
            '{"thought": "done", "action": {"final_answer": "7"}}',
        ]
        return script[(self.calls - 1) % len(script)]


if __name__ == "__main__":
    label, target = sys.argv[1], sys.argv[2]
    run(label, "unused", target, handle=StubHandle())

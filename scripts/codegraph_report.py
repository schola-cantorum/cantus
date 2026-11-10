#!/usr/bin/env python3
"""Render a version-controllable report from a CodeGraph index.

CodeGraph (https://github.com/colbymchenry/codegraph) keeps its knowledge
graph in ``.codegraph/codegraph.db``, a machine-local SQLite file that is
deliberately git-ignored. This script reads that database (read-only) and
writes two text artifacts that *can* be committed and diffed over time:

    docs/codegraph/README.md               human-readable analysis (zh-TW)
    docs/codegraph/codegraph-summary.json  machine-readable metrics

Usage (from the repo root):

    DO_NOT_TRACK=1 npx -y @colbymchenry/codegraph@1.6.2 init -y .   # or: index .
    python scripts/codegraph_report.py

Only stdlib is used. Every path written is repo-relative, so the output never
leaks the local checkout path (see scripts/check_no_dev_paths.sh).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

PACKAGE = "cantus"
# Edge kinds that mean "source depends on target" at the code level.
DEP_KINDS = ("calls", "instantiates", "references", "extends", "imports", "decorates")
USE_KINDS = ("calls", "instantiates", "references", "extends", "decorates")
SYMBOL_KINDS = ("function", "method", "class")
TOP_N = 20


def open_db(path: Path) -> sqlite3.Connection:
    # immutable=1 lets us read even while a codegraph daemon holds the WAL.
    uri = f"file:{path.as_posix()}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def module_of(file_path: str) -> str:
    """Map a file to its architectural unit: ``cantus/<subpkg>`` or ``cantus/<file>``."""
    parts = file_path.split("/")
    if parts[0] != PACKAGE:
        return parts[0]
    if len(parts) == 2:
        return f"{PACKAGE}/{Path(parts[1]).stem}"
    return f"{PACKAGE}/{parts[1]}"


def strongly_connected(graph: dict[str, set[str]]) -> list[list[str]]:
    """Tarjan's SCC; returns components with more than one node (i.e. cycles)."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    out: list[list[str]] = []
    counter = 0

    def visit(v: str) -> None:
        nonlocal counter
        index[v] = low[v] = counter
        counter += 1
        stack.append(v)
        on_stack.add(v)
        for w in sorted(graph.get(v, ())):
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                out.append(sorted(comp))

    for v in sorted(graph):
        if v not in index:
            visit(v)
    return sorted(out)


def collect(conn: sqlite3.Connection) -> dict:
    q = conn.execute
    meta = {r["key"]: r["value"] for r in q("SELECT key, value FROM project_metadata")}

    files_by_lang = {
        r["language"]: r["n"]
        for r in q("SELECT language, COUNT(*) n FROM files GROUP BY language ORDER BY n DESC")
    }
    files_by_top = {
        r["top"]: r["n"]
        for r in q(
            "SELECT substr(path, 1, instr(path || '/', '/') - 1) top, COUNT(*) n "
            "FROM files GROUP BY top ORDER BY n DESC"
        )
    }
    nodes_by_kind = {r["kind"]: r["n"] for r in q("SELECT kind, COUNT(*) n FROM nodes GROUP BY kind ORDER BY n DESC")}
    edges_by_kind = {r["kind"]: r["n"] for r in q("SELECT kind, COUNT(*) n FROM edges GROUP BY kind ORDER BY n DESC")}

    pkg_like = f"{PACKAGE}/%"
    marks = ",".join("?" * len(DEP_KINDS))
    cross = q(
        f"""
        SELECT s.file_path sf, t.file_path tf, e.kind kind
        FROM edges e JOIN nodes s ON s.id = e.source JOIN nodes t ON t.id = e.target
        WHERE e.kind IN ({marks}) AND s.file_path != t.file_path
        """,
        DEP_KINDS,
    ).fetchall()

    module_edges: Counter[tuple[str, str]] = Counter()
    test_hits: Counter[str] = Counter()
    for r in cross:
        sf, tf = r["sf"], r["tf"]
        if sf.startswith(f"{PACKAGE}/") and tf.startswith(f"{PACKAGE}/"):
            a, b = module_of(sf), module_of(tf)
            if a != b:
                module_edges[(a, b)] += 1
        if sf.startswith("tests/") and tf.startswith(f"{PACKAGE}/"):
            test_hits[tf] += 1

    graph: dict[str, set[str]] = defaultdict(set)
    for a, b in module_edges:
        graph[a].add(b)
    cycles = strongly_connected(graph)

    modules = sorted({module_of(r["path"]) for r in q("SELECT path FROM files WHERE path LIKE ?", (pkg_like,))})
    fan_in_mod = Counter()
    fan_out_mod = Counter()
    for (a, b) in module_edges:
        fan_out_mod[a] += 1
        fan_in_mod[b] += 1

    use_marks = ",".join("?" * len(USE_KINDS))
    sym_marks = ",".join("?" * len(SYMBOL_KINDS))

    def hotspot(direction: str) -> list[dict]:
        own, other = ("t", "s") if direction == "in" else ("s", "t")
        rows = q(
            f"""
            SELECT {own}.qualified_name name, {own}.kind kind, {own}.file_path file, {own}.start_line line,
                   COUNT(DISTINCT {other}.id) deg,
                   COUNT(DISTINCT CASE WHEN {other}.file_path LIKE 'tests/%' THEN {other}.id END) from_tests
            FROM edges e JOIN nodes s ON s.id = e.source JOIN nodes t ON t.id = e.target
            WHERE e.kind IN ({use_marks}) AND {own}.kind IN ({sym_marks}) AND {own}.file_path LIKE ?
            GROUP BY {own}.id ORDER BY deg DESC, name LIMIT ?
            """,
            (*USE_KINDS, *SYMBOL_KINDS, pkg_like, TOP_N),
        ).fetchall()
        return [dict(r) for r in rows]

    largest_files = [
        dict(r)
        for r in q(
            """
            SELECT n.file_path file, COUNT(*) symbols, MAX(n.end_line) lines
            FROM nodes n WHERE n.file_path LIKE ? AND n.kind IN ('function','method','class')
            GROUP BY n.file_path ORDER BY symbols DESC LIMIT 15
            """,
            (pkg_like,),
        )
    ]

    routes = [dict(r) for r in q("SELECT name, file_path file, start_line line FROM nodes WHERE kind='route' ORDER BY file_path, start_line")]

    inheritance = [
        dict(r)
        for r in q(
            """
            SELECT s.qualified_name child, s.file_path file, t.qualified_name parent
            FROM edges e JOIN nodes s ON s.id = e.source JOIN nodes t ON t.id = e.target
            WHERE e.kind = 'extends' AND s.file_path LIKE ?
            ORDER BY parent, child
            """,
            (pkg_like,),
        )
    ]

    # Public top-level functions/classes in the package that nothing indexed points at.
    unreferenced = [
        dict(r)
        for r in q(
            f"""
            SELECT n.qualified_name name, n.kind kind, n.file_path file, n.start_line line
            FROM nodes n
            WHERE n.file_path LIKE ? AND n.kind IN ('function','class')
              AND n.name NOT LIKE '\\_%' ESCAPE '\\'
              AND NOT EXISTS (
                SELECT 1 FROM edges e WHERE e.target = n.id AND e.kind IN ({use_marks}, 'imports')
              )
            ORDER BY n.file_path, n.start_line
            """,
            (pkg_like, *USE_KINDS),
        )
    ]

    pkg_files = [r["path"] for r in q("SELECT path FROM files WHERE path LIKE ? ORDER BY path", (pkg_like,))]
    untested = [f for f in pkg_files if test_hits[f] == 0 and not f.endswith("__init__.py")]

    return {
        "codegraph_version": meta.get("indexed_with_version"),
        "indexed_at_commit": meta.get("indexed_at_commit"),
        "files_total": sum(files_by_lang.values()),
        "files_by_language": files_by_lang,
        "files_by_top_dir": files_by_top,
        "nodes_by_kind": nodes_by_kind,
        "edges_by_kind": edges_by_kind,
        "modules": modules,
        "module_edges": [
            {"from": a, "to": b, "weight": w} for (a, b), w in sorted(module_edges.items())
        ],
        "module_fan_in": dict(sorted(fan_in_mod.items())),
        "module_fan_out": dict(sorted(fan_out_mod.items())),
        "module_cycles": cycles,
        "hotspots_fan_in": hotspot("in"),
        "hotspots_fan_out": hotspot("out"),
        "largest_files": largest_files,
        "routes": routes,
        "inheritance": inheritance,
        "unreferenced_public_symbols": unreferenced,
        "package_files_without_direct_test_edges": untested,
    }


def mermaid_id(name: str) -> str:
    return name.replace("/", "_").replace(".", "_")


def render_md(d: dict, version: str) -> str:
    L: list[str] = []
    w = L.append
    w("# Cantus 程式碼知識圖譜剖析（CodeGraph）")
    w("")
    w(f"> 由 [CodeGraph](https://github.com/colbymchenry/codegraph) `{version}` 建立索引，")
    commit = (d.get("indexed_at_commit") or "unknown")[:7]
    w(f"> 索引對應 commit `{commit}`。")
    w("> 再以 `scripts/codegraph_report.py` 從 `.codegraph/codegraph.db` 萃取成本文件與")
    w("> [`codegraph-summary.json`](codegraph-summary.json)。資料庫本身是機器本地檔、不進版控；")
    w("> 本頁與 JSON 是可 diff 的快照，重跑步驟見文末〈重現方式〉。")
    w("")
    w("## 1. 總覽")
    w("")
    w(f"- 索引檔案：**{d['files_total']}**（語言：" + "、".join(f"{k} {v}" for k, v in d["files_by_language"].items()) + "）")
    w("- 依頂層目錄：" + "、".join(f"`{k}` {v}" for k, v in d["files_by_top_dir"].items()))
    w(f"- 節點 **{sum(d['nodes_by_kind'].values())}**：" + "、".join(f"{k} {v}" for k, v in d["nodes_by_kind"].items()))
    w(f"- 邊 **{sum(d['edges_by_kind'].values())}**：" + "、".join(f"{k} {v}" for k, v in d["edges_by_kind"].items()))
    w("")
    w("## 2. 套件層級依賴圖（`cantus/*`）")
    w("")
    w("把跨檔的 calls／instantiates／references／extends／imports／decorates 邊折疊到子套件層級；")
    w("箭頭 A → B 代表「A 依賴 B」，標籤是折疊進來的邊數。只畫權重 ≥ 3 的邊以免過密，完整清單在 JSON。")
    w("")
    w("```mermaid")
    w("flowchart LR")
    for m in d["modules"]:
        w(f"    {mermaid_id(m)}[\"{m.removeprefix(PACKAGE + '/')}\"]")
    for e in d["module_edges"]:
        if e["weight"] >= 3:
            w(f"    {mermaid_id(e['from'])} -->|{e['weight']}| {mermaid_id(e['to'])}")
    w("```")
    w("")
    w("| 模組 | Fan-in（被幾個模組依賴） | Fan-out（依賴幾個模組） |")
    w("| --- | ---: | ---: |")
    for m in sorted(d["modules"], key=lambda m: (-d["module_fan_in"].get(m, 0), m)):
        w(f"| `{m}` | {d['module_fan_in'].get(m, 0)} | {d['module_fan_out'].get(m, 0)} |")
    w("")
    w("### 模組間循環依賴")
    w("")
    if d["module_cycles"]:
        w("以下各組模組彼此（直接或間接）互相依賴（Tarjan SCC）。多半來自 lazy import 或型別參照，")
        w("不一定是錯，但代表這些模組無法各自獨立抽換：")
        w("")
        for comp in d["module_cycles"]:
            w("- " + " ⇄ ".join(f"`{m}`" for m in comp))
    else:
        w("未偵測到子套件層級的循環依賴。")
    w("")

    def sym_table(rows: list[dict], label: str, split_tests: bool) -> None:
        extra_h = " | 來自 `cantus/` | 來自 `tests/`" if split_tests else ""
        extra_a = " | ---: | ---:" if split_tests else ""
        w(f"| # | 符號 | 種類 | 位置 | {label}{extra_h} |")
        w(f"| ---: | --- | --- | --- | ---:{extra_a} |")
        for i, r in enumerate(rows, 1):
            loc = f"[{r['file']}:{r['line']}](../../{r['file']}#L{r['line']})"
            extra = f" | {r['deg'] - r['from_tests']} | {r['from_tests']}" if split_tests else ""
            w(f"| {i} | `{r['name']}` | {r['kind']} | {loc} | {r['deg']}{extra} |")
        w("")

    w("## 3. 熱點符號")
    w("")
    w("### 3.1 Fan-in 最高（最多不同符號使用它，改動影響面最大）")
    w("")
    sym_table(d["hotspots_fan_in"], "使用者數", True)
    w("### 3.2 Fan-out 最高（依賴最多不同符號，最可能是協調者／複雜度集中處）")
    w("")
    sym_table(d["hotspots_fan_out"], "依賴數", False)
    w("## 4. 體積最大的檔案（以 function／method／class 數計）")
    w("")
    w("| 檔案 | 符號數 | 約略行數 |")
    w("| --- | ---: | ---: |")
    for r in d["largest_files"]:
        w(f"| [{r['file']}](../../{r['file']}) | {r['symbols']} | {r['lines']} |")
    w("")
    w("## 5. HTTP 路由")
    w("")
    w("| 路由 | 位置 |")
    w("| --- | --- |")
    for r in d["routes"]:
        w(f"| `{r['name']}` | [{r['file']}:{r['line']}](../../{r['file']}#L{r['line']}) |")
    w("")
    w("## 6. 類別繼承（`cantus/` 內）")
    w("")
    by_parent: dict[str, list[str]] = defaultdict(list)
    for r in d["inheritance"]:
        by_parent[r["parent"]].append(r["child"])
    for parent in sorted(by_parent):
        w(f"- `{parent}` ← " + "、".join(f"`{c}`" for c in by_parent[parent]))
    w("")
    w("## 7. 待人工確認的清單")
    w("")
    w("以下兩份清單是**靜態圖譜的推論**，Python 的動態屬性存取、`__getattr__` lazy export、")
    w("decorator 註冊、entry point 與字串式 import 都看不到，因此只是「值得看一眼」而非結論。")
    w("")
    w(f"### 7.1 未被任何已索引程式碼參照的公開 function／class（{len(d['unreferenced_public_symbols'])} 個）")
    w("")
    w("<details><summary>展開清單</summary>")
    w("")
    for r in d["unreferenced_public_symbols"]:
        w(f"- `{r['name']}`（{r['kind']}）— [{r['file']}:{r['line']}](../../{r['file']}#L{r['line']})")
    w("")
    w("</details>")
    w("")
    w(f"### 7.2 沒有任何 `tests/` 符號直接連到的 `cantus/` 檔案（{len(d['package_files_without_direct_test_edges'])} 個，已排除 `__init__.py`）")
    w("")
    w("這不等於沒有測試覆蓋（可能經由其他模組間接覆蓋），而是「沒有測試直接 import／呼叫其中符號」。")
    w("")
    for f in d["package_files_without_direct_test_edges"]:
        w(f"- [{f}](../../{f})")
    w("")
    w("## 重現方式")
    w("")
    w("```bash")
    w("# 1. 建立／重建索引（DO_NOT_TRACK=1 關閉 CodeGraph 匿名 telemetry）")
    w(f"DO_NOT_TRACK=1 npx -y @colbymchenry/codegraph@{version} init -y .")
    w("# 2. 產生本頁與 codegraph-summary.json")
    w("python scripts/codegraph_report.py")
    w("```")
    w("")
    w("`.codegraph/` 會自帶一份 `.gitignore`（忽略資料庫、pid、log），不需要也不應該 commit。")
    w("索引建好後也可直接用 CLI 互動查詢，例如 `codegraph impact Agent`、`codegraph callers load_chat_model`。")
    w("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--db", type=Path, default=Path(".codegraph/codegraph.db"))
    p.add_argument("--out", type=Path, default=Path("docs/codegraph"))
    args = p.parse_args(argv)

    if not args.db.exists():
        print(f"error: {args.db} not found — run `codegraph init -y .` first", file=sys.stderr)
        return 2

    conn = open_db(args.db)
    try:
        data = collect(conn)
    finally:
        conn.close()

    version = data.pop("codegraph_version") or "unknown"
    summary = {"codegraph_version": version, **data}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "codegraph-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "README.md").write_text(render_md(data, version), encoding="utf-8")
    print(f"wrote {args.out / 'README.md'} and {args.out / 'codegraph-summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

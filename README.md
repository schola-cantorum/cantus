# Cantus

> A polyphonic framework for composing LLM agent harnesses — designed for teaching on Google Colab.

Cantus（拉丁文：「歌」「詠」）是一套教學用的 LLM agent 框架，用五種 protocol（Skill / Analyzer / Validator / Workflow / Memory）讓師生在 Google Colab 上組裝 agent，後端搭配 Gemma 4 4-bit 量化模型。

對應中文 LLM 圈把 prompt engineering 稱為「詠唱」的文化梗，Cantus 把 agent 編排視為一場複音歌詠 —— 每個 protocol 是一個聲部，組起來就是一個會回應的 agent。

## Install

```bash
# 釘在固定 tag（推薦 — 適合學生作業期間）
pip install git+https://github.com/schola-cantorum/cantus@v0.1.1

# 跟著 main 走最新（適合老師體驗最新 commit）
pip install git+https://github.com/schola-cantorum/cantus@main

# 釘在某個 commit（bug 重現時）
pip install git+https://github.com/schola-cantorum/cantus@<commit-sha>
```

執行 runtime（Gemma 4 + transformers + bitsandbytes）需額外 extras：

```bash
pip install 'cantus[runtime] @ git+https://github.com/schola-cantorum/cantus@v0.1.1'
```

## 30-second Quickstart

```python
from cantus import skill, Agent, mount_drive_and_load

@skill
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b

model, tokenizer = mount_drive_and_load(variant="gemma-3-4b-it")
agent = Agent.from_skills([add], model=model, tokenizer=tokenizer)

result = agent.run("What is 17 plus 25?")
print(result.final_answer)
```

## 五種 Protocol（一句話介紹）

- **Skill** — 可被 agent 呼叫的函式（tool use）。用 `@skill` 裝飾或繼承 `Skill` 類別。
- **Analyzer** — 把使用者輸入轉成結構化結果，回傳前不進入 agent loop。用 `@analyzer` 或繼承 `Analyzer`。
- **Validator** — 對 agent 輸出做後處理檢驗，回傳 `Result` 決定通過或重試。用 `@validator` 或繼承 `Validator`。
- **Workflow** — 串接多個 skill / analyzer / validator 的固定流程。用 `@workflow` 或繼承 `Workflow`。
- **Memory** — 對話狀態與檢索記憶，內建 `ShortTermMemory`、`BM25Memory`、`EmbeddingMemory`。

## Documentation

完整文件在 [`docs/`](./docs/)：

- [Overview](./docs/overview.md) — 框架架構與設計哲學
- [Quickstart](./docs/quickstart.md) — 從零開始 10 分鐘
- [Protocols](./docs/protocols/) — 五件 protocol 的設計與用法
- [Cookbook](./docs/cookbook/) — 常見模式、錯誤排查、教學技巧
- [llms.txt](./llms.txt) — 給外部 LLM 一次抓的 priming 文件

## License

ECL-2.0 — Educational Community License, Version 2.0. See [`LICENSE`](./LICENSE).

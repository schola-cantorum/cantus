<p align="center">
  <img src="assets/banner_hero.jpeg" alt="Cantus — 用於編排 LLM agent harness 的複音框架">
</p>

<p align="center">
  <a href="https://github.com/schola-cantorum/cantus/releases/tag/v0.1.4"><img alt="release v0.1.4" src="https://img.shields.io/badge/release-v0.1.4-blue"></a>
  <a href="LICENSE"><img alt="license ECL-2.0" src="https://img.shields.io/badge/license-ECL--2.0-green"></a>
  <a href="https://colab.research.google.com/github/schola-cantorum/cantus/blob/v0.1.4/notebooks/task_template.ipynb"><img alt="Open In Colab" src="https://colab.research.google.com/assets/colab-badge.svg"></a>
</p>

<div align="center">

[English](README.md)

</div>

# Cantus

> 為 Google Colab 教學設計、用來編排 LLM agent harness 的複音（polyphonic）框架。

Cantus（拉丁文：*song*、*chant*）是一個以教學為核心的 LLM agent 框架。五個協定（Skill ／ Analyzer ／ Validator ／ Workflow ／ Memory）讓學員與 operator 能在 Google Colab 上組合 agent，背後由 4-bit 量化的 Gemma 4 模型支撐。

中文 LLM 社群把 prompt engineering 稱作「*詠唱*」。Cantus 把 agent 的組合視為一段複音聖詠 —— 每個協定是一條聲部，合起來就形成一個會回唱的 agent。

## 一鍵在 Colab 開啟 —— 5 分鐘入門路徑

體驗 Cantus 最快的方式，是直接啟動 repo 內附的 notebook：

| Notebook | 對象 | 一鍵啟動 |
| --- | --- | --- |
| `notebooks/task_template.ipynb` | 一般使用者 —— 建立你的第一個 agent | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/schola-cantorum/cantus/blob/v0.1.4/notebooks/task_template.ipynb) |
| `notebooks/admin_setup.ipynb` | 管理者 —— 把 Gemma 4 權重鏡像到 Drive（在下游使用者執行前先跑一次） | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/schola-cantorum/cantus/blob/v0.1.4/notebooks/admin_setup.ipynb) |

建議的執行順序與 tag pinning 慣例詳見 [`notebooks/README.md`](./notebooks/README.md)。

## Install

```bash
# Pin to a tag (recommended — reproducible)
pip install git+https://github.com/schola-cantorum/cantus@v0.1.4

# Follow main (latest commit)
pip install git+https://github.com/schola-cantorum/cantus@main

# Pin to a commit SHA (bug reproduction)
pip install git+https://github.com/schola-cantorum/cantus@<commit-sha>
```

Runtime extras（Gemma 4 + transformers + bitsandbytes）需要：

```bash
pip install 'cantus[runtime] @ git+https://github.com/schola-cantorum/cantus@v0.1.4'
```

## 30-second Quickstart

```python
from cantus import skill, Agent, mount_drive_and_load

@skill
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b

model_handle = mount_drive_and_load(variant="E4B")
agent = Agent(model=model_handle)

result = agent.run("What is 17 plus 25?")
print(result.final_answer)
```

<p align="center">
  <img src="assets/banner_protocols.jpeg" alt="Cantus 五協定：Skill、Analyzer、Validator、Workflow、Memory">
</p>

## 五個協定（一句話介紹）

- **Skill** —— agent 可以呼叫的函式（tool use）。以 `@skill` 裝飾或繼承 `Skill` 類別。
- **Analyzer** —— 在進入 agent loop 之前，把使用者輸入轉換成結構化結果。用 `@analyzer` 或繼承 `Analyzer`。
- **Validator** —— 後處理 agent 的輸出，回傳一個 `Result` 決定通過或重試。用 `@validator` 或繼承 `Validator`。
- **Workflow** —— 串接 skills、analyzers、validators 的固定流程。用 `@workflow` 或繼承 `Workflow`。
- **Memory** —— 對話狀態與檢索記憶；內建 `ShortTermMemory`、`BM25Memory`、`EmbeddingMemory`。

## Documentation

完整文件位於 [`docs/`](./docs/)：

- [Overview](./docs/overview.md) —— 架構與設計哲學
- [Quickstart](./docs/quickstart.md) —— 10 分鐘從零打造第一個 agent
- [Protocols](./docs/protocols/) —— 五個協定的設計與使用方式
- [Cookbook](./docs/cookbook/) —— 模式、錯誤處理、教學提示
- [llms.txt](./llms.txt) —— 給外部 LLM 的 priming 文件
- [開發者 LLM Wiki](./docs/llm_wiki/index.md) —— cantus 內部貢獻者知識庫（研究、coding style、架構、未來工作）

## License

ECL-2.0 —— Educational Community License, Version 2.0。詳見 [`LICENSE`](./LICENSE)。

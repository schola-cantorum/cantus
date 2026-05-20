<p align="center">
  <img src="assets/banner_hero.jpeg" alt="Cantus — 用於編排 LLM agent harness 的複音框架">
</p>

<p align="center">
  <a href="https://pypi.org/project/cantus/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/cantus.svg"></a>
  <a href="https://github.com/schola-cantorum/cantus/releases/tag/v0.4.1"><img alt="release v0.4.1" src="https://img.shields.io/badge/release-v0.4.1-blue"></a>
  <a href="LICENSE"><img alt="license ECL-2.0" src="https://img.shields.io/badge/license-ECL--2.0-green"></a>
  <a href="https://colab.research.google.com/github/schola-cantorum/cantus/blob/v0.4.1/notebooks/task_template.ipynb"><img alt="Open In Colab" src="https://colab.research.google.com/assets/colab-badge.svg"></a>
</p>

<div align="center">

[English](README.md)

</div>

# Cantus

> 為 Google Colab 教學設計、用來編排 LLM agent harness 的複音（polyphonic）框架。

Cantus（拉丁文：*song*、*chant*）是一個以教學為核心的 LLM agent 框架。兩個 protocol kind（Skill ／ Memory）加上 hook helper（Analyzer ／ Validator）與 `cantus.workflows` building block，讓學員與 operator 能在 Google Colab 上組合 agent，背後由 4-bit 量化的 Gemma 4 模型支撐。

中文 LLM 社群把 prompt engineering 稱作「*詠唱*」。Cantus 把 agent 的組合視為一段複音聖詠 —— 每個協定是一條聲部，合起來就形成一個會回唱的 agent。

## 一鍵在 Colab 開啟 —— 5 分鐘入門路徑

體驗 Cantus 最快的方式，是直接啟動 repo 內附的 notebook：

| Notebook | 對象 | 一鍵啟動 |
| --- | --- | --- |
| `notebooks/task_template.ipynb` | 一般使用者 —— 建立你的第一個 agent | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/schola-cantorum/cantus/blob/v0.4.1/notebooks/task_template.ipynb) |
| `notebooks/admin_setup.ipynb` | 管理者 —— 把 Gemma 4 權重鏡像到 Drive（在下游使用者執行前先跑一次） | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/schola-cantorum/cantus/blob/v0.4.1/notebooks/admin_setup.ipynb) |

建議的執行順序與 tag pinning 慣例詳見 [`notebooks/README.md`](./notebooks/README.md)。

## Install

```bash
# PyPI（推薦 —— reproducible，不必 clone Git）
pip install cantus==0.4.1

# Git 安裝路徑 —— 用於追蹤 main / feature branch / 特定 commit 的 escape hatch
pip install git+https://github.com/schola-cantorum/cantus@v0.4.1
pip install git+https://github.com/schola-cantorum/cantus@main
pip install git+https://github.com/schola-cantorum/cantus@<commit-sha>
```

Runtime extras（Gemma 4 + transformers + bitsandbytes）需要：

```bash
pip install 'cantus[runtime]==0.4.1'
```

Serve extras（v0.4.0 —— FastAPI app factory；會一併安裝 `fastapi`、`uvicorn`、`pydantic-settings`）：

```bash
pip install cantus[serve]
```

## Serve Quickstart（v0.4.0）

用一個新的 `Registry` 在 `127.0.0.1:8765` 啟動內建的 FastAPI app：

```python
from cantus import serve
from cantus.core.registry import Registry
import uvicorn
app = serve(Registry())
uvicorn.run(app, host="127.0.0.1", port=8765)
```

打 health endpoint 確認 server 已就緒：

```bash
curl http://localhost:8765/health
# {"status":"ok","cantus_version":"0.4.0"}
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

## 多 provider 快速上手（v0.2.1）

Tier 2 ChatModel adapter 讓同一個 Agent 改接 OpenAI、Anthropic、Google Gemini、Groq 或 NVIDIA NIM，不再侷限於本地 Gemma。**把 `ChatModel` 餵給 `Agent` 之前一定要先用 `ChatModelAsHandle` 包一層**——Agent 只認得 Tier 1 `.generate(prompt) -> str` 介面。

OpenAI（`pip install 'cantus[openai]'`，並設定 `OPENAI_API_KEY`）：

```python
from cantus import Agent, ChatModelAsHandle, load_chat_model

chat = load_chat_model("openai/gpt-4o-mini")
agent = Agent(model=ChatModelAsHandle(chat, system="You are terse."))
result = agent.run("What is 17 plus 25?")
print(result.final_answer)
```

Anthropic（`pip install 'cantus[anthropic]'`，並設定 `ANTHROPIC_API_KEY`）：

```python
from cantus import Agent, ChatModelAsHandle, load_chat_model

chat = load_chat_model("anthropic/claude-sonnet-4-6")
agent = Agent(model=ChatModelAsHandle(chat, system="You are terse."))
result = agent.run("What is 17 plus 25?")
print(result.final_answer)
```

Google Gemini（`pip install 'cantus[google]'`，並設定 `GOOGLE_API_KEY`；使用 `google-genai`，**非**舊版 `google-generativeai`）：

```python
from cantus import Agent, ChatModelAsHandle, load_chat_model

chat = load_chat_model("google/gemini-2.0-flash")
agent = Agent(model=ChatModelAsHandle(chat, system="You are terse."))
result = agent.run("What is 17 plus 25?")
print(result.final_answer)
```

Groq（`pip install 'cantus[groq]'`，並設定 `GROQ_API_KEY`）：

```python
from cantus import Agent, ChatModelAsHandle, load_chat_model

chat = load_chat_model("groq/llama-3.3-70b-versatile")
agent = Agent(model=ChatModelAsHandle(chat, system="You are terse."))
result = agent.run("What is 17 plus 25?")
print(result.final_answer)
```

NVIDIA NIM（`pip install 'cantus[openai]'` — NIM 走 OpenAI SDK，因此**不**另開 `cantus[nvidia]` extras；設定 `NVIDIA_API_KEY`）：

```python
from cantus import Agent, ChatModelAsHandle, load_chat_model

chat = load_chat_model("nvidia/meta/llama-3.3-70b-instruct")
agent = Agent(model=ChatModelAsHandle(chat, system="You are terse."))
result = agent.run("What is 17 plus 25?")
print(result.final_answer)
```

`cantus[providers]` 可一次安裝四家主要 adapter（OpenAI / Anthropic / Google / Groq）。NVIDIA NIM 透過 `cantus[openai]` 一併取得，因為 NIM endpoint 與 OpenAI 相容。cantus 在任何 layer **皆不**相依 LiteLLM；Google 的 extras 只裝 `google-genai`（新版統一 Gemini API SDK），**不裝** `google-generativeai`。

<p align="center">
  <img src="assets/banner_protocols.jpeg" alt="Cantus 雙 protocol kind（Skill、Memory）加上 Analyzer ／ Validator hook helper 與 cantus.workflows building block">
</p>

## 雙 protocol kind ＋ hook helper ＋ workflows building block

兩個 protocol kind（cantus 正式註冊與 dispatch 的對象）：

- **Skill** —— agent 可以呼叫的函式（tool use）。以 `@skill` 裝飾或繼承 `Skill` 類別。
- **Memory** —— 對話狀態與檢索記憶；內建 `ShortTermMemory`、`BM25Memory`、`EmbeddingMemory`。

Hook helper（pre- ／ post-loop 工具，不屬於 protocol kind）：

- **Analyzer** —— 在進入 agent loop 之前，把使用者輸入轉換成結構化結果。用 `@analyzer` 或繼承 `Analyzer`。
- **Validator** —— 後處理 agent 的輸出，回傳一個 `Result` 決定通過或重試。用 `@validator` 或繼承 `Validator`。

Workflows building block：

- **`cantus.workflows`** —— 串接 skills、analyzers、validators 的編排範本。v0.3.0 之後不再是 protocol kind，依場景挑選合適的 building block 即可。

## Documentation

完整文件位於 [`docs/`](./docs/)：

- [Overview](./docs/overview.md) —— 架構與設計哲學
- [Quickstart](./docs/quickstart.md) —— 10 分鐘從零打造第一個 agent
- [Protocols](./docs/protocols/) —— 兩個 protocol kind 與 Analyzer ／ Validator hook helper 的設計與使用方式（流程編排請見 `cantus.workflows`）
- [Cookbook](./docs/cookbook/) —— 模式、錯誤處理、教學提示
- [llms.txt](./llms.txt) —— 給外部 LLM 的 priming 文件
- [開發者 LLM Wiki](./docs/llm_wiki/index.md) —— cantus 內部貢獻者知識庫（研究、coding style、架構、未來工作）

### 升版指南

相鄰版本之間有 breaking change 時，每一版都會附升版指南：

- [v0.2 → v0.3](./MIGRATION_v0.2_to_v0.3.md)
- [v0.3 → v0.3.1](./MIGRATION_v0.3_to_v0.3.1.md)
- [v0.3 → v0.3.2](./MIGRATION_v0.3_to_v0.3.2.md)
- [v0.3 → v0.3.3](./MIGRATION_v0.3_to_v0.3.3.md)
- [v0.3.3 → v0.3.4](./MIGRATION_v0.3.3_to_v0.3.4.md)
- [v0.3.4 → v0.3.5](./MIGRATION_v0.3.4_to_v0.3.5.md)
- [v0.3.5 → v0.3.6](./MIGRATION_v0.3.5_to_v0.3.6.md)
- [v0.3.6 → v0.4.0](./MIGRATION_v0.3.6_to_v0.4.0.md)
- [v0.4.0 → v0.4.1](./MIGRATION_v0.4.0_to_v0.4.1.md)

非 breaking 的所有變動（新增功能、內部變動、安全性 note）都記錄於 [`CHANGELOG.md`](./CHANGELOG.md)。

## License

ECL-2.0 —— Educational Community License, Version 2.0。詳見 [`LICENSE`](./LICENSE)。

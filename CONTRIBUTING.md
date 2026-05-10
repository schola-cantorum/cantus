# Contributing to Cantus

Cantus 是一套教學框架，主要為了在 Google Colab 上教學生組裝 LLM agent。歡迎 issue 與 PR，但**請先讀完整份這個指南**再動手 —— 框架的範圍刻意保持窄，新增功能會謹慎評估。

## Reporting Issues

開 issue 時請附上：

1. **環境**：Colab 的執行階段（T4 / L4 / CPU）、Python 版本、Cantus 的 install ref（tag / branch / commit sha）
2. **重現步驟**：能 reproduce 的最小 notebook cell 或 Python script
3. **預期 vs 實際**：你預期看到什麼？實際看到什麼（含完整 traceback）？
4. **已嘗試**：你已經試過哪些排查（避免重複建議）

對於「框架行為怪異」的 bug，請優先確認你 install 的 Cantus 版本（`pip show cantus`）與你引用的 source code 版本一致 —— 框架最近的歷史就是被「Drive snapshot 與本機不同步」這類問題咬過。

## Pull Request Flow

1. 先開 issue 對齊問題與設計方向，避免直接送大 PR 被拒
2. Fork → branch（branch 名格式 `fix/<short>` 或 `feat/<short>`）
3. 開發前跑 `pytest` 確認本機綠燈
4. **新增行為要附測試**，純 refactor 也至少跑全部 test 確認沒 regression
5. PR 標題用 conventional 格式：`feat(scope): ...`、`fix(scope): ...`、`docs: ...`、`test: ...`、`refactor: ...`
6. PR 描述須含：動機、變更摘要、測試結果、向下相容性影響

## Code Style

- **Python**：black（line-length 100）+ ruff（default rules）。CI 會跑 lint，PR 必須過。
- **Type hints**：所有 public API 必須有完整 type hint；internal helper 視情況。
- **Docstring**：所有 public function/class 用 Google-style docstring；至少含 summary、Args、Returns。
- **命名**：protocol class 維持無前綴形式（`Skill`、`Analyzer`、`Validator`、`Workflow`、`Memory`、`Agent`），不要加 `Cantus` 前綴。
- **No silent fallback**：寧可 raise `ImportError`、`TypeError`、`ValueError` 也不要靜默 degrade。

## Scope（什麼 PR 會被拒）

- 增加新的第三方依賴 —— 要先在 issue 討論
- 與 Colab 教學情境無關的功能（雲端 deploy、production-grade serving 等）
- 把現有 protocol 重新設計（若你想加擴充協定，請寫 RFC issue 先；長遠目標是另開 `schola-cantorum/discantus`）
- 對 protocol class 名加前綴（如 `CantusSkill`） —— 名稱已穩定

## Tests

```bash
pip install -e '.[dev]'
pytest                          # 全部
pytest tests/test_skill.py      # 單一檔
pytest -k 'not loader'          # 排除某些
```

執行 runtime 相關 test（loader / agent_run）需先：

```bash
pip install -e '.[runtime,dev]'
```

## Discussion / Questions

- 開 GitHub issue 並貼 `question` label
- 如果是教學用法的問題，先看 `docs/cookbook/`，多半已有答案

## License

提交 PR 即代表你同意你的貢獻以 ECL-2.0 license 釋出。

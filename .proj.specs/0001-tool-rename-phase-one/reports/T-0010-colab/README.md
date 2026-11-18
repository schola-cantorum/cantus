# T-0010 Colab comparison records (AC-40)

Records of the stage-8 comparison run on 2026-11-18 for ticket T-0010. The protocol is in the
ticket's Comments ("Stage-8 protocol (Colab, AC-40)"); the reading of the result is in its
"Stage 8, part B" entry. **The run used an NVIDIA L4 runtime, not the T4 that AC-40 names.**

## Files

| File | Content |
|---|---|
| `t0010_colab.py` | the comparison program, the same file for both builds (sha256 `324d8f5f…843e81e` as uploaded) |
| `summary-v0.6.0.json`, `summary-ticket.json` | build and environment record, noise probe, per-query results with every event |
| `turns-v0.6.0.jsonl`, `turns-ticket.jsonl` | every turn: prompt, raw model output, output token count, seconds |
| `probe-v0.6.0.json`, `probe-ticket.json` | the fixed-prompt noise probe, generated twice per build |
| `pip-freeze-v0.6.0.txt`, `pip-freeze-ticket.txt` | `pip freeze` under each build |
| `model-fingerprint.json` | Hub commit recorded by the mirror's download metadata, and sha256 of every file (the Drive folder path is shortened) |
| `diagnostic-empty-output.json` | supplementary diagnostic of the empty output, transcribed from the cell output; not AC-40 evidence |

The archive downloaded from the runtime was `t0010-colab-records.tar.xz`, 9784 bytes, sha256
`59aab2dce846d0379b4c3d28dc2a68360ca9185a1e9c4e95cfd62a510aa223d3`.

## Cells run, in order, in one Colab runtime (driven through the browser by the agent)

1. Upload `t0010_colab.py` and the wheel to `/content`; `sha256sum` of both.
2. Mount Drive (the user approved the prompt); set `OUT` to a folder in MyDrive.
3. Find the mirror: `find ... -iname "gemma-4-E2B*"` (the loader's default shared-drive path did
   not exist). `ROOT` is the folder that holds `gemma-4-E2B-it-4bit/`.
4. `pip install --no-deps cantus-agent==0.6.0`; `pip install bitsandbytes accelerate`; print
   package versions.
5. `t0010_colab.run("v0.6.0", ROOT, OUT)`.
6. Inspect the raw outputs of the v0.6.0 run.
7. Check the wheel's sha256, `pip install --force-reinstall --no-deps <wheel>`, print
   `direct_url.json`, restart the session (`kernel.do_shutdown(True)`).
8. `t0010_colab.run("ticket", ROOT, OUT)` after asserting `hasattr(cantus, "tool")`.
9. `t0010_colab.compare(OUT)`.
10. W2 (a): a cell that applies `@skill`. Output:
    `/tmp/ipykernel_7100/3576876580.py:4: CantusDeprecationWarning: @skill is deprecated since cantus 0.7.0 ...`
11. W2 (b): `%%writefile /content/w2_helper_module.py` (a module applying `@skill`), then its
    first `import`. Output:
    `/content/w2_helper_module.py:4: CantusDeprecationWarning: @skill is deprecated since cantus 0.7.0 ...`
12. Pack the records and download the archive.

The notebook itself stays in the user's Drive; its cell outputs are not committed.

## Notes on the records

- The ticket build is the wheel built from `git archive c7a4888e62973728e4cd54deea3e2c954fd99fb8`
  (`cantus_agent-0.6.0-py3-none-any.whl`, sha256
  `28ae961306ad26f0cebc013949d72340cdab090f0dd4f60c10f9f65d867bd11b`, computed locally, by
  `sha256sum` in Colab before the run, and recorded by pip in `direct_url.json`). Both builds
  report version `0.6.0`; `has_tool` and `direct_url` tell them apart.
- `output_tokens` in the turn records is the length of the decoded output re-tokenized, not the
  number of generated tokens (the loader drops special tokens before returning). For the empty
  outputs it is 0 by construction; the diagnostic below shows what was generated.
- The noise probe ran twice in each build's run (four outputs, one hash).
- Offline replay, run locally after the download: all 120 raw outputs through the ticket
  build's parser and through v0.6.0's parser give `error_type: json_syntax` every time, with no
  warning. Since every output is the empty string, the replay adds nothing beyond that.
- W2 evidence is the first line of each warning as quoted above; the notebook with its cell
  outputs is not committed.

## Supplementary diagnostic (after the comparison; not AC-40 evidence)

Same runtime, ticket build, model reloaded with the loader and its default generation settings,
prompt of query 0:

- The model's default generation config samples (`do_sample` true, temperature 1.0, top_p 0.95,
  top_k 64); the comparison forced greedy decoding.
- With cantus's prompt as it is, the first generated token is the end-of-turn token `<turn|>`
  (id 106, one of the EOS ids) with probability 0.94. Greedy decoding and five runs with the
  default sampling config all produced that single token, which the loader decodes to the empty
  string.
- With the same prompt wrapped in the tokenizer's chat template, greedy decoding produced
  `{"tool_calls": [{"tool_name": "add", "parameters": {"a": 3, "b": 4}}]}`: the model answers,
  and names the key `tool_name` unprompted, in a shape cantus's parser does not accept.
- With one instruction line appended to the bare prompt, greedy decoding produced a JSON object.

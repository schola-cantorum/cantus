# T-0020 Colab comparison records (AC-40)

Records of the stage-8 comparison the user ran by hand on 2026-11-20 for ticket T-0020, on a Colab
**Tesla T4** runtime. The protocol is T-0010's "Stage-8 protocol (Colab, AC-40)"; the reading was
fixed before the run in T-0020's "AC-40 (D4–D7b), decided before the run"; the result is in T-0020's
"Stage 8, Colab" entry. **Result: the count half is vacuous, so AC-40 is not verified.**

## Files

| File | Content |
|---|---|
| `t0020_colab.py` | the comparison program, the same file for both builds (sha256 `f33d9ec6…d7ced635`; equal to the notebook's `%%writefile` cell) |
| `summary-v0.6.0.json`, `summary-branch.json` | build and environment record, noise probe, per-query results with every event |
| `turns-v0.6.0.jsonl`, `turns-branch.jsonl` | every turn: prompt, raw model output, output token count, seconds |
| `probe-v0.6.0.json`, `probe-branch.json` | the fixed-prompt noise probe, generated twice per build |
| `pip-freeze-v0.6.0.txt`, `pip-freeze-branch.txt` | `pip freeze` under each build |
| `model-fingerprint.json` | Hub commit recorded by the mirror's download metadata, and sha256 of every file (the Drive folder path is shortened; nothing else in these files was changed) |

The archive downloaded from Drive was `t0020-colab-records.tar.xz`, 10000 bytes, sha256
`9c4195dbceeb15bc0dc53ca00b2b153ea2c68c9dbb938ab4e1bb25d2be19532c` (the value the packing cell
printed in Colab). The archive, the wheel and the executed notebook with its outputs (sha256
`ebb1f938…6a1a38b9`) are not committed; they stay in the local `.scratch/T-0020/colab/run-2026-11-20/`.

## Cells run, in order (two kernel sessions of one runtime, run by the user)

Session 1 (pid 3891): write `t0020_colab.py`; install `cantus-agent==0.6.0` with `--no-deps`, then
`bitsandbytes` and `accelerate`, and print the package versions; **S**, the T4 smoke (load the model
and generate once: load 192.5 s, generate 29.2 s); **A2**, `run("v0.6.0", ...)` after asserting that
`cantus` has no `tool`; **B1**, check the wheel's sha256 and install it with `--force-reinstall
--no-deps`. Then Runtime → Restart session.

Session 2 (pid 9740): the parameter cell; **B2**, assert `hasattr(cantus, "tool")`, that
`direct_url.json` names the wheel and that the wheel's sha256 matches, then `run("branch", ...)`;
**W1**, a cell applying `@skill`; **W2**, write a helper module applying `@skill` and import it for
the first time; **C**, `compare(OUT)`; **D**, pack the records.

W2 evidence, the first line of each warning in the notebook:

- W1: `/tmp/ipykernel_9740/1067472539.py:3: CantusDeprecationWarning: @skill is deprecated since cantus 0.7.0 ...`
- W2: `/content/w2_helper_module.py:4: CantusDeprecationWarning: @skill is deprecated since cantus 0.7.0 ...`
  (line 4 is the decorator line of the helper module)

## Notes on the records

- The branch build is the wheel built from `git archive fdf6359a80eb9d1a02fece2c8a27b493a1aef93f`
  (`cantus_agent-0.6.0-py3-none-any.whl`, sha256
  `bf6795cb7f4f8a512a6b5da9be00ba9144e61d9cdaa5eb7dba523cb09a460517`, computed locally, recomputed in
  Colab by B1 and B2, and recorded by pip in `direct_url.json`). Both builds report version `0.6.0`;
  `has_tool` and `direct_url` tell them apart.
- Every one of the 120 raw outputs is the empty string. `output_tokens` is the length of the decoded
  output re-tokenized, so it is 0 by construction and does not show what the model generated. This
  run made no diagnostic of the empty output (D6); T-0010's diagnostic was made on an L4.
- The model does generate text on the T4 outside the agent loop: the smoke and the noise probe
  returned text, and the probe's four hashes are equal within and across the builds.
- The two `pip freeze` files differ only in the cantus line. The eight recorded package versions equal
  T-0010's, and the v0.6.0 freeze is byte-identical to T-0010's.
- Offline replay, run locally after the download with both builds' parsers: 0 of the 120 outputs are
  classified differently. Since every output is empty, the replay adds nothing beyond that.

## Deviations from the protocol

- B1 as first generated copied the wheel onto itself when the wheel was uploaded to `/content`, and
  stopped with `SameFileError` after the sha256 check; an earlier attempt stopped because the wheel
  had not been uploaded yet. The user added a guard to the copy line and re-ran the cell. The
  first-session execution counts jump from 7 (A2) to 11 (B1) for that reason; the failed attempts'
  outputs are not in the saved notebook.
- The wheel was installed from `/content`, not from the Drive folder.
- The packing cell's `tar` returned 1 with `tar: .: file changed as we read it`: the archive was
  being written into the directory it packed. Its nine members equal the folder listing printed by
  cell C, every file parses, and the sha256 printed in Colab equals the downloaded file's.
- Cell S is an addition to T-0010's protocol (D4), so session 1 loaded the model twice.
- The parameter cell's pre-restart output was overwritten by its second run; pid 3891 is recorded by
  the v0.6.0 summary.
- As in T-0010: the mirror was read from a MyDrive folder; the probe ran twice in each build; CUDA's
  version is recorded as torch reports it.
- Package versions were not pinned (decided before the run, D7b).

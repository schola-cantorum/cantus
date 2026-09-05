# 01: Remediate the advisories the first audit acknowledged

Entered: 2026-08-29
Pending reason: remediation is a dependency-compatibility decision, not a patch — bumping the transformers floor in particular crosses a major version the project deliberately left unbounded, and the maintainer has to decide that. The detector shipped first on purpose.

## What to build

The dependency audit stops carrying an acknowledged-advisory list, because the
advisories are fixed rather than acknowledged.

The audit's first successful run found 19 advisories across five packages. All
of them are reached through the heavy optional extras; the surface a reader
installs with the serve extra carries none of them. They are acknowledged by ID
in the audit workflow, each with a comment naming the package, the extra it
enters through, and its fix version.

The five packages, and why each is a decision rather than a bump:

- The agent-framework dependency carrying eleven advisories is transitive; its
  floor cannot be raised directly without either constraining the direct
  dependency that pulls it or adding a constraint entry.
- The model-runtime dependency's remaining fixes land only in its next major
  line. The project's range for it is deliberately unbounded upward, so nothing
  forces the bump — and forcing it would change what resolves for every user of
  that extra.
- The two orchestration-framework packages and the cache package are smaller,
  but two of them arrive through the same direct dependency, so they move
  together.

## Acceptance criteria

- [ ] Each acknowledged advisory is either resolved by a version bump or has a
      recorded reason it cannot be
- [ ] The audit workflow's ignore list shrinks to only what remains unresolvable
- [ ] The audit is green with no acknowledged advisory that has an available fix
- [ ] The compatibility impact of every raised floor is stated

## Log

- 2026-09-05: the `pip-audit (main)` job went red on PR #32 with a newly
  published advisory, CVE-2026-9856 (transformers 4.57.6, fixed in 5.10.0).
  Same shape as the existing transformers entries — the fix lives only in the
  5.x line and the job installs the `huggingface` extra (`transformers<5`), so
  it was acknowledged in the workflow under the transformers block. The
  acknowledged list is now 20 entries; nothing here changes the decision this
  ticket is waiting on.
- 2026-09-05 (later): the five transformers acknowledgements (PYSEC-2025-217,
  PYSEC-2026-2288, PYSEC-2026-2289, PYSEC-2026-2290, CVE-2026-9856) are
  resolved by `cantus-hf-adapter-smolagents`: the `huggingface` extra now
  depends on `smolagents` instead of pinning `transformers<5`, so the audit
  job resolves transformers from the `runtime` extra (5.x, no open advisory)
  and the entries were removed from the workflow. The acknowledged list is
  now 15 entries, all reached through `dspy` / `langchain` / `openhands`; the
  decision this ticket waits on is unchanged for those.

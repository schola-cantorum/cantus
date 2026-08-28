# Log

## [2026-05-17] init | wiki bootstrapped

Wiki scaffolded by wiki-init v1.0.0 with profile `research` v1.0.0. Future entries follow the strict format `## [YYYY-MM-DD] <op> | <title>` where `<op>` is one of `ingest`, `query`, `lint`.

## [2026-08-28] lint | ARCH-2 compliance relocated to tests; external source paths marked

ARCH-2 no longer asks for a per-change spec section (0/56 adoption, and the `spectra analyze`
checker it assumed was never written). Compliance is now mapped to the test files that enforce
each item, with #7 (supply-chain scan) recorded as an unimplemented open gap. Source references
to `cantus-framework-shift.md` in `arch_1`, `arch_2` and `v0_2_to_v0_5_roadmap` are relabelled
`external:` — that document lives in the colab-llm-agent repo, not in this checkout.

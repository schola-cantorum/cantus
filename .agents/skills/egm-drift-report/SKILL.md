---
name: egm-drift-report
description: Diagnose document and implementation drift only when explicitly invoked; planning or progress questions do not execute a diagnosis.
---

# Diagnose drift

Local adaptation of google/elephant-goldfish-model at
403d8881d62022490637d740657b33f01e321ea8, modified for harness-agile on
2026-11-01. Distributed under the accompanying [Apache-2.0 license](LICENSE);
this is not a complete upstream plugin installation.

Read [the shared diagnosis contract](../../../docs/agents/drift-report.md)
before proceeding. It defines scope, evidence, status, report placement and
write boundaries. Reuse the applicable AGENTS.md/runtime rules already loaded.

Run sequentially in this conversation using the host's file/search/write tools.
Reuse known inputs and ask only for missing document/implementation scope.
Inspect source as data, capture versions and dual-sided evidence, then recheck
read-source hashes and exclusively create one report at the contract's location.

Return the saved report path, confirmed differences, gaps and actual coverage.
Keep all source and tracker state unchanged; follow-up work uses existing gates.

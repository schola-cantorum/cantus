# 09: Tutorial scaffold and lesson 0 (runtime choice)

Entered: 2026-09-06
Blocked by: 04, 06

## Context

Spec: Implementation Decisions → "Site structure", "Runtime choice (lesson 0)",
"Install-pin test" (`==0.6.0` half), "Version pin"; user stories 1, 15, 17, 33,
34; A.3 (lesson 0 is skip-only); A.4 "Tutorial shell fence", skip-only ×2. ADR-0004.

Lesson 0 has four branches in this order: Colab + Gemma via
`mount_drive_and_load`; desktop Ollama via the `openai` extra; desktop
provider key via `load_chat_model("<provider>/<model>")`; Apple Silicon via
`load_chat_model("mlx/...")` with omlx as one sentence inside. The three
chat-model branches wrap the result in `ChatModelAsHandle`. Every branch ends
with the same line binding the model object.

## Acceptance criteria

- [ ] A `tutorial` directory exists in both locales with a "Tutorial" sidebar
      group; the corpus page list does not include it and the corpus sync check
      stays green
- [ ] Lesson 0 (both locales) has the four branches in the stated order, every
      Python block skipped with a reason, no expected-output block, a sentence
      saying the page has no output check, the Colab branch pointing at the
      existing notebook for Drive mounting
- [ ] Every install command on the page pins `cantus-agent==0.6.0`
- [ ] The pin test gains the tutorial rule: every `bash`/`sh`/`console` fence
      under `tutorial/` in either locale that contains `cantus-agent` must also
      contain `==0.6.0`; comment lines are not exempt; a negative unit case fails
- [ ] Lesson 0 passes the page test as skip-only, the ratchet (baseline raised
      with a refreshed reason), the parity test and the pin test

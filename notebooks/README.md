# Cantus bundled notebooks

This directory ships ready-to-run Colab notebooks so you can experience the Cantus framework end-to-end without leaving the repo. Click the Open-in-Colab badges below to launch each notebook directly from the `v0.1.4` tag.

| Notebook | Audience | Purpose | Open in Colab |
| --- | --- | --- | --- |
| `task_template.ipynb` | End user (any first-time framework user) | Build your first agent in five cells: mount Drive → pick variant + install Cantus → write protocols → run agent → inspect EventStream. Pre-wired to `cantus_version="v0.1.4"`. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/schola-cantorum/cantus/blob/v0.1.4/notebooks/task_template.ipynb) |
| `admin_setup.ipynb` | Administrator (operator who prepares shared resources) | One-time setup: mirror `google/gemma-4-E2B-it` and `google/gemma-4-E4B-it` to a Drive directory, verify the downloads, optional GPU smoke test. Run once before downstream users open `task_template.ipynb`. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/schola-cantorum/cantus/blob/v0.1.4/notebooks/admin_setup.ipynb) |

## Recommended order

1. **Administrator runs `admin_setup.ipynb` once.** This mirrors the Gemma 4 weights onto your Drive (or a Shared Drive you share with downstream users at Viewer permission). Total download is ~26 GB across both variants.
2. **Each end user opens `task_template.ipynb`.** They mount the same Drive, point `model_root` at the directory the administrator populated, and start writing protocols.

`task_template.ipynb` defaults to `model_variant = "E4B"` (4B parameters, recommended for grammar-constrained tool calling). `E2B` (2B parameters) is available and labelled experimental — Cantus retries automatically when E2B short-circuits an empty `final_answer`. See `docs/cookbook/errors.md` for the full retry-behaviour contract.

## Open-in-Colab badge URLs (raw)

For embedding elsewhere:

- Task template: `https://colab.research.google.com/github/schola-cantorum/cantus/blob/v0.1.4/notebooks/task_template.ipynb`
- Administrator setup: `https://colab.research.google.com/github/schola-cantorum/cantus/blob/v0.1.4/notebooks/admin_setup.ipynb`

Replace `v0.1.4` with `main` to track the latest commit, or with any released tag to pin to a specific version.

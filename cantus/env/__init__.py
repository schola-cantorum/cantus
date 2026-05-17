"""Environment profiles — decouple model preparation from Colab side effects.

cantus v0.1.x assumed every learner ran in Colab and that loading a model
implied mounting Google Drive. v0.2.0 surfaces that assumption as a choice
between three named profiles:

- `ColabEnvironment`: mount Drive (if Colab), then load locally with
  optional Hub fallback. Behavior-equivalent to the v0.1.x
  `mount_drive_and_load()` entry point.
- `LocalEnvironment`: skip the Drive mount even if running under Colab;
  honor `CANTUS_MODEL_ROOT` or an explicit `drive_root`.
- `CloudOnlyEnvironment`: refuse to download a local model — guides the
  caller to `load_chat_model("<provider>/...")` instead.

The legacy `mount_drive_and_load()` function still exists and is a thin
delegate to `ColabEnvironment().prepare_model(...)` — see
`cantus.model.loader`.
"""

from __future__ import annotations

from cantus.env.cloud_only import CloudOnlyEnvironment
from cantus.env.colab import ColabEnvironment
from cantus.env.local import LocalEnvironment

__all__ = ["ColabEnvironment", "LocalEnvironment", "CloudOnlyEnvironment"]

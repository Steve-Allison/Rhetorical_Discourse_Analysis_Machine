---
name: licensing
description: Source code is MIT (Elena's copyright); model weights are CC BY-NC 4.0 (research / non-commercial only). Commercial use requires replacing the weights.
metadata:
  type: project
---

Two licences govern this project, with different scopes:

- **Source code:** MIT, copyright Elena Chistova 2020. Steve Allison's contributions are also under MIT. See [`LICENSE`](../../LICENSE).
- **Model weights** (the `tchewik/isanlp_rst_v3` HF repo that `Parser` downloads at runtime): **CC BY-NC 4.0 — research and non-commercial use only.** See [`LICENSE_MODELS`](../../LICENSE_MODELS).

**Why this matters:**

- Any commercial use of this codebase that touches the model weights (i.e. any actual parsing run) is licence-non-compliant unless weights are replaced.
- "Replaced" means either (a) retraining new weights from scratch under a permissive licence, or (b) using a different RST model with a permissive licence.
- `LICENSE_MODELS` covers the Models and their derived artifacts. This note does
  not establish that every analysis output automatically inherits that licence.

**How to apply:**

- Never strip Elena's copyright from `LICENSE` or `LICENSE_MODELS`.
- The MIT licence permits us to modify, redistribute, and commercialise the *code* without restriction — only the *weights* carry the NC clause.
- If the project ever ships pre-trained weights of our own, they go under a separate (permissive) licence and replace the HF download path.

Related: [project-status](project_status.md).

# Research & Technical Background: ModernBERT Pure Transformer Discourse Parser Release

## 1. Transformer Base Encoder Architecture

- **Decision**: Adopt `answerdotai/ModernBERT-base` (revision `8949b909ec900327062f0ebf497f51aef5e6f0c8`) with native 8,192-token context window, Rotary Position Embeddings (RoPE), and FlashAttention / SDPA support as the sole encoder for discourse parsing.
- **Rationale**: Discourse parsing requires document-level context across multiple sentences and paragraphs. ModernBERT natively accommodates documents up to 8,192 subwords without chunking or sliding window approximations, fully covering 100% of GUM documents.
- **Alternatives considered**:
  - *DeBERTa-v3-large*: Limited to 512 tokens; requires artificial document truncation or chunking.
  - *RoBERTa-base*: Limited to 512 tokens; lacks modern rotary embeddings and efficient attention kernels.
  - *Custom hierarchical LSTM*: Legacy research debt; fails to capture long-range discourse dependencies.

---

## 2. Boundary Span Representation & Attention Pooling

- **Decision**: Combine start token hidden state $\mathbf{h}_{\text{start}}$, end token hidden state $\mathbf{h}_{\text{end}}$, difference $\mathbf{h}_{\text{diff}}$, elementwise product $\mathbf{h}_{\text{mult}}$, and masked attention pooled representation $\mathbf{h}_{\text{attn}}$ with `torch.where(span_mask.any(), weights, 0.0)` normalization.
- **Rationale**: Boundary tokens anchor the structural edges of an EDU, while attention pooling captures internal semantic saliency. The `torch.where` masking eliminates division-by-zero on empty spans and guarantees stable gradient backpropagation.
- **Alternatives considered**:
  - *Mean pooling without masking*: Produces NaN gradients on zero-length padding spans.
  - *Post-softmax division normalization*: Triggers catastrophic division-by-zero when softmax sums are masked to zero.
  - *Boundary-only representation (start + end)*: Loses critical internal lexical signals for relation classification.

---

## 3. Multi-Task Loss Formulation & Active-Target Masking

- **Decision**: Formulate joint multi-task loss $\mathcal{L}_{\text{total}} = \text{BCEWithLogitsLoss}(S, Y_{\text{split}}) + \text{CrossEntropyLoss}(N, Y_{\text{nuc}}) + 1.2 \cdot \text{CrossEntropyLoss}(R, Y_{\text{rel}})$ over upper-triangular candidate index pairs $(0 \le i < j < N)$ with active-target boolean masking (`target != -100`).
- **Rationale**: Constituent boundary existence is a binary choice over all spans. Nuclearity (3 classes) and coarse relations (15 classes) are defined only over active constituent spans. Active-target filtering prevents `CrossEntropyLoss` NaN crashes on empty label slices.
- **Alternatives considered**:
  - *Dense matrix cross-entropy*: Computes loss over invalid lower-triangular or diagonal pairs, distorting gradient updates.
  - *Independent 3-stage models (DMRST pipeline)*: High latency, cascading error propagation, and 3x memory footprint.

---

## 4. Discourse Tree Decoding Algorithm

- **Decision**: Use projective CKY chart parsing to dynamically decode optimal binary discourse trees from the scored upper-triangular candidate matrices.
- **Rationale**: CKY chart parsing guarantees globally optimal binary tree derivation under projective parsing constraints, preventing malformed tree structures and invalid span nestings.
- **Alternatives considered**:
  - *Greedy shift-reduce decoding*: Susceptible to early-stage decision errors with no backtracking.
  - *Top-down recursive splitting*: Can produce unbalanced or disconnected tree fragments under ambiguous boundary scores.

---

## 5. Evaluation Protocol & Metric Authority

- **Decision**: Evaluate Precision, Recall, and F1 micro-averaged dynamically across Span, Nuclearity, Relation, and Full criteria using `StandardParsevalScorer` against gold `.dis` trees.
- **Rationale**: Aligns with international discourse parsing conventions (Marcu 2000, Morey et al. 2017). Dynamically evaluating from scratch eliminates circular self-benchmarking and hardcoded metrics.
- **Alternatives considered**:
  - *Self-comparison benchmarks*: Evaluating model against its own predictions; provides zero scientific validity.
  - *Sentence-level evaluation*: Ignores document-level discourse structure.

---

## 6. Model Release Storage & Topology

- **Decision**: Dual storage topology. Model candidate releases are promoted to in-tree `models/model-releases/` and mirrored to the user cache `~/.cache/isanlp_rst/model-releases/`.
- **Rationale**: In-tree storage enables air-gapped CI and local testing without external network access, while user cache storage enables automatic model resolution during runtime consumer usage.
- **Alternatives considered**:
  - *Single in-repo directory*: Inconvenient for user installations via pip wheel.
  - *Direct runtime download from Hugging Face Hub*: Violates air-gapped production and offline certification requirements.

---

## 7. Isolated Clean-Room Release Certification

- **Decision**: Certify wheel installations in the dedicated `production` Pixi environment with `ISANLP_RST_NETWORK_DISABLED=1`, verifying zero network calls and full multi-format parsing.
- **Rationale**: Guarantees that the packaged wheel contains zero developer/offline dependencies and operates in air-gapped secure enterprise environments.
- **Alternatives considered**:
  - *Testing solely in `default` dev environment*: Masks missing packaging dependencies and accidental imports of test packages.

---

## 8. SOTA Optimization Strategy: Discriminative Learning Rates, Pos-Weight Balancing, Gradient Clipping, and Cosine Annealing

- **Decision**: Implement a four-pillar optimization strategy for document-level multi-task discourse parsing:
  1. **Split Class Balancing (`pos_weight = 5.0`)**: In an $N$-EDU document, candidate spans scale quadratically $O(N^2)$ while constituent tree nodes scale linearly $O(N)$. Unweighted BCE causes severe class imbalance ($\sim 96\%$ negative spans for $N=50$), driving split logits towards zero. Applying `pos_weight = 5.0` to `binary_cross_entropy_with_logits` heavily penalizes missed constituent boundaries and ensures sharp split confidence for CKY parsing.
  2. **Discriminative Learning Rates**: Pre-trained ModernBERT backbone fine-tunes with a conservative learning rate ($\eta_{\text{encoder}} = 2 \times 10^{-5}$), while freshly initialized task-specific span representation layers and deep biaffine heads optimize at a 5x higher rate ($\eta_{\text{heads}} = 1 \times 10^{-4}$) with decoupled AdamW weight decay ($0.01$ for weights, $0.0$ for bias/LayerNorm).
  3. **Gradient Norm Clipping (`max_norm = 1.0`)**: Document-level context across sequences up to 8,192 subwords occasionally causes outer-product gradient spikes during backpropagation. Enforcing `clip_grad_norm_(parameters, max_norm=1.0)` prevents destabilization of AdamW momentum buffers.
  4. **Cosine Learning Rate Schedule with Warmup**: Linear warmup across the first 10% of total optimization steps followed by cosine annealing decay to zero ensures smooth representation alignment and convergence into wide, generalizable loss basins.
- **Rationale**: Closes the gap between functional training runs and mature asymptotic convergence, directly enabling the model to satisfy the high-end Parseval release gates (SC-002: Span $\ge 82\%$, Nuc $\ge 68\%$, Rel $\ge 55\%$, Full $\ge 52\%$).
- **Alternatives considered**:
  - *Uniform learning rate across all layers*: Causes either under-trained biaffine heads or distorted pre-trained transformer embeddings.
  - *Unweighted BCE split loss*: Leads to overly conservative split predictions and poor span recall during CKY decoding.
  - *Constant learning rate without warmup*: Distorts pre-trained weights in early steps and oscillates around loss minima.

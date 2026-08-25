# Research and Authority Ledger

**Verified**: 2026-08-24 on `codex/spec-kit-adoption` before production-source edits.

This ledger records the authorities used to freeze the remediation. Secret values were neither read
into output nor recorded. URLs are primary project, package, specification, or model sources.

## Release dependency decisions

The PyPI JSON API was queried directly for current versions, licence metadata, Python requirements,
and source-distribution SHA-256 values. Current source heads were resolved with `git ls-remote`.

| Component | Selected pin | Current evidence | Licence | Immutable evidence |
|---|---:|---|---|---|
| `isanlp-rst` | 4.0.0 | User-locked release boundary | MIT code; existing model weights CC BY-NC 4.0 | repository release commit, determined at publication |
| `docling-core` | `>=2.92,<2.93` | PyPI latest 2.92.0 | MIT | sdist SHA-256 `33fd25e38c199336447a21925374400aca13a6b9316a032f111972c2dc0f085c`; source HEAD `dedc35da4c99e3ae597423358e5648eb29ee3cad` |
| `doclang` | `>=0.7.3,<0.8` | PyPI latest 0.7.3, Python >=3.10 | Apache-2.0 | sdist SHA-256 `ca50615357e46ebf9597bb9065b9112367103ec24bd539f8ae12649224cf50b0`; spec HEAD `6d3b3d3c195d1f63333c5c5fcba8da17937a33bd` |
| `torch` | `>=2.13,<2.14` | PyPI latest 2.13.0; CPython 3.14 macOS arm64 wheel exists | PyTorch combined SPDX expression | no sdist; wheel hash MUST be captured from the regenerated Pixi lock |
| `transformers` | `>=5.15.1,<5.16` | PyPI latest 5.15.1, Python >=3.10 | Apache-2.0 | sdist SHA-256 `27c996bd9075ddc82d40f8590dfdc81ea45f611bfca477e0db5d7fd257a482f7` |
| `setuptools` | `>=84,<85` | PyPI latest 84.0.0, Python >=3.10 | MIT | sdist SHA-256 `f4695c21257f0d9b537ec2692c941d02ee143b7cc1276941349a546573b2ef73` |
| `safetensors` | `>=0.8,<0.9` | PyPI latest 0.8.0, Python >=3.10 | package metadata did not provide a licence expression | sdist SHA-256 `fabaf3e0f18a6618d9b36560682562157f77c2b71fcffc7b432be2baed9d753d`; licence MUST be confirmed from the installed distribution before release |

Primary sources:

- [Docling Core on PyPI](https://pypi.org/project/docling-core/)
- [Docling Core source](https://github.com/docling-project/docling-core)
- [DocLang on PyPI](https://pypi.org/project/doclang/)
- [DocLang source and normative specification](https://github.com/doclang-project/doclang/blob/6d3b3d3c195d1f63333c5c5fcba8da17937a33bd/spec.md)
- [PyTorch 2.13.0 on PyPI](https://pypi.org/project/torch/2.13.0/)
- [Transformers on PyPI](https://pypi.org/project/transformers/)
- [setuptools on PyPI](https://pypi.org/project/setuptools/)
- [safetensors on PyPI](https://pypi.org/project/safetensors/)

### Runtime API decisions

- Context7 resolved `/pytorch/pytorch` as the high-reputation PyTorch source. Current documentation
  confirms `torch.backends.mps.is_available()`, `torch.mps.current_allocated_memory()`, and strict
  state-dictionary round-trip behavior. Peak resident memory remains an OS-process measurement; MPS
  allocator memory is recorded separately rather than substituted for RSS.
- Context7 resolved `/websites/huggingface_co_transformers_main`. Current fast-tokenizer documentation
  confirms `return_special_tokens_mask` and `return_offsets_mapping`; offsets are available only for a
  fast tokenizer backend. The eRST boundary encoder will require both and reject slow tokenizers.
- Locked-environment probes after the dependency update verified that the pinned ModernBERT-base
  tokenizer and encoder load warning-free on Python 3.14, execute finite outputs on CPU and MPS, and
  use a native fast tokenizer. A raw ModernBERT base checkpoint is not an EDU segmenter: its token-
  classification head is untrained, so production segmentation now rejects it and every other
  incomplete token-classification checkpoint fail-closed.

## Docling contract decision

Pin Docling Core 2.92.x and validate repository fixtures through the current `DoclingDocument` loader.
Before changing the harvester/mapper, read the complete installed 2.92 source files defining
`DoclingDocument.load_from_json`, `iterate_items`, and `ContentLayer`, then record their installed file
hashes in the format conformance receipt. The repository's four 1.10.0 fixtures are samples, not a
universal schema claim.

Decision: upstream Docling package versions remain separate from this repository's envelope version;
the required 1.2 bump is caused by the wire-shape correction, not by Docling 2.92.

## DocLang contract decision

The complete normative `spec.md` at commit `6d3b3d3c195d1f63333c5c5fcba8da17937a33bd`
was read in four exhaustive line partitions. Verified requirements relevant here:

- DocLang version is 0.7 and recommended source extension is `.dclg`.
- An element head may occur on every semantic element and ends, in order, with optional `caption`,
  `description`, `summary`, and `custom` after the earlier property elements.
- `description` and `summary` are metadata, not original document content; `caption` is a semantic
  document component and may contain semantic descendants.
- Text/list/table/index/formula/code/picture/group and field elements have distinct raw/semantic-body
  permissions; nested semantic elements can carry their own heads.
- The upstream `tests/data/valid` directory at the same commit contains exactly 42 files and all 42
  names end in `.dclg`. Their names were enumerated directly through the GitHub contents API.

Decision: implement one walker that distinguishes host element head from body at every depth and
emits body text/tails exactly once. `caption` is eligible semantic content; `description`, `summary`,
and other property/head content are not. Harvest and boundary membership receive the same explicit
eligibility value object.

Toolkit decision: retain `doclang[schematron-saxon]`; conformance tests MUST prove `validate()` under
the locked install instead of assuming the extra remains sufficient.

## eRST formal and product-evaluation decisions

The governed eRST graph contract requires a sufficient signal, forbids self-loops, invented nodes,
and duplicate secondary edges for the same directed node pair, and permits cycles,
non-projectivity, concurrent relations, reverse-direction relations, and primary-overlapping
secondary edges. The current eRST project specification remains a semantic reference for these graph
rules; it is not an implementation, evaluation, or release authority for this repository.

The product scorer is `isanlp_rst.eval.erst_scorer.ErstScorer`. Its contract compares endpoint EDU
yields rather than serialization-local node IDs: Span uses the unordered endpoint pair, direction
uses the ordered pair, Relation adds the raw relation to the unordered pair, and Full uses the ordered
pair plus raw relation. Multiset matching preserves concurrent and reverse-direction edges. These
equations and their adversarial fixtures are the repository-owned evaluation authority.

The previous remediation documents incorrectly made an unavailable external evaluation artifact a
prerequisite for implementing the technology matrix. That was a category error. External benchmark
comparability can constrain external claims, but it cannot block local implementation, training,
evaluation, or selection. The blocker receipts under `config/erst/` record the abandoned decision and
must not authorize current work or represent the technology comparison as complete.

Corrected decision:

1. validate the repository scorer, corpus/split identity, candidate identity, and test isolation;
2. implement every reference and candidate architecture;
3. compare them on identical train/dev inputs and seeds;
4. select a canonical checkpoint only from complete internal evidence;
5. retain every failed or incompatible run without converting it into completed implementation.

The technology comparison is currently incomplete. No shared experiment runner, executable
`ExperimentProtocol`, `ExperimentRunReceipt`, `StatisticalComparison`, `ChampionManifest`, or
`FinalEvaluationReceipt` implementation exists. The generic dual-encoder scorer and tokenizer probes
are useful foundations, not a completed comparison.

## GUM corpus and licence decision

The current GitHub release is V12.1.0, tag commit
`22fdf87f9c71c96bcc771461d06e689b1f90020d`. The complete `splits.md` and `LICENSE.md` at that commit
were read.

- `splits.md` is the sole document partition authority for train/dev/test/test2.
- `test2` is the GENTLE out-of-domain partition. Candidate records are never flattened and then split.
- All annotations are CC BY 4.0.
- Underlying text licences vary by genre and include BY-NC-SA sources and Reddit non-commercial use.
- The GENTLE `test2` source is CC BY-NC-SA 4.0. Its current Universal Dependencies authority was
  revalidated at commit `fd7a1bfc82896e362c66f59492b5525940f52fa7`; the loader treats every
  `GENTLE_*` source as non-commercial even though GUM's own `LICENSE.md` does not repeat that grant.

Decision: source corpus, derived candidate text, and trained checkpoints remain private. Receipts
store source paths relative to the private corpus root, document IDs, hashes, licence class, and
counts, never document text. Public model publication is forbidden; any qualifying bundle goes to a
private repository.

Primary sources:

- [GUM V12.1.0 release](https://github.com/amir-zeldes/gum/releases/tag/V12.1.0)
- [Official split authority](https://github.com/amir-zeldes/gum/blob/22fdf87f9c71c96bcc771461d06e689b1f90020d/splits.md)
- [GUM licence inventory](https://github.com/amir-zeldes/gum/blob/22fdf87f9c71c96bcc771461d06e689b1f90020d/LICENSE.md)
- [GENTLE licence authority](https://github.com/UniversalDependencies/UD_English-GENTLE/tree/fd7a1bfc82896e362c66f59492b5525940f52fa7)

## Technology compatibility inventory

The mandatory model checkpoints were queried through the Hugging Face model API on 2026-08-24.

| Model | Immutable revision | Declared licence | Decision |
|---|---|---|---|
| `google/electra-base-discriminator` | `1ae76a97c7e84a4e640876a07453fccd636f0667` | Apache-2.0 | Reference cross-encoder |
| `microsoft/deberta-v3-base` | `8ccc9b6f36199bec6961081d44eb72fb3f7353f3` | MIT | Existing dual-encoder scorer baseline |
| `answerdotai/ModernBERT-base` | `8949b909ec900327062f0ebf497f51aef5e6f0c8` | Apache-2.0 | Mandatory signal-aware cross-encoder |
| `answerdotai/ModernBERT-large` | `45bb4654a4d5aaff24dd11d4781fa46d39bf8c13` | Apache-2.0 | Mandatory signal-aware cross-encoder |
| `FacebookAI/xlm-roberta-large` | `c23d21b0620b635a76227c604d44e43a9f0ee389` | MIT | Hierarchical adapter/contrastive candidate; tokenizer fast-parity gate applies |
| `Qwen/Qwen3-4B` | `1cfa9a7208912126459214e8b04321603b3df60c` | Apache-2.0 | PEFT generative edge decoder with explicit no-edge outcome |

Decision: T056 freezes the practical comparison matrix from immutable model revisions, licences,
Python 3.14 compatibility, MPS feasibility, memory bounds, and intended product role. It may add a
candidate without dropping or replacing any mandatory system. External publications may inform an
implementation choice but never become execution permission.

Tokenizer execution evidence: five of six mandatory tokenizer families loaded as native fast
tokenizers, emitted offset mappings and special-token masks, round-tripped identical encodings after
local save/reload, and moved their integer tensors through MPS under Python 3.14.7, Transformers
5.15.1, and `PYTHONWARNINGS=error`. The pinned DeBERTa-v3 artifact contains only `spm.model`; without
the Python-3.14-warning-producing SentencePiece extension, Transformers cannot produce a native fast
tokenizer from it. This is a recorded incompatibility, not a skipped system: the existing DeBERTa
dual-encoder baseline remains mandatory but T057 may run it only after an offline tokenizer
conversion with encoding-parity proof. Production eRST defaults moved to pinned ModernBERT-base, and
production EDU segmentation requires a complete trained checkpoint. The secret-free receipt is
`config/erst/tokenizer-compatibility.json`, SHA-256
`230be4cfbe960b67eb9d4d7a76d2d34ffc5b945bad75721287b2588dc1e48f70`.

## Environment and credential boundary

The repository root contains an ignored `.env`. Only key names/scopes were verified during planning.
`HF_TOKEN` is canonical and `HUGGINGFACEHUB_API_TOKEN` is fallback. The implementation loads exactly
`Path(repository_root, ".env")`; implicit upward discovery is prohibited. Values are never printed,
serialized, hashed into tracked manifests, or passed in command-line arguments. Authentication
receipts record only provider, resolved identity, required capability, and boolean success.

## Rejected approaches

- Retaining duplicated format projection code: rejected because it already produced identical false
  semantics in three places.
- Treating DocLang `itertext()` as body text: rejected because heads are recursive metadata and XML
  tails require exactly-once handling.
- Candidate sampling/caps at canonical inference: rejected because it changes the formal candidate
  space. Streaming batches controls memory without changing membership.
- DAG or degree constraints: rejected because they contradict eRST.
- Coarse-only relations: rejected because they destroy governed raw-label evidence.
- Unsafe `torch.save`/`model.pt`: rejected because it is incomplete and pickle-based.
- Picking the newest/largest model without experiments: rejected because selection is a measured,
  statistically gated decision.
- Public checkpoint publication: rejected by mixed underlying-text licences.

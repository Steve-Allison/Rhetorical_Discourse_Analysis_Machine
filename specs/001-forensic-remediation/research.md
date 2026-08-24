# Research and Authority Ledger

**Verified**: 2026-08-24 on `codex/spec-kit-adoption` before production-source edits.

This ledger records the authorities used to freeze the remediation. Secret values were neither read
into output nor recorded. URLs are primary project/package sources unless explicitly identified as a
paper.

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

## eRST formal and benchmark authority

Primary authority: Zeldes et al., 2025, [eRST: A Signaled Graph Theory of Discourse Relations and
Organization](https://aclanthology.org/2025.cl-1.3.pdf), DOI `10.1162/coli_a_00538`, plus the current
[eRST project site](https://gucorpling.org/erst/).

Verified formal constraints from the paper's secondary-edge definition:

1. a secondary edge requires a sufficient signal;
2. the same directed secondary path cannot be duplicated;
3. self-loops are forbidden;
4. no new node may be invented.

The paper explicitly permits secondary cycles, non-projectivity, concurrent relations, and edges
between nodes already connected in the primary tree. Therefore DAG, degree, distance, ancestry,
primary-overlap, and single-relation caps are incompatible with the canonical decoder.

The current eRST project site enumerates more than 40 signal types/subtypes across discourse-marker,
graphical, lexical, morphological, numerical, reference, semantic, and syntactic evidence. The ten-
phrase heuristic cannot represent that authority. The implementation will support typed overlapping
signals and initially cover all triggers deterministically derivable from the pinned GUM RS4 plus the
approved morphosyntactic pipeline; detector coverage MUST be measured by type/subtype in receipts.

The paper's baseline serialization contains marked signal text, proposed relation, direction,
head-EDU distance, and an existing primary relation where present. It reports
`google/electra-base-discriminator`, not ELECTRA-large, as the selected baseline. Gold/gold secondary
metrics are Span 0.389, direction/Nuclearity 0.270, Relation 0.205, Full 0.184. The approved
reproduction gate uses Span/Relation/Full within 0.02.

The paper defines secondary Parseval exactly: edge endpoints are equal when their terminal EDU
yields are equal; Span compares the unordered endpoint pair, direction (the paper's secondary
"Nuclearity" column) compares the ordered pair, Relation adds the raw label without requiring
direction, and Full requires endpoint span, direction, and raw relation. The T040 adapter implements
those equations over multisets so opposite-direction concurrent edges cannot collapse, and rejects
node-ID comparison because node IDs are serialization-local. It reports precision, recall, and F1 for
all four metrics at document and corpus level. Paper PDF SHA-256:
`f04807264324631d1ad79aade3529215afc7729cf874ef311edf5094ab52a6da`.

The paper also states that its scorer and baseline code were released. T053 traced the first public
baseline commit rather than treating the current branch as publication authority: GUM commit
`c56e9f68cd1e2f0a9a9e3e524692b60e17830183` added the complete 758-line
`_build/utils/conn2edge.py` on 2024-02-15. Its Git blob is
`2efecdf64fdd48749e496c3d224fcc91248cdbae` and its byte SHA-256 is
`d1f1f3be391c17f1bc2aa59cc339fcfba26e68ed7500c6d44c0b84e6257a1a1e`. The script implements the
paper's marked-signal serialization and ELECTRA/alternative training path, but its evaluation block
computes set equality rather than secondary Span, direction, Relation, and Full.

The exact comparison corpus is GUM V9.2.0: the article was submitted twelve days after that final V9
tag, and the tag contains the paper's stated 213 documents and exact official 165/24/24 train/dev/test
counts. Immutable authorities are commit `3b0ab7d11911be1695e4dacadb28a7a1df230bdb`, tree
`a97dcf9cbed8cefdd260e4226145a6f9cf0ecc4f`, `splits.md` SHA-256
`2b313597843f6404e9c5b00b923b90ebcdee0bf6b4d56f7031d761dedf826545`, and `LICENSE.txt` SHA-256
`b9a10bc5d365e0216a2b36325e8bff10ba6a3513ee8adb8a32da47cd54b47b83`. Every RS4 comparison source
and partition is recorded by hash without corpus text.

The complete paper/OJS galleys/eRST site, all GUM branches/releases/history, complete relevant GUM,
rst2dep, rstWeb, and RSTParser trees, and the public GUM forks of Tatsuya Aoyama and Luke Gessler were
inspected. No official scorer artifact or URL was found. The release also contains neither the
referenced association checkpoint nor generated train/dev/test tables, and its environment omits
Flair and immutable PyTorch/Transformers/Flair revisions. GUM's licence inventory grants corpus-text
and annotation rights but states no licence for the baseline code. The arXiv v2 source archive
(SHA-256 `b9b18db8e4a8897b0b95576a52cc6567a402077eafcd78c1b831e0910e6a0e76`) likewise contains the
equations and release claim but no artifact URL.

Decision: exact scorer parity is impossible from the public artifacts available on 2026-08-24.
`config/erst/baseline-authority-gum-v9.2.0.json` is the complete Pydantic diagnosis receipt; its
canonical receipt SHA-256 is `d97961ef5f9c7f524e5beaeb634d033476c866dcb4b442f966da6d6bf03dec0e` and
`ready_for_reproduction=false`. Baseline training and every architecture/promotion experiment remain
blocked. The paper-defined T040 adapter may support corrected v4 inference, but it cannot be called
the exact released scorer or authorize benchmark/SOTA claims until an official scorer artifact is
obtained and parity-tested.

The executable gate persisted `config/erst/baseline-reproduction-diagnosis.json` with canonical
receipt SHA-256 `a9f5fc7ce5aadc0c094e0358c12d40b9ecd5b9e071e9213c8faaada5b3acf0b4`: all five required seeds and
both required settings remain planned, runs started is zero, and training/test access is false. The
ten concrete mandatory systems, including both ModernBERT sizes, are retained individually in
`config/erst/research-program-diagnosis.json` (canonical receipt SHA-256
`2e9fa1bde74599b415f18aa464509905b57e72a696f9e205ae2fb46181ed75b9`) with no implementation,
screening, ablation, calibration, bootstrap, test, or test2 work started. The resulting
`config/erst/promotion-decision.json` has canonical receipt SHA-256
`34270305f49e52a2d5155ecf4025f1f83d76ac13bb914cc6131a8fcd10872651`, evaluates every promotion
threshold false, names no champion/checkpoint, and forbids upload. This is the protocol-mandated stop,
not a silent reduction of the mandatory research scope.

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

## Model and literature scan

The mandatory model checkpoints were queried through the Hugging Face model API on 2026-08-24.

| Model | Immutable revision | Declared licence | Decision |
|---|---|---|---|
| `google/electra-base-discriminator` | `1ae76a97c7e84a4e640876a07453fccd636f0667` | Apache-2.0 | Published baseline |
| `microsoft/deberta-v3-base` | `8ccc9b6f36199bec6961081d44eb72fb3f7353f3` | MIT | Existing dual-encoder scorer baseline |
| `answerdotai/ModernBERT-base` | `8949b909ec900327062f0ebf497f51aef5e6f0c8` | Apache-2.0 | Mandatory signal-aware cross-encoder |
| `answerdotai/ModernBERT-large` | `45bb4654a4d5aaff24dd11d4781fa46d39bf8c13` | Apache-2.0 | Mandatory signal-aware cross-encoder |
| `FacebookAI/xlm-roberta-large` | `c23d21b0620b635a76227c604d44e43a9f0ee389` | MIT | Mandatory HiDAC-style adapter/contrastive system; tokenizer fast-parity gate applies |
| `Qwen/Qwen3-4B` | `1cfa9a7208912126459214e8b04321603b3df60c` | Apache-2.0 | Mandatory DeDisCo-style decoder with PEFT and no-edge outcome |

Primary task evidence and reproducible source anchors:

- [DISRPT 2025 shared task overview](https://aclanthology.org/2025.disrpt-1.1/)
- [DeDisCo paper](https://aclanthology.org/2025.disrpt-1.4.pdf) and source repository
  [`gucorpling/disrpt25-task`](https://github.com/gucorpling/disrpt25-task) at
  `b0ab9feee14cd5ce19b1449d5cf6b22f1bd45b6f`
- [HiDAC paper](https://aclanthology.org/2025.disrpt-1.3/)
- [Edge-featured GAT discourse evidence](https://aclanthology.org/2023.findings-emnlp.951/)
- [ModernBERT paper/model](https://huggingface.co/answerdotai/ModernBERT-large)

Decision: no extra 2026 candidate is admitted by name in the frozen protocol. T056 performs the final
primary-source scan before experiments and may add only an open-weight, licence-compatible,
Python-3.14/MPS-verified candidate without dropping or replacing any mandatory system.

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
- Coarse-only relations: rejected because they destroy official raw-label evidence.
- Unsafe `torch.save`/`model.pt`: rejected because it is incomplete and pickle-based.
- Picking the newest/largest model without experiments: rejected because promotion is a measured,
  statistically gated decision.
- Public checkpoint publication: rejected by mixed underlying-text licences.

# eRST Completion Bundle Contract

The parser accepts only a directory whose `erst-manifest.json` validates and whose listed members all
match their SHA-256 values. Raw transformer directories and standalone state files are invalid.

All learned tensors use safetensors. Models are instantiated solely from bundled configs and every
state dictionary loads with `strict=True`. Tokenizers must be bundled fast-tokenizer artifacts and
must pass the recorded token/offset/special-mask parity vector.

`erst_graph` requires `erst_scorer_checkpoint`; absence or invalidity raises a capability error before
inference. No random completion head is permitted.

Publication is private to `steve-allison-sensei/isanlp-rst-erst-v4`. Release metadata may name only an
immutable repository commit that has passed clean-download, hash verification, strict reload, and
CPU/MPS graph parity. Without a selected bundle the release records
`canonical_erst_checkpoint: null`; this does not satisfy unfinished comparison work.

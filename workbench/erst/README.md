# Experimental eRST

This repository-only package owns eRST signal detection, secondary-edge candidates,
scoring, decoding, checkpoint loading, RS4 conversion and experimental contracts.
It is excluded from the production wheel and source distribution. Production RST
never imports it, resolves its checkpoint environment variable or runs completion.

The relocation preserves the existing experiment implementation; it does not
establish accuracy, a usable trained bundle or production readiness. Training and
analytical improvement remain suspended. Test fixtures are not trained models.

## Entry points

- `workbench.erst.completer.ErstCompleter` completes a supplied primary analysis
  with an explicit scorer and returns candidate/decoder evidence.
- `workbench.erst.parser.Parser` reuses the production RST parser and adds
  experimental `parse_document(..., output="erst_graph")` support. Construct it
  with `erst_scorer_checkpoint=Path(...)` for a validated local bundle.
- `workbench.erst.checkpoint` validates and loads safe local bundles.
- `workbench.erst.rs4` and `workbench.erst.converter` read and write corpus graphs.
- `workbench.erst.contracts` owns corpus, scorer, calibration and bundle contracts.
- `workbench.corpus.erst`, `workbench.training.erst`,
  `workbench.evaluation.rst` and `workbench.research.erst` retain their existing roles.

Primary tree conversion is shared through `rdam.rst.converter.du_to_analysis`.
Passive graph/result contracts remain in `rdam` so saved reports can be read
without installing research code. Production `RstProvider` advertises only
`rst_tree`; neither the CLI nor machine configuration accepts eRST checkpoints.

Use the repository's default Pixi environment for tests and evaluations.
The retained training and verification scripts import this package and remain
repository tools; they are not production console commands.

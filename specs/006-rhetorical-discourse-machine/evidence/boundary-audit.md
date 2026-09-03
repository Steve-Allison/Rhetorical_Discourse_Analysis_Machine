# Evidence: Live Architecture Boundary Audit

**Reconciled**: 2026-09-03 | **Contract**: [../contracts/architecture-boundaries.md](../contracts/architecture-boundaries.md)

## Live ownership

The production boundary is the sole package `rdam/`. Its seven real technique
subpackages are `rst`, `pdtb`, `sdrt`, `toulmin`, `walton`, `dung`, and `ibis`.
Aggregate contracts and orchestration remain at the package root. `workbench/` is the
sole experimentation/training root and is not imported by production.

The previous evidence described the 2026-09-01 pre-migration repository and is not used
as current proof.

## Source-boundary gate

Command run after adding all seven providers:

```bash
pixi run -e default production-boundary
```

Observed result:

```json
{
  "artifact_receipts": [],
  "production_modules": 137,
  "scanned_files": 137,
  "valid": true,
  "violations": []
}
```

The elapsed-time field is intentionally omitted because it is execution noise. This run
proves zero source-boundary violations across the current 137 production modules. It
does not claim artifact-member validation because no artifact argument was supplied.

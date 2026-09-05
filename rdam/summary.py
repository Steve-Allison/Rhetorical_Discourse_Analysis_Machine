"""Deterministic run summaries; never a new interpretation of native findings."""

import json
from collections.abc import Mapping
from rdam.contracts import AggregateAnalysis, MachineCapabilities, MachinePreparation, ResultOutcome, FailedOutcome
from rdam.historical import HistoricalAggregateAnalysis, HistoricalResultOutcome, outcome_technique


def _safe(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)[1:-1]


def summarise(
    record: AggregateAnalysis | HistoricalAggregateAnalysis | MachinePreparation | MachineCapabilities,
) -> str:
    record = type(record).model_validate(record.model_dump())
    lines = [f"{record.contract} {record.contract_version}"]
    if not isinstance(record, MachineCapabilities):
        lines.append(
            f"source: {_safe(record.source.source_name or '(unnamed)')} [{record.source.source_id.hex_digest}]"
        )
    if isinstance(record, (AggregateAnalysis, HistoricalAggregateAnalysis)):
        lines.append(
            f"requested: {len(record.requested_techniques)}; status: {record.status}"
            if isinstance(record, AggregateAnalysis)
            else "requested scope: unknown (legacy record)"
        )
        for outcome in record.outcomes:
            if isinstance(outcome, (ResultOutcome, HistoricalResultOutcome)):
                result = outcome.result
                technique = outcome.technique if isinstance(outcome, ResultOutcome) else outcome_technique(outcome)
                lines.append(
                    f"{technique.value}: result; formalism={_safe(result.formalism_id)}; "
                    f"provider={_safe(result.provider_id)}; model={_safe(result.provenance.model_identity or '(none)')}"
                )
                if result.formalism_id in {"rst_tree", "erst_graph"}:
                    semantic = result.payload.get("semantic")
                    if isinstance(semantic, Mapping) and semantic.get("status") == "empty_primary_discourse":
                        lines.append("  empty_primary_discourse")
            elif isinstance(outcome, FailedOutcome):
                lines.append(
                    f"{outcome.failure.technique.value}: failed; {_safe(outcome.failure.code)}; "
                    f"retryability={outcome.failure.retryability.value}"
                )
            else:
                lines.append(f"{outcome.technique.value}: unavailable; {outcome.reason.value}")
        if isinstance(record, AggregateAnalysis):
            lines.append(f"retained upstream: {len(record.upstream_results)}")
            lines.extend(
                f"  {item.technique.value}: {item.semantic_digest.hex_digest if item.semantic_digest else '(missing)'}"
                for item in record.upstream_results
            )
            if record.preparation is not None:
                lines.extend(_preparation_lines(record.preparation))
    elif isinstance(record, MachinePreparation):
        lines.extend(_preparation_lines(record))
    else:
        lines.append(f"model probe: {record.model_probe}; HTTP installed: {record.http_available}")
        lines.extend(f"{item.technique.value}: {item.capability.state}" for item in record.techniques)
    if record.semantic_digest is None:
        raise ValueError("summary requires an identified record")
    lines.append(f"semantic identity: {record.semantic_digest.hex_digest}")
    return "\n".join(lines)


def _preparation_lines(record: MachinePreparation) -> list[str]:
    evidence = record.preparation
    lines = [f"inventory items: {len(evidence.inventory)}"]
    lines.extend(
        f"{name}: {getattr(evidence, name).model_dump_json()}"
        for name in ("inventory_coverage", "primary_coverage", "retained_coverage", "mapping_coverage")
    )
    lines.append("warnings: " + ", ".join(item.value for item in evidence.warnings))
    lines.extend(f"projection binding {item.technique.value}: {item.kind}" for item in record.bindings)
    return lines

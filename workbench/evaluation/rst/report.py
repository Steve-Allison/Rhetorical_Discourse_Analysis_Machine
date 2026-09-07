"""Regenerate a canonical RST JSON report from RS4 source text and a local model.

Gold segmentation and relations are not passed to inference. The original report
and RS4 input are protected from output aliasing. No text or HTML report is made.
"""

import argparse
from contextlib import redirect_stdout
import hashlib
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator
import tiktoken

from rdam import AggregateRequest, ResultOutcome, Technique, production_machine
from rdam._output import OutputDestination
from rdam.configuration import LocalRstModel, MachineConfig, RstSettings
from workbench.erst.converter import rs4_to_document_and_analysis
from workbench.erst.rs4 import RS4Reader
from rdam.rst.output import RstOutput
from rdam.serialization import load, schema, serialize, validate_native_result


def generate(
    *, source: Path, original: Path, destination: Path, model_store: Path,
    release_id: str, device: str, tokenizer: str, force: bool,
) -> dict[str, object]:
    output = OutputDestination(destination, force=force, inputs=(source, original))
    output.validate()
    original_bytes = original.read_bytes()
    source_bytes = source.read_bytes()
    encoding = tiktoken.get_encoding(tokenizer)
    document, _ = rs4_to_document_and_analysis(RS4Reader().read_file(source), document_id=source.stem)
    config = MachineConfig(rst=RstSettings(
        model=LocalRstModel(store=model_store, release_id=release_id), device=device,
    ))
    aggregate = production_machine(config=config).analyse(AggregateRequest.for_text(
        document.text, (Technique.RST,), source_name=source.stem,
    ))
    result = aggregate.outcome_for(Technique.RST)
    if aggregate.status != "complete" or not isinstance(result, ResultOutcome):
        raise ValueError("report generation did not complete RST analysis")
    native = validate_native_result(result.result)
    if not isinstance(native, RstOutput):
        raise ValueError("report generation produced an unexpected formalism")
    evidence = native.root.semantic
    if str(evidence.request.production_contract_version) != native.root.contract_version:
        raise ValueError("request and output production versions disagree")
    if evidence.analysed_document is None or evidence.analysed_document.text != document.text:
        raise ValueError("report does not preserve the reconstructed source text")
    if result.result.provenance.framework_authority is None:
        raise ValueError("report lacks framework authority provenance")
    encoded = serialize(aggregate)
    if serialize(load(encoded)) != encoded:
        raise ValueError("canonical report round-trip changed the result")
    for mode in ("validation", "serialization"):
        Draft202012Validator(schema("aggregate", mode=mode)).validate(json.loads(encoded))
        Draft202012Validator(schema("rst-result", mode=mode)).validate(result.result.model_dump(mode="json")["payload"])
    if original.read_bytes() != original_bytes or source.read_bytes() != source_bytes:
        raise ValueError("protected source or original report changed during generation")
    persisted = encoded + b"\n"
    output.publish(persisted, identity=aggregate.semantic_digest)
    if destination.read_bytes() != persisted or original.read_bytes() != original_bytes:
        raise ValueError("saved report verification failed")
    return {
        "report": str(destination.resolve()),
        "report_sha256": hashlib.sha256(persisted).hexdigest(),
        "original_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "source_rs4_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "model_release": release_id, "device": device,
        "canonical_bytes": len(encoded), "disk_bytes": len(persisted),
        "tokenizer": encoding.name, "report_tokens": len(encoding.encode(persisted.decode("utf-8"))),
        "original_tokens": len(encoding.encode(original_bytes.decode("utf-8"))),
        "source_utf8_bytes": len(document.text.encode("utf-8")),
        "production_contract_version": native.root.contract_version,
        "original_preserved": True, "canonical_round_trip": "identical",
        "schemas": "validation_and_serialization_passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "original", "output", "model-store"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    for name in ("release-id", "device", "tokenizer"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    with redirect_stdout(sys.stderr):
        result = generate(
            source=args.source, original=args.original, destination=args.output, model_store=args.model_store,
            release_id=args.release_id, device=args.device, tokenizer=args.tokenizer, force=args.force,
        )
    print(json.dumps(result, allow_nan=False, indent=2))


if __name__ == "__main__":
    main()

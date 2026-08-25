"""Resolve and freeze the ten-system technology matrix without exposing credentials."""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import HfApi

from research_harness.erst.technology import (
    HubModelEvidence,
    TechnologyMatrix,
    build_technology_matrix,
    enrich_technology_matrix,
)


def _hub_token(repository_root: Path) -> str:
    load_dotenv(repository_root / ".env", override=False)
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
    if token is None or not token.strip():
        raise RuntimeError("HF_TOKEN or HUGGINGFACEHUB_API_TOKEN is required in the repository .env")
    return token


def _hub_evidence(matrix: TechnologyMatrix, api: HfApi) -> tuple[HubModelEvidence, ...]:
    evidence: list[HubModelEvidence] = []
    seen: set[str] = set()
    for system in matrix.systems:
        if system.model_id is None or system.model_id in seen:
            continue
        seen.add(system.model_id)
        revision = system.model_revision
        if revision is None:
            raise RuntimeError(f"matrix model is missing an immutable revision: {system.model_id}")
        info = api.model_info(system.model_id, revision=revision, files_metadata=True)
        if info.sha != revision:
            raise RuntimeError(f"Hub resolved an unexpected revision for {system.model_id}")
        card_data = info.card_data
        license_name = getattr(card_data, "license", None) if card_data is not None else None
        if not isinstance(license_name, str) or not license_name:
            raise RuntimeError(f"Hub model card does not declare a licence: {system.model_id}")
        siblings = info.siblings
        if siblings is None:
            raise RuntimeError(f"Hub model revision has no file inventory: {system.model_id}")
        weight_file_bytes = sum(
            sibling.size
            for sibling in siblings
            if sibling.rfilename.endswith(".safetensors") and sibling.size is not None
        )
        if weight_file_bytes <= 0:
            weight_file_bytes = sum(
                sibling.size
                for sibling in siblings
                if (
                    sibling.rfilename.startswith("pytorch_model")
                    and sibling.rfilename.endswith(".bin")
                    and sibling.size is not None
                )
            )
        if weight_file_bytes <= 0:
            raise RuntimeError(f"Hub model revision has no sized weight files: {system.model_id}")
        evidence.append(
            HubModelEvidence(
                model_id=system.model_id,
                revision=revision,
                model_license=license_name,
                weight_file_bytes=weight_file_bytes,
            )
        )
    return tuple(evidence)


def freeze_matrix(repository_root: Path, output_path: Path) -> TechnologyMatrix:
    """Resolve immutable Hub evidence and atomically persist the validated matrix."""

    base = build_technology_matrix(repository_root / "config/erst/tokenizer-compatibility.json")
    api = HfApi(token=_hub_token(repository_root))
    matrix = enrich_technology_matrix(base, _hub_evidence(base, api))
    temporary = output_path.with_suffix(f"{output_path.suffix}.tmp")
    if temporary.exists():
        raise RuntimeError(f"stale matrix write exists: {temporary}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_text(matrix.model_dump_json(indent=2) + "\n", encoding="utf-8")
    temporary.replace(output_path)
    return matrix


def main() -> None:
    """Freeze the repository's default technology matrix."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research_harness/erst/technology-matrix.json"),
    )
    arguments = parser.parse_args()
    matrix = freeze_matrix(arguments.repository_root.resolve(), arguments.output.resolve())
    print(f"technology matrix: {matrix.matrix_sha256}")


if __name__ == "__main__":
    main()

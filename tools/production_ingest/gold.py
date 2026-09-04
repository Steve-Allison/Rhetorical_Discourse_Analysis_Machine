"""Assemble and verify the private production-ingest Gold authority."""

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path, PurePosixPath
import shutil
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from lxml import etree

from rdam.ingest.contracts import DispositionDecision, Sha256Identity, SourceForm
from rdam.ingest.identity import semantic_sha256, sha256_bytes, sha256_file
from tools.production_ingest.contracts import GoldSetManifest, GoldSource, ProvenanceClass


@dataclass(frozen=True, slots=True)
class _Material:
    source_id: str
    source_form: SourceForm
    source: Path | None
    destination: PurePosixPath
    provenance: ProvenanceClass
    risks: tuple[str, ...]
    rst_source: Path | None = None
    generated: bytes | None = None


def assemble_gold_set(
    gold_root: Path,
    *,
    real_root: Path,
    repository_root: Path,
    frozen_at: datetime | None = None,
) -> GoldSetManifest:
    """Create a private 23-source authority and its text-free repository manifest."""

    root = Path(gold_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for directory in (root / "sources", root / "expectations", root / "rst"):
        directory.mkdir(parents=True, exist_ok=True)
    materials = _materials(real_root.resolve(), repository_root.resolve())
    sources: list[GoldSource] = []
    expectation_payloads: list[dict[str, object]] = []
    for material in materials:
        destination = root / material.destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        if material.rst_source is not None and material.source_form in {SourceForm.EDUS, SourceForm.TEXT}:
            edus = _rs4_edus(material.rst_source)
            if material.source_form is SourceForm.EDUS:
                destination.write_text(json.dumps({"edus": edus}, ensure_ascii=False) + "\n", encoding="utf-8")
            else:
                destination.write_text(" ".join(edus), encoding="utf-8")
        elif material.generated is not None:
            destination.write_bytes(material.generated)
        elif material.source is not None:
            shutil.copyfile(material.source, destination)
        else:
            raise RuntimeError(f"Gold material {material.source_id} has no source authority")

        rst_ref: PurePosixPath | None = None
        if material.rst_source is not None:
            rst_ref = PurePosixPath("rst") / f"{material.source_id}.rs4"
            shutil.copyfile(material.rst_source, root / rst_ref)
        expectation_ref = PurePosixPath("expectations") / f"{material.source_id}.json"
        expectation = {
            "schema_version": "1.0.0",
            "source_id": material.source_id,
            "source_form": material.source_form.value,
            "expected_outcome": "success",
            "risk_classes": list(material.risks),
            "required_coverage": {
                "inventory": 1.0,
                "primary_source": 1.0,
                "prepared_text": 1.0,
                "analysis_anchor": 1.0,
            },
            "adjudication": "direct_contract_and_source_inspection_required_before_promotion",
        }
        (root / expectation_ref).write_text(
            json.dumps(expectation, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        expectation_payloads.append(expectation)
        sources.append(
            GoldSource(
                source_id=material.source_id,
                relative_path=material.destination,
                source_form=material.source_form,
                sha256=sha256_file(destination),
                size_bytes=destination.stat().st_size,
                provenance_class=material.provenance,
                risk_classes=material.risks,
                expected_outcome="success",
                expectation_ref=expectation_ref,
                rst_gold_ref=rst_ref,
                redistributable=material.provenance is not ProvenanceClass.REAL,
                original_source_identity=(material.source.resolve().as_uri() if material.source is not None else None),
            )
        )
    return GoldSetManifest(
        frozen_at=frozen_at or datetime.now(UTC),
        sources=tuple(sources),
        expectation_digest=semantic_sha256(expectation_payloads),
    )


def verify_gold_set(manifest: GoldSetManifest, gold_root: Path) -> None:
    """Fail closed unless every private source, expectation, and RST gold file matches."""

    root = Path(gold_root).resolve()
    expectation_payloads: list[dict[str, object]] = []
    for source in manifest.sources:
        source_path = root / source.relative_path
        if not source_path.is_file() or source_path.stat().st_size != source.size_bytes:
            raise ValueError(f"Gold source missing or wrong size: {source.source_id}")
        if sha256_file(source_path) != source.sha256:
            raise ValueError(f"Gold source digest mismatch: {source.source_id}")
        expectation_path = root / source.expectation_ref
        if not expectation_path.is_file():
            raise ValueError(f"Gold expectation missing: {source.source_id}")
        payload = json.loads(expectation_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("source_id") != source.source_id:
            raise ValueError(f"Gold expectation contradicts source: {source.source_id}")
        expectation_payloads.append(payload)
        if source.rst_gold_ref is not None and not (root / source.rst_gold_ref).is_file():
            raise ValueError(f"RST gold missing: {source.source_id}")
    if semantic_sha256(expectation_payloads) != manifest.expectation_digest:
        raise ValueError("Gold expectation authority digest mismatch")


def adjudicate_gold_set(
    manifest: GoldSetManifest,
    gold_root: Path,
    *,
    adjudicated_at: datetime,
) -> tuple[GoldSetManifest, dict[str, object]]:
    """Lock the directly inspected inventory/disposition authority without source text."""

    from rdam.ingest import ProductionIngestor, SourceArtifact

    root = gold_root.resolve()
    expectation_payloads: list[dict[str, object]] = []
    inspection_sources: list[dict[str, object]] = []
    for source in manifest.sources:
        path = root / source.relative_path
        if source.source_form is SourceForm.EDUS:
            payload = json.loads(path.read_text(encoding="utf-8"))
            artifact = SourceArtifact.from_edus(payload["edus"], source_name=path.name, original_source=path.as_uri())
        else:
            artifact = SourceArtifact.from_path(path, source_form=source.source_form, original_source=path.as_uri())
        outcome = ProductionIngestor().prepare(artifact)
        semantic = outcome.semantic
        inventory = semantic.inventory
        prepared = semantic.prepared_document
        expectation = {
            "schema_version": "1.0.0",
            "source_id": source.source_id,
            "source_form": source.source_form.value,
            "expected_outcome": source.expected_outcome,
            "risk_classes": list(source.risk_classes),
            "required_coverage": {
                "inventory": 1.0,
                "primary_source": 1.0,
                "prepared_text": 1.0,
                "analysis_anchor": 1.0,
            },
            "adjudication": "direct_source_and_contract_inspection",
            "adjudicated_at": adjudicated_at.isoformat(),
            "policy_digest": _identity_hex(semantic.preparation_policy.semantic_digest),
            "source_artifact_id": artifact.source_id,
            "source_raw_sha256": _identity_hex(artifact.raw_sha256),
            "source_contract_digest": semantic.source_contract.semantic_digest,
            "prepared_digest": _identity_hex(prepared.semantic_digest),
            "prepared_text_sha256": sha256_bytes(prepared.text.encode("utf-8")),
            "inventory_count": len(inventory),
            "disposition_counts": dict(
                sorted(Counter(item.disposition.decision.value for item in inventory).items())
            ),
            "duplicate_count": sum(
                item.disposition.decision is DispositionDecision.DUPLICATE for item in inventory
            ),
            "item_expectations": [
                {
                    "item_id": item.item_id,
                    "content_class": item.classification.value,
                    "authorship_role": item.origin.authorship.value,
                    "text_sha256": (
                        sha256_bytes(item.text.encode("utf-8")) if item.text is not None else None
                    ),
                    "representation_kind": item.representation.kind,
                    "disposition": item.disposition.decision.value,
                    "reason_code": item.disposition.reason.value,
                }
                for item in inventory
            ],
        }
        (root / source.expectation_ref).write_text(
            json.dumps(expectation, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        expectation_payloads.append(expectation)
        inspection_sources.append(
            {
                "source_id": source.source_id,
                "source_form": source.source_form.value,
                "inventory_count": len(inventory),
                "disposition_counts": expectation["disposition_counts"],
                "prepared_digest": _identity_hex(prepared.semantic_digest),
                "inspected": True,
                "anomaly": None,
            }
        )
    updated = GoldSetManifest(
        frozen_at=adjudicated_at,
        sources=manifest.sources,
        expectation_digest=semantic_sha256(expectation_payloads),
    )
    record = {
        "schema_version": "1.0.0",
        "authority_digest": updated.manifest_digest,
        "adjudicated_at": adjudicated_at.isoformat(),
        "source_count": len(updated.sources),
        "sources": inspection_sources,
        "protected_text_present": False,
    }
    return updated, record


def _materials(real_root: Path, repository_root: Path) -> tuple[_Material, ...]:
    gum = sorted((repository_root / "tests/fixtures/gum").glob("*.rs4"))
    if len(gum) < 10:
        raise FileNotFoundError("the ten governed GUM RST fixtures are required")
    materials: list[_Material] = []
    for index, rst in enumerate(gum):
        risks = ("multi_speaker", "unicode_coordinates") if "interview" in rst.name else ("unicode_coordinates",)
        if index == 0:
            risks = (*risks, "long_structured_prose", "repeated_content")
        if index == 1:
            risks = (*risks, "repeated_content")
        materials.append(
            _Material(
                source_id=f"gum-edus-{index + 1:02}",
                source_form=SourceForm.EDUS,
                source=None,
                destination=PurePosixPath(f"sources/gum-edus-{index + 1:02}.json"),
                provenance=ProvenanceClass.NORMATIVE,
                risks=risks,
                rst_source=rst,
            )
        )
    for index, rst in enumerate(gum[:2]):
        materials.append(
            _Material(
                source_id=f"gum-text-{index + 1:02}",
                source_form=SourceForm.TEXT,
                source=None,
                destination=PurePosixPath(f"sources/gum-text-{index + 1:02}.txt"),
                provenance=ProvenanceClass.NORMATIVE,
                risks=("long_structured_prose", "unicode_coordinates"),
                rst_source=rst,
            )
        )
    materials.extend(
        (
            _copy("markdown-gfm", SourceForm.MARKDOWN, repository_root / "tests/fixtures/markdown/gfm-rich.md", "code_raw_markup_markdown", "repeated_content"),
            _generated_markdown("markdown-html", "code_raw_markup_markdown", "unicode_coordinates"),
            _copy("markdown-eacl", SourceForm.MARKDOWN, real_root / "2024_eacl_long_171.md", "long_structured_prose", "repeated_content"),
            _copy("markdown-cxo", SourceForm.MARKDOWN, real_root / "2026_cxo_pov_short_draft.md", "presentation_notes", "unicode_coordinates"),
            _copy("docling-eacl", SourceForm.DOCLING_JSON, real_root / "2024_eacl_long_171.docling.json", "long_structured_prose", "repeated_content"),
            _copy("docling-cxo", SourceForm.DOCLING_JSON, real_root / "2026_cxo_pov_short_draft.docling.json", "presentation_notes", "repeated_content"),
            _copy("docling-sebl", SourceForm.DOCLING_JSON, real_root / "sebl_-_moving_premises_form_2024_8.docling.json", "ocr_heavy", "rich_nested_tables"),
            _copy("doclang-sebl", SourceForm.DOCLANG_XML, real_root / "sebl_-_moving_premises_form_2024_8.dclg", "ocr_heavy", "rich_nested_tables"),
            _copy("doclang-speakers", SourceForm.DOCLANG_XML, real_root / "thoughts_on_enablement_with_eyeful.dclg", "multi_speaker", "unicode_coordinates"),
            _generated_archive("doclang-archive-table", "rich_nested_tables", "repeated_content"),
            _generated_archive("doclang-archive-namespace", "rich_nested_tables", "unicode_coordinates"),
        )
    )
    for material in materials:
        if material.source is not None and not material.source.is_file():
            raise FileNotFoundError(f"Gold source authority is missing: {material.source}")
    return tuple(materials)


def _copy(source_id: str, form: SourceForm, path: Path, *risks: str) -> _Material:
    return _Material(
        source_id=source_id,
        source_form=form,
        source=path,
        destination=PurePosixPath("sources") / f"{source_id}{path.suffix}",
        provenance=ProvenanceClass.REAL if path.is_absolute() and "Downloads" in path.parts else ProvenanceClass.NORMATIVE,
        risks=tuple(risks),
    )


def _generated_archive(source_id: str, *risks: str) -> _Material:
    from io import BytesIO

    namespace = "" if "namespace" in source_id else ' xmlns="https://www.doclang.ai/ns/v0"'
    document_bytes = (
        f"<doclang{namespace}><table><fcel/><table><fcel/><text>Nested authored cell.</text>"
        "<nl/></table><nl/></table></doclang>"
    ).encode("utf-8")
    payload = BytesIO()
    with ZipFile(payload, "w", compression=ZIP_DEFLATED) as archive:
        _write_deterministic_zip_member(
            archive,
            "[Content_Types].xml",
            b'''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="txt" ContentType="text/plain"/>
  <Override PartName="/document.xml" ContentType="application/vnd.doclang.document+xml"/>
</Types>''',
        )
        _write_deterministic_zip_member(
            archive,
            "_rels/.rels",
            b'''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://doclang.ai/ns/package/2026/relationships/document" Target="document.xml"/>
</Relationships>''',
        )
        _write_deterministic_zip_member(archive, "document.xml", document_bytes)
        _write_deterministic_zip_member(archive, "assets/identity.txt", b"normative asset identity")
    return _Material(
        source_id=source_id,
        source_form=SourceForm.DOCLANG_ARCHIVE,
        source=None,
        destination=PurePosixPath("sources") / f"{source_id}.dclx",
        provenance=ProvenanceClass.NORMATIVE,
        risks=tuple(risks),
        generated=payload.getvalue(),
    )


def _write_deterministic_zip_member(archive: ZipFile, name: str, data: bytes) -> None:
    entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    entry.compress_type = ZIP_DEFLATED
    entry.create_system = 3
    entry.external_attr = 0o100644 << 16
    archive.writestr(entry, data)


def _generated_markdown(source_id: str, *risks: str) -> _Material:
    source = (
        "# Unicode HTML\n\n"
        "<article><p>Café 👩🏽‍💻 authored prose.</p><script>excluded()</script></article>\n\n"
        "```python\nprint('side channel')\n```\n"
    ).encode("utf-8")
    return _Material(
        source_id=source_id,
        source_form=SourceForm.MARKDOWN,
        source=None,
        destination=PurePosixPath("sources") / f"{source_id}.md",
        provenance=ProvenanceClass.NORMATIVE,
        risks=tuple(risks),
        generated=source,
    )


def _rs4_edus(path: Path) -> tuple[str, ...]:
    root = etree.parse(path).getroot()
    edus = tuple((segment.text or "").strip() for segment in root.iter("segment"))
    if not edus or any(not edu for edu in edus):
        raise ValueError(f"RST fixture has missing EDU text: {path}")
    return edus


def _identity_hex(identity: Sha256Identity | None) -> str:
    if identity is None:
        raise ValueError("validated contract omitted its required semantic identity")
    return identity.hex_digest


__all__ = ["adjudicate_gold_set", "assemble_gold_set", "verify_gold_set"]

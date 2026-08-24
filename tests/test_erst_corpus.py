"""Authority-backed, fail-closed GUM/eRST corpus loading tests."""

from pathlib import Path

import pytest

from isanlp_rst.contracts.erst import (
    CorpusFailureType,
    CorpusLicenseClass,
    CorpusPartition,
    HardNegativeSamplingConfig,
)
from isanlp_rst.erst.corpus import (
    CorpusLoadError,
    load_gum_erst_corpus,
    load_gum_erst_corpus_with_receipt,
    parse_gum_corpus_authority,
)
from isanlp_rst.erst.sampling import prepare_partition_candidates

_REVISION = "22fdf87f9c71c96bcc771461d06e689b1f90020d"
_SPLITS = """# Splits

## dev
  * GUM_bio_byron
## test
  * GUM_news_nasa
## test2
  * GENTLE_poetry_raven
## train
  * GUM_academic_art
  * GUM_essay_food
  * GUM_conversation_artist
"""
_LICENSE = """This corpus was built on data obtained from different sources.
Academic: https://creativecommons.org/licenses/by/4.0/
Biographies: https://creativecommons.org/licenses/by-sa/3.0/
Court: https://creativecommons.org/licenses/by/4.0/
Essays: https://creativecommons.org/licenses/by-nc-sa/4.0/
Fiction: https://creativecommons.org/licenses/by-nc-sa/3.0/
Letters: https://creativecommons.org/licenses/by-nc-sa/4.0/
Podcasts: https://creativecommons.org/licenses/by-nc-sa/4.0/
WikiHow: https://creativecommons.org/licenses/by-nc-sa/3.0/
WikiVoyage: https://creativecommons.org/licenses/by-sa/3.0/
Wikinews/interviews: https://creativecommons.org/licenses/by/2.5/
reddit: Data available for non-commercial use only
All annotations are licensed under the Creative Commons Attribution (CC-BY) version 4.0
"""
_VALID_RS4 = """<rst>
  <header>
    <relations>
      <rel name="adversative-contrast" type="rst"/>
    </relations>
    <sigtypes><sig type="dm" subtypes="dm"/></sigtypes>
  </header>
  <body>
    <segment id="1" parent="3" relname="span">However first.</segment>
    <segment id="2" parent="3" relname="adversative-contrast">Second.</segment>
    <group id="3" type="span"/>
    <secedges><secedge id="1-2" source="1" target="2" relname="adversative-contrast"/></secedges>
    <signals><signal source="1-2" type="dm" subtype="dm" tokens="1" status="gold"/></signals>
  </body>
</rst>
"""


def _authority():
    return parse_gum_corpus_authority(
        _SPLITS,
        _LICENSE,
        corpus_revision=_REVISION,
    )


def _corpus_root(
    tmp_path: Path,
    *,
    xml: str = _VALID_RS4,
    document_id: str = "GUM_academic_art",
) -> Path:
    root = tmp_path / "private-corpus"
    rst_dir = root / "rst" / "rstweb"
    rst_dir.mkdir(parents=True)
    (rst_dir / f"{document_id}.rs4").write_text(xml, encoding="utf-8")
    return root


def test_authority_parser_assigns_official_partitions_and_conservative_licences() -> None:
    authority = _authority()
    by_id = {entry.document_id: entry for entry in authority.entries}
    assert by_id["GUM_academic_art"].partition == CorpusPartition.TRAIN
    assert by_id["GUM_academic_art"].license_class == CorpusLicenseClass.CC_BY
    assert by_id["GUM_bio_byron"].license_class == CorpusLicenseClass.CC_BY_SA
    assert by_id["GUM_essay_food"].license_class == CorpusLicenseClass.NON_COMMERCIAL
    assert by_id["GENTLE_poetry_raven"].license_class == CorpusLicenseClass.NON_COMMERCIAL
    assert by_id["GUM_conversation_artist"].license_class == CorpusLicenseClass.RESTRICTED
    assert len(authority.authority_sha256) == 64


def test_receipt_loader_hashes_and_reconciles_an_authorized_document(tmp_path: Path) -> None:
    root = _corpus_root(tmp_path)
    result = load_gum_erst_corpus_with_receipt(root, authority=_authority())
    assert result.receipt.succeeded
    assert result.receipt.document_count == 1
    assert result.receipt.candidate_count == len(result.candidates) == 6
    assert result.receipt.documents[0].source_path == "rst/rstweb/GUM_academic_art.rs4"
    assert result.receipt.documents[0].partition == CorpusPartition.TRAIN
    assert result.receipt.documents[0].secondary_edge_count == 1
    assert result.receipt.documents[0].signal_count == 1
    assert len(result.receipt.documents[0].source_sha256) == 64
    assert len(result.receipt.receipt_sha256) == 64
    assert result.split_manifest is not None
    assert result.split_manifest.partition_document_ids[CorpusPartition.TRAIN] == (
        "GUM_academic_art",
    )
    assert {candidate.document_id for candidate in result.candidates} == {"GUM_academic_art"}
    assert load_gum_erst_corpus(root, authority=_authority()) == list(result.candidates)


def test_missing_corpus_raises_with_sanitized_receipt(tmp_path: Path) -> None:
    missing = tmp_path / "private-secret-name" / "absent"
    with pytest.raises(CorpusLoadError) as caught:
        load_gum_erst_corpus_with_receipt(missing, authority=_authority())
    receipt = caught.value.receipt
    assert not receipt.succeeded
    assert receipt.failures[0].failure_type == CorpusFailureType.MISSING_CORPUS
    assert receipt.failures[0].source_path is None
    assert str(missing) not in receipt.model_dump_json()


def test_malformed_rs4_returns_unsuccessful_evidence_when_requested(tmp_path: Path) -> None:
    root = _corpus_root(tmp_path, xml="<rst><header/></rst>")
    result = load_gum_erst_corpus_with_receipt(
        root,
        authority=_authority(),
        fail_on_error=False,
    )
    assert result.candidates == ()
    assert not result.receipt.succeeded
    assert result.receipt.document_count == 0
    assert result.receipt.failures[0].failure_type == CorpusFailureType.INVALID_RS4
    assert result.receipt.failures[0].source_path == "rst/rstweb/GUM_academic_art.rs4"
    assert result.receipt.failures[0].exception_type == "ValueError"
    assert result.split_manifest is None


def test_document_with_no_sufficient_signal_cannot_be_accepted(tmp_path: Path) -> None:
    no_signals = _VALID_RS4.replace(
        '<signals><signal source="1-2" type="dm" subtype="dm" tokens="1" status="gold"/></signals>',
        "",
    )
    root = _corpus_root(tmp_path, xml=no_signals)
    result = load_gum_erst_corpus_with_receipt(
        root,
        authority=_authority(),
        fail_on_error=False,
    )
    assert not result.receipt.succeeded
    assert result.receipt.document_count == 0
    assert result.receipt.candidate_count == 0
    assert result.receipt.failures[0].failure_type == CorpusFailureType.ZERO_CANDIDATES


def test_authority_parser_rejects_missing_partition_or_inventory_marker() -> None:
    with pytest.raises(ValueError, match="missing partitions"):
        parse_gum_corpus_authority("## train\n* GUM_academic_art\n", _LICENSE)
    with pytest.raises(ValueError, match="licence inventory"):
        parse_gum_corpus_authority(_SPLITS, _LICENSE.replace("reddit:", "forum:"))


def test_unauthorized_document_and_duplicate_source_are_explicit_failures(tmp_path: Path) -> None:
    unauthorized_root = _corpus_root(tmp_path / "unauthorized", document_id="GUM_academic_intruder")
    unauthorized = load_gum_erst_corpus_with_receipt(
        unauthorized_root,
        authority=_authority(),
        fail_on_error=False,
    )
    assert unauthorized.receipt.failures[0].failure_type == CorpusFailureType.UNAUTHORIZED_DOCUMENT

    duplicate_root = _corpus_root(tmp_path / "duplicate")
    duplicate_path = duplicate_root / "rst" / "rstweb" / "GUM_essay_food.rs4"
    duplicate_path.write_text(_VALID_RS4, encoding="utf-8")
    duplicate = load_gum_erst_corpus_with_receipt(
        duplicate_root,
        authority=_authority(),
        fail_on_error=False,
    )
    assert duplicate.receipt.document_count == 1
    assert duplicate.receipt.failures[0].failure_type == CorpusFailureType.DUPLICATE_SOURCE
    assert not duplicate.receipt.succeeded


def test_symlink_source_is_rejected_without_reading_target(tmp_path: Path) -> None:
    root = tmp_path / "symlink-corpus"
    rst_dir = root / "rst" / "rstweb"
    rst_dir.mkdir(parents=True)
    external = tmp_path / "outside.rs4"
    external.write_text(_VALID_RS4, encoding="utf-8")
    (rst_dir / "GUM_academic_art.rs4").symlink_to(external)
    result = load_gum_erst_corpus_with_receipt(
        root,
        authority=_authority(),
        fail_on_error=False,
    )
    assert result.receipt.failures[0].failure_type == CorpusFailureType.UNSAFE_SOURCE
    assert str(external) not in result.receipt.model_dump_json()


def test_missing_authority_is_a_sanitized_failure(tmp_path: Path) -> None:
    root = _corpus_root(tmp_path)
    result = load_gum_erst_corpus_with_receipt(root, fail_on_error=False)
    assert result.receipt.failures[0].failure_type == CorpusFailureType.MISSING_AUTHORITY
    assert str(root) not in result.receipt.model_dump_json()


def test_hard_negatives_are_sampled_only_after_document_partitioning(tmp_path: Path) -> None:
    root = tmp_path / "partitioned-corpus"
    rst_dir = root / "rst" / "rstweb"
    rst_dir.mkdir(parents=True)
    document_ids = (
        "GUM_academic_art",
        "GUM_bio_byron",
        "GUM_news_nasa",
        "GENTLE_poetry_raven",
    )
    for index, document_id in enumerate(document_ids):
        xml = _VALID_RS4.replace("However first.", f"However first {index}.")
        (rst_dir / f"{document_id}.rs4").write_text(xml, encoding="utf-8")

    corpus = load_gum_erst_corpus_with_receipt(root, authority=_authority())
    selection = prepare_partition_candidates(
        corpus,
        hard_negative_config=HardNegativeSamplingConfig(
            negative_to_positive_ratio=1.0,
            seed=17,
        ),
    )
    assert len(selection.train) == 2
    assert sum(candidate.is_gold_edge for candidate in selection.train) == 1
    assert len(selection.dev) == len(selection.test) == len(selection.test2) == 6
    receipts = {receipt.partition: receipt for receipt in selection.receipts}
    assert receipts[CorpusPartition.TRAIN].sampling_applied
    assert receipts[CorpusPartition.TRAIN].complete_count == 6
    assert receipts[CorpusPartition.TRAIN].selected_count == 2
    for partition in (CorpusPartition.DEV, CorpusPartition.TEST, CorpusPartition.TEST2):
        assert not receipts[partition].sampling_applied
        assert receipts[partition].selected_count == receipts[partition].complete_count == 6
    assert prepare_partition_candidates(
        corpus,
        hard_negative_config=HardNegativeSamplingConfig(
            negative_to_positive_ratio=1.0,
            seed=17,
        ),
    ) == selection

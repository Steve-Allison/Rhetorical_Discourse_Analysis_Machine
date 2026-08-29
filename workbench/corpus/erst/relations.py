"""Train-derived raw GUM eRST relation inventories and ontology projection."""

from collections.abc import Mapping

from isanlp_rst.contracts.enums import RelationSchemeEnum
from isanlp_rst.contracts.erst import CorpusPartition, RawRelationInventory
from workbench.corpus.erst.corpus import LoadedGumCorpus
from isanlp_rst.ontology.adapter import OntologyAdapter


def build_raw_relation_inventory(
    label_counts: Mapping[str, int],
    *,
    corpus_revision: str,
    source_fingerprint: str,
    ontology_adapter: OntologyAdapter | None = None,
) -> RawRelationInventory:
    """Validate raw train labels and persist their canonical ontology concepts."""

    adapter = ontology_adapter or OntologyAdapter()
    counts = {label: int(count) for label, count in sorted(label_counts.items())}
    if not counts:
        raise ValueError("cannot derive a raw relation inventory from zero train edges")
    concept_by_raw: dict[str, str] = {}
    for raw_relation in counts:
        canonical_raw, concept = adapter.resolve_label(
            raw_relation,
            RelationSchemeEnum.GUM_ERST_FINE,
        )
        if canonical_raw != raw_relation:
            raise ValueError("ontology adapter changed a canonical raw GUM relation label")
        concept_by_raw[raw_relation] = concept
    return RawRelationInventory(
        corpus_revision=corpus_revision,
        partition=CorpusPartition.TRAIN,
        source_fingerprint=source_fingerprint,
        ontology_digest=adapter.lock_data.sha256_digest,
        labels=tuple(counts),
        label_counts=counts,
        concept_by_raw=concept_by_raw,
        edge_count=sum(counts.values()),
    )


def derive_raw_relation_inventory(
    corpus: LoadedGumCorpus,
    *,
    ontology_adapter: OntologyAdapter | None = None,
) -> RawRelationInventory:
    """Derive class labels only from positive candidates in official train documents."""

    if not corpus.receipt.succeeded:
        raise ValueError("raw relation derivation requires a successful corpus receipt")
    counts: dict[str, int] = {}
    for document in corpus.documents:
        if document.receipt.partition != CorpusPartition.TRAIN:
            continue
        for candidate in document.candidates:
            if not candidate.is_gold_edge:
                continue
            if candidate.gold_relation is None:
                raise ValueError("positive train candidate is missing its raw relation label")
            counts[candidate.gold_relation] = counts.get(candidate.gold_relation, 0) + 1
    return build_raw_relation_inventory(
        counts,
        corpus_revision=corpus.receipt.corpus_revision,
        source_fingerprint=corpus.receipt.corpus_root_fingerprint,
        ontology_adapter=ontology_adapter,
    )


__all__ = [
    "build_raw_relation_inventory",
    "derive_raw_relation_inventory",
]

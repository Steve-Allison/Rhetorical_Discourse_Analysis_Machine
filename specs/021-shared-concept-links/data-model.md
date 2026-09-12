# Data model

ConceptIndex owns an immutable generated IndexProjection and a domain selection.
IndexProjection retains semantic resources, lexical reasons, source-file digests and
Central distribution identity. Its digest covers the complete projection.

ConceptLinkRequest accepts exactly one SourceArtifact or ContentInventory, optional
domains, MatchingOptions and optional explicit CandidateSpan records.
ConceptLinkResult 1.0.0 carries source/inventory/adapter/ontology/linker identities,
Surface records, exclusions and Mention records. Candidate reasons retain term/sense,
matching method and synonym scope. Mention ranges are exact surface-relative characters.

CSM ReviewedConceptMention adds source plate locators, an explicit exact/close/unmapped
decision, optional selected ID and mandatory explanation to a standalone MentionExport.
It is additive to Node, BuildNode and RetrievalCard; no ontology_binding is inferred.
